"""Las dos etapas del agente.

Etapa 1 (lector):  cada documento -> JSON de datos.   Modelo chico, un documento por llamada.
Etapa 2 (conciliador): movimientos del extracto + candidatos -> decisiones.  Solo lo que el codigo no resuelve solo.

Lo determinístico (gris, tabla exacta, importe unico) lo resuelve el codigo sin modelo:
es mas barato, mas rapido y auditable.
"""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import lector
from config import DATOS, MODELOS
from extracto import es_gris, norm
from referencias import CUIT

TIPOS = ["factura", "nota_credito", "vep_impuesto", "liquidacion_servicio", "expensas", "recibo_sueldo",
         "resumen_sueldos", "comprobante_pago", "echeq", "remito", "retencion", "resumen_cuenta", "otro"]
S = {"type": "string"}
SCHEMA_LECTOR = {
    "type": "object", "additionalProperties": False,
    "required": ["tipo", "rol", "emisor", "emisor_cuit", "receptor", "receptor_cuit", "numero_comprobante",
                 "fecha", "importes", "identificador", "pertenece", "nota"],
    "properties": {
        "tipo": {"type": "string", "enum": TIPOS},
        "rol": {"type": "string", "enum": ["origen", "pago", "otro"]},
        "emisor": S, "emisor_cuit": S, "receptor": S, "receptor_cuit": S,
        "numero_comprobante": S, "fecha": S,
        "importes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["etiqueta", "monto"],
            "properties": {"etiqueta": S, "monto": {"type": "number"}}}},
        "identificador": S,
        "pertenece": {"type": "string", "enum": ["si", "no", "dudoso"]},
        "nota": S}}

SCHEMA_CONCILIADOR = {
    "type": "object", "additionalProperties": False, "required": ["decisiones"],
    "properties": {"decisiones": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["n", "docs", "comprobante", "detalle", "detalle_origen", "confianza", "motivo"],
        "properties": {
            "n": {"type": "integer"}, "docs": {"type": "array", "items": S}, "comprobante": S, "detalle": S,
            "detalle_origen": {"type": "string", "enum": ["tabla", "deducido", "ninguno"]},
            "confianza": {"type": "string", "enum": ["alta", "media", "baja"]}, "motivo": S}}}}}


def render(plantilla: str, **kw) -> str:
    for k, v in kw.items():
        plantilla = plantilla.replace("{{" + k + "}}", str(v))
    return plantilla


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


# ---------------------------------------------------------------- etapa 1
def etapa_lectura(llm, docs: list[Path], modelo: str, sistema: str, usuario: str, cache: Path,
                  workers: int = 4) -> dict[str, dict]:
    """Devuelve {doc: {extraccion, uso, truncado, reutilizado}}. Reusa el cache si el prompt y el modelo no cambiaron."""
    cache.mkdir(parents=True, exist_ok=True)
    huella = hashlib.sha256((sistema + usuario + modelo).encode()).hexdigest()[:8]

    def uno(p: Path):
        f = cache / f"{_sha(p)}_{huella}.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            d["reutilizado"] = True
            return p.name, d
        leido = lector.leer(p)
        contenido = []
        if leido["bloque"]:
            contenido.append(leido["bloque"])
        contenido.append({"type": "text", "text": usuario + (("\n\n" + leido["texto"]) if leido["texto"] else "")})
        n0 = len(llm.registro)
        ext = llm.llamar("lectura", modelo, sistema, contenido, SCHEMA_LECTOR, max_tokens=2000)
        u = llm.registro[-1] if len(llm.registro) > n0 else {}
        d = {"extraccion": ext, "truncado": leido["truncado"], "chars": leido["chars_originales"], "montos": leido["montos"],
             "vision": bool(leido["bloque"]),
             "uso": {k: u.get(k) for k in ("input_tokens", "output_tokens", "usd")}, "reutilizado": False}
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return p.name, d

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(uno, docs))


SOLO_INFORMATIVOS = {"remito", "retencion", "resumen_cuenta"}   # no justifican un pago: nunca son "documento de origen"
UNO_A_UNO = {"recibo_sueldo", "factura", "liquidacion_servicio"}          # cada uno respalda un movimiento cuando hay igual importe
COMPARTIDOS = {"resumen_sueldos", "expensas"}                            # un mismo documento respalda varios movimientos
EXCLUSIVOS = {"comprobante_pago", "recibo_sueldo"}                       # un comprobante de pago o recibo respalda UN solo movimiento


def normalizar_lecturas(lecturas: dict) -> dict:
    """Coherencia en codigo: el modelo a veces marca 'origen' a un remito o un certificado de retencion."""
    for d in lecturas.values():
        e = d["extraccion"]
        if e["tipo"] in SOLO_INFORMATIVOS and e["rol"] != "otro":
            e["rol_original"], e["rol"] = e["rol"], "otro"
        elif e["tipo"] == "comprobante_pago" and e["rol"] != "pago":
            e["rol_original"], e["rol"] = e["rol"], "pago"
    return lecturas


# ---------------------------------------------------------------- etapa 2
PALABRAS_COMUNES = {
    "compra", "tarjeta", "debito", "transferencia", "realizada", "inmediata", "recibida", "pago", "pagos", "servicios",
    "proveedores", "tarj", "nro", "online", "banking", "automatico", "sistema", "cuit", "cbu", "saldo", "factura",
    "sociedad", "anonima", "limitada", "haberes", "varios", "expensas", "agro", "srl", "sas"}
try:   # palabras que no distinguen a un emisor en la zona del cliente (ej. nombre de la localidad): archivo privado
    PALABRAS_COMUNES |= set(json.loads((DATOS / "empresa.json").read_text(encoding="utf-8")).get("palabras_locales", []))
except OSError:
    pass


def _tokens(texto: str) -> set[str]:
    return {t for t in norm(texto).split() if len(t) >= 4 and not t.isdigit() and t not in PALABRAS_COMUNES}


def importes_efectivos(e: dict) -> list[dict]:
    """Importes impresos + los que el banco debita aparte y el documento no imprime (se calculan en codigo, no con el modelo)."""
    imps = list(e["importes"])
    lab = lambda i: norm(i["etiqueta"])  # noqa: E731
    unif = next((i for i in imps if "unificado" in lab(i)), None)
    total = next((i for i in imps if lab(i) in ("total", "total detalle de conceptos", "total conceptos")), None)
    if unif and total and unif["monto"] > total["monto"]:
        imps.append({"etiqueta": "(derivado) total unificado - total = cuota de plan de pagos",
                     "monto": round(unif["monto"] - total["monto"], 2)})
    cap = next((i for i in imps if "cuota capital" in lab(i)), None)
    fun = next((i for i in imps if "fundac" in lab(i)), None)
    if cap and fun:
        imps.append({"etiqueta": "(derivado) cuota capital + fundacion educacional",
                     "monto": round(cap["monto"] + fun["monto"], 2)})
    return imps


def candidatos(mov: dict, lecturas: dict[str, dict], cuit_empresa: str) -> list[dict]:
    """Documentos que podrian respaldar el movimiento: importe exacto, suma de dos facturas, CUIT o nombre del emisor."""
    monto = abs(mov["importe"])
    cuits = {c for c in CUIT.findall(mov["concepto"]) if c != cuit_empresa}
    toks = _tokens(mov["concepto"])
    ok = {d: x["extraccion"] for d, x in lecturas.items()
          if (x["extraccion"]["tipo"] == "echeq" and "cheq" in norm(mov["concepto"]))      # un e-cheq solo respalda movimientos de cheques
          or (x["extraccion"]["tipo"] != "echeq" and x["extraccion"]["rol"] != "otro")}
    coinc = {d: [i for i in importes_efectivos(e) if abs(i["monto"] - monto) < 0.005] for d, e in ok.items()}
    en_texto = {d: lecturas[d].get("montos", {}).get(f"{monto:.2f}") for d in ok}      # importe impreso en el texto completo
    for d in ok:
        if not coinc[d] and en_texto[d]:
            coinc[d] = [{"etiqueta": "importe en el texto del documento", "monto": monto}]
    pares: dict[str, str] = {}
    if not any(coinc.values()):                              # suma de dos facturas del mismo emisor
        tot = [(d, i["monto"]) for d, e in ok.items() if e["rol"] == "origen" and e["pertenece"] != "no"
               for i in e["importes"] if "total" in norm(i["etiqueta"])]
        for a in range(len(tot)):
            for b in range(a + 1, len(tot)):
                (da, ma), (db, mb) = tot[a], tot[b]
                if da != db and ok[da]["emisor_cuit"] == ok[db]["emisor_cuit"] and abs(ma + mb - monto) < 0.005:
                    pares[da], pares[db] = db, da
    out = []
    for d, e in ok.items():
        por_cuit = bool(e["emisor_cuit"]) and e["emisor_cuit"] in cuits
        por_nombre = e["rol"] == "origen" and e["pertenece"] != "no" and bool(_tokens(e["emisor"]) & toks)
        if not (coinc[d] or por_cuit or por_nombre or d in pares):
            continue
        c = {"doc": d, "tipo": e["tipo"], "rol": e["rol"], "emisor": e["emisor"], "numero": e["numero_comprobante"],
             "fecha": e["fecha"], "identificador": e["identificador"], "pertenece": e["pertenece"],
             "importes": coinc[d] if coinc[d] else (e["importes"] if len(e["importes"]) <= 4 else e["importes"][:4]),
             "coincide_importe": bool(coinc[d]), "coincide_cuit": por_cuit, "coincide_nombre": por_nombre}
        if e["nota"]:
            c["nota"] = e["nota"][:90]
        if en_texto[d] and not any(abs(i["monto"] - monto) < 0.005 for i in importes_efectivos(e)):
            c["contexto_importe"] = en_texto[d]              # el importe aparece en una linea del texto (ej. un recibo dentro de un resumen)
        if coinc[d] and monto % 10000 == 0:
            c["importe_redondo"] = True                       # coincidencia poco informativa
        if d in pares:
            c["suma_con"] = pares[d]
        out.append(c)
    return out


def preparar(movs: list[dict], lecturas, refs, cuit_empresa: str, convenciones: dict | None = None):
    """Resuelve por regla lo que se puede. Devuelve (decisiones_por_regla, movimientos_para_el_modelo, candidatos_por_movimiento)."""
    convenciones = {norm(k): v for k, v in (convenciones or {}).items()}
    reglas, para_llm, todos = {}, [], {}
    for m in movs:
        if es_gris(m["concepto"]):
            continue
        tabla, _ = refs.buscar(m["concepto"])
        cands = candidatos(m, lecturas, cuit_empresa)
        todos[m["n"]] = cands
        por_importe = [c for c in cands if c["coincide_importe"]]
        conv = next((v for k, v in convenciones.items() if k in norm(m["concepto"])), None)
        if tabla and not cands:
            reglas[m["n"]] = {"n": m["n"], "docs": [], "comprobante": "", "detalle": tabla, "detalle_origen": "tabla",
                              "confianza": "media", "motivo": "regla: tabla exacta, sin documento candidato"}
        elif conv and not tabla and not cands:
            reglas[m["n"]] = {"n": m["n"], "docs": [], "comprobante": "", "detalle": conv, "detalle_origen": "deducido",
                              "confianza": "media", "motivo": "regla: convencion del cliente para este tipo de concepto"}
        elif (tabla and len(cands) == 1 and len(por_importe) == 1 and cands[0]["rol"] == "origen"
              and cands[0]["pertenece"] == "si" and (cands[0]["coincide_cuit"] or cands[0]["coincide_nombre"])
              and cands[0]["tipo"] != "vep_impuesto"):
            c = cands[0]
            reglas[m["n"]] = {"n": m["n"], "docs": [c["doc"]], "comprobante": c["numero"], "detalle": tabla,
                              "detalle_origen": "tabla", "confianza": "alta",
                              "motivo": "regla: importe unico + emisor coincide + tabla exacta"}
        else:
            para_llm.append({"n": m["n"], "fecha": m["fecha"], "concepto": m["concepto"], "importe": m["importe"],
                             "sugerencia_tabla": tabla, "pistas_tabla": [] if tabla else refs.pistas(m["concepto"]),
                             "candidatos": cands})
    return reglas, para_llm, todos


def etapa_conciliacion(llm, para_llm: list[dict], modelo: str, sistema: str, usuario: str, mes: str,
                       lote: int = 20) -> dict[int, dict]:
    decisiones: dict[int, dict] = {}
    for i in range(0, len(para_llm), lote):
        chunk = para_llm[i:i + lote]
        texto = render(usuario, cantidad=len(chunk), mes=mes,
                       movimientos_json=json.dumps(chunk, ensure_ascii=False, separators=(",", ":")))
        r = llm.llamar("conciliacion", modelo, sistema, [{"type": "text", "text": texto}],
                       SCHEMA_CONCILIADOR, max_tokens=250 * len(chunk) + 500)
        for d in r["decisiones"]:
            decisiones[d["n"]] = d
    return decisiones


# ---------------------------------------------------------------- armado final
PERIODO = re.compile(r"^(Retiro - |Personal - Haberes)")
SOSPECHA = re.compile(r"instruc|sospech|manipul", re.IGNORECASE)   # el lector avisa si un documento intenta dar ordenes
NUM_EN_LINEA = re.compile(r"[A-C]\s?\d{4}-\d{8}|\d{4,5}-\d{8}")   # numero de recibo impreso en una linea de un resumen
MMAAAA = re.compile(r"(?<!\d)(0[1-9]|1[0-2])-(20\d{2})(?!\d)")


def _afinidad(concepto: str, ext: dict) -> int:
    """Cuantas palabras del nombre en el concepto del banco aparecen en el documento (beneficiario o destinatario)."""
    campos = ext["receptor"] if ext["tipo"] == "recibo_sueldo" else " ".join((ext["identificador"], ext["nota"], ext["receptor"]))
    doc = _tokens(campos)
    nombres = sum(any(a.startswith(b) or b.startswith(a) for b in doc) for a in _tokens(concepto))
    cuit = 3 if any(c in re.sub(r"\D", "", campos) for c in CUIT.findall(concepto)) else 0     # CUIT del beneficiario en el concepto
    return nombres + cuit


def armar(movs: list[dict], reglas: dict, decisiones: dict, lecturas: dict, para_llm: list[dict], cands: dict,
          nombre_corto: str = "") -> list[dict]:
    """Junta reglas y decisiones del modelo, aplica las guardas en codigo y calcula el estado (color)."""
    sugerencia = {x["n"]: x["sugerencia_tabla"] for x in para_llm}
    ext = lambda x: lecturas[x]["extraccion"]  # noqa: E731
    por_n = {m["n"]: m for m in movs}
    D, AV = {}, {}
    for m in movs:
        if es_gris(m["concepto"]):
            continue
        n = m["n"]
        d = dict(reglas.get(n) or decisiones.get(n) or {
            "docs": [], "comprobante": "", "detalle": "", "detalle_origen": "ninguno",
            "confianza": "baja", "motivo": "el modelo no devolvio decision"})
        av = AV[n] = []
        d["docs"] = list(d["docs"])
        validos = [x for x in d["docs"] if x in lecturas]              # el modelo no puede citar documentos que no existen
        if validos != d["docs"]:
            av.append("guarda: se descartaron ids de documento inexistentes")
            d["docs"] = validos
        # Guarda: todo vinculo necesita al menos un documento con el importe exacto (o una suma exacta) impreso.
        evidencia = {c["doc"] for c in cands.get(n, []) if c["coincide_importe"] or "suma_con" in c}
        if d["docs"] and not (set(d["docs"]) & evidencia):
            av.append("guarda: se descartaron documentos vinculados sin el importe exacto")
            d["docs"], d["comprobante"] = [], ""
            d["confianza"] = "baja"
        D[n] = d
    # Documentos que respaldan varios movimientos por diseno (resumenes de sueldos y de expensas) y todos los comprobantes
    # de pago con el importe exacto: se agregan aunque el modelo haya elegido solo uno.
    for n, d in D.items():
        for c in cands.get(n, []):
            if c["doc"] in d["docs"] or not c["coincide_importe"]:
                continue
            if c["tipo"] in COMPARTIDOS or (c["rol"] == "pago" and (d["docs"] or _afinidad(por_n[n]["concepto"], ext(c["doc"])) > 0)):
                d["docs"].append(c["doc"])
                AV[n].append(f"guarda: se agrego {c['doc']} (importe exacto)")
        if any(ext(x)["tipo"] == "expensas" for x in d["docs"]):            # los documentos hermanos de un edificio van juntos
            for x, l in lecturas.items():
                if l["extraccion"]["tipo"] == "expensas" and l["extraccion"]["rol"] == "origen" and x not in d["docs"]:
                    d["docs"].append(x)
    # Exclusividad: un recibo o comprobante de pago respalda UN movimiento; si hay varios con el mismo importe, gana el
    # que tiene mas palabras del nombre en comun con el documento (el beneficiario). Los que quedan sin documento
    # buscan otro comprobante libre del mismo importe.
    usos: dict[str, list[int]] = {}
    for n, d in D.items():
        for x in d["docs"]:
            if ext(x)["tipo"] in EXCLUSIVOS:
                usos.setdefault(x, []).append(n)
    perdieron = []
    for x, ns in usos.items():
        if len(ns) > 1:
            mejor = max(ns, key=lambda n: (_afinidad(por_n[n]["concepto"], ext(x)), -n))
            for n in ns:
                if n != mejor:
                    D[n]["docs"].remove(x)
                    AV[n].append(f"guarda: {x} pertenece a otro movimiento (mejor coincidencia de nombre)")
                    perdieron.append(n)
    usados = {x for d in D.values() for x in d["docs"] if ext(x)["tipo"] in EXCLUSIVOS}
    for n in perdieron:
        libres = [c for c in cands.get(n, []) if c["coincide_importe"] and c["tipo"] in EXCLUSIVOS and c["doc"] not in usados]
        if libres:
            mejor = max(libres, key=lambda c: _afinidad(por_n[n]["concepto"], ext(c["doc"])))
            D[n]["docs"].append(mejor["doc"])
            usados.add(mejor["doc"])
            AV[n].append(f"guarda: se reasigno {mejor['doc']}")
    # Cobro parcial: un comprobante de pago con el importe exacto y UNA factura del mismo emisor (por nombre) por un monto mayor.
    for n, d in D.items():
        if (por_n[n]["importe"] > 0 and any(ext(x)["rol"] == "pago" for x in d["docs"])      # cobro parcial de una factura de venta
                and not any(ext(x)["rol"] == "origen" for x in d["docs"])):
            fact = [c for c in cands.get(n, []) if c["rol"] == "origen" and c["tipo"] == "factura" and c["coincide_nombre"]
                    and not c["coincide_importe"] and max((i["monto"] for i in c["importes"]), default=0) >= abs(por_n[n]["importe"])]
            if len(fact) == 1:
                d["docs"].append(fact[0]["doc"])
                AV[n].append(f"guarda: pago parcial de la factura {fact[0]['doc']}")
    # Empate de igual importe (dos sueldos iguales, dos facturas de gas iguales) sin pista de nombre: se asigna en orden
    # (numero de comprobante ascendente <-> movimiento ascendente).
    por_imp: dict[float, list[int]] = {}
    for n in D:
        por_imp.setdefault(round(por_n[n]["importe"], 2), []).append(n)
    for ns in por_imp.values():
        if len(ns) < 2:
            continue
        docs = sorted({c["doc"] for n in ns for c in cands.get(n, []) if c["coincide_importe"] and c["rol"] == "origen"
                       and c["tipo"] in UNO_A_UNO}, key=lambda x: ext(x)["numero_comprobante"])
        if len(docs) == len(ns) and max(_afinidad(por_n[n]["concepto"], ext(x)) for n in ns for x in docs) == 0:
            for n, x in zip(sorted(ns), docs):
                D[n]["docs"] = [y for y in D[n]["docs"] if ext(y)["tipo"] not in UNO_A_UNO] + [x]
                AV[n].append("guarda: empate de igual importe resuelto por orden")
    filas = []
    for m in movs:
        f = dict(m)
        if es_gris(m["concepto"]):
            f.update(estado="GRIS", detalle="", comprobante="", docs=[], detalle_origen="ninguno",
                     confianza="alta", motivo="cargo automatico del banco", fuente="regla")
            filas.append(f)
            continue
        n, d, avisos = m["n"], D[m["n"]], AV[m["n"]]
        sug = sugerencia.get(n)
        es_vep = any(ext(x)["tipo"] == "vep_impuesto" for x in d["docs"]) and bool(re.search(r"afip|arca", norm(m["concepto"])))
        # Guarda: un documento que trae "instrucciones" para el sistema es sospechoso: nunca da confianza alta.
        sospechosos = [x for x in d["docs"] if SOSPECHA.search(ext(x)["nota"])]
        if sospechosos:
            d["confianza"] = "baja"
            avisos.append("ALERTA: el lector marco instrucciones sospechosas en " + ", ".join(sospechosos))
        # Guarda: la tabla manda. El modelo no puede reescribirla ni dejarla vacia (salvo un VEP de AFIP/ARCA: su propio tipo de pago decide).
        if sug and not es_vep and d["detalle"] != sug:
            avisos.append("guarda: se restituyo el Detalle de la tabla")
            d["detalle"], d["detalle_origen"] = sug, "tabla"
        # Guarda: el N° de comprobante sale de los documentos de origen vinculados (no de lo que escribe el modelo),
        # salvo que el modelo lo haya tomado de una linea del texto del documento (contexto del importe).
        ctx_nums = list(dict.fromkeys(mm.group(0).strip() for c in cands.get(n, []) if c["doc"] in d["docs"] and "contexto_importe" in c
                                      for mm in [NUM_EN_LINEA.search(c["contexto_importe"])] if mm))
        if ctx_nums:                                          # el importe esta en una linea de recibo dentro del documento
            d["comprobante"] = " ; ".join(ctx_nums)
            avisos.append("guarda: comprobante tomado de la linea del documento donde figura el importe")
        ctx = " ".join(c.get("contexto_importe", "") for c in cands.get(n, []) if c["doc"] in d["docs"])
        nums = list(dict.fromkeys(ext(x)["numero_comprobante"] for x in d["docs"] if ext(x)["rol"] == "origen" and ext(x)["numero_comprobante"]))
        num_en_ctx = bool(d["comprobante"]) and re.sub(r"\D", "", d["comprobante"]) in re.sub(r"\D", "", ctx)
        if nums and nums != [d["comprobante"]] and not num_en_ctx and not ctx_nums:
            d["comprobante"] = " ; ".join(nums)
            avisos.append("guarda: comprobante tomado de los documentos de origen")
        # Guarda: expensas sin numero propio -> el periodo (MM-AAAA) que informa el documento.
        if not d["comprobante"] and any(ext(x)["tipo"] == "expensas" for x in d["docs"]):
            per = next((mm.group(0) for x in d["docs"] for mm in [MMAAAA.search(ext(x)["identificador"])] if mm), "")
            if not per:                                          # las expensas se pagan el mes siguiente al periodo que cubren
                y, mes = int(m["fecha"][:4]), int(m["fecha"][5:7]) - 1
                y, mes = (y - 1, 12) if mes == 0 else (y, mes)
                per = f"{mes:02d}-{y}"
            d["comprobante"] = per
            avisos.append("convencion: expensas sin numero -> periodo (MM-AAAA)")
        # Guarda: convencion de periodo (MM-AAAA) para retiros y haberes, salvo que haya una factura con numero propio.
        if PERIODO.match(d["detalle"]) and not any(ext(x)["tipo"] == "factura" and ext(x)["numero_comprobante"] for x in d["docs"]):
            d["comprobante"] = f"{m['fecha'][5:7]}-{m['fecha'][:4]}"
            avisos.append("convencion: comprobante = periodo")
        if nombre_corto and d["detalle"].startswith("Personal - Leyes"):
            d["detalle"] = f"Personal - Leyes - {nombre_corto}"                # convencion del cliente: el identificador es la empresa
        roles = [ext(x)["rol"] for x in d["docs"]]
        estado = "BLANCO" if "origen" in roles else "AMARILLO" if roles else "NARANJA"
        f.update(estado=estado, detalle=d["detalle"], comprobante=d["comprobante"], docs=d["docs"],
                 detalle_origen=d["detalle_origen"], confianza=d["confianza"],
                 motivo=(d["motivo"] + (" | " + "; ".join(avisos) if avisos else "")),
                 fuente="regla" if n in reglas else "modelo")
        filas.append(f)
    for f in filas:
        if not f["detalle"] and f["estado"] != "GRIS":
            gemelo = next((g for g in filas if g is not f and g["detalle"] and g["concepto"] == f["concepto"] and g["importe"] == f["importe"]), None)
            if gemelo:
                f["detalle"], f["detalle_origen"] = gemelo["detalle"], gemelo["detalle_origen"]
                f["motivo"] += f" | guarda: Detalle heredado del movimiento {gemelo['n']} (mismo concepto e importe)"
    return filas

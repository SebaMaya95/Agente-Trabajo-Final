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
        d = {"extraccion": ext, "truncado": leido["truncado"], "chars": leido["chars_originales"],
             "vision": bool(leido["bloque"]),
             "uso": {k: u.get(k) for k in ("input_tokens", "output_tokens", "usd")}, "reutilizado": False}
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return p.name, d

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(uno, docs))


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
    ok = {d: x["extraccion"] for d, x in lecturas.items() if x["extraccion"]["rol"] != "otro"}
    coinc = {d: [i for i in importes_efectivos(e) if abs(i["monto"] - monto) < 0.005] for d, e in ok.items()}
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
        if coinc[d] and monto % 10000 == 0:
            c["importe_redondo"] = True                       # coincidencia poco informativa
        if d in pares:
            c["suma_con"] = pares[d]
        out.append(c)
    return out


def preparar(movs: list[dict], lecturas, refs, cuit_empresa: str) -> tuple[dict, list[dict]]:
    """Resuelve por regla lo que se puede; devuelve (decisiones_por_regla, movimientos_para_el_modelo)."""
    reglas, para_llm = {}, []
    for m in movs:
        if es_gris(m["concepto"]):
            continue
        tabla, _ = refs.buscar(m["concepto"])
        cands = candidatos(m, lecturas, cuit_empresa)
        por_importe = [c for c in cands if c["coincide_importe"]]
        if tabla and not cands:
            reglas[m["n"]] = {"n": m["n"], "docs": [], "comprobante": "", "detalle": tabla, "detalle_origen": "tabla",
                              "confianza": "media", "motivo": "regla: tabla exacta, sin documento candidato"}
        elif (tabla and len(cands) == 1 and len(por_importe) == 1 and cands[0]["rol"] == "origen"
              and cands[0]["pertenece"] == "si" and (cands[0]["coincide_cuit"] or cands[0]["coincide_nombre"])):
            c = cands[0]
            reglas[m["n"]] = {"n": m["n"], "docs": [c["doc"]], "comprobante": c["numero"], "detalle": tabla,
                              "detalle_origen": "tabla", "confianza": "alta",
                              "motivo": "regla: importe unico + emisor coincide + tabla exacta"}
        else:
            para_llm.append({"n": m["n"], "fecha": m["fecha"], "concepto": m["concepto"], "importe": m["importe"],
                             "sugerencia_tabla": tabla, "pistas_tabla": [] if tabla else refs.pistas(m["concepto"]),
                             "candidatos": cands})
    return reglas, para_llm


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


def armar(movs: list[dict], reglas: dict, decisiones: dict, lecturas: dict, para_llm: list[dict]) -> list[dict]:
    """Junta reglas y decisiones del modelo, aplica las guardas en codigo y calcula el estado (color)."""
    sugerencia = {x["n"]: x["sugerencia_tabla"] for x in para_llm}
    filas = []
    for m in movs:
        f = dict(m)
        if es_gris(m["concepto"]):
            f.update(estado="GRIS", detalle="", comprobante="", docs=[], detalle_origen="ninguno",
                     confianza="alta", motivo="cargo automatico del banco", fuente="regla")
        else:
            d = dict(reglas.get(m["n"]) or decisiones.get(m["n"]) or {
                "docs": [], "comprobante": "", "detalle": "", "detalle_origen": "ninguno",
                "confianza": "baja", "motivo": "el modelo no devolvio decision"})
            avisos = []
            validos = [x for x in d["docs"] if x in lecturas]          # el modelo no puede citar documentos que no existen
            if validos != d["docs"]:
                avisos.append("guarda: se descartaron ids de documento inexistentes")
                d["docs"] = validos
            sug = sugerencia.get(m["n"])
            # Guarda 0: un documento que trae "instrucciones" para el sistema es sospechoso: nunca da confianza alta.
            sospechosos = [x for x in d["docs"] if x in lecturas and SOSPECHA.search(lecturas[x]["extraccion"]["nota"])]
            if sospechosos:
                d["confianza"] = "baja"
                avisos.append("ALERTA: el lector marco instrucciones sospechosas en " + ", ".join(sospechosos))
            # Guarda 1: la tabla manda. El modelo no puede reescribirla ni dejarla vacia.
            if sug and (d["detalle_origen"] == "tabla" or not d["detalle"]) and d["detalle"] != sug:
                avisos.append("guarda: se restituyo el Detalle de la tabla")
                d["detalle"], d["detalle_origen"] = sug, "tabla"
            # Guarda 2: el N° de comprobante sale de los documentos de origen vinculados (no de lo que escribe el modelo).
            ext = [lecturas[x]["extraccion"] for x in d["docs"] if x in lecturas]
            nums = list(dict.fromkeys(e["numero_comprobante"] for e in ext if e["rol"] == "origen" and e["numero_comprobante"]))
            if nums and nums != [d["comprobante"]]:
                d["comprobante"] = " ; ".join(nums)
                avisos.append("guarda: comprobante tomado de los documentos de origen")
            # Guarda 3: convencion de periodo (MM-AAAA) para retiros y haberes, salvo que haya una factura con numero propio.
            if PERIODO.match(d["detalle"]) and not any(e["tipo"] == "factura" and e["numero_comprobante"] for e in ext):
                d["comprobante"] = f"{m['fecha'][5:7]}-{m['fecha'][:4]}"
                avisos.append("convencion: comprobante = periodo")
            roles = [lecturas[x]["extraccion"]["rol"] for x in d["docs"] if x in lecturas]
            estado = "BLANCO" if "origen" in roles else "AMARILLO" if roles else "NARANJA"
            f.update(estado=estado, detalle=d["detalle"], comprobante=d["comprobante"], docs=d["docs"],
                     detalle_origen=d["detalle_origen"], confianza=d["confianza"],
                     motivo=(d["motivo"] + (" | " + "; ".join(avisos) if avisos else "")),
                     fuente="regla" if m["n"] in reglas else "modelo")
        filas.append(f)
    return filas

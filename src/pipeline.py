"""Las dos etapas del agente.

Etapa 1 (lector):  cada documento -> JSON de datos.   Modelo chico, un documento por llamada.
Etapa 2 (conciliador): movimientos del extracto + candidatos -> decisiones.  Solo lo que el codigo no resuelve solo.

Lo determinístico (gris, tabla exacta, importe unico) lo resuelve el codigo sin modelo:
es mas barato, mas rapido y auditable.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import lector
from config import DATOS, MODELOS
from extracto import es_gris
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
def candidatos(mov: dict, lecturas: dict[str, dict], cuit_empresa: str) -> list[dict]:
    """Documentos cuyo importe coincide con el movimiento o cuyo emisor tiene el CUIT del concepto."""
    monto = abs(mov["importe"])
    cuits = {c for c in CUIT.findall(mov["concepto"]) if c != cuit_empresa}
    out = []
    for doc, d in lecturas.items():
        e = d["extraccion"]
        if e["rol"] == "otro" or e["pertenece"] == "no":
            continue
        coinc = [i for i in e["importes"] if abs(i["monto"] - monto) < 0.005]
        por_cuit = e["emisor_cuit"] in cuits
        if not coinc and not por_cuit:
            continue
        out.append({
            "doc": doc, "tipo": e["tipo"], "rol": e["rol"], "emisor": e["emisor"], "numero": e["numero_comprobante"],
            "fecha": e["fecha"], "identificador": e["identificador"], "pertenece": e["pertenece"],
            "importes": e["importes"] if len(e["importes"]) <= 4 else coinc,
            "coincide_importe": bool(coinc), "coincide_cuit": por_cuit})
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
        elif tabla and len(cands) == 1 and len(por_importe) == 1 and cands[0]["rol"] == "origen":
            c = cands[0]
            reglas[m["n"]] = {"n": m["n"], "docs": [c["doc"]], "comprobante": c["numero"], "detalle": tabla,
                              "detalle_origen": "tabla", "confianza": "alta",
                              "motivo": "regla: importe unico + tabla exacta"}
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
def armar(movs: list[dict], reglas: dict, decisiones: dict, lecturas: dict) -> list[dict]:
    filas = []
    for m in movs:
        f = dict(m)
        if es_gris(m["concepto"]):
            f.update(estado="GRIS", detalle="", comprobante="", docs=[], detalle_origen="ninguno",
                     confianza="alta", motivo="cargo automatico del banco", fuente="regla")
        else:
            d = reglas.get(m["n"]) or decisiones.get(m["n"]) or {
                "docs": [], "comprobante": "", "detalle": "", "detalle_origen": "ninguno",
                "confianza": "baja", "motivo": "el modelo no devolvio decision"}
            roles = [lecturas[x]["extraccion"]["rol"] for x in d["docs"] if x in lecturas]
            estado = "BLANCO" if "origen" in roles else "AMARILLO" if roles else "NARANJA"
            f.update(estado=estado, detalle=d["detalle"], comprobante=d["comprobante"], docs=d["docs"],
                     detalle_origen=d["detalle_origen"], confianza=d["confianza"], motivo=d["motivo"],
                     fuente="regla" if m["n"] in reglas else "modelo")
        filas.append(f)
    return filas

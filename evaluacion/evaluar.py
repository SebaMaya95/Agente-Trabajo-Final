"""Compara la salida del agente con el cierre hecho a mano.

Que se mide (y con que cuidado):
  - comprobante: coincide el/los numeros con los del cierre manual (solo filas no grises).
  - detalle exacto y por categoria: solo contra celdas que la persona NO dejo en celeste
    (las celestes son deducciones sin validar, no sirven como verdad).
  - detalle 'de tabla' vs 'deducido': la Tabla actual ya incluye Detalles de agosto (se actualizo
    despues del cierre), asi que el acierto de lo 'deducido' es la medida honesta de la capacidad del modelo.
  - documentos: cada documento vinculado al movimiento correcto (segun el nombre que tenia en el cierre manual).
  - 'no encontre': documentos que el cierre manual dejo sin movimiento y el agente no vinculo.

Uso: python evaluar.py <ruta_salida_json> <mes>
"""
import csv
import json
import re
import sys
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from extracto import es_gris, norm  # noqa: E402


def num(s) -> set[str]:
    """Numeros de comprobante normalizados: sin prefijo de tipo, sin ceros a la izquierda por tramo."""
    if not s:
        return set()
    out = set()
    for parte in re.split(r"[;,]", str(s)):
        parte = re.sub(r"^(fc|fac|vep|a|b|c|comp|liq)\s+", "", parte.strip().lower())
        tramos = re.findall(r"\d+", parte)
        if tramos:
            out.add("-".join(t.lstrip("0") or "0" for t in tramos))
    return out


def cargar_esperado(mes: str):
    ws = openpyxl.load_workbook(RAIZ / f"datos_privados/{mes}/esperado/{mes}_manual.xlsx").active
    esp = {}
    for r in ws.iter_rows(min_row=2):
        celeste = bool(r[9].fill.fill_type) and str(r[9].fill.fgColor.rgb).endswith("B0E0FF")
        naranja = str(r[0].fill.fgColor.rgb).endswith("FFA500") if r[0].fill.fill_type else False
        esp[r[0].value] = {"detalle": r[9].value or "", "comprobante": r[10].value or "",
                           "celeste": celeste, "naranja": naranja, "concepto": r[6].value}
    return esp


def cargar_mapa(mes: str) -> dict[str, set]:
    with open(RAIZ / f"datos_privados/{mes}/esperado/mapa_documentos.csv", encoding="utf-8-sig") as fh:
        return {r["doc"]: {int(x) for x in r["movimientos_esperados"].split(",") if x} for r in csv.DictReader(fh)}


def evaluar(salida: list[dict], mes: str) -> dict:
    esp = cargar_esperado(mes)
    mapa = cargar_mapa(mes)
    con_doc = {n for m in mapa.values() for n in m}
    R = {"filas_no_gris": 0, "comprobante": {"ok": 0, "n": 0}, "detalle_exacto_validado": {"ok": 0, "n": 0},
         "categoria_validada": {"ok": 0, "n": 0}, "deducido_exacto": {"ok": 0, "n": 0},
         "deducido_categoria": {"ok": 0, "n": 0}, "tabla_exacto": {"ok": 0, "n": 0},
         "tiene_comprobante_coincide": {"ok": 0, "n": 0}, "no_reconstruibles": [], "errores": []}
    for f in salida:
        e = esp[f["n"]]
        if es_gris(e["concepto"] or ""):
            continue
        R["filas_no_gris"] += 1
        # Si el cierre manual tiene un comprobante pero ese documento NO esta en la carpeta,
        # ninguna version del agente puede acertarlo: se cuenta aparte, no como falla.
        if e["comprobante"] and f["n"] not in con_doc:
            R["no_reconstruibles"].append(f["n"])
            continue
        R["comprobante"]["n"] += 1
        ok_c = num(f["comprobante"]) == num(e["comprobante"])
        R["comprobante"]["ok"] += ok_c
        R["tiene_comprobante_coincide"]["n"] += 1
        R["tiene_comprobante_coincide"]["ok"] += bool(f["comprobante"]) == bool(e["comprobante"])
        if not ok_c:
            R["errores"].append({"n": f["n"], "campo": "comprobante", "agente": f["comprobante"],
                                 "esperado": e["comprobante"], "motivo": f["motivo"]})
        # detalle (solo si la persona lo valido)
        if e["detalle"] and not e["celeste"]:
            ok_d = norm(f["detalle"]) == norm(e["detalle"])
            ok_k = norm(f["detalle"].split(" - ")[0]) == norm(e["detalle"].split(" - ")[0])
            R["detalle_exacto_validado"]["n"] += 1
            R["detalle_exacto_validado"]["ok"] += ok_d
            R["categoria_validada"]["n"] += 1
            R["categoria_validada"]["ok"] += ok_k
            grupo = "tabla_exacto" if f["detalle_origen"] == "tabla" else "deducido_exacto"
            R[grupo]["n"] += 1
            R[grupo]["ok"] += ok_d
            if f["detalle_origen"] != "tabla":
                R["deducido_categoria"]["n"] += 1
                R["deducido_categoria"]["ok"] += ok_k
            if not ok_d:
                R["errores"].append({"n": f["n"], "campo": "detalle", "agente": f["detalle"],
                                     "esperado": e["detalle"], "origen": f["detalle_origen"], "motivo": f["motivo"]})
    # documentos
    vinc = {}
    for f in salida:
        for d in f["docs"]:
            vinc.setdefault(d, set()).add(f["n"])
    con_mov = {d: m for d, m in mapa.items() if m}
    sin_mov = [d for d, m in mapa.items() if not m]
    R["documentos"] = {
        "con_movimiento_esperado": len(con_mov),
        "vinculados_correctamente": sum(1 for d, m in con_mov.items() if vinc.get(d, set()) == m),
        "vinculados_parcial": sum(1 for d, m in con_mov.items() if vinc.get(d) and vinc[d] != m),
        "no_vinculados": sum(1 for d in con_mov if d not in vinc),
        "sin_movimiento_esperado": len(sin_mov),
        "sin_movimiento_bien_dejados": sum(1 for d in sin_mov if d not in vinc),
        "sin_movimiento_vinculados_de_mas": [d for d in sin_mov if d in vinc]}
    return R


def pct(x):
    return f"{100 * x['ok'] / x['n']:.0f}% ({x['ok']}/{x['n']})" if x["n"] else "n/a"


def informe(R: dict) -> str:
    d = R["documentos"]
    L = [f"Filas no grises: {R['filas_no_gris']} (evaluables: {R['filas_no_gris'] - len(R['no_reconstruibles'])}; "
         f"{len(R['no_reconstruibles'])} con comprobante en el cierre manual pero sin ese documento en la carpeta)",
         f"- N° de comprobante exacto: {pct(R['comprobante'])}",
         f"- Coincide si tiene o no comprobante: {pct(R['tiene_comprobante_coincide'])}",
         f"- Detalle exacto (solo celdas validadas por la persona): {pct(R['detalle_exacto_validado'])}",
         f"  · resueltos con la tabla: {pct(R['tabla_exacto'])}",
         f"  · deducidos por el modelo: {pct(R['deducido_exacto'])}  (categoría correcta: {pct(R['deducido_categoria'])})",
         f"- Categoría (1er nivel) correcta: {pct(R['categoria_validada'])}",
         f"Documentos con movimiento esperado: {d['con_movimiento_esperado']} -> "
         f"bien vinculados {d['vinculados_correctamente']}, parciales {d['vinculados_parcial']}, sin vincular {d['no_vinculados']}",
         f"Documentos sin movimiento (deben quedar afuera): {d['sin_movimiento_esperado']} -> "
         f"bien dejados {d['sin_movimiento_bien_dejados']}, vinculados de más {len(d['sin_movimiento_vinculados_de_mas'])}"]
    return "\n".join(L)


if __name__ == "__main__":
    ruta, mes = Path(sys.argv[1]), sys.argv[2]
    R = evaluar(json.loads(ruta.read_text(encoding="utf-8"))["filas"], mes)
    (ruta.parent / "evaluacion.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
    print(informe(R))

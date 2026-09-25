"""Genera corridas/RESUMEN.md a partir de las corridas publicadas (solo cifras, sin datos de clientes)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
filas = []
for d in sorted((REPO / "corridas").glob("0*")):
    m = json.loads((d / "salida.json").read_text(encoding="utf-8"))["meta"]
    e = json.loads((d / "evaluacion.json").read_text(encoding="utf-8"))
    pct = lambda x: f"{100 * x['ok'] / x['n']:.0f}% ({x['ok']}/{x['n']})" if x["n"] else "n/a"  # noqa: E731
    doc = e["documentos"]
    g = m["gastado_en_esta_corrida"]
    tin = sum(v["input_tokens"] for v in g.values())
    tout = sum(v["output_tokens"] for v in g.values())
    completo = m["costo_referencia_lectura_completa"]["usd"] + g.get("conciliacion", {}).get("usd", 0)   # lectura completa medida + conciliacion de esta corrida
    filas.append(f"| {d.name} | {m['fecha'][:16].replace('T', ' ')} | {m['modelo_lector'] or '-'} / {m['modelo_conciliador'] or '-'} | "
                 f"{pct(e['comprobante'])} | {pct(e['detalle_exacto_validado'])} | {doc['vinculados_correctamente']}/{doc['con_movimiento_esperado']} | "
                 f"{len(doc['sin_movimiento_vinculados_de_mas'])} | {tin:,} / {tout:,} | {m['usd_esta_corrida']:.3f} | {completo:.3f} |")
cab = ("# Resumen de corridas (mes 202608)\n\n"
       "Generado por `evaluacion/resumen_corridas.py`. Evaluación contra el cierre manual, sobre 90 movimientos evaluables "
       "(7 más quedan fuera porque el cierre manual tiene un comprobante cuyo documento no está en la carpeta). "
       "Las reglas de v2 a v4 se derivaron de las fallas de este mismo mes: los resultados son optimistas (ver DECISIONES.md, D12).\n\n"
       "| Corrida | Fecha | Modelo lector / conciliador | N° comprobante | Detalle (celdas validadas) | Docs bien vinculados | Docs vinculados de más | Tokens entrada / salida gastados | US$ gastados en la corrida | US$ pipeline completo* |\n"
       "|---|---|---|---|---|---|---|---|---|---|\n")
pie = ("\n(*) Lectura completa de los 128 documentos (medida en la corrida que la hizo) más la conciliación de esa corrida. "
       "Las corridas 03 a 05 y 07 reutilizaron la lectura de la 02 desde el cache, por eso gastaron mucho menos. "
       "La prueba de humo con 5 documentos (US$ 0,049) no se publica.\n")
(REPO / "corridas" / "RESUMEN.md").write_text(cab + "\n".join(filas) + "\n" + pie, encoding="utf-8")
print(cab + "\n".join(filas))

"""Genera corridas/RESUMEN.md a partir de las corridas publicadas (solo cifras, sin datos de clientes)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
filas = []
for d in sorted((REPO / "corridas").glob("[0-9]*")):
    m = json.loads((d / "salida.json").read_text(encoding="utf-8"))["meta"]
    e = json.loads((d / "evaluacion.json").read_text(encoding="utf-8"))
    pct = lambda x: f"{100 * x['ok'] / x['n']:.0f}% ({x['ok']}/{x['n']})" if x["n"] else "n/a"  # noqa: E731
    doc = e["documentos"]
    g = m["gastado_en_esta_corrida"]
    tin = sum(v["input_tokens"] for v in g.values())
    tout = sum(v["output_tokens"] for v in g.values())
    completo = m["costo_referencia_lectura_completa"]["usd"] + g.get("conciliacion", {}).get("usd", 0)   # lectura completa medida + conciliacion de esta corrida
    lect = json.loads((d / "lecturas_documentos.json").read_text(encoding="utf-8"))
    cfg = (m['modelo_lector'] or '-') + (f" (imágenes: {m['modelo_lector_imagenes']})" if m.get('modelo_lector_imagenes') not in (None, m['modelo_lector']) else '')         + ' / ' + (m['modelo_conciliador'] or '-') + (f", temperatura {m['temperatura']}" if m.get('temperatura') is not None else '')
    (d / "LEEME.md").write_text(f"""# Corrida {d.name}

- **Fecha:** {m['fecha'].replace('T', ' ')}
- **Modelos:** lector `{m['modelo_lector'] or 'ninguno (solo código)'}`{(' (imágenes y PDF escaneados: `' + m['modelo_lector_imagenes'] + '`)') if m.get('modelo_lector_imagenes') not in (None, m['modelo_lector']) else ''} / conciliador `{m['modelo_conciliador'] or 'ninguno (solo código)'}`{(', temperatura ' + str(m['temperatura'])) if m.get('temperatura') is not None else ''}
- **Prompts usados:** `prompts_usados/` (plantillas; los datos de la empresa se completan desde un archivo privado)

## Entrada
- El extracto del banco del mes (143 movimientos, saldos omitidos): `../entrada_extracto_202608.csv`
- {'Lo que el lector extrajo de cada uno de los ' + str(len(lect)) + ' documentos (los PDF y las fotos no se publican): `lecturas_documentos.json`' if lect else 'Ningún documento: esta corrida usa solo código y la Tabla de Referencias.'}

## Salida
- Una fila por movimiento, con estado (color), Detalle, N° de comprobante, documentos vinculados, confianza y motivo: `resultado.csv`
- Lo mismo en JSON, con la metadata de la corrida (cantidad de movimientos resueltos por regla y enviados al modelo, control de saldo, tokens y costo): `salida.json`
- Tokens de entrada y salida de cada llamada a la API: `llamadas.json`

## Evaluación contra el cierre manual
- N° de comprobante exacto: {pct(e['comprobante'])} · Detalle (celdas validadas): {pct(e['detalle_exacto_validado'])} · documentos bien vinculados: {doc['vinculados_correctamente']}/{doc['con_movimiento_esperado']}
- Cada error, uno por uno, con lo que decidió el agente y lo esperado: `evaluacion.json`
- Costo de esta corrida: US$ {m['usd_esta_corrida']:.3f} ({tin:,} tokens de entrada y {tout:,} de salida). Contexto y advertencias: `../RESUMEN.md` y `DECISIONES.md` del repositorio.

*Anonimizada: nombres, CUIT, cuentas, direcciones y saldos reemplazados; importes, fechas y números de comprobante reales.*
""", encoding="utf-8")
    filas.append(f"| {d.name} | {m['fecha'][:16].replace('T', ' ')} | {cfg} | "
                 f"{pct(e['comprobante'])} | {pct(e['detalle_exacto_validado'])} | {doc['vinculados_correctamente']}/{doc['con_movimiento_esperado']} | "
                 f"{len(doc['sin_movimiento_vinculados_de_mas'])} | {tin:,} / {tout:,} | {m['usd_esta_corrida']:.3f} | {completo:.3f} |")
cab = ("# Resumen de corridas (mes 202608)\n\n"
       "Generado por `evaluacion/resumen_corridas.py`. Evaluación contra el cierre manual, sobre 92 movimientos evaluables "
       "(5 más quedan fuera porque el cierre manual tiene un comprobante cuyo documento no está en la carpeta; ver DECISIONES.md, D9 y D18). "
       "Las reglas de v2 a v9 se derivaron de las fallas de este mismo mes: los resultados son optimistas (ver DECISIONES.md, D12 y D18).\n\n"
       "| Corrida | Fecha | Modelo lector / conciliador | N° comprobante | Detalle (celdas validadas) | Docs bien vinculados | Docs vinculados de más | Tokens entrada / salida gastados | US$ gastados en la corrida | US$ pipeline completo* |\n"
       "|---|---|---|---|---|---|---|---|---|---|\n")
pie = ("\n(*) Lectura completa de los 128 documentos (medida en la corrida que la hizo) más la conciliación de esa corrida. "
       "Las corridas 03 a 05 y 07 reutilizaron la lectura de la 02 desde el cache, por eso gastaron mucho menos. "
       "La prueba de humo con 5 documentos (US$ 0,049) no se publica.\n")
(REPO / "corridas" / "RESUMEN.md").write_text(cab + "\n".join(filas) + "\n" + pie, encoding="utf-8")
print(cab + "\n".join(filas))

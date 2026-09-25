"""Corre el agente sobre un mes.

  python src/main.py --mes 202608 --etiqueta v1 --lector haiku --conciliador haiku
  python src/main.py --mes 202608 --etiqueta base --sin-modelo      # linea base sin LLM (gratis)

Entradas (privadas):  datos_privados/<mes>/entrada/ (extracto.xls + documentos),
                      datos_privados/Tabla de Referencias.xlsx, datos_privados/empresa.json
Salidas:              datos_privados/<mes>/corridas/<fecha>_<etiqueta>/
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))

import pipeline as P  # noqa: E402
import salida  # noqa: E402
from config import DATOS, MODELOS, REPO  # noqa: E402
from extracto import control_saldo, leer_extracto  # noqa: E402
from referencias import Referencias  # noqa: E402

EXT = {".pdf", ".jpg", ".jpeg", ".png"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default="202608")
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--lector", default="haiku", choices=MODELOS)
    ap.add_argument("--conciliador", default="haiku", choices=MODELOS)
    ap.add_argument("--lector-imagenes", choices=MODELOS, default=None, help="modelo para imagenes y PDF escaneados (por defecto, el del lector)")
    ap.add_argument("--temperatura", type=float, default=None, help="solo Haiku (Sonnet 5 no admite el parametro)")
    ap.add_argument("--sin-cache", action="store_true", help="vuelve a leer todos los documentos aunque esten en el cache")
    ap.add_argument("--cache-prompt", action="store_true", help="marca el prompt del sistema como cacheable")
    ap.add_argument("--prompts", default=str(REPO / "prompts"))
    ap.add_argument("--sin-modelo", action="store_true")
    ap.add_argument("--limite", type=int, default=0, help="solo los primeros N documentos (prueba de humo)")
    ap.add_argument("--lote", type=int, default=20)
    a = ap.parse_args()

    base = DATOS / a.mes
    empresa = json.loads((DATOS / "empresa.json").read_text(encoding="utf-8"))
    movs = leer_extracto(base / "entrada" / "extracto.xls")
    docs = sorted(p for p in (base / "entrada").iterdir() if p.suffix.lower() in EXT)
    if a.limite:
        docs = docs[:a.limite]
    refs = Referencias(DATOS / "Tabla de Referencias.xlsx")
    run = base / "corridas" / f"{datetime.now():%Y%m%d-%H%M}_{a.etiqueta}"
    run.mkdir(parents=True)
    pdir = Path(a.prompts)
    shutil.copytree(pdir, run / "prompts", ignore=shutil.ignore_patterns("historial"))

    sub = dict(empresa=empresa["razon_social"], cuit=empresa["cuit"],
               no_pertenecen="; ".join(empresa["no_pertenecen"]),
               tambien_pertenecen="; ".join(empresa.get("tambien_pertenecen", [])), nombre_corto=empresa.get("nombre_corto", ""), categorias="; ".join(refs.categorias()))
    lecturas: dict = {}
    llm = None
    if a.sin_modelo:
        reglas, para_llm, cands = P.preparar(movs, {}, refs, empresa["cuit"], empresa.get("convenciones_concepto"))
        decisiones = {}
    else:
        from llm import LLM
        llm = LLM(temperatura=a.temperatura, cache_prompt=a.cache_prompt)
        leer = lambda n: (pdir / n).read_text(encoding="utf-8")  # noqa: E731
        sis_l = P.render(leer("system_prompt_lector.md"), **sub)
        lecturas = P.etapa_lectura(llm, docs, a.lector, sis_l, leer("user_prompt_lector.md"),
                                   base / "cache_lectura", modelo_imagenes=a.lector_imagenes, usar_cache=not a.sin_cache)
        P.normalizar_lecturas(lecturas)
        reglas, para_llm, cands = P.preparar(movs, lecturas, refs, empresa["cuit"], empresa.get("convenciones_concepto"))
        sis_c = P.render(leer("system_prompt.md"), **sub)
        decisiones = P.etapa_conciliacion(llm, para_llm, a.conciliador, sis_c, leer("user_prompt.md"), a.mes, a.lote)

    filas = P.armar(movs, reglas, decisiones, lecturas, para_llm, cands, empresa.get("nombre_corto", ""))
    reutilizadas = sum(d["reutilizado"] for d in lecturas.values())
    lect_usd = sum((d["uso"].get("usd") or 0) for d in lecturas.values())
    lect_in = sum((d["uso"].get("input_tokens") or 0) for d in lecturas.values())
    lect_out = sum((d["uso"].get("output_tokens") or 0) for d in lecturas.values())
    gastado = llm.resumen() if llm else {}
    meta = {
        "mes": a.mes, "etiqueta": a.etiqueta, "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo_lector": None if a.sin_modelo else MODELOS[a.lector]["id"],
        "modelo_lector_imagenes": None if a.sin_modelo else MODELOS[a.lector_imagenes or a.lector]["id"],
        "temperatura": None if a.sin_modelo else a.temperatura,
        "cache_prompt": a.cache_prompt,
        "modelo_conciliador": None if a.sin_modelo else MODELOS[a.conciliador]["id"],
        "movimientos": len(movs), "control_saldo": control_saldo(movs), "documentos": len(docs), "resueltos_por_regla": len(reglas),
        "enviados_al_modelo": len(para_llm), "lecturas_reutilizadas_del_cache": reutilizadas,
        "gastado_en_esta_corrida": gastado,
        "costo_referencia_lectura_completa": {"input_tokens": lect_in, "output_tokens": lect_out, "usd": round(lect_usd, 4)},
        "usd_esta_corrida": round(sum(v["usd"] for v in gastado.values()), 4),
        "docs_truncados": [k for k, d in lecturas.items() if d["truncado"]],
        "docs_con_vision": [k for k, d in lecturas.items() if d["vision"]],
    }
    (run / "salida.json").write_text(json.dumps({"meta": meta, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    (run / "lecturas.json").write_text(json.dumps(lecturas, ensure_ascii=False, indent=1), encoding="utf-8")
    if llm:
        (run / "llamadas.json").write_text(json.dumps(llm.registro, indent=1), encoding="utf-8")
    salida.excel_mes(filas, run / f"{a.mes}_agente.xlsx")
    salida.reporte(filas, run / f"{a.mes}_Reporte.xlsx", f"Cierre bancario {a.mes} ({a.etiqueta})",
                   {"Movimientos resueltos por regla (sin modelo)": len(reglas),
                    "Movimientos enviados al modelo": len(para_llm)})
    if lecturas:
        salida.copiar_renombrados(filas, lecturas, base / "entrada", run / "comprobantes_renombrados")
    (run / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    from evaluar import evaluar, informe
    R = evaluar(filas, a.mes)
    (run / "evaluacion.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Corrida: {run.name}   costo esta corrida: US$ {meta['usd_esta_corrida']}   "
          f"(lectura completa de referencia: US$ {meta['costo_referencia_lectura_completa']['usd']})")
    print(f"Resueltos por regla: {len(reglas)}  |  enviados al modelo: {len(para_llm)}")
    print(informe(R))


if __name__ == "__main__":
    main()

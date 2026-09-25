"""Completa el mapa documento -> movimiento usando el N° de comprobante del cierre manual.

Problema: el mapa original sale del NOMBRE que la persona le puso al archivo ("17 - Maquinaria - ... .pdf").
Los archivos que la persona vinculo pero nunca renombro (por ejemplo dos facturas que quedaron con su nombre
original) figuran como "sin movimiento" y el agente parece vincularlos "de mas" aunque acerto.
Solucion: buscar, en el texto de cada documento, el N° de comprobante que el cierre manual asigna a cada movimiento.
Los comprobantes que son solo un periodo (MM-AAAA) no se buscan.
Uso: python mapear_por_texto.py <mes>   -> escribe esperado/mapa_por_texto.csv (privado)
"""
import csv
import logging
import re
import sys
from pathlib import Path

import pypdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluar import cargar_esperado  # noqa: E402

logging.getLogger("pypdf").setLevel(logging.CRITICAL)
RAIZ = Path(__file__).resolve().parents[2]


def corridas_de_digitos(t: str) -> set[str]:
    return {x for x in re.findall(r"\d+", t)}


def main(mes: str):
    base = RAIZ / f"datos_privados/{mes}"
    textos = {}
    for f in sorted((base / "entrada").glob("*.pdf")):
        try:
            textos[f.name] = " ".join((p.extract_text() or "") for p in pypdf.PdfReader(str(f)).pages)
        except Exception:
            textos[f.name] = ""
    filas = []
    for n, e in cargar_esperado(mes).items():
        for comp in re.split(r"[;,]", str(e["comprobante"] or "")):
            comp = comp.strip()
            if not comp or re.fullmatch(r"\d{2}-\d{4}", comp):
                continue
            partes = [p.lstrip("0") or "0" for p in re.findall(r"\d+", comp)]
            partes_ok = [p for p in partes if len(p) >= 4]
            if not partes_ok:
                continue
            for doc, t in textos.items():
                corr = {c.lstrip("0") or "0" for c in corridas_de_digitos(t)}
                if all(p in corr for p in partes_ok):
                    filas.append({"movimiento": n, "doc": doc, "comprobante_buscado": comp})
    with open(base / "esperado/mapa_por_texto.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["movimiento", "doc", "comprobante_buscado"])
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} coincidencias movimiento-documento encontradas por texto")
    for r in filas:
        print(r["movimiento"], r["doc"], r["comprobante_buscado"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "202608")

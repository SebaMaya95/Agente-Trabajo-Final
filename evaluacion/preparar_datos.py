"""Prepara la entrada "ciega" de un mes cerrado para probar el agente.

Problema que resuelve: la carpeta del mes ya cerrado tiene los PDF renombrados
con el numero de movimiento, el detalle y el comprobante ("17 - Maquinaria -
Repuestos - Allochis - 0001-00005206.pdf"). Si el agente viera esos nombres,
la prueba estaria contaminada: tendria la respuesta en el nombre del archivo.

Que hace:
  1. Junta todos los PDF/imagenes del mes (raiz + "Sin movimientos").
  2. Elimina duplicados exactos (mismo contenido).
  3. Los copia a entrada/ con nombre neutro doc_NNN.ext (orden por hash, para
     que el orden tampoco filtre informacion).
  4. Guarda la correspondencia nombre-original <-> doc_NNN en esperado/ (privado).
  5. Copia el extracto del banco y el cierre ya hecho a mano (la "respuesta").

Uso:  python preparar_datos.py 202608
Todo lo que escribe queda en ../../datos_privados/ (fuera del repositorio).
"""
import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]            # .../Trabajo Final
ORIGEN = RAIZ / "Banco"
DESTINO = RAIZ / "datos_privados"
EXT_DOC = {".pdf", ".jpg", ".jpeg", ".png"}
PREFIJO_MOV = re.compile(r"^(\d+(?:\s*(?:,|y)\s*\d+)*)\s+-\s+")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(mes: str) -> None:
    src = ORIGEN / mes
    ent = DESTINO / mes / "entrada"
    esp = DESTINO / mes / "esperado"
    ent.mkdir(parents=True, exist_ok=True)
    esp.mkdir(parents=True, exist_ok=True)

    por_hash: dict[str, list[Path]] = {}
    ignorados = []
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.name.startswith("~$"):
            continue
        if p.suffix.lower() in EXT_DOC:
            por_hash.setdefault(sha(p), []).append(p)
        else:
            ignorados.append(p.relative_to(src).as_posix())

    filas = []
    for i, h in enumerate(sorted(por_hash), start=1):
        originales = por_hash[h]
        ext = originales[0].suffix.lower()
        doc = f"doc_{i:03d}{ext}"
        shutil.copy2(originales[0], ent / doc)
        movs = set()
        for o in originales:
            m = PREFIJO_MOV.match(o.name)
            if m:
                movs.update(int(n) for n in re.findall(r"\d+", m.group(1)))
        filas.append({
            "doc": doc,
            "sha256": h,
            "nombres_originales": " | ".join(o.relative_to(src).as_posix() for o in originales),
            "movimientos_esperados": ",".join(str(n) for n in sorted(movs)),
        })

    with open(esp / "mapa_documentos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    # extracto del banco (es un TSV latin-1 disfrazado de .xls) y cierre manual
    shutil.copy2(src / "descargaUltimosMovimientos (1).xls", ent / "extracto.xls")
    shutil.copy2(src / f"{mes}.xlsx", esp / f"{mes}_manual.xlsx")
    shutil.copy2(ORIGEN / "Tabla de Referencias.xlsx", DESTINO / "Tabla de Referencias.xlsx")

    (esp / "archivos_ignorados.json").write_text(
        json.dumps(ignorados, ensure_ascii=False, indent=2), encoding="utf-8")
    con_mov = sum(1 for f in filas if f["movimientos_esperados"])
    print(f"{len(filas)} documentos unicos en entrada/ "
          f"({sum(len(v) for v in por_hash.values()) - len(filas)} duplicados eliminados)")
    print(f"{con_mov} con movimiento asignado en el cierre manual, {len(filas) - con_mov} sin asignar")
    print(f"{len(ignorados)} archivos de otro tipo ignorados (docx, zip, msi, jsx, xls sueltos...)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "202608")

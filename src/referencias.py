"""Tabla de Referencias: memoria de Detalles ya validados por la persona.

Busqueda en dos niveles, sin modelo:
  1. clave del concepto (normalizada, sin nro de tarjeta) -> Detalle unico
  2. CUIT de 11 digitos dentro del concepto -> Detalle unico
Si no hay coincidencia, se ofrecen hasta 3 'pistas' parecidas para que el modelo decida.
"""
import re
from difflib import SequenceMatcher
from pathlib import Path

import openpyxl

from extracto import clave_concepto

CUIT = re.compile(r"(?<!\d)(\d{11})(?!\d)")


class Referencias:
    def __init__(self, ruta: Path):
        ws = openpyxl.load_workbook(ruta, read_only=True)["Referencias"]
        self.filas = [(r[0], r[3]) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] and r[3]]
        por_clave: dict[str, set] = {}
        por_cuit: dict[str, set] = {}
        for concepto, detalle in self.filas:
            por_clave.setdefault(clave_concepto(concepto), set()).add(detalle)
            for c in CUIT.findall(concepto):
                por_cuit.setdefault(c, set()).add(detalle)
        # solo se usan las claves que apuntan a un unico Detalle (las ambiguas van como pista)
        self.por_clave = {k: next(iter(v)) for k, v in por_clave.items() if len(v) == 1}
        self.por_cuit = {k: next(iter(v)) for k, v in por_cuit.items() if len(v) == 1}
        self.claves = list(por_clave)
        self.detalle_de_clave = {k: sorted(v) for k, v in por_clave.items()}

    def buscar(self, concepto: str) -> tuple[str | None, str]:
        k = clave_concepto(concepto)
        if k in self.por_clave:
            return self.por_clave[k], "clave"
        for c in CUIT.findall(concepto):
            if c in self.por_cuit:
                return self.por_cuit[c], "cuit"
        return None, ""

    def pistas(self, concepto: str, n: int = 3) -> list[str]:
        k = clave_concepto(concepto)
        rank = sorted(((SequenceMatcher(None, k, c).ratio(), c) for c in self.claves), reverse=True)[:n]
        return sorted({d for r, c in rank if r >= 0.6 for d in self.detalle_de_clave[c]})

    def categorias(self) -> list[str]:
        """Pares 'Categoria - Subcategoria' ya usados: sirven de vocabulario al modelo."""
        pares = {" - ".join(d.split(" - ")[:2]) for _, d in self.filas}
        return sorted(pares)

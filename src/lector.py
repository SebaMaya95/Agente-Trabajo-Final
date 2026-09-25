"""Herramienta: leer un documento (PDF o imagen) y devolver lo que se le manda al modelo.

Regla de ahorro: si el PDF tiene texto, se manda solo texto (barato). Solo los PDF
escaneados y las fotos van como imagen/documento (caro), y las fotos se achican antes.
"""
import base64
import io
import logging
import re
from pathlib import Path

import pypdf
from PIL import Image

from config import MAX_CHARS_CABEZA, MAX_CHARS_COLA, MAX_LADO_IMAGEN

logging.getLogger("pypdf").setLevel(logging.ERROR)
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _limpiar(t: str) -> str:
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def leer(ruta: Path) -> dict:
    """Devuelve {'texto': str|None, 'bloque': dict|None, 'truncado': bool, 'chars_originales': int}."""
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        try:
            texto = _limpiar("\n".join((p.extract_text() or "") for p in pypdf.PdfReader(str(ruta)).pages))
        except Exception:
            texto = ""
        if len(texto) >= 50:
            n = len(texto)
            truncado = n > MAX_CHARS_CABEZA + MAX_CHARS_COLA
            if truncado:
                texto = texto[:MAX_CHARS_CABEZA] + "\n[...recortado...]\n" + texto[-MAX_CHARS_COLA:]
            return {"texto": texto, "bloque": None, "truncado": truncado, "chars_originales": n}
        datos = base64.standard_b64encode(ruta.read_bytes()).decode()
        return {"texto": None, "truncado": False, "chars_originales": 0,
                "bloque": {"type": "document",
                           "source": {"type": "base64", "media_type": "application/pdf", "data": datos}}}
    if ext in MEDIA:
        img = Image.open(ruta)
        img.thumbnail((MAX_LADO_IMAGEN, MAX_LADO_IMAGEN))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=85)
        return {"texto": None, "truncado": False, "chars_originales": 0,
                "bloque": {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                       "data": base64.standard_b64encode(buf.getvalue()).decode()}}}
    raise ValueError(f"tipo no soportado: {ext}")

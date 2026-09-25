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


RE_MONTO = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}|\d+\.\d{2})(?!\d)")


def montos_del_texto(texto: str, ventana: int = 70, tope: int = 400) -> dict[str, str]:
    """Todos los importes impresos en el texto COMPLETO (aunque luego se recorte para el modelo), con su contexto.
    Se calcula en local, sin modelo: sirve para encontrar un importe que el lector no listo o que estaba en la parte recortada."""
    out: dict[str, str] = {}
    plano = re.sub(r"\s+", " ", texto)
    for m in RE_MONTO.finditer(plano):
        s_ = m.group(1)
        v = float(s_.replace(".", "").replace(",", ".")) if "," in s_ else float(s_)
        k = f"{v:.2f}"
        if k not in out and len(out) < tope:
            out[k] = plano[max(0, m.start() - ventana): m.end() + ventana]
    return out


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
            montos = montos_del_texto(texto)
            truncado = n > MAX_CHARS_CABEZA + MAX_CHARS_COLA
            if truncado:
                texto = texto[:MAX_CHARS_CABEZA] + "\n[...recortado...]\n" + texto[-MAX_CHARS_COLA:]
            return {"texto": texto, "bloque": None, "truncado": truncado, "chars_originales": n, "montos": montos}
        datos = base64.standard_b64encode(ruta.read_bytes()).decode()
        return {"texto": None, "truncado": False, "chars_originales": 0, "montos": {},
                "bloque": {"type": "document",
                           "source": {"type": "base64", "media_type": "application/pdf", "data": datos}}}
    if ext in MEDIA:
        img = Image.open(ruta)
        img.thumbnail((MAX_LADO_IMAGEN, MAX_LADO_IMAGEN))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=85)
        return {"texto": None, "truncado": False, "chars_originales": 0, "montos": {},
                "bloque": {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                       "data": base64.standard_b64encode(buf.getvalue()).decode()}}}
    raise ValueError(f"tipo no soportado: {ext}")

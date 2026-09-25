"""Rutas, modelos y precios. Nada de datos reales vive en este archivo."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATOS = REPO.parent / "datos_privados"          # fuera del repo (ver .gitignore)

# Precios USD por millon de tokens (tabla oficial vigente al 2026-06; verificar antes de citar)
MODELOS = {
    "haiku": {"id": "claude-haiku-4-5", "usd_in": 1.00, "usd_out": 5.00},
    "sonnet": {"id": "claude-sonnet-5", "usd_in": 2.00, "usd_out": 10.00},
}

# Documentos: texto que se le manda al modelo (caracteres). Se guarda cabeza + cola
# porque en facturas y liquidaciones los totales suelen estar al final.
MAX_CHARS_CABEZA = 4000
MAX_CHARS_COLA = 2000
MAX_LADO_IMAGEN = 1568                           # px; mas grande no mejora la lectura y cuesta tokens


def cargar_env() -> None:
    """Carga datos_privados/.env (ANTHROPIC_API_KEY=...) sin imprimir nada."""
    env = DATOS / ".env"
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

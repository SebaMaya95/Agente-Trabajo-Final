"""Lee el extracto del banco (texto tabulado latin-1 con extension .xls) y clasifica cargos automaticos."""
import re
import unicodedata
from datetime import datetime
from pathlib import Path

# Cargos que el banco aplica solo, sin comprobante posible (fila GRIS).
PATRON_GRIS = re.compile(
    r"impuesto ley 25\.?413|\biva\b|iva percepcion|comision|imp\.? al debito|imp\.? ley 25\.?413",
    re.IGNORECASE)


def norm(texto: str) -> str:
    """minusculas, sin tildes, sin signos, espacios colapsados."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def clave_concepto(concepto: str) -> str:
    """Igual que norm() pero sin numero de tarjeta ni el relleno 'factura/fac/exp/var/hab'."""
    t = norm(concepto)
    t = re.sub(r"\btarj nro \d+\b", "", t)
    t = re.sub(r"\b(factura|fac|exp|var|hab|cuo|saldo|expensas|varios|haberes)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _importe(s: str) -> float:
    s = s.strip()
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-").replace(".", "").replace(",", ".")
    v = float(s)
    return -v if neg else v


def leer_extracto(ruta: Path) -> list[dict]:
    lineas = ruta.read_text(encoding="latin-1").splitlines()
    inicio = next(i for i, l in enumerate(lineas) if l.startswith("Fecha\t")) + 1
    movs = []
    for l in lineas[inicio:]:
        c = l.split("\t")
        if len(c) < 8 or not re.match(r"\d{1,2}/\d{1,2}/\d{4}$", c[0].strip()):
            continue                              # filas vacias, de saldo o con ####
        movs.append({
            "n": len(movs) + 1,
            "fecha": datetime.strptime(c[0].strip(), "%d/%m/%Y").date().isoformat(),
            "suc_origen": c[1].strip(), "desc_sucursal": c[2].strip(),
            "cod_operativo": c[3].strip(), "referencia": c[4].strip(),
            "concepto": re.sub(r"\s+", " ", c[5]).strip(),
            "importe": _importe(c[6]), "saldo": c[7].strip(),
        })
    return movs


def es_gris(concepto: str) -> bool:
    return bool(PATRON_GRIS.search(concepto))


def control_saldo(movs: list[dict]) -> dict:
    """Control de integridad: el saldo de cada fila debe ser el anterior mas el importe. Detecta filas perdidas o mal leidas."""
    saldos = [_importe(m["saldo"]) for m in movs]
    saltos = [movs[i]["n"] for i in range(1, len(movs)) if abs(saldos[i - 1] + movs[i]["importe"] - saldos[i]) > 0.01]
    return {"filas": len(movs), "filas_que_no_cierran": saltos, "cuadra": not saltos,
            "saldo_inicial": round(saldos[0] - movs[0]["importe"], 2), "saldo_final": saldos[-1],
            "suma_importes": round(sum(m["importe"] for m in movs), 2)}

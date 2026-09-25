"""Convierte una corrida privada en una carpeta publicable (anonimizada) dentro de corridas/.

Que se anonimiza: nombres de personas y empresas, CUIT, cuentas/CBU, direcciones, y el saldo.
Que se conserva: importes, fechas, numeros de comprobante y toda la logica (para poder reconstruir la corrida).

Dos modos de reemplazo:
  - campos estructurados (concepto, detalle, emisor, identificador): toda palabra que no este en la lista
    de palabras permitidas (vocabulario bancario y de categorias) se reemplaza por un alias estable.
  - texto libre (motivo, nota): solo se reemplazan las palabras que ya fueron aliasadas en los campos
    estructurados, para no destruir la legibilidad.
Despues se verifica: ningun nombre real puede aparecer en ningun archivo publicado.

Uso: python publicar_corrida.py <carpeta_corrida_privada> <numero_y_nombre>   (ej: ... 20260925-1343_v4 04_v4)
"""
import csv
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPO = RAIZ / "Agente-Trabajo-Final"
sys.path.insert(0, str(REPO / "src"))
from referencias import Referencias  # noqa: E402

PALABRAS_PERMITIDAS = set("""
transferencia realizada inmediata recibida debito credito automatico compra tarjeta pago pagos servicios proveedores
retiro efectivo online banking emp sistema por impuesto ley comision iva percepcion cheque deposito echeq factura
fac exp var hab cuo cuit cbu saldo tarj nro cta cte snp directo haberes varios expensas sindicato leyes personal
accionista mantenimiento maquinaria repuestos insumo insumos flete agricultura ganaderia ganaderia venta cereal
electricidad gas internet telefonia software salud asesoramiento asociacion estudio contable combustible ferreteria
materiales electricos plomeria herramientas embargo tasas marcas senales vehiculos camion aeronave equip rural
alimentacion indumentaria administracion analisis laboratorio parque impuesto arca arba ganancias sociales iva iibb
senasa efectivo diag calle ruta suministro depto cochera liq vep boleta comprobante pagos mes
de del la el los las y en con sin para sobre desde hasta este esta que
capital cuota descuento importe monto origen pagado region retencion retenciones semestre sueldo sueldos subtotal total
neto gravado cargo fijo variable energia electrica unificado fundacion educacional plan detalle conceptos periodo transferido
adelanto ordinarias egresos consorcio propietario propietarios inquilino unidad funcional departamento dpto impuestos
derivado enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre moneda pesos usd ars
tasa saldo primer segundo cuenta banco liquidacion resumen comprobante operacion transferencia judicial
feria general vinculado sociedades empleador gastos retenido segun productos servicio empresa movimiento movimientos documento documentos concepto precio recaudacion pagar practicada tipo impuestos impuesto vep consolidado
""".split())


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


VALORES_EJEMPLO_REALES = [("80.210,02", "<importe-real-1>"), ("80210.02", "<importe-real-1>"), ("1023536.89", "<importe-real-2>"),
                          ("1018855.9", "<importe-real-3>"), ("4680.99", "<importe-real-4>"), ("00011-00153429", "<n-real-1>"),
                          ("00011-00155355", "<n-real-2>"), ("$2.000.000", "$<importe-real-5>"), ('"monto":2000000', '"monto":<importe-real-5>'),
                          ("FC 0001-00000004", "<n-real-3>")]
GLOSARIO = RAIZ / "datos_privados" / "glosario_alias.json"   # privado: mapa palabra real -> alias


class Anon:
    def __init__(self, permitidas: set[str]):
        self.ok = permitidas
        g = json.loads(GLOSARIO.read_text(encoding="utf-8")) if GLOSARIO.exists() else {}
        self.alias: dict[str, str] = {k: v for k, v in g.get("alias", {}).items() if k not in permitidas}   # palabra real -> alias estable entre corridas
        self.en_libre: set[str] = {w for w in g.get("en_libre", []) if w not in permitidas}               # palabras que tambien se reemplazan en texto libre
        self.digitos: dict[str, str] = {}

    def guardar(self) -> None:
        GLOSARIO.write_text(json.dumps({"alias": self.alias, "en_libre": sorted(self.en_libre)},
                                       ensure_ascii=False, indent=1), encoding="utf-8")

    def _alias(self, w: str) -> str:
        k = _norm(w)
        if k not in self.alias:
            self.alias[k] = f"Nombre{len(self.alias) + 1:03d}"
        return self.alias[k]

    def _num(self, n: str) -> str:
        if n not in self.digitos:
            base = str(int(hashlib.sha256(n.encode()).hexdigest(), 16) % 10 ** len(n)).zfill(len(n))
            self.digitos[n] = n[:2] + base[2:] if len(n) == 11 else base
        return self.digitos[n]

    def estructurado(self, t: str, libre: bool = True) -> str:
        """libre=False para etiquetas genericas ('total', 'cargo fijo'): se aliasan pero no contaminan el texto libre."""
        if not t:
            return t
        t = re.sub(r"\d{9,}", lambda m: self._num(m.group()), t)      # CUIT, cuentas, CBU, referencias largas

        def cambio(m):
            k = _norm(m.group())
            if k in self.ok:
                return m.group()
            if libre:
                self.en_libre.add(k)
            return self._alias(m.group())
        return re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", cambio, t)

    def libre(self, t: str) -> str:
        if not t:
            return t
        t = re.sub(r"\d{9,}", lambda m: self._num(m.group()), t)
        return re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}",
                      lambda m: self.alias[_norm(m.group())] if _norm(m.group()) in self.en_libre else m.group(), t)


def main(run: Path, destino_nombre: str) -> None:
    sal = json.loads((run / "salida.json").read_text(encoding="utf-8"))
    lec = json.loads((run / "lecturas.json").read_text(encoding="utf-8")) if (run / "lecturas.json").exists() else {}
    ev = json.loads((run / "evaluacion.json").read_text(encoding="utf-8"))
    refs = Referencias(RAIZ / "datos_privados" / "Tabla de Referencias.xlsx")
    permitidas = set(PALABRAS_PERMITIDAS)
    for _, d in refs.filas:                                            # vocabulario de categorias (niveles 1 y 2)
        for seg in d.split(" - ")[:2]:
            permitidas |= {_norm(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", seg)}
    extra = RAIZ / "datos_privados" / "terminos_sensibles.json"        # privado: palabras del vocabulario de categorias que identifican al cliente
    if extra.exists():
        permitidas -= {_norm(t) for t in json.loads(extra.read_text(encoding="utf-8"))}
    a = Anon(permitidas)

    from extracto import leer_extracto
    ent = REPO / "corridas" / "entrada_extracto_202608.csv"
    if not ent.exists():
        with open(ent, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["n", "fecha", "concepto", "importe"])          # se omite el saldo
            for m in leer_extracto(RAIZ / "datos_privados/202608/entrada/extracto.xls"):
                w.writerow([m["n"], m["fecha"], a.estructurado(m["concepto"]), m["importe"]])
    dest = REPO / "corridas" / destino_nombre
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    filas = []
    for f in sal["filas"]:
        filas.append({
            "n": f["n"], "fecha": f["fecha"], "concepto": a.estructurado(f["concepto"]), "importe": f["importe"],
            "estado": f["estado"], "detalle": a.estructurado(f["detalle"]), "detalle_origen": f["detalle_origen"],
            "comprobante": f["comprobante"], "docs": f["docs"], "confianza": f["confianza"], "fuente": f["fuente"],
            "motivo": f["motivo"]})
    lecturas = {}
    for doc, d in lec.items():
        e = d["extraccion"]
        lecturas[doc] = {
            "tipo": e["tipo"], "rol": e["rol"], "emisor": a.estructurado(e["emisor"]), "emisor_cuit": a.estructurado(e["emisor_cuit"]),
            "receptor": a.estructurado(e["receptor"]), "numero_comprobante": e["numero_comprobante"], "fecha": e["fecha"],
            "importes": [{"etiqueta": a.estructurado(i["etiqueta"], libre=False), "monto": i["monto"]} for i in e["importes"]],
            "identificador": a.estructurado(e["identificador"]), "pertenece": e["pertenece"], "nota": e["nota"],
            "uso": d["uso"], "vision": d["vision"], "truncado": d["truncado"]}
    # texto libre: recien ahora, con el glosario completo
    for f in filas:
        f["motivo"] = a.libre(f["motivo"])
    for l in lecturas.values():
        l["nota"] = a.libre(l["nota"])
    errores = [{**e, "agente": a.estructurado(str(e["agente"])) if e["campo"] == "detalle" else e["agente"],
                "esperado": a.estructurado(str(e["esperado"])) if e["campo"] == "detalle" else e["esperado"],
                "motivo": a.libre(e["motivo"])} for e in ev["errores"]]
    ev_pub = {**ev, "errores": errores}
    meta = {k: v for k, v in sal["meta"].items()}
    if "control_saldo" in meta:                                        # los saldos son datos del cliente: solo se publica si cuadra
        meta["control_saldo"] = {k: meta["control_saldo"][k] for k in ("filas", "cuadra", "filas_que_no_cierran")}

    (dest / "salida.json").write_text(json.dumps({"meta": meta, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    (dest / "lecturas_documentos.json").write_text(json.dumps(lecturas, ensure_ascii=False, indent=1), encoding="utf-8")
    (dest / "evaluacion.json").write_text(json.dumps(ev_pub, ensure_ascii=False, indent=2), encoding="utf-8")
    if (run / "llamadas.json").exists():
        shutil.copy2(run / "llamadas.json", dest / "llamadas.json")
    shutil.copytree(run / "prompts", dest / "prompts_usados")
    for f in (dest / "prompts_usados").glob("*.md"):                   # v1-v4 tenian valores reales en los ejemplos (DECISIONES D16)
        t = f.read_text(encoding="utf-8")
        for viejo, nuevo in VALORES_EJEMPLO_REALES:
            t = t.replace(viejo, nuevo)
        f.write_text(t, encoding="utf-8")
    with open(dest / "resultado.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "fecha", "concepto", "importe", "estado", "detalle", "n_comprobante", "documentos", "confianza", "origen_detalle", "fuente", "motivo"])
        for f in filas:
            w.writerow([f["n"], f["fecha"], f["concepto"], f["importe"], f["estado"], f["detalle"], f["comprobante"],
                        " ".join(f["docs"]), f["confianza"], f["detalle_origen"], f["fuente"], f["motivo"]])
    a.guardar()
    print(f"{destino_nombre}: publicada. {len(a.alias)} nombres aliasados.")

    # verificacion: ningun nombre real en lo publicado
    sensibles = set(a.alias)
    crudo = " ".join(str(x) for f in sal["filas"] for x in (f["concepto"], f["detalle"])) + " " + \
        " ".join(d["extraccion"]["emisor"] + " " + d["extraccion"]["receptor"] for d in lec.values())
    cuits = set(re.findall(r"\d{11}", crudo))
    texto_pub = _norm(" ".join(p.read_text(encoding="utf-8") for p in dest.rglob("*") if p.is_file() and p.suffix in (".json", ".csv") and p.name != "llamadas.json"))
    fugas = [s for s in sensibles if len(s) >= 5 and re.search(rf"\b{re.escape(s)}\b", texto_pub)]
    fugas += [c for c in cuits if c in texto_pub]
    if fugas:
        shutil.rmtree(dest)
        sys.exit(f"FUGA DE DATOS, no se publico: {sorted(fugas)[:15]}")
    print("verificacion de fuga: OK (ningun nombre ni CUIT real en los archivos publicados)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])

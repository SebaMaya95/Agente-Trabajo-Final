# DECISIONES — la historia de cómo se construyó

> Registro cronológico, escrito a medida que pasaban las cosas. Las cifras son las medidas reales de cada corrida.
> Fechas: el armado del repo empezó el 25/09/2026, después de la fecha original de entrega (13/09); se consulta prórroga con el profesor.

## D1 · Elección del caso y alcance (25/09)
**Caso:** conciliar cada mes el extracto bancario de una empresa agropecuaria con los comprobantes de la carpeta del mes: completar `N° Comprobante` y `DETALLE` (Categoría - Subcategoría - Identificador), marcar el estado de cada fila con colores, renombrar los comprobantes y generar un reporte de importe por categoría.

**De dónde viene:** ya existía una versión hecha en Cowork como una única instrucción larga (~5.000 palabras) que hacía el cierre mensual, la corrida semanal, el cruce de echeqs contra comprobantes sueltos y un circuito de tres facturas con una empresa vinculada. Cada regla del texto nació de una falla real: documentos que cubren dos movimientos, expensas sin número de comprobante, fechas guardadas como serial de Excel, recibos de pago confundidos con la factura, etc.

**Qué se achicó y por qué** (para dos semanas y media de atención parcial):
- Se quitó el cruce de echeqs y el circuito de facturas con la empresa vinculada: son casos particulares de un solo cliente, difíciles de evaluar y no cambian la arquitectura.
- Se quitó la corrida programada semanal: lo que se evalúa es el agente, no el agendador. Corre a demanda sobre un mes.
- Se conservó: leer extracto y comprobantes, vincular, categorizar, estado por color, renombrado y reporte por categoría.

## D2 · Datos reales en un repositorio público (25/09)
Los datos son de clientes reales (CUIT, razones sociales, nombres de personas, saldos). Decisiones:
- El repo vive en su propia carpeta (`Agente-Trabajo-Final/`) y los datos reales en `datos_privados/`, **fuera** del repo. Así, subir la carpeta del repo (incluso arrastrándola desde el navegador) no puede arrastrar datos.
- `.gitignore` bloquea además `*.xls`, `*.xlsx`, `*.zip` y `.env`.
- Los prompts del repo no contienen nombres reales: usan marcadores (`{{empresa}}`, `{{cuit}}`) que el código completa desde un archivo privado, y los ejemplos son ficticios.
- Lo que se publique de las corridas será una versión anonimizada.

## D3 · El "Excel" del banco no es un Excel (25/09)
`descargaUltimosMovimientos (1).xls` es un archivo de texto con tabuladores en latin-1: Excel lo abre igual, pero `xlrd` falla con `Expected BOF record`. Se lee como texto: se busca la fila que empieza con `Fecha` y se descartan las filas vacías, de saldo y las que no empiezan con una fecha. Resultado: **143 movimientos, en el mismo orden y con los mismos importes que el cierre manual** (verificado fila por fila).
En la misma carpeta hay otro `.xls` de otra cuenta y otro banco (Banco Nación): el agente solo lee el archivo que se le indica.

## D4 · Cómo probar sin hacer trampa: entrada "ciega" (25/09)
Problema: la carpeta de agosto ya cerrada tiene los comprobantes renombrados con el número de movimiento, el detalle y el comprobante (`17 - Maquinaria - Repuestos - X - 0001-00005206.pdf`). Si el agente viera esos nombres tendría la respuesta en el nombre del archivo.

Solución (`evaluacion/preparar_datos.py`): se juntan todos los PDF e imágenes (raíz + `Sin movimientos`), se eliminan duplicados exactos por hash (57 de 185) y se copian como `doc_001.pdf`… en orden de hash, sin pistas. Quedan **128 documentos únicos: 68 con movimiento asignado en el cierre manual y 60 que no corresponden a ningún movimiento** (otras empresas, meses anteriores, duplicados, manuales). Que casi la mitad no corresponda a nada hace que "saber decir *este no es de acá*" pese tanto como el match. Los nombres originales quedan solo en un mapa privado, para evaluar.

## D5 · Qué cuenta como "verdad" (25/09)
- El cierre manual tiene 45 celdas de Detalle en celeste: son deducciones de la versión anterior que la persona no terminó de validar. **No se usan como verdad**: el Detalle se evalúa solo contra las celdas no celestes (40 filas no grises).
- La Tabla de Referencias se actualizó el 10/09, después del cierre de agosto, y ya incluye Detalles de agosto. Por eso se mide por separado lo resuelto **con la tabla** y lo **deducido por el modelo**: solo lo segundo mide la capacidad del modelo sin filtración.
- Problema de fondo de la tabla: el mismo concepto del banco puede tener distinto Detalle según el documento (pagos a AFIP: Ganancias vs IVA vs cargas sociales). En agosto, 3 de los 44 movimientos resueltos por tabla difieren del cierre manual. Queda como riesgo: la tabla es una sugerencia, no una verdad.

## D6 · Arquitectura: qué hace el código y qué hace el modelo (25/09)
Se evaluó una llamada única con todo el mes (128 documentos, del orden de 250 mil tokens más el extracto). Se descartó: cara por corrida, difícil de auditar y con riesgo de errores al buscar importes exactos en un contexto enorme.

Diseño elegido, dos etapas:
1. **Lector** (modelo chico, una llamada por documento): saca tipo, rol (origen / pago / otro), emisor, CUIT, número de comprobante y **todos los importes impresos**. Si el PDF tiene texto va solo texto (172 de 178 tienen); solo los escaneados y las fotos van como imagen, y las fotos se achican a 1568 px.
2. **Conciliador** (una llamada por lote de 20 movimientos): recibe únicamente lo que el código no resolvió solo, con candidatos ya filtrados por importe exacto o CUIT.

El código resuelve sin modelo: filas grises (cargos automáticos del banco), Detalle por tabla exacta, y el caso "importe único + tabla". Motivo: más barato, más rápido, reproducible y auditable.

**Modelos:** criterio del curso, el más chico que hace bien la tarea. Se arranca con Haiku 4.5 (US$1 / US$5 por millón de tokens de entrada / salida) y se compara con Sonnet 5 (US$2 / US$10) en las corridas finales. No se usa un modelo grande por defecto: el costo lo decide la medición.

## D7 · Línea base sin modelo (25/09, corrida `base-sin-modelo`)
Solo código + tabla (sin lector ni conciliador). Costo: US$0.
- 44 de 97 movimientos no grises resueltos con la tabla; 53 quedan para el modelo.
- Detalle exacto sobre celdas validadas: 32/40 (80%); de los que resolvió la tabla, 32/34.
- Comprobantes: 0 documentos vinculados (68 esperados). El "21%" de comprobante exacto es engañoso: son las filas que en el cierre manual tampoco tienen comprobante. Queda anotado como advertencia sobre la métrica, y por eso se mide también cuántos documentos quedan bien vinculados.
- Los 60 documentos que no corresponden a nada quedan bien afuera (trivial: no se vincula ninguno).

Esto fija el piso contra el que hay que ganar.

*(Las iteraciones con modelo se agregan abajo a medida que se corren.)*

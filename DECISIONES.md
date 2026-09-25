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
- Detalle exacto sobre celdas validadas: 32/38 (84%, con la evaluación corregida de D9; medida originalmente como 32/40); todo lo que resolvió fue con la tabla.
- Comprobantes: 0 documentos vinculados (68 esperados). El "22%" de comprobante exacto (20/90) es engañoso: son las filas que en el cierre manual tampoco tienen comprobante. Queda anotado como advertencia sobre la métrica, y por eso se mide también cuántos documentos quedan bien vinculados.
- Los 60 documentos que no corresponden a nada quedan bien afuera (trivial: no se vincula ninguno).

Esto fija el piso contra el que hay que ganar.

## D8 · Corrida v1: Haiku 4.5 en las dos etapas (25/09)
Antes, una prueba de humo con 5 documentos (US$ 0,05) confirmó que la API, el esquema de salida y el lector funcionan: ~US$ 0,004 por documento. Después, la corrida completa sobre los 128 documentos.

**Costo real v1:** US$ 0,53 (medido; 5 de los 128 documentos ya estaban en el cache de la prueba de humo, por eso la lectura completa de referencia es US$ 0,51 y no 0,49) (lector: 123 llamadas, 376.047 tokens de entrada y 22.965 de salida = US$ 0,49; conciliador: 4 llamadas, 21.695 de entrada y 4.246 de salida = US$ 0,04). El lector es el 92% del gasto.

**Resultado (contra el cierre manual, ya con la evaluación corregida, ver D9):**
- N° de comprobante exacto: 49/90 (54%).
- Documentos bien vinculados: 42 de 68; 6 parciales; 20 sin vincular.
- De los 60 documentos que no deben vincularse, 56 quedaron bien afuera; 4 se vincularon de más.
- Detalle exacto sobre celdas validadas: 33/38 (87%): 29/31 con la tabla, pero solo 4/7 cuando lo deduce el modelo.
- 32 movimientos resueltos por regla (sin conciliador) y 65 enviados al modelo.

**Qué falló (análisis de los 48 errores de comprobante, mirando para cada movimiento qué había leído el lector del documento esperado):**
1. **Liquidaciones de la cooperativa eléctrica (19 movimientos).** Cada liquidación respalda dos débitos: el total del detalle de conceptos y la cuota de un plan de pagos, que el documento no imprime como un importe propio (es *total unificado − total*, o *cuota capital + fundación educacional*). Al no estar ese importe en la lista del lector, el movimiento quedaba "sin candidatos". Además el lector tomó el número interno de factura (`B 0012-…`) en vez del "Comprobante adicional" (`B-0014-…`) que usa la persona. Y marcó como "no pertenece" las liquidaciones de un inmueble de un accionista que la empresa paga: el contrato no decía que eso es gasto de la empresa.
2. **Convención que vivía en la cabeza de la persona (14 movimientos):** para sueldos, retiros de accionistas y expensas sin número, el "N° de comprobante" es el período (`MM-AAAA`). El agente puso el número del recibo del banco. Nunca estuvo escrito en el contrato.
3. **Una factura pagada con un débito que es la suma de dos facturas del mismo emisor** (1 movimiento): el candidato por importe exacto no existía.
4. **Expensas por unidad funcional** (1 movimiento): el lector solo registró el total del edificio, no el importe de cada unidad.
5. **Un cobro parcial** de una venta (el documento fiscal es por un monto mayor que el cobro): solo se puede vincular por el nombre del emisor, y el candidato por nombre no existía.
6. **Un falso positivo de la regla "importe único + tabla":** vinculó un documento que no tenía relación (coincidencia de importe) y lo dio por hecho con confianza alta. La regla debía exigir que el emisor coincida además del importe.
7. **Un comprobante de pago con importe exacto que el lector marcó como "no pertenece"** (embargo a un empleado) y **una factura cuyo importe no coincide** con el débito (1 movimiento cada uno): el primero se resuelve al relajar la exclusión por "no pertenece"; el segundo no, y se deja como límite (no se vincula sin importe exacto).
8. **Dos pagos de gas de igual importe** vinculados a dos facturas de un período anterior con ese mismo importe: ambiguo, y el cierre manual las considera no relacionadas. Queda anotado, no se intenta resolver.

**Decisión:** cada punto se ataca en v2 con un cambio concreto, en el código o en el contrato, y se mide de nuevo. Los importes que el documento no imprime se calculan **en código** (no se le pide al modelo que reste). Las convenciones de la persona pasan al contrato escrito.

## D9 · Corrección de la evaluación: lo que ningún agente podía acertar (25/09)
Al revisar los errores, en 7 movimientos el cierre manual tiene un N° de comprobante pero **el documento que lo contiene no está en la carpeta** (se archivó en papel o se borró). Ninguna versión del agente puede acertarlos. Se pasaron a una categoría aparte ("no reconstruibles") y no cuentan ni a favor ni en contra: las métricas quedan sobre 90 movimientos evaluables, no 97. Se recalculó v1 con la evaluación nueva para que sea comparable con las siguientes.

## D10 · Corrida v2: atacar las fallas de v1 (25/09)
**Cambios**, cada uno atado a una falla medida de D8:
- *Código:* se calculan los importes que el documento no imprime (total unificado − total; cuota capital + fundación educacional); se buscan **sumas de dos facturas del mismo emisor**; los documentos "no pertenece" dejan de excluirse (pasan como candidatos marcados); se agregan candidatos por **nombre del emisor**; la regla "importe único + tabla" ahora exige que el emisor coincida además del importe.
- *Contrato del lector:* usar el "Comprobante adicional" en las liquidaciones de cooperativas; listar cada fila en resúmenes por persona/unidad; etiquetas fijas para total / total unificado / cuota capital / fundación; `pertenece=no` solo si es claramente de otra empresa.
- *Contexto privado nuevo:* "sí pertenecen aunque no lo parezcan" (servicios de inmuebles de accionistas que paga la empresa).
- *Contrato del conciliador:* la convención del período (`MM-AAAA`) para sueldos, retiros y expensas; señales de candidatos explicadas; regla de "no vincular sin importe exacto".

**Resultado v2:** comprobante exacto **54% → 91%** (82/90); documentos bien vinculados 42 → 55 de 68. Costo US$ 0,635 (la lectura completa se repite porque cambió el prompt del lector; el prompt más largo sumó unos 500 tokens por documento: +US$ 0,06).
**Lo que empeoró:** Detalle exacto 87% → 79%, y lo deducido por el modelo 4/7 → 1/8. Causa: al enviar más movimientos al modelo (82 en vez de 65), el modelo "corrigió" Detalles de la tabla que estaban bien (reescribió una dirección) y dejó vacío otro pese a tener la sugerencia.

## D11 · Corrida v3: guardas en código (25/09)
Idea guía: **una regla determinística no debe depender de que el modelo la obedezca.**
- *Guarda de tabla:* si el modelo dice que el Detalle viene de la tabla, se copia la sugerencia textual; si lo deja vacío teniendo sugerencia, se usa la sugerencia.
- *Convención del período pasada a código:* el modelo la cumplió 10 de 14 veces (sueldos sí; retiros de accionistas no). Si el Detalle es `Retiro - …` o `Personal - Haberes…`, el comprobante es `MM-AAAA`.
- *Contrato:* importe redondo sin CUIT ni nombre no alcanza para vincular; se prefiere el número del documento de origen sobre el del comprobante de pago; convenciones de categoría del cliente (impuestos nacionales, cargas sociales, retiros de efectivo).
- Como el prompt del lector no cambió, se reutilizó su lectura (costo de la corrida: US$ 0,069).

**Resultado v3:** comprobante 92% (83/90), Detalle 95% (36/38), documentos bien vinculados 58/68.
**Un error propio, encontrado al mirar los errores restantes:** la guarda del período **rompió** un caso que v2 tenía bien: una persona que cobra con factura propia. La convención no es "haberes → período" sino "haberes **sin factura con número propio** → período". Se me había pasado al generalizar a partir de casos.

## D12 · Corrida v4 y una advertencia sobre lo que se mide (25/09)
- Se corrige la regresión: el período no se aplica si hay una factura con número entre los documentos vinculados.
- El N° de comprobante final sale de los **documentos de origen vinculados**, no de lo que escribe el modelo (arregla un caso donde el modelo sumó el número del comprobante de pago).
- Los VEP mandan sobre la tabla: el concepto del banco es el mismo para todos los VEP (Ganancias, IVA, cargas sociales), así que la tabla no puede distinguirlos. (Ver abajo: neto cero.)

**Resultado v4:** comprobante **94% (85/90)**, Detalle 95% (36/38), documentos bien vinculados 58/68 y 5 vinculados de más (US$ 0,07 por corrida con la lectura en cache; US$ 0,64 el pipeline completo).

**Advertencia importante:** las reglas de v2, v3 y v4 se derivaron de las fallas **de este mismo mes** y se evalúan sobre este mismo mes. Es entrenar y probar con los mismos datos: la cifra de v4 es **optimista** y no dice cuánto generaliza. Lo honesto que se puede afirmar es que el sistema, con las convenciones de la persona escritas, reproduce el 94% de su cierre manual de agosto; para medir si generaliza hace falta correrlo sobre otro mes sin tocarlo. No se hizo (solo estaba disponible agosto). Ver "Qué falta" en el README.

**Lo que sigue fallando en v4** (5 comprobantes y 2 detalles sobre 90 y 38 evaluables) y por qué se deja así:
- *Expensas de un edificio* (comprobante): vinculó bien el documento (una imagen), pero dejó vacío el N° de comprobante. La convención del cliente es el período (`07-2026`) cuando las expensas no traen número; en código solo se aplicó a retiros y haberes, no a expensas. Es una regla que faltó, no un límite del modelo.
- *Una factura de teléfono cuyo importe no coincide* con el débito: no se vincula sin importe exacto; límite deliberado.
- *Un cobro parcial de una venta*: la factura es por un monto mayor que el cobro; el agente vincula los dos comprobantes de pago con importe exacto y la persona vincula la factura, cuyo importe no coincide.
- *Una guía de tránsito de hacienda con el mismo importe que un débito*: el agente la vincula, el cierre manual no. Puede ser un error del cierre manual, no del agente; lo tiene que decidir la persona.
- *Dos VEP*: la regla "el impuesto del VEP manda sobre la tabla" arregló uno (Ganancias) y **rompió otro** (cargas sociales, que la tabla tenía bien); el neto es cero (2 errores de Detalle en v3, 2 en v4, en movimientos distintos). Con lo que el lector extrae, el modelo no distingue de forma confiable qué impuesto es cada VEP. En el segundo VEP además vinculó una retención con el mismo importe. Queda como caso de revisión humana.
- *Dos pagos de gas de igual importe con dos facturas de un período anterior*: el cierre manual las considera no relacionadas; el agente las vincula por importe exacto. Son ambiguas sin mirar el período; se cuentan como "documentos de más".
Ninguno fue "arreglado a mano": todos aparecen en la hoja "Para revisar" o con confianza baja o media.

## D13 · ¿Un modelo más grande ayuda? (25/09)
Misma versión v4, mismo mes, mismo cierre manual como vara; Sonnet 5 sin razonamiento extendido (se apagó porque Sonnet 5 razona por defecto y no sería una comparación en igualdad).

| Configuración | Comprobante | Detalle | Docs bien vinculados | Vinculados de más | US$ pipeline completo |
|---|---|---|---|---|---|
| Haiku 4.5 en las dos etapas | 94% (85/90) | 95% (36/38) | 58/68 | 5 | 0,64 |
| Haiku lector + Sonnet 5 conciliador | 91% (82/90) | 97% (37/38) | 55/68 | 6 | 0,76 |
| Sonnet 5 en las dos etapas | 96% (86/90) | 95% (36/38) | 58/68 | 3 | 1,62 |

Lectura: Sonnet como conciliador **no mejora** (peor en comprobantes) y cuesta más; Sonnet en las dos etapas suma **un** movimiento acertado (de 90) y dos documentos menos "de más", a **2,5 veces** el costo. Con un solo mes y n=90, esa diferencia no es distinguible del ruido (D15 lo confirmó: repetir la misma corrida da ±1 movimiento). **Decisión:** Haiku 4.5 en las dos etapas, según el criterio del curso (el más chico que hace bien la tarea). Se reabre si el problema pasa a ser el lector (imágenes), que es donde las dos configuraciones difieren.

## D14 · Publicar corridas sin publicar clientes (25/09)
La consigna pide corridas "tal como salieron", pero salieron con datos reales. Solución (`evaluacion/publicar_corrida.py`): las corridas originales quedan en la máquina y en `corridas/` se publica una versión **anonimizada**: nombres de personas y empresas, CUIT, cuentas, direcciones y saldos se reemplazan por alias estables (el mismo nombre → el mismo alias en todas las corridas, así se puede seguir un caso de una corrida a otra). Se conservan importes, fechas, números de comprobante y toda la lógica de decisión. Un verificador aborta la publicación si algún nombre real queda en un archivo publicado (falló dos veces con palabras comunes como "sociedades" y "vinculado", que no son nombres, y se ajustó el vocabulario permitido). No se publican los PDF ni las imágenes: la entrada de cada corrida es el extracto anonimizado más lo que el lector extrajo de cada documento (`lecturas_documentos.json`).
**Desvío respecto de la consigna, dicho con todas las letras:** lo publicado no es literalmente "tal como salió"; es lo que salió, con los datos personales sustituidos.

## D15 · El mismo código, la misma entrada, otro resultado (25/09)
Antes de cerrar se repitió v4 con el código final (US$ 0,07, con la lectura en cache) y se comparó fila por fila con la v4 original.
- **26 de 143 filas cambiaron.** Casi todas son de redacción del Detalle (el identificador de una dirección con o sin el número de suministro, `Personal - Haberes` con o sin un sufijo), pero también cambió el vínculo de 6 movimientos, todos ya ambiguos: un echeq con el mismo importe que un retiro, un documento de 'venta' sin importe claro, dos comprobantes de pago para un cobro, un VEP con una retención de igual importe y dos sueldos de exactamente el mismo importe.
- **Métricas de la repetición:** comprobante 93% (84/90) frente a 94% (85/90); Detalle 92% (35/38) frente a 95% (36/38). Es decir, **±1 movimiento entre dos corridas idénticas**.
- **Consecuencia para lo que se dijo antes:** la diferencia de 1 movimiento entre Haiku y Sonnet (D13), y la de un punto entre v3 y v4, **están dentro del ruido de la corrida**. Lo que no está dentro del ruido son los saltos grandes: de v1 a v2 (54% → 91%) y el costo (2,5×).
- Por qué pasa: no se fijó la temperatura (Sonnet 5 no admite el parámetro) y el modelo decide con criterio los casos ambiguos. Para una corrida en producción esto es una razón más para que las filas ambiguas las revise una persona.
- No se probó `temperature=0` en Haiku para reducir la variación. Queda como paso siguiente, junto con repetir cada configuración 3 veces para tener un intervalo en vez de un punto.


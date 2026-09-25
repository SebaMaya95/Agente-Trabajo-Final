# v0 — La instrucción original de Cowork (anonimizada)

> Es el punto de partida del proyecto: una única instrucción larga, corrida en Cowork, que hacía todo el cierre mensual. Se conserva como estaba, salvo por la **anonimización** de nombres, CUIT, familias de accionistas, edificios y rutas (reemplazados por marcadores). El texto es de la persona, no del agente. Ver `DECISIONES.md` (D1) para qué se conservó y qué se descartó al pasar a este repositorio.

---

Ejecutá el cierre mensual bancario para Empresa A SA.

## Objetivo
Finalizar el cierre del mes anterior: actualizar la Tabla de Referencias, procesar los movimientos restantes (del último sábado al cierre del mes), y generar el reporte final.

## Carpeta de trabajo
`C:\...\Empresa A SA\Banco`

## Contexto general
- Esta tarea corre el **día 2 de cada mes** a las 10:00 AM.
- La carpeta que se cierra es la del **mes anterior** con formato AAAAMM (ej: si hoy es 02/07/2026 → carpeta `202606`).
- El usuario descargó antes de las 10:00 el Excel mensual completo del banco y lo guardó en esa carpeta.
- Ese Excel es **acumulativo**: contiene TODOS los movimientos del mes anterior, del día 1 al último día.
- Durante el mes, la tarea semanal fue incorporando movimientos cada sábado al `AAAAMM.xlsx`. Esta tarea agrega los días restantes (del último sábado al fin del mes) y cierra el expediente.

---

## ETAPA A — Actualizar Tabla de Referencias (SIEMPRE PRIMERO)

Antes de procesar nada, actualizar la Tabla de Referencias con los Detalles que el usuario validó a lo largo del mes.

### Paso A1 — Leer el AAAAMM.xlsx del mes que se va a cerrar
- Calcular la carpeta del mes anterior: mes actual - 1 (ej: si hoy es 02/07/2026 → carpeta `202606`).
- Abrir `202606\202606.xlsx`.
- Si no existe todavía (no hubo ningún sábado procesado), saltear Etapa A e ir directamente a Etapa B desde cero.

### Paso A2 — Incorporar Detalles nuevos a la Tabla de Referencias
- Abrir `Banco\Tabla de Referencias.xlsx`.
- Para cada movimiento en `AAAAMM.xlsx` que tenga `DETALLE` completado (no en blanco): verificar si ya existe en la Tabla una fila con esa combinación de Concepto Banco + Dato Clave Comprobante.
  - Si ya existe → no modificar.
  - Si NO existe → agregar fila nueva con: Concepto Banco, Dato Clave Comprobante, Tipo Dato Clave (deducir), Detalle.
- NUNCA eliminar ni modificar filas existentes.
- Guardar `Tabla de Referencias.xlsx`.
- Esta sincronización solo debe ocurrir en esta corrida programada (la primera del mes siguiente). No repetir la Etapa A ni volver a escribir en la Tabla de Referencias para un mes ya cerrado fuera de esta corrida, aunque se hagan correcciones posteriores al AAAAMM.xlsx de ese mes en otra conversación.

---

## ETAPA B — Cerrar el mes anterior

### Paso B1 — Identificar carpeta del mes anterior
- Calcular: mes actual - 1 (ej: si hoy es 02/07/2026 → carpeta `202606`).

### Paso B2 — Leer el Excel mensual completo del banco
- Buscar el archivo Excel (.xlsx o .xls) en la carpeta que NO sea el `AAAAMM.xlsx`. Es el extracto mensual completo.
- Localizar la sección "Últimos Movimientos" y extraer todos los movimientos del mes (ignorar vacías, filas de saldo y filas con '###########').

### Paso B3 — Identificar movimientos restantes
- Comparar todos los movimientos del Excel del banco con los que ya están en `AAAAMM.xlsx` (por fecha + concepto + importe). Al comparar fechas, tener en cuenta que algunas pueden estar almacenadas como serial numérico de Excel — convertirlas antes de comparar.
- Los que NO están en `AAAAMM.xlsx` son los días finales del mes (del último sábado al cierre del mes).
- Si no hay movimientos nuevos: verificar igualmente si hay celdas de fecha en formato numérico (serial) en la columna B y corregirlas a `DD/MM/YYYY` antes de continuar.

### Paso B4 — Agregar movimientos restantes a AAAAMM.xlsx
- Agregar los movimientos nuevos continuando la numeración correlativa del mes.
- Al escribir la columna B (Fecha): convertir siempre el valor a datetime y aplicar el formato de celda `DD/MM/YYYY` (fecha corta). Nunca dejar el serial numérico de Excel.

### Paso B5 — Leer comprobantes nuevos
- Para cada archivo PDF o imagen en la carpeta que aún no tenga número de movimiento en su nombre: extraer número de comprobante, importe, emisor y dato identificador.
- El número de comprobante a registrar es el que figura explícitamente en el documento (ej. "NÚMERO DE COMPROBANTE", "Nro. VEP", "Comp. Nro", "CLASE A Nº", "Comprobante adicional"), no un código de pago ni un dato de cuenta/servicio. Si el documento tiene un apartado explícito con ese rótulo, usar ese valor.
- **Distinción clave — "documento de origen" vs. "comprobante de pago"**: un **documento de origen** es la factura, VEP, resumen de expensas u otro comprobante que **justifica el gasto** (qué se compró/pagó y por qué). Un **comprobante de pago/transferencia** (recibos del banco o de Pago Mis Cuentas: "Comprobante de Transferencia", "Comprobante de pago manual", "Comprobante de débito automático", etc., ver Paso B8.5) solo certifica que el banco ejecutó el pago, pero no explica el gasto en sí. Un movimiento puede tener comprobante de pago sin tener documento de origen (por ejemplo, si nunca se consiguió la factura real). Esta distinción determina el color de la fila (ver Paso B10: GRIS/BLANCO/AMARILLO/NARANJA) — tener solo el comprobante de pago, sin el documento de origen, deja la fila en AMARILLO, no en blanco. Los pagos de impuestos propios de la empresa (AFIP, ARBA, ARCA, etc., aunque se paguen vía "Pago De Servicios" desde la tarjeta/cuenta) tienen su propio VEP/comprobante como documento de origen y se evalúan con esta misma lógica (BLANCO/AMARILLO/NARANJA) — NO son GRIS (ver Paso B10).
- **Particularidad — UPC (Cooperativa Eléctrica, suministros eléctricos)**: cada PDF de liquidación de la cooperativa se vincula a **DOS movimientos bancarios distintos**, no a uno solo:
  1. El primer movimiento es el importe que figura como **"TOTAL"** dentro del recuadro **"DETALLE DE CONCEPTOS"** (la suma de Cargo Fijo + Cargo Variable + Impuestos, etc., de esa liquidación).
  2. El segundo movimiento es el importe de **"TOTAL UNIFICADO"** (que aparece más abajo, junto a la fila "Totales") **menos** el importe (1). Esa diferencia corresponde a la cuota de un plan de pagos en curso (conceptos "Cuota Capital E.E." + "Fundación Educacional" que aparecen impresos en el PDF, cuya suma debe coincidir con la diferencia calculada).
  - Buscar AMBOS importes exactos entre los movimientos bancarios (pueden estar en fechas distintas dentro del mismo mes, no necesariamente el mismo día). Es normal que el segundo movimiento (la diferencia) no aparezca todavía en el extracto del mes — en ese caso, vincular solo el primer movimiento y dejar aclarado en el reporte que falta el de la cuota, sin inventarlo ni forzarlo.
  - El número de comprobante a usar para ambos movimientos es el mismo: el que figura como "Comprobante adicional" en el PDF (formato ej. `A-0014-00122380` o `B-0014-02317691`). El PDF de la liquidación es el **documento de origen** de ambos movimientos (aunque sea un único archivo compartido), así que ambos quedan en BLANCO (sin color) una vez cargado el N° de Comprobante, no en amarillo ni naranja.
  - Cada suministro tiene su propio N° de Suministro y, en los pagos con concepto bancario "Coop Upc Neco: [cuenta]", su propia cuenta de 20 dígitos — no mezclar importes entre distintos suministros aunque compartan el mismo Socio.
  - Para el Detalle: si el PDF muestra una dirección física en "DATOS DEL SUMINISTRO" (ej. "Calle Falsa 123"), preferirla como identificador (`Servicios - Electricidad - Calle Falsa 123`), consistente con la Tabla de Referencias. Si no hay dirección o el comprobante es de compra con tarjeta (concepto "Compra Con Tarjeta De Debito - Upc Necochea"), usar `Servicios - Electricidad - UPC` (o agregar el N° de Suministro entre paréntesis si hace falta distinguirlo y no hay match exacto en la Tabla, marcando la celda de CELESTE en ese caso — la celda de Detalle en celeste es independiente del color de fila GRIS/BLANCO/AMARILLO/NARANJA).
- **Particularidad — Expensas del Edificio A**: el edificio suele reportarse con uno o dos archivos JPG (no PDF), del tipo "Resumen Egresos Consorcio" (gastos generales del edificio: proveedor/servicio/monto) y/o "Resumen Expensas Ordinarias" (tabla propietario/departamento/expensas/%). El movimiento bancario relevante es la transferencia al edificio. Para identificar la unidad funcional: en la tabla "Expensas Ordinarias" (columnas Propietarios/Inquilino, Departamento, Expensas Ordinarias, %), buscar la fila donde el propietario mencione "[apellido de la familia]" (u variantes/errores de tipeo) — la columna "Departamento" de esa fila es la unidad a usar en el Detalle: `Expensas - Edificio A - [unidad]` (ej. `Expensas - Edificio A - 5A`). No hay número de comprobante tradicional en estos archivos: usar el período como N° Comprobante en formato `MM-AAAA` (ej. `07-2026`). El/los JPG son el documento de origen de este movimiento, así que la fila queda BLANCA (sin color) aunque no tenga N° Comprobante tradicional — solo queda naranja si no se encuentra ningún archivo de expensas para ese movimiento. Renombrar el/los JPG con el número de movimiento como cualquier comprobante (Paso B8).
- **Particularidad — Expensas Consorcio B (edificio B, Administración C)**: suele llegar un único PDF multi-página con el detalle "EXPENSAS A ABONAR [MES] [AÑO]" que cubre VARIOS movimientos bancarios a la vez (la transferencia con concepto "Transferencia Inmediata - A Consorcio De Copropieta / - Exp / [CUIT]" puede repetirse 2 o 3 veces el mismo día, una por cada unidad funcional). Una de las hojas del PDF tiene la tabla con columnas `UF | Dpto | %A %B %C | Propietario | Expensas | Saldo anterior | Interes | Otros | Total | Deposito`. Las unidades funcionales (UF) que corresponden a la familia de los accionistas de la Empresa A son la **23** y **24** (cocheras, propietaria "[Propietaria X]") y la **41** (departamento, propietaria "[Propietaria X]"; en la tabla figura como Dpto "1º23", "1º24" y "3B/Ba" respectivamente, pero se identifican como UF 23, 24 y 41). Cada movimiento bancario de este grupo se distingue de los demás por los **centavos del importe de la transferencia**, que coinciden exactamente con el número de UF (ej. una transferencia de $205.910,41 corresponde a la UF 41; $8.108,23 a la UF 23; $8.108,24 a la UF 24 — el "Total" de esa fila de la tabla debe coincidir con el importe completo, no solo los centavos). Detalle por movimiento: `Expensas - Consorcio B - Depto 41`, `Expensas - Consorcio B - Cochera 23`, `Expensas - Consorcio B - Cochera 24`. Si aparece un recibo de pago individual con N° de comprobante real para alguno de estos movimientos (ver Paso B8.5), usarlo para completar `N° Comprobante`; si no aparece ninguno, dejar la celda en blanco (no inventar un número). El PDF de expensas es el documento de origen de los tres movimientos, así que la fila queda BLANCA (sin color) aunque `N° Comprobante` esté vacío. Renombrar el único PDF listando TODOS los movimientos que cubre, separados por coma y con "y" antes del último: `[mov1], [mov2] y [mov3] - Consorcio B - Expensas [MM-AAAA].pdf`.

### Paso B6 — Cruzar comprobantes con movimientos restantes
- Vincular cada comprobante nuevo a un movimiento por importe exacto.
- Si hay varios movimientos con el mismo importe: usar Concepto del banco + contenido del comprobante para desambiguar.
- Registrar en `N° Comprobante` **solo el número de comprobante** (ej. `FC 0012-625134`, `VEP 1643231563`, `A-0014-00122381`). No agregar el número de movimiento, el Detalle, ni el nombre de archivo dentro de esta celda — esa información ya está en las columnas A y J.
- Ver particularidades de UPC, Expensas del Edificio A y Consorcio B en el Paso B5 para los casos con más de un movimiento por comprobante o sin N° Comprobante tradicional.

### Paso B7 — Completar la columna DETALLE de los movimientos restantes
- Usar la `Tabla de Referencias.xlsx` (ya actualizada en Etapa A).
  - Coincidencia en tabla → completar Detalle. Celda sin color.
  - Sin coincidencia → deducir con estructura `Categoría - Subcategoría - Identificador`. Pintar celda de **CELESTE**.
  - Sin deducción posible → dejar en blanco.
- Para identificar el "Identificador" de servicios (luz, gas, etc.) preferir la dirección física del suministro (si el comprobante la muestra, ej. en el apartado "DATOS DEL SUMINISTRO") en vez de un número de cuenta o código interno.
- NUNCA inventar categoría sin fundamento. NUNCA modificar la Tabla de Referencias en este paso.
- El color CELESTE de esta celda (columna J, Detalle) es independiente del color de fila GRIS/BLANCO/AMARILLO/NARANJA del Paso B10 — pueden combinarse (ej. una fila AMARILLA puede tener además su celda de Detalle en CELESTE).

### Paso B7.5 — Verificar TODOS los Detalles ya cargados contra la Tabla de Referencias (no solo los nuevos)
Además de completar el Detalle de los movimientos nuevos (Paso B7), en cada corrida conviene re-chequear los movimientos que ya tenían Detalle cargado de antes (de meses/corridas previas), porque la Tabla de Referencias pudo haberse actualizado después:
- Para cada movimiento no-GRIS de `AAAAMM.xlsx` cuyo Concepto Banco tenga una coincidencia EXACTA en `Tabla de Referencias.xlsx`: si el Detalle ya cargado en la fila NO coincide con el de la Tabla, corregirlo para que coincida (señalar el cambio en el reporte). Si la celda estaba en CELESTE (deducido sin match exacto) y ahora SÍ hay match exacto en la Tabla, limpiar el color CELESTE de esa celda — ya no hace falta validación manual.
- Esto es una limpieza de consistencia, no reemplaza la Etapa A (que sigue siendo la única que agrega filas nuevas a la Tabla de Referencias).

### Paso B8 — Renombrar comprobantes vinculados nuevos
- Formato: `[N° movimiento] - [Detalle o Concepto abreviado] - [N° comprobante].[extensión]`
- Casos con más de un movimiento en el mismo archivo (ej. Consorcio B, o UPC con sus dos movimientos según el Paso B5): `[mov1] y [mov2] - [Detalle] - [N° comprobante].[extensión]` (movimientos en orden ascendente). Si el archivo ya existía con el nombre de un solo movimiento y hay que renombrarlo a la versión de dos movimientos, y el archivo no se puede borrar/renombrar por una restricción de la carpeta, crear una copia con el nombre correcto y señalar en el reporte que el archivo viejo (nombre de un solo movimiento) quedó duplicado y se puede borrar manualmente.

### Paso B8.5 — Vincular el comprobante de pago/transferencia bancaria (recibo del banco) junto a su documento
Además del documento que justifica el gasto (factura, VEP, etc.), suele aparecer también el **comprobante de pago o transferencia** que generó el propio banco/Pago Mis Cuentas al efectivizar ese pago (formatos habituales: "Comprobante de Transferencia a Otro Banco", "Comprobante de Transferencia", "Comprobante de pago manual", "Comprobante de débito automático", "Comprobante de pago" con Beneficiario/CUIT). Estos recibos suelen traer el número de factura vinculado en un campo tipo "Información adicional" (útil para identificar a qué movimiento corresponden) y su propio número de comprobante interno del banco (distinto del número de factura). **Importante: este recibo NUNCA cuenta como "documento de origen" (ver Paso B5) — es solo la prueba de que el banco ejecutó el pago, no explica el gasto.** Esto aplica también a los VEP de AFIP/ARBA/ARCA: el VEP en sí (o la constancia de pago del organismo) es el documento de origen; si además aparece un comprobante de transferencia/débito del banco para ese mismo pago, ese comprobante bancario se vincula con " - Comprobante" como cualquier otro caso.

- **Si ya existe un documento de origen para ese movimiento** (factura, VEP, etc., ya nombrado según el Paso B8): renombrar el recibo del banco con el **mismo nombre base que el documento**, agregando **" - Comprobante"** antes de la extensión. Así, ordenados alfabéticamente, cada documento queda al lado de su comprobante de pago (misma lógica que echeq/" - echeq"). El movimiento queda con documento de origen real y comprobante de pago, así que la fila queda BLANCA (sin color), salvo que sea GRIS por su Concepto.
- **Si NO existe un documento de origen separado para ese movimiento** (el recibo del banco es el único respaldo, ej. transferencias a haberes de empleados, retiros de accionistas, débitos automáticos sin factura propia): el recibo pasa a ser el único archivo del movimiento. Renombrarlo directamente con el formato completo del Paso B8 **más el agregado final " - Comprobante"**: `[N° movimiento] - [Detalle] - [N° comprobante] - Comprobante.[extensión]`. **Este movimiento queda (o pasa a estar) pintado AMARILLO, porque tiene comprobante de pago pero no documento de origen** (ver regla de color en el Paso B10 — la única excepción es si el Concepto del movimiento entra en los patrones GRIS).
- **Casos con más de un movimiento en el mismo documento base** (Consorcio B, UPC): si aparece un recibo de pago individual para cada movimiento (con su propio N° de comprobante), nombrar cada recibo por separado con el número de ESE movimiento puntual (no los dos/tres juntos), aunque el documento original sea compartido: `[mov] - [Detalle] - [N° comprobante] - Comprobante.[extensión]`. Si ese N° de comprobante individual es real y confiable, también se puede usar para completar `N° Comprobante` en `AAAAMM.xlsx` si antes estaba en blanco por no tener uno propio. Estos movimientos SÍ tienen documento de origen (el PDF compartido), así que quedan en BLANCO (sin color), no en amarillo.
- Si aparecen dos recibos de pago prácticamente idénticos (mismo importe, misma cuenta, mismo número de control/transacción, con segundos de diferencia en el timestamp) para dos movimientos distintos con igual importe: no se puede garantizar cuál corresponde a cuál. Vincular uno a cada movimiento de todas formas (mejor esfuerzo) pero agregar "(verificar)" al nombre del que quede dudoso, y señalarlo en el reporte.
- No mover ni duplicar el documento original: solo el recibo de pago se renombra/vincula.

### Paso B9 — Mover comprobantes sin movimiento
- A la subcarpeta `Sin movimientos\`. Si ya existe, usarla. Si no existe, crearla.
- Formato: `x - [emisor o descripción breve] - [N° comprobante].[extensión]`

### Paso B10 — Pintar filas según su estado (4 colores)
En `AAAAMM.xlsx`, aplicar los siguientes colores de fondo a la fila completa (columnas A a K). Evaluar en este orden: GRIS primero (siempre gana, solo para los patrones bancarios automáticos listados abajo); si no es gris, evaluar documento de origen y comprobante de pago para elegir entre BLANCO / AMARILLO / NARANJA.

- **GRIS**: reservado ÚNICAMENTE para comisiones e impuestos que el **banco aplica de forma directa y automática sobre la cuenta**, sin que exista (ni pueda existir) un comprobante propio de pago — son cargos que el banco genera internamente, no un pago que la empresa haya ordenado. Patrones a detectar (case-insensitive, en Concepto):
  - `Impuesto Ley 25.413` (débito o crédito 0,6%)
  - `Iva 21%` / `Iva Percepcion` / cualquier variante de IVA bancario
  - `Comision` o `Comisión` (transferencias, compensación de cheques, servicio cuenta dólares, etc.)
  - `Imp Al Debito Extr Efvo` y variantes similares de impuestos sobre movimientos bancarios que el banco cobra directamente
  - Las filas GRIS nunca pasan a blanco/amarillo/naranja. No tienen (ni necesitan) documento de origen ni comprobante de pago propio, porque el banco no emite uno — es un cargo automático de extracto.
  - **Importante — lo que NO es GRIS**: los pagos de impuestos propios de la empresa a organismos recaudadores (AFIP, ARBA, ARCA, Ingresos Brutos, Ganancias, IVA, etc.), aunque se paguen desde "Pago De Servicios" con la tarjeta/cuenta de la empresa, **se tratan como un movimiento más**: tienen su propio VEP o constancia de pago como documento de origen (y, si corresponde, su comprobante de transferencia/débito del banco — Paso B8.5), y se evalúan por la regla normal BLANCO/AMARILLO/NARANJA según tengan o no ese documento y comprobante. No van en GRIS solo por tratarse de un impuesto: el criterio es si el cargo lo genera el banco motu proprio (GRIS) o si es un pago que la empresa ordenó a un tercero, aunque ese tercero sea un organismo público (regla normal).
- **BLANCO (sin color)**: la fila tiene tanto **documento de origen** (factura, VEP, resumen de expensas, etc. — ver distinción del Paso B5) como **N° de Comprobante** cargado. Es el estado normal/completo.
- **AMARILLO** (`FFFF00`): falta el **documento de origen**, pero la fila SÍ tiene **N° de Comprobante** cargado (por ejemplo, a partir de un recibo de pago/transferencia del Paso B8.5 que quedó como único respaldo — haberes, retiros de accionistas, débitos automáticos sin factura propia, etc.).
- **NARANJA** (`FFA500`): falta el **documento de origen** Y la fila tampoco tiene **N° de Comprobante** cargado (no hay nada).
- **Excepciones que quedan en BLANCO aunque a primera vista parezca que falta algo**: los casos de UPC, Expensas del Edificio A y Consorcio B (Paso B5), porque el documento de origen (el PDF/JPG de la liquidación/expensas) sí existe, aunque el N° de Comprobante sea atípico (período `MM-AAAA`, en blanco, o compartido entre varios movimientos).
- En la práctica: para cada movimiento, primero chequear si el Concepto bancario coincide con uno de los patrones GRIS (cargo automático del banco, sin comprobante propio posible). Si no lo es (incluidos los pagos de AFIP/ARBA/ARCA, que van por la regla normal), revisar (a) ¿existe en la carpeta un archivo con su número de movimiento que sea el documento de origen (no un archivo terminado en "- Comprobante" o "- echeq", que son solo comprobantes de pago)? y (b) ¿tiene algo cargado en `N° Comprobante`? Con eso, aplicar BLANCO (ambos sí), AMARILLO (solo comprobante) o NARANJA (ninguno).

### Paso B11 — Guardar el Excel
- Guardar `AAAAMM.xlsx` con todos los cambios.

### Paso B12 — Generar Excel de reporte mensual
- Crear el archivo `AAAAMM_Reporte.xlsx` en la carpeta del mes (ej: `202605_Reporte.xlsx`), con 3 hojas. NO incluir información relacionada a echeqs (Pasos B12.5, B12.6, B12.7) en este reporte — eso se maneja aparte, en el chat (Paso B13), no en el Excel.
  Usar texto negro en todas las celdas de datos; texto blanco solo en encabezados con fondo oscuro. Pintar las filas de datos de las hojas 1 y 3 con el mismo color (gris/blanco/amarillo/naranja) que tienen en `AAAAMM.xlsx` cuando corresponda mostrar ese estado.
- **Hoja 1 — "Resumen"**: panorama general del cierre:
  - Total de movimientos del mes, y rango de fechas de los movimientos nuevos incorporados en esta corrida.
  - Desglose de colores: cantidad en GRIS, BLANCO, AMARILLO y NARANJA (con su definición corta al lado, y su color de fondo aplicado a la celda).
  - Calidad del Detalle (solo movimientos no-GRIS): cantidad con match exacto en Tabla de Referencias, cantidad en CELESTE (deducido, a validar), cantidad en blanco (sin Detalle).
  - Cualquier otra novedad relevante del cierre (comprobantes movidos a `Sin movimientos`, entradas nuevas a la Tabla de Referencias, casos "(verificar)" del Paso B8.5, correcciones de Detalle o celeste del Paso B7.5, etc.).
- **Hoja 2 — "Totales por categoría"**: tabla con columnas `Categoría | Total ($) | Movimientos`. Texto negro en datos, texto blanco en encabezados con fondo oscuro. Importes negativos en rojo. Agrupar por el primer elemento del Detalle (antes del primer guion), EXCEPTO las filas GRIS, que van todas juntas en una única categoría `Gris - Impuestos y comisiones bancarias` (no bajo el primer elemento de su Detalle, aunque lo tengan cargado). Los movimientos sin Detalle y sin ser GRIS van a `Sin categorizar / sin documento`. Los pagos de AFIP/ARBA/ARCA (no-GRIS) se agrupan normalmente por su Detalle (típicamente bajo `Personal` o `Impuesto`, según corresponda), no bajo el bucket gris. Ordenar de mayor a menor importe absoluto. Incluir fila de TOTAL al final con fórmulas `SUM`.
- **Hoja 3 — "Sin documento de origen"**: listado detallado de todas las filas AMARILLAS y NARANJAS (separadas en dos bloques, cada fila pintada de su color correspondiente), con columnas N° Mov., Fecha, Concepto (banco), Importe, Detalle, N° Comprobante. Esta hoja es la que más le importa al usuario para revisar: dejar claro en cada bloque si el movimiento tiene comprobante de pago cargado (amarillo) o no tiene absolutamente nada (naranja).

### Paso B12.5 — Cruzar comprobantes "Sin movimientos" del mes que se cierra con su carpeta Echeqs
*(Pasos B12.5, B12.6 y B12.7 — cruce de echeqs con comprobantes sueltos y circuito de tres facturas con una empresa vinculada: **fuera del alcance del trabajo final**, ver `DECISIONES.md`, D1. En el original ocupaban más de mil palabras: extraer importe y razón social de cada PDF de la subcarpeta `Echeqs\`, cruzar por importe exacto contra los comprobantes de `Sin movimientos\` del mes que se cierra y del mes anterior, renombrarlos con los sufijos " - echeq" y " - TRH", moverlos a una carpeta por razón social y reportar los circuitos completos o incompletos solo en el chat.)*

### Paso B13 — Reporte final del mes en chat
Mostrar resumen completo con:
- Mes cerrado y total de días procesados
- Total de movimientos del mes, desglosados en GRIS / BLANCO (documento + comprobante) / AMARILLO (solo comprobante, sin documento) / NARANJA (sin nada)
- Comprobantes en `Sin movimientos`
- Cruces realizados entre `Sin movimientos` y `Echeqs` *(fuera de alcance)*
- Casos de circuito con la empresa vinculada *(fuera de alcance)*
- Casos de UPC con dos movimientos por comprobante, Expensas del Edificio A y Consorcio B procesados (Paso B5)
- Recibos de pago/transferencia vinculados con " - Comprobante" (Paso B8.5)
- Correcciones de Detalle/celeste hechas contra la Tabla de Referencias (Paso B7.5)
- Detalles en celeste (requieren revisión del usuario)
- Detalles en blanco (sin coincidencia)
- Gastos agrupados por categoría (primer elemento del Detalle antes del primer guion; GRIS aparte, agrupado)

## Notas importantes
- La Etapa A siempre ocurre ANTES que la Etapa B, y solo se ejecuta una vez por mes (esta corrida). No volver a tocar la Tabla de Referencias de un mes ya cerrado hasta la primera corrida semanal del mes siguiente.
- El Excel del banco es acumulativo (todo el mes). Los movimientos nuevos son los que aún no están en `AAAAMM.xlsx`.
- El número de movimiento es el identificador permanente del mes; nunca renumerar.
- La subcarpeta `Sin movimientos` se crea solo si no existe; si ya existe, simplemente mover los archivos allí.
- La columna `N° Comprobante` lleva únicamente el número/código del comprobante, nunca una descripción compuesta (salvo las excepciones de período `MM-AAAA` para Expensas del Edificio A, y celda en blanco para Consorcio B, descriptas en el Paso B5).
- Si un comprobante tiene mala legibilidad, indicarlo en el reporte.
- Todo lo relacionado a echeqs y al circuito con la empresa vinculada se reporta solo en el chat, nunca en el Excel `AAAAMM_Reporte.xlsx` *(fuera de alcance del trabajo final)*.
- UPC es un caso particular de "un comprobante = dos movimientos bancarios": el importe (1) es el "TOTAL" de "DETALLE DE CONCEPTOS" y el importe (2) es "TOTAL UNIFICADO" menos (1) (cuota de un plan de pagos). Ambos movimientos comparten el mismo N° de Comprobante ("Comprobante adicional" del PDF) y, si se renombra el archivo, el nombre lleva los dos números de movimiento. Ambos quedan en BLANCO (tienen documento de origen compartido).
- Expensas del Edificio A y Consorcio B son casos particulares de "sin N° Comprobante tradicional pero con respaldo documental": quedan en BLANCO, no en naranja/amarillo.
- Recibos de pago/transferencia bancaria (Paso B8.5): se vinculan con el sufijo " - Comprobante" al mismo nombre base del documento que justifica el gasto. Si no hay documento de origen separado, el recibo del banco es el único archivo del movimiento y lleva el nombre completo del Paso B8 más " - Comprobante" — pero el movimiento queda en AMARILLO, porque tener el comprobante de pago no reemplaza al documento de origen.
- **Esquema de colores de fila (Paso B10)**: GRIS solo para cargos automáticos del banco (prioridad máxima, agrupado en `Gris - Impuestos y comisiones bancarias`); los pagos de AFIP/ARBA/ARCA NO son GRIS; BLANCO = documento de origen + comprobante; AMARILLO = solo comprobante de pago; NARANJA = nada.
- **Chequeo de Detalles contra la Tabla de Referencias (Paso B7.5)**: en cada corrida hay que re-validar también los Detalles ya cargados de corridas anteriores.

---

*Nota de la anonimización: en los pasos B12.5 a B13 se reemplazó el texto sobre echeqs y el circuito con la empresa vinculada por un resumen entre corchetes, porque quedó fuera del alcance del trabajo y contenía nombres y CUIT reales de terceros.*

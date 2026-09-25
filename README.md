# Conciliador bancario mensual (agente)

## Qué construí
Un agente que concilia el extracto bancario mensual de una empresa agropecuaria con la carpeta de comprobantes del mes (PDF y fotos): vincula cada movimiento con su comprobante, completa el N° de comprobante y una categoría (`Categoría - Subcategoría - Identificador`), marca el estado de cada fila con colores (gris, blanco, amarillo, naranja, celeste), copia los comprobantes con un nombre ordenado y genera un reporte de importe por categoría. Es para quien administra empresas de terceros y hoy lo hace a mano cada mes (~140 movimientos). El código resuelve lo determinístico (cargos automáticos del banco, tabla de Detalles ya validados, importes exactos) y el modelo (Haiku 4.5) lee los documentos y decide los casos ambiguos; una persona revisa lo marcado y firma.

Documentos del repositorio: [DECISIONES.md](DECISIONES.md) (historia y errores) · [ANALISIS_ECONOMICO.md](ANALISIS_ECONOMICO.md) · [GOBIERNO_Y_RIESGO.md](GOBIERNO_Y_RIESGO.md) · [prompts/](prompts/) (contrato vigente y versiones anteriores) · [corridas/](corridas/) (9 corridas; resumen en [corridas/RESUMEN.md](corridas/RESUMEN.md)).

## Cómo se lo pedí
Las instrucciones textuales que le di al agente que construyó el sistema (Claude Code), en orden. Los datos personales están reemplazados por `<...>`.

1. *"Te vas a manejar en `<carpeta del trabajo final>`. Analiza los archivos dentro."* (había dos: la consigna y el formato del README).
2. *"`<enlace al repositorio>` es el repo en git"*
3. *"Me dedico a la administración agropecuaria y consultoria de pymes. Tareas que me llevan tiempo: Todos los meses saco el extracto de movimientos del banco, y para cada fila le completo dos columnas nuevas (1) el número del comprobante que dio origen a ese movimiento y (2) una breve categorización de ese movimiento, a que corresponde. Todos los documentos se guardan en la carpeta del mes y ahí deberian de estar todos los que generen los movimientos bancarios y algunos extras que no corresponden a movimientos bancarios; Para otro trabajo tengo una pediatra que trabaja en distintas clinicas y en todas cobra un valor hora distinto. Las hora que trabaja las anota en su calendar de google. Podria crear un agente que extraiga del calendar los eventos, identifique la clinica, y según los valores previamentes cargados, hago un calculo de lo que deberia facturar a cada identidad."* (se eligió el primer caso; el segundo quedó como plan B).
4. Respuestas a mis preguntas de diseño: *"1. Excel 2. En todos los mencionados (PDF principalmente), tienen nombres random. Se podria agregar como tarea del agente que los renombre con el orden del movimiento seguido de ' - ...' el detalle de la categorización 3. Si 4. Si, a medida que pasan los meses, las categorias ya chequeadas para un 'Concepto' quedan determinadas. 5. 140 aprox 6. Si. Adjunto un extracto bancario y un cierre de mes. A su vez seria de utilidad un reporte sencillo especificando el importe destinado a cada categoria"*
5. *"Yo lo tenia en cowork pero con cowork no se tiene registro del gasto? para pasarle al profesor el repo de git conviene hacerlo en code? Que se gasta en cada caso? Te paso la descripción de la tarea?"* — seguido de la instrucción original de Cowork, ~5.000 palabras: [prompts/historial/v0_cowork_original_anonimizado.md](prompts/historial/v0_cowork_original_anonimizado.md).
6. *"1. Estoy de acuerdo. 2. Ok 3. Ok"* (aprobación del recorte de alcance, de la carpeta de datos y de la evaluación contra un mes cerrado) y *"Dejo lo de Agosto."* / *"Si tengo [cuenta de la API]"*.
7. *"1. El verde significa que tengo una copia en papel, pero eso no importa para el agente. Correcto, por eso bajo el naranja. 2. No, porque se va actualizando cada mes. 3. Hagamos todas las corridas en Agosto, mejorando el contrato y, en consecuencia, el resultado obtenido. Cuando consideres, anda subiendo todo a git para que quede registro. Lo central es cumplir con la consigna del tp, mientras que hacemos un uso eficiente de tokens junto con un modelo optimo."*

**El contrato que usa el agente en cada corrida** (las seis piezas: Rol, Contexto, Tarea, Restricciones, Formato, Ejemplos) está en [prompts/system_prompt_lector.md](prompts/system_prompt_lector.md) + [prompts/user_prompt_lector.md](prompts/user_prompt_lector.md) (etapa 1) y [prompts/system_prompt.md](prompts/system_prompt.md) + [prompts/user_prompt.md](prompts/user_prompt.md) (etapa 2). Las versiones v1, v2 y v3 están en `prompts/historial/`, y cada corrida guarda los prompts que usó en `prompts_usados/`.

## Qué funciona
**Cómo se usa** (sobre un mes con el extracto descargado y los comprobantes en una carpeta):
```
pip install -r requirements.txt
python evaluacion/preparar_datos.py 202608        # solo para probar contra un mes ya cerrado
python src/main.py --mes 202608 --etiqueta v5 --lector haiku --conciliador haiku
```
Necesita una clave de la API de Anthropic en `datos_privados/.env` (`ANTHROPIC_API_KEY=...`). Los datos reales no están en el repositorio: para reproducir hace falta una carpeta propia con la misma forma. Cada corrida genera en `datos_privados/<mes>/corridas/<fecha>_<etiqueta>/`: el Excel del mes con las columnas y colores, el reporte de 3 hojas (resumen, totales por categoría, filas para revisar), los comprobantes copiados con nombre nuevo, y el JSON con cada decisión, su confianza, su motivo y los tokens gastados.

**Qué se probó y anduvo** (mes de agosto: 143 movimientos, 128 documentos únicos, 60 de los cuales no corresponden a ningún movimiento). Evaluación contra el cierre manual, sobre 90 movimientos evaluables:

| Corrida | N° comprobante exacto | Detalle (celdas validadas) | Documentos bien vinculados | US$ por corrida completa |
|---|---|---|---|---|
| Solo código + tabla, sin modelo (línea base) | 22%* | 84% | 0 de 68 | 0 |
| v1 (Haiku) | 54% | 87% | 42 de 68 | 0,55 |
| v2 | 91% | 79% | 55 de 68 | 0,64 |
| v3 | 92% | 95% | 58 de 68 | 0,64 |
| v4 (Haiku) | 94% (85/90) | 95% (36/38) | 58 de 68 | 0,64 |
| v4 repetida (misma entrada, mismo código) | 93% | 92% | 55 de 68 | 0,64 |
| **v5 (final, Haiku; ejemplos del prompt sin datos reales)** | **94% (85/90)** | **92% (35/38)** | **57 de 68** | **0,63** |
| v4 con Sonnet 5 en las dos etapas | 96% | 95% | 58 de 68 | 1,62 |

\* La línea base "acierta" en las filas que no tienen comprobante; por eso se mira también cuántos documentos quedan bien vinculados.

- Los 46 cargos automáticos del banco se marcan solos y sin costo; 15 movimientos más se resuelven por regla, sin modelo.
- El pipeline cuesta unos **US$ 0,63 por mes por cliente** (US$ 7,6 por año), de los cuales el 89% es la lectura de documentos. Ver [ANALISIS_ECONOMICO.md](ANALISIS_ECONOMICO.md).
- Elegí **Haiku 4.5** en las dos etapas: Sonnet 5 como conciliador no mejora, y en las dos etapas suma un movimiento acertado de 90 al 2,5× del costo.
- Las corridas guardan tokens de entrada y salida, modelo, prompts y decisiones por movimiento, y permiten reconstruir qué pasó (ver [corridas/](corridas/)).

## Qué falta o qué falló
- **El modelo no es determinista.** Repetir v4 con la misma entrada dio 93% en comprobantes en vez de 94% y cambió 26 de 143 filas (casi todas de redacción). Las diferencias de un movimiento entre configuraciones (Haiku vs. Sonnet, v3 vs. v4) están dentro de ese ruido; los saltos grandes (v1 → v2) no. Falta repetir cada configuración varias veces y probar `temperature=0` en Haiku (D15).
- **La cifra está inflada y no dice cuánto generaliza.** Las reglas de v2 a v4 salieron de las fallas de agosto y se miden sobre agosto. Hay un solo mes; falta correrlo sobre otro mes sin tocar nada. Es lo primero que haría.
- **Errores que siguen en la versión final** (5 comprobantes y 3 detalles sobre 90 y 38 evaluables; D12 y D16): un N° de comprobante de expensas (el documento se vinculó bien pero faltó aplicar la convención del período), una factura de un importe distinto del débito, un cobro parcial, una guía de tránsito que el cierre manual no vincula, dos VEP de impuestos que el modelo confunde entre sí, una liquidación de granos del mes anterior vinculada a un cobro y un retiro de efectivo sin categoría. La regla "el VEP manda sobre la tabla" arregló uno y rompió otro. Detalle en `DECISIONES.md`, D12.
- **Un error propio en los prompts:** dos ejemplos usaban importes y un N° de comprobante reales de agosto; lo encontré revisando el diff antes de publicar, los reemplacé por valores inventados y repetí todo (v5): el resultado se sostuvo (D16).
- **Una regresión propia:** al pasar a código la convención "haberes → período", rompí el caso de una persona que cobra con factura propia. Lo detecté al revisar los errores de v3 y lo corregí en v4 (D11).
- **7 movimientos no se pueden evaluar:** el cierre manual tiene su comprobante pero ese documento no está en la carpeta. Se separaron como "no reconstruibles" (D9).
- **Los 13 documentos que son imágenes** dependen de la lectura por visión de Haiku, que es débil (extrajo solo el total de un resumen de expensas, no el importe por unidad). No se probó un modelo más grande solo para esas.
- **Lo que quedó fuera de alcance a propósito:** el cruce de echeqs con comprobantes sueltos, el circuito de facturas con una empresa vinculada y la ejecución programada semanal (D1).
- **Las corridas publicadas están anonimizadas**, no son literalmente "tal como salieron" (D14). Los PDF no se publican.
- **No probado:** documentos adversariales (un PDF con instrucciones escondidas), la API de lotes y el caché de prompts para bajar el costo, y un segundo cliente.
- El agente **no** actualiza la Tabla de Referencias: agregar filas es decisión de la persona.

## Qué aprendí
- **Casi todo el salto de calidad vino de escribir lo que estaba en la cabeza de la persona** (convenciones como "el N° de comprobante de un retiro es el período") y de darle candidatos ya filtrados al modelo, no de un modelo más grande: de v1 a v4 el acierto pasó de 54% a 94% con el mismo Haiku, y Sonnet sumó como mucho un punto, que además queda dentro del ruido entre corridas idénticas.
- **Lo que es una regla debe ser código, no un pedido al modelo.** El modelo cumplió una convención 10 de 14 veces y "corrigió" una tabla que estaba bien; las guardas en código lo resolvieron. A la vez, pasar una regla a código sin entender su excepción la vuelve más dañina.
- **Medir mal es peor que no medir.** La primera evaluación contaba como fallas casos que ningún agente podía acertar, y una métrica ("acierta si no hay comprobante") premiaba al sistema que no hacía nada. Hubo que mirar los errores uno por uno.
- **Entrenar y probar con el mismo mes da una cifra optimista.** Lo honesto es decirlo y no llamarlo generalización.
- Con datos de clientes reales, la **privacidad del repositorio se diseña al principio** (datos fuera del repo, anonimizador con verificación), no se arregla al final.

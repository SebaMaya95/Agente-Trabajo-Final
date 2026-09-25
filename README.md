# Conciliador bancario mensual (agente)

## Qué construí
Un agente que concilia el extracto bancario mensual de una empresa agropecuaria con la carpeta de comprobantes del mes (PDF y fotos): vincula cada movimiento con su comprobante, completa el N° de comprobante y una categoría (`Categoría - Subcategoría - Identificador`), marca el estado de cada fila con colores (gris, blanco, amarillo, naranja, celeste), copia los comprobantes con un nombre ordenado y genera un reporte de importe por categoría. Es para quien administra empresas de terceros y hoy lo hace a mano cada mes (~140 movimientos). El código resuelve lo determinístico (cargos automáticos del banco, tabla de Detalles ya validados, importes exactos) y el modelo (Haiku 4.5) lee los documentos y decide los casos ambiguos; una persona revisa lo marcado y firma.

**Dónde está la evidencia de cada requisito de la consigna:**

| Requisito | Dónde |
|---|---|
| 1 · Sistema completo (objetivo, contrato, herramienta real, salida estructurada, supervisión L0–L4) | Contrato: [prompts/](prompts/) · código: [src/](src/) · supervisión L0–L4: [GOBIERNO_Y_RIESGO.md](GOBIERNO_Y_RIESGO.md), punto 2 |
| 2 · Corre de verdad (tres corridas reales, reconstruibles) | [corridas/](corridas/): 15 corridas, cada una con su `LEEME.md` (fecha, entrada, salida); resumen en [corridas/RESUMEN.md](corridas/RESUMEN.md) |
| 3 · Formato estricto | Este README, `prompts/`, `corridas/` y `DECISIONES.md`, más dos documentos de apoyo (`ANALISIS_ECONOMICO.md` y `GOBIERNO_Y_RIESGO.md`) |
| 4 · Historia del proceso | [DECISIONES.md](DECISIONES.md) (D0 a D18: quién hizo qué, iteraciones, errores, cambios de alcance) y [prompts/historial/](prompts/historial/) |
| 5 · Análisis económico | [ANALISIS_ECONOMICO.md](ANALISIS_ECONOMICO.md) |
| 6 · Gobierno y riesgo | [GOBIERNO_Y_RIESGO.md](GOBIERNO_Y_RIESGO.md) |

## Cómo se lo pedí
Las instrucciones textuales que le di al agente que construyó el sistema (Claude Code), en orden. Los datos personales están reemplazados por `<...>`.

1. *"Te vas a manejar en `<carpeta del trabajo final>`. Analiza los archivos dentro."* (había dos: la consigna y el formato del README).
2. *"`<enlace al repositorio>` es el repo en git"*
3. *"Me dedico a la administración agropecuaria y consultoria de pymes. Tareas que me llevan tiempo: Todos los meses saco el extracto de movimientos del banco, y para cada fila le completo dos columnas nuevas (1) el número del comprobante que dio origen a ese movimiento y (2) una breve categorización de ese movimiento, a que corresponde. Todos los documentos se guardan en la carpeta del mes y ahí deberian de estar todos los que generen los movimientos bancarios y algunos extras que no corresponden a movimientos bancarios; Para otro trabajo tengo una pediatra que trabaja en distintas clinicas y en todas cobra un valor hora distinto. Las hora que trabaja las anota en su calendar de google. Podria crear un agente que extraiga del calendar los eventos, identifique la clinica, y según los valores previamentes cargados, hago un calculo de lo que deberia facturar a cada identidad."* (se eligió el primer caso; el segundo quedó como plan B).
4. Respuestas a mis preguntas de diseño: *"1. Excel 2. En todos los mencionados (PDF principalmente), tienen nombres random. Se podria agregar como tarea del agente que los renombre con el orden del movimiento seguido de ' - ...' el detalle de la categorización 3. Si 4. Si, a medida que pasan los meses, las categorias ya chequeadas para un 'Concepto' quedan determinadas. 5. 140 aprox 6. Si. Adjunto un extracto bancario y un cierre de mes. A su vez seria de utilidad un reporte sencillo especificando el importe destinado a cada categoria"*
5. *"Yo lo tenia en cowork pero con cowork no se tiene registro del gasto? para pasarle al profesor el repo de git conviene hacerlo en code? Que se gasta en cada caso? Te paso la descripción de la tarea?"* — seguido de la instrucción original de Cowork, ~5.000 palabras: [prompts/historial/v0_cowork_original_anonimizado.md](prompts/historial/v0_cowork_original_anonimizado.md).
6. *"1. Estoy de acuerdo. 2. Ok 3. Ok"* (aprobación del recorte de alcance, de la carpeta de datos y de la evaluación contra un mes cerrado) y *"Dejo lo de Agosto."* / *"Si tengo [cuenta de la API]"*.
7. *"1. El verde significa que tengo una copia en papel, pero eso no importa para el agente. Correcto, por eso bajo el naranja. 2. No, porque se va actualizando cada mes. 3. Hagamos todas las corridas en Agosto, mejorando el contrato y, en consecuencia, el resultado obtenido. Cuando consideres, anda subiendo todo a git para que quede registro. Lo central es cumplir con la consigna del tp, mientras que hacemos un uso eficiente de tokens junto con un modelo optimo."*

**El contrato que usa el agente en cada corrida** (las seis piezas: Rol, Contexto, Tarea, Restricciones, Formato, Ejemplos) está en [prompts/system_prompt_lector.md](prompts/system_prompt_lector.md) + [prompts/user_prompt_lector.md](prompts/user_prompt_lector.md) (etapa 1) y [prompts/system_prompt.md](prompts/system_prompt.md) + [prompts/user_prompt.md](prompts/user_prompt.md) (etapa 2). Las versiones v1 a v7 están en `prompts/historial/`, y cada corrida guarda los prompts que usó en `prompts_usados/`.

## Qué funciona
**Cómo se usa** (sobre un mes con el extracto descargado y los comprobantes en una carpeta):
```
pip install -r requirements.txt
python evaluacion/preparar_datos.py 202608        # solo para probar contra un mes ya cerrado
python src/main.py --mes 202608 --etiqueta v9 --lector haiku --conciliador haiku
```
Necesita una clave de la API de Anthropic en `datos_privados/.env` (`ANTHROPIC_API_KEY=...`). Los datos reales no están en el repositorio: para reproducir hace falta una carpeta propia con la misma forma. Cada corrida genera en `datos_privados/<mes>/corridas/<fecha>_<etiqueta>/`: el Excel del mes con las columnas y colores, el reporte de 3 hojas (resumen, totales por categoría, filas para revisar), los comprobantes copiados con nombre nuevo, y el JSON con cada decisión, su confianza, su motivo y los tokens gastados.

**Qué se probó y anduvo** (mes de agosto: 143 movimientos, 128 documentos únicos, 58 de los cuales no corresponden a ningún movimiento). Evaluación contra el cierre manual, que es la verdad, sobre 92 movimientos evaluables:

| Corrida | N° comprobante exacto | Detalle (celdas validadas) | Documentos bien vinculados (de 70) | US$ por corrida completa |
|---|---|---|---|---|
| Solo código + tabla, sin modelo (línea base) | 22%* | 80% | 0 | 0 |
| v1 (Haiku) | 53% | 82% | 44 | 0,55 |
| v5 (Haiku; ejemplos del prompt sin datos reales) | 95% | 88% | 59 | 0,63 |
| **v9 (final, Haiku)** | **98% (90/92)** | **100% (40/40)** | **67** | **0,69** |
| v9 repetida dos veces (misma entrada, mismo código) | 99% y 98% | 100% | 68 y 67 | 0,69 |
| v4 con Sonnet 5 en las dos etapas | 93% | 90% | 60 | 1,62 |

\* La línea base "acierta" en las filas que no tienen comprobante; por eso se mira también cuántos documentos quedan bien vinculados. Historia completa de las 15 corridas en [corridas/RESUMEN.md](corridas/RESUMEN.md).

- Los 46 cargos automáticos del banco se marcan solos y sin costo; 24 movimientos más se resuelven por regla, sin modelo.
- El pipeline cuesta unos **US$ 0,69 por mes por cliente** (US$ 8,3 por año), de los cuales el 88% es la lectura de documentos. Ver [ANALISIS_ECONOMICO.md](ANALISIS_ECONOMICO.md).
- Elegí **Haiku 4.5** en las dos etapas: Sonnet 5 no mejora el resultado y cuesta hasta 2,5 veces más.
- **De 97 movimientos que no son cargos del banco, 69 quedan marcados para revisar** (71%): el agente prefiere avisar a vincular mal.
- Las corridas guardan tokens de entrada y salida, modelo, prompts y decisiones por movimiento, y permiten reconstruir qué pasó (ver [corridas/](corridas/)).
- Cada diferencia con el cierre manual se investigó leyendo los documentos y se corrigió en el contrato o en el código (`DECISIONES.md`, D18).

## Qué falta o qué falló
- **La cifra no dice cuánto generaliza.** Las reglas de v2 a v9 salieron de las fallas de agosto y se miden sobre agosto: es entrenar y probar con el mismo mes. Algunas reglas son muy específicas de agosto. Hay un solo mes; falta correrlo sobre otro mes **sin tocar nada**. Es lo primero que haría.
- **El ahorro en horas no está medido.** El proceso manual lleva 6 a 8 horas por mes; el agente cuesta US$ 0,69 pero la revisión humana con el agente no se cronometró (quedan 69 filas marcadas de 97). Ver `ANALISIS_ECONOMICO.md`, 2.b.
- **El modelo no es determinista.** Repetir la misma corrida cambia el resultado en ±1 movimiento (v4: 95% y 93%; la final: 98%, 99% y 98%). Falta probar `temperature=0` en Haiku (D15, D18).
- **Errores que siguen en la versión final** (2 comprobantes de 92, 0 detalles de 40, 3 documentos de 70 sin vincular): una transferencia judicial que el modelo considera dudosa, una boleta con dos comprobantes de pago, y dos documentos de apoyo (un resumen de egresos de un edificio, que es una imagen, y un analítico de cuota de la obra social) que el lector clasifica mal. Detalle en `DECISIONES.md`, D18.
- **5 movimientos no se pueden evaluar:** el cierre manual tiene su comprobante pero ese documento no está en la carpeta (D9, D18).
- **Errores propios que encontré y corregí** (D11, D16, D18): una regresión de "haberes → período", ejemplos del prompt con importes reales, una vara de evaluación que no reconocía documentos sin renombrar, una regla de "pago parcial" demasiado amplia. Cada uno está contado con su corrección.
- **Los 13 documentos que son imágenes** dependen de la lectura por visión de Haiku, que es débil. No se probó un modelo más grande solo para esas.
- **Lo que quedó fuera de alcance a propósito:** el cruce de echeqs con comprobantes sueltos, el circuito de facturas con una empresa vinculada y la ejecución programada semanal (D1).
- **Las corridas publicadas están anonimizadas**, no son literalmente "tal como salieron" (D14). Los PDF no se publican.
- **Poco probado:** documentos adversariales (un solo caso ficticio y directo, `corridas/adversarial/`, D17). **No probado:** la API de lotes y el caché de prompts para bajar el costo, y un segundo cliente.
- El agente **no** actualiza la Tabla de Referencias: agregar filas es decisión de la persona.

## Qué aprendí
- **Casi todo el salto de calidad vino de escribir lo que estaba en la cabeza de la persona** (convenciones como "el N° de comprobante de un retiro es el período") y de darle candidatos ya filtrados al modelo, no de un modelo más grande: de v1 a v4 el acierto pasó de 54% a 94% con el mismo Haiku, y Sonnet sumó como mucho un punto, que además queda dentro del ruido entre corridas idénticas.
- **Lo que es una regla debe ser código, no un pedido al modelo.** El modelo cumplió una convención 10 de 14 veces y "corrigió" una tabla que estaba bien; las guardas en código lo resolvieron. A la vez, pasar una regla a código sin entender su excepción la vuelve más dañina.
- **Medir mal es peor que no medir.** La primera evaluación contaba como fallas casos que ningún agente podía acertar, y una métrica ("acierta si no hay comprobante") premiaba al sistema que no hacía nada. Hubo que mirar los errores uno por uno.
- **Entrenar y probar con el mismo mes da una cifra optimista.** Lo honesto es decirlo y no llamarlo generalización.
- Con datos de clientes reales, la **privacidad del repositorio se diseña al principio** (datos fuera del repo, anonimizador con verificación), no se arregla al final.

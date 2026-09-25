# Conciliador bancario mensual (agente)

## Qué construí
Un agente que concilia el extracto bancario mensual de una empresa agropecuaria con la carpeta de comprobantes del mes (PDF y fotos): vincula cada movimiento con su comprobante, completa el N° de comprobante y una categoría (`Categoría - Subcategoría - Identificador`), marca el estado de cada fila con colores (gris, blanco, amarillo, naranja, celeste), copia los comprobantes con un nombre ordenado y genera un reporte de importe por categoría. Es para quien administra empresas de terceros y hoy lo hace a mano cada mes (~140 movimientos, 6 a 8 horas por cliente). El código resuelve lo determinístico (cargos automáticos del banco, tabla de Detalles ya validados, importes exactos) y el modelo (Haiku 4.5; Sonnet 5 solo para leer imágenes) lee los documentos y decide los casos ambiguos; una persona revisa lo marcado y firma.

**Dónde está la evidencia de cada requisito de la consigna:**

| Requisito | Dónde |
|---|---|
| 1 · Sistema completo (objetivo, contrato, herramienta real, salida estructurada, supervisión L0–L4) | Contrato: [prompts/](prompts/) · código: [src/](src/) · supervisión L0–L4: [docs/GOBIERNO_Y_RIESGO.md](docs/GOBIERNO_Y_RIESGO.md), punto 2 |
| 2 · Corre de verdad (tres corridas reales, reconstruibles) | [corridas/](corridas/): 20 corridas, cada una con su `LEEME.md` (fecha, entrada, salida); resumen en [corridas/RESUMEN.md](corridas/RESUMEN.md) |
| 3 · Formato estricto | Este README, `prompts/`, `corridas/` y `DECISIONES.md`, más dos documentos de apoyo (`docs/ANALISIS_ECONOMICO.md` y `docs/GOBIERNO_Y_RIESGO.md`) |
| 4 · Historia del proceso | [DECISIONES.md](DECISIONES.md) (D0 a D19: quién hizo qué, iteraciones, errores, cambios de alcance) y [prompts/historial/](prompts/historial/) |
| 5 · Análisis económico | [docs/ANALISIS_ECONOMICO.md](docs/ANALISIS_ECONOMICO.md) |
| 6 · Gobierno y riesgo | [docs/GOBIERNO_Y_RIESGO.md](docs/GOBIERNO_Y_RIESGO.md) |

## Cómo se lo pedí
Las instrucciones textuales que le di al agente que construyó el sistema (Claude Code), en orden. Los datos personales están reemplazados por `<...>`.

1. *"Te vas a manejar en `<carpeta del trabajo final>`. Analiza los archivos dentro."* (había dos: la consigna y el formato del README).
2. *"`<enlace al repositorio>` es el repo en git"*
3. *"Me dedico a la administración agropecuaria y consultoria de pymes. Tareas que me llevan tiempo: Todos los meses saco el extracto de movimientos del banco, y para cada fila le completo dos columnas nuevas (1) el número del comprobante que dio origen a ese movimiento y (2) una breve categorización de ese movimiento, a que corresponde. Todos los documentos se guardan en la carpeta del mes y ahí deberian de estar todos los que generen los movimientos bancarios y algunos extras que no corresponden a movimientos bancarios; Para otro trabajo tengo una pediatra que trabaja en distintas clinicas y en todas cobra un valor hora distinto. Las hora que trabaja las anota en su calendar de google. Podria crear un agente que extraiga del calendar los eventos, identifique la clinica, y según los valores previamentes cargados, hago un calculo de lo que deberia facturar a cada identidad."* (se eligió el primer caso; el segundo quedó como plan B).
4. Respuestas a mis preguntas de diseño: *"1. Excel 2. En todos los mencionados (PDF principalmente), tienen nombres random. Se podria agregar como tarea del agente que los renombre con el orden del movimiento seguido de ' - ...' el detalle de la categorización 3. Si 4. Si, a medida que pasan los meses, las categorias ya chequeadas para un 'Concepto' quedan determinadas. 5. 140 aprox 6. Si. Adjunto un extracto bancario y un cierre de mes. A su vez seria de utilidad un reporte sencillo especificando el importe destinado a cada categoria"*
5. *"Yo lo tenia en cowork pero con cowork no se tiene registro del gasto? para pasarle al profesor el repo de git conviene hacerlo en code? Que se gasta en cada caso? Te paso la descripción de la tarea?"* — seguido de la instrucción original de Cowork, ~5.000 palabras: [prompts/historial/v0_cowork_original_anonimizado.md](prompts/historial/v0_cowork_original_anonimizado.md).
6. *"1. Estoy de acuerdo. 2. Ok 3. Ok"* (aprobación del recorte de alcance, de la carpeta de datos y de la evaluación contra un mes cerrado) y *"Dejo lo de Agosto."* / *"Si tengo [cuenta de la API]"*.
7. *"1. El verde significa que tengo una copia en papel, pero eso no importa para el agente. Correcto, por eso bajo el naranja. 2. No, porque se va actualizando cada mes. 3. Hagamos todas las corridas en Agosto, mejorando el contrato y, en consecuencia, el resultado obtenido. Cuando consideres, anda subiendo todo a git para que quede registro. Lo central es cumplir con la consigna del tp, mientras que hacemos un uso eficiente de tokens junto con un modelo optimo."*

8. *"1. Publicar tal cual"* (las corridas anonimizadas) y *"Entonces tal como esta, esta listo para entregar? Cumple con la rubrica con la que se va a evaluar?"*
9. *"Si te cargo en la carpeta la consigna con la cual se creo el agente que va a corregir el tp, es de ayuda para considerar algun ajuste?"* y, después de cargarla: *"No es el prompt ni el contrato del agente, es la consigna que se dio al momento de crearlo. Ese tp no lo tenemos que hacer, es solo para que absorbas lo que puede servir para mejorar el tp actual."*
10. *"1. Hace la planilla para que revise solo los casos con diferencia. 2. Sin contar con eso, como quedo? Se dio un contrato que luego se fue perfeccionando con cada prueba? 3. Lleva 6-8hs al mes. Desde que se descarga los movimientos del banco, hasta que se revisa cada documento con un movimiento, se renombra y se hace el informe final. 4. Esta contemplado."*
11. *"No entendi las diferencias. Siempre la razon la tiene el documento con el cierre manual. Podes darte cuenta de la diferencia y el motivo para corregir? O necesitas que te lo marque? Usando el contrato que tengo en cowork te podes ayudar para detectar el error o aspecto a perfeccionar?"*
12. *"Ok, actualiza todo lo necesario en el repo de github para que quede listo para entregar. incluso lo que queda pendiente de resolver"*

**El contrato que usa el agente en cada corrida** (las seis piezas: Rol, Contexto, Tarea, Restricciones, Formato, Ejemplos) está en [prompts/system_prompt_lector.md](prompts/system_prompt_lector.md) + [prompts/user_prompt_lector.md](prompts/user_prompt_lector.md) (etapa 1) y [prompts/system_prompt.md](prompts/system_prompt.md) + [prompts/user_prompt.md](prompts/user_prompt.md) (etapa 2). Las versiones v1 a v7 están en `prompts/historial/`, y cada corrida guarda los prompts que usó en `prompts_usados/`.

## Qué funciona
**Cómo se usa** (sobre un mes con el extracto descargado y los comprobantes en una carpeta):
```
pip install -r requirements.txt
python evaluacion/preparar_datos.py 202608        # solo para probar contra un mes ya cerrado
python src/main.py --mes 202608 --etiqueta final --temperatura 0 --lector-imagenes sonnet
```
Necesita una clave de la API de Anthropic en `datos_privados/.env` (`ANTHROPIC_API_KEY=...`). Los datos reales no están en el repositorio: para reproducir hace falta una carpeta propia con la misma forma. Cada corrida genera en `datos_privados/<mes>/corridas/<fecha>_<etiqueta>/`: el Excel del mes con las columnas y colores, el reporte de 3 hojas (resumen, totales por categoría, filas para revisar), los comprobantes copiados con nombre nuevo, y el JSON con cada decisión, su confianza, su motivo y los tokens gastados.

**Qué se probó y anduvo** (mes de agosto: 143 movimientos, 128 documentos únicos, 58 de los cuales no corresponden a ningún movimiento). Evaluación contra el cierre manual, que es la verdad, sobre 92 movimientos evaluables:

| Corrida | N° comprobante exacto | Detalle (celdas validadas) | Documentos bien vinculados (de 70) | US$ por corrida completa |
|---|---|---|---|---|
| Solo código + tabla, sin modelo (línea base) | 22%* | 80% | 0 | 0 |
| v1 (Haiku) | 53% | 82% | 44 | 0,55 |
| v5 (Haiku; ejemplos del prompt sin datos reales) | 95% | 88% | 59 | 0,63 |
| v9 (Haiku en todo), tres corridas | 98%, 99%, 98% | 100% | 67, 68, 67 | 0,69 |
| **v10 (final: Haiku + Sonnet solo para imágenes, temperatura 0)** | **100% (92/92)** | **100% (40/40)** | **69** | **0,78** |
| v10, dos repeticiones (misma lectura) | 100% y 100% | 100% | 69 y 69 | 0,78 |
| v10 releyendo los 128 documentos, y la corrida final sobre esa relectura | 99% y 99% | 100% | 68 y 68 | 0,79 |
| v4 con Sonnet 5 en las dos etapas | 93% | 90% | 60 | 1,62 |

\* La línea base "acierta" en las filas que no tienen comprobante; por eso se mira también cuántos documentos quedan bien vinculados. Historia completa de las 20 corridas en [corridas/RESUMEN.md](corridas/RESUMEN.md).

- Los 46 cargos automáticos del banco se marcan solos y sin costo; 25 movimientos más se resuelven por regla, sin modelo.
- El pipeline cuesta unos **US$ 0,78 por mes por cliente** (US$ 9,4 por año), el 92% en la lectura de documentos. Ver [docs/ANALISIS_ECONOMICO.md](docs/ANALISIS_ECONOMICO.md).
- **Modelos:** Haiku 4.5 en las dos etapas, y Sonnet 5 **solo** para las 13 imágenes y PDF escaneados (+US$ 0,11 por mes). Sonnet en todo no mejora el resultado y cuesta 2,5 veces más.
- **Repetibilidad:** con temperatura 0 el conciliador da exactamente lo mismo dos veces con la misma lectura; el lector no (al releer cambian 29 de 128 lecturas, con efecto de 3 filas), por eso el cache de lecturas forma parte de la evidencia de una corrida (D19).
- **De 97 movimientos que no son cargos del banco, 68 quedan marcados para revisar** (70%): el agente prefiere avisar a vincular mal.
- Las corridas guardan tokens de entrada y salida, modelo, prompts y decisiones por movimiento, y permiten reconstruir qué pasó (ver [corridas/](corridas/), cada una con su `LEEME.md`).
- Cada diferencia con el cierre manual se investigó leyendo los documentos y se corrigió en el contrato o en el código (`DECISIONES.md`, D18).
- **Prueba adversarial:** 10 de 10 verificaciones con dos ataques ficticios (uno visible y otro de texto invisible); un detector local marca los documentos con instrucciones sospechosas y baja su confianza (`corridas/adversarial/`, D17 y D19).

## Qué falta o qué falló
- **La cifra no dice cuánto generaliza.** Las reglas de v2 a v9 salieron de las fallas de agosto y se miden sobre agosto: es entrenar y probar con el mismo mes. Algunas reglas son muy específicas de agosto. Hay un solo mes; falta correrlo sobre otro mes **sin tocar nada**. Es lo primero que haría, y no se puede cerrar con los datos que hay.
- **El ahorro en horas no está medido.** El proceso manual lleva 6 a 8 horas por mes; el agente cuesta US$ 0,78 pero la revisión humana con el agente no se cronometró (quedan 68 filas marcadas de 97). Ver `docs/ANALISIS_ECONOMICO.md`, 2.b. Requiere que la persona cronometre un mes real.
- **El lector no es determinista**, ni siquiera con temperatura 0 (Sonnet no admite fijarla): al releer los 128 documentos cambian 29 lecturas. El efecto en el resultado fue de 3 filas y 1 comprobante (D19).
- **Errores que siguen** (0 a 1 comprobantes de 92, 0 detalles de 40, 1 a 2 documentos de 70 sin vincular según la lectura): un documento de apoyo que el lector confunde con un resumen de sueldos y un comprobante que varía entre lecturas. Detalle en `DECISIONES.md`, D18 y D19.
- **5 movimientos no se pueden evaluar:** el cierre manual tiene su comprobante pero ese documento no está en la carpeta (D9, D18).
- **Errores propios que encontré y corregí** (D11, D16, D18, D19): una regresión de "haberes → período", ejemplos del prompt con importes reales, una vara de evaluación que no reconocía documentos sin renombrar, una regla de "pago parcial" demasiado amplia. Cada uno está contado con su corrección.
- **Los ataques probados son dos y los escribí yo:** el detector de instrucciones sospechosas cubre esas frases y no otras redacciones ni instrucciones dentro de imágenes (D19).
- **Lo que quedó fuera de alcance a propósito:** el cruce de echeqs con comprobantes sueltos, el circuito de facturas con una empresa vinculada y la ejecución programada semanal (D1).
- **Las corridas publicadas están anonimizadas**, no son literalmente "tal como salieron" (D14). Los PDF no se publican, y sin ellos el repositorio no se puede volver a ejecutar tal cual.
- **La historia de git** son todos del mismo día (25/09), y los dos primeros contienen importes y números de comprobante reales (sin nombres) de los ejemplos de los primeros prompts; ya están reemplazados en los archivos, pero reescribir la historia requiere un force-push que necesita la autorización de la persona (D0, D19).
- **No implementado ni medido:** la API de lotes y el agrupado de documentos por llamada. **Probado y descartado:** el caché de prompts (no aplica con prompts de este tamaño).
- El agente **no** actualiza la Tabla de Referencias: agregar filas es decisión de la persona.

## Qué aprendí
- **Casi todo el salto de calidad vino de escribir lo que estaba en la cabeza de la persona** (convenciones como "el N° de comprobante de un retiro es el período") y de darle candidatos ya filtrados al modelo, no de un modelo más grande: de v1 a v4 el acierto pasó de 54% a 94% con el mismo Haiku, y Sonnet sumó como mucho un punto, que además queda dentro del ruido entre corridas idénticas.
- **Lo que es una regla debe ser código, no un pedido al modelo.** El modelo cumplió una convención 10 de 14 veces y "corrigió" una tabla que estaba bien; las guardas en código lo resolvieron. A la vez, pasar una regla a código sin entender su excepción la vuelve más dañina.
- **Medir mal es peor que no medir.** La primera evaluación contaba como fallas casos que ningún agente podía acertar, y una métrica ("acierta si no hay comprobante") premiaba al sistema que no hacía nada. Hubo que mirar los errores uno por uno.
- **Entrenar y probar con el mismo mes da una cifra optimista, y un modelo no da dos veces lo mismo.** Lo honesto es decirlo, medir el ruido repitiendo la corrida y no llamarlo generalización.
- Con datos de clientes reales, la **privacidad del repositorio se diseña al principio** (datos fuera del repo, anonimizador con verificación), no se arregla al final.

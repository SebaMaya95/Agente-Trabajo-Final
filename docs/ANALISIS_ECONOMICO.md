# Análisis económico

Todas las cifras de tokens y costos salen de `usage` de la API, registrado llamada por llamada en `corridas/*/llamadas.json`. Los precios son los de la tabla oficial de Anthropic vigente al 24/06/2026 (verificar antes de citar): Haiku 4.5 US$ 1,00 entrada / US$ 5,00 salida por millón de tokens; Sonnet 5 US$ 2,00 / US$ 10,00.

## 1. Qué cuesta una corrida (un mes completo: 143 movimientos, 128 documentos)

**Configuración final:** Haiku 4.5 en las dos etapas, con **Sonnet 5 solo para las imágenes y los PDF escaneados** (13 de 128 documentos), temperatura 0 en Haiku. Medida en la corrida `15_v10` (`corridas/15_v10/llamadas.json`).

| Etapa y modelo | Llamadas | Tokens de entrada | Tokens de salida | US$ |
|---|---|---|---|---|
| Lector, Haiku 4.5 (documentos con texto) | 115 | 426.282 | 18.625 | 0,519 |
| Lector, Sonnet 5 (imágenes y escaneados) | 12* | 78.888 | 2.872 | 0,187 |
| Conciliador, Haiku 4.5 (lotes de 20; solo lo que el código no resuelve: 72 de 97) | 4 | 35.038 | 5.382 | 0,062 |
| **Total por mes** | 131 | 540.208 | 26.879 | **0,768** |

\* Un documento se reutilizó del cache de un intento anterior interrumpido; medida con la lectura completa de referencia, el pipeline entero cuesta **US$ 0,784** (lector US$ 0,723 + conciliador US$ 0,062).

- Por movimiento: US$ 0,0055. Por documento leído: US$ 0,0056 (~4.200 tokens de entrada y ~170 de salida).
- **El lector es el 92% del gasto**, casi todo entrada. Medido con el contador de tokens de la API, el prompt del sistema del lector pesa **1.971 tokens** (1.124 en v1) y se repite en las 128 llamadas: ~252.000 tokens, la mitad de la entrada de Haiku en el lector. El del conciliador pesa 2.722 tokens.
- **Leer las 13 imágenes con Sonnet en vez de Haiku cuesta unos US$ 0,11 más por mes** (US$ 0,78 frente a US$ 0,69 con Haiku en todo) y arregla el documento que Haiku no leía (un resumen de egresos de un edificio, una imagen).
- El costo subió de US$ 0,53 (v1) a US$ 0,78 (final) porque el contrato del lector creció y se sumó Sonnet para imágenes. Es el precio de los aciertos: de 53% a 99–100% en N° de comprobante.
- La lectura se guarda en un cache por contenido del documento, versión del prompt, modelo y temperatura: releer el mes con otro contrato del conciliador cuesta solo la etapa 2 (US$ 0,06). Así se hicieron varias corridas. **El cache además fija la lectura**: mientras esté, el resultado de la etapa 2 es idéntico (ver `DECISIONES.md`, D19).
- Lo que el código resuelve sin modelo (46 cargos automáticos del banco y 25 movimientos por regla) no cuesta tokens.

**Costo total de construir y probar el agente (solo API): US$ 7,39**: 21 corridas con la API (US$ 7,33, incluida una prueba de humo de US$ 0,049 y una de caché de prompt) más 6 pasadas de la prueba adversarial (US$ 0,06). No incluye el uso de Claude Code para escribir el código, que corre con la suscripción y no se mide por token.

## 2. Qué costaría corriendo en serio

Supuesto: un cliente, una corrida completa por mes, ~140 movimientos y ~130 documentos (lo medido en agosto).

| Escenario | US$ / mes | US$ / año | Base |
|---|---|---|---|
| **A. Una corrida mensual, configuración final (recomendado)** | 0,78 | 9,4 | medido |
| A'. Haiku en todo (sin Sonnet para imágenes) | 0,69 | 8,3 | medido (`corridas/11_v8` + `12_v9`) |
| B. Como el proceso actual: conciliación cada semana sobre el mes acumulado (la lectura de cada documento se paga una sola vez) | ~1,0 | ~12 | estimado: 0,78 + 4 conciliaciones adicionales de hasta 0,06 |
| C. Sonnet 5 en las dos etapas | ~1,7 | ~20 | medido con el contrato v4 (`corridas/06`); no se repitió con el final |
| D. Escenario A con la API de lotes (procesamiento asincrónico con 50% de descuento sobre el lector) | ~0,42 | ~5 | proyección; **no implementado ni medido** |

Con **10 clientes** parecidos: el escenario A cuesta unos US$ 94 por año.

## 2.b Frente al proceso manual

- **Tiempo actual (dato del administrador):** **6 a 8 horas por mes y por cliente**, desde que descarga los movimientos del banco hasta que revisa cada documento contra su movimiento, los renombra y arma el informe final.
- **Lo que el agente hace en lugar de esas horas:** leer los 128 documentos, vincularlos con los movimientos, completar comprobante y categoría, copiarlos con nombre ordenado y armar el reporte por categoría. Costo: US$ 0,78.
- **Lo que sigue haciendo la persona** (medido en agosto, corrida final): de los 143 movimientos, 46 son cargos automáticos del banco (sin revisión). De los 97 restantes, **68 quedan marcados para revisar** (70%; las causas se superponen: 25 naranjas sin documento, 5 amarillas, 39 de confianza media o baja y 46 con Detalle deducido en celeste) y 29 quedan como "alta confianza", que se revisan por muestreo. Marcar de más es una decisión de diseño: el agente prefiere avisar a vincular mal.
- **Lo que NO está medido: cuánto tarda esa revisión.** No hay un mes real corrido con el agente y cronometrado, así que **el ahorro en horas es una hipótesis, no un resultado**. Cualquier cifra sería inventada. Lo que sí se puede afirmar con lo medido: la parte que el agente automatiza (leer, vincular, renombrar, reportar) es la mayor parte de las 6 a 8 horas descriptas, y la revisión humana pasa de ser sobre todos los documentos a ser sobre 68 filas marcadas más una muestra.
- **Punto de equilibrio:** el agente conviene mientras la revisión lleve menos que las 6 a 8 horas actuales, y el costo de la API es despreciable. **A modo de ilustración** (valor hora hipotético de US$ 20, no un dato del administrador), 6 a 8 horas equivalen a US$ 120 a 160 por mes por cliente: la API sería el 0,5% a 0,7% de ese costo. Si la revisión llevara la mitad del tiempo actual (hipótesis), el ahorro sería de 3 a 4 horas por mes, es decir 36 a 48 horas por año por cliente.
- **Cómo cerrar el dato:** correr un mes real con el agente, cronometrar la revisión y registrar el resultado en `DECISIONES.md`.

## 3. Elección del modelo, con el criterio del curso (el más chico que hace bien la tarea)

Se probó lo mismo, sobre el mismo mes y con la misma vara (el cierre manual, evaluación corregida de 92 movimientos; `DECISIONES.md`, D13, D18 y D19).

| Configuración | N° comprobante exacto | Detalle (celdas validadas) | US$ / mes |
|---|---|---|---|
| Haiku 4.5 + Haiku 4.5 (contrato v4) | 95% (87/92) | 90% (36/40) | 0,64 |
| Haiku 4.5 + Sonnet 5 conciliador (contrato v4) | 91% (84/92) | 92% (37/40) | 0,76 |
| Sonnet 5 + Sonnet 5 (contrato v4) | 93% (86/92) | 90% (36/40) | 1,62 |
| Haiku 4.5 en todo (versión v9, 3 corridas) | 98%, 99%, 98% | 100% | 0,69 |
| **Haiku 4.5 + Sonnet 5 solo para imágenes (versión final: 2 lecturas independientes y 4 conciliaciones)** | **100%, 100%, 100% y 99%** | **100%** | **0,78** |

- Con la evaluación corregida, **Haiku queda igual o mejor que las opciones más caras** cuando se compara con el mismo contrato (primeras tres filas). Sonnet como conciliador no mejora y cuesta 19% más; Sonnet en las dos etapas cuesta 2,5 veces más y acierta un comprobante menos.
- **La única escalada que se justifica es la de las imágenes:** Sonnet solo para 13 documentos suma US$ 0,11 por mes y es la diferencia entre 98–99% y 99–100%. La escalada por tipo de documento (no por tarea) sigue el criterio del curso: el modelo más chico donde alcanza y uno mayor donde mide que no.
- Las diferencias de un movimiento no son distinguibles del ruido: repetir la misma corrida da ±1 (`DECISIONES.md`, D15, D18 y D19). Lo que separa a la versión final de v9 son 1 o 2 movimientos y un documento; es coherente pero **no concluyente** con un solo mes.
- El salto de calidad (53% → 99–100%) vino del contrato y del código, no del modelo.
- No se probaron: un modelo de la familia Opus ni razonamiento extendido activado.

## 4. Lo que se probó para ahorrar (y lo que no)
1. **Caché de prompts: probado, no aplica.** Se marcó el prompt del sistema como cacheable en 8 llamadas del lector (1.971 tokens) y 2 del conciliador (2.722 tokens): ninguna creó ni leyó caché. El mínimo cacheable de Haiku 4.5 es mayor que esos prompts. Para aprovecharlo habría que juntar más de un contexto por llamada, lo que aumenta el riesgo de confundir documentos.
2. **Prompt del lector más corto:** es la mitad de la entrada de Haiku en el lector (1.971 tokens). No se acortó: cada regla del contrato existe por un error medido. Es un compromiso costo–acierto que queda documentado.
3. **API de lotes** para la etapa 1 (50% menos; el lector no necesita respuesta inmediata): **no implementada ni medida**.
4. **Agrupar 3 o 4 documentos por llamada** para repartir el prompt: **no probado** (riesgo: más confusión entre documentos).
5. **No leer con modelo** los documentos que el código ya sabe descartar: los duplicados exactos por hash ya se eliminan.

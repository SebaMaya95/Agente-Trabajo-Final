# Análisis económico

Todas las cifras de tokens y costos salen de `usage` de la API, registrado llamada por llamada en `corridas/*/llamadas.json`. Los precios son los de la tabla oficial de Anthropic vigente al 24/06/2026 (verificar antes de citar): Haiku 4.5 US$ 1,00 entrada / US$ 5,00 salida por millón de tokens; Sonnet 5 US$ 2,00 / US$ 10,00.

## 1. Qué cuesta una corrida (un mes completo: 143 movimientos, 128 documentos)

Configuración final: Haiku 4.5 en las dos etapas, contrato y código de la versión final (v9). La lectura se midió en la corrida `11_v8` y la conciliación en la `12_v9` (el lector no cambió entre ambas, por eso la lectura se reutilizó del cache).

| Etapa | Llamadas | Tokens de entrada | Tokens de salida | US$ |
|---|---|---|---|---|
| Lector (1 llamada por documento) | 128 | 500.670 | 21.594 | 0,609 |
| Conciliador (lotes de 20 movimientos, solo los que el código no resuelve: 73 de 97) | 4 | 51.177 | 5.598 | 0,079 |
| **Total por mes** | 132 | 551.847 | 27.192 | **0,688** |

- Por movimiento: US$ 0,0048. Por documento leído: US$ 0,0048 (~3.900 tokens de entrada y ~170 de salida).
- **El lector es el 88% del gasto**, y casi todo es entrada. Medido con el contador de tokens de la API: el prompt del sistema del lector pesa **1.971 tokens** (1.124 en v1) y se repite en las 128 llamadas: son ~252.000 de los 500.670 tokens de entrada del lector, **el 50%**. El del conciliador pesa 2.722 tokens.
- El costo subió de US$ 0,53 (v1) a US$ 0,69 (versión final) porque el contrato del lector creció ~850 tokens al agregar reglas. Es el precio de los aciertos: de 53% a 98% en N° de comprobante por unos US$ 0,15 más por mes.
- La lectura se guarda en un cache por contenido del documento y versión del prompt: releer el mes con otro contrato del conciliador cuesta solo la etapa 2 (US$ 0,08). Así se hicieron las corridas v3, v4, v7 y v9.
- Lo que el código resuelve sin modelo (46 cargos automáticos del banco y 24 movimientos por regla) no cuesta tokens.

**Costo total de construir y probar el agente (solo API):** **US$ 5,55**: 15 corridas con la API (US$ 5,52, incluida una prueba de humo de US$ 0,049) más 4 pasadas de la prueba adversarial (US$ 0,03). No incluye el uso de Claude Code para escribir el código, que corre con la suscripción y no se mide por token.

## 2. Qué costaría corriendo en serio

Supuesto: un cliente, una corrida completa por mes, ~140 movimientos y ~130 documentos (lo medido en agosto).

| Escenario | US$ / mes | US$ / año | Base |
|---|---|---|---|
| **A. Una corrida mensual, Haiku (recomendado)** | 0,69 | 8,3 | medido |
| B. Como el proceso actual: conciliación cada semana sobre el mes acumulado (la lectura de cada documento se paga una sola vez) | ~1,0 | ~12 | estimado: 0,69 + 4 conciliaciones adicionales de hasta 0,08 |
| C. Sonnet 5 solo como conciliador | ~0,8 | ~10 | medido con el contrato v4 (`corridas/05`); no se repitió con el final |
| D. Sonnet 5 en las dos etapas | ~1,7 | ~20 | medido con el contrato v4 (`corridas/06`); no se repitió con el final |
| E. Escenario A con la API de lotes (procesamiento asincrónico con 50% de descuento sobre el lector) | ~0,38 | ~4,6 | proyección; **no implementado ni medido** |

Con **10 clientes** parecidos: el escenario A cuesta unos US$ 83 por año.

## 2.b Frente al proceso manual

- **Tiempo actual (dato del administrador):** **6 a 8 horas por mes y por cliente**, desde que descarga los movimientos del banco hasta que revisa cada documento contra su movimiento, los renombra y arma el informe final.
- **Lo que el agente hace en lugar de esas horas:** leer los 128 documentos, vincularlos con los movimientos, completar comprobante y categoría, copiarlos con nombre ordenado y armar el reporte por categoría. Costo: US$ 0,69.
- **Lo que sigue haciendo la persona** (medido en agosto, corrida final): de los 143 movimientos, 46 son cargos automáticos del banco (sin revisión). De los 97 restantes, **69 quedan marcados para revisar** (71%; las causas se superponen: 26 naranjas sin documento, 5 amarillas, 41 de confianza media o baja y 44 con Detalle deducido en celeste) y 28 quedan como "alta confianza", que se revisan por muestreo. Marcar de más es una decisión de diseño: el agente prefiere avisar a vincular mal.
- **Lo que NO está medido: cuánto tarda esa revisión.** No hay un mes real corrido con el agente y cronometrado, así que **el ahorro en horas es una hipótesis, no un resultado**. Cualquier cifra sería inventada. Lo que sí se puede afirmar con lo medido: la parte que el agente automatiza (leer, vincular, renombrar, reportar) es la mayor parte de las 6 a 8 horas descriptas, y la revisión humana pasa de ser sobre todos los documentos a ser sobre 69 filas marcadas más una muestra.
- **Punto de equilibrio:** el agente conviene mientras la revisión lleve menos que las 6 a 8 horas actuales, y el costo de la API es despreciable. **A modo de ilustración** (valor hora hipotético de US$ 20, no un dato del administrador), 6 a 8 horas equivalen a US$ 120 a 160 por mes por cliente: la API sería el 0,4% a 0,6% de ese costo. Si la revisión llevara la mitad del tiempo actual (hipótesis), el ahorro sería de 3 a 4 horas por mes, es decir 36 a 48 horas por año por cliente.
- **Cómo cerrar el dato:** correr un mes real con el agente, cronometrar la revisión y registrar el resultado en `DECISIONES.md`.

## 3. Elección del modelo, con el criterio del curso (el más chico que hace bien la tarea)

Se probó lo mismo, sobre el mismo mes y con la misma vara (el cierre manual, evaluación corregida de 92 movimientos; `DECISIONES.md`, D13 y D18), con tres configuraciones del contrato v4:

| Configuración | N° comprobante exacto | Detalle (celdas validadas) | US$ / mes |
|---|---|---|---|
| **Haiku 4.5 + Haiku 4.5** | 95% (87/92) | 90% (36/40) | **0,64** |
| Haiku 4.5 + Sonnet 5 | 91% (84/92) | 92% (37/40) | 0,76 |
| Sonnet 5 + Sonnet 5 | 93% (86/92) | 90% (36/40) | 1,62 |

- Con la evaluación corregida, **Haiku con Haiku queda igual o mejor que las opciones más caras** en comprobantes y empata en Detalle. Sonnet como conciliador no mejora y cuesta 19% más; Sonnet en las dos etapas cuesta 2,5 veces más y acierta un comprobante menos.
- Las diferencias de un movimiento no son distinguibles del ruido: repetir la misma corrida da ±1 (v4: 95% y 93%; la versión final, tres veces: 98%, 99% y 98%; `DECISIONES.md`, D15 y D18).
- **Decisión: Haiku 4.5 en las dos etapas.** Es el modelo más chico disponible y hace bien la tarea *cuando el contrato y el código hacen su parte* (candidatos filtrados por importe, guardas, convenciones escritas). El salto de calidad (53% → 98%) vino del contrato y del código, no del modelo.
- No se probaron: un modelo de la familia Opus, razonamiento extendido activado, ni un modelo más grande solo para la lectura de imágenes (13 de 128 documentos). Es la primera prueba que se haría si el lector de imágenes resultara ser el límite: el resumen de egresos de un edificio, una imagen, sigue sin leerse bien con Haiku.

## 4. Dónde se puede ahorrar más (no implementado)
1. **API de lotes** para la etapa 1 (50% menos; el lector no necesita respuesta inmediata).
2. **Prompt del lector más corto o cacheado.** Es la mitad de la entrada del lector: pasó de 1.124 a 1.971 tokens entre v1 y la versión final. El caché de prompts tiene un mínimo de tokens que depende del modelo y puede ser mayor que 1.971: habría que medir si aplica antes de contar con ese ahorro.
3. **Agrupar 3 o 4 documentos por llamada** para repartir el prompt (riesgo: más confusión entre documentos; habría que medirlo).
4. **No leer con modelo** los documentos que el código ya sabe descartar (por ejemplo, duplicados exactos por hash, que ya se eliminan).

# Análisis económico

Todas las cifras de tokens y costos salen de `usage` de la API, registrado llamada por llamada en `corridas/*/llamadas.json`. Los precios son los de la tabla oficial de Anthropic vigente al 24/06/2026 (verificar antes de citar): Haiku 4.5 US$ 1,00 entrada / US$ 5,00 salida por millón de tokens; Sonnet 5 US$ 2,00 / US$ 10,00.

## 1. Qué cuesta una corrida (un mes completo: 143 movimientos, 128 documentos)

Configuración final: Haiku 4.5 en las dos etapas, contrato v5 (corrida `08_v5-ejemplos-limpios`, medida completa).

| Etapa | Llamadas | Tokens de entrada | Tokens de salida | US$ |
|---|---|---|---|---|
| Lector (1 llamada por documento) | 128 | 457.790 | 21.365 | 0,565 |
| Conciliador (lotes de 20 movimientos, solo los que el código no resuelve) | 5 | 35.015 | 6.118 | 0,066 |
| **Total por mes** | 133 | 492.805 | 27.483 | **0,630** |

- Por movimiento: US$ 0,0044. Por documento leído: US$ 0,0044 (~3.600 tokens de entrada y ~170 de salida).
- **El lector es el 89% del gasto**, y casi todo es entrada. Medido con el contador de tokens de la API: el prompt del sistema del lector pesa **1.636 tokens** (1.124 en v1) y se repite en las 128 llamadas: son ~209.000 de los 457.790 tokens de entrada del lector, **el 46%**. El resto es el texto de cada documento.
- La lectura se guarda en un cache por contenido del documento y versión del prompt: releer el mes con otro conciliador (o con otro contrato del conciliador) cuesta solo la etapa 2 (US$ 0,07). Así se hicieron las corridas v3 y v4.
- Lo que el código resuelve sin modelo (filas grises: 46 de 143; y la regla "importe único + emisor + tabla": 15) no cuesta tokens.

**Costo total de construir y probar el agente (solo API):** US$ 3,88 = prueba de humo 0,049 + v1 0,534 + v2 0,635 + v3 0,069 + v4 0,070 + Sonnet conciliador 0,190 + Sonnet completo 1,616 + repetición de v4 0,069 + v5 0,630 + prueba adversarial 0,015. (No incluye el uso de Claude Code para escribir el código, que corre con la suscripción y no se mide por token.)

## 2. Qué costaría corriendo en serio

Supuesto: un cliente, una corrida completa por mes, ~140 movimientos y ~130 documentos (lo medido en agosto).

| Escenario | US$ / mes | US$ / año | Base |
|---|---|---|---|
| **A. Una corrida mensual, Haiku (recomendado)** | 0,63 | 7,6 | medido |
| B. Como el proceso actual: conciliación cada semana sobre el mes acumulado (la lectura de cada documento se paga una sola vez) | ~0,91 | ~11 | estimado: 0,63 + 4 conciliaciones adicionales de hasta 0,07 |
| C. Sonnet 5 solo como conciliador | 0,76 | 9,1 | medido (contrato v4) |
| D. Sonnet 5 en las dos etapas | 1,62 | 19,4 | medido (contrato v4) |
| E. Escenario A con la API de lotes (procesamiento asincrónico con 50% de descuento sobre el lector) | ~0,35 | ~4,2 | proyección; **no implementado ni medido** |

Con **10 clientes** parecidos: el escenario A cuesta unos US$ 76 por año; el D, unos US$ 194.

**Frente al ahorro:** el costo de la API (US$ 0,63 por cliente por mes) es despreciable frente al tiempo humano del proceso manual. *Falta un dato que solo tiene el administrador: cuántas horas lleva hoy el cierre de un mes. No se estimó acá para no inventarlo.* Lo que sí se puede decir con lo medido es que el agente no es el cuello de botella económico: lo es la revisión humana de lo marcado.

## 3. Elección del modelo, con el criterio del curso (el más chico que hace bien la tarea)

Se probó lo mismo, sobre el mismo mes y con la misma vara (el cierre manual), con tres configuraciones (ver `DECISIONES.md`, D13, y `corridas/RESUMEN.md`):

| Configuración | N° comprobante exacto | Detalle (celdas validadas) | US$ / mes |
|---|---|---|---|
| **Haiku 4.5 + Haiku 4.5** (v4; v5 dio 94% / 92%, US$ 0,63) | 94% (85/90) | 95% (36/38) | **0,64** |
| Haiku 4.5 + Sonnet 5 | 91% (82/90) | 97% (37/38) | 0,76 |
| Sonnet 5 + Sonnet 5 | 96% (86/90) | 95% (36/38) | 1,62 |

- Sonnet como conciliador **no mejora** el resultado (peor en comprobantes) y cuesta 19% más.
- Sonnet en las dos etapas acierta **un** comprobante más de 90 (y deja dos documentos menos vinculados de más) a **2,5 veces** el costo. Con un mes y n=90, la diferencia no es distinguible del ruido: repetir la misma corrida con Haiku dio 93% en vez de 94% (`DECISIONES.md`, D15).
- **Decisión: Haiku 4.5 en las dos etapas.** Es el modelo más chico disponible y hace bien la tarea *cuando el contrato y el código hacen su parte* (candidatos filtrados por importe, guardas, convenciones escritas). El salto de calidad de v1 a v4 (54% → 94%) vino del contrato y del código, no del modelo: cambiar de modelo agregó, como mucho, dos puntos.
- No se probaron: un modelo de la familia Opus, razonamiento extendido activado, ni un modelo más grande solo para la lectura de imágenes (13 de 128 documentos). Es la primera prueba que se haría si el lector de imágenes resultara ser el límite.

## 4. Dónde se puede ahorrar más (no implementado)
1. **API de lotes** para la etapa 1 (50% menos; el lector no necesita respuesta inmediata).
2. **Prompt del lector más corto o cacheado.** Es casi la mitad de la entrada del lector: pasó de 1.124 a 1.636 tokens entre v1 y v2 (+US$ 0,06 por corrida). El caché de prompts tiene un mínimo de tokens que depende del modelo y puede ser mayor que 1.636: habría que medir si aplica antes de contar con ese ahorro.
3. **Agrupar 3 o 4 documentos por llamada** para repartir el prompt (riesgo: más confusión entre documentos; habría que medirlo).
4. **No leer con modelo** los documentos que el código ya sabe descartar (por ejemplo, duplicados exactos por hash, que ya se eliminan).

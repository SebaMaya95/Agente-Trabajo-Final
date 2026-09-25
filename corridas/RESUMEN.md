# Resumen de corridas (mes 202608)

Generado por `evaluacion/resumen_corridas.py`. Evaluación contra el cierre manual, sobre 90 movimientos evaluables (7 más quedan fuera porque el cierre manual tiene un comprobante cuyo documento no está en la carpeta). Las reglas de v2 a v4 se derivaron de las fallas de este mismo mes: los resultados son optimistas (ver DECISIONES.md, D12).

| Corrida | Fecha | Modelo lector / conciliador | N° comprobante | Detalle (celdas validadas) | Docs bien vinculados | Docs vinculados de más | Tokens entrada / salida gastados | US$ gastados en la corrida | US$ pipeline completo* |
|---|---|---|---|---|---|---|---|---|---|
| 00_base-sin-modelo | 2026-09-25 13:07 | - / - | 22% (20/90) | 84% (32/38) | 0/68 | 0 | 0 / 0 | 0.000 | 0.000 |
| 01_v1 | 2026-09-25 13:33 | claude-haiku-4-5 / claude-haiku-4-5 | 54% (49/90) | 87% (33/38) | 42/68 | 4 | 397,742 / 27,211 | 0.534 | 0.554 |
| 02_v2 | 2026-09-25 13:40 | claude-haiku-4-5 / claude-haiku-4-5 | 91% (82/90) | 79% (30/38) | 55/68 | 4 | 496,025 / 27,802 | 0.635 | 0.635 |
| 03_v3 | 2026-09-25 13:42 | claude-haiku-4-5 / claude-haiku-4-5 | 92% (83/90) | 95% (36/38) | 58/68 | 5 | 39,132 / 6,013 | 0.069 | 0.636 |
| 04_v4 | 2026-09-25 13:44 | claude-haiku-4-5 / claude-haiku-4-5 | 94% (85/90) | 95% (36/38) | 58/68 | 5 | 39,367 / 6,180 | 0.070 | 0.637 |
| 05_v4-conc-sonnet | 2026-09-25 13:46 | claude-haiku-4-5 / claude-sonnet-5 | 91% (82/90) | 97% (37/38) | 55/68 | 6 | 52,370 / 8,559 | 0.190 | 0.757 |
| 06_v4-todo-sonnet | 2026-09-25 13:49 | claude-sonnet-5 / claude-sonnet-5 | 96% (86/90) | 95% (36/38) | 58/68 | 3 | 620,560 / 37,484 | 1.616 | 1.616 |
| 07_v4-repeticion | 2026-09-25 14:01 | claude-haiku-4-5 / claude-haiku-4-5 | 93% (84/90) | 92% (35/38) | 55/68 | 5 | 39,367 / 5,979 | 0.069 | 0.636 |
| 08_v5-ejemplos-limpios | 2026-09-25 14:05 | claude-haiku-4-5 / claude-haiku-4-5 | 94% (85/90) | 92% (35/38) | 57/68 | 6 | 492,805 / 27,483 | 0.630 | 0.630 |

(*) Lectura completa de los 128 documentos (medida en la corrida que la hizo) más la conciliación de esa corrida. Las corridas 03 a 05 y 07 reutilizaron la lectura de la 02 desde el cache, por eso gastaron mucho menos. La prueba de humo con 5 documentos (US$ 0,049) no se publica.

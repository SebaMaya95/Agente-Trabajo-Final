# Resumen de corridas (mes 202608)

Generado por `evaluacion/resumen_corridas.py`. Evaluación contra el cierre manual, sobre 92 movimientos evaluables (5 más quedan fuera porque el cierre manual tiene un comprobante cuyo documento no está en la carpeta; ver DECISIONES.md, D9 y D18). Las reglas de v2 a v9 se derivaron de las fallas de este mismo mes: los resultados son optimistas (ver DECISIONES.md, D12 y D18).

| Corrida | Fecha | Modelo lector / conciliador | N° comprobante | Detalle (celdas validadas) | Docs bien vinculados | Docs vinculados de más | Tokens entrada / salida gastados | US$ gastados en la corrida | US$ pipeline completo* |
|---|---|---|---|---|---|---|---|---|---|
| 00_base-sin-modelo | 2026-09-25 13:07 | - / - | 22% (20/92) | 80% (32/40) | 0/70 | 0 | 0 / 0 | 0.000 | 0.000 |
| 01_v1 | 2026-09-25 13:33 | claude-haiku-4-5 / claude-haiku-4-5 | 53% (49/92) | 82% (33/40) | 44/70 | 2 | 397,742 / 27,211 | 0.534 | 0.554 |
| 02_v2 | 2026-09-25 13:40 | claude-haiku-4-5 / claude-haiku-4-5 | 91% (84/92) | 75% (30/40) | 57/70 | 2 | 496,025 / 27,802 | 0.635 | 0.635 |
| 03_v3 | 2026-09-25 13:42 | claude-haiku-4-5 / claude-haiku-4-5 | 92% (85/92) | 90% (36/40) | 60/70 | 3 | 39,132 / 6,013 | 0.069 | 0.636 |
| 04_v4 | 2026-09-25 13:44 | claude-haiku-4-5 / claude-haiku-4-5 | 95% (87/92) | 90% (36/40) | 60/70 | 3 | 39,367 / 6,180 | 0.070 | 0.637 |
| 05_v4-conc-sonnet | 2026-09-25 13:46 | claude-haiku-4-5 / claude-sonnet-5 | 91% (84/92) | 92% (37/40) | 57/70 | 4 | 52,370 / 8,559 | 0.190 | 0.757 |
| 06_v4-todo-sonnet | 2026-09-25 13:49 | claude-sonnet-5 / claude-sonnet-5 | 93% (86/92) | 90% (36/40) | 60/70 | 1 | 620,560 / 37,484 | 1.616 | 1.616 |
| 07_v4-repeticion | 2026-09-25 14:01 | claude-haiku-4-5 / claude-haiku-4-5 | 93% (86/92) | 88% (35/40) | 57/70 | 3 | 39,367 / 5,979 | 0.069 | 0.636 |
| 08_v5-ejemplos-limpios | 2026-09-25 14:05 | claude-haiku-4-5 / claude-haiku-4-5 | 95% (87/92) | 88% (35/40) | 59/70 | 4 | 492,805 / 27,483 | 0.630 | 0.630 |
| 09_v6 | 2026-09-25 15:35 | claude-haiku-4-5 / claude-haiku-4-5 | 96% (88/92) | 88% (35/40) | 64/70 | 0 | 529,828 / 27,270 | 0.666 | 0.666 |
| 10_v7 | 2026-09-25 15:38 | claude-haiku-4-5 / claude-haiku-4-5 | 96% (88/92) | 98% (39/40) | 67/70 | 1 | 34,506 / 5,340 | 0.061 | 0.666 |
| 11_v8 | 2026-09-25 15:42 | claude-haiku-4-5 / claude-haiku-4-5 | 96% (88/92) | 98% (39/40) | 66/70 | 0 | 551,847 / 27,096 | 0.687 | 0.687 |
| 12_v9 | 2026-09-25 15:44 | claude-haiku-4-5 / claude-haiku-4-5 | 98% (90/92) | 100% (40/40) | 67/70 | 0 | 51,177 / 5,598 | 0.079 | 0.688 |
| 13_v9-repeticion1 | 2026-09-25 15:45 | claude-haiku-4-5 / claude-haiku-4-5 | 99% (91/92) | 100% (40/40) | 68/70 | 0 | 51,177 / 5,644 | 0.079 | 0.688 |
| 14_v9-repeticion2 | 2026-09-25 15:45 | claude-haiku-4-5 / claude-haiku-4-5 | 98% (90/92) | 100% (40/40) | 67/70 | 0 | 51,177 / 5,644 | 0.079 | 0.688 |
| 15_v10 | 2026-09-25 16:09 | claude-haiku-4-5 (imágenes: claude-sonnet-5) / claude-haiku-4-5, temperatura 0.0 | 100% (92/92) | 100% (40/40) | 69/70 | 0 | 540,208 / 26,879 | 0.768 | 0.784 |
| 16_v10-repeticion1 | 2026-09-25 16:11 | claude-haiku-4-5 (imágenes: claude-sonnet-5) / claude-haiku-4-5, temperatura 0.0 | 100% (92/92) | 100% (40/40) | 69/70 | 0 | 35,038 / 5,377 | 0.062 | 0.784 |
| 17_v10-repeticion2 | 2026-09-25 16:12 | claude-haiku-4-5 (imágenes: claude-sonnet-5) / claude-haiku-4-5, temperatura 0.0 | 100% (92/92) | 100% (40/40) | 69/70 | 0 | 35,038 / 5,382 | 0.062 | 0.784 |
| 18_v10-relectura | 2026-09-25 16:14 | claude-haiku-4-5 (imágenes: claude-sonnet-5) / claude-haiku-4-5, temperatura 0.0 | 99% (91/92) | 100% (40/40) | 68/70 | 0 | 545,333 / 27,860 | 0.787 | 0.787 |
| 19_v11-final | 2026-09-25 16:18 | claude-haiku-4-5 (imágenes: claude-sonnet-5) / claude-haiku-4-5, temperatura 0.0 | 99% (91/92) | 100% (40/40) | 68/70 | 0 | 35,369 / 5,488 | 0.063 | 0.787 |

(*) Lectura completa de los 128 documentos (medida en la corrida que la hizo) más la conciliación de esa corrida. Las corridas 03 a 05 y 07 reutilizaron la lectura de la 02 desde el cache, por eso gastaron mucho menos. La prueba de humo con 5 documentos (US$ 0,049) no se publica.

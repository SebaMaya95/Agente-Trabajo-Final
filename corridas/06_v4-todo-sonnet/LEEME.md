# Corrida 06_v4-todo-sonnet

- **Fecha:** 2026-09-25 13:49:29
- **Modelos:** lector `claude-sonnet-5` / conciliador `claude-sonnet-5`
- **Prompts usados:** `prompts_usados/` (plantillas; los datos de la empresa se completan desde un archivo privado)

## Entrada
- El extracto del banco del mes (143 movimientos, saldos omitidos): `../entrada_extracto_202608.csv`
- Lo que el lector extrajo de cada uno de los 128 documentos (los PDF y las fotos no se publican): `lecturas_documentos.json`

## Salida
- Una fila por movimiento, con estado (color), Detalle, N° de comprobante, documentos vinculados, confianza y motivo: `resultado.csv`
- Lo mismo en JSON, con la metadata de la corrida (cantidad de movimientos resueltos por regla y enviados al modelo, control de saldo, tokens y costo): `salida.json`
- Tokens de entrada y salida de cada llamada a la API: `llamadas.json`

## Evaluación contra el cierre manual
- N° de comprobante exacto: 93% (86/92) · Detalle (celdas validadas): 90% (36/40) · documentos bien vinculados: 60/70
- Cada error, uno por uno, con lo que decidió el agente y lo esperado: `evaluacion.json`
- Costo de esta corrida: US$ 1.616 (620,560 tokens de entrada y 37,484 de salida). Contexto y advertencias: `../RESUMEN.md` y `DECISIONES.md` del repositorio.

*Anonimizada: nombres, CUIT, cuentas, direcciones y saldos reemplazados; importes, fechas y números de comprobante reales.*

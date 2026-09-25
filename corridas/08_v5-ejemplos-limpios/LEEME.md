# Corrida 08_v5-ejemplos-limpios

- **Fecha:** 2026-09-25 14:05:33
- **Modelos:** lector `claude-haiku-4-5` / conciliador `claude-haiku-4-5`
- **Prompts usados:** `prompts_usados/` (plantillas; los datos de la empresa se completan desde un archivo privado)

## Entrada
- El extracto del banco del mes (143 movimientos, saldos omitidos): `../entrada_extracto_202608.csv`
- Lo que el lector extrajo de cada uno de los 128 documentos (los PDF y las fotos no se publican): `lecturas_documentos.json`

## Salida
- Una fila por movimiento, con estado (color), Detalle, N° de comprobante, documentos vinculados, confianza y motivo: `resultado.csv`
- Lo mismo en JSON, con la metadata de la corrida (cantidad de movimientos resueltos por regla y enviados al modelo, control de saldo, tokens y costo): `salida.json`
- Tokens de entrada y salida de cada llamada a la API: `llamadas.json`

## Evaluación contra el cierre manual
- N° de comprobante exacto: 95% (87/92) · Detalle (celdas validadas): 88% (35/40) · documentos bien vinculados: 59/70
- Cada error, uno por uno, con lo que decidió el agente y lo esperado: `evaluacion.json`
- Costo de esta corrida: US$ 0.630 (492,805 tokens de entrada y 27,483 de salida). Contexto y advertencias: `../RESUMEN.md` y `DECISIONES.md` del repositorio.

*Anonimizada: nombres, CUIT, cuentas, direcciones y saldos reemplazados; importes, fechas y números de comprobante reales.*

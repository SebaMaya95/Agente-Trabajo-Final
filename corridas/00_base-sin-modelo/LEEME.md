# Corrida 00_base-sin-modelo

- **Fecha:** 2026-09-25 13:07:31
- **Modelos:** lector `ninguno (solo código)` / conciliador `ninguno (solo código)`
- **Prompts usados:** `prompts_usados/` (plantillas; los datos de la empresa se completan desde un archivo privado)

## Entrada
- El extracto del banco del mes (143 movimientos, saldos omitidos): `../entrada_extracto_202608.csv`
- Ningún documento: esta corrida usa solo código y la Tabla de Referencias.

## Salida
- Una fila por movimiento, con estado (color), Detalle, N° de comprobante, documentos vinculados, confianza y motivo: `resultado.csv`
- Lo mismo en JSON, con la metadata de la corrida (cantidad de movimientos resueltos por regla y enviados al modelo, control de saldo, tokens y costo): `salida.json`
- Tokens de entrada y salida de cada llamada a la API: `llamadas.json`

## Evaluación contra el cierre manual
- N° de comprobante exacto: 22% (20/90) · Detalle (celdas validadas): 84% (32/38) · documentos bien vinculados: 0/68
- Cada error, uno por uno, con lo que decidió el agente y lo esperado: `evaluacion.json`
- Costo de esta corrida: US$ 0.000 (0 tokens de entrada y 0 de salida). Contexto y advertencias: `../RESUMEN.md` y `DECISIONES.md` del repositorio.

*Anonimizada: nombres, CUIT, cuentas, direcciones y saldos reemplazados; importes, fechas y números de comprobante reales.*

# Gobierno y riesgo

## 1. Qué sistemas toca el agente y con qué permisos

| Sistema | Qué hace el agente | Permiso |
|---|---|---|
| Extracto del banco (archivo descargado a mano) | Lo lee | Solo lectura. **No se conecta al banco**: no tiene credenciales bancarias ni puede mover dinero. |
| Carpeta de comprobantes (PDF, imágenes) | Los lee | Solo lectura. Los originales **nunca se modifican, renombran ni borran**. |
| Tabla de Referencias (Excel con los Detalles ya validados) | La lee como sugerencia | Solo lectura. **El agente no escribe en la tabla**: agregarle filas es una decisión de la persona, después de revisar. |
| Carpeta de salida de la corrida | Escribe el Excel del mes, el reporte por categoría, JSON de trazabilidad y **copias** de los comprobantes con nombre nuevo (más un manifiesto original → nuevo) | Escritura solo en una carpeta nueva por corrida. |
| API de Anthropic | Envía el texto (o imagen) de cada documento, las líneas del extracto que hay que decidir y las sugerencias de la tabla | Salida de datos a un tercero (ver punto 5). La clave vive en un archivo local fuera del repositorio. |
| Correo, mensajería, sistemas contables, AFIP/ARCA | **Nada.** No tiene acceso. | Sin acceso. |

Consecuencia de diseño: lo peor que puede hacer el agente por sí mismo es dejar un Excel mal completado en una carpeta nueva. No puede pagar, presentar, enviar ni borrar nada.

## 2. Niveles de autonomía (vocabulario L0–L4)

Escala usada: **L0** sin agente (manual) · **L1** el agente sugiere y la persona hace · **L2** el agente hace y la persona revisa todo · **L3** el agente hace y la persona revisa por excepción y por muestreo · **L4** el agente hace solo y se lo audita a posteriori.

| Decisión | Quién la toma | Nivel |
|---|---|---|
| Marcar cargos automáticos del banco (impuesto a los débitos y créditos, comisiones, IVA bancario) como "gris" | Código, regla fija | **L4** |
| Asignar Detalle por coincidencia exacta con la tabla; período `MM-AAAA` en retiros y haberes | Código | **L3**: se revisa por muestreo |
| Vincular comprobante y proponer Detalle con confianza *alta* | Modelo + reglas de código | **L3**: la persona revisa una muestra de las "altas" |
| Filas amarillas, naranjas, con confianza media o baja, Detalle "deducido" (celeste), vínculos por suma de facturas o por nombre | Modelo | **L2**: la persona revisa **todas** (hoja "Para revisar") |
| Decidir si un documento de un tercero es un gasto de la empresa | Modelo propone; persona decide | **L1** |
| Agregar filas a la Tabla de Referencias | Persona | **L0** |
| **Firmar el cierre del mes** | **Persona** | **L0**: el agente nunca lo da por final |

## 3. Qué puede salir mal, qué pasa y qué lo frena

| Falla | Qué pasa si ocurre | Qué la frena | Evidencia medida (agosto, versión final) |
|---|---|---|---|
| **Vínculo equivocado**: un comprobante asignado a un movimiento que no es | Se guarda como respaldo un documento que no corresponde; puede llegar a una presentación contable | Importe exacto como señal principal; el modelo no puede citar documentos que no existen; el contrato pide confianza media o baja para los vínculos dudosos (documento de un tercero, sin importe exacto); hoja "Para revisar" | 6 de 60 documentos que no correspondían quedaron vinculados de más (10%); 5 comprobantes distintos del cierre manual sobre 90 evaluables (v5) |
| **Vínculo perdido**: no encuentra un comprobante que existe | La fila queda naranja; la persona lo busca. Es el error más barato | El agente prefiere "no encontré" a forzar (regla del contrato) | 11 de 68 documentos con movimiento no se vincularon o se vincularon a medias (v5) |
| **Número de comprobante inventado o mal leído** | Un dato falso en el registro | El número sale del documento de origen vinculado (no lo escribe el modelo); el período se calcula en código | Los errores encontrados fueron de elección de documento, no de números inventados; 0 identificadores de documento inexistentes en las 7 corridas |
| **Categoría (Detalle) equivocada** | El reporte por categoría distorsiona importes por rubro | La tabla manda y el modelo no la puede reescribir (guarda en código); lo deducido va en celeste; se agrupa aparte lo "sin categorizar" | Detalle exacto 92% sobre celdas validadas (35/38); los errores fueron VEP de impuestos y un retiro de efectivo sin categoría |
| **Fila perdida o mal leída del extracto** | Un movimiento no se concilia | Control automático de integridad: cada saldo debe ser el anterior más el importe | En agosto las 143 filas cuadran |
| **Instrucciones escondidas en un documento** (inyección de instrucciones) | Un PDF que diga "ignorá lo anterior" podría manipular el resultado | Los documentos entran como datos; el modelo no tiene herramientas que ejecuten acciones; la salida se fuerza a un esquema JSON y el código valida ids; una nota de sospecha del lector baja la confianza a *baja* y agrega una alerta | Probado con **un** caso ficticio (`corridas/adversarial/`): 7/7 verificaciones; la prueba encontró que la nota del lector no llegaba al revisor y se corrigió (`DECISIONES.md`, D17). No se probaron ataques sutiles ni documentos falsos con importe real |
| **Fuga de datos de clientes** | Datos personales y financieros públicos en GitHub | Datos reales fuera del repositorio; corridas publicadas anonimizadas; verificador que aborta si queda un nombre real (ver `DECISIONES.md`, D2 y D14) | El verificador frenó la publicación dos veces por falsos positivos; nunca por un nombre real |
| **No determinismo**: la misma entrada puede dar salidas distintas | Un caso ambiguo se resuelve distinto de un mes a otro o entre dos corridas | Los casos ambiguos van a revisión humana; las guardas en código fijan lo que no debe variar (tabla, período, número de comprobante) | Repetir v4 cambió 26 de 143 filas (mayormente de redacción) y ±1 movimiento en las métricas (`DECISIONES.md`, D15) |
| **Sobreconfianza por evaluar con los mismos datos con que se ajustó** | Se cree que el agente acierta 94% en cualquier mes | Está dicho en el README y en `DECISIONES.md` (D12) | Solo hay un mes: la cifra es optimista |
| **Cambio del modelo o de sus precios** | Cambian resultados y costo sin aviso | Modelo fijado por identificador; cada corrida guarda modelo, prompts usados y tokens | Sin incidentes; no se probó otra versión del mismo modelo |
| **Gasto descontrolado** | Una corrida con un error de bucle o documentos enormes | Texto recortado a 6.000 caracteres por documento; imágenes reducidas; tope de `max_tokens`; costo registrado por llamada | El pipeline completo cuesta US$ 0,63 por mes |

## 4. Qué reviso antes de confiar en una salida
1. **Hoja "Para revisar"** del reporte: todas las filas amarillas, naranjas, celestes y con confianza distinta de "alta". Es la lista de trabajo.
2. **Muestreo de las "alta"**: abrir el comprobante de unas 10 filas al azar y comparar importe, emisor y número.
3. **Control de saldo del extracto** en `meta.json` (`control_saldo.cuadra`): si dice `false`, no se confía en nada hasta entender por qué.
4. **Documentos vinculados a más de un movimiento** y **vínculos por suma de facturas**: se abren siempre.
5. **Documentos a nombre de terceros vinculados** (confianza media): se decide si es gasto de la empresa.
6. **Totales por categoría** contra lo que la persona espera de ese mes: un rubro que se dispara suele delatar un Detalle mal asignado.
7. Los Detalles celestes que se aceptan pasan a la Tabla de Referencias (a mano), para que el mes siguiente los resuelva el código.

## 5. Privacidad
- Cada corrida **envía a la API de Anthropic** el contenido de los comprobantes, las líneas del extracto y el nombre y CUIT de la empresa. Es información de clientes del consultor: **hay que contar con la autorización del cliente**, y conviene confirmar la política de retención de datos y de uso para entrenamiento de la cuenta de API (no se verificó al escribir esto).
- La clave de la API está en `datos_privados/.env`, fuera del repositorio y bloqueada por `.gitignore`.
- En el repositorio público no hay PDF, imágenes, Excel ni datos personales: solo código, prompts genéricos, y corridas anonimizadas.

## 6. Quién firma
**La persona que administra y presenta el cierre (el consultor)** firma el resultado, y es quien responde ante el cliente. El agente prepara y propone; nunca da el cierre por final. Para el cliente, la firma corresponde a quien tenga la responsabilidad formal sobre la contabilidad de la empresa.

## 6.b Lo que este documento no puede afirmar
- La medición es de **un solo mes** y las reglas se derivaron de ese mismo mes.
- Los errores del cierre manual (por ejemplo, documentos que no están en la carpeta) pueden hacer que la vara misma sea imperfecta; lo que se encontró se separó como "no reconstruible" (`DECISIONES.md`, D9), pero puede haber más.
- Los documentos adversariales se probaron con un solo caso ficticio y directo (D17); tampoco se probó un segundo cliente.

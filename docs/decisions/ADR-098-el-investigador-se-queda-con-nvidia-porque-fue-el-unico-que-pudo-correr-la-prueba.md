# ADR-098 — El investigador se queda con NVIDIA, porque fue el único que pudo correr la prueba

- Estado: PROPUESTO
- Fecha: 2026-08-27
- Aprobación: la fusión de la PR por el propietario
- Contexto: S2/B1. El propietario pidió «una comparación entre NVIDIA y Google AI
  y decidimos, calidad, precio y todo lo que conlleva»
- Relacionadas: ADR-095 (el atestado), ADR-097 (el plazo por pregunta),
  investigación `docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`

## Contexto y problema

Dos configuraciones declaradas, las dos con clave puesta y las dos atestiguadas
como vivas el mismo día. Dos pasadas reales del banco:

| | pasada 2 | pasada 3 (plazo por pregunta) |
|---|---|---|
| nvidia | contestó las 7 en 5 min 21 s | **MEDIDA: 2/7, 311,7 s** |
| google | 1500 s gastados, cero respuestas | **0 de 7: las siete cortadas a 192 s** |

El criterio pedido era «calidad, precio y todo lo que conlleva». La medición
resolvió antes de llegar a la calidad: **una de las dos no puede ejecutar el
trabajo**.

## Decisión

**El investigador de Sirius usa la configuración NVIDIA**
(`openai:nvidia/nemotron-3-nano-30b-a3b` + `nvidia/llama-nemotron-embed-vl-1b-v2`
contra `https://integrate.api.nvidia.com/v1`).

**Google queda descartado, no vetado.** La condición de revancha, escrita para
que no haga falta discutirla: si su capa gratuita cambia de cuota —o el
propietario decide pagarla—, se relanza el banco tal cual está; si Google
completa las siete preguntas, la comparación de calidad que hoy no pudo
existir se hace de verdad. Hasta entonces, insistir es gastar 25 minutos y
cuota para ver el mismo `cortada=True` siete veces.

### Por qué esto se decide ahora y no tras otra pasada

- Las siete preguntas de Google fallaron **idéntico** (192,0 s exactos las
  siete): no es una pregunta difícil ni un pico, es sistemático.
- No hay plazo mayor que dárselo: dos configuraciones × 1500 s ya rozan el tope
  de 55 min del paso, y el tope del trabajo no puede pasar de 85 min sin romper
  la ventana de tolerancia del contador (§11.2, medido en su día).
- El preflight demuestra que los modelos de Google **responden** a llamadas
  sueltas: el fallo es del régimen sostenido, exactamente lo que el investigador
  necesita y lo que una capa gratuita estrangula.

## Lo que esta decisión NO cierra

**El número de calidad de S2 sigue pendiente.** El 28,6 % de NVIDIA no es la
calidad del modelo: sus cinco fallos son todos `fuentes=0`, o sea DuckDuckGo
devolviendo vacío desde los runners de GitHub (2 búsquedas con resultados de 7).
Con la regla `fuentes > 0` —irrenunciable: sin ella un buscador muerto daba
100 %— cada búsqueda vacía es un suspenso aunque la respuesta sea correcta.

El siguiente paso para el 80 % no es tocar el modelo: es **un buscador que
devuelva fuentes**. `gpt-researcher` 0.15.1 trae varios sin clave de OpenAI ni
Anthropic; el que su propio proyecto usa por defecto (Tavily) tiene capa
gratuita con clave propia. Añadir una clave a los secretos es un acto del
propietario, así que la elección de buscador queda como la única pregunta
abierta, y está hecha en la conversación con las dos opciones medidas.

## Cómo se comprueba

- Las dos pasadas citadas, con sus registros públicos (runs 33079519839 y
  33088012637) y el desglose por pregunta en el registro del trabajo.
- La investigación con caducidad declarada, en `docs/investigaciones/`.
- El atestado del día: los cuatro modelos USABLES antes de gastar cuota.

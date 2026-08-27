# Evidencia — El catálogo tampoco basta

Rama `probar-catalogo`, 27-08-2026. Sin ADR: no hay decisión nueva. Es la
consecuencia directa de lo que la prueba de vida midió en su primera pasada.

## Afirmación

Preguntarle el catálogo al servidor **no es suficiente**. El catálogo dice lo que
el proveedor OFRECE, no lo que ESTA CUENTA PUEDE USAR.

## Comprobación — la primera pasada de la prueba de vida

Los tres modelos estaban en el catálogo. Al usarlos:

```
google   NO RESPONDE gemini-2.5-flash
         -> HTTP 404: "This model models/gemini-2.5-flash is no longer available"
         USABLE      models/gemini-embedding-001

nvidia   NO RESPONDE nvidia/llama-3.1-nemotron-70b-instruct
         -> HTTP 404: "Not found for account 'loE28k...'"
         NO RESPONDE nvidia/llama-3.2-nv-embedqa-1b-v1
         -> HTTP 404: "Not found for account 'loE28k...'"
```

**Uno de cuatro funciona.** Y los dos motivos son distintos, lo que importa:

- Google: el modelo **ya no está disponible**, aunque siga listado.
- NVIDIA: el modelo existe pero **no para esta cuenta** — es cuestión de
  permisos o cuota, no de que el nombre sea viejo.

## La escalera completa, que es lo que se lleva de aquí

Cuatro preguntas distintas, y cada una tumbó a la anterior en menos de un día:

| pregunta | quién la contesta | qué tumbó |
|---|---|---|
| ¿qué modelo pongo? | un documento | tres nombres muertos |
| ¿existe? | el catálogo | `gemini-2.5-flash` figura y no sirve |
| ¿me responde? | una llamada real | uno de cuatro |
| ¿responde BIEN? | el banco de preguntas | **sin medir todavía** |

Cada peldaño cuesta más que el anterior y descarta lo que el anterior no podía
ver. Saltárselos es exactamente lo que costó esta noche.

## Criterio de parada (escrito antes)

- Si probar candidatos costara más que céntimos, no vale: existe para costar
  menos que el fallo que evita. Por eso hay tope y por eso lo barato va primero.
- Si el orden de candidatos fuera arbitrario, tampoco: probar seis al azar de un
  catálogo de 84 es tirar una moneda. Se penalizan los que no son de trabajo
  diario —guard, safety, reward, visión, traducción— y los gigantes.

## Lo que NO hace

No dice cuál es mejor. Dice cuáles responden. La calidad sigue siendo el peldaño
que falta, y es el único que necesita el banco de preguntas.

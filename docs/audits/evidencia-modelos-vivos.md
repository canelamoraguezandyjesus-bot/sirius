# Evidencia — Los modelos, sacados del servidor y no de un papel

Rama `modelos-vivos`, 27-08-2026. Sin ADR: no hay decisión nueva. Es la
aplicación de lo que el preflight midió.

## Afirmación

De los cuatro modelos que `configuraciones.yml` declaraba, **tres no existían**.

## Comprobación — el veredicto del propio servidor

```
===== RESUMEN =====
google   OK     50 modelos
         VIVO    gemini-2.5-flash
         MUERTO  models/text-embedding-004
nvidia   OK     84 modelos
         MUERTO  meta/llama-3.3-70b-instruct
         MUERTO  nvidia/nv-embedqa-e5-v5
```

## Los sustitutos, elegidos del catálogo real

| antes | ahora | por qué éste |
|---|---|---|
| `google_genai:models/text-embedding-004` | `google_genai:models/gemini-embedding-001` | de los tres que Google lista, el único que no es `-2-preview` ni depende de una entrada en disputa entre su índice y su tabla de deprecaciones |
| `openai:meta/llama-3.3-70b-instruct` | `openai:nvidia/llama-3.1-nemotron-70b-instruct` | mismo tamaño (70B) e instruct, para no cambiar dos variables a la vez |
| `openai:nvidia/nv-embedqa-e5-v5` | `openai:nvidia/llama-3.2-nv-embedqa-1b-v1` | sucesor de la misma familia `nv-embedqa`, presente en el catálogo |

Comprobado tras el cambio, leyendo el fichero real:

```
google -> ['gemini-2.5-flash', 'models/gemini-embedding-001']
nvidia -> ['nvidia/llama-3.1-nemotron-70b-instruct', 'nvidia/llama-3.2-nv-embedqa-1b-v1']
```

## Lo que esto NO demuestra

Que estén **en la cuota gratuita** de la cuenta, ni que `gpt-researcher` sepa
hablar con ellos —el de NVIDIA puede exigir `input_type: query/passage`, que una
llamada compatible con OpenAI no manda—. Eso solo se sabe usándolos, y es lo
siguiente. El preflight dice que existen; nada más, y nada menos.

## Nota sobre el método, que es lo que se lleva de aquí

Los cuatro nombres viejos venían de tres documentos escritos en tres momentos
distintos: el plan, el spike I2 y la investigación del 27-08. **Los tres eran
correctos el día que se escribieron.** Incluso los sustitutos que proponía la
investigación más reciente —`llama-nemotron-embed-1b-v2` y `bge-m3`— tampoco
están en el catálogo.

Preguntarle al servidor cuesta trece segundos y no caduca. Un informe cuesta
horas y caduca antes de leerlo.

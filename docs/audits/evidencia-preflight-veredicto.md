# Evidencia — El preflight contesta la pregunta directa

Rama `preflight-veredicto`, 27-08-2026. Sin ADR: no hay decisión de arquitectura
nueva. Es la segunda mitad del instrumento que ya decidió existir en
`evidencia-preflight-investigador.md`, y su sitio es el mismo.

## Afirmación

Con las claves ya puestas, el preflight demostró que **los tres modelos
configurados están muertos** — y aun así hubo que ir a pescarlos al log uno por
uno, porque volcaba el catálogo entero y empujaba fuera de la cola visible justo
la línea que importaba.

## Comprobación

Los catálogos reales, devueltos por los servidores el 27-08-2026:

```
google   HTTP 200   50 modelos   embeddings: gemini-embedding-001,
                                 gemini-embedding-2, gemini-embedding-2-preview
nvidia   HTTP 200   84 modelos   embeddings: embed-qa-4, llama-3.2-nv-embedqa-1b-v1,
                                 llama-nemotron-embed-vl-1b-v2, nemotron-3-embed-1b,
                                 nv-embedqa-mistral-7b-v2, arctic-embed-l,
                                 llama-3.2-nemoretriever-1b-vlm-embed-v1
```

De los cuatro nombres que `configuraciones.yml` declara, **tres no aparecen**:

| configurado | ¿existe? | de dónde salió el nombre |
|---|---|---|
| `google_genai:gemini-2.5-flash` | por confirmar | investigación del 27-08 |
| `google_genai:models/text-embedding-004` | **NO** | investigación del 26-08 |
| `openai:meta/llama-3.3-70b-instruct` | **NO** | plan / spike |
| `openai:nvidia/nv-embedqa-e5-v5` | **NO** | spike I2 |

Y un hallazgo que cierra el argumento: la investigación del 27-08 proponía como
sustitutos `nvidia/llama-nemotron-embed-1b-v2` y `baai/bge-m3`. **Ninguno de los
dos está en el catálogo.** Un informe de un día, con fuentes oficiales, y sus
recomendaciones tampoco sobrevivían al contacto con la API.

La extracción nueva, comprobada en local contra el fichero real:

```
google -> ['gemini-2.5-flash', 'models/text-embedding-004']
nvidia -> ['meta/llama-3.3-70b-instruct', 'nvidia/nv-embedqa-e5-v5']
```

## Descartado con datos: no era la clave ni la cuenta

El propietario preguntó, con razón, si fallaba algo suyo. **No.**

- Una clave inválida devuelve 401 y cero modelos. Las dos devolvieron 200 y
  catálogo completo.
- Una cuenta recortada no listaría los modelos grandes. La de NVIDIA lista
  `nemotron-3-ultra-550b`, `gpt-oss-120b` y `nemotron-4-340b`.
- Si faltara configuración, no habría catálogo que leer.

**La causa es una sola:** los cuatro nombres se copiaron de documentos escritos
en momentos distintos, y un catálogo de modelos se pudre en semanas.

## Criterio de parada (escrito antes de tocar)

- Si la comprobación exigiera mantener una lista de modelos **dentro del guion**,
  no vale: sería una copia que se queda atrás en cuanto alguien toque
  `configuraciones.yml`, y entonces diría «todo bien» apuntando a un muerto. Se
  leen del fichero real.
- Si el resumen no cupiera en la cola de un log, no vale: es lo único que se lee
  sin descargar nada, y ése era el defecto que se venía a corregir.

## Lo que NO hace

Dice si un modelo **existe en el catálogo**, no si está incluido en la cuota
gratuita de la cuenta ni si `gpt-researcher` sabe hablar con él. Eso solo se sabe
usándolo, y va después.

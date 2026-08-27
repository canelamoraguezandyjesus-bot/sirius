# Evidencia — Preflight: preguntarle al servidor en vez de creerle a un informe

Rama `preflight-investigador`, 27-08-2026. No hay decisión de arquitectura nueva
que registrar en un ADR: esto no elige proveedor ni cambia el diseño del
investigador. Es el **instrumento** que tiene que existir antes de poder elegir,
y su sitio es aquí, junto al registro de defectos.

## Afirmación

Los dos modelos de vectorización que `configuraciones.yml` declara están muertos,
y el arnés no tenía forma de enterarse: pregunta a su propia configuración, no al
servidor.

## Comprobación

Verificado en `main` antes de escribir una línea:

```
$ grep -n "EMBEDDING" scripts/investigacion/configuraciones.yml
65:      EMBEDDING: "openai:nvidia/nv-embedqa-e5-v5"
92:      EMBEDDING: "google_genai:models/text-embedding-004"

$ grep -n 'servidor=os.environ' scripts/investigacion/medir_investigador.py
224:        servidor=os.environ.get("OPENAI_BASE_URL", "(por defecto del proveedor)"),
```

La primera línea es la que una investigación externa del 27-08 señala como
retirada por Google en enero; la segunda, como deprecada por NVIDIA. La tercera
es el eco que los refutadores del 26-08 ya habían señalado y que **no se
corrigió** en aquella ronda: el campo que dice «con quién hablé» sale de la
variable que el propio proceso acaba de escribir.

El guion nuevo, ejecutado en local sin claves, informa de la ausencia en vez de
fingir:

```
"hay_clave": false,
"error": "falta GOOGLE_API_KEY en el entorno"
"error": "falta NVIDIA_API_KEY en el entorno"
```

## Criterio de parada (escrito antes de construir)

- **(a)** Si el preflight necesitara instalar `gpt-researcher`, no vale: se está
  comprobando al PROVEEDOR, no a la herramienta, y mezclarlos haría que un fallo
  de la herramienta se leyera como un proveedor caído. Se hizo con la librería
  estándar; no importa nada del paquete.
- **(b)** Si el preflight pudiera salir en verde sin que ningún servidor
  contestara, no vale: sería otra vez el verde que no significa nada. El código
  de salida exige catálogo de los dos.
- **(c)** Si una clave pudiera aparecer en un log, un artefacto o el texto de un
  error, se para. Todo lo que sale pasa por `_sin_clave`, incluido el cuerpo de
  una respuesta HTTP de error.

## Lo que esto NO hace

No elige proveedor ni mide calidad: solo dice qué existe. Tampoco comprueba que
un modelo del catálogo esté **incluido en la cuota gratuita** de la cuenta —eso
solo se sabe usándolo—. Y no valida que `gpt-researcher` sepa hablar con el
modelo que se elija: eso es la comparación, y va después.

## Por qué va antes que la comparación

Porque la alternativa ya se probó y falló: se construyó el banco primero, con
guardianes y mutaciones, y midió dos modelos inexistentes. El instrumento que
dice «esto ya no existe» tenía que ser el primero, no el último.

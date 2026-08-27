# Evidencia — Probar seis al azar no es probar

Rama `mas-candidatos`, 27-08-2026. Sin ADR: corrige el orden de una heurística
que se vio fallar en su primera pasada real.

## Afirmación

La primera pasada de `--probar gemini` gastó su tope de seis candidatos en:

```
candidato no  models/gemini-2.5-computer-use-preview-10-2025
candidato no  models/gemini-2.5-flash
candidato no  models/gemini-2.5-flash-image
candidato no  models/gemini-2.5-flash-lite
candidato no  models/gemini-2.5-flash-native-audio-latest
candidato no  models/gemini-2.5-flash-native-audio-preview-09-2025
```

Seis de la misma familia, tres de ellos de audio, imagen o uso del ordenador.
**El orden alfabético los ponía delante**, así que el tope se agotó antes de
llegar a ninguna familia distinta. Ninguno servía.

Un orden que no distingue el trabajo diario del resto convierte «probar
candidatos» en tirar una moneda seis veces.

## Comprobación

Con el orden corregido, sobre un catálogo de ejemplo:

```
models/gemini-2.0-flash
models/gemini-2.5-flash
models/gemini-2.5-flash-lite
models/gemini-3-flash
models/gemini-3-pro
models/gemini-2.5-computer-use-preview-10-2025   <- ahora al final
models/gemini-2.5-flash-image
models/gemini-2.5-flash-native-audio-latest
```

Los de trabajo delante; audio, imagen, uso del ordenador y previews detrás. Una
preview va al fondo a propósito: puede desaparecer sin aviso, y atarse a ella
sería repetir el defecto que este instrumento existe para cazar.

## Criterio de parada (escrito antes)

- Si al subir el tope el coste dejara de ser céntimos, se para. Cada candidato es
  una llamada de una frase; ocho siguen siendo céntimos.
- Si la heurística tuviera que saber de antemano qué modelo es bueno, no vale:
  eso es lo que mide el banco, no el preflight. Aquí solo se ordena por «esto es
  de trabajo diario» frente a «esto es especial».

## Lo que NO hace

No garantiza encontrar uno usable. Si ninguno responde, la respuesta correcta es
que **esta cuenta no puede usar esa familia**, y eso también es un dato.

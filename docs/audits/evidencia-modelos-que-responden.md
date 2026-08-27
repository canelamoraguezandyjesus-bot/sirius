# Evidencia — Los cuatro que responden, encontrados probándolos

Rama `modelos-que-responden`, 27-08-2026. Sin ADR: no hay decisión nueva; es el
resultado de ejecutar el instrumento.

## Lo que se encontró

**Google — toda la familia 2.5 está muerta, la 3.x responde:**

```
candidato no  models/gemini-2.5-flash
candidato no  models/gemini-2.5-flash-lite
candidato no  models/gemini-2.5-pro
CANDIDATO OK  models/gemini-3.1-flash-lite
CANDIDATO OK  models/gemini-3.5-flash
CANDIDATO OK  models/gemini-3.5-flash-lite
CANDIDATO OK  models/gemini-3.6-flash
CANDIDATO OK  models/gemini-3.7-flash
CANDIDATO OK  models/gemini-embedding-001
CANDIDATO OK  models/gemini-embedding-2
CANDIDATO OK  models/gemini-flash-latest
```

**NVIDIA — la familia `llama-*-nemotron` no responde; la `nemotron-3.x` sí:**

```
candidato no  nvidia/llama-3.1-nemotron-51b-instruct
candidato no  nvidia/llama-3.1-nemotron-70b-instruct
candidato no  nvidia/llama-3.1-nemotron-ultra-253b-v1
candidato no  nvidia/nemotron-3-embed-1b
candidato no  nvidia/nemotron-4-340b-instruct
CANDIDATO OK  nvidia/nemotron-3-nano-30b-a3b
CANDIDATO OK  nvidia/nemotron-3.5-lightning-30b-a3b
CANDIDATO OK  nvidia/nemotron-3-super-120b-a12b
CANDIDATO OK  nvidia/nemotron-3-ultra-550b-a55b
CANDIDATO OK  nvidia/llama-nemotron-embed-vl-1b-v2
```

## Lo elegido, y por qué

| | modelo | motivo |
|---|---|---|
| Google LLM | `gemini-3.5-flash` | escalón «flash» estable. Ni preview ni `-latest`: un alias móvil vuelve a atar la configuración a algo que cambia solo |
| Google vector | `models/gemini-embedding-001` | responde, y es el que ya salía USABLE en la comprobación de configurados |
| NVIDIA LLM | `nvidia/nemotron-3-nano-30b-a3b` | mismo escalón rápido/barato que un «flash», para que la comparación sea de tú a tú. Elegir `super-120b` o `ultra-550b` compararía tamaños distintos y mediría eso |
| NVIDIA vector | `nvidia/llama-nemotron-embed-vl-1b-v2` | **el único vectorizador de NVIDIA que respondió** |

## Un dato incómodo que conviene dejar escrito

`nvidia/llama-nemotron-embed-vl-1b-v2` lleva `vl` de *vision-language*. Responde a
una llamada de vectorización de texto —está medido— pero **no está comprobado que
vectorice texto tan bien como uno pensado solo para texto**. Es el único que hay:
`nemotron-3-embed-1b` no responde para esta cuenta.

Si la comparación sale mal para NVIDIA, **esta es la primera sospecha antes de
culpar al modelo de lenguaje**, y por eso queda anotado aquí y no en la cabeza de
nadie.

## Lo que NO demuestra

Que respondan **bien**. Solo que responden. La calidad es el banco de preguntas, y
es el paso que sigue.

# Evidencia — las tres palancas

Fecha: 2026-08-28. Nota de arranque: `docs/audits/arranque-tres-palancas.md`.
Orden del propietario: «dale con las tres y me traes la comparación».

## Las palancas, con su comprobación

| palanca | cambio | comprobación | mutación vista caer |
|---|---|---|---|
| 1 idioma | `LANGUAGE: "spanish"` + `TOTAL_WORDS: "2500"` en la configuración | `test_el_idioma_y_las_palabras_llegan_al_entorno_del_hijo` (valores parseados Y entorno construido de verdad) | M3 (quitar el idioma) |
| 2 profundo | las órdenes van con `--tipo deep` (el workflow lo declara; el padre lo pasa; el hijo lo usa) | `test_el_tipo_de_informe_llega_al_hijo_...` (argv del hijo real retratado) | M1 (el padre deja de pasarlo) |
| 2b frontera | el BANCO se queda en `research_report` | `test_el_banco_sigue_en_research_report` | M2 (el banco se vuelve profundo) |
| 3 modelo | `nemotron-3-super-120b-a12b` en los tres LLM | prueba de vida VIVA (preflight run 33167996379: `CANDIDATO OK`) + **el banco como puerta final**: si no da 7/7, se vuelve al anterior | — (la puerta es la pasada del banco, no una prueba local) |

Plazos del ejecutor de órdenes: trabajo 45 (≤ 85, guardián del contador en
verde), paso 40, guion 2280 s, hijo 0,9×.

## Un defecto propio, cazado en la misma rama

El aserto de paso que verificaba el cambio de modelo buscaba el nombre viejo en
el TEXTO y mordió mi propio comentario («SUBIDO desde el modelo nano…»),
bloqueando la escritura. Misma familia que los guardianes vacuos ya contados.
Corregido comprobando los VALORES PARSEADOS del YAML, que es lo que la
herramienta lee.

## Candidatos probados en vivo (registro)

- `nvidia/nemotron-3-super-120b-a12b` → `CANDIDATO OK` (elegido: misma familia
  que el medido, el salto más grande con menos riesgo de formato).
- `deepseek-ai/deepseek-v4-*` y `openai/gpt-oss-*` → probados en los runs
  33168004445 y 33168009795; sus artefactos quedan como respaldo si el banco
  suspende al elegido.

## Criterio de parada, revisado

- (a) Presupuesto Tavily: gastado hasta hoy ~150 de 1000 créditos del mes; el
  plan de hoy (1 banco + 1 examen profundo) suma ~100–130 más. Dentro.
- (b) La puerta del banco queda por delante: NADA de esto se usa en una orden
  hasta ver 7/7 con el modelo nuevo.
- (c) Ningún tope > 85. Comprobado por guardián.

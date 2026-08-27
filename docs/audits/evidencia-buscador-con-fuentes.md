# Evidencia — un buscador que devuelva fuentes

Fecha: 2026-08-27. Nota de arranque:
`docs/audits/arranque-buscador-con-fuentes.md` (publicada antes del primer
cambio de código). Decisión: ADR-098.

## Las cuatro preguntas, contestadas ejecutando

| pregunta | prueba | mutación vista caer |
|---|---|---|
| 1a. presente se entrega | `test_la_clave_opcional_presente_llega_al_hijo` (con hijo real que retrata su entorno) | M1: quitar la entrega |
| 1b. ausente no rompe ni avisa | `test_la_clave_opcional_ausente_no_rompe_ni_avisa` | — (queda `medida` y sin la variable) |
| 2. el criterio de parada (a) alcanza a las opcionales | `test_una_clave_opcional_de_openai_o_anthropic_para_el_guion` | M3: quitar la guarda |
| 3. el valor se tapa en la salida | `test_el_valor_de_la_clave_opcional_se_tapa_en_la_salida` | M2: dejar de taparlo |
| 4. las dos configuraciones, el mismo buscador | `test_las_dos_configuraciones_declaran_el_mismo_buscador` | M4: cambiar uno |
| (cable) el workflow pasa la clave | `test_las_claves_entran_por_env_y_solo_las_declaradas` | M5: quitarla del `env:` |

La 1a comprueba dos cosas con una sola llamada real: el retrato del hijo trae
`TAVILY_API_KEY` (llegó) y su valor es `«clave oculta»` (se tapó antes de tocar
el disco). La primera versión de la prueba esperaba el valor crudo y falló
contra el propio tapado: el fallo era de la prueba, no de la pieza, y se
corrigió la prueba.

## Un guardián con el número escrito en dos sitios

`test_las_claves_entran_por_env_y_solo_las_dos_previstas` fijaba a mano el par
NVIDIA/GOOGLE, y añadir la clave opcional lo puso rojo. El conjunto esperado
ahora se DERIVA de `configuraciones.yml` (principales más opcionales): una clave
en el workflow que nadie nombra no la usa nadie, y una nombrada que el workflow
no pasa deja la pieza muerta —que es exactamente lo que M5 demuestra—. El
criterio de parada (a) queda como comprobación aparte y explícita.

## Por qué esto es inerte hasta que exista el secreto

Comprobado en el código instalado de `gpt-researcher` 0.15.1
(`retrievers/tavily/tavily_search.py`): sin `TAVILY_API_KEY`, `get_api_key`
avisa y devuelve cadena vacía, y `search()` captura cualquier excepción y
devuelve `[]`. Con `RETRIEVER="tavily,duckduckgo"`, DuckDuckGo se comporta
exactamente como hoy. El secreto (`SIRIUS_INVESTIGADOR_TAVILY_KEY`) es un acto
del propietario; el paso «Comprobar que hay claves» NO lo exige.

## Criterio de parada

- (a) Tavily no es OpenAI ni Anthropic; y la guarda ahora alcanza también a las
  claves opcionales, con prueba.
- (b) No hay verde sobre pieza ausente: `fuentes > 0` sigue mandando, y la
  medición sin la clave queda como hoy (DuckDuckGo, con sus vacíos contados).
- (c) No hubo segunda ronda de la misma familia.

## Lo que queda escrito y NO se arregla aquí

P1/P2 son preguntas «de memoria» cuyo propósito era distinguir un fallo del
modelo de uno de la búsqueda; con `fuentes > 0`, un fallo de búsqueda las
suspende igual y ese diagnóstico queda anulado. Tocar la regla del acierto es
otra decisión con su propia nota, no un ajuste de pasada.

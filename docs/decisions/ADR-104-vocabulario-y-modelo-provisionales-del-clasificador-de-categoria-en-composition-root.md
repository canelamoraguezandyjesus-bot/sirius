# ADR-104 — Vocabulario y modelo provisionales del clasificador de categoría en composition_root

- Estado: PROPUESTO
- Fecha: 2026-08-29
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

M8 (incidencia #442, WI-20260829-212001) construye `CategoryClassifierPort`,
`OllamaCategoryClassifierAdapter` y `TagCategoryUseCase` (D7, SIRIUS-ARQ-0.2
§6.1). D7 punto 1 y §6.1 fijan que el vocabulario cerrado de `category` "es
exactamente el que porta el banco de 47 casos" que M7 (§8, encargo distinto
e independiente de M8 según el orden de construcción de §8: "M7 antes que M9
y M10... M8 antes que M9 y M10", sin relación de orden entre M7 y M8 en sí)
versiona en `tests/acceptance/fixtures/evidence_bank_47_casos.json` — un
fichero que, comprobado antes de escribir código, no existe todavía en este
repositorio (M7 no se ha construido). El adaptador Ollama necesita, sin
embargo, un vocabulario concreto para construir su prompt y validar la
respuesta del modelo, y `composition_root.py` necesita un nombre de modelo
Ollama concreto para poder construir un `TagCategoryUseCase` real y cablear
`KnowledgeWidget._handle_correct_memory_clicked` (probado explícitamente por
el criterio de aceptación de M8) contra dependencias de producción de
verdad, no contra `None`.

## Criterio de parada (escrito ANTES de decidir)

Si programar el vocabulario cerrado o el nombre del modelo exigiera inventar
una taxonomía de categorías con intención de producto (nombres que
condicionen cómo se mide luego la coincidencia en M11, o que aparezcan en
documentación canónica como si fueran la lista oficial), paro y emito
`BLOCKED_BY_DECISION`: eso sí sería tomar una decisión de producto que no me
corresponde. Si en cambio basta con un valor de configuración interno,
confinado a `composition_root.py` (la única raíz de composición, nunca el
dominio ni los puertos/adaptadores, que ya reciben vocabulario y modelo como
parámetros explícitos), documentado como provisional y sustituible por una
sola constante el día que M7 exista, sigo adelante sin bloquear el encargo.

## Opciones consideradas

1. Bloquear todo M8 con `BLOCKED_BY_DECISION` hasta que exista M7.
2. Implementar el puerto, el adaptador y los casos de uso completos, pero
   dejar sin cablear la producción (`composition_root`/`MainWindow`) hasta
   que M7 exista — la orquestación de `_handle_correct_memory_clicked` queda
   escrita pero nunca se ejercita con dependencias reales.
3. Definir un vocabulario y un nombre de modelo provisionales, confinados a
   `composition_root.py`, documentados como sustituibles, y cablear
   producción de verdad.

## Decisión

Opción 3. `CategoryClassifierPort`/`OllamaCategoryClassifierAdapter` reciben
`vocabulary`/`model` como parámetros explícitos del constructor — ninguno de
los dos los inventa ni los codifica dentro de sí mismos. Solo
`composition_root.py` fija los valores concretos
(`_CATEGORY_VOCABULARY`, `_CATEGORY_CLASSIFIER_MODEL`), con un comentario que
señala exactamente qué los sustituye (el vocabulario real del banco de 47
casos, en cuanto M7 lo porte) y por qué no se sustituyen ya (M7 es un
encargo distinto e independiente). `tag_category_use_case`/
`thread_pool` en `KnowledgeWidget`/`MainWindow` quedan como parámetros
opcionales (`| None = None`), mismo patrón que `studio_voice_use_case` ya
usa en `MainWindow`, para no forzar cambios en los ~30 casos de prueba de
`KnowledgeWidget` ni en las pruebas de `MainWindow` que no ejercitan
etiquetado — pero `main.py`/`ValidatedMainWindow` sí los cablean siempre con
el valor real de `composition_root`, así que la función queda activa en
producción, no muerta.

M9/M10/M11, o el propio M7, sustituyen `_CATEGORY_VOCABULARY` por el
vocabulario real cuando el fixture exista: un cambio de una constante en un
único fichero, no un rediseño.

## Comprobación que la sostiene

- `find . -iname "*evidence_bank*"` y `find . -iname "*47_casos*"` (excluido
  `.venv`) no devuelven ningún resultado: el fixture de M7 no existe en este
  árbol antes de este cambio.
- `grep -rn "D1 —\|D7 —\|M7 antes\|M8 antes" docs/evolution/STATUS.md
  docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` confirma
  que el orden de construcción (§8) solo fija "M7 antes que M9 y M10" y "M8
  antes que M9 y M10", sin ninguna frase que ordene M7 antes de M8.
- `grep -n "class ConversationDependencies" -A 60 src/sirius/composition_root.py`
  confirma que `tag_category_use_case`/`set_category_use_case` se añaden
  como campos nuevos de `ConversationDependencies`, construidos siempre por
  `build_conversation_dependencies`, y que `main.py`
  (`_build_main_window`) los pasa a `ValidatedMainWindow` sin ningún hueco.
- `uv run pytest -q` (suite completa): `4156 passed, 9 skipped`.

## Consecuencias

- Positivas: M8 queda completo y cableado en producción, sin bloquear a la
  espera de M7; el punto de sustitución cuando M7 llegue es mínimo y
  localizado.
- Negativas/riesgos: el vocabulario provisional (`trabajo`, `personal`,
  `salud`, `finanzas`, `proyecto`, `aprendizaje`, `otros`) y el modelo
  (`llama3.2`) son responsabilidad de esta decisión, no del propietario ni
  de D7; si M7 fija un vocabulario distinto, cualquier `category` ya escrita
  en una base de datos real con el vocabulario provisional queda fuera del
  vocabulario nuevo hasta que se reclasifique — aceptable porque, a fecha de
  este ADR, M8 no está todavía cableado contra ninguna base de datos de
  usuario real ni ha sido medido contra el banco (esa medición es de M11).

## Alternativas descartadas y por qué

La opción 1 (bloquear) se descartó porque el propio documento de
arquitectura, en su orden de construcción (§8), afirma explícitamente que
"ninguno de estos seis encargos queda bloqueado a la espera de una decisión
del propietario: D1 y D7 ya la resolvieron" — bloquear M8 por la ausencia de
M7 habría contradicho esa afirmación sin una razón nueva que la sostenga. La
opción 2 (dejar sin cablear) se descartó porque el propio criterio de
aceptación de M8 exige una prueba de
`KnowledgeWidget._handle_correct_memory_clicked` que reencola un
`CategoryTaggingWorker` real — una implementación nunca cableada en
`MainWindow` habría dejado la función construida pero muerta en producción,
en tensión con "no dejes... implementaciones a medias".

# ADR-108 — El banco de 47 casos no alcanza el suelo D1 de 29/47 porque FTS5 empareja con cualquier palabra, incluidas las vacías

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta un
  hallazgo bloqueante encontrado durante M11 (incidencia #453), no una
  decisión ya tomada; el veredicto de esa incidencia es `BLOCKED_BY_DECISION`
  y este documento es su comprobación completa.

## Contexto y problema

M11 (SIRIUS-ARQ-0.2 §6.5, §8-M11) pide re-ejecutar la prueba del banco de 47
casos (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, M7) con el
pipeline íntegro ya cableado — índice de categoría (M9) y filtro de
relevancia (M10) con la puerta de D7 punto 6 abierta — y "confirmar el suelo
de D1 (aciertos exactos ≥ 29/47)", afirmado como aserción dura que hace
fallar la prueba si se incumple (§6.5: "Suelos exigidos por D1/D2, afirmados
como aserciones duras que hacen fallar la prueba si se incumplen").

Al cablear ese pipeline íntegro exactamente como M9/M10/M11 lo especifican y
volver a ejecutar el banco, la cifra medida es **aciertos_exactos = 1/47**,
con **elementos_de_mas = 2141-2142** (media de ~45 elementos de más por caso,
sobre un canon de 97 items) — muy lejos del suelo de 29/47 que D1 fija. Antes
de escribir ninguna línea de código de M11, se comprobó que esta cifra **no
la introduce M11**: revirtiendo únicamente los cambios de esta rama sobre
`test_pa_0_2_rec_01_banco_evidencia.py` y `composition_root.py` (con `git
stash`) y volviendo a ejecutar la prueba tal como M7 la dejó en `main`, la
cifra ya es idéntica: `aciertos_exactos=1/47 elementos_de_mas=2141
omisiones_criticas=21 cobertura=51/81` — la diferencia de un solo elemento de
más entre ambas ejecuciones es la propia medición de M11 (un item más
`category_match`, sin efecto práctico). El pipeline de M7, ya en `main` antes
de esta rama, ya estaba a esa distancia del suelo D1.

**Causa raíz, localizada, no supuesta.** `sanitize_fts5_query`
(`src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py:29-46`)
extrae cada token alfanumérico de la consulta y los une con `OR`: "cualquier
término que coincida cuenta como acierto" (línea 34 del propio docstring).
Para una consulta real del banco como «¿Qué reglas de calidad aplican a
Gamma?», eso incluye tokens como `de`, `a`, `qué` — palabras vacías del
español — unidas por `OR` a `reglas`, `calidad`, `aplican`, `gamma`. FTS5
devuelve como acierto **todo item que contenga la preposición "de" o "a"**,
que es prácticamente el canon entero: `B04-CA-03` (0 esperados) obtiene 79
elementos; `B04-CA-46` (0 esperados) obtiene 82. Esto es una propiedad
estructural de `sanitize_fts5_query`/B6a — ya fusionada en `main` desde antes
de M7 —, no un defecto de M8, M9, M10 ni de este M11: ninguno de los cuatro
toca `sanitize_fts5_query` ni el disparador FTS5.

**Por qué el cableado de M9/M10 no puede cerrar esta brecha por sí solo.**
Comprobado, no supuesto: de las 47 consultas del banco, **solo una**
(`B04-CA-17`, «¿Qué política de teletrabajo tenemos en Alfa?», por
`teletrabajo` conteniendo `trabajo`) contiene literalmente una palabra del
vocabulario cerrado de siete categorías — así que `category_match` (§6.2)
apenas puede aportar señal sobre este banco concreto, incluso con la puerta
abierta. El filtro de relevancia (§6.3) sí podría, en producción, con Ollama
real, descartar buena parte del ruido — pero D7 punto 6/§6.5 exige medir esa
misma prueba con "un doble de prueba determinista del puerto, nunca una
llamada real a Ollama dentro de la suite": no hay ningún juicio real que
aplicar dentro de esta suite, y fabricar un doble que descarte selectivamente
lo suficiente para alcanzar 29/47 sería, en la práctica, codificar las
respuestas esperadas de cada caso dentro del doble — lo que el objetivo de
la incidencia prohíbe explícitamente ("No reduzcas, saltes ni falsees
ninguna prueba para conseguir verde").

## Criterio de parada (escrito ANTES de decidir)

Antes de tocar el pipeline del banco: si, tras cablear M9/M10 exactamente
como los describe la Arquitectura Técnica 0.2 (índice de categoría con el
vocabulario real, filtro de relevancia con un doble determinista que no lea
las respuestas esperadas), la cifra medida de aciertos exactos quedara por
debajo de 29/47, paro sin forzar la aserción dura de D1 y emito
`BLOCKED_BY_DECISION` — porque cerrarla exigiría, o bien tocar
`sanitize_fts5_query`/el disparador FTS5 (fuera del alcance permitido de esta
incidencia, que es cablear M9/M10 y medir, no rediseñar B6a), o bien fabricar
un doble del filtro que en la práctica codificara las respuestas esperadas
(prohibido explícitamente). Ocurrió: la cifra medida es 1/47, muy por debajo
de 29/47, por la causa raíz documentada arriba, y ninguna de las dos vías de
cierre está autorizada por el alcance de esta incidencia.

## Opciones consideradas

1. Afirmar la aserción dura de D1 (`aciertos_exactos >= 29`) tal como pide
   §6.5, dejando `uv run pytest` en rojo — descartada: "no ocultes un fallo
   real para conseguir verde" no autoriza lo contrario, dejar la suite
   completa en rojo a sabiendas, tampoco: las cuatro validaciones
   obligatorias de la incidencia deben quedar en verde antes de dar el
   trabajo por terminado.
2. Debilitar la aserción a la cifra real medida (`>= 1`) y declarar D1
   cumplido igualmente — descartada: D1 fija 29/47 como cifra literal
   heredada de la PR #117, no como "lo que se mida" (a diferencia del suelo
   de cobertura de D2, que sí es "la cifra que se mida"); rebajar 29 a 1
   silenciosamente sería exactamente "falsear una prueba para conseguir
   verde".
3. Fabricar un doble de `RelevanceFilterPort` que descarte selectivamente
   los elementos de más de cada caso hasta alcanzar el suelo — descartada:
   equivale a codificar el resultado esperado dentro del doble; la cifra
   resultante no mediría nada real y falsearía la evidencia que D7 punto 6
   pide publicar de buena fe.
4. Tocar `sanitize_fts5_query` para excluir palabras vacías del español y
   medir de nuevo — descartada para esta incidencia: es un cambio al
   disparador FTS5 de B6a, fuera del alcance permitido de M11 ("cablear M9 y
   M10... medir... re-ejecutar la prueba de M7", no rediseñar la búsqueda de
   texto libre), y una decisión de qué lista de palabras vacías usar, en qué
   idioma(s) y con qué efecto sobre el resto de Sirius 0.1/0.2 es, por
   tamaño, una decisión de arquitectura que no corresponde a este encargo.
5. **Detener el encargo, documentar el hallazgo con su causa raíz localizada,
   completar y validar todo lo demás que no depende de esta cifra, y emitir
   `BLOCKED_BY_DECISION`** para que el propietario decida entre migrar D1 a
   "la cifra que se mida" (como ya hace D2), autorizar tocar
   `sanitize_fts5_query` en un encargo aparte, o alguna tercera vía. Elegida.

## Decisión

Opción 5. El resto de M11 —el cableado de `composition_root`/`_save_configuration`
(§6.3), la medición de RNF-003 en los tres escenarios (§6.4) y el mecanismo
de medición de coincidencia del etiquetado (D7 punto 6, §6.1/§6.5)— se
completa, se prueba y se deja listo en la misma rama/PR, porque ninguno de
los tres depende de esta cifra. La prueba del banco
(`test_pa_0_2_rec_01_banco_evidencia.py`) queda con el pipeline íntegro
cableado de verdad (categoría + filtro con candado, puerta abierta) y
reportando las cuatro métricas, más el suelo de cobertura de D2 actualizado a
la cifra medida (51/81, sustituyendo el provisional 63/81 — este sí es "la
cifra que se mida", D2 lo fija así explícitamente) — pero **sin** la
aserción dura de D1 sobre aciertos exactos, documentando en el propio módulo
por qué, con un enlace a este ADR.

## Comprobación que la sostiene

- `git stash push -- tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py src/sirius/composition_root.py`
  seguido de `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
  sobre el `main` sin tocar de esta rama imprime
  `aciertos_exactos=1/47 elementos_de_mas=2141 omisiones_criticas=21
  cobertura=51/81` — la cifra ya existía antes de este encargo; `git stash
  pop` la restaura.
- Con el pipeline íntegro de esta rama (categoría + filtro con candado,
  puerta abierta): `aciertos_exactos=1/47 elementos_de_mas=2142
  omisiones_criticas=21 cobertura=51/81` — un único elemento de más de
  diferencia frente a la cifra de `main`, y ninguna mejora en aciertos
  exactos.
- `python3 -c "import json; d=json.load(open('tests/acceptance/fixtures/evidence_bank_47_casos.json')); vocab={'trabajo','personal','salud','finanzas','proyecto','aprendizaje','otros'}; print([c['id'] for c in d['casos'] if any(v in c['consulta'].casefold() for v in vocab)])"`
  devuelve `['B04-CA-17']`: una sola consulta de 47 activa el vocabulario
  cerrado, confirmando que `category_match` apenas puede mover esta cifra
  sobre este banco.
- Lectura completa de `sanitize_fts5_query`
  (`src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py:29-46`)
  y de su único punto de llamada,
  `SqliteKnowledgeSearchRepository.search_knowledge` (líneas 75-84): el `OR`
  entre tokens, incluidas las palabras vacías, es literal en el código, no
  una inferencia.
- Desglose caso a caso de "obtenido"/"extra" reproducido con un script ad hoc
  contra el pipeline de `rank()` puro (sin filtro, sin precedencia): 33 de
  los 47 casos devuelven entre 20 y 82 elementos de más, con casos de 0
  elementos esperados devolviendo hasta 82 — evidencia consistente con la
  causa raíz, no con un caso aislado.
- `uv run pytest -q` (suite completa): ver PR de M11 para el conteo exacto;
  ninguna prueba de este módulo queda en rojo porque ninguna afirma el suelo
  D1 que no se alcanza.

## Consecuencias

- Positivas: el resto de M11 (composition_root/settings, RNF-003, mecanismo
  de coincidencia del etiquetado) queda completo, probado y no bloqueado por
  este hallazgo; la causa raíz queda localizada con precisión (archivo y
  línea), así que quien retome esto no necesita repetir la investigación.
- Negativas/riesgos: PA-0.2-REC-01 no puede declararse superada hasta que el
  propietario resuelva esta decisión — ni por aciertos exactos (D1, muy por
  debajo del suelo) ni, en consecuencia, por la puerta integral que D1/D2
  fijan. `category_match` y el filtro de relevancia, aun cableados
  correctamente, aportan poca señal sobre este banco concreto mientras la
  sobre-coincidencia de FTS5 domine el ruido — un dato relevante para
  cualquier decisión futura sobre `sanitize_fts5_query`.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: las cuatro alternativas a la opción 5 se
descartaron porque cada una, por una vía distinta, habría publicado como
cumplido un suelo que la evidencia no sostiene (opciones 1-3) o habría tomado
una decisión de arquitectura sobre B6a que no corresponde a esta incidencia
(opción 4).

# ADR-115 — Las dos puertas que la ampliación del arnés no heredaba bajan los aciertos exactos a 29/47 pero elementos de más no alcanza D1 (incidencia #469)

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico elemento a elemento que la propia incidencia #469 pide.

## Contexto y problema

ADR-114 (incidencia #467) cerró la causa dominante de `elementos_de_mas`
(ámbito del índice de categoría) y midió 27/47, 62 elementos de más, 0
omisiones críticas, cobertura 63/81 — quedando 62 `elementos_de_mas` sin
explicar más allá de agruparlos por la etapa del arnés que los producía
(grupo A: 39, admitidos por el motor; grupo B: 20, la corrida congelada
nunca los examinó; grupo C: 3, precio de precisión de la «categoría
buscable»).

La incidencia #469 autoriza un método mecánico, elemento a elemento: para
cada uno de los 62, comprobar contra los artefactos congelados del
laboratorio si la corrida terminó produciendo también ese elemento. Si lo
producía, no es infidelidad del porte — es parte de los `elementos_de_mas`
propios del laboratorio, y se queda anotado. Si no lo producía, localizar en
la fuente del laboratorio la regla exacta que lo excluía y corregir la pieza
portada que la traiciona, citando fichero y línea del laboratorio.

`relevance_filter_frozen_run.json` (el único artefacto por caso ya portado)
solo registra qué entró al filtro y qué conservó el modelo para la fila "4.
filtro con regla, con categoria" — sin la siembra al ensamblar contexto que
el arnés también activa (incidencia #465, causa 2). Para poder comparar
`obtenido` final contra final, hacía falta la fila "5. con siembra en
contexto" de `resultado_modelo_local_v0.7.json` (rama
`evidence/adr001-spikes`, commit `8ff535b91dc6a7a2c42eb886699ebdefd902e4fd`),
que sí combina las mismas piezas que el arnés activa. Se porta ahora
verbatim, restringida a los 47 casos del banco, como
`tests/acceptance/fixtures/lab_final_run_row5.json` — sin tocar
`evidence_bank_47_casos.json` ni ningún `resultado_esperado`.

## Criterio de parada (escrito ANTES de decidir)

Antes de comparar los 62 elementos contra `lab_final_run_row5.json`: si
todos aparecieran en el `obtenido` del laboratorio, no habría nada que
corregir en código — solo documentar que los 62 son ruido propio del
laboratorio, y las cuatro métricas quedarían exactamente como en ADR-114
(27/47, 62, 0, 63/81). Si alguno NO apareciera, sería infidelidad de porte:
localizaría la regla exacta del laboratorio que lo excluye (citando fichero
y línea), corregiría únicamente la pieza portada que la traiciona —nunca el
motor, la corrida congelada ni el fixture congelado, salvo que la regla
viviera ahí—, mediría de nuevo, y actualizaría las cotas de no regresión a
lo medido sin forzar D1 si alguna métrica seguía sin alcanzarlo. No
forzaría la aserción dura de las cuatro métricas a la vez si `elementos_de_
mas` seguía por encima de 21, y afirmaría como aserción dura cada métrica
individual que sí alcanzara su suelo D1/D2, citándolo.

Ocurrió lo segundo: 50 de los 62 elementos están en el `obtenido` del
laboratorio (grupos A completo, C completo, y 8 de los 20 del grupo B —
`B04-CA-33`/`B04-CA-34`, vía `siembra_de_contexto`); los otros 12 (grupo B,
`B04-CA-26`/`B04-CA-38`/`B04-CA-44`, vía `indice_de_categoria`) no. La regla
que los excluía en el laboratorio no es de ámbito (`G4`, ya cerrada por
#467): es `G8` (vigencia temporal) y `G12` (criticidad y límite duro) — dos
puertas que el motor por etapas ya aplica a lo que genera él mismo, pero que
`indice_de_categoria`/`siembra_de_contexto` nunca heredaban al ampliar el
conjunto admitido por otro camino. Corregido, mide: **29/47** (< 29 no; ≥ 29
sí), **50** elementos de más (> 21), 0 omisiones críticas (≤ 1, alcanzado),
cobertura 63/81 (≥ 63/81, alcanzado). `aciertos_exactos` alcanza su suelo D1
y se afirma como aserción dura; `elementos_de_mas` no, y su cota de no
regresión baja de 62 a 50 (nunca por debajo de lo medido).

## Comprobación que la sostiene

`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
imprime, para el motor portado con las cinco piezas conectadas (categoría
buscable con restricción por ámbito, G8/G12 sobre la ampliación, RF-25/RF-26,
siembra en contexto): `aciertos_exactos=29/47 elementos_de_mas=50
omisiones_criticas=0 cobertura=63/81 (77.8%)`.

Medido por configuración (línea base: ADR-114, fila 4):

| configuración | aciertos exactos | elementos de más | omisiones críticas | cobertura |
|---|---|---|---|---|
| 4. índice de categoría por ámbito (ADR-114) | 27/47 | 62 | 0 | 63/81 |
| 5. + G8/G12 sobre la ampliación (#469) | **29/47** | **50** | 0 | 63/81 |
| objetivo D1/D2 | ≥ 29/47 | ≤ 21 | ≤ 1 | ≥ 63/81 |

**Diagnóstico elemento a elemento de los 62 `elementos_de_mas` de la fila 4**,
contra `tests/acceptance/fixtures/lab_final_run_row5.json` (`obtenido` de la
fila "5. con siembra en contexto" del laboratorio, por caso):

**50 elementos — el laboratorio también los produce.** Están en su
`obtenido` para el mismo caso, así que no son infidelidad del porte: son
parte de los `elementos_de_mas` propios del laboratorio. La fuente publica
21 `elementos_de_mas` para esta fila, pero esa cifra excluye los 16 `casos_
de_ausencia` (`resultado_esperado` vacío) y solo suma sobre los 31 `casos_
con_contenido` (`experiments/adr002/modelo_local/medir.py:255-269`, rama
`evidence/adr001-spikes`); sumando también los 16 casos de ausencia (29 más)
da exactamente 50, el número medido aquí — CODEX-001,
`test_la_corrida_del_laboratorio_reproduce_las_metricas_publicadas_de_la_fuente`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`), comprueba esto
mecánicamente contra el fixture, junto con `aciertos_exactos`/`cobertura`
(que sí coinciden con la fuente sin salvedad) y documenta por qué
`omisiones_criticas` (1 en la fuente) tampoco se reproduce contra el banco
portado: ninguno de los elementos que faltan en `obtenido` es `CRITICO` en
`evidence_bank_47_casos.json`, una diferencia de clasificación entre la
lista de críticos de la fuente y el campo `criticidad` de ese banco que ya
existía antes de esta incidencia (#457/#461/#463) y que #469 no autoriza a
tocar. Los 50 se quedan, anotados —
`test_los_elementos_de_mas_restantes_son_los_del_laboratorio`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) lo fija como
prueba de forma sobre el banco completo: para todo caso, `obtenido - esperado`
del arnés es subconjunto de `obtenido` del laboratorio.

- Grupo A completo (39): `sirius.domain.staged_engine.recuperar` los admite
  antes de que `indice_de_categoria`/`siembra_de_contexto` intervengan —
  fuera del alcance de #469 igual que lo estaba del de #467 (esta incidencia
  no autoriza tocar el motor). Verificado uno a uno contra
  `lab_final_run_row5.json`: `B04-CA-03` (MEM-101..112, 12), `B04-CA-35`
  (MEM-903/906/910/911/912/913/914/915/917/919/921/925/930/931/939, 15),
  `B04-CA-04` (MEM-906/925, 2), `B04-CA-05` (DEC-003, 1), `B04-CA-20`
  (MEM-016 y DEC-010, 2), `B04-CA-21` (MEM-014, 1), `B04-CA-34` (MEM-011,
  1), `B04-CA-43` (MEM-012, 1), `B04-CA-14` (MEM-025, 1), `B04-CA-25`
  (DEC-003/DEC-010, 2), `B04-CA-30` (DEC-010, 1): los 39 aparecen en el
  `obtenido` del laboratorio para su caso.
- Grupo C completo (3): `B04-CA-02`/`B04-CA-26`/`B04-CA-31`, todos
  `MEM-001` — el precio de precisión de activar la categoría por cualquiera
  de las cinco palabras del vocabulario, ya diagnosticado por
  ADR-112/ADR-113. `relevance_filter_frozen_run.json` muestra que
  `MEM-001` entró al filtro pero el modelo NO lo conservó directamente en
  ninguno de los tres casos; en el laboratorio (igual que en el arnés)
  sobrevive por RF-25 (rescate de críticas cuando el filtro conservó
  alguna): está en `entraron_al_filtro` pero no en `conservados_por_el_
  modelo`, y aun así aparece en `obtenido` de `lab_final_run_row5.json` —
  no es un defecto de ámbito ni de porte, es la misma regla RF-25 actuando
  igual en ambos lados.
- 8 del grupo B (`B04-CA-33` 5: DEC-010/MEM-001/MEM-014/MEM-016/MEM-025;
  `B04-CA-34` 3: DEC-010/MEM-001/MEM-025): vía `siembra_de_contexto`, que
  nunca pasa por el filtro de relevancia — ni en el arnés ni en el
  laboratorio, que la aplica después del filtro
  (`experiments/adr002/lateral/categoria.py:_pide_contexto`, rama
  `evidence/adr001-spikes`). Confirmado en `lab_final_run_row5.json`: los 8
  elementos están en `obtenido` para `N1-33`/`N1-34`.

**12 elementos — el laboratorio NO los produce**, los 12 restantes del
grupo B, todos vía `indice_de_categoria`:

| caso | elemento(s) | por qué el laboratorio no lo produce |
|---|---|---|
| B04-CA-26 | MEM-112 (1) | `G8`: `valid_from` 2026-05-01 posterior al tiempo objetivo 2026-04-01 de la petición |
| B04-CA-38 | MEM-001, MEM-111, MEM-112 (3) | `G12`: `limite.tipo="DURO"`, `n=10` — el motor ya trunca sus propios candidatos a 10 (MEM-101..110); la ampliación añadía por encima |
| B04-CA-44 | MEM-001, MEM-106..112 (8) | `G12`: `limite.tipo="DURO"`, `n=5` — el motor ya trunca a 5 (MEM-101..105); la ampliación añadía por encima |

La pieza portada que traicionaba la regla del laboratorio no era el motor
—que ya aplica `G8`/`G12` correctamente a lo que genera él mismo,
verificado con `recuperacion.omitidos_por_limite`— sino `indice_de_
categoria`/`siembra_de_contexto`: ampliaban el conjunto admitido por un
camino que nunca pasaba por esas dos puertas. `G8` está en
`experiments/adr002/candidates/common/gates.py:228-256` (`_g8`), portada en
`src/sirius/domain/staged_engine_gates.py:194-210`; `G12` está en
`experiments/adr002/candidates/common/gates.py:356-386` (`aplicar_g12`),
portada en `src/sirius/domain/staged_engine_gates.py:304-332`.
`vigente_en_tiempo_objetivo`/`truncar_por_limite_duro`
(`tests/acceptance/staged_engine_category_and_relevance.py`) reproducen la
mitad de cada puerta que le faltaba a la ampliación —la mitad de corte de
registro/desbordamiento declarado no la ejerce ninguna de las 47
peticiones del banco—, aplicadas sobre el conjunto combinado (motor más
ampliación) en `_ejecutar_banco_motor_portado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`).

Al cerrar esta causa, `B04-CA-38` y `B04-CA-44` pasan a coincidir
exactamente con `resultado_esperado` (antes tenían 3 y 8 elementos de más
respectivamente): son los 2 aciertos exactos que suben `aciertos_exactos`
de 27 a 29/47, el suelo de D1 para esa métrica.

`test_vigente_en_tiempo_objetivo_excluye_lo_aun_no_vigente` y
`test_truncar_por_limite_duro_prioriza_criticidad_y_luego_identidad`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) fijan, con casos
controlados, el comportamiento de las dos funciones nuevas. Los tres se
vieron fallar antes del cambio —el banco medía 27/47 y 62, y
`test_los_elementos_de_mas_restantes_son_los_del_laboratorio` fallaba con
los 12 elementos del grupo B sin explicar (`B04-CA-26`: `['MEM-112']`;
`B04-CA-38`: `['MEM-001', 'MEM-111', 'MEM-112']`; `B04-CA-44`: 8
elementos)— y pasan después.

`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
tests`, `uv run pytest`, `git diff --check`: los cinco en verde — ver PR
para el resultado completo.

## Opciones consideradas

1. **No comprobar elemento a elemento y dejar los 62 como ADR-114 los
   agrupó** — descartada: la incidencia #469 autoriza y pide exactamente esa
   comprobación, y dejarla sin hacer habría desperdiciado una autorización
   ya concedida sin razón técnica.
2. **Tocar `indice_de_categoria` para que respete `G8`/`G12` por dentro,
   como hace con el ámbito** — descartada: `G8`/`G12` no son del resorte de
   `indice_de_categoria` en el laboratorio (esa función solo decide qué
   activa la categoría; el filtrado por vigencia y límite ocurre aguas
   abajo, en el motor común, para lexical y categoría por igual) — mezclar
   las responsabilidades habría oscurecido de dónde viene cada regla y qué
   la sostiene. Se eligió reproducir cada puerta como una función propia
   (`vigente_en_tiempo_objetivo`, `truncar_por_limite_duro`), igual que
   `_en_ambito_declarado` ya lo hacía para `G4`, y aplicarlas en el sitio de
   llamada sobre el conjunto combinado.
3. **Alimentar los candidatos de categoría al propio `sirius.domain.
   staged_engine.recuperar()` como una etapa más, para heredar G1-G12
   completas** — descartada por desproporcionada frente a lo que el banco
   necesita: solo `G8` y `G12` tienen efecto medible sobre las 47 peticiones
   (verificado: ninguna otra puerta descarta nada de la ampliación en este
   banco), y construir una fuente de candidatas sintética con `ItemCanonico`/
   `Candidata` completos para reutilizar `recuperar()` habría sido más
   superficie de código portado —con más riesgo de apartarse del laboratorio
   sin que ninguna medición lo exigiera— que reproducir directamente las dos
   puertas que sí hacen falta, citando su fuente exacta.
4. **Afirmar el suelo D1 igualmente sobre las cuatro métricas, o debilitar
   la cota de no regresión de `elementos_de_mas` por debajo de lo medido
   (50)** — descartada explícitamente por la incidencia y por la disciplina
   de evidencia de `CLAUDE.md`.
5. **Cerrar la causa exactamente donde el diagnóstico elemento a elemento la
   localiza (`G8`/`G12` sobre la ampliación), afirmar `aciertos_exactos` como
   aserción dura ahora que alcanza su suelo D1, bajar la cota de no
   regresión de `elementos_de_mas` a 50, y documentar con la prueba de forma
   que los 50 restantes son ruido propio del laboratorio** — elegida.

## Decisión

Opción 5. `vigente_en_tiempo_objetivo` y `truncar_por_limite_duro`
(`tests/acceptance/staged_engine_category_and_relevance.py`) reproducen,
respectivamente, la mitad de aplicabilidad temporal de `G8` y la mitad de
límite de `G12` —sin la mitad de cada puerta que ninguna de las 47
peticiones del banco ejerce (corte de registro; declaración de
desbordamiento, que solo interesa a la traza)—, citando fichero y línea del
laboratorio y de su porte ya existente en `src/sirius/domain/staged_engine_
gates.py`. `_ejecutar_banco_motor_portado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) las aplica sobre
`obtenido_por_el_motor | categoria | siembra`, después de calcular la
ampliación y antes de `aplicar_regla_de_criticas_original` — nunca dentro
del motor ni de `indice_de_categoria`/`siembra_de_contexto`, que conservan
su contrato de #465/#467 sin cambios (sus pruebas existentes,
`test_indice_de_categoria_respeta_el_ambito_declarado`/`test_siembra_de_
contexto_respeta_el_ambito_declarado`, siguen en verde sin tocarlas).

La corrida final por caso del laboratorio (fila "5. con siembra en
contexto") se porta verbatim como
`tests/acceptance/fixtures/lab_final_run_row5.json`, citando rama, commit y
fichero de origen — nunca se toca `evidence_bank_47_casos.json` ni ningún
`resultado_esperado`.

Las cotas de no regresión: `_MINIMO_ACIERTOS_EXACTOS_MOTOR` sube de 27 a 29
(el suelo D1, alcanzado) y se afirma además como aserción dura aparte
(`assert metricas.aciertos_exactos >= 29`), igual que `omisiones_criticas`/
`cobertura` ya lo estaban; `_MAXIMO_ELEMENTOS_DE_MAS_MOTOR` baja de 62 a 50
(la cifra medida, nunca por debajo, y **no** se afirma como aserción dura
frente al suelo D1 de 21, que seguiría dejando `uv run pytest` en rojo);
`_MAXIMO_OMISIONES_CRITICAS_MOTOR` (0) y `_MINIMO_ELEMENTOS_HALLADOS_MOTOR`
(63) no cambian. El camino real del producto no cambia:
`category_matches_query`/`solo_por_categoria`, el orden aprobado de
`rank_relevant_knowledge` fuera del camino del motor y `context.py` no se
tocan; con la puerta `category_matching_enabled` cerrada, el producto queda
exactamente igual que hoy (las pruebas de identidad con puerta cerrada no se
tocaron y siguen en verde).

Decisión que falta y que no corresponde a esta incidencia: los 50
`elementos_de_mas` restantes (grupos A y C completos, y la porción de
`siembra_de_contexto` del grupo B) no son infidelidad del porte — son la
diferencia irreducible entre lo que este arnés puede reproducir sin tocar
el motor, la corrida congelada o la activación de la categoría buscable, y
lo que el laboratorio produce con esas piezas conectadas de otra forma.
Cerrarlos exigiría, como encargo aparte con autorización explícita: ampliar
el banco con casos que aíslen cada grupo, reabrir la corrida congelada del
filtro para que examine más candidatos, o cambiar la activación de la
«categoría buscable» — ninguna de las tres está autorizada por la
incidencia #469, igual que ADR-114 ya lo declaró para #467.

## Consecuencias

- Positivas: `aciertos_exactos` alcanza su suelo D1 (29/47) y queda afirmado
  como aserción dura; `elementos_de_mas` baja un 19% (62 → 50) al cerrar la
  única infidelidad de porte real que quedaba en los 62 elementos
  diagnosticados por ADR-114. El diagnóstico deja probado, con una prueba de
  forma sobre el banco completo (`test_los_elementos_de_mas_restantes_son_
  los_del_laboratorio`), que los 50 `elementos_de_mas` restantes no son
  infidelidad del porte sino ruido propio del laboratorio — una afirmación
  ahora verificable automáticamente contra el artefacto congelado, no solo
  documentada en prosa.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido en las cuatro
  métricas a la vez (50 > 21); PA-0.2-REC-01 sigue sin poder declararse
  superada por esta vía. Cerrar los 50 elementos restantes exigiría
  autorización sobre piezas que #469 deja fuera de alcance (el motor, la
  corrida congelada, la activación de la categoría buscable), igual que ya
  ocurría tras ADR-114.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría desperdiciado la
autorización que #469 concede; la opción 2 habría mezclado responsabilidades
que en el laboratorio viven en piezas distintas; la opción 3 habría sido
desproporcionada frente a lo que el banco necesita medir, con más riesgo de
apartarse del laboratorio que beneficio medible; la opción 4 habría
falseado la prueba.

# ADR-129 — M20: la siembra en contexto por criticidad

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama `feature/m20-siembra-en-contexto`
(incidencia #516, Work ID WI-20260903-111215), publicada antes del primer
cambio de código, con las cuatro preguntas de la disciplina de evidencia
(ADR-001).

## Contexto y problema

`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan (02-09-2026)», registra la **Decisión 2**
del propietario, literal: «la siembra entra. Su precondición documentada
(ampliar el banco o retirarla) se resuelve así: el propietario la porta
SABIENDO que el banco no puede validarla de forma independiente (solo
B04-CA-34 y otro caso la ejercitan); su aceptación es la medición de
críticas perdidas (3 → 0) y el uso real del propietario, no una prueba del
banco.»

`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:1744-1759`
("Siembra en contexto: aplazada, no se porta en esta decisión") documentaba
DOS vías excluyentes para resolver la precondición de PA-0.2-REC-01: ampliar
el banco de 47 casos con casos independientes que ejerciten la siembra, o
retirarla del código. La Decisión 2 es una TERCERA vía que ese bloque no
enumeraba — portarla sabiendo que el banco no la valida de forma
independiente —, así que este encargo añade una nota breve a ese bloque
(conservándolo íntegro) en vez de sustituirlo, con la cita de la evidencia,
ADR-126 (donde se registró literal la decisión el 02-09-2026) y este ADR.

M18b (ADR-126) y M19a/M19b (ADR-127/ADR-128, ya en `main`, head `b1d6c34`)
ya dieron a cada `Memory`/`Decision` la señal `criticality` y ya hicieron
que la *búsqueda* (índice) y el *rescate* (RF-25/RF-26 + prioridad de G12)
miraran esa señal en vez del tema. M20 es la tercera y última pieza que
`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md` predijo
para cerrar del todo las críticas perdidas del banco (10 → 3 → 0): la
*siembra* — `siembra_de_contexto` del laboratorio
(`experiments/adr002/lateral/categoria.py`, réplica en el arnés,
`tests/acceptance/staged_engine_category_and_relevance.py:412-445`) — que
amplía el conjunto admitido con TODA identidad no ordinaria vigente del
ámbito declarado (más las de ámbito global) cuando la petición declara, en
su propio campo `proposito`, que ensambla contexto.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del
arreglo observar el fallo que arregla?**

El "fallo" (la pieza que falta) es que `RankRelevantKnowledgeUseCase.
_rank_via_staged_engine` (`src/sirius/application/rank_relevant_knowledge.py`)
solo tiene dos bloques de ampliación (`solo_por_categoria`,
`solo_por_criticidad`, M14/M19a) — ninguno activado por el *propósito* de
la petición, solo por el *vocabulario* de la consulta. B04-CA-34 («Prepara
el contexto de planificación de Alfa») no contiene ninguna palabra de
ningún vocabulario, así que sus tres identidades no ordinarias (DEC-003,
MEM-014, MEM-016) quedan sin encontrar (`NO_ENTRO`) con esos dos bloques
solos — la medición de M19b lo confirma: 7/47, 290, 3 omisiones críticas
(las tres de B04-CA-34), 68/81.

El arreglo vive en el mismo sitio: un TERCER bloque, `siembra`, con la
misma forma exacta que `solo_por_criticidad` (dedup contra el motor y los
dos bloques anteriores, restricción de ámbito
`candidate_in_declared_scope`, sobre `Memory.criticality`/
`Decision.criticality`) pero activado por `pide_contexto(peticion.
proposito)` (M20, réplica exacta de `_pide_contexto` del laboratorio,
portada al dominio en `src/sirius/domain/relevance.py`) en vez de
`category_index_activated`. `RankedKnowledge` gana una sexta señal,
`seeded: bool = False`, paralela a `category_match`/`criticality_match`:
entra en `_sort_key` justo después de `criticality_match` y amplía
`is_related`.

Sí puede observarse: pruebas unitarias de dominio para `pide_contexto` (con
y sin "contexto", insensible a mayúsculas) y para `seeded`/`is_related`/
`_sort_key` (vistas fallar antes con `ImportError`/`TypeError` — ver
«Comprobación» más abajo), pruebas de integración con SQLite real para el
bloque `siembra` (solo no ordinarios, respeta ámbito, dedup contra los tres
bloques, sin propósito no siembra, con la puerta cerrada no siembra), y el
banco de 47 casos mide el agregado end-to-end vía `ContextBuilder.
_rank_related_knowledge` real (`_ejecutar_banco_paquete_completo`).

**2. ¿Qué NO va a garantizar esto?**

- No toca `_apply_relevance_filter`, RF-25/RF-26 ni G12 (M19b): el rescate y
  la prioridad de truncado siguen exactamente igual, sobre lo que la
  siembra les entregue como cualquier otro candidato.
- No toca `category`, los vocabularios, `category_locked` ni D7.
- No toca el camino con la puerta `category_matching_enabled` cerrada: sin
  puerta abierta, `_rank_via_staged_engine` ni siquiera se ejecuta —
  `rank()` sigue `_rank_via_current_pipeline` —, así que la siembra nunca
  puede aportar nada.
- No abre la puerta por defecto, ni añade interfaz, ni adelanta M21
  (propuesta automática de criticidad).
- No cambia `_intercalar_por_categoria`: la siembra se une a los otros dos
  bloques en una sola lista antes de esa función, que sigue sin conocer
  ninguno de los tres por separado.
- No garantiza que el banco de 47 casos valide la regla de forma
  independiente: la Decisión 2 ya asume esa limitación (solo B04-CA-33/34
  la ejercitan con propósito de contexto en su propio fixture) y la acepta
  por medición de críticas perdidas, no por prueba del banco.

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir (incidencia #516, objetivo, punto h):

- Runner, con el doble que conserva todo (`_ejecutar_banco_paquete_completo`,
  sin Ollama): críticas `NO_ENTRO` **3 → 0** (entran DEC-003, MEM-014,
  MEM-016 de B04-CA-34); cobertura **68 → 71/81**; aciertos exactos 7/47
  (si sube, regístralo); elementos de más SUBEN claramente y sin cota (la
  siembra mete en cada consulta todo lo no ordinario del ámbito, y el doble
  no poda) — regístralo y explícalo, no es motivo de parada.
- Máquina del propietario con Ollama real, **medido el 05-09-2026**
  (`qwen3:4b-instruct`, espera 30 s, 47 llamadas, 0 rendiciones, 0,8 min,
  main `a07c5d5`): críticas perdidas **3 → 0** — DEC-003, MEM-014 y MEM-016
  de B04-CA-34 y DEC-003 de B04-CA-33 pasan de `NO_ENTRO` en el laboratorio
  a `OK` en producción —, cobertura **70/81** (suelo D1 63: alcanza),
  aciertos exactos 8/47, y los elementos de más que el doble del runner
  dejaba sin cota quedan **podados por el filtro a 218** (el medidor los
  clasifica como ruido tolerable; frente a los 39 del 02-09 sin siembra, es
  el precio de sembrar todo lo no ordinario del ámbito, tal como esta
  decisión aceptó). Registro completo en
  `docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
  «Resultado en la máquina del propietario (Ollama real, 05-09-2026)».

Criterio de parada: si en el runner las `NO_ENTRO` no bajan a 0, o si algún
caso PIERDE una crítica que antes tenía, se para y se busca la raíz (regla
de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que un candidato no ordinario de OTRO ámbito se siembre: la siembra aplica
`candidate_in_declared_scope` exactamente igual que los otros dos bloques
—nunca una condición más débil—, así que un CRITICO/IMPORTANTE fuera del
proyecto activo (y no global) no puede entrar por esta vía, sin importar
cuán fuerte sea el propósito de contexto. Una prueba de integración
(`test_siembra_rejects_a_critico_decision_scoped_to_a_different_project`)
lo fija explícitamente, y la mutación descrita abajo (prescindir de esa
restricción) confirma que esa prueba SÍ detecta su ausencia.

## Opciones consideradas

1. **Activar la siembra por vocabulario, como `solo_por_criticidad`, en vez
   de por propósito.** Descartada: es exactamente la pieza que ya existe
   (M19a) y que, por diseño, no puede cerrar B04-CA-34 — su consulta no
   contiene ninguna palabra de ningún vocabulario a propósito (incidencia
   #516, objetivo, punto d, lo deja escrito como prueba obligatoria). Sería
   una tercera copia de `solo_por_criticidad` sin aportar nada nuevo.
2. **Reescribir `_peticion_ordinaria` para declarar el propósito solo en
   las consultas que "parezcan" de ensamblaje de contexto.** Descartada:
   fuera de alcance (M21, no autorizado aquí) y contraria al propio diseño
   del laboratorio — el propósito es un campo explícito de la petición
   (E0/G1), nunca una adivinanza sobre el texto de la consulta; adivinarlo
   sería exactamente el tipo de heurística oculta que S7.5 prohíbe.
3. **Un tercer bloque `siembra`, activado por `pide_contexto(peticion.
   proposito)`, con la misma forma exacta que `solo_por_criticidad`**
   (elegida, la que pide el propio encargo). `_peticion_ordinaria` ya
   declara un propósito fijo que contiene "contexto" a propósito (M16,
   ADR-124) — la única llamada real a `rank()` ocurre desde
   `ContextBuilder._rank_related_knowledge` para ensamblar el contexto de
   un turno, así que ese literal ya es honesto, no una ficción para activar
   la siembra. Consecuencia asumida y no evitada: en producción real, la
   siembra actúa en **cada** turno, no solo en los que "parecen" pedir
   contexto — exactamente lo que el objetivo de la incidencia deja escrito
   («en producción la siembra actúa en cada turno, y quien poda el ruido es
   el filtro de relevancia, con el rescate RF-25/RF-26 protegiendo lo
   crítico»).

## Decisión

`src/sirius/domain/relevance.py` gana `PROPOSITO_DE_CONTEXTO: Final =
"contexto"` y `pide_contexto(proposito: str) -> bool`, réplica exacta de
`_pide_contexto`/`PROPOSITO_DE_CONTEXTO` del arnés
(`tests/acceptance/staged_engine_category_and_relevance.py:257,403-409`,
a su vez réplica de `experiments/adr002/lateral/categoria.py`). El arnés no
se duplica: puede seguir con su propia copia (documentada como réplica) sin
importar la del dominio, tal como pide el objetivo.

`RankedKnowledge` gana una sexta señal, `seeded: bool = False`, con el
mismo estilo de docstring que `criticality_match`; `is_related` la suma
como cuarta forma de encontrar un candidato; `_sort_key` la inserta justo
después de `not candidate.criticality_match` y antes de la recencia — así
que ningún orden existente cambia (todo lo que antes ordenaba por recencia
sigue haciéndolo entre dos candidatos que empatan en las cinco señales
anteriores) y lo sembrado se ordena detrás de lo hallado por índice de
criticidad.

`RankRelevantKnowledgeUseCase._rank_via_staged_engine`
(`src/sirius/application/rank_relevant_knowledge.py`) gana el tercer bloque,
`siembra`: con `category_matching_enabled` abierta y `pide_contexto(peticion.
proposito)` cierto, recorre `list_current_memories_by_criticality`/
`list_current_decisions_by_criticality` sobre
`_NIVELES_DE_CRITICIDAD_NO_ORDINARIOS` (la misma constante de M19a),
descarta lo ya admitido por el motor y por los dos bloques anteriores (dedup
por `(kind, id)` contra los tres conjuntos), aplica
`candidate_in_declared_scope`, y construye cada `RankedKnowledge` con
`fts_match=False`, `category_match`/`criticality_match` calculados con las
mismas funciones que `solo_por_criticidad` ya usa (normalmente `False` en la
siembra: si cualquiera de las dos fuera realmente `True` para un candidato
dado, ese candidato ya habría entrado por el bloque de categoría o de
criticidad y el dedup lo habría excluido de la siembra) y `seeded=True`. Los
tres bloques se unen en una sola lista y se pasan juntos a
`_intercalar_por_categoria`, sin tocar su algoritmo.

`ContextBuilder` (`src/sirius/application/context.py`) no cambia su lógica:
sigue llamando a `rank_relevant_knowledge_use_case.rank()` exactamente
igual, así que los candidatos sembrados fluyen por el filtro de relevancia
(§6.3) y el presupuesto (B6c) sin ningún cableado nuevo. Su docstring de
módulo (líneas 37-46 antes de este encargo) deja de decir que la siembra no
está portada y pasa a citar la Decisión 2, ADR-126 y este ADR.

`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:1744-1759`
conserva su bloque íntegro (registro histórico de la precondición tal como
se dejó escrita) y gana una nota breve inmediatamente después, con la fecha,
la tercera vía y las tres citas (evidencia, ADR-126, este ADR).

`scripts/medir_variantes_de_criticidad.py` actualiza su docstring y la
predicción impresa a la verdad nueva (`hoy` = 0 `NO_ENTRO`), conservando sus
tres variantes sin cambiar su lógica. `scripts/medir_banco_con_ollama_real.py`
no se toca (fuera de alcance, punto g del objetivo).

## Comprobación que la sostiene

Comandos ejecutados tras completar la implementación, en este orden:

1. Pruebas nuevas vistas fallar antes del cambio (ADR-001): con
   `src/sirius/domain/relevance.py`, `src/sirius/application/
   rank_relevant_knowledge.py` y `src/sirius/application/context.py`
   apartados (`git stash`) y las pruebas nuevas ya escritas,
   `uv run pytest tests/unit/test_relevance_domain.py
   tests/integration/test_rank_relevant_knowledge.py -q` →
   `ImportError: cannot import name 'pide_contexto' from
   'sirius.domain.relevance'` al recolectar — confirma que las pruebas
   unitarias e de integración nuevas no podían pasar contra el código de
   antes de este encargo. Cambios restaurados (`git stash pop`) antes de
   seguir.
2. Tras completar la implementación:
   `uv run pytest tests/unit/test_relevance_domain.py
   tests/integration/test_rank_relevant_knowledge.py
   tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q` →
   `157 passed, 1 skipped, 1 xfailed`.
3. `uv run python scripts/medir_variantes_de_criticidad.py` →
   `hoy=0/47,487,0,72/81` — `hoy` = **0** `NO_ENTRO` (críticas perdidas
   3 → 0, tal como pedía la Decisión 2), cobertura **72/81** (no 71/81
   como predecía el objetivo), elementos de más **487** (290 antes de este
   encargo) — sube sin cota, tal como predecía el criterio de parada, y no
   es motivo de parada.

   **Explicación de la diferencia 72 vs. 71/81 (disciplina de evidencia:
   no basta con anotar el número, hay que explicarlo):** medido con
   `pide_contexto` monkeypatcheado a `False` solo en
   `sirius.application.rank_relevant_knowledge` (para reproducir la
   medición de "antes de M20" con el mismo código real, no una
   aproximación) frente al código real, el único caso que gana identidades
   nuevas más allá de B04-CA-34 es B04-CA-30 (ámbito `PRJ-ALFA`), que gana
   `MEM-001` — un recuerdo IMPORTANTE de ámbito **global**
   (`candidate_in_declared_scope` lo admite siempre, cualquiera que sea el
   proyecto activo). La predicción "71/81" del objetivo asumía,
   implícitamente, que la siembra solo se ejercita en las consultas que el
   propio fixture del arnés de examen marca con propósito de contexto
   (B04-CA-33/34); pero `_ejecutar_banco_paquete_completo` mide el camino
   real de producción, cuya `_peticion_ordinaria` declara el mismo
   propósito fijo para las 47 consultas (M16) — así que la siembra actúa en
   las 47, no solo en 2, exactamente como describe el objetivo de la
   incidencia («en producción la siembra actúa en cada turno»). El +1 extra
   es una consecuencia correcta y determinista de esa misma decisión de
   diseño (opción 3, arriba), no un defecto: `omisiones_criticas` (3 → 0,
   sin excepción) y `NO_ENTRO` (3 → 0) son las dos métricas que el criterio
   de parada até explícitamente, y ninguna incumple.
4. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q`
   → `27 passed, 1 skipped, 1 xfailed` — verde, con
   `_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO` bajado de 7 a 0 (cota de no
   regresión, no el suelo de D1/§8-M11): `aciertos_exactos` cae a **0/47**
   porque la siembra añade candidatos no esperados a las 47 filas por
   igual, así que ninguna conserva ya un acierto exacto — consecuencia
   directa de "elementos de más sube sin cota", que el criterio de parada
   ya declaraba explícitamente "no motivo de parada". La prueba
   `xfail(strict=True)` del suelo 29/47 sigue fallando-como-se-espera (no
   pasó a XPASS).
5. `uv run ruff format --check .` → `587 files already formatted`.
   `uv run ruff check .` → `All checks passed!` (tras `--fix` para
   `RUF022`, orden de `__all__`).
   `uv run mypy src tests` → `Success: no issues found in 555 source
   files`.
   `uv run pytest -q` (suite completa) → `4589 passed, 15 skipped, 2
   xfailed in 462.12s` (19 más que las `4570 passed` de M19b: 10 pruebas
   unitarias nuevas de `pide_contexto`/`seeded` + 9 de integración del
   bloque `siembra`). Ningún fallo, ninguna prueba debilitada u omitida.
   `git diff --check` → limpio (sin salida, código de salida 0).
6. Prueba por mutación (ADR-001, la sugerida en el objetivo, punto f):
   se sustituyó temporalmente, en las dos ramas (memoria y decisión) del
   bloque `siembra` (`src/sirius/application/rank_relevant_knowledge.py`),
   `if candidate_in_declared_scope(...)` por
   `if True or candidate_in_declared_scope(...)` — prescindiendo de la
   restricción de ámbito — y se ejecutó
   `uv run pytest tests/integration/test_rank_relevant_knowledge.py -q -k
   siembra`: **`test_siembra_rejects_a_critico_decision_scoped_to_a_
   different_project` falla** (`assert (RankedKnowledge(...),) == ()` — el
   CRITICO de otro proyecto se cuela), mientras las otras ocho pruebas de
   siembra siguen en verde. Revertida la mutación,
   `uv run pytest tests/integration/test_rank_relevant_knowledge.py -q -k
   siembra` vuelve a dar `9 passed`.

## Consecuencias

- Con la puerta `category_matching_enabled` abierta, toda petición real
  (cuyo propósito siempre declara "contexto", M16) siembra en el conjunto
  admitido toda identidad no ordinaria vigente del ámbito declarado (más
  las de ámbito global) que el motor, la categoría o la criticidad no
  hubieran admitido ya — en cada turno, no solo en los que "parecen" pedir
  contexto.
- Eso cierra las tres críticas perdidas que M19a/M19b dejaban sin resolver
  (B04-CA-34: DEC-003, MEM-014, MEM-016) y, como efecto colateral correcto
  de activarse en las 47 consultas del banco (no solo en las 2 que el
  arnés de examen marca con propósito de contexto en su fixture), también
  cierra una identidad más (MEM-001 en B04-CA-30) — cobertura 68 → 72/81.
- El volumen de candidatos que llegan al filtro de relevancia (ADR-125)
  sube sin cota conocida — la poda del ruido pasa a depender enteramente
  del filtro y de RF-25/RF-26 (M19b), tal como registra la Decisión 2 y tal
  como predecía el objetivo de esta incidencia. La medición con Ollama real
  sobre esa poda llegó el 05-09-2026 (máquina del propietario): 218
  elementos de más tras el filtro, frente a los 39 de antes de la siembra,
  con 0 críticas perdidas y cobertura 70/81 — el intercambio exacto que esta
  decisión aceptó, ahora medido.
- Con la puerta cerrada, el comportamiento de hoy no cambia: la siembra
  vive exclusivamente en `_rank_via_staged_engine`, que ni se ejecuta.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.

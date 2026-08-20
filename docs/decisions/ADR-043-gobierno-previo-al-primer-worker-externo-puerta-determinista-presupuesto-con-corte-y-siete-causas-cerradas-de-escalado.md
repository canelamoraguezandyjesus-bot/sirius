# ADR-043 — Gobierno previo al primer Worker externo: puerta determinista, presupuesto con corte y siete causas cerradas de escalado

- Estado: APROBADO — por la fusión de la PR que acompaña a esta rama.
- Fecha: 2026-08-19
- Aprobación: la fusión de la PR de este bloque (A5, incidencia #206) por el propietario.
- Este documento ES la nota de arranque de la rama (skill `disciplina-evidencia`):
  publicada aquí, no como comentario en la incidencia, porque el contrato de
  ejecución de esta ronda («implementador genérico de Sirius», incidencia #206)
  restringe los comentarios de la incidencia a un único texto fijo
  (`PR abierta: <URL>`). El ADR es el lugar visible que sí queda disponible —
  mismo patrón que ADR-039 (A4) sobre la incidencia #202.

## Contexto y problema

La incidencia #206 (SIRIUS-WORK-ENGINE-A5-001) pide el último bloque de la
Fase A del Work Engine: la Capa 1 de interacción (conversar/consultar/explorar
sin crear WorkItem, apoyada en `contexto.recuperar` de A3) y el gobierno que
ningún Worker externo puede estrenarse sin él (presupuesto con corte
determinista, `NEEDS_DECISION` con la lista cerrada de siete causas de
arquitectura §10, escalado y notificación), más la creación/activación del
WorkItem con la autoridad que fija el contrato v1.7 §11 (ADR-041, ya fusionado)
y una interfaz v0 de sesión/CLI sin estado propio.

Hoy nada de esto existe como código: A1-A4 dan el núcleo del motor, el espejo
de solo lectura y los perfiles/permisos/egress, pero ningún camino convierte
una intención en un WorkItem activado, y no hay ninguna noción de presupuesto
que corte ni de escalado con causa cerrada. La arquitectura mínima (§8.5,
§9, §10) ya especifica la forma; A5 la construye.

**Corrección sobre el primer commit de esta rama (autocorrección, no un
hallazgo de revisor)**: el primer commit de esta rama afirmaba que
`src/sirius_engine/context_recall.py:95` (`except UnicodeDecodeError,
OSError:`) era un `SyntaxError` -sintaxis de Python 2- y lo "corregía"
envolviéndolo en paréntesis. Esa afirmación era falsa, y la causa es
exactamente la que ADR-001 pide nombrar sin suavizar: la comprobación se hizo
con el `python3` del sistema (3.12), no con `uv run python` (el intérprete
real del proyecto, fijado en 3.14 por `requires-python = ">=3.14,<3.15"` en
`pyproject.toml`). Python 3.14 incorpora PEP 758, que permite exactamente
`except A, B:` sin paréntesis; `ruff format` (con `target-version = "py314"`
en este repositorio) lo trata como la forma canónica y **deshace** la versión
con paréntesis al reformatear -que es la señal que expuso el error: el fichero
"se revertía solo" tras `ruff format .`, y no era una regresión externa sino
`ruff` corrigiendo una desviación de estilo que yo mismo había introducido.
Verificado con el intérprete correcto:

```
$ uv run python --version
Python 3.14.6
$ uv run python -c "compile('try:\n pass\nexcept ValueError, TypeError:\n pass\n', '<t>', 'exec')"
(sin error: la sintaxis sin paréntesis es válida)
```

Revertido a la forma original (`except UnicodeDecodeError, OSError:`) en el
commit que sigue a este; `ruff format --check`, `ruff check`, `mypy` y
`pytest tests/engine/test_context_recall.py` en verde sobre el fichero
intacto. Ningún otro fichero de este bloque se vio afectado por el error de
diagnóstico. Se deja constancia aquí en vez de silenciarlo, como pide
`disciplina-evidencia` §4 sobre verificar antes de aceptar cualquier
afirmación -incluida la propia.

## Criterio de parada (escrito ANTES de decidir)

Publicado antes de tocar código nuevo, siguiendo el método de la skill
`disciplina-evidencia`:

1. **¿Dónde vive el fallo (la ausencia) y dónde va el arreglo? ¿Puede el
   sitio del arreglo OBSERVAR lo que soluciona?**
   - (Nota posterior: el primer commit de esta rama afirmó aquí un
     `SyntaxError` en `context_recall.py` que no existía -ver la sección
     «Contexto y problema» arriba para la corrección completa. Se deja el
     resto de este criterio de parada como se publicó, sin retocar la
     redacción original, salvo esta nota.)
   - La ausencia de gobierno (puerta, presupuesto, escalado): vive fuera de
     `src/sirius_engine/` en el sentido de que hoy NO EXISTE ningún camino que
     convierta una intención en trabajo gobernado; el arreglo es código nuevo
     dentro de `src/sirius_engine/`, que sí puede observar lo que debe
     igualar — las cinco pruebas de terminado de la incidencia (A5-P1..P5)
     ejercitan el comportamiento contra el almacén real (`WorkEngineStore`,
     ambas implementaciones vía `conftest.py`), no una copia simulada de él.
2. **¿Qué NO va a garantizar esto?**
   - No garantiza interpretación de intención por modelo real: el
     clasificador v0 (`intent_interpreter.py`) es una heurística determinista
     de marcador de posición (verbos imperativos, marcadores de pregunta,
     palabras clave de sensibilidad), documentada como tal. La arquitectura
     (§11) marca "interpretar intención" como algo que "necesita modelo": ese
     modelo real es trabajo futuro que sustituye este v0 sin cambiar la
     puerta determinista que lo consume.
   - No garantiza que las siete causas cubran todo lo que un revisor humano
     consideraría "sensible": la detección de palabras clave es
     necesariamente incompleta; lo que sí garantiza es que la lista de
     causas *posibles* está cerrada a siete y no crece por accidente.
   - No garantiza persistencia del presupuesto entre reinicios del proceso:
     el `Budget` es un valor explícito que el llamador conserva y pasa entre
     invocaciones (mismo patrón que `now`/`deadline` en todo el motor — nunca
     leído de un reloj ni de un estado oculto). Persistirlo de verdad es
     trabajo de un futuro adaptador, no de este bloque.
   - No calcula un `PermissionEnvelope` por cada WorkItem creado: ese cómputo
     sigue siendo del despachador real (C2/B1), que conoce el perfil
     concreto del paso; A5 solo dispone la maquinaria de A4 para cuando haga
     falta, no la fuerza sobre clases que todavía no tienen perfil (v.g.
     investigación, documentación).
   - No escribe nada en GitHub ni activa ningún Worker externo (alcance de
     la incidencia).
3. **Criterio de parada, decidido ahora:**
   - Si la puerta determinista necesitara consultar a un modelo en su camino
     crítico (no en la clasificación previa, sino en la decisión misma de
     crear/activar/escalar), me detengo con `BLOCKED_BY_DECISION`: la
     incidencia lo prohíbe explícitamente.
   - Si asignar autoridad a una clase de trabajo exigiera una fila no
     escrita en el contrato §11.1 de forma ambigua e irresoluble sin
     inventar producto, me detengo con `BLOCKED_BY_DECISION`. (Nota: las
     clases `consulta-larga` y `mixta` no aparecen nombradas explícitamente
     en la tabla del contrato; se resuelve por defecto conservador —
     autoridad `motor`, la misma que las demás clases nativas sin
     proyección GitHub— documentado en la sección Decisión, no bloqueante.)
   - Si hiciera falta una dependencia nueva, me detengo con
     `BLOCKED_BY_DECISION`.
   - Dos rondas de revisión propia con defectos de la misma familia → paro,
     busco la raíz en vez de seguir parcheando.
   - Cierro con `READY_FOR_REVIEW` solo si las cinco pruebas de terminado
     (A5-P1..P5) están en verde, las tres mutaciones sembradas exigidas por
     la incidencia fallan como se espera, y las cuatro validaciones
     obligatorias + `git diff --check` + `tests/engine/test_boundary.py`
     (sin tocarlo) están en verde.
4. **¿Qué hace el fallo IMPOSIBLE en vez de improbable?**
   - Orden inequívoca pidiendo confirmación: `CrearYActivar` (la decisión de
     la puerta para ese caso) no tiene ningún parámetro de confirmación ni
     punto de espera; quien la consume llama directamente a
     `create_work_item` + `activate_work_item`, sin ninguna rama intermedia.
   - Presupuesto agotado que no corta: `registrar_gasto` es la ÚNICA función
     que actualiza el consumo, y siempre devuelve si el resultado quedó
     agotado; no existe otra vía para gastar sin pasar por ella.
   - Causa de escalado fuera de las siete: `CausaEscalado` es un `StrEnum`
     cerrado; una prueba compara `frozenset(CausaEscalado)` contra una lista
     literal de siete cadenas escrita de forma independiente en el test (no
     derivada del propio enum), así que añadir un octavo miembro sin darse
     cuenta se detecta estructuralmente.
   - Fallo técnico corregible que escala: la única función que produce
     `NEEDS_DECISION` es `escalar_con_causa`, y exige una `CausaEscalado`
     como argumento obligatorio (no opcional, no inferible) — un fallo
     técnico se resuelve con `resolver_fallo_tecnico`, que llama a
     `fail_work_item_safely`, un camino del dominio que nunca produce
     `NEEDS_DECISION`.

## Opciones consideradas

**Dónde vive el consumo de presupuesto:**

1. Dentro de `WorkItem.limites`, actualizado vía `change_work_item_scope`.
2. Como valor externo explícito (`Budget`), pasado por el llamador igual que
   `now`.

**Cómo se clasifica la intención sin modelo real:**

1. Exigir que el llamador ya entregue la intención pre-clasificada
   (`IntentSignal` construido a mano), sin ningún clasificador de texto libre.
2. Un clasificador heurístico v0 mínimo, documentado como marcador de
   posición del futuro intérprete con modelo.

**Autoridad para las clases sin fila explícita en el contrato
(`consulta-larga`, `mixta`):**

1. Bloquear y pedir decisión del propietario.
2. Adoptar el valor por defecto conservador `motor` (igual que las demás
   clases sin proyección GitHub), documentado explícitamente como
   interpretación, no como ampliación de la tabla aprobada.

## Decisión

**Presupuesto: opción 2 (valor externo explícito).** `change_work_item_scope`
(`adapters/memory_store.py` / `adapters/durable/store.py`) cancela o invalida
TODOS los Runs vivos del WorkItem como efecto colateral de cualquier cambio de
`limites` (arquitectura §3.2: "Si el cambio invalida Runs vivos, el motor los
cancela primero"). Reutilizarlo para registrar un gasto ordinario destruiría
en el acto el propio Run cuyo coste se está contabilizando — el efecto
colateral existe para cambios reales de alcance (p. ej., que el propietario
amplíe el presupuesto), no para la contabilidad rutinaria de consumo. Por eso
el consumo vive en un valor `Budget` externo, explícito, con la misma
disciplina que `now`: nunca leído de un estado oculto. El LÍMITE declarado sí
vive en `WorkItem.limites["presupuesto"]["limite"]` en el momento de la
creación (dato del WorkItem, §3.1); ampliarlo de verdad —una decisión
material— sí pasa por `change_work_item_scope`, correctamente.

**Clasificación de intención: opción 2 (heurística v0 documentada).** Sin
ella, "interfaz v0: sesión/CLI" (entrega 5 de la incidencia) no podría
demostrarse con texto libre, y las pruebas de terminado hablan explícitamente
de «una conversación», «una orden inequívoca», «una petición ambigua» — texto,
no estructuras ya clasificadas. Se mantiene deliberadamente pequeña (patrones
léxicos, sin dependencia nueva) para no fingir una capacidad de comprensión
que no tiene.

**Autoridad para clases sin fila explícita: opción 2 (motor, por defecto
conservador).** No es una ampliación de la tabla aprobada (ADR-041, contrato
§11.1): es la lectura más conservadora posible de una tabla que se declara
"sin huecos" pero cuyo texto no nombra las dos clases nativas
`consulta-larga`/`mixta` una por una. Ninguna de las dos tiene proyección en
GitHub definida en ningún documento — el mismo hecho que hace `motor` la
autoridad de `investigación` y `documental no publicada` — así que aplicar el
mismo criterio no inventa una decisión de producto nueva, solo completa un
patrón ya aprobado. Si el propietario quisiera lo contrario, es una
corrección de una fila, no un rediseño.

Componentes nuevos, dentro de `src/sirius_engine/` y `tests/engine/`:

- **`domain/budget.py`**: `Budget` (límite/consumido, inmutable) y
  `BudgetExhaustedError`.
- **`domain/escalation.py`**: `CausaEscalado` (las siete causas cerradas de
  arquitectura §10) y `Escalada` (instantánea completa del WorkItem + causa +
  referencias, para que "decidir sin reconstruir nada" sea una propiedad
  verificable).
- **`domain/authority.py`**: `Autoridad` (`motor`/`incidencia`) y
  `autoridad_de_clase`, función total sobre `WorkItemClass` (contrato §11.1).
- **`domain/intent.py`**: `TipoIntencion`, `IntentSignal`,
  `DatosNuevoTrabajo` — la forma de una intención ya clasificada.
- **`intent_interpreter.py`**: `interpretar_intencion_v0` — heurística
  determinista de texto libre a `IntentSignal`.
- **`gate.py`**: `decidir` (la puerta determinista, arquitectura §8.5) — las
  tres salidas (`NO_CREAR`/`CREAR_Y_ACTIVAR`/`CREAR_Y_ESCALAR`) y ninguna más.
- **`work_intake.py`**: `aplicar_decision` — la creación/activación (o
  creación/escalado) real contra el `WorkEngineStore`, con la autoridad de
  la clase calculada y devuelta en el mismo movimiento.
- **`governance.py`**: `registrar_gasto` (corte determinista) y
  `resolver_fallo_tecnico` (nunca escala).
- **`ports/notification.py`** + **`adapters/cli_notification.py`**: el canal
  de notificación v0.
- **`session.py`**: `SesionCLI` — la interfaz v0, sin estado propio: cada
  turno se resuelve con lo que el llamador inyecta (almacén, presupuesto,
  notificador), sin caché ni historial retenido entre turnos más allá de lo
  que el propio almacén y `contexto.recuperar` ya dan.

## Comprobación que la sostiene

Las cuatro validaciones obligatorias, en verde sobre el repositorio completo
(intérprete real del proyecto, `uv run`, Python 3.14.6):

```
$ uv run ruff format --check .
429 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 410 source files

$ QT_QPA_PLATFORM=offscreen uv run pytest -q
2813 passed, 6 skipped in 268.91s (0:04:28)

$ git diff --check
$ git diff --cached --check
(sin salida; exit 0)

$ uv run pytest tests/engine/test_boundary.py -q   # sin modificarlo
2 passed in 0.24s
```

Las cinco pruebas de terminado, mapeadas a sus ficheros:

- **A5-P1** (conversar/consultar el pasado en varios turnos no crea
  WorkItem): `tests/engine/test_session.py::test_conversacion_de_varios_turnos_no_crea_ningun_workitem`
  y `test_una_conversacion_larga_intercalada_con_una_orden_solo_crea_ese_workitem`.
- **A5-P2** (orden inequívoca crea y activa sin segunda confirmación):
  `tests/engine/test_gate.py::test_orden_inequivoca_crea_y_activa_sin_ningun_campo_de_confirmacion`,
  `tests/engine/test_work_intake.py::test_crear_y_activar_no_pide_ninguna_confirmacion_intermedia`,
  `tests/engine/test_session.py::test_orden_inequivoca_crea_y_activa_sin_segunda_confirmacion`.
- **A5-P3** (petición ambigua no crea trabajo):
  `tests/engine/test_gate.py::test_tipos_sin_trabajo_nunca_crean_nada`,
  `tests/engine/test_session.py::test_peticion_ambigua_no_crea_trabajo`.
- **A5-P4** (presupuesto agotado corta el Run y produce `NEEDS_DECISION` con
  notificación, visto fallar con el corte desactivado):
  `tests/engine/test_governance.py::test_agotar_el_presupuesto_corta_el_run_y_escala_con_notificacion`.
- **A5-P5** (lista cerrada de siete causas, las dos direcciones):
  `tests/engine/test_escalation.py::test_la_lista_de_causas_es_exactamente_la_cerrada_de_arquitectura_10`
  (positiva: son exactamente esas siete) y
  `tests/engine/test_governance.py::test_fallo_tecnico_corregible_nunca_escala`
  (negativa: un fallo técnico no escala).

**Prueba por mutación (ADR-001 §3), las tres exigidas por la incidencia,
sembradas y vistas fallar, luego revertidas:**

1. Desactivar el corte por presupuesto (`governance.registrar_gasto`: la
   guarda `if not nuevo_presupuesto.agotado:` sustituida por `if True:`) →
   ```
   $ uv run pytest tests/engine/test_governance.py -q
   4 failed, 4 passed in 0.10s
   FAILED test_agotar_el_presupuesto_corta_el_run_y_escala_con_notificacion[_make_in_memory_store]
   FAILED test_agotar_el_presupuesto_corta_el_run_y_escala_con_notificacion[_make_durable_store]
   FAILED test_agotar_por_encima_del_limite_tambien_corta[_make_in_memory_store]
   FAILED test_agotar_por_encima_del_limite_tambien_corta[_make_durable_store]
   ```
   A5-P4 cayó como se esperaba. Revertido con
   `git checkout -- src/sirius_engine/governance.py` (confirmado sin diff).
2. Hacer que la puerta pida confirmación ante una orden inequívoca
   (`gate.decidir`: la rama `ORDEN_INEQUIVOCA` devuelve `CREAR_Y_ESCALAR` en
   vez de `CREAR_Y_ACTIVAR`) →
   ```
   $ uv run pytest tests/engine/test_gate.py tests/engine/test_work_intake.py tests/engine/test_session.py -q
   2 failed, 23 passed in 0.49s
   FAILED test_gate.py::test_orden_inequivoca_crea_y_activa_sin_ningun_campo_de_confirmacion
   FAILED test_session.py::test_orden_inequivoca_crea_y_activa_sin_segunda_confirmacion
   ```
   A5-P2 cayó como se esperaba. Revertido con `git checkout -- src/sirius_engine/gate.py`
   (confirmado sin diff).
3. Añadir una causa de escalado fuera de las siete
   (`domain/escalation.CausaEscalado`: octavo miembro
   `OCTAVA_CAUSA_FUERA_DE_LA_LISTA`) →
   ```
   $ uv run pytest tests/engine/test_escalation.py -q
   2 failed, 2 passed in 0.04s
   FAILED test_la_lista_de_causas_tiene_exactamente_siete_miembros - assert 8 == 7
   FAILED test_la_lista_de_causas_es_exactamente_la_cerrada_de_arquitectura_10
   ```
   A5-P5 cayó como se esperaba. Revertido con
   `git checkout -- src/sirius_engine/domain/escalation.py` (confirmado sin diff).

Tras revertir las tres mutaciones, se repitieron las cuatro validaciones
obligatorias completas (arriba) y quedaron en verde, confirmando que el
árbol quedó exactamente como antes de sembrar cada mutación.

## Consecuencias

- El HITO M1 queda demostrado con pruebas automáticas: se puede conversar
  con el motor (`SesionCLI`), preguntarle por el pasado
  (`contexto.recuperar`, A3), y convertir una orden en un WorkItem activado
  con presupuesto, corte y cauce de escalado — todo sin escribir en GitHub
  ni estrenar ningún Worker externo.
- B1 (investigación) y C2 (despacho de programación) pueden consumir
  `gate.decidir` + `work_intake.aplicar_decision` sin reimplementar la
  puerta de intención ni la interfaz, tal como exige el plan de
  implementación (A5 es "bloque COMPARTIDO").
- `interpretar_intencion_v0` queda documentado como marcador de posición: el
  día que exista un intérprete de intención con modelo real, sustituye a
  esta función produciendo el mismo `IntentSignal`, sin que `gate.py` cambie
  una línea.
- Límite conocido: el `Budget` no persiste entre reinicios del proceso -es
  un valor explícito que el llamador conserva, mismo patrón que `now`. Un
  futuro adaptador que sí lo persista deberá decidir dónde vive ese estado
  (probablemente junto al `WorkEngineStore` durable de A2), pero eso es
  trabajo de un bloque posterior, no de A5.
- Límite conocido: la heurística de sensibilidad de `intent_interpreter.py`
  reconoce un conjunto pequeño y explícito de marcadores léxicos; no
  pretende cubrir todo lo que un revisor humano consideraría sensible. Lo
  que sí garantiza -y lo que las pruebas fijan- es que la lista de causas
  *posibles* nunca crece de forma accidental.
- La corrección del error de diagnóstico sobre `context_recall.py` (ver
  «Contexto y problema») deja una lección operativa para el resto de esta
  ronda y para futuras: cualquier comprobación de sintaxis o de
  comportamiento debe hacerse con `uv run python`/`uv run pytest`, nunca con
  el intérprete del sistema.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: las alternativas descartadas comparten la misma
razón de fondo — reutilizar un mecanismo diseñado para otra cosa
(`change_work_item_scope` para contabilidad rutinaria) o pedir al propietario
una decisión que un patrón ya aprobado permite completar sin ambigüedad
material.

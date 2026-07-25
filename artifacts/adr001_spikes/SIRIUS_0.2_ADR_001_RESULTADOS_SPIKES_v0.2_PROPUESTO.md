# SIRIUS 0.2 — ADR-001 · Resultados de los spikes decisivos

**Versión:** 0.2
**Estado:** PROPUESTO · este informe no aprueba nada por sí mismo
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md`
**Ámbito:** spikes decisivos 1–8, 10 y 15–19 (14 en total)
**No autoriza:** implementación de Sirius 0.2, modificación de Sirius 0.1, cambios en migraciones canónicas ni apertura de ADR-002.

---

## 0. Qué cambia respecto de v0.1

Esta versión es una **corrección dirigida de cierre**, no una nueva campaña. Solo se ha hecho dos cosas:

1. **Corregir y reejecutar el spike 7** con las siete dimensiones canónicas obligatorias, sustituyendo las dimensiones experimentales que la v0.1 declaró como supuesto propio.
2. **Revisar de forma dirigida la consistencia** de los catorce resultados registrados, sin rehacer la auditoría completa.

Los otros trece spikes **no se han reejecutado**. Sus entradas se arrastran literalmente desde `evidencia_spikes.json` (v0.1) hacia `evidencia_spikes_v0.2.json`, y todo lo que la v0.1 estableció sobre ellos sigue vigente palabra por palabra. La v0.1 se conserva íntegra como registro de la primera pasada.

---

## 1. Resumen ejecutivo

Los 14 spikes decisivos terminan en `PASS`, cada uno reproducido desde una base limpia. Aplicando literalmente la regla del §5 del paquete operativo, la decisión resultante sigue siendo **RATIFICAR A**.

La corrección del spike 7 **refuerza** la conclusión en lugar de debilitarla: con las siete dimensiones canónicas reales —y con una demostración derivada, no asumida— el modelo aditivo sostiene las siete de forma independiente, y queda medido que ámbito y autoridad caen enteramente fuera de lo que el enum monolítico heredado puede expresar.

La revisión dirigida **no encontró ningún defecto demostrable** en los catorce resultados. No se ha cambiado ningún veredicto. Sí se registran cinco observaciones que no constituyen defecto (§6) y que conviene conocer antes de ratificar.

Los dos hallazgos operativos de la v0.1 se mantienen intactos, porque no dependen del spike 7:

1. **El borrado lógico actual no purga nada.** Marcar una memoria como `deleted` deja el contenido íntegro en el fichero. Verificado leyendo los bytes, no consultando SQL.
2. **Tras eliminar el contenido canónico, el dato sigue vivo en los derivados.** Es exactamente el riesgo D-09. En la traza del spike 10, después de borrar las filas canónicas quedaban 2 coincidencias en los derivados y el canario seguía presente en disco; solo desapareció al destruir los derivados explícitamente.

Ningún spike encontró una limitación propia de SQLite. No procede abrir la contingencia C.

---

## 2. Entorno y versiones

| Elemento | Valor |
|---|---|
| Python | 3.14.6 |
| Biblioteca SQLite | 3.45.1 |
| SQLAlchemy | 2.0.51 |
| Alembic | 1.18.5 |
| Plataforma | linux |
| Head de Alembic | `61be4bb269bf` (sin cambios en todo el ensayo) |

Verificado de nuevo en esta ronda: las cinco cifras coinciden exactamente con las que registró la v0.1.

PRAGMAs reales, obtenidos a través de `sirius.adapters.persistence.database.build_engine` (no de un `create_engine` plano):

| PRAGMA | Valor |
|---|---|
| `foreign_keys` | 1 (lo fija Sirius por conexión) |
| `synchronous` | 2 = FULL (lo fija Sirius por conexión) |
| `journal_mode` | delete (rollback journal; WAL fuera de alcance en 0.1) |
| `secure_delete` | 1 |
| `auto_vacuum` | 0 |
| `page_size` | 4096 |

**Advertencia sobre `secure_delete`.** Vale 1 en esta biblioteca, pero es un valor por defecto de *compilación*. El SQLite que embarque el ejecutable de Windows puede traerlo a 0. Esto importa para el spike 10 (ver §8).

Mecanismo transaccional: `SqliteUnitOfWork` (`src/sirius/adapters/persistence/sqlite_unit_of_work.py`), con `begin/commit/rollback/close` y protocolo de contexto.

FTS5 y triggers en head: dos tablas virtuales (`knowledge_fts`, `message_fts`) y ocho triggers (`memory_revisions_fts_ai/au/ad`, `decision_revisions_fts_ai/ad`, `messages_fts_ai/au/ad`).

---

## 3. Corrección del spike 7 — las siete dimensiones canónicas

### 3.1 Qué estaba mal

La v0.1 usó siete dimensiones **experimentales** (`existencia`, `disponibilidad`, `epistemico`, `confianza`, `aprobacion`, `sensibilidad`, `verificacion`) y lo declaró abiertamente como supuesto propio en su §5 y en su limitación 1: el paquete operativo v1.0 exige el spike pero no enumera las canónicas.

Ese supuesto ya no es necesario: las siete dimensiones canónicas están fijadas y son exactamente

1. **confirmación**
2. **validez**
3. **disponibilidad**
4. **sensibilidad**
5. **temporalidad**
6. **ámbito**
7. **autoridad**

La sustitución no es cosmética. Cuatro de las siete canónicas (**sensibilidad**, **temporalidad**, **ámbito**, **autoridad**) no tienen ninguna correspondencia con el enum heredado, y dos de ellas —ámbito y autoridad— son justamente las que el paquete exige comprobar que no se colapsan.

Además, la v0.1 tenía un **punto débil de método** en este spike concreto, que esta corrección elimina: la pérdida de información del enum se demostraba comparando dos literales escritos a mano (`proyeccion_a = "archived"`, `proyeccion_b = "archived"`). Era cierto por construcción, no medido. Ahora la proyección es una función real (`xmodel.project_to_legacy_status`) aplicada a estados **releídos desde SQLite**.

### 3.2 Qué demuestra el spike corregido

Todo lo que sigue es medido y se persiste en `evidencia_spikes_v0.2.json`.

**a) Las siete dimensiones se representan de forma independiente.** Una afirmación fija las siete y se releen desde `x_state`: 7 filas, un valor por dimensión, sin colisión ni solapamiento. Cada dimensión es una fila propia con clave `(assertion_id, dimension)`.

**b) Modificar una dimensión deja intactas las otras seis.** Barrido completo, una afirmación independiente por dimensión:

| Dimensión mutada | De | A | Otras comprobadas | Otras seis intactas |
|---|---|---|---|---|
| confirmación | confirmada | provisional | 6 | sí |
| validez | vigente | caducada | 6 | sí |
| disponibilidad | activa | archivada | 6 | sí |
| sensibilidad | normal | restringida | 6 | sí |
| temporalidad | puntual | duradera | 6 | sí |
| ámbito | global | proyecto | 6 | sí |
| autoridad | usuario | sistema | 6 | sí |

Siete de siete. No es una dimensión de muestra: son las siete, cada una en su propia base de comprobación.

**c) Coexisten combinaciones que el enum monolítico no puede expresar.** Se persisten **15 combinaciones distintas simultáneamente** y se releen desde SQLite; las 15 tuplas son distintas entre sí. Proyectadas sobre el enum heredado quedan en **3 valores**:

| Valor heredado | Combinaciones canónicas distintas que colapsan en él |
|---|---|
| `current` | **10** |
| `deleted` | 3 |
| `archived` | 2 |

Quince estados distinguibles se reducen a tres. El mayor grupo de colapso agrupa diez combinaciones diferentes bajo un único `current`.

**d) El colapso ocurre incluso dentro de las dimensiones que el enum sí roza.** Dos estados que difieren únicamente en `confirmación` (`confirmada` frente a `provisional`) proyectan al mismo valor `current`. El enum heredado no distingue una afirmación confirmada de una provisional.

**e) Ámbito y autoridad no se colapsan con confirmación, validez ni disponibilidad.** Es la comprobación central del paquete, y se mide de tres maneras concurrentes:

- **No son entradas de la proyección.** El enum heredado solo alcanza a `confirmación`, `validez` y `disponibilidad`; `ámbito` y `autoridad` no intervienen.
- **No son derivables de ellas.** Manteniendo el triple `(confirmación, validez, disponibilidad)` idéntico en `(confirmada, vigente, activa)`, coexisten los **3 valores** de ámbito (`global`, `proyecto`, `conversación`) y los **3 valores** de autoridad (`usuario`, `sistema`, `derivada`). Todo ese grupo proyecta a un **único** valor heredado: `current`. Si ámbito o autoridad fueran función del triple, esto sería imposible.
- **El enum es invariante ante ellas.** Todos los pares de estados que difieren *solo* en ámbito —e igual para autoridad— proyectan al mismo valor heredado. Cambiar el ámbito o la autoridad no mueve el enum ni un milímetro: no es que se confundan, es que el enum no las ve.

**f) Se repite dos veces desde bases limpias con el mismo resultado.** `run_twice` ejecuta el spike sobre dos bases recién creadas y solo deja `PASS` si ambas coinciden; si difieren, degrada a `INCONCLUSIVE`. Además se ejecutaron dos pasadas más comparando la **evidencia completa**, no solo el veredicto: los dos diccionarios de evidencia salieron idénticos, huellas SHA-256 incluidas.

**g) La huella de Sirius 0.1 permanece idéntica y no se altera ninguna tabla heredada.** Tres medidas independientes: huella SHA-256 de esquema y datos heredados idéntica antes y después (`f18fbed6…`), volcado del esquema heredado idéntico, y recuentos de las 13 tablas heredadas idénticos. Ni un `ALTER`, `DROP` o `UPDATE` sobre 0.1.

**h) Sigue siendo un modelo experimental.** La evidencia lo registra explícitamente: `modelo_experimental: true`, `ddl_productivo_fijado: false`, `nombres_fisicos_productivos_fijados: false`. Los nombres de tabla `x_`, el vocabulario de valores de cada dimensión y la propia función de proyección son instrumentos de medida, no DDL definitivo ni nombres físicos productivos.

### 3.3 Resultado

| Elemento | Valor |
|---|---|
| Resultado | **`PASS`** |
| Repetición desde base limpia | sí — segunda pasada también `PASS` |
| Reproducibilidad reforzada | evidencia íntegra idéntica en dos pasadas adicionales |
| Clasificación | ningún `FAIL_STRUCTURAL_MODEL`: la capacidad se obtiene por pura adición |

**Conclusión del spike:** A soporta las siete dimensiones canónicas por pura adición. Cada una se mueve sin arrastrar a las otras seis, coexisten combinaciones que el enum monolítico heredado no puede expresar, y ámbito y autoridad quedan fuera de su alcance en lugar de colapsarse con confirmación, validez o disponibilidad. El enum heredado se conserva intacto y queda como proyección con pérdida, no como fuente.

Evidencia legible por máquina: `artifacts/adr001_spikes/evidencia_spikes_v0.2.json`, entrada 7. Traza legible: `artifacts/adr001_spikes/06_spike7_corregido.txt`.

---

## 4. Resultado de la revisión dirigida

Sin rehacer la auditoría completa y sin reejecutar los otros trece spikes, se cotejaron el informe v0.1, el paquete de evidencia, las pruebas y el código. La revisión es automática y reproducible: `uv run python -m experiments.adr001.revision_dirigida`. Traza: `artifacts/adr001_spikes/07_revision_dirigida.txt`.

| Comprobación exigida | Resultado |
|---|---|
| Los 14 resultados registrados corresponden con las pruebas y el JSON | **sí** — 14 entradas, numeración exacta 1–8, 10, 15–19; las 14 invocadas por pruebas pytest; los 11 campos del §6 completos en las 14 |
| No hay ningún `PASS` declarado sin evidencia automática | **confirmado** — 64 medidas registradas, derivadas de la expresión de veredicto de cada spike, cotejadas una a una contra el JSON |
| No hay discrepancias entre resultado, repetición y conclusión | **ninguna** |
| La regla RATIFICAR A / ESCALAR A B / ABRIR C está bien aplicada | **sí** — verificada además con seis contraejemplos |
| El spike 19 mantiene explícito su modelo de amenaza y sus límites | **sí** |
| Derivados, `secure_delete` y Windows siguen siendo condiciones y no garantías | **sí** |

**Ningún PASS sin sostén.** Para cada spike se extrajo del código la expresión que decide su veredicto y se comprobó que la evidencia registrada en el JSON contiene exactamente las medidas que la sostienen, con el valor exigido. Los catorce quedan sostenidos. Ninguno declara `PASS` por construcción ni con evidencia vacía.

**La regla de decisión reacciona, no solo acierta.** Verificar que devuelve `RATIFICAR A` sobre un conjunto de catorce `PASS` no demuestra que esté bien implementada: lo demostraría igual una función que devolviera siempre eso. Se comprobó con contraejemplos sintéticos que la regla también reacciona correctamente cuando debe:

| Conjunto | Decisión devuelta | Correcta |
|---|---|---|
| 14 en `PASS` | RATIFICAR A | sí |
| `FAIL_STRUCTURAL_MODEL` en el 7 | ESCALAR A B | sí |
| `FAIL_STRUCTURAL_MODEL` en el 15 | ESCALAR A B | sí |
| `FAIL_ENGINE_SQLITE` en el 10 | ABRIR CONTINGENCIA C | sí |
| `FAIL_ENGINE_SQLITE` en el 19 | ABRIR CONTINGENCIA C | sí |
| `INCONCLUSIVE` en el 3 | DECISIÓN BLOQUEADA | sí |

**No se ha cambiado ningún resultado.** La revisión no encontró defecto demostrable en ninguno de los catorce veredictos. Las observaciones de §6 no lo son: no invalidan ninguna medida ni cambian ninguna clasificación.

---

## 5. Tabla final de los 14 spikes

| # | Spike | Resultado | Repetición desde base limpia | Origen |
|---|---|---|---|---|
| 1 | Afirmación atómica con varias procedencias | `PASS` | sí | v0.1 |
| 2 | Apoyo y refutación múltiples | `PASS` | sí | v0.1 |
| 3 | Tiempo válido separado del tiempo de registro | `PASS` | sí | v0.1 |
| 4 | Corrección retroactiva sin destruir el estado anterior | `PASS` | sí | v0.1 |
| 5 | Consulta «válida en T» | `PASS` | sí | v0.1 |
| 6 | Consulta «conocida en T» | `PASS` | sí | v0.1 |
| 7 | **Siete dimensiones canónicas ortogonales sin enum monolítico** | **`PASS`** | **sí** | **v0.2 — corregido y reejecutado** |
| 8 | Ámbito multi-proyecto cerrado | `PASS` | sí | v0.1 |
| 10 | Borrado duro con FTS5 y todos los derivados | `PASS` | sí (dos bases independientes) | v0.1 |
| 15 | Migración de una base 0.1 representativa | `PASS` | sí | v0.1 |
| 16 | Rollback | `PASS` | sí | v0.1 |
| 17 | Fallo inyectado durante escritura crítica | `PASS` | sí | v0.1 |
| 18 | Ningún derivado actúa como fuente canónica | `PASS` | sí | v0.1 |
| 19 | No reconstruibilidad | `PASS` | sí (escenarios WAL y `secure_delete=0`) | v0.1 |

**14 de 14 en `PASS`.**

Evidencia completa y legible por máquina, con los 11 campos que exige el §6 para cada spike: `artifacts/adr001_spikes/evidencia_spikes_v0.2.json`. La evidencia de la primera pasada se conserva sin tocar en `evidencia_spikes.json`.

---

## 6. Observaciones de la revisión que no son defecto

Ninguna de estas cinco cambia un resultado. Se registran porque afectan a cuánto pesa la evidencia, y quien ratifique debe conocerlas.

**O1 · El spike 19 no condiciona su veredicto a su propio control positivo.** El spike 10 sí lo hace: su veredicto es `PASS if (control_ok and limpio)`. El 19 mide el control positivo y el contraste, los registra, pero su veredicto solo depende de `limpio`. En la práctica no hay problema —los valores registrados muestran que el control se sembró (`db.frase = true`) y que el contraste con `secure_delete=0` sí dejó el canario—, así que el `PASS` no es vacío de hecho. Pero la comprobación es más débil que la del 10: si un día el sembrado fallara en silencio, el 19 pasaría igual. Corregirlo exige reejecutar el spike 19, que esta ronda tiene prohibido.

**O2 · En el escenario WAL del spike 19, `-wal` y `-shm` no existían en el momento del escaneo.** Al cerrar limpiamente la conexión, SQLite elimina ambos ficheros. El escaneo los da por limpios por **ausencia**, no por inspección de su contenido. El vector realmente inspeccionado byte a byte es el `.db` (y la copia hecha con `VACUUM INTO`), que es el que sostiene la conclusión. La fila «`-wal` tras checkpoint · limpios» de la v0.1 debe leerse así.

**O3 · Defecto corregido en el registro de evidencia.** En `run_twice`, la rama que degrada un spike a `INCONCLUSIVE` construía su mensaje **después** de sobrescribir el veredicto, de modo que habría informado «primera pasada INCONCLUSIVE» en lugar del resultado realmente obtenido. Corregido. La rama nunca llegó a ejecutarse —los catorce spikes coincidieron en sus dos pasadas—, así que **ninguna evidencia registrada cambia**: era un defecto latente en el informe de incidencias, no en ningún veredicto.

**O4 · Residuo de nomenclatura, deliberado.** El mapa `LEGACY_STATUS_PROJECTION`, que el spike 15 usa para su backfill, sigue escrito con las dimensiones experimentales derogadas. Se ha dejado **intacto a propósito**: unificarlo con las canónicas cambiaría lo que el spike 15 escribe y obligaría a reejecutarlo, cosa que esta ronda tiene prohibida, y su evidencia registrada dejaría de corresponder con el código que la produjo. Queda pendiente de unificar cuando ADR-001 ratifique la taxonomía. No afecta al spike 7, que usa exclusivamente las siete canónicas, ni al veredicto del 15, que no depende de los nombres de las dimensiones.

**O5 · La línea base de la suite de 0.1 que cita la v0.1 no es reproducible en esta rama.** La v0.1 registra 1203 pruebas sobre la rama `fix/chat-history-layout`, commit `b57ad7b2…`. Ese commit no existe en este repositorio, y sobre `evidence/adr001-spikes` la misma suite recoge **1195**. La diferencia es de árbol de partida, no de los spikes: ningún veredicto depende del recuento de la suite de 0.1, y la propiedad que la v0.1 quería demostrar —que `testpaths = ["tests"]` impide que `uv run pytest` recoja `experiments/`— se vuelve a confirmar aquí. Aun así, las cifras de las §3 y §10 de la v0.1 hay que leerlas referidas a aquel árbol.

---

## 7. Evidencia individual (spikes no reejecutados)

Lo que sigue procede de la v0.1 y se conserva sin cambios. El spike 7 se ha sustituido por su versión corregida (§3).

### Spike 1 — Afirmación atómica con varias procedencias
Una afirmación atómica sujeto/predicado/objeto sostuvo **3 procedencias simultáneas** (evento, mensaje y confirmación manual) en `x_provenance`. El modelo heredado admite **1**: `memory_revisions.origin` es un TEXT libre y `source_event_id` un FK único. Huella de 0.1 idéntica. Conclusión: A soporta procedencia múltiple por adición.

### Spike 2 — Apoyo y refutación múltiples
La afirmación central recibió 2 apoyos y 2 refutaciones tipadas coexistiendo en `x_stance`. El modelo heredado tiene **0** relaciones tipadas; la única relación real es `decisions.supersedes_decision_id`, que es 1:1 y solo entre decisiones. Huella de 0.1 idéntica.

### Spike 3 — Tiempo válido separado del tiempo de registro
Se verificaron ambas direcciones: misma validez con distinto registro, y mismo registro con distinta validez. Los dos ejes varían de forma independiente. Columnas de validez en el modelo heredado: **0** (solo `created_at`/`updated_at`, que son tiempo de registro). Confirma D-02 y demuestra que la bitemporalidad es añadible.

### Spike 4 — Corrección retroactiva
La afirmación original («azul») se cerró en el eje de registro (`recorded_until = T2`) y se insertó la corregida («verde») con el mismo intervalo de validez y enlace `corrects_assertion_id`. Tras corregir, el valor original seguía siendo recuperable literalmente como «azul». Nada se sobrescribió.

### Spike 5 — Consulta «válida en T»
Con dos periodos de validez y una corrección posterior: en 2021 devuelve exactamente la afirmación vigente entonces; en 2023, exactamente la corregida. Ni las dos ni ninguna.

### Spike 6 — Consulta «conocida en T»
La prueba bitemporal clave. Antes de la corrección el sistema creía «15 euros»; después, «18 euros». La creencia anterior sigue siendo recuperable y ya no aparece como vigente. En 0.1 esto no es representable: `is_current` es un booleano del presente, sin eje de registro cerrado.

### Spike 8 — Ámbito multi-proyecto cerrado
Con 3 proyectos y un ámbito global, cada proyecto vio exactamente lo suyo más lo global, sin una sola fuga. En paralelo se confirmó la restricción heredada: intentar activar un segundo proyecto lanza `IntegrityError` por `uq_projects_single_active` (la operación se revirtió; la tabla `projects` no se tocó). Confirma D-04 y demuestra que el ámbito es añadible sin rediseñarla.

### Spike 17 — Fallo inyectado durante escritura crítica
Escritura de 4 partes (afirmación, procedencia, estado y derivado) con excepción inyectada antes del commit. Los recuentos de las 6 tablas implicadas fueron idénticos antes y después: **cero estado parcial**, derivados incluidos.

### Spike 18 — Ningún derivado actúa como canon
Se destruyeron todos los derivados (`DROP`, arrastrando las tablas sombra de FTS5). Las consultas canónicas siguieron devolviendo exactamente el mismo resultado sin ellos. Al reconstruirlos solo desde las tablas canónicas, el hash SHA-256 del derivado fue **idéntico** al de antes de destruirlos.

---

## 8. Resultado de borrado y no reconstruibilidad

Conservado de la v0.1, con las precisiones O1 y O2 de §6.

### Las cinco cosas que el paquete exige distinguir

La traza del spike 10 las separa con medición propia en cada etapa (búsqueda de un canario en los **bytes** de los ficheros, no por SQL):

| Etapa | Qué se hizo | Filas canónicas con el token | Coincidencias en derivados | ¿Canario en disco? |
|---|---|---|---|---|
| 1 · borrado lógico | `status = 'deleted'` | 2 | 2 | **Sí** |
| 2 · borrado canónico | `DELETE` de filas heredadas y experimentales | 0 | **2** | **Sí** |
| 3 · eliminación de derivados | `DROP` de derivados y sombras FTS5 | 0 | 0 | No |
| 4 · purga física | checkpoint + `VACUUM` | 0 | 0 | No |
| 5 · no reconstruibilidad | ver spike 19 | — | — | No |

Lo importante está en la etapa 2: **borrar el contenido canónico no basta**. Los triggers heredados sí limpiaron `knowledge_fts` y `message_fts` (0 coincidencias), pero el dato seguía vivo en los derivados y en el fichero. Es la materialización exacta de D-09.

### Spike 19 — No reconstruibilidad

**Modelo de amenaza operativo declarado** (el paquete v1.0 no lo enumera, así que se hace explícito): un tercero con acceso de lectura a `.db`, `-wal`, `-shm`, `-journal` y a copias generadas por la propia aplicación. **Queda fuera** la recuperación forense del medio físico (sectores reasignados, wear leveling de SSD, instantáneas del sistema de ficheros y copias de seguridad previas).

Este límite es parte del resultado, no una nota al pie: fuera de ese modelo de amenaza, el spike **no afirma nada**. Si ADR-001 define un modelo más amplio, el spike 19 debe reejecutarse contra él.

Tras el procedimiento completo en modo WAL, ningún vector reconstruyó nada:

| Vector | Resultado |
|---|---|
| Filas canónicas con el token | 0 |
| Coincidencias FTS5 | 0 |
| Eventos residuales | 0 |
| Derivados experimentales presentes | 0 |
| Tablas sombra FTS5 que aún contienen el token | 0 |
| Copia hecha con `VACUUM INTO` | no contiene el canario |
| `.db` tras `VACUUM` | limpio |
| `-wal` / `-shm` tras checkpoint | ausentes en el momento del escaneo (ver O2) |

**Contraste que valida la medición:** con `secure_delete=0` y sin `VACUUM`, el canario **sí** permanece en el fichero. Esto prueba que la prueba discrimina de verdad y que la purga física es un paso separado, no un efecto colateral del `DELETE`.

### Secuencia verificada

1. `DELETE` de las filas canónicas (heredadas y experimentales).
2. `DROP` de los derivados propios (arrastra sus tablas sombra FTS5).
3. `rebuild` de los FTS5 heredados — **paso defensivo**, no demostrado necesario aquí.
4. Checkpoint del WAL cuando aplique.
5. `VACUUM`.

Sobre el paso 3: con `secure_delete=1` no fue necesario. Se documenta igualmente porque `secure_delete` es un valor por defecto de compilación y puede diferir en el SQLite del ejecutable de Windows.

**Clasificación:** no se observó ninguna limitación propia del motor. Ni el spike 10 ni el 19 son `FAIL_ENGINE_SQLITE`. **No se abre la contingencia C.**

---

## 9. Resultado de migración y rollback

Conservado de la v0.1 sin cambios.

### Spike 15 — Migración

Base sintética construida **exclusivamente con el esquema real de 0.1** (`upgrade_to_head`), con los casos que el paquete exige: 8 mensajes (incluido uno redactado con `content` NULL), 5 memorias con 9 revisiones cubriendo los tres estados del enum, 3 decisiones con cadena de sustitución, 3 proyectos con revisiones, 3 eventos, uso de LLM e índices FTS5.

| Comprobación | Resultado |
|---|---|
| Head de Alembic antes / después | `61be4bb269bf` / `61be4bb269bf` — sin cambios |
| Huella SHA-256 de 0.1 antes / después | idéntica |
| Recuentos por tabla antes / después | idénticos |
| Memorias vigentes en 0.1 | 5 |
| Afirmaciones creadas | 5 — sin pérdidas |
| Memorias distintas cubiertas | 5 — sin duplicaciones |
| Afirmaciones huérfanas | 0 |
| Afirmaciones sin procedencia | 0 |
| Contenido conservado | en las 5 |
| Autoridad declarada | `['legacy']` — única |
| Derivados reconstruidos | 5 |

El backfill solo **lee** de las tablas heredadas. La autoridad se registra explícitamente en `x_migration_state` y se comprobó que solo existe un valor.

### Spike 16 — Rollback

| Comprobación | Resultado |
|---|---|
| Objetos en `sqlite_master`: inicio / tras expandir / tras rollback | 45 / 60 / **45** |
| Esquema completo idéntico al inicial | sí |
| Residuo experimental | ninguno |
| Huella de 0.1 antes / tras rollback | idéntica |
| Head de Alembic | sin cambios |
| Base utilizable por el código **real** de 0.1 | sí — `schema_version=61be4bb269bf; conversación=1; mensajes=8` |

La última fila es la prueba fuerte: tras el rollback la base se abrió con `build_sqlite_conversation_repository` y `get_supported_schema_version` reales de Sirius 0.1 y se leyó de ella sin incidencias.

Este ensayo demuestra **viabilidad**, no estrategia. No se decide secuencia productiva, ventana de corte, dual-write, despliegue ni retirada de tablas: eso pertenece a ADR-004.

---

## 10. Archivos

Todo dentro de las dos rutas autorizadas. Ningún fichero fuera de ellas fue creado, modificado ni borrado.

**Modificados en esta ronda — `experiments/adr001/`**

| Archivo | Cambio |
|---|---|
| `xmodel.py` | `STATE_DIMENSIONS` pasa a ser las siete canónicas; se añaden `CANONICAL_STATE_VALUES`, `CANONICAL_INITIAL_STATE`, `LEGACY_STATUS_VALUES`, `LEGACY_PROJECTION_INPUTS` y `project_to_legacy_status()` |
| `spikes_model.py` | `spike_07` reescrito por completo; se añaden los auxiliares `_read_state`, `_assertion_with_state`, `_legacy_counts` y `_difieren_solo_en` |
| `test_adr001_spikes.py` | 7 pruebas nuevas específicas del spike 7 corregido |
| `evidence.py` | corrección del mensaje de incidencia en `run_twice` (ver O3) |

**Creados en esta ronda — `experiments/adr001/`**

| Archivo | Función |
|---|---|
| `run_spike7_v02.py` | Reejecuta solo el spike 7, arrastra los otros trece y produce la evidencia v0.2 |
| `revision_dirigida.py` | Revisión dirigida automática y reproducible |

**Creados en esta ronda — `artifacts/adr001_spikes/`**

| Archivo | Contenido |
|---|---|
| `evidencia_spikes_v0.2.json` | Los 14 spikes con el 7 corregido; los otros 13 arrastrados literalmente |
| `06_spike7_corregido.txt` | Traza del spike 7 corregido |
| `07_revision_dirigida.txt` | Traza de la revisión dirigida |
| `SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.2_PROPUESTO.md` | Este informe |

**No modificados, conservados de la v0.1**

`synthetic.py`, `fingerprint.py`, `spikes_deletion.py`, `spikes_migration.py`, `conftest.py`, `run_all.py`, `__init__.py`, `00_prevuelo.txt`, `01_linea_base_check_antes.txt`, `02_ejecucion_spikes.txt`, `03_pruebas_experimentales.txt`, `04_linea_base_check_despues.txt`, `05_git_status_final.txt`, `evidencia_spikes.json` y el informe v0.1.

---

## 11. Pruebas ejecutadas en esta ronda

| Comando | Resultado |
|---|---|
| `uv run pytest experiments/adr001 -k "spike_7 or (modelo_fisico and 7)"` | **9 pasadas** |
| `uv run python -m experiments.adr001.run_spike7_v02` | spike 7 `PASS`, 4 bases limpias, decisión RATIFICAR A |
| `uv run python -m experiments.adr001.revision_dirigida` | sin defectos demostrables (código de salida 0) |
| `uv run ruff format --check experiments/adr001` | PASA |
| `uv run ruff check experiments/adr001` | PASA |
| `uv run mypy src tests` | PASA — 236 ficheros |
| `uv run pytest --collect-only` (suite de 0.1) | 1195 recogidas — ver O5 |

**La suite completa de Sirius 0.1 no se ha reejecutado**, conforme a la instrucción de esta ronda: ningún fichero productivo fue modificado. `git status` lo confirma (§13). `pyproject.toml` fija `testpaths = ["tests"]`, así que `uv run pytest` no recoge `experiments/`; y `mypy` está configurado con `files = ["src", "tests"]`, así que tampoco analiza el código experimental. No hizo falta ningún cambio en la configuración de pruebas.

---

## 12. Limitaciones e incertidumbres

Se conservan las de la v0.1, con la primera ya resuelta.

1. ~~Las 7 dimensiones de estado son experimentales.~~ **Resuelta.** Las siete dimensiones son ahora las canónicas. Lo que sigue siendo experimental es el **vocabulario de valores** de cada dimensión y la función de proyección al enum heredado: son instrumentos de medida, no taxonomía aprobada.
2. **El modelo de amenaza del spike 19 lo declara el ensayo, no el paquete.** Queda fuera la recuperación forense del medio físico. Si ADR-001 define un modelo más amplio, el spike 19 debe reejecutarse contra él. Ver también O1 y O2.
3. **`secure_delete` es un valor de compilación.** Aquí vale 1. En el SQLite que embarque el ejecutable de Windows puede valer 0, y en ese caso el `DELETE` sin `VACUUM` no purga (probado en el contraste del spike 19). Conviene verificarlo sobre el ejecutable real.
4. **Entorno Linux, no Windows.** Todo se ejecutó en Linux con SQLite 3.45.1. Los PRAGMAs efectivos y el comportamiento de purga deberían confirmarse sobre el ejecutable empaquetado de Windows.
5. **`journal_mode` de Sirius 0.1 es `delete`, no WAL.** El escenario WAL del spike 19 es prospectivo: cubre el requisito del paquete, pero hoy 0.1 no usa WAL.
6. **Volumen sintético pequeño.** Las bases tienen decenas de filas. Los spikes son de *capacidad estructural*, no de rendimiento; no se fijó ningún umbral, porque eso pertenece al Registro de Tolerancias.
7. **Las tres fuentes 0.2 originales siguen sin estar en el repositorio.** Este ensayo se ejecutó contra el paquete operativo v1.0, que es autosuficiente para la ejecución. Si ADR-001 define A/B/C/D de otro modo, la interpretación de los veredictos debe revisarse.
8. **El modelo experimental es deliberadamente mínimo.** No es DDL definitivo ni nombres productivos. Falsa A; no la diseña.
9. **Trece de los catorce spikes no se han reejecutado en esta ronda.** Sus veredictos proceden de la pasada de la v0.1. La revisión dirigida los ha cotejado contra el JSON, las pruebas y el código, pero cotejar no es reejecutar.

---

## 13. Decisión resultante

### RATIFICAR A

Fundamento, aplicando literalmente la regla del §5 del paquete:

- los 14 spikes decisivos están en `PASS`, incluido el 7 tras su corrección;
- ningún `FAIL_STRUCTURAL_MODEL` en 1–8 ni en 15–18 → no procede escalar a B;
- ningún `FAIL_ENGINE_SQLITE` confirmado en 10 ni en 19 → no procede abrir C;
- ningún `INCONCLUSIVE` → la decisión no queda bloqueada.

Las nueve capacidades exigidas se obtuvieron por pura adición sobre el esquema heredado, con la huella de Sirius 0.1 idéntica en todos los casos y el head de Alembic intacto.

**Esta ratificación es una propuesta.** El informe está en estado PROPUESTO y no aprueba nada por sí mismo. La decisión formal corresponde al usuario sobre ADR-001.

**Condiciones que la ratificación arrastra** (no son objeciones a A; son consecuencias medidas, y siguen siendo condiciones pendientes, no garantías ya implementadas):

1. El borrado tendrá que destruir explícitamente los derivados. `DELETE` + `VACUUM` no basta: el dato sobrevive en ellos.
2. Todo derivado deberá ser reconstruible desde lo canónico y no podrá consultarse como fuente. El spike 18 muestra que es alcanzable y da la forma de comprobarlo.
3. La secuencia de purga debe verificarse sobre el ejecutable real de Windows, por `secure_delete`.

Ninguna de las tres está implementada. Las tres son requisitos para la implementación futura de A.

---

## 14. Siguiente movimiento único

**Que el usuario revise este informe y decida si ratifica formalmente la alternativa A en ADR-001.**

Nada más. No se abre ADR-002, no se diseña la estrategia de migración de ADR-004, no se toca Sirius 0.1 y no se convierte nada de `experiments/adr001/` en código productivo.

---

**Cierre técnico:** `git status` muestra cambios exclusivamente dentro de `experiments/adr001/` y `artifacts/adr001_spikes/`. Ningún fichero de Sirius 0.1, ninguna migración canónica y ningún documento de `docs/` fueron modificados. El informe v0.1 y su evidencia se conservan intactos.

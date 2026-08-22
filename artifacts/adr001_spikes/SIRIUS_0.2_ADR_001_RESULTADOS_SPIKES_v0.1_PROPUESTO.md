# SIRIUS 0.2 — ADR-001 · Resultados de los spikes decisivos

**Versión:** 0.1
**Estado:** PROPUESTO · este informe no aprueba nada por sí mismo
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md` (leído desde `origin/main`, commit `24fc9d5`)
**Ámbito:** spikes decisivos 1–8, 10 y 15–19 (14 en total)
**No autoriza:** implementación de Sirius 0.2, modificación de Sirius 0.1, cambios en migraciones canónicas ni apertura de ADR-002.

---

## 1. Resumen ejecutivo

Los 14 spikes decisivos terminaron en `PASS`, cada uno reproducido desde una base limpia. Aplicando literalmente la regla del §5 del paquete operativo, la decisión resultante es **RATIFICAR A**.

La hipótesis de la alternativa A —conservar el esquema heredado y añadir— se sostuvo en todos los casos: cada capacidad exigida se obtuvo creando tablas nuevas con prefijo `x_`, sin un solo `ALTER`, `DROP` o `UPDATE` sobre ninguna tabla de Sirius 0.1. En todos los spikes la huella SHA-256 del esquema y los datos heredados fue idéntica antes y después.

Dos hallazgos operativos merecen constar, porque no invalidan A pero condicionan cómo habrá que implementarla:

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

PRAGMAs reales, obtenidos a través de `sirius.adapters.persistence.database.build_engine` (no de un `create_engine` plano):

| PRAGMA | Valor |
|---|---|
| `foreign_keys` | 1 (lo fija Sirius por conexión) |
| `synchronous` | 2 = FULL (lo fija Sirius por conexión) |
| `journal_mode` | delete (rollback journal; WAL fuera de alcance en 0.1) |
| `secure_delete` | 1 |
| `auto_vacuum` | 0 |
| `page_size` | 4096 |

**Advertencia sobre `secure_delete`.** Vale 1 en esta biblioteca, pero es un valor por defecto de *compilación*. El SQLite que embarque el ejecutable de Windows puede traerlo a 0. Esto importa para el spike 10 (ver §7).

Mecanismo transaccional: `SqliteUnitOfWork` (`src/sirius/adapters/persistence/sqlite_unit_of_work.py`), con `begin/commit/rollback/close` y protocolo de contexto.

FTS5 y triggers en head: dos tablas virtuales (`knowledge_fts`, `message_fts`) y ocho triggers (`memory_revisions_fts_ai/au/ad`, `decision_revisions_fts_ai/ad`, `messages_fts_ai/au/ad`).

---

## 3. Estado inicial del repositorio

```
raiz            /home/user/sirius
rama            fix/chat-history-layout
HEAD            b57ad7b24c7f0232d45540cde73294e2d68e02ef
origin/main     24fc9d5869309b71f4a1a333a7b4f0fda51938e4
git status      limpio (sin ficheros rastreados modificados)
```

Línea base ejecutada antes de crear código experimental. No hay PowerShell en este contenedor Linux (`command -v pwsh/powershell` no devuelve nada), así que se ejecutaron los cuatro comandos de `scripts/check.ps1` en su mismo orden:

| Comprobación | Resultado antes |
|---|---|
| `uv run ruff format --check .` | PASA — 239 ficheros |
| `uv run ruff check .` | PASA |
| `uv run mypy src tests` | PASA — 236 ficheros |
| `uv run pytest` | PASA — **1203 tests** en 206 s |

La línea base estaba verde, así que no hubo bloqueo y no se corrigió nada de Sirius 0.1.

---

## 4. Tabla de los 14 spikes

| # | Spike | Resultado | Repetición desde base limpia |
|---|---|---|---|
| 1 | Afirmación atómica con varias procedencias | `PASS` | sí |
| 2 | Apoyo y refutación múltiples | `PASS` | sí |
| 3 | Tiempo válido separado del tiempo de registro | `PASS` | sí |
| 4 | Corrección retroactiva sin destruir el estado anterior | `PASS` | sí |
| 5 | Consulta «válida en T» | `PASS` | sí |
| 6 | Consulta «conocida en T» | `PASS` | sí |
| 7 | Siete dimensiones ortogonales sin enum monolítico | `PASS` | sí |
| 8 | Ámbito multi-proyecto cerrado | `PASS` | sí |
| 10 | Borrado duro con FTS5 y todos los derivados | `PASS` | sí (dos bases independientes) |
| 15 | Migración de una base 0.1 representativa | `PASS` | sí |
| 16 | Rollback | `PASS` | sí |
| 17 | Fallo inyectado durante escritura crítica | `PASS` | sí |
| 18 | Ningún derivado actúa como fuente canónica | `PASS` | sí |
| 19 | No reconstruibilidad | `PASS` | sí (escenarios WAL y `secure_delete=0`) |

Evidencia completa y legible por máquina, con los 11 campos que exige el §6 para cada spike: `artifacts/adr001_spikes/evidencia_spikes.json`.

---

## 5. Evidencia individual

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

### Spike 7 — Siete dimensiones ortogonales
Se fijaron las 7 dimensiones, se modificó una sola (`disponibilidad` → `archivada`) y **las otras 6 no variaron**. Además se demostró la pérdida de información del enum heredado: dos combinaciones distintas del modelo nuevo se proyectan al mismo valor único `archived`.

> **Supuesto declarado.** Las 7 dimensiones usadas (`existencia`, `disponibilidad`, `epistemico`, `confianza`, `aprobacion`, `sensibilidad`, `verificacion`) son EXPERIMENTALES. El paquete v1.0 exige el spike pero no enumera las canónicas. La incertidumbre que el spike resuelve es estructural —¿puede el modelo representar N dimensiones independientes y absorber el enum heredado sin pérdida?— y esa respuesta no depende de los nombres concretos. La lista canónica debe venir de ADR-001.

### Spike 8 — Ámbito multi-proyecto cerrado
Con 3 proyectos y un ámbito global, cada proyecto vio exactamente lo suyo más lo global, sin una sola fuga. En paralelo se confirmó la restricción heredada: intentar activar un segundo proyecto lanza `IntegrityError` por `uq_projects_single_active` (la operación se revirtió; la tabla `projects` no se tocó). Confirma D-04 y demuestra que el ámbito es añadible sin rediseñarla.

### Spike 17 — Fallo inyectado durante escritura crítica
Escritura de 4 partes (afirmación, procedencia, estado y derivado) con excepción inyectada antes del commit. Los recuentos de las 6 tablas implicadas fueron idénticos antes y después: **cero estado parcial**, derivados incluidos.

### Spike 18 — Ningún derivado actúa como canon
Se destruyeron todos los derivados (`DROP`, arrastrando las tablas sombra de FTS5). Las consultas canónicas siguieron devolviendo exactamente el mismo resultado sin ellos. Al reconstruirlos solo desde las tablas canónicas, el hash SHA-256 del derivado fue **idéntico** al de antes de destruirlos.

---

## 6. Fallos inyectados y repeticiones

**Fallos deliberados de diseño (spike 17):** una excepción a mitad de una escritura crítica de 4 partes. Resultado: reversión total.

**Fallos del prototipo, corregidos y repetidos** (el paquete los distingue explícitamente de los fallos estructurales):

1. **Patrón `LIKE` inválido.** La primera pasada dio `FAIL_STRUCTURAL_MODEL` en los 10 spikes de modelo. Causa: usé `LIKE 'x[_]%'`, sintaxis de clases de caracteres de SQL Server que SQLite no interpreta, de modo que no casaba con nada y las tablas experimentales entraban en la huella «heredada». Corregido a `LIKE 'x\_%' ESCAPE '\'` y repetido.
2. **Autoíndices no filtrados.** Tras la corrección anterior seguían fallando todos por la huella. Causa: los índices que SQLite crea automáticamente para las claves primarias compuestas de las tablas experimentales se llaman `sqlite_autoindex_x_...`, así que el filtro por `name` no los excluía. Corregido filtrando también por `tbl_name` y repetido. A partir de ahí, 10/10 `PASS`.

Ninguno de los dos era una limitación del modelo heredado: eran defectos de mi instrumentación, y así se clasificaron.

**Hipótesis mía que la evidencia refutó.** Escribí inicialmente que FTS5 retendría los términos borrados en sus segmentos y que haría falta un `rebuild`. La medición lo desmintió en este entorno: la pasada **sin** `rebuild` también terminó limpia (`fts5_retiene_terminos_sin_rebuild: false`). Corregí la conclusión para que dijera lo que la evidencia muestra, y el `rebuild` queda documentado como paso defensivo, no como necesidad demostrada. Ver §7.

**Repetición desde base limpia.** Los spikes 1–8, 15–18 se ejecutan dos veces mediante `run_twice`, cada una sobre una base recién creada; si los dos veredictos difieren, el resultado se degrada automáticamente a `INCONCLUSIVE`. Los spikes 10 y 19 ejecutan internamente varias bases limpias independientes (con y sin `rebuild`; escenarios WAL y `secure_delete=0`).

---

## 7. Resultado de borrado y no reconstruibilidad

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

Modelo de amenaza operativo declarado (el paquete v1.0 no lo enumera, así que se hace explícito): un tercero con acceso de lectura a `.db`, `-wal`, `-shm`, `-journal` y a copias generadas por la propia aplicación. **Queda fuera** la recuperación forense del medio físico (sectores reasignados, wear leveling de SSD, instantáneas del sistema de ficheros y copias de seguridad previas).

Tras el procedimiento completo en modo WAL, ningún vector reconstruyó nada:

| Vector | Resultado |
|---|---|
| Filas canónicas con el token | 0 |
| Coincidencias FTS5 | 0 |
| Eventos residuales | 0 |
| Derivados experimentales presentes | 0 |
| Tablas sombra FTS5 que aún contienen el token | 0 |
| Copia hecha con `VACUUM INTO` | no contiene el canario |
| `-wal` tras checkpoint · `.db` tras `VACUUM` | limpios |

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

## 8. Resultado de migración y rollback

### Spike 15 — Migración

Base sintética construida **exclusivamente con el esquema real de 0.1** (`upgrade_to_head`), con los casos que el paquete exige: 8 mensajes (incluido uno redactado con `content` NULL), 5 memorias con 9 revisiones cubriendo los tres estados del enum, 3 decisiones con cadena de sustitución, 3 proyectos con revisiones, 3 eventos, uso de LLM e índices FTS5.

| Comprobación | Resultado |
|---|---|
| Head de Alembic antes / después | `61be4bb269bf` / `61be4bb269bf` — sin cambios |
| Huella SHA-256 de 0.1 antes / después | idéntica (`e9c0a881…`) |
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

## 9. Archivos creados

Todo dentro de las dos rutas autorizadas. Ningún fichero fuera de ellas fue creado, modificado ni borrado.

**Código experimental — `experiments/adr001/`**

| Archivo | Función |
|---|---|
| `__init__.py` | Declaración de aislamiento del paquete |
| `synthetic.py` | Bases sintéticas con el esquema real de 0.1 |
| `xmodel.py` | Modelo físico experimental aditivo (tablas `x_`) |
| `fingerprint.py` | Huellas deterministas para probar que 0.1 no se toca |
| `evidence.py` | Registro de evidencia y ejecución doble |
| `spikes_model.py` | Spikes 1–8, 17, 18 |
| `spikes_deletion.py` | Spikes 10 y 19 |
| `spikes_migration.py` | Spikes 15 y 16 |
| `test_adr001_spikes.py` | 18 pruebas pytest |
| `conftest.py` | Hace importable el paquete bajo `--import-mode=importlib` |
| `run_all.py` | Runner y aplicación de la regla de decisión |

**Evidencia — `artifacts/adr001_spikes/`**

| Archivo | Contenido |
|---|---|
| `00_prevuelo.txt` | Versiones, PRAGMAs reales, head, UnitOfWork, triggers, FTS5 |
| `01_linea_base_check_antes.txt` | Las 4 comprobaciones antes de los experimentos |
| `02_ejecucion_spikes.txt` | Salida del runner de los 14 spikes |
| `03_pruebas_experimentales.txt` | Salida de las 18 pruebas |
| `04_linea_base_check_despues.txt` | Las 4 comprobaciones después |
| `05_git_status_final.txt` | `git status` e inventario de archivos |
| `evidencia_spikes.json` | Los 11 campos del §6 para cada spike |
| `SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.1_PROPUESTO.md` | Este informe |

Los directorios `__pycache__` bajo `experiments/adr001/` son bytecode generado automáticamente por Python, no artefactos del ensayo.

---

## 10. Pruebas ejecutadas

| Comando | Antes | Después |
|---|---|---|
| `uv run ruff format --check .` | PASA (239 ficheros) | PASA (250 ficheros) |
| `uv run ruff check .` | PASA | PASA |
| `uv run mypy src tests` | PASA (236 ficheros) | PASA (236 ficheros) |
| `uv run pytest` (suite de 0.1) | **1203** en 206 s | **1203** en 204 s |
| `uv run pytest experiments/adr001 -q` | — | **18** en 13,8 s |
| `uv run python -m experiments.adr001.run_all` | — | 14 spikes en 10,8 s |

El recuento de la suite de Sirius 0.1 es **exactamente el mismo antes y después: 1203**. `pyproject.toml` fija `testpaths = ["tests"]`, así que `uv run pytest` no recoge `experiments/`; y `mypy` está configurado con `files = ["src", "tests"]`, así que tampoco analiza el código experimental. **No hizo falta ningún cambio en la configuración de pruebas.**

Las 250 vs. 239 ficheros de `ruff format` son exclusivamente los 11 ficheros nuevos de `experiments/adr001/`.

---

## 11. Limitaciones e incertidumbres

1. **Las 7 dimensiones de estado son experimentales.** El paquete v1.0 no enumera las canónicas. El spike resuelve la pregunta estructural, no fija la taxonomía. La lista canónica debe venir de ADR-001.
2. **El modelo de amenaza del spike 19 lo he declarado yo.** El paquete v1.0 no lo especifica. Queda fuera la recuperación forense del medio físico. Si ADR-001 define un modelo más amplio, el spike 19 debe reejecutarse contra él.
3. **`secure_delete` es un valor de compilación.** Aquí vale 1. En el SQLite que embarque el ejecutable de Windows puede valer 0, y en ese caso el `DELETE` sin `VACUUM` no purga (probado en el contraste del spike 19). Conviene verificarlo sobre el ejecutable real.
4. **Entorno Linux, no Windows.** Todo se ejecutó en Linux con SQLite 3.45.1. Los PRAGMAs efectivos y el comportamiento de purga deberían confirmarse sobre el ejecutable empaquetado de Windows.
5. **`journal_mode` de Sirius 0.1 es `delete`, no WAL.** El escenario WAL del spike 19 es prospectivo: cubre el requisito del paquete, pero hoy 0.1 no usa WAL.
6. **Volumen sintético pequeño.** Las bases tienen decenas de filas. Los spikes son de *capacidad estructural*, no de rendimiento; no se fijó ningún umbral, porque eso pertenece al Registro de Tolerancias.
7. **Las tres fuentes 0.2 originales siguen sin estar en el repositorio.** Este ensayo se ejecutó contra el paquete operativo v1.0, que es autosuficiente para la ejecución. Las definiciones canónicas de A/B/C/D se tomaron de la §8 del inventario de línea base («A conserva este esquema y añade; B lo sustituye manteniendo SQLite; C cambia motor y esquema; D lo reconstruye por eventos»). Si ADR-001 las define de otro modo, la interpretación de los veredictos debe revisarse.
8. **El modelo experimental es deliberadamente mínimo.** No es DDL definitivo ni nombres productivos. Falsa A; no la diseña.

---

## 12. Decisión resultante

### RATIFICAR A

Fundamento, aplicando literalmente la regla del §5 del paquete:

- los 14 spikes decisivos terminaron en `PASS`;
- ningún `FAIL_STRUCTURAL_MODEL` en 1–8 ni en 15–18 → no procede escalar a B;
- ningún `FAIL_ENGINE_SQLITE` confirmado en 10 ni en 19 → no procede abrir C;
- ningún `INCONCLUSIVE` → la decisión no queda bloqueada.

Las nueve capacidades exigidas se obtuvieron por pura adición sobre el esquema heredado, con la huella de Sirius 0.1 idéntica en todos los casos y el head de Alembic intacto.

**Esta ratificación es una propuesta.** El informe está en estado PROPUESTO y no aprueba nada por sí mismo. La decisión formal corresponde al usuario sobre ADR-001.

**Condiciones que la ratificación arrastra** (no son objeciones a A; son consecuencias medidas):

1. El borrado tendrá que destruir explícitamente los derivados. `DELETE` + `VACUUM` no basta: el dato sobrevive en ellos.
2. Todo derivado deberá ser reconstruible desde lo canónico y no podrá consultarse como fuente. El spike 18 muestra que es alcanzable y da la forma de comprobarlo.
3. La secuencia de purga debe verificarse sobre el ejecutable real de Windows, por `secure_delete`.

---

## 13. Siguiente movimiento único

**Que el usuario revise este informe y decida si ratifica formalmente la alternativa A en ADR-001.**

Nada más. No se abre ADR-002, no se diseña la estrategia de migración de ADR-004, no se toca Sirius 0.1 y no se convierte nada de `experiments/adr001/` en código productivo.

---

**Cierre técnico:** `git status` final muestra únicamente `experiments/` y `artifacts/` como rutas nuevas sin rastrear. `git diff --stat HEAD` está vacío: ningún fichero rastreado de Sirius 0.1 fue modificado. No se hizo commit, push ni merge.

# SIRIUS 0.2 — ADR-002 · Aprobación de `ADR002-A` como PREPARADO PARA BENCHMARK

**Versión:** 1.0
**Estado:** **APROBADO · `ADR002-A` PREPARADO PARA BENCHMARK**
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado:** `e40eff416d4a7965217580635980ac897716306d`
**Autorización explícita del usuario:** «Aprobado»

## 0. Objeto y alcance

Esta acta materializa la aprobación explícita del usuario, expresada
literalmente como **«Aprobado»**, y registra el estado:

> **`ADR002-A`: PREPARADO PARA BENCHMARK**

La aprobación acepta, según la declaró el usuario:

1. la corrección de los tres defectos bloqueantes de `ADR002-A`;
2. la ficha vigente `ADR002-A` v2;
3. la sustitución normativa de la ficha v1;
4. la interpretación documentada de que la v1 conserva íntegro su contenido
   original en Git mientras su estado actual pasa a `SUSTITUIDA` conforme al
   contrato;
5. la conclusión de que `ADR002-A` está **PREPARADO PARA BENCHMARK**.

**Esta aprobación NO autoriza ejecutar el benchmark ni medir el candidato.**

Los documentos y artefactos conservan sus nombres y etiquetas históricas
`PROPUESTO`. Esta acta prevalece sobre esas etiquetas sin reescribirlos,
preservando las identidades exactas auditadas.

## 1. Qué significa exactamente PREPARADO PARA BENCHMARK

Este estado es una afirmación **estrecha** y su borde está escrito aquí para
que nadie lo ensanche después.

### 1.1 Significa, y solo esto

| # | Significado |
|---|---|
| 1 | **Prototipo implementado**: `ADR002-A` existe como candidato ejecutable sobre la infraestructura común. |
| 2 | **Ficha vigente congelada**: `ficha_ADR002-A_v2.json`, en estado `CONGELADA`, con su huella recomputable y sin ningún resultado observado del candidato. |
| 3 | **Reglas funcionales comprobadas**: etapas, puertas, paradas, ámbito, polaridad, tiempo, explicación, traza y ciclo del derivado, sobre fixtures técnicos propios. |
| 4 | **Custodia válida**: anterioridad estricta de la ficha frente a las ejecuciones, unicidad de ficha `CONGELADA`, identidades que resuelven y evidencia previa no reescrita. |
| 5 | **Candidato apto para recibir una futura autorización de ejecución**: el material de gobierno está completo para que esa autorización pueda decidirse. |

### 1.2 No significa, en ningún grado

| # | Lo que **no** se afirma |
|---|---|
| 1 | **Benchmark ejecutado.** No se ha ejecutado. |
| 2 | **Rendimiento validado.** No existe ni una sola cifra de rendimiento de `ADR002-A`. |
| 3 | **Puertas del benchmark superadas.** Ninguna se ha evaluado contra este candidato. |
| 4 | **Candidato aprobado como arquitectura final.** No lo es. |
| 5 | **Candidato ganador.** No hay comparación, y `ADR002-B/C/D` ni siquiera existen. |
| 6 | **Autorización de uso productivo.** Ninguna. |

**La ejecución sigue bloqueada.** Autorizar una ejecución sobre el corpus
oficial es un acto de gobierno distinto, posterior e independiente de esta
acta.

## 2. Identidad vinculante: SHA y blobs

La identidad se fija sobre el commit auditado
`e40eff416d4a7965217580635980ac897716306d`. La cadena es **lineal** y cada
commit citado es **ancestro estricto** del siguiente.

### 2.1 Preparación original de `ADR002-A`

| Commit | Contenido |
|---|---|
| `c01f23fc2652ddb038cdccc59fca3cd19c9a5b28` | paquete de trabajo 11 · acta de preinscripción de la infraestructura común y de `ADR002-A` |
| `e37c0d1773a4df629b20f0943f5331e3b7ee4e13` | infraestructura común neutral · prototipo original de `ADR002-A` |
| `b96e6ea76d60bc51f1dc0cb8e9f3d12cb3900d25` | ficha `ADR002-A` v1 original · blob original `1a96f535250bce643e8ccf2edb0362b3ec9320fe` |
| `5c5c4be6cc056f18b631fdba595d42b251b041b1` | pruebas técnicas realizadas bajo la ficha v1 |

### 2.2 Corrección

| Commit | Contenido |
|---|---|
| `f6dae77590fbc3cf95fca36b8f6bc9921935bd82` | paquete de corrección 01 · los tres defectos y las declaraciones de ficha afectadas |
| `97c9977609e6244547d1e0aa2f495e7a3f99273d` | prototipo corregido · `E3` dirigida · controles anti-barrido · reconstrucción completa del derivado |
| `e15e5d0f9f2dda87ea3abb4b9b86adcba015d4a0` | ficha `ADR002-A` v2 · ficha v1 marcada `SUSTITUIDA` · fe de erratas 02 |
| `e40eff416d4a7965217580635980ac897716306d` | pruebas funcionales posteriores a la ficha v2 |

### 2.3 Ficha vigente

| Campo | Valor |
|---|---|
| Ruta | `artifacts/adr002_cards/ficha_ADR002-A_v2.json` |
| Blob | `c0169c26ead4e9237d4e81e8f5e75b412f505296` |
| Huella canónica | `4ed820fab545dd9154ce078349c214f870baecd1` |
| Estado | `CONGELADA` |
| Versión | `2` |
| Sustituye a | `1` |
| Commit de referencia declarado | `f6dae77590fbc3cf95fca36b8f6bc9921935bd82` |
| Commit de entrada observado en Git | `e15e5d0f9f2dda87ea3abb4b9b86adcba015d4a0` |

### 2.4 Ficha histórica

| Campo | Valor |
|---|---|
| Ruta | `artifacts/adr002_cards/ficha_ADR002-A_v1.json` |
| Estado actual | `SUSTITUIDA` |
| Blob actual | `4dcb53873de5ca58cf3e929e861511219430b6be` |
| Huella actual | `8d8c21b6afd1d32ee612dd14199ab9c5605bfb96` |
| Contenido original | commit `b96e6ea76d60bc51f1dc0cb8e9f3d12cb3900d25` · blob `1a96f535250bce643e8ccf2edb0362b3ec9320fe` |
| Huella original | `00571890294bcd18748e2ee600eb43bad1b92f80` |

La v1 **no se borra ni se retira**: se conserva como historial y se marca. El
diff entre su contenido original y el actual son **exactamente dos líneas** —el
campo `estado` y la huella que se recomputa de él—, porque el estado forma
parte de la forma canónica. Ningún límite y ninguna declaración de la v1 se han
tocado. La fe de erratas 02 registra esta interpretación y por qué manda el
mecanismo del contrato.

### 2.5 Código ejecutable cubierto por la ficha

La ficha v2 cita el árbol `94e387507ae66947fd97316fa46a66b3a4ca2219` de
`experiments/adr002/candidates` en el commit del prototipo corregido
`97c9977`. Después de ese commit, el árbol del **directorio** cambió porque las
pruebas y el fixture viven en él. Lo que importa es que el **código ejecutable
no cambió ni un byte**:

| Subárbol | En `97c9977` | En `e40eff4` | |
|---|---|---|---|
| `experiments/adr002/candidates/common` | `9ada666e0e044758107f4089e7585bb47aabbbf0` | `9ada666e0e044758107f4089e7585bb47aabbbf0` | **idéntico** |
| `experiments/adr002/candidates/adr002_a` | `2d90b551445db340458278a5accad55372995b76` | `2d90b551445db340458278a5accad55372995b76` | **idéntico** |

### 2.6 Blobs de los artefactos vinculados

**Documentación de gobierno**

| Artefacto | Blob Git |
|---|---|
| `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_11_INFRAESTRUCTURA_COMUN_Y_ADR002A_v0.1.md` | `2a3bc6073782a8c494206f81fbde3ab94abed1ae` |
| `SIRIUS_0.2_ADR_002_PAQUETE_CORRECCION_01_ADR002A_v0.1.md` | `ec20c36ee94c65d283bbaf0fdef2ff6fa5da2de7` |
| `SIRIUS_0.2_ADR_002_FE_DE_ERRATAS_02_CONSERVACION_DE_LA_FICHA_V1.md` | `0a34068fcba7f8d46781db3ce0b6de76d23a5b5c` |

**Infraestructura común neutral**

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/candidates/common/contracts.py` | `11f6b89049e291a200550b061624fb8b2b4dc1bb` |
| `experiments/adr002/candidates/common/engine.py` | `95cb4a4f62bbbd55f2c417a0a9b94ba21c111038` |
| `experiments/adr002/candidates/common/gates.py` | `b4361fc87f6a08a65700fe4495a692ef64e4bd48` |
| `experiments/adr002/candidates/common/stops.py` | `f63712159626bb0249d727ba9f6519e074179f5f` |
| `experiments/adr002/candidates/common/port.py` | `3a0ed12fdfc69833a51e91cc3bc9efee631017c8` |
| `experiments/adr002/candidates/common/trace.py` | `6e0a0822ad3536b06fdc8735c7def3a34ee934d6` |
| `experiments/adr002/candidates/common/derived.py` | `996e353b44fe16af035689912a6a69520ee8097e` |
| `experiments/adr002/candidates/common/neutrality.py` | `d549444f424be8c697cacd2e34fc7dc44d742830` |

**Candidato y sus pruebas**

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/candidates/adr002_a/candidate.py` | `9e8205b817ef23a03338e295d2f4b71fe4a307d4` |
| `experiments/adr002/candidates/adr002_a/lexical.py` | `549922cb61c4c8c9a067ca6bae2b6f485c107eb3` |
| `experiments/adr002/candidates/fixtures.py` | `59135f654d814e74142d78e63a5c05d5176ca54b` |
| `experiments/adr002/candidates/test_adr002_candidates_static.py` | `b6d5614a7452f79a21ce4cecdeca3c19aaf9ca8b` |
| `experiments/adr002/candidates/test_adr002_a_funcional.py` | `7a1f025062463406b8892592dd388277f782803d` |
| `experiments/adr002/candidates/test_adr002_a_e3_y_regeneracion.py` | `a1ff1852eca4acb671a33ece705cd44b9a4a0d2d` |

Cualquier modificación posterior de los contenidos de esta §2 requiere revisión
explícita y un **acto sucesor**.

## 3. Criterios de preparación declarados demostrados

Los catorce criterios quedan declarados **demostrados** en el commit auditado.
Cada uno indica dónde se comprueba.

| # | Criterio | Demostración |
|---|---|---|
| 1 | `ADR002-A` es un **candidato completo**, no `T0` ni un control | ficha v2 con `papel: CANDIDATO`, validada por la rama de candidato de `schema_card_v0_2`; el control `papel_de_control_reservado_a_t0` reserva `CONTROL` a `T0-control` |
| 2 | Implementa **`E0`–`E5`**, **`G1`–`G12`** y **`S1`–`S7`** mediante la infraestructura común | `ORDEN_DE_ETAPAS` con las seis etapas; `gates.PUERTAS` con las doce, `G1`–`G10` antes de exponer, `G11` antes de ordenar, `G12` antes del límite; `stops.PARADAS` con las siete y su constructor cada una; el candidato no implementa el motor ni las puertas ni el orden, y un control estático lo impide |
| 3 | `E3` recupera un caso **inaccesible para `E1`/`E2`** y su etapa de origen es **exactamente `E3`** | `test_el_caso_elegido_es_inalcanzable_para_e1_y_para_e2` y `test_e3_alcanza_el_caso_y_su_etapa_de_origen_es_exactamente_e3`: primero se rechazan `E1` y `E2`, después se exige `is Etapa.E3` |
| 4 | **Desactivar `E3` elimina ese resultado** | `test_desactivar_e3_hace_desaparecer_ese_resultado` |
| 5 | `E3` **expande desde semillas** mediante consultas dirigidas y acotadas | `ContextoDeEtapa.semillas` en la capa común; términos puente (≤ 8) y familias de sujeto por prefijo (≤ 4, mínimo 3 caracteres); `test_e3_expande_desde_lo_recuperado_y_no_desde_la_consulta` y `test_los_prefijos_consultados_son_concretos_y_derivados_de_las_semillas` |
| 6 | El **ámbito actúa como filtro `G4`**, nunca como generador de candidatos | `por_entidad` eliminado del puerto; un control estático exige que `candidate.py` no contenga `por_entidad` ni `ambito.proyectos`; `test_coincidir_en_ambito_sin_relacion_no_basta_para_entrar` |
| 7 | Ampliar el proyecto con elementos irrelevantes **no incrementa el trabajo observado de `E3`** | `test_ampliar_el_proyecto_no_convierte_e3_en_un_barrido`: proyecto de 11 → 41 elementos, `E3` sigue en **7 sentencias / 28 filas** y devuelve los mismos ids |
| 8 | **No existe señal vectorial ni índice relacional derivado** | `senal_tardia: ninguna_adicional` en la ficha; `neutrality.fallos_de_neutralidad` sobre el código de los siete módulos comunes: `[]` |
| 9 | El **borrado y la reconstrucción** restauran tablas, sombras, **triggers** y contenido | `test_el_borrado_hace_desaparecer_el_derivado_objeto_a_objeto` y `test_la_reconstruccion_restaura_el_inventario_y_el_contenido`: 2 tablas, 9 sombras, 8 triggers; contenido derivado idéntico |
| 10 | **Altas y modificaciones posteriores vuelven a sincronizar FTS5** | `test_tras_reconstruir_el_canon_vuelve_a_sincronizarse`: tras reconstruir, un alta se indexa sola y una modificación retira el texto anterior |
| 11 | La infraestructura común **continúa neutral** para `ADR002-A/B/C/D` | cuatro controles sobre el código de la capa común: `[]`; quinto control ejecutable, `test_el_motor_funciona_con_un_candidato_ajeno`; exclusión única y nombrada: `neutrality.py` |
| 12 | La **ficha v2 precede estrictamente** a las pruebas funcionales | entrada observada en `e15e5d0`, ancestro estricto de `e40eff4`; comprobado contra el grafo de Git por la primera prueba de ambas suites |
| 13 | El **código ejecutable cubierto por la ficha no cambió** después de congelarla | §2.5: los subárboles `common` y `adr002_a` son idénticos byte a byte entre `97c9977` y `e40eff4` |
| 14 | **No se usó el corpus oficial ni se midió rendimiento** | fixtures técnicos propios; un control lee el propio fichero fuente de cada suite y falla si aparece `perf_counter`, `timeit`, `time.time`, `p95`, `percentil` o `performance_corpus` |

### 3.1 Precisiones sobre el criterio 2, para no afirmar de más

El criterio 2 es una afirmación de **implementación**, no de cobertura de
prueba. Se precisa aquí:

- **Las doce puertas** están implementadas y **se aplican a toda candidata** en
  el orden normativo. Tienen caso de prueba discriminante `G1`, `G4`, `G6`,
  `G7`, `G8`, `G11` y `G12`. `G2`, `G3`, `G5`, `G9` y `G10` se aplican en cada
  ejecución pero el fixture no incluye hoy un elemento que las haga disparar en
  solitario.
- **Las siete paradas** están declaradas y cada una tiene su constructor. El
  motor adjudica hoy `S1`, `S2`, `S3`, `S4`, `S5` y `S6`. `S7` —fuente
  autorizada inaccesible— existe con su constructor pero **no tiene camino de
  adjudicación en el motor actual**, porque el puerto es local y no falla. Se
  registra como limitación conocida en el §6, no como cobertura.

Ninguna de estas dos precisiones afecta a los tres defectos corregidos ni a los
demás criterios.

## 4. Evidencia de verificación en el commit auditado

| Comprobación | Resultado |
|---|---|
| Verificador de fichas (`verify_cards --check`) | `RC=0` · 3 fichas conformes · 14/14 controles bloqueantes · puertas de arranque pendientes: ninguna |
| Unicidad de ficha `CONGELADA` para `ADR002-A` | **una sola**: la v2; la v1 consta `SUSTITUIDA` |
| Recomputación de las tres huellas | coinciden con las declaradas |
| Verificador de custodia (`fallos_de_identidad`) | `[]` · ninguna cita de identidad rota |
| Neutralidad de la capa común | `[]` |
| Aislamiento del candidato | `[]` |
| Ruff lint | conforme |
| Ruff format | conforme |
| mypy | sin errores |
| `experiments/adr002/candidates` | `75 passed` |
| `experiments/` | `1 261 passed` |
| repositorio (`tests/`) | `1 195 passed` |
| Quality (GitHub Actions) sobre `e40eff4` | **success** |

## 5. Estado tras esta acta

| Elemento | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-208` | **SATISFECHA** |
| `ADR002-TOL-209` | **SATISFECHA** |
| `ADR002-TOL-210` | **SATISFECHA** |
| **`ADR002-A`** | **PREPARADO PARA BENCHMARK** — por esta acta |
| `T0-control` | ficha `CONGELADA`; rederivación aprobada |
| `ADR002-B`, `ADR002-C`, `ADR002-D` | **NO IMPLEMENTADOS** |
| `EJE-1`, `EJE-2` | **NO ABIERTOS** |
| Benchmark | **NO EJECUTADO · ejecución no autorizada** |
| PR #117 | **ABIERTO y SIN FUSIONAR** |

### 5.1 Por qué esta acta no toca ningún verificador

`ADR002-A` **no es una puerta**, y el repositorio no tiene —ni esta acta
inventa— un registro legible por máquina de preparación por candidato. El
mecanismo que sí existe, `card_protocol.estado_de_las_puertas`, deriva el
estado de las **puertas de arranque** de las actas presentes, y esta acta no
crea ni satisface ninguna puerta nueva.

El único mecanismo que ya reconoce a un candidato,
`card_protocol.ejecutabilidad`, exige las cinco puertas de arranque y una ficha
`CONGELADA`. Ambas condiciones **ya se cumplían** antes de esta acta, de modo
que no hay nada que actualizar: esta acta **no cambia** lo que la máquina
comprueba, sino que **registra el juicio de gobierno** sobre un material que la
máquina ya validaba.

Se hace notar expresamente, porque importa para no confundir dos cosas:
`ejecutabilidad` significa «tiene ficha vigente y las puertas están
satisfechas», **no** «está autorizado a ejecutarse». La autorización de
ejecución es un acto de gobierno y hoy no existe.

## 6. Limitaciones conocidas registradas

1. **Una ficha no acredita un candidato.** Acredita que sus límites se
   congelaron antes, completos y coherentes. Si `ADR002-A` los cumple es cosa
   del benchmark, que no está autorizado.
2. **Los límites de la ficha v2 proceden de análisis estático**, no de
   medición. El de `E3` subió de 5 a 8 ms por el cambio de tipo de su camino, y
   así está escrito en la propia ficha. Ninguna medición los respalda porque
   ninguna existe.
3. **`S7` no tiene camino de adjudicación** en el motor actual (§3.1).
4. **`G2`, `G3`, `G5`, `G9` y `G10` no tienen caso discriminante** en el
   fixture (§3.1).
5. **Las pruebas usan fixtures propios**, de una docena de elementos, elegidos
   para ejercitar reglas. No dicen nada sobre comportamiento a escala.
6. **`LIKE 'prefijo%'` sobre `subject_key` y `subject` no está indexado** por la
   cadena canónica. La consulta es dirigida y devuelve como mucho 64 filas, pero
   su plan de acceso recorre la tabla. El límite de `E3` lo contempla; no se
   añade ningún índice, porque modificar Sirius 0.1 no está autorizado.
7. **Un solo entorno.** Todo es `LAB-LINUX`.
8. **La anterioridad se apoya en el grafo de Git**: un historial reescrito la
   invalidaría —comportamiento querido—, pero la garantía es tan fuerte como la
   custodia del repositorio.

## 7. Lo que esta acta no autoriza

- **No autoriza ejecutar `ADR002-A` sobre el corpus oficial.**
- **No autoriza ejecutar el benchmark.**
- **No autoriza medir rendimiento** de ningún candidato.
- No modificar la ficha v2 ni ningún límite congelado.
- No implementar `ADR002-B`, `ADR002-C` ni `ADR002-D`.
- No abrir `EJE-1` ni `EJE-2`.
- No elegir ganador ni declarar arquitectura final.
- No autorizar uso productivo.
- No modificar Sirius 0.1 (`src/`, `tests/`, `migrations/` ni configuración
  productiva).
- No abrir otro PR.
- **No fusionar el PR #117.**

## 8. Reglas de custodia que siguen vigentes

1. Toda ficha se congela **antes** de la primera ejecución de su candidato, y
   la anterioridad se comprueba contra el grafo de Git, no contra una fecha.
2. Una ejecución que no referencie una ficha previa por `candidato · versión ·
   huella` **no es utilizable como evidencia**.
3. **Una sola ficha `CONGELADA` por candidato.** Publicar una sucesora obliga a
   marcar `SUSTITUIDA` la anterior y a **repetir** las ejecuciones hechas bajo
   ella.
4. Las versiones de ficha crecen de una en una y nunca retroceden.
5. Una ficha sustituida **se marca, no se borra ni se reescribe**: se conserva
   su contenido normativo y su blob original en el historial.
6. Cualquier cambio de los contenidos vinculados en §2 exige revisión y un
   **acto sucesor**.
7. La evidencia publicada no se reescribe: los errores se declaran mediante fe
   de erratas y documento sucesor.
8. Las etiquetas internas `PROPUESTO` permanecen como historia auditada y no
   disminuyen la autoridad de esta acta.

---

**Decisión final:** `ADR002-A` queda **APROBADO como PREPARADO PARA
BENCHMARK**, con el alcance exacto del §1 y ni un milímetro más. La ejecución
del benchmark, la medición del candidato, la implementación de
`ADR002-B/C/D`, la apertura de `EJE-1` y `EJE-2`, la elección de ganador y la
fusión del PR #117 **continúan no autorizadas**.

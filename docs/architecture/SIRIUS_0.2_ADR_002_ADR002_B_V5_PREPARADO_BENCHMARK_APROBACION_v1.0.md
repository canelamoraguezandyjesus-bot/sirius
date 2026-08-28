# SIRIUS 0.2 — ADR-002 · Aprobación de `ADR002-B` v5 como PREPARADO PARA BENCHMARK

**Versión:** 1.0
**Estado:** **APROBADO · `ADR002-B` v5 PREPARADO PARA BENCHMARK**
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado:** `18efacff3b7a8e82483f8cd78d6e3c15077a891c`
**Autorización explícita del usuario:** «Apruebo»

## 0. Objeto y alcance

Esta acta materializa la decisión explícita del usuario, expresada literalmente
como **«Apruebo»**, y registra el estado:

> **`ADR002-B` v5: PREPARADO PARA BENCHMARK**

**Contexto inmediato que cierra su interpretación.** La respuesta se produjo
inmediatamente después de la recomendación expresa «Aprobar `ADR002-B` v5 como
PREPARADO PARA BENCHMARK», formulada al término de la corrección 04 y de su fe
de erratas. Por tanto:

1. se refiere **únicamente** a `ADR002-B` **v5**, la ficha vigente;
2. **no autoriza ninguna ejecución** —ni del benchmark, ni de `ADR002-B`
   aisladamente—;
3. no modifica, amplía ni sustituye la decisión vigente sobre `ADR002-A` v3.

La aprobación acepta, para `ADR002-B` v5: su realización experimental como base
`ADR002-A` v3 más señal semántica vectorial tardía en `E3`; su composición sobre
`ADR002-A` v3; la materialización por identidad canónica exacta; su índice
vectorial local, determinista, sin red, sin API y regenerable desde el canon; la
validación lógica del sidecar; la diferenciación entre corrupción, desfase e
inconsistencia; las cotas de longitud y representabilidad incorporadas por la fe
de erratas 04; la minimización de los mensajes de corrupción y apertura; el
cierre de conexiones en las rutas declaradas; la ficha vigente v5; las pruebas
funcionales ejecutadas después de congelarla; la custodia y la anterioridad de
la evidencia; y los límites declarados, **todavía sujetos a comprobación futura
mediante benchmark**.

## 1. Qué significa exactamente PREPARADO PARA BENCHMARK

### 1.1 Significa, y solo esto

| # | Significado |
|---|---|
| 1 | **Implementación experimental identificada**: `ADR002-B` existe como candidato ejecutable, con identidad fijada por SHA, blob, árbol y huella (§3). |
| 2 | **Ficha v5 congelada**: `ficha_ADR002-B_v5.json`, `CONGELADA`, huella recomputable, sin ningún resultado observado del candidato. |
| 3 | **Custodia válida**: anterioridad estricta de la ficha frente a las pruebas, unicidad de ficha `CONGELADA` para B, identidades que resuelven o constan inventariadas, evidencia previa no reescrita. |
| 4 | **Pruebas funcionales superadas**: las suites completas de B, repetidas bajo la v5 (§6). |
| 5 | **Limitaciones conocidas declaradas**: las de §7, visibles y no resueltas. |
| 6 | **Aptitud para recibir posteriormente una autorización conjunta de la primera ronda**: el material de gobierno está completo para que esa autorización pueda decidirse. |

### 1.2 No significa, en ningún grado

| # | Lo que **no** se afirma |
|---|---|
| 1 | **Benchmark ejecutado.** No se ha ejecutado. |
| 2 | **Rendimiento validado.** No existe ni una sola cifra de rendimiento de `ADR002-B`. |
| 3 | **Candidato ganador.** No hay comparación alguna. |
| 4 | **Arquitectura final aprobada.** No lo es. |
| 5 | **Tecnología productiva aprobada.** Esta acta **no aprueba** embeddings, proveedor ni almacenamiento para producción (`ARQ-00 §23`, `B04-RF-31`). |
| 6 | **Ejecución aislada autorizada.** Ejecutar `ADR002-B` por separado tampoco está autorizado. |
| 7 | **Fusión del PR autorizada.** El PR #117 permanece abierto y sin fusionar. |

**La ejecución sigue bloqueada.** Autorizar la primera ronda sobre el corpus
oficial es un acto de gobierno distinto, posterior, independiente y **conjunto**
para los candidatos.

## 2. Autorización literal

> **«Apruebo»**

Registrada tal cual, con el contexto de §0. No se le atribuye ningún alcance
adicional: no se extiende a la ejecución, ni a otros candidatos, ni a versiones
distintas de la v5.

## 3. Identidad vinculante: SHA, blobs, árboles y huella

Todos los valores han sido **resueltos directamente desde Git en el commit
auditado**, no copiados de ningún informe.

### 3.1 Ficha vigente de `ADR002-B`

| Campo | Valor |
|---|---|
| Ruta | `artifacts/adr002_cards/ficha_ADR002-B_v5.json` |
| Blob | `b9ddf6de393e21bebdd3d0eab1e182aa069053e3` |
| Huella canónica declarada | `b27866b1278f37473fa6151ab7f26df7386bcd81` |
| Huella **recomputada** sobre la forma canónica | `b27866b1278f37473fa6151ab7f26df7386bcd81` — **coincide** |
| Versión / Estado / Sustituye a / Papel | `5` / `CONGELADA` / `4` / `CANDIDATO` |
| Señal tardía declarada | `semantica_vectorial` |
| `no_contiene_resultados` | `true` |
| Commit de referencia declarado | `317ad5fc406012c5a8684b57f8e53d61ff9fd7c0` (fe de erratas 04) |
| Commit de entrada observado en Git | `96e90c58e6bc021509cf5757c93f692cc74bc4f4` |

### 3.2 Código y documentación vinculados

| Artefacto | Blob |
|---|---|
| `experiments/adr002/candidates/adr002_b/vectores.py` | `f8d92722e7a9da3c7b4846e57ab2e34c4c396581` |
| `experiments/adr002/candidates/adr002_b/candidate.py` | `a6d5bd36ca72fb9828a29145cee7506b1375732b` |
| `docs/architecture/SIRIUS_0.2_ADR_002_FE_DE_ERRATAS_04_ESCAPES_SIN_TIPAR_DE_ADR002B_v1.0.md` | `be4815550e0a01f2a89e24387ba4eaff6fa68bb2` |

### 3.3 Árboles

| Subárbol | Hash | Nota |
|---|---|---|
| `experiments/adr002/candidates/adr002_b` | `43eaa374d6eef827599472588a54494be9704565` | **fuente propia cubierta por la huella de la v5** |
| `experiments/adr002/candidates/common` | `a83539e3c8b5396371b355619a29478cad054834` | infraestructura común, **sin cambios** |
| `experiments/adr002/candidates/adr002_a` | `2d90b551445db340458278a5accad55372995b76` | base por composición, **sin cambios** |
| `experiments/adr002/candidates` | `ac016a045565298954edbe8671cb79758de1b559` | árbol de candidatos en el commit auditado |

### 3.4 Ancestralidad completa, comprobada contra el grafo

`575378b` (implementación corregida) → `96e90c5` (entrada de la ficha v5) →
`8fc4f74` (pruebas posteriores) → `18efacf` (commit auditado). **Cada uno es
ancestro estricto del siguiente**, y la ficha precede estrictamente a toda
ejecución que la cita.

### 3.5 Estabilidad de la fuente congelada

El árbol propio de `ADR002-B` es **`43eaa374…` en los cuatro commits** de §3.4:
implementación, entrada de la ficha, pruebas y commit auditado. **Después de la
entrada de la ficha v5 no cambió ninguna fuente incluida en su huella.** Los
únicos cambios posteriores afectan a ficheros de prueba y a la documentación de
custodia, que no forman parte de esa huella.

### 3.6 Fichas históricas de `ADR002-B`

| Versión | Estado | Huella |
|---|---|---|
| v1 | `SUSTITUIDA` | `351413b91dcb0d7b37d184bd7779fb2f6a56d0a5` |
| v2 | `SUSTITUIDA` | `11b2a881a1126e77fcd6196ba7837274ee426918` |
| v3 | `SUSTITUIDA` | `1c639d37ca6af5d5d6921c4695ba049325f01270` |
| v4 | `SUSTITUIDA` | `28017d9502ce9850071426329f0b2e75e2bd7826` |
| **v5** | **`CONGELADA`** | **`b27866b1278f37473fa6151ab7f26df7386bcd81`** |

Ninguna se borra ni se reescribe: se conservan marcadas, con su contenido
normativo íntegro en el historial de Git.

## 4. La cadena de corrección que condujo a la v5

| Hito | Qué aportó |
|---|---|
| Paquete de trabajo 12 | prototipo original de `ADR002-B` por composición y ficha v1 |
| **Corrección 02** | **materialización por identidad canónica**: la ruta vectorial deja de materializar por clave de sujeto y pide al puerto los identificadores exactos (`por_identificadores`); una identidad ausente del canon falla cerrada. Ficha v2 |
| Fe de erratas 03 | registro de las limitaciones conocidas de B, sin reescribir la evidencia |
| **Corrección 03** | **validación lógica del sidecar**: identidades, JSON de vectores, normas exactas, referencias `posting`↔vector, aritmética de similitud; traducción tipada, **minimización de mensajes**, defensa en la frontera con el puerto y descarte de pesos que redondean a cero. Ficha v3 |
| **Corrección 04** | **validación canónica de la huella persistida** y **minimización de los mensajes de apertura**: distinción entre corrupción y desfase, causas preservadas sin reproducir el texto de SQLite, y eliminación de la ruta del entorno. Ficha v4 |
| **Fe de erratas 04** | reconocimiento y **cierre de los cuatro escapes sin tipar** hallados por la auditoría adversarial sobre el propio resultado: cota de dígitos en los conteos, cota de longitud del vector antes de deserializar más traducción de `RecursionError`, cota de representabilidad de la identidad, y cierre de conexión en la recomputación del canon. Corrige además dos afirmaciones excesivas del texto de la v4. **Ficha v5** |
| Pruebas posteriores a la v5 | los cuatro escenarios exactos que antes escapaban, más la repetición íntegra de las suites de B |
| Correcciones posteriores | **exclusivamente de cobertura** (corrupción en cascada entre iteraciones, aserción tautológica, recuento por línea) y de una entrada obsoleta de custodia: **no alteraron ninguna fuente congelada** (§3.5) |

## 5. Criterios declarados demostrados

Cada criterio se declara demostrado **con su evidencia ejecutable verificada en
el commit auditado**; las pruebas citadas se ejecutaron y pasaron.

| # | Criterio | Demostración |
|---|---|---|
| 1 | B sigue siendo **candidato completo, no control** | ficha v5 con `papel: CANDIDATO`, validada por la rama de candidato de `schema_card_v0_2`; el papel `CONTROL` sigue reservado a `T0-control` |
| 2 | **B = `ADR002-A` v3 + señal semántica vectorial tardía** | `test_la_composicion_delega_en_a_y_no_copia_su_logica`; `test_b_sin_senal_vectorial_es_exactamente_a` (identidad id a id con A); `test_la_composicion_documenta_la_base_vigente_a_v3` |
| 3 | La señal vectorial **solo se activa en `E3`** tras la insuficiencia de `E1`/`E2` | guarda `contexto.etapa is not Etapa.E3` en `candidate.py`; el motor común posee el bucle de etapas |
| 4 | **`E1`/`E2` suficientes no abren ni consultan el sidecar** | `test_si_e1_satisface_la_ruta_vectorial_se_invoca_cero_veces` y `test_si_e2_satisface_…`: contador a cero y sidecar **inexistente a propósito**, que reventaría con error tipado si alguien lo tocara |
| 5 | Existe una **ablación técnica** que B recupera y A no | `test_b_recupera_el_objetivo_y_su_etapa_de_origen_es_exactamente_e3` y `test_desactivar_la_senal_vectorial_hace_desaparecer_el_objetivo` |
| 6 | La **similitud no sustituye identidad, verdad ni validación semántica** | las candidatas vectoriales se devuelven en **una sola lista** con las de la base y pasan por las mismas puertas `G1`–`G12`; la lectura semántica es la misma de A, item a item (`CandidatoB.leer` delega en la base) |
| 7 | **Sujeto, ámbito, polaridad y tiempo** pasan por las mismas puertas | suite funcional de B: ámbito como filtro `G4` con coseno 1,0 exacto, vigencia, polaridad conservada, corte temporal, `G11`, `G12` |
| 8 | Una **clave vacía no elimina** una coincidencia | `test_una_clave_vacia_no_pierde_la_coincidencia` |
| 9 | **Claves duplicadas no cambian la identidad** | `test_una_clave_duplicada_no_cambia_la_identidad`: solo el id solicitado se materializa; el de la gemela no aparece en ningún parámetro |
| 10 | **Más de 512 filas con una clave no ocultan el objetivo** | `test_el_objetivo_tras_512_filas_de_la_misma_clave_se_recupera`, con la premisa probada primero (la ruta antigua devolvía 512 filas **sin** el objetivo) |
| 11 | La **materialización es por identificador exacto** | `candidate.py` pide `por_identificadores` con los ids del sidecar; control estático `test_b_materializa_por_identidad_y_nunca_por_clave` (ausencia de `por_clave_exacta` en la ruta vectorial) |
| 12 | Un **identificador canónico ausente** produce fallo cerrado sin recuperación parcial | `IndiceInconsistenteError` lanzado **antes** de construir ninguna `Candidata`; prueba de identidad inconsistente de extremo a extremo por el motor |
| 13 | **Corrupción física** tratada conforme a la ficha | `test_un_indice_corrupto_falla_cerrado`, `test_una_base_ilegible_es_corrupcion`, error físico con centinela traducido con causa preservada |
| 14 | **Corrupción lógica** tratada conforme a la ficha | 18 formas de JSON corrupto, normas corruptas, 11 formas de identidad corrupta, referencias huérfanas e incoherentes y aritmética imposible, todas `IndiceCorruptoError` |
| 15 | Los **mensajes de corrupción y apertura no reproducen celdas** | control estático de interpolaciones sobre todo el fuente; `test_la_apertura_no_reproduce_la_huella_ni_el_error_fisico`; barrido que planta el mismo texto protegido en **cada** celda de metadatos, restaurando entre iteraciones, y comprueba que **cada una alcanza su propia rama** |
| 16 | Las identidades de `IndiceInconsistenteError` son **canónicas y acotadas** | por el contrato explícito de la corrección 02 —que esta acta no altera— y por la cota de representabilidad de la fe de erratas 04: `test_la_identidad_persistida_es_representable_por_el_puerto` |
| 17 | **Corrupción, desfase e inconsistencia** son distinguibles | `test_el_formato_invalido_es_corrupcion_y_el_valor_distinto_es_desfase`; `test_una_huella_canonica_distinta_es_desfase_sin_reproducirla`; `test_el_desfase_real_por_cambio_del_canon_sigue_siendo_desfase` |
| 18 | Las **cotas de la fe de erratas 04** están implementadas y probadas | `test_el_conteo_se_acota_en_digitos_antes_de_convertirlo`; `test_el_vector_se_acota_en_longitud_antes_de_deserializar`; `test_un_conteo_de_miles_de_digitos_es_corrupcion_tipada`; `test_un_vector_con_anidamiento_profundo_es_corrupcion_tipada`; `test_una_identidad_no_representable_no_llega_al_puerto` |
| 19 | El índice es **derivado, no autoritativo, borrable y reconstruible** | `test_borrado_completo_y_reconstruccion_identica` (igualdad de volcado lógico), `test_la_construccion_es_determinista`, borrado de `.db`, `-wal`, `-shm` y `-journal` comprobado fichero a fichero |
| 20 | La construcción **no usa corpus oficial, etiquetas esperadas ni resultados del benchmark** | `test_el_paquete_no_referencia_el_corpus_oficial`; origen exclusivo declarado: memorias vigentes y decisiones aprobadas del canon |
| 21 | **No hay red, API, modelo descargado ni proveedor externo** | `test_ningun_modulo_del_paquete_mide_ni_abre_red`, que lee el fuente crudo de todos los módulos del paquete |
| 22 | Las pruebas posteriores son **descendientes estrictas** de la ficha | guarda de anterioridad en cada suite (`test_la_ficha_b_es_anterior_estricta_a_esta_ejecucion`), comprobada contra el grafo de Git |
| 23 | **Ninguna fuente congelada cambió** tras emitir la v5 | §3.5: árbol `adr002_b` idéntico en los cuatro commits de la cadena |
| 24 | **Quality verde** y **benchmark no ejecutado ni medido** | Quality `success` sobre el commit auditado; `no_contiene_resultados: true`; controles anti-medición en cada suite; no existe ningún artefacto de resultados de B |

### 5.1 Precisión sobre el criterio 7, para no afirmar de más

La **condición** (marcadores de condicionalidad) se valida por el mismo camino
que en `ADR002-A` —la lectura semántica es literalmente la de la base— y las
candidatas vectoriales atraviesan las mismas puertas por construcción. Sin
embargo, **el fixture técnico de B no incluye hoy un elemento condicional
alcanzable por el canal vectorial**, de modo que para la condición existe
demostración **estructural**, no un caso funcional discriminante propio de esa
ruta. Se registra como precisión, no como cobertura.

Se hace notar también que la deduplicación normativa de `E5` sigue agrupando por
`(clave de sujeto, proyecto, polaridad)`: eso es agrupación de resultados del
motor común, no sustitución de identidad, y es independiente de la
materialización por identificador exacto del criterio 11.

## 6. Evidencia de verificación en el commit auditado

| Comprobación | Resultado |
|---|---|
| Verificador de fichas (`verify_cards --check`) | **RC=0** · 9 fichas conformes · 14/14 controles bloqueantes · puertas de arranque pendientes: ninguna |
| Unicidad de ficha `CONGELADA` para `ADR002-B` | **una sola**: la v5; v1–v4 constan `SUSTITUIDA` |
| Recomputación de las nueve huellas | coinciden con las declaradas |
| Verificador de custodia (`fallos_de_identidad`) | `[]` |
| Neutralidad de la capa común | `[]` |
| Aislamiento de `ADR002-A` / de `ADR002-B` | `[]` / `[]` |
| Ruff format | conforme (358 ficheros) |
| Ruff lint | conforme |
| mypy | sin errores (236 ficheros) |
| repositorio (`tests/`) | `1 195 passed` |
| `experiments/` | `1 473 passed` |
| Quality (GitHub Actions) sobre `18efacf` | **success** |

## 7. Limitaciones conocidas aceptadas como NO bloqueantes

La aprobación se concede **con estas limitaciones todavía abiertas**:

1. la ventana de **4 096 elementos examinados** se aplica antes de las
   exclusiones;
2. un **canon ilegible** durante la recomputación de la huella puede escapar sin
   el error tipado específico del índice —si bien la conexión del sidecar **sí**
   se cierra desde la fe de erratas 04—;
3. la **ventana concurrente** entre las lecturas de `construir` (TOCTOU);
4. el **techo de almacenamiento** del sidecar está declarado pero no autoimpuesto
   por el código;
5. posibles **diferencias de `libm`** entre entornos (√ y ln en la construcción y
   el coseno);
6. posible **creación accidental de un fichero vacío** por `sqlite3.connect` en
   utilidades mal invocadas;
7. ausencia de **cierre explícito del lector** durante su vida normal (el cierre
   nuevo solo cubre las rutas de fallo);
8. **`S7`** existe con su constructor, pero el **motor común no posee camino de
   adjudicación** para esa parada;
9. dos huecos conocidos del **verificador de fichas**, fuera del ámbito de B:
   detecta múltiples fichas `CONGELADA` por candidato pero **no necesariamente
   cero**, y alguna ruta publica `anterioridad_comprobada_contra_git` sin
   ejercitar completamente esa comprobación.

Se aclara expresamente:

- estas limitaciones **no se declaran resueltas**;
- **no se aprueban como decisiones productivas**;
- **deben permanecer visibles durante la primera ronda**;
- **pueden convertir al candidato en fallo o en NO EVALUABLE** si afectan a la
  ejecución;
- **no impiden identificar y congelar el candidato** para comparación, que es
  exactamente lo que este acta hace y nada más.

## 8. Estado de `ADR002-A`

> **`ADR002-A` v3: PREPARADO PARA BENCHMARK**

Su ficha (`b3ce920e6dc0ee62a0358f8bfb9762dcac0d64d7`, huella
`427905a06f6c12666a09c73b8720e229f17eeef3`) y su acta de reaprobación
(`f2babe06a8c883924a464df6fc96d14f52da367d`) permanecen **intactas byte a byte**,
verificadas en el commit auditado y aseveradas por pruebas de la propia suite.

Esta aprobación de `ADR002-B` **no modifica, no amplía, no sustituye y no vuelve
a aprobar** la decisión vigente sobre `ADR002-A`.

## 9. Por qué esta acta no toca ningún verificador

`ADR002-B` **no es una puerta**, y el repositorio no tiene —ni esta acta
inventa— un registro legible por máquina de preparación por candidato, ni una
puerta nueva, ni un campo nuevo en las fichas, ni una autorización de ejecución.
Se comprobó expresamente: el estado `PREPARADO PARA BENCHMARK` **no aparece en
ningún mecanismo del código**. Igual que en `ADR002-A`, el acta documental **es**
el registro del estado: recoge el juicio de gobierno sobre un material que la
máquina ya validaba, sin cambiar lo que la máquina comprueba.

`card_protocol.ejecutabilidad` significa «tiene ficha vigente y las puertas están
satisfechas», **no** «está autorizado a ejecutarse». La autorización de ejecución
es un acto de gobierno y hoy no existe.

## 10. Estado del tablero tras esta acta

| Elemento | Estado |
|---|---|
| `T0-control` | **INTACTO** |
| **`ADR002-A` v3** | **PREPARADO PARA BENCHMARK** (por su acta de reaprobación, intacta) |
| **`ADR002-B` v5** | **PREPARADO PARA BENCHMARK** — por esta acta |
| `ADR002-B` v1–v4 | **SUSTITUIDAS**, conservadas como historial |
| `ADR002-C` | **NO IMPLEMENTADO** |
| `ADR002-D` | **NO IMPLEMENTADO** |
| `EJE-1`, `EJE-2` | **NO ABIERTOS** |
| Benchmark | **NO AUTORIZADO y NO EJECUTADO** |
| Ganador | **NO ELEGIDO** |
| Sirius 0.1 | **NO MODIFICADO** |
| PR #117 | **ABIERTO y SIN FUSIONAR** |

## 11. Lo que esta acta no autoriza

- **No autoriza ejecutar el benchmark.**
- **No autoriza usar el corpus oficial** ni los casos oficiales.
- **No autoriza medir rendimiento** de ningún candidato.
- **No autoriza ejecutar `ADR002-B` aisladamente.**
- No elegir ganador ni declarar arquitectura final.
- No aprobar una arquitectura productiva, ni embeddings, proveedor o
  almacenamiento para producción.
- No implementar `ADR002-C` ni `ADR002-D`.
- No abrir `EJE-1` ni `EJE-2`.
- No modificar Sirius 0.1, `ADR002-A`, la capa común ni ninguna ficha.
- **No fusionar el PR #117.**

## 12. Reglas de custodia que siguen vigentes

1. Toda ficha se congela **antes** de la primera ejecución de su candidato, y la
   anterioridad se comprueba contra el grafo de Git, no contra una fecha.
2. Una ejecución que no referencie una ficha previa por `candidato · versión ·
   huella` **no es utilizable como evidencia**.
3. **Una sola ficha `CONGELADA` por candidato.** Publicar una sucesora obliga a
   marcar `SUSTITUIDA` la anterior y a **repetir** las ejecuciones hechas bajo
   ella — regla ya cumplida cuatro veces por `ADR002-B`.
4. Las versiones de ficha crecen de una en una y nunca retroceden.
5. Una ficha sustituida **se marca, no se borra ni se reescribe**.
6. Cualquier cambio de los contenidos vinculados en §3 exige revisión y un
   **acto sucesor**.
7. La evidencia publicada no se reescribe: los errores se declaran mediante fe
   de erratas y documento sucesor — como se hizo con las erratas 03 y 04.

---

**Decisión final:** `ADR002-B` v5 queda **APROBADO como PREPARADO PARA
BENCHMARK**, con el alcance exacto del §1 y ni un milímetro más, y con las
limitaciones del §7 expresamente aceptadas como no bloqueantes **para congelar e
identificar al candidato**, no para su resultado. La ejecución del benchmark, el
uso del corpus oficial, la medición de rendimiento, la ejecución aislada de
`ADR002-B`, la implementación de `ADR002-C/D`, la apertura de `EJE-1` y `EJE-2`,
la elección de ganador y la fusión del PR #117 **continúan no autorizadas**.

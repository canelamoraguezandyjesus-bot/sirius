# SIRIUS 0.2 — ADR-002 · Aprobación de `ADR002-C` v2 como PREPARADO PARA BENCHMARK

**Versión:** 1.0
**Estado:** **APROBADO · `ADR002-C` v2 PREPARADO PARA BENCHMARK**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**Commit auditado:** `94664daed9a9f640e6e3609a02bd57ded13ed71a`

**Autoridad:** pasos **8 y 9** del plan aprobado por
`..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4 — «implementar, congelar y
probar `ADR002-C`».

**Acto de aprobación:** el usuario, directamente en el chat de trabajo, respondió
**«Sí, apruebo C v2»** a la solicitud única presentada sobre este HEAD.

---

## 1. Lo aprobado

| Ficha | Estado | Huella canónica | Sustituye a |
|---|---|---|---|
| `ficha_ADR002-C_v2.json` | **CONGELADA · PREPARADO PARA BENCHMARK** | `5e034078eb1d01ef6485cfd10707ce30f92ed7e5` | v1 |

Se aprueba **la ficha v2 y la implementación que identifica**, con el alcance
exacto del §5 y ni un milímetro más.

---

## 2. Por qué hubo dos versiones y no una

La v1 se presentó a aprobación y **el usuario la rechazó por un defecto
documental de la propia ficha, no de la implementación**: se derivó de la ficha
de `ADR002-B` y arrastró texto ajeno —señal vectorial, sidecar, similitud,
coseno, PPMI, `vectores.py`, `CandidatoB`, y el ciclo y la purga de un índice
que `ADR002-C` no tiene—, y además citaba como vigente `A v3` cuando la base
aprobada es `A v5`.

La corrección ordenada fue **exactamente una y sólo una**: emitir una sucesora
append-only que reparase la ficha **sin cambiar la implementación ni su
semántica**. La v2 se deriva de **`A v5`**, que es la base real de `C` y que
tampoco declara índice derivado propio; por eso sustrato léxico, ciclo de
índice, purga y puertas previas son **literalmente los de `A`**, y sólo se
sobrescribe lo propio de `C`.

| Campo | v1 (derivada de `B`) | v2 (derivada de `A v5`) |
|---|---|---|
| Base citada | `A v3`, ya sustituida | **`A v5`**, la aprobada |
| Índices no léxicos | heredaba el sidecar vectorial de `B` | **fuente relacional**; `C` no construye índice derivado |
| Ciclo de índice y purga | ciclo y purga del índice vectorial | los de `A`: **no hay índice derivado que purgar** |
| Coste de `E3` | 3 ms heredados de la base | **8 ms**, el presupuesto propio de la señal relacional |
| `almacenamiento.consumo_declarado_b` | valor del sidecar de `B` | **0** |
| Léxico ajeno | vectorial, sidecar, similitud, coseno, PPMI | **eliminado** |

La v1 **no se borra**: queda `SUSTITUIDA`, huella
`2472615eef2159fe22a2accd053db3b58df21e50`, con su contenido íntegro en el
historial.

---

## 3. Identidad vinculante, resuelta desde Git en el commit auditado

### 3.1 Fichas

| Ruta | Blob | Estado | Huella |
|---|---|---|---|
| `artifacts/adr002_cards/ficha_ADR002-C_v2.json` | `0828f8592debb2593da36a93b9fb8787321c8297` | **CONGELADA** | `5e034078eb1d01ef6485cfd10707ce30f92ed7e5` |
| `artifacts/adr002_cards/ficha_ADR002-C_v1.json` | `d1f7d9757a549827fa3f5ad64b50eba81c0f4451` | `SUSTITUIDA` | `2472615eef2159fe22a2accd053db3b58df21e50` |

### 3.2 Árboles y fuentes

| Artefacto | Hash | Nota |
|---|---|---|
| `experiments/adr002/candidates/adr002_c` | `6767fb9f3bc276fe0361174c300634dc0cef4860` | **fuente propia, byte a byte igual que en la v1** |
| `experiments/adr002/candidates/common` | `30984c1f054fc47b12f708fad23ddf617a46645c` | capa común corregida por el paso 5, **sin cambios** |
| `experiments/adr002/candidates/adr002_a` | `ceb4247c9fee913ae86d5203f199b19341f1c833` | base por composición, **sin cambios** |
| `experiments/adr002/candidates` | `27b0a6f6f49f88fe56f90daae151e28808e0c130` | árbol de candidatos en el commit auditado |
| `experiments/adr002/candidates/adr002_c/relaciones.py` | `0512093878c73c795ea165db91fda5fb3398a953` | fuente relacional |
| `experiments/adr002/candidates/adr002_c/candidate.py` | `f70c6f36a2b24bb9eccc4143ce989e7bc99127db` | candidato |

**Que el árbol propio de `C` sea el mismo en la v1 y en la v2 es la prueba
material de que la reparación tocó únicamente la ficha**, que es lo que el
usuario ordenó.

`src/sirius` sigue en `6d8558ef1fe4994cb15a12967525bf3496b3c0b8`: **`T0-control
v1` no se ve afectada.**

---

## 4. Lo que `ADR002-C` es, y cómo se demuestra

`ADR002-C` = base léxica/estructurada de `ADR002-A` **más señal relacional
explícita únicamente en etapas tardías**, tras fallar la puerta de suficiencia.

| # | Criterio | Demostración ejecutable |
|---|---|---|
| 1 | La señal es **relacional, no de forma**: un salto, aristas salientes | `test_un_solo_salto_declarado`, `test_la_direccion_se_respeta` |
| 2 | `SUSTITUYE_A` y `CONFLICTO_CON` **no expanden** | `test_los_dos_tipos_que_otra_regla_adjudica_no_expanden`, `test_una_supersesion_no_expande_y_se_declara` — los adjudican `G7` y la parada `S6` |
| 3 | Existe una **ablación discriminante**: `C` alcanza lo que `A` no | `test_a_alcanza_la_semilla_y_no_el_destino` + `test_c_alcanza_el_destino_por_la_arista_explicita` |
| 4 | El alcance es **atribuible a una arista concreta** | `test_borrar_la_arista_elimina_el_alcance`, `test_sin_la_arista_ese_alcance_desaparece` |
| 5 | Sin la señal, `C` **es exactamente `A`** | `test_la_ablacion_deja_a_c_identico_a_a` |
| 6 | **Control positivo**: el destino no es inalcanzable por otra vía | `test_el_destino_es_recuperable_por_su_propia_consulta`, `test_el_destino_es_recuperable_por_una_consulta_propia` |
| 7 | El destino **no entra por la puerta de atrás**: supera las puertas comunes | `test_el_destino_supera_las_puertas_comunes` |
| 8 | La señal **no puede adelantarse**: apertura perezosa dentro de `E3` | `test_el_plano_no_se_abre_cuando_las_etapas_tempranas_bastan` (contador a cero) |
| 9 | Acceso **dirigido y acotado**, nunca barrido | `test_el_plano_se_abre_una_sola_vez_y_consulta_dirigido`; 16 semillas, 64 aristas, materialización por identidad exacta |
| 10 | **Fallo cerrado** ante grafo inválido | plano ausente, tipo desconocido, extremo vacío, bucle, destino inexistente en el canon: cinco pruebas, ninguna degrada a recuperación parcial (`test_la_corrupcion_no_se_degrada_a_recuperacion_parcial`) |
| 11 | **No toca el oráculo** | `test_c_no_nombra_nada_del_oraculo` (paramétrica sobre la lista prohibida), `test_c_no_selecciona_la_nota_de_ninguna_relacion` |
| 12 | **Determinista** | `test_c_es_determinista` |
| 13 | **No reimplementa el motor ni las puertas**, y la capa común sigue sin nombrar candidatos | `test_c_no_reimplementa_el_motor_ni_las_puertas`, `test_la_capa_comun_sigue_sin_nombrar_a_ningun_candidato` |
| 14 | **No hay índice derivado propio** que declarar, purgar ni presupuestar | las relaciones son entrada declarada del corpus, disponible **por igual** para los cuatro candidatos |

---

## 5. Qué significa exactamente PREPARADO PARA BENCHMARK

### 5.1 Significa, y sólo esto

1. **Implementación experimental identificada**, con identidad fijada por blob y
   árbol (§3).
2. **Ficha v2 congelada**, huella recomputable, `no_contiene_resultados: true`.
3. **Custodia válida**: anterioridad estricta de la ficha frente a las pruebas
   que la citan, una sola ficha `CONGELADA` para `C`, evidencia previa no
   reescrita.
4. **Pruebas funcionales superadas** (§6).
5. **Aptitud para recibir después la autorización conjunta de la ronda
   primaria.**

### 5.2 No significa, en ningún grado

1. **Benchmark ejecutado.** No lo está.
2. **Rendimiento validado.** No existe ni una cifra de `ADR002-C`.
3. **Candidato ganador.** No hay comparación alguna.
4. **Arquitectura final o productiva aprobada.** No lo es. Esta acta **no
   aprueba** un grafo de relaciones para producción.
5. **Ejecución aislada autorizada.**
6. **Fusión del PR #117 autorizada.** Permanece abierto y sin fusionar.

---

## 6. Evidencia de verificación en el commit auditado

| Comprobación | Resultado |
|---|---|
| `verify_cards --check` | **15 fichas conformes**, una `CONGELADA` por candidato, **14/14 controles bloqueantes**, ninguna puerta de arranque pendiente |
| Unicidad de ficha `CONGELADA` para `ADR002-C` | **una sola**: la v2; la v1 consta `SUSTITUIDA` |
| Recomputación de las quince huellas | coinciden con las declaradas |
| Suite propia de `C` | **25 pruebas** en `test_adr002_c_funcional.py` |
| Discriminante relacional | **12 pruebas** en `test_adr002_discriminante_relacional.py` |
| Suite experimental completa | **1 644 pruebas en verde** |
| Ruff format, Ruff lint, mypy | conformes |
| **Quality** sobre `94664da` | **success** (run 311, intento 2) |

### 6.1 La prueba de interfaz de `main`, adjudicada y no declarada inestable

El intento 1 del run 311 falló en
`tests/gui/test_conversation_ui.py::test_streaming_message_grows_without_overlapping_neighbours`,
con `assert 24 >= 54` sobre la altura de un `QRect`. Es la misma prueba que ya
falló en el intento 1 del run 305 y pasó en su intento 2. El usuario ordenó
reejecutarla y, si volvía a fallar, corregir su causa reproducible. Lo
comprobado es esto:

| Comprobación | Resultado |
|---|---|
| Quality, run 311, intento 2, mismo commit | **success** |
| `tests/gui/test_conversation_ui.py` aislado sobre `main` | **60 passed** |
| Suite completa de `main`, igual que hace Quality | **1 469 passed** |

**Hay una causa localizada, y aun así no se corrige aquí.** En
`MessageItemWidget.set_message` (`src/sirius/presentation/message_view.py`), el
cuerpo nuevo emite `height_changed` **antes** de que `addWidget` lo incorpore al
layout, de modo que un `_sync_size` anidado publica un `sizeHint` calculado con
el contenedor todavía vacío; el guardia `_syncing_size` suprime después el
recálculo que lo repararía dentro de la misma pila, y la fila queda a la altura
colapsada hasta el siguiente reflujo. **Es de `main`, no de esta rama.**

Corregirlo cambiaría el árbol de `src/sirius`, que es exactamente la identidad
congelada de `T0-control v1` (`6d8558ef1fe4994cb15a12967525bf3496b3c0b8`), y
obligaría a rederivar la línea base entera. Con Quality en verde **no hay
decisión aprobada que lo exija inequívocamente**, que es la condición que
ARQ-00 impone para tocar Sirius 0.1 productivo. Queda **declarado aquí, con su
causa, para que quien decida sobre `main` lo tenga localizado**, y fuera del
alcance de ADR-002.

---

## 7. Limitaciones conocidas aceptadas como NO bloqueantes

1. El grafo relacional se **valida entero al abrir** la fuente; un corpus
   relacional muy grande pagaría esa validación en la primera apertura de `E3`.
2. Las cotas —16 semillas, 64 aristas, 1 salto— son **declaradas y comprobadas
   en la ficha**, no negociadas por el motor: un caso que las agote entrega
   menos alcance y lo declara, no falla.
3. `CLASES_MATERIALIZABLES` se restringe a `MEMORIA` y `DECISION`: una arista
   hacia otra clase **no expande**, y eso se declara en la traza.
4. Las limitaciones abiertas de la capa común y de `A`, que `C` hereda por
   composición, siguen siendo las de sus propias actas.

Estas limitaciones **no se declaran resueltas**, **no se aprueban como
decisiones productivas**, **deben permanecer visibles durante la ronda
primaria** y **pueden convertir al candidato en fallo o en NO EVALUABLE** si
afectan a la ejecución.

---

## 8. Estado de gobierno tras esta acta

| Elemento | Estado |
|---|---|
| `T0-control v1` | **CONGELADA**, intacta |
| `ADR002-A v5` | **PREPARADO PARA BENCHMARK** |
| `ADR002-B v7` | **PREPARADO PARA BENCHMARK** |
| **`ADR002-C v2`** | **PREPARADO PARA BENCHMARK** — por esta acta |
| `ADR002-C v1` | **SUSTITUIDA**, conservada como historial |
| `ADR002-D` | **NO IMPLEMENTADO** — paso 9, siguiente |
| Ronda primaria | `T0 + A + B + C + D`, **sin reducción** |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |
| Ganador | **NO ELEGIDO** |
| Sirius 0.1 | **NO MODIFICADO** |
| PR #117 | **ABIERTO y SIN FUSIONAR**; `main` no se toca |

---

## 9. Lo que esta acta no autoriza

- **No** autoriza ejecutar el benchmark, usar el corpus oficial ni medir
  rendimiento de ningún candidato.
- **No** autoriza ejecutar `ADR002-C` aisladamente.
- **No** elige ganador ni declara arquitectura final o productiva.
- **No** aprueba `ADR002-D`, todavía no implementado.
- **No** modifica Sirius 0.1, `T0-control`, la capa común, `ADR002-A` ni
  `ADR002-B`.
- **No** fusiona el PR #117.

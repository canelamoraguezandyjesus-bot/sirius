# SIRIUS 0.2 — ADR-002 · Ficha de candidato · plantilla

**Versión:** 0.4
**Estado:** **PROPUESTO** · plantilla, **no está aprobada por acta de puerta propia**; su autoridad la da el acto sucesor 01 de TOL-210, que la aprueba como lectura humana del contrato sucedido
**Fecha:** 31 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md`, que se conserva **sin modificar** (igual que la v0.1 y la v0.2). Su blob `c2beba3e829163ea5fd052c9f1831a13b205873a` lo cita el §2.1 del acta de `ADR002-TOL-210` y pasa a la lista de intangibles: alterarla haría incomprobable esa acta
**Cambio de esta versión:** materializa la **opción (a)** aprobada por el acto sucesor: `T0-control` queda **exento** de los campos exclusivos de candidato que no le son aplicables, declarando **explícitamente y con fundamento** cada inaplicabilidad (§2 bis). **Para los candidatos `ADR002-A/B/C/D` nada cambia de fondo**: rige íntegro el contenido mínimo de la v0.3, con dos citas actualizadas —esta plantilla y el acto sucesor entre las actas—
**Acto que la aprueba:** `SIRIUS_0.2_ADR_002_TOL_210_ACTO_SUCESOR_01_EXENCION_T0_v1.0.md`
**Contrato ejecutable:** `experiments/adr002/cards/schema_card_v0_2.py`, que **envuelve** a `schema_card_v0_1.py` sin reescribirlo
**Exigida por:** `ADR002-TOL-210` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md`
**No autoriza:** ejecutar el benchmark, ejecutar T0, implementar prototipos, elegir alternativa ni merge.

---

## 0. Por qué existe esta versión

La v0.3 hizo la ficha auditable por máquina, y al construir la primera ficha
real el paquete 10 encontró el límite del contrato: exigía al **control** lo
mismo que a un **candidato**, y el control no podía darlo. `T0-control` no
implementa E0–E5, no tiene límites por etapa ni extremo a extremo congelados
—el Registro declara que T0 «no es un presupuesto heredable»—, y declarar su
consumo habría sido **medirlo** sin autorización. Rellenar esos campos exigía
medir —prohibido— o inventar —prohibido por la regla 1 del §9 del Registro—.

El §8.1 del paquete 10 elevó la decisión y el usuario aprobó la **opción (a)**:
eximir al control de lo inaplicable, exigiéndole declarar **por qué** no
aplica. Esta versión es la lectura humana de ese contrato sucedido.

### 0.1 Qué cambia y qué no

| Punto | v0.3 | **v0.4** |
|---|---|---|
| Contrato ejecutable | `schema_card_v0_1` | **`schema_card_v0_2`**, que delega en la v0.1 para candidatos y añade la rama del control |
| Ficha de candidato (`ADR002-A/B/C/D`) | contenido mínimo íntegro | **sin cambio de fondo**: misma exigencia, delegada byte a byte en la v0.1 |
| Ficha de `T0-control` | mismo contenido que un candidato — insatisfacible | **secciones propias del control** + **exenciones fundamentadas** (§2 bis) |
| Actas citadas | TOL-207 y TOL-209 | TOL-207, TOL-209, **TOL-210 y el acto sucesor 01** |
| Exención para candidatos | no existía | **sigue sin existir**: declararla invalida la ficha |
| Custodia (huella, anterioridad, congelación) | §1.1 y regla 2 | **sin cambio** |
| Universo de fichas | `ADR002-A/B/C/D` + `T0-control` | **sin cambio** |

---

## 1. Reglas de uso

Rigen las **nueve reglas** del §1 de la v0.3 sin cambio, y se añade una:

10. **La exención es exclusiva de `T0-control` y cerrada.** Solo la ficha del
    control puede declarar la sección `exenciones_de_control`; sus áreas son
    exactamente las **seis** del §2 bis; cada una exige fundamento no vacío; y
    una ficha de candidato que la declare es **inválida**. Exento no significa
    mudo: significa que la imposibilidad se congela **por escrito**, que es la
    regla 3 de siempre aplicada al control.

La huella (§1.1 de la v0.3) y la anterioridad observada en el grafo de Git
(regla 2) rigen **idénticas** para la ficha del control.

---

## 2. Contenido mínimo de los candidatos `ADR002-A/B/C/D`

**El de la v0.3, íntegro y sin relajación**: §2.1 a §2.19. El contrato v0.2 lo
comprueba **delegando** en `schema_card_v0_1` congelado, tras normalizar
exactamente tres citas —versión de esquema, plantilla vigente y lista de
actas—. Todo lo demás —conjuntos cerrados, coherencias, señal tardía,
restricción de `D`, sustrato, índices, ciclo, coste por etapa, extremo a
extremo, almacenamiento, estabilidad, banda temporal, purga— lo comprueba la
v0.1 **sin cambios**.

Una ficha v0.2 de candidato declara:

| Campo | Valor |
|---|---|
| `version_esquema` | `ficha-candidato-0.2` |
| `plantilla` | esta v0.4 |
| `actas_de_puerta` | TOL-207 · TOL-209 · TOL-210 · acto sucesor 01, exactamente |
| `exenciones_de_control` | **prohibida** — declararla invalida la ficha |

## 2 bis. Contenido mínimo de `T0-control`

La forma normativa es el JSON descrito por la rama de control de
`experiments/adr002/cards/schema_card_v0_2.py`. Secciones obligatorias, todas
con conjuntos de campos **cerrados**:

### 2 bis.1 Identidad y congelación · `identidad` · `congelacion`

Idénticas a las de un candidato (§2.1 y §2.2 de la v0.3): candidato
`T0-control`, papel `CONTROL_DE_FALSACION` —que solo T0 puede ostentar—,
versión que crece de una en una, commit de referencia del **acto de
gobierno** —para la v1, el commit que introduce el acto sucesor 01—, huella
canónica y ruta `artifacts/adr002_cards/ficha_T0-control_v<N>.json`.

### 2 bis.2 Arquitectura de control · `arquitectura_de_control`

| Campo | Valor |
|---|---|
| **Sustrato léxico** | el FTS5 **medido** de Sirius 0.1, tal cual está |
| **Materialización de relaciones** | la de Sirius 0.1, sin índice adicional |
| **Puerto de acceso** | `KnowledgeSearchRepository`, el puerto real medido |
| **Incumplimientos conocidos** | mapa **cerrado** `RF-06 · RF-14 · RF-19` → declaración, uno a uno |

T0 declara sus incumplimientos por escrito en vez de esconderlos: incumple
`RF-06`, `RF-14` y `RF-19` (medido e inventariado por la Resolución de la
partición §3). Es la razón de que sea control y no candidato.

### 2 bis.3 Corpus · `corpus`

Los mismos campos del §2.7 de la v0.3, con dos valores **no elegibles** que el
contrato impone: `commit` = `d27352b9f03dfc6a4d939b855474ce0ad1c2fc86` —el
commit auditado del acta de congelación v0.4— y `head_de_esquema` =
`61be4bb269bf` —el head de Alembic de T0—.

### 2 bis.4 Protocolo aplicado · `protocolo_aplicado`

El del §2.8 de la v0.3, sin cambio: protocolo v0.2 aprobado, desviaciones,
entorno, semilla, **≥ 30** repeticiones por magnitud.

### 2 bis.5 Escenario de control · `escenario_de_control`

El plan del paquete 10, **citado literalmente, no elegido**:

| Campo | Valor |
|---|---|
| **Fuente del plan** | `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_10_TOL208_REDERIVACION_T0_v0.1.md` |
| **Escenarios** | `cero_resultados` · `un_resultado_exacto` · `muchos_candidatos`, en ese orden |
| **Capas** | `solo_indice_fts5` · `recuperacion_completa_rank`, en ese orden |
| **Magnitudes** | `6`, recomputado como escenarios × capas |

### 2 bis.6 Estabilidad · `estabilidad`

La del §2.15 de la v0.3, **idéntica**: once sesiones exactas, `SM = 17405`,
`U50 = 2685`, dos reglas por percentil, sin umbral relativo para P95, citadas
del perfil aprobado por el acta de TOL-209.

### 2 bis.7 Presupuesto aplicable · `presupuesto_aplicable`

| Campo | Valor |
|---|---|
| **Presupuesto absoluto (B)** | `1610612736` — citado del acta de TOL-207, no elegido |
| **Nota** | qué papel juega para un control que no compite por la puerta 7 |

### 2 bis.8 Exenciones de control · `exenciones_de_control`

**El corazón de la opción (a).** Conjunto **cerrado** de seis áreas, cada una
con fundamento no vacío, más `limitada_a: T0-control`:

| Área | Inaplicabilidad que congela |
|---|---|
| `alternativa_minima_y_senal_tardia` | T0 no representa alternativa de ARQ-00 §23 ni declara señal tardía |
| `etapas_e0_e5` | T0 no implementa E0–E5 (Resolución de la partición §3) |
| `limites_locales_por_etapa` | sin etapas, ninguna decisión los congela para T0 |
| `limites_extremo_a_extremo` | T0 «no es un presupuesto heredable» (Registro); no existe P95/P99 propio |
| `consumo_de_almacenamiento_previo` | declararlo sería **medir T0**, que exige el acta de autorización |
| `limites_del_ciclo_de_indice` | T0 no añade índice adicional alguno |

### 2 bis.9 Huella y declaración · `huella_candidato` · `declaracion_de_congelacion`

Idénticas a §2.18 y §2.19 de la v0.3: commit del prototipo de T0, árbol de
fuentes, migraciones, artefactos, reproducción; y la declaración de que los
valores se fijaron **antes** de la primera ejecución, con
`valores_anteriores_a_la_primera_ejecucion: true` y `no_contiene_resultados:
true`.

---

## 3. Verificación antes de ejecutar

La del §3 de la v0.3, sin cambio de recorrido, con dos comprobaciones más:

8. la ficha se valida con el esquema que su `version_esquema` declara —v0.1 o
   v0.2—, y una versión desconocida falla cerrado;
9. la plantilla **v0.3** sigue intacta, junto a la v0.1 y la v0.2, contra los
   blobs citados por sus actas.

---

## 4. Lo que esta plantilla no hace

Todo lo del §4 de la v0.3, y además:

- **No exime a ningún candidato de nada.** La exención es exclusiva del
  control, y el contrato invalida la ficha de candidato que la invoque.
- **No autoriza ejecutar T0.** La autorización es el acta
  `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md`, independiente del
  acto sucesor que aprueba esta plantilla.
- No emite la ficha de `T0-control`: la ficha es un artefacto JSON aparte,
  congelado bajo las reglas de custodia intactas.

---

**Siguiente movimiento único:** emitir la ficha de `T0-control` v1 conforme a
esta plantilla y al contrato v0.2, congelarla, y solo entonces —con el acta de
autorización independiente presente— ejecutar los pasos 2 y 3 de
`ADR002-TOL-208`.

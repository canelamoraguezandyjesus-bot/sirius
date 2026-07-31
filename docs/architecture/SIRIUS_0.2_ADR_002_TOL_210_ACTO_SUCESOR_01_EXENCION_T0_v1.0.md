# SIRIUS 0.2 — ADR-002 · Acto sucesor 01 de TOL-210 · exención del control `T0-control`

**Versión:** 1.0
**Estado:** **APROBADO** — acto sucesor del acta de `ADR002-TOL-210`, conforme a su regla de custodia §8.5
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Acta a la que sucede:** `SIRIUS_0.2_ADR_002_TOL_210_APROBACION_v1.0.md`
**Commit de partida verificado:** `db6cc9ee47e4f1df18dc9d696fd7128ea63b031f`
**Decisión que resuelve:** la abierta por el §8.1 del `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_10_TOL208_REDERIVACION_T0_v0.1.md`
**Autorización explícita del usuario:** «Apruebo y autorizo» — se aprueba la **opción (a)**
**No autoriza:** por sí mismo, ejecutar T0 —esa autorización es un acta distinta e independiente—, implementar o ejecutar candidatos, iniciar el benchmark, sustituir la línea base histórica ni fusionar el PR #117.

---

## 0. Objeto

El paquete 10 dejó registrado un bloqueo sustantivo: `ADR002-TOL-210` exige que
toda ejecución referencie una **ficha congelada previa**, y la ficha de
`T0-control` **no podía derivarse** de las decisiones existentes. El contrato
aprobado exigía al **control** lo mismo que a un **candidato**, y el control no
podía darlo sin **medir** —prohibido sin autorización— o sin **inventar** —lo
que la regla 1 del §9 del Registro prohíbe expresamente—.

El §8.1 del paquete 10 planteó las dos únicas salidas y declaró que la decisión
no era del ejecutor. **El usuario la ha resuelto: se aprueba la opción (a).**

> **(a)** el contrato **exime al control** de los campos que solo tienen
> sentido para un candidato, exigiéndole en su lugar declarar **por qué** no
> aplican — coherente con la regla 3 del propio contrato: «si un valor no puede
> declararse, se declara por qué».

Este acto **materializa** esa decisión. Es un acto sucesor en el sentido exacto
del §8.5 del acta de TOL-210: modifica el contrato aprobado, y por eso se
registra como acto, con identidad propia, sin reescribir nada de lo aprobado.

## 1. Decisión aprobada

### 1.1 La exención, y su límite

`T0-control` queda **exento** de los campos del contenido mínimo que son
exclusivos de candidato y que ninguna decisión congeló para él. La exención
tiene tres propiedades que el contrato ejecutable hace cumplir:

1. **Exenta, no muda.** Cada área eximida exige una declaración **no vacía y
   con fundamento** de por qué no aplica. Un área eximida sin fundamento
   invalida la ficha.
2. **Cerrada.** Las áreas eximibles son exactamente **seis** —las del §1.2—,
   ni una más. Un área no listada no es eximible.
3. **Exclusiva de `T0-control`.** Una ficha de `ADR002-A`, `ADR002-B`,
   `ADR002-C` o `ADR002-D` que declare la sección de exenciones es
   **inválida**: para los candidatos rige **íntegro** el contenido mínimo de la
   v0.1, sin relajación alguna.

### 1.2 Las seis áreas eximidas, con su fundamento

| Área eximida | Por qué no aplica a `T0-control` |
|---|---|
| `alternativa_minima_y_senal_tardia` | T0 **no representa ninguna alternativa mínima** de ARQ-00 §23 ni declara señal tardía: es la línea base medida de Sirius 0.1, y la Resolución de la partición §3 lo declara control de falsación, no candidato |
| `etapas_e0_e5` | la Resolución de la partición §3 declara que T0 **no implementa E0–E5**: no hay etapas cuyas transiciones declarar |
| `limites_locales_por_etapa` | sin etapas E0–E5 **no existe** ninguna decisión que congele límites locales por etapa para T0, y fijarlos ahora sería inventarlos |
| `limites_extremo_a_extremo` | el Registro declara que T0 «**no es un presupuesto heredable**» y que ningún candidato «se descarta por superar el tiempo de T0»: un objetivo P95 y un límite duro P99 propios de T0 no existen ni deben existir |
| `consumo_de_almacenamiento_previo` | declarar el consumo de T0 **sería una medición de T0**, que exige la autorización expresa e independiente del acta de autorización, no de este acto |
| `limites_del_ciclo_de_indice` | T0 no añade **ningún índice adicional** al FTS5 medido: no existe decisión que congele límites de ciclo de índice para T0 |

### 1.3 Lo que sigue vinculando a `T0-control`, sin excepción

La exención no toca nada de esto. La ficha del control declara y el contrato
comprueba:

- su **identidad** —`T0-control`, versión, sustituciones— y su **papel** de
  `CONTROL_DE_FALSACION`, que solo T0 puede ostentar;
- el **corpus congelado v0.4**, citado por el commit auditado
  `d27352b9f03dfc6a4d939b855474ce0ad1c2fc86` de su acta —no es elegible—;
- el **head de esquema** de T0: `61be4bb269bf`;
- el **protocolo aprobado** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md`,
  con desviaciones, entorno y semilla declarados y **≥ 30** repeticiones;
- las **once sesiones exactas** y el perfil de estabilidad aprobado por el
  acta de TOL-209 —`SM = 17 405 ns`, `U50 = 2 685 ns`, dos reglas por
  percentil, sin umbral relativo para P95—, **citados, no propuestos**;
- el **presupuesto aplicable** aprobado por el acta de TOL-207
  —`1 610 612 736 B`—, citado como referencia del entorno de medición;
- el **puerto de acceso** y el sustrato declarados en su arquitectura de
  control;
- el **escenario de control**: exactamente el plan preinscrito del paquete 10
  —tres escenarios, dos capas, seis magnitudes—, citado literalmente;
- la **custodia completa**: huella canónica excluido el propio campo (§1.4 del
  acta de TOL-210), commit de referencia de un acto de gobierno existente,
  anterioridad **observada** en el grafo de Git como ancestro estricto (§1.3
  del acta de TOL-210), estado `CONGELADA` único por candidato;
- la **declaración de incumplimientos conocidos**: T0 incumple `RF-06`,
  `RF-14` y `RF-19` (medido e inventariado por la Resolución de la partición
  §3), y su ficha lo dice por escrito, uno a uno, en vez de esconderlo;
- la **declaración de congelación**: valores fijados antes de la primera
  ejecución, sin proceder de ningún resultado observado;
- la **ausencia de resultados**: la ficha declara límites y citas, jamás
  mediciones, con todos los conjuntos de campos **cerrados**.

### 1.4 Por qué la opción (a) y no la (b)

La opción (b) —congelar la ficha **después** de la rederivación, con los
valores que esta produzca— invertía el orden que `ADR002-TOL-210` exige: la
ficha existe para congelar límites **antes** de observar resultados, y una
ficha rellenada con los resultados de la ejecución que debe gobernar no
congela nada. La opción (a) preserva el orden: todo lo declarable se declara
antes, y lo no declarable declara **por qué** no lo es — que es exactamente la
regla 3 que el contrato ya tenía.

## 2. Materialización: versión, no reescritura

Tres reglas de custodia gobiernan la materialización:

1. **La v0.1 del esquema no se toca.** `schema_card_v0_1.py` queda byte a byte
   como lo fijó el §2.2 del acta de TOL-210. El esquema v0.2 la **envuelve**
   para los candidatos —delegando en ella íntegramente— y añade la rama del
   control; no la reescribe.
2. **La plantilla v0.3 no se toca.** Su blob
   `c2beba3e829163ea5fd052c9f1831a13b205873a` lo cita el §2.1 del acta de
   TOL-210 y pasa a la lista de **intangibles**, junto a la v0.1 y la v0.2. La
   v0.4 la sustituye como norma vigente **sin reescribirla**.
3. **El acta de TOL-210 no se toca.** Este acto la **sucede**; no la corrige.
   `ADR002-TOL-210` continúa **SATISFECHA**, ahora con el contrato en su forma
   sucedida.

### 2.1 Artefactos que este acto aprueba

| Artefacto | Papel |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.4_PROPUESTO.md` | plantilla vigente: lectura humana del contrato sucedido |
| `experiments/adr002/cards/schema_card_v0_2.py` | contrato ejecutable v0.2: rama del control + delegación íntegra en la v0.1 para candidatos |
| `experiments/adr002/cards/verify_cards.py` | verificador: despacha por `version_esquema` y añade la v0.3 a las plantillas intangibles |
| `experiments/adr002/cards/test_adr002_cards_v0_2.py` | pruebas fail-closed de la exención, su exclusividad y la integridad de lo intangible |

Toda ficha v0.2 —de control o de candidato— cita **las tres actas de puerta y
este acto sucesor**: `TOL-207`, `TOL-209`, `TOL-210` y
`SIRIUS_0.2_ADR_002_TOL_210_ACTO_SUCESOR_01_EXENCION_T0_v1.0.md`.

### 2.2 Qué pasa con las fichas v0.1

Ninguna ficha v0.1 existe congelada a la fecha de este acto —el verificador lo
reporta: «sin fichas que controlar»—, de modo que este acto **no obliga a
repetir ninguna ejecución** ni a sustituir ninguna ficha. El esquema v0.1
permanece válido como norma congelada citada por el acta de TOL-210; las
fichas nuevas se emiten bajo la v0.2.

## 3. Lo que este acto no autoriza

- **No autoriza ejecutar T0.** La autorización de ejecución es el acta
  `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md`, distinta e
  independiente de este acto, y el recorrido de la rederivación la comprueba
  por separado.
- No emite por sí mismo la ficha de `T0-control`: la ficha se emite como
  artefacto JSON aparte, validado por el contrato sucedido, y su congelación
  se comprueba con las reglas de custodia intactas.
- No exime a **ningún candidato** de nada: `ADR002-A/B/C/D` conservan íntegro
  su contenido mínimo.
- No declara satisfecha `ADR002-TOL-208` ni adelanta sus pasos 2 y 3.
- No inicia el benchmark, no implementa candidatos, no sustituye la línea
  base histórica, no modifica Sirius 0.1 (`src/`, `tests/`, `migrations/` ni
  configuración productiva) y **no fusiona el PR #117**.

## 4. Reglas de custodia de este acto

1. Este acto se registra **antes** de emitir la ficha de `T0-control`: la
   ficha lo cita como acta y su `commit_de_referencia` es el commit que
   introduce este acto.
2. Las seis áreas del §1.2 son un conjunto **cerrado**. Ampliarlo exigiría un
   nuevo acto sucesor, con revisión explícita.
3. La exención es **intransferible**: el contrato la rechaza en cualquier
   ficha cuyo candidato no sea `T0-control`, y una prueba lo comprueba.
4. Las plantillas v0.1, v0.2 **y v0.3** son intangibles. El verificador
   comprueba sus blobs y falla cerrado ante cualquier alteración.
5. Cualquier modificación posterior del contrato sucedido exige un nuevo acto
   sucesor, conforme al §8.5 del acta de TOL-210, que sigue rigiendo.

---

**Decisión final:** se aprueba la **opción (a)**. `T0-control` queda exento de
los campos exclusivos de candidato que no le son aplicables, con la obligación
de declarar **explícitamente y con fundamento** cada inaplicabilidad, mediante
el contrato ejecutable v0.2 y la plantilla v0.4 que este acto aprueba. La
ejecución de T0 sigue requiriendo su acta de autorización **independiente**.
`ADR002-TOL-208` continúa **NO SATISFECHA** en sus pasos 2 y 3. El benchmark y
el PR #117 continúan donde estaban: bloqueado el primero, abierto y sin
fusionar el segundo.

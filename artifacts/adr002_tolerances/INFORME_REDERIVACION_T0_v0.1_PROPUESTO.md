# SIRIUS 0.2 — ADR-002 · Informe de ejecución y rederivación de T0 · pasos 2 y 3 de TOL-208

**Versión:** 0.1
**Estado:** **EVIDENCIA · EJECUTADA** — este informe publica resultados; **no aprueba `ADR002-TOL-208`**, cuya satisfacción es un acto del usuario
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de ejecución (`HEAD` al medir):** `425964872c73ec4e4f44d80189907d7ca08bedff`
**Autorización:** `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md` — «Apruebo y autorizo»
**Ficha que ampara la ejecución:** `T0-control` v1 · huella `d47a767e61b30729e15f48c9924413f6fddc9429` · commit de entrada `95d00a1c3c4fc0a9ed74374d1786bec9bd0b3483` — **ancestro estricto** del commit de ejecución, observado por el verificador
**Artefacto normativo:** `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json`, validado con `schema_rederivation_v0_1` **antes** de escribirse y revalidado tras releerse
**Muestras crudas:** `artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json` — los 6.600 valores cronometrados (6 magnitudes × 11 sesiones × 100 repeticiones), recomputables
**Protocolo:** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` · perfil aprobado por el acta de `ADR002-TOL-209`

---

## 1. Qué se ejecutó, exactamente

El plan preinscrito del paquete 10, sin desviación alguna:

| Concepto | Ejecutado |
|---|---|
| Candidato | `T0-control` · head de Alembic `61be4bb269bf` · papel `CONTROL_DE_FALSACION` |
| Corpus | v0.4 congelado: `performance_corpus_v0_2.json`, blob `4e9e2746e49b158a43eda7826b47c78c41b36e90`, verificado byte a byte antes de cargar |
| Escenarios | `cero_resultados` · `un_resultado_exacto` · `muchos_candidatos` |
| Capas | `solo_indice_fts5` (consulta `MATCH` real) · `recuperacion_completa_rank` (caso de uso `RankRelevantKnowledgeUseCase.rank`, con el barrido que RF-14 prohíbe) |
| Magnitudes | **6** — escenario × capa |
| Sesiones | **exactamente 11**, cada una un **proceso independiente del sistema operativo** con fichero, motor, caché y warm-up propios · pids `3065 · 3067 · 3068 · 3070 · 3074 · 3075 · 3077 · 3080 · 3082 · 3084 · 3086` |
| Repeticiones | **100 por magnitud y sesión** (n = 100 de cada percentil por sesión), warm-up 5 descartado íntegro |
| Percentiles | nearest-rank, nunca interpolados |
| Cronómetro | `floor_scale_probes.medir_ns`, el congelado de los paquetes 06 y 07, sin tocar |
| Repetición única §6.8 | **NO ejercitada**: la corrida fue funcionalmente válida a la primera |

Antes de abrir una sola ventana cronometrada se comprobó, fallando cerrado:
autorización presente, actas de TOL-207/209/210 presentes, corpus congelado
intacto por blob, línea base histórica intacta (`f9f051332d9833fb7e10b27f4820849f00b6fe6c`),
ficha de T0 congelada con entrada **anterior estricta**, perfil aprobado y su
fuente intactos (`4100349…`, `7273264…`), árbol limpio y salidas inexistentes.
La batería completa de pruebas se ejecutó antes de medir: **1 151** en
`experiments/` y **1 195** en `tests/`, todas verdes, con Ruff conforme.

## 2. Las consultas de control: derivadas, no elegidas

La regla cerrada de `frozen_corpus.derivar_consultas` —preinscrita en el
commit de la autorización, antes de observar nada— produjo:

| Escenario | Consulta | Resultados esperados (derivados del corpus) | Observados en FTS5, en las 11 sesiones |
|---|---|---:|---:|
| `cero_resultados` | `zetaausentenoindexado` | 0 | 0 |
| `un_resultado_exacto` | `duna` | 1 | 1 |
| `muchos_candidatos` | `la` | 211 | 211 |

La verificación funcional fue **idéntica en las once sesiones**. La carga del
corpus materializó fielmente los conteos declarados: 2 proyectos, 5 000
mensajes, 500 recuerdos —248 vigentes por el reparto `validez ×
disponibilidad` del propio corpus—, 50 decisiones, **550 filas** en
`knowledge_fts`. Entidades (24), documentos (120) y relaciones (180) del
corpus **no se cargan porque el esquema de T0 no tiene tablas para ellos**:
T0 no materializa relaciones, y esa carencia es parte de lo que el control es.

## 3. Resultados: por primera vez, comparables

**Ninguna magnitud queda `NO_COMPARABLE`.** Con once sesiones exactas, las
seis magnitudes reciben veredicto del perfil aprobado por primera vez, que es
lo que el paso 3 de `ADR002-TOL-208` ordenaba conseguir.

Veredictos del perfil aprobado (`SM = 17 405 ns`, `U50 = 2 685 ns`, régimen
P50 relativo ≤ 20 % sobre `U50`, régimen P95 absoluto contra `B95(M)`):

| Magnitud | P50 entre sesiones (ns) | disp. P50 | régimen P50 | P95 entre sesiones (ns) | disp. P95 | banda B95 (ns) | régimen P95 | **Veredicto** |
|---|---|---:|---|---|---:|---:|---|---|
| `cero_resultados.solo_indice_fts5` | 148 586 – 184 501 | 35 915 | relativo **24,1 % > 20 %** → INVALIDA | 210 298 – 332 808 | 122 510 | 332 895 | absoluto ≤ banda → VALIDA | **INVALIDA** |
| `cero_resultados.recuperacion_completa_rank` | 62 234 032 – 69 483 598 | 7 249 566 | relativo 11,6 % → VALIDA | 68 830 892 – 104 011 659 | 35 180 767 | 25 197 279 | absoluto **> banda** → INVALIDA | **INVALIDA** |
| `un_resultado_exacto.solo_indice_fts5` | 164 912 – 237 070 | 72 158 | relativo **43,7 % > 20 %** → INVALIDA | 242 739 – 422 490 | 179 751 | 332 895 | absoluto ≤ banda → VALIDA | **INVALIDA** |
| `un_resultado_exacto.recuperacion_completa_rank` | 62 745 492 – 72 751 674 | 10 006 182 | relativo 15,9 % → VALIDA | 70 526 005 – 106 030 205 | 35 504 200 | 25 197 279 | absoluto **> banda** → INVALIDA | **INVALIDA** |
| `muchos_candidatos.solo_indice_fts5` | 713 275 – 800 124 | 86 849 | relativo 12,1 % → VALIDA | 792 756 – 1 202 089 | 409 333 | 971 628 | absoluto ≤ banda → VALIDA | **VALIDA** |
| `muchos_candidatos.recuperacion_completa_rank` | 61 783 207 – 70 980 973 | 9 197 766 | relativo 14,8 % → VALIDA | 70 255 499 – 111 878 078 | 41 622 579 | 25 197 279 | absoluto **> banda** → INVALIDA | **INVALIDA** |

Cada P50 y P95 por sesión procede de **n = 100** repeticiones; los once
valores por percentil y magnitud están íntegros en el artefacto, y los 6 600
crudos en el fichero de muestras. Los mínimos, máximos, dispersiones y
veredictos de esta tabla se **recomputaron independientemente** desde los
crudos tras la ejecución: cero discrepancias con el artefacto.

### 3.1 Lectura de los veredictos

**Resultado agregado: 1 `VALIDA` · 5 `INVALIDA` · 0 `NO_COMPARABLE`.**

1. **Las dos magnitudes ligeras del índice fallan el P50 relativo.** A
   ~150–240 µs, una deriva entre sesiones de 24 % y 44 % supera el objetivo
   del 20 %. La magnitud grande del índice (~750 µs, `muchos_candidatos`)
   pasa con 12,1 %: la deriva relativa cae al crecer la magnitud.
2. **Las tres magnitudes de `rank()` fallan el P95 absoluto por la cola.**
   Sus P50 son estables (11,6–15,9 %), pero las colas entre sesiones abren
   35–42 ms frente a una banda `B95` de 25,2 ms. La carga del contenedor
   creció de 0,54 a 1,01 durante la corrida —registrada sesión a sesión, no
   controlada, exactamente como declara la ficha (`LAB-LINUX`, «carga no
   controlada y declarada»)—.
3. **Ninguna magnitud queda bajo `SM`** (17 405 ns): todas las cifras emiten
   afirmación de latencia; ningún veredicto está dominado por el instrumento.
4. **`INVALIDA` no descarta a T0.** T0 es el **control de falsación**, no un
   candidato: el Registro declara que T0 no es un presupuesto heredable y que
   nadie se descarta por compararse con él. Lo que estos veredictos publican
   es un hecho medido: **en este entorno, la estabilidad entre sesiones de la
   línea base no cabe entera en las bandas aprobadas** — cinco de sus seis
   magnitudes no lo hacen, y la sexta sí.

### 3.2 Qué significa para la línea base histórica

La línea base histórica (cinco sesiones, corpus 5 000/500) **permanece
congelada, intacta y no sustituida** (`linea_base_historica.sustituida =
False`; blob verificado antes y después de medir). Sus cifras siguen siendo
`NO_COMPARABLE` frente a las bandas de once sesiones, como siempre. La
rederivación no la corrige: produce la **medición nueva y comparable** sobre
el corpus definitivo que el paso 3 ordenaba, publicada aparte.

## 4. Controles

**Los once controles bloqueantes preinscritos: verdes**, derivados del estado
observado y no declarados a mano —`autorizacion_expresa_presente`,
`actas_de_puerta_presentes`, `corpus_congelado_intacto`,
`linea_base_historica_intacta`, `ficha_de_t0_congelada_y_anterior`,
`once_sesiones_completas`, `repeticiones_suficientes`,
`percentiles_por_rango_mas_cercano`,
`escenarios_y_capas_identicos_a_la_linea_base`,
`veredictos_delegados_al_perfil_aprobado`,
`sin_sustituir_la_linea_base_historica`—.

Controles funcionales y ambientales de la corrida: once pids distintos,
conteos de escenario idénticos en las once sesiones, `boot_id` estable
(`fd0d2268…`) —la máquina no se reinició—, carga registrada por sesión
(0,54 → 1,01), warm-up y repeticiones exactos en todas. **La repetición única
del §6.8 no se ejercitó** porque ningún control funcional invalidó la
corrida; el §8.8 del protocolo prohíbe expresamente repetir para «conseguir»
un veredicto distinto, y este informe publica los veredictos tal como
salieron.

## 5. Custodia

1. **Nada se cambió después de observar los resultados**: ni esquema, ni
   protocolo, ni magnitudes, ni repeticiones, ni tolerancias, ni criterio de
   veredicto, ni ficha, ni corpus. El arnés completo quedó congelado en el
   commit de la autorización, **anterior** a la ejecución.
2. El artefacto validó contra `schema_rederivation_v0_1` —congelado en el
   paquete 10, dos commits antes de existir medición alguna— antes de
   escribirse, y revalidó tras releerse del disco.
3. La escritura fue atómica y **sin sobrescribir**: las rutas de salida se
   exigieron inexistentes como precondición.
4. Toda la evidencia anterior permanece byte a byte: corpus v0.4, línea base
   histórica, suelo v0.3, perfil v0.1, actas, plantillas v0.1–v0.3.
5. El veredicto de cada magnitud es **recomputable por terceros**: perfil
   reconstruido desde los vectores crudos del suelo v0.3 (no aceptado del
   JSON aprobado, contrastado con él: `SM = 17 405`, `U50 = 2 685`,
   `B50(U50) = 537`), percentiles nearest-rank desde los 100 crudos de cada
   sesión, rangos y veredictos desde los once valores por percentil.

## 6. Lo que este informe no hace

- **No aprueba `ADR002-TOL-208`.** Los pasos 2 y 3 están **ejecutados**; la
  satisfacción de la puerta exige el acta de aprobación de resultados del
  usuario, que no existe.
- No convierte ningún resultado en tolerancia ni fija límite alguno nuevo.
- No descarta ni acredita a T0: publica su estabilidad medida bajo las bandas
  aprobadas.
- No sustituye la línea base histórica.
- No autoriza candidatos, ni el benchmark, ni el merge del PR #117.

## 7. La decisión que queda abierta

Con los pasos 2 y 3 ejecutados, la decisión es del usuario y tiene dos
salidas legítimas, ninguna automática:

- **(a) Aprobar los resultados tal cual** mediante el acta de satisfacción de
  `ADR002-TOL-208`, asumiendo el hecho medido: en este entorno, cinco de las
  seis magnitudes del control no caben en las bandas aprobadas (colas de
  `rank()` y deriva relativa de las magnitudes ligeras del índice).
- **(b) Ordenar la repetición única del §6.8 para la comparación** —una sola,
  en condiciones más controladas de carga, con nueva autorización expresa y
  artefacto v0.2 aparte— si se considera que la comparación resultó inválida
  por variación del entorno. El §6.9 y el §8.8 siguen rigiendo: una segunda
  corrida inválida deja el resultado `NO_EVALUABLE` y no habrá tercera.

---

**Estado de las puertas tras esta ejecución:** `SRC-ADR002-01`, `TOL-207`,
`TOL-209` y `TOL-210` **SATISFECHAS**; `ADR002-TOL-208` **pasos 1, 2 y 3
EJECUTADOS** y puerta **NO SATISFECHA** a la espera del acta de aprobación de
resultados. **El benchmark continúa bloqueado. El PR #117 continúa abierto y
sin fusionar.**

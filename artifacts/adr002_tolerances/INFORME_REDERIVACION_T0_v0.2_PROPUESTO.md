# SIRIUS 0.2 — ADR-002 · Informe de la repetición única controlada (§6.8) · rederivación de T0 v0.2

**Versión:** 0.2
**Estado:** **EVIDENCIA · REPETICIÓN ÚNICA CONSUMIDA** — este informe publica los resultados finales de estabilidad conforme al §6.9; **no aprueba `ADR002-TOL-208`**, cuya satisfacción es un acto del usuario
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de ejecución (`HEAD` al medir):** `5797f5205cdb3054921054461f77dbdb8f550af4`
**Autorización:** `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_REPETICION_68_v1.0.md` — exactamente una repetición; **queda prohibida una tercera corrida**
**Ficha que ampara la ejecución:** `T0-control` v1 · huella `d47a767e61b30729e15f48c9924413f6fddc9429` · commit de entrada `95d00a1c3c4fc0a9ed74374d1786bec9bd0b3483` — **anterior a ambas ejecuciones** (v0.1 y v0.2), observado por el verificador
**Artefacto normativo:** `artifacts/adr002_tolerances/rederivacion_t0_v0.2.json`, validado con el esquema congelado `schema_rederivation_v0_1` **antes** de escribirse y revalidado tras releerse
**Muestras crudas:** `artifacts/adr002_tolerances/rederivacion_t0_v0.2_muestras.json` — los 6.600 crudos + registro completo de condiciones controladas + estado final §6.9 por magnitud
**Evidencia v0.1:** **válida, congelada e intacta byte a byte** (blobs `781132bf…`, `04cd8051…`, `11d41f42…` verificados como precondición y como control final). Esta repetición **no la sustituye ni la corrige**

---

## 1. Qué se repitió, y bajo qué condiciones controladas

**El método fue idéntico al de la v0.1, byte a byte**: mismo corpus congelado
v0.4 (por blob), mismos escenarios y capas, mismas consultas derivadas por la
regla cerrada (`zetaausentenoindexado` / `duna` / `la` → 0 / 1 / 211,
verificados idénticos en las once sesiones), mismo worker congelado de
`execute_rederivation` invocado con la misma orden —el ejecutor de la
repetición no añade ni una línea dentro de la ventana cronometrada—, once
procesos independientes, cien repeticiones por magnitud, warm-up 5,
percentiles nearest-rank, perfil aprobado de TOL-209 y esquema congelado.
**Lo único distinto fue el control ambiental**, congelado en el acta ANTES de
medir:

| Condición congelada | Registro de la corrida |
|---|---|
| Carga 1 min ≤ 0,35 antes de la primera ventana | **cumplida**: 0,34 al abrir (v0.1 arrancó a 0,54); espera previa de 35,0 s |
| Asentamiento antes de cada sesión (plazo 120 s) | **las once esperas alcanzadas**, duraciones 0–60 s; **cero incidencias** |
| Sin tareas concurrentes evitables | ninguna batería ni proceso pesado en la ventana; cargas iniciales por sesión **0,32–0,35** (v0.1: 0,54 → 1,01 creciente) |
| Mismo arranque durante toda la corrida | **`boot_id` estable** (`b2271f4f…`) capturado antes y después |
| Arranque de la v0.1 | **ya no existe** (`fd0d2268…`, contenedor efímero): registrado honestamente; la condición realizable era la estabilidad intra-corrida, y se cumplió |
| Pids de sesión | 11920 · 11931 · 11941 · 12675 · 12688 · 12700 · 12712 · 12723 · 13087 · 13097 · 13107 — once procesos distintos |

La batería completa se ejecutó **antes** de medir (1 171 `experiments/` +
1 195 `tests/`, Ruff y mypy limpios) y las salidas v0.2 se verificaron
inexistentes. **La repetición quedó consumida al abrirse la primera ventana
cronometrada.**

## 2. Resultados de la corrida v0.2

Veredictos recomputados por el perfil aprobado (SM = 17 405 ns, U50 = 2 685
ns; P50 relativo ≤ 20 %; P95 absoluto contra `B95(M)` consultada en el mínimo
P95 entre sesiones):

| Magnitud | P50 (ns, 11 sesiones) | disp. P50 | P95 (ns, 11 sesiones) | disp. P95 | banda B95 | Veredicto v0.2 |
|---|---|---:|---|---:|---:|---|
| `cero_resultados.solo_indice_fts5` | 117 172 – 186 931 | 69 759 (**59,5 %**) | 168 142 – 241 919 | 73 777 | 155 066 | **INVALIDA** (P50) |
| `cero_resultados.recuperacion_completa_rank` | 48 070 317 – 54 242 550 | 6 172 233 (12,8 %) | 53 924 638 – 68 277 773 | 14 353 135 | 25 197 279 | **VALIDA** |
| `un_resultado_exacto.solo_indice_fts5` | 127 571 – 158 021 | 30 450 (**23,8 %**) | 193 865 – 260 309 | 66 444 | 155 066 | **INVALIDA** (P50) |
| `un_resultado_exacto.recuperacion_completa_rank` | 46 521 786 – 52 608 357 | 6 086 571 (13,0 %) | 52 530 588 – 65 885 001 | 13 354 413 | 25 197 279 | **VALIDA** |
| `muchos_candidatos.solo_indice_fts5` | 524 398 – 972 899 | 448 501 (**85,5 %**) | 578 426 – 1 147 894 | 569 468 | 971 628 | **INVALIDA** (P50) |
| `muchos_candidatos.recuperacion_completa_rank` | 47 451 503 – 54 387 254 | 6 935 751 (14,6 %) | 52 070 373 – 62 629 480 | 10 559 107 | 25 197 279 | **VALIDA** |

Cada percentil por sesión procede de **n = 100** repeticiones; los 6 600
crudos están en el fichero de muestras. Percentiles, extremos, dispersiones y
veredictos se **recomputaron independientemente** desde los crudos tras la
corrida: **cero discrepancias**. Ninguna magnitud queda `NO_COMPARABLE` ni
bajo `SM`. Los seis P95 caben en sus bandas: **todo fallo de la v0.2 es P50
relativo del índice ligero**.

## 3. Comparación v0.1 ↔ v0.2 — sin mezclar muestras

Dos corridas del **mismo método**; solo cambian las observaciones y el
control ambiental. Ninguna cifra de una corrida se combina con la otra:

| Magnitud | v0.1 (carga 0,54→1,01) | v0.2 (controlada, 0,32–0,35) | Qué cambió |
|---|---|---|---|
| `cero_resultados.solo_indice_fts5` | INVALIDA — P50 rel. 24,1 % | INVALIDA — P50 rel. 59,5 % | sigue fallando P50; P95 pasa en ambas |
| `cero_resultados.recuperacion_completa_rank` | INVALIDA — P95 disp. 35,2 ms > 25,2 ms | **VALIDA** — P95 disp. 14,4 ms | **la cola se domó**: −59 % de dispersión P95 |
| `un_resultado_exacto.solo_indice_fts5` | INVALIDA — P50 rel. 43,7 % | INVALIDA — P50 rel. 23,8 % | mejora (43,7 → 23,8 %) pero sigue > 20 % |
| `un_resultado_exacto.recuperacion_completa_rank` | INVALIDA — P95 disp. 35,5 ms | **VALIDA** — P95 disp. 13,4 ms | **la cola se domó**: −62 % |
| `muchos_candidatos.solo_indice_fts5` | VALIDA — P50 rel. 12,1 % | INVALIDA — P50 rel. 85,5 % | **se invirtió**: una sesión con P50 973 µs frente a 524 µs |
| `muchos_candidatos.recuperacion_completa_rank` | INVALIDA — P95 disp. 41,6 ms | **VALIDA** — P95 disp. 10,6 ms | **la cola se domó**: −75 % |
| Nivel general de `rank()` | P50 62–73 ms | P50 46–54 ms | ~25 % más rápido con la máquina en reposo |

**Atribución.** La diferencia entre corridas se atribuye **únicamente a las
observaciones bajo condiciones distintas, no a cambios del método**: los
diffs de Git entre el commit de la v0.1 y el de la v0.2 sobre el arnés
congelado, el esquema, el protocolo, el perfil, el corpus y la ficha son
**vacíos**; el worker es el mismo módulo con la misma orden; y una prueba lo
comprueba. Las tres magnitudes de `rank()` —cuyo fallo v0.1 eran colas P95—
pasan al eliminar la carga concurrente: la causa ambiental queda confirmada
experimentalmente. Las magnitudes del índice ligero (~120–970 µs por sesión)
fallan el 20 % relativo **incluso en reposo**: a esa escala de microsegundos
la deriva entre procesos (caché, frecuencia, scheduling) excede el objetivo
relativo con este entorno, y eso es un **hecho del entorno medido**, no un
defecto del método ni una regla a suavizar.

## 4. Veredicto final conforme al §6.9 — la repetición está consumida

Regla congelada en el acta **antes** de medir: pasa P50 y P95 → `VALIDA`;
cualquier otro resultado → **`NO_EVALUABLE` en rendimiento** (§6.9).
`INVALIDA` no es publicable como estado definitivo tras consumir la
repetición única. **No existe tercera corrida.**

| Magnitud | Estado final de estabilidad |
|---|---|
| `cero_resultados.solo_indice_fts5` | **NO_EVALUABLE** (rendimiento) |
| `cero_resultados.recuperacion_completa_rank` | **VALIDA** |
| `un_resultado_exacto.solo_indice_fts5` | **NO_EVALUABLE** (rendimiento) |
| `un_resultado_exacto.recuperacion_completa_rank` | **VALIDA** |
| `muchos_candidatos.solo_indice_fts5` | **NO_EVALUABLE** (rendimiento) |
| `muchos_candidatos.recuperacion_completa_rank` | **VALIDA** |

**Resultado agregado final: 3 `VALIDA` · 3 `NO_EVALUABLE` · 0 `INVALIDA`
definitivas · 0 `NO_COMPARABLE`.** `T0-control` **no se descarta**: es el
control de falsación, no un candidato. Las tres magnitudes `NO_EVALUABLE` lo
son **en rendimiento** y así quedan registradas, con sus cifras crudas
íntegras para cualquier lectura futura.

## 5. Controles y custodia

- **Los once controles bloqueantes preinscritos: verdes**, derivados del
  estado observado (autorización —ambas actas—, actas de puerta, corpus por
  blob, línea base histórica intacta, ficha congelada y anterior, once
  sesiones, cien repeticiones, nearest-rank recomputado, escenarios y capas
  idénticos, veredictos delegados, línea base no sustituida).
- **El artefacto v0.2 valida contra el esquema congelado** antes y después de
  escribirse; escritura atómica; salidas exigidas inexistentes antes.
- **La evidencia v0.1 permanece intacta byte a byte** — precondición y
  control final, blobs verificados.
- **Nada cambió tras observar resultados**: ni protocolo, ni perfil, ni
  bandas, ni corpus, ni ficha, ni consultas, ni escenarios, ni capas, ni
  cronómetro, ni repeticiones, ni sesiones, ni esquema, ni percentiles, ni
  criterio de veredicto. La regla del estado final §6.9 se congeló en el
  commit **anterior** a la corrida.
- **La ficha fue anterior a ambas ejecuciones**: entrada en `95d00a1`,
  ancestro estricto de los dos commits de ejecución.

## 6. Lo que este informe no hace

- **No aprueba `ADR002-TOL-208`** ni crea su acta de satisfacción: la puerta
  sigue **NO SATISFECHA** hasta el acto explícito del usuario sobre esta
  evidencia final.
- No autoriza una tercera corrida — **prohibida** por el acta, el §6.9 y el
  §8.8.
- No convierte ninguna cifra observada en tolerancia ni fija límites nuevos.
- No descarta a T0. No sustituye la evidencia v0.1 ni la línea base
  histórica. No autoriza candidatos, benchmark ni el merge del PR #117.

---

**Estado:** la repetición reglamentaria del §6.8 queda **CONSUMIDA** y la
evidencia final de los pasos 2 y 3 de `ADR002-TOL-208` está completa: v0.1
(corrida original) + v0.2 (repetición controlada) + estados finales §6.9.
`ADR002-TOL-208` permanece **NO SATISFECHA** a la espera del acto explícito
del usuario. **El benchmark continúa bloqueado. El PR #117 continúa abierto y
sin fusionar.**

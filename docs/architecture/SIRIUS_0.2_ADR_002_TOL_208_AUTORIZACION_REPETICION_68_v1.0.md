# SIRIUS 0.2 — ADR-002 · Autorización de la repetición única controlada del §6.8 · TOL-208

**Versión:** 1.0
**Estado:** **APROBADO** — autorización expresa de exactamente UNA repetición
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**HEAD de partida verificado:** `3c9a1cb4185fead79c4c13d0c07d2223d223f782`
**Autoridad:** Usuario / Proyecto Sirius — «El usuario autoriza expresamente la repetición única controlada prevista por el §6.8 del protocolo v0.2»
**Acta que la precede:** `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md`, cuya corrida produjo la evidencia v0.1
**Motivo:** la primera ejecución produjo **cinco magnitudes `INVALIDA` por variación** (colas P95 de `rank()` y deriva relativa P50 de las magnitudes ligeras del índice), con la carga del entorno creciendo de 0,54 a 1,01 durante la corrida
**No autoriza:** una tercera corrida, cambiar tolerancias o protocolo, reescribir la evidencia v0.1, aprobar `ADR002-TOL-208` ni crear su acta final de satisfacción, iniciar el benchmark, implementar candidatos, modificar Sirius 0.1, ni fusionar el PR #117.

---

## 1. Registro literal de la autorización

Queda registrado, con carácter vinculante:

1. **Se autoriza exactamente UNA repetición** de la comparación de T0,
   conforme al §6.8 del protocolo v0.2: «si la comparación resulta inválida
   por variación, se repite una única vez en condiciones controladas
   conforme a este protocolo».
2. **La evidencia v0.1 permanece válida, congelada e intacta.** Esta
   repetición **no la sustituye ni la corrige**: la v0.2 se publica aparte y
   los tres ficheros v0.1 son intangibles por blob (§3.2).
3. **Ningún criterio se modifica después de observar resultados.** Protocolo
   v0.2, perfil y bandas aprobadas, corpus v0.4, ficha de `T0-control`,
   consultas derivadas, escenarios y capas, cronómetro, cien repeticiones,
   once sesiones, esquema de rederivación, fórmula de percentiles y criterio
   de veredicto: **idénticos e intocados**.
4. **Una segunda invalidez cierra el rendimiento como `NO_EVALUABLE`**,
   conforme al §6.9: «si vuelve a fallar, el candidato queda NO EVALUABLE en
   rendimiento y así se registra».
5. **Queda prohibida una tercera corrida**, conforme al §6.9 y al §8.8
   («prohibido repetir una comparación inválida más de una vez para
   "conseguir" un resultado válido»). El arnés de la repetición no ofrece
   ninguna puerta para ella: sin bucle de reintento, y con las salidas v0.2
   existentes como bloqueo permanente de toda invocación posterior.

### 1.1 Cuándo queda consumida la repetición

La repetición se **consume al abrirse la primera ventana cronometrada** de la
corrida v0.2. Un bloqueo **previo** —precondiciones de custodia o
asentamiento inicial no alcanzado— **no** la consume, porque no mide nada.
Consumida la repetición, cualquier desenlace distinto de una corrida válida
—invalidez funcional, cambio de arranque a mitad de corrida, controles
bloqueantes fallidos— se registra como **`NO_EVALUABLE`** sin escribir
artefacto y **sin tercera corrida**.

### 1.2 El estado final de estabilidad, congelado antes de medir

Consumida la repetición única, el estado definitivo de cada magnitud es:

- pasa P50 **y** P95 en la corrida v0.2 → **`VALIDA`**;
- cualquier otro veredicto → **`NO_EVALUABLE` en rendimiento** (§6.9).

**`INVALIDA` no es publicable como estado definitivo de estabilidad** después
de consumir la repetición. Esta regla queda materializada en
`controlled_conditions.estado_final_6_9`, congelada en este mismo commit,
**antes** de observar resultado alguno. El artefacto v0.2 sigue publicando el
veredicto crudo que recomputa el perfil —el esquema congelado lo exige—; el
estado final del §6.9 es la capa de gobierno que este acta fija sobre él.

`T0-control` **no se descarta** en ningún caso: es el control de falsación,
no un candidato.

## 2. Condiciones controladas, congeladas antes de medir

Materializadas y comprobadas por `controlled_conditions.py` y
`execute_repetition.py`, en este commit, conforme al protocolo existente y
realizables en `LAB-LINUX`:

| Condición | Materialización congelada |
|---|---|
| **Ausencia de tareas concurrentes evitables** | Ninguna batería de pruebas ni proceso pesado durante la ventana de medición; comprobado en lo observable: la carga media a 1 minuto debe ser **≤ 0,35** antes de abrir la primera ventana cronometrada (en reposo la máquina marca ~0,18; la corrida v0.1 arrancó a 0,54 por el residuo de la batería de pruebas) |
| **Carga inicial y evolución registrada** | La carga por sesión que ya registra el worker congelado, **más** la serie completa de cada espera de asentamiento, con duración y muestreo cada 5 s |
| **Misma máquina y arranque** | `boot_id` capturado antes y después; un cambio a mitad de corrida invalida la repetición (§6.9). **La igualdad con el arranque de la v0.1 no es realizable y no se finge**: el contenedor es efímero y aquel arranque (`fd0d2268-0abc-4037-8b2a-c0a91dade2ef`) ya no existe; el de la v0.2 se registra junto a él (§3.2 de las muestras) |
| **Once sesiones independientes** | Idénticas a la v0.1: once procesos del sistema operativo, secuenciales, con fichero, motor, caché y warm-up propios |
| **Orden y pausas** | Mismo orden de magnitudes y sesiones que la v0.1; antes de **cada** sesión, espera de asentamiento hasta carga ≤ 0,35 con plazo máximo de 120 s —la pausa técnica que reduce la deriva acumulada—; el asentamiento **previo** a la corrida tiene plazo de 600 s y, si no se alcanza, la corrida **no se inicia y la repetición no se consume** |
| **Sin alterar el trabajo medido** | Cada sesión es el **mismo worker** de `execute_rederivation` invocado con la **misma orden** que en la v0.1; las esperas ocurren fuera de los procesos de medición y una prueba comprueba que la orden del worker es idéntica |

Un plazo de asentamiento agotado **entre** sesiones no aborta la corrida
—abortar consumiría la repetición sin evidencia—: se registra como
incidencia y la corrida continúa.

## 3. Lo que no cambia y lo que queda intangible

### 3.1 Congelado e intocado

Protocolo v0.2 · perfil y bandas del acta de TOL-209 (`SM = 17 405 ns`,
`U50 = 2 685 ns`, `B50(U50) = 537 ns`) · corpus v0.4 por blob
(`4e9e2746…`, `c21b702c…`) · ficha `T0-control` v1 (huella `d47a767e…`,
entrada `95d00a1`, **anterior a ambas ejecuciones**) · consultas derivadas
por la regla cerrada (`zetaausentenoindexado` / `duna` / `la`) · escenarios y
capas · cronómetro `medir_ns` · **100** repeticiones · **11** sesiones ·
`schema_rederivation_v0_1` · percentiles nearest-rank · criterio de veredicto
del perfil.

### 3.2 Evidencia v0.1, intangible por blob

| Fichero | Blob Git |
|---|---|
| `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json` | `781132bfe0365f6b7ebcb9139330d10dc76fd0db` |
| `artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json` | `04cd805181f9067318adaf84aaa676df1eb52c7c` |
| `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.1_PROPUESTO.md` | `11d41f42838a3fb3512bfe32dcf9e35689980611` |

Su integridad es **precondición** para medir y **control final** tras
escribir la v0.2.

### 3.3 Salidas de la repetición

`artifacts/adr002_tolerances/rederivacion_t0_v0.2.json` ·
`rederivacion_t0_v0.2_muestras.json` ·
`INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md` — exigidas **inexistentes** antes
de medir; su existencia posterior bloquea permanentemente cualquier nueva
invocación del arnés de repetición.

## 4. Lo que esta acta no hace

- **No aprueba `ADR002-TOL-208`** ni crea su acta final de satisfacción: la
  puerta seguirá **NO SATISFECHA** hasta el acto explícito del usuario sobre
  la evidencia final.
- No acepta de antemano ningún resultado de la v0.2.
- No autoriza tercera corrida, benchmark, candidatos `ADR002-A/B/C/D`,
  cambios en Sirius 0.1 (`src/`, `tests/`, `migrations/`, configuración
  productiva) ni la fusión del PR #117.

---

**Decisión final:** queda autorizada **exactamente una** repetición
controlada de la comparación de T0 conforme al §6.8, con las condiciones del
§2 congeladas antes de medir, la evidencia v0.1 intangible, el estado final
del §6.9 fijado por regla previa a la observación, y la prohibición expresa
de una tercera corrida. `ADR002-TOL-208` seguirá **NO SATISFECHA** hasta el
acto explícito del usuario. El PR #117 permanece abierto y sin fusionar.

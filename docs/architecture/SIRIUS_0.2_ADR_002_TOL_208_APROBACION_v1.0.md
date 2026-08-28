# SIRIUS 0.2 — ADR-002 · Aprobación de TOL-208

**Versión:** 1.0
**Estado:** **APROBADO · ADR002-TOL-208 SATISFECHA**
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado:** `df3355b287717aa40cba20d783bde80583289622`
**Autorización explícita del usuario:** «**aprobado**»

## 0. Objeto

Esta acta materializa la aprobación explícita de `ADR002-TOL-208` —**corpus
definitivo congelado, T0 ejecutado sobre él y comparación de línea base
rederivada**— tras la ejecución original v0.1, la repetición única controlada
del §6.8 que produjo la evidencia v0.2, y la fe de erratas 01 que corrigió la
única cita de identidad Git defectuosa sin reescribir evidencia alguna.

Desde esta acta, `ADR002-TOL-208` queda **SATISFECHA** dentro del alcance
exacto definido aquí, y **las cinco puertas de arranque de ADR-002 quedan
satisfechas**.

Los documentos y artefactos conservan sus nombres y etiquetas históricas
`PROPUESTO`. Esta acta prevalece sobre esas etiquetas sin reescribirlos,
preservando las identidades exactas auditadas.

## 1. Decisión aprobada

Se aprueba la **evidencia final de `ADR002-TOL-208` tal como quedó publicada**,
sin modificación alguna de sus cifras, su método ni sus veredictos:

1. **Paso 1 — corpus congelado.** El corpus definitivo v0.4 quedó congelado
   por su acta y citado **por blob** en todo el recorrido.
2. **Paso 2 — T0 ejecutado sobre ese mismo corpus.** Ejecución real de
   `T0-control` sobre el corpus congelado v0.4, con el plan preinscrito por el
   paquete de trabajo 10.
3. **Paso 3 — comparación de línea base rederivada.** Rederivación con
   **exactamente once sesiones** independientes, que es lo que devuelve la
   comparabilidad que la regla 3.3.b del protocolo exigía: **ninguna magnitud
   queda `NO_COMPARABLE`**.
4. **Repetición reglamentaria consumida.** La corrida original v0.1 produjo
   cinco magnitudes `INVALIDA` por variación; el usuario autorizó la
   **repetición única del §6.8**, que se ejecutó bajo condiciones ambientales
   controladas congeladas antes de medir y **quedó consumida**.
5. **Resultado final conforme al §6.9**, por la regla congelada **antes** de
   observar resultado alguno.

### 1.1 El resultado final que esta acta acepta

| Magnitud | Estado final de estabilidad |
|---|---|
| `cero_resultados.solo_indice_fts5` | **NO_EVALUABLE** en rendimiento |
| `cero_resultados.recuperacion_completa_rank` | **VALIDA** |
| `un_resultado_exacto.solo_indice_fts5` | **NO_EVALUABLE** en rendimiento |
| `un_resultado_exacto.recuperacion_completa_rank` | **VALIDA** |
| `muchos_candidatos.solo_indice_fts5` | **NO_EVALUABLE** en rendimiento |
| `muchos_candidatos.recuperacion_completa_rank` | **VALIDA** |

**Agregado: 3 `VALIDA` · 3 `NO_EVALUABLE` · 0 `INVALIDA` definitivas ·
0 `NO_COMPARABLE`.**

Las tres magnitudes `NO_EVALUABLE` **permanecen expresamente `NO_EVALUABLE`**:
esta acta las acepta como tales, no las convierte en válidas ni las suaviza.
Sus cifras crudas quedan íntegras para cualquier lectura futura.

### 1.2 `T0-control` no se descarta

`T0-control` es el **control de falsación**, no un candidato. El Registro
declara que T0 «no es un presupuesto heredable» y que ningún candidato se
descarta por superar el tiempo de T0. Que tres de sus seis magnitudes queden
`NO_EVALUABLE` en rendimiento **no lo descarta ni lo invalida como control**:
los candidatos se juzgarán contra **sus propios límites congelados**, no
contra T0.

### 1.3 Lo que la evidencia demostró sobre la causa

Las tres magnitudes de `recuperacion_completa_rank` fallaban en la v0.1 por
**colas P95** (dispersiones de 35–42 ms frente a una banda de 25,2 ms). Bajo
carga controlada esas colas cayeron a 10,6–14,4 ms y **las tres pasaron**: la
causa ambiental queda **confirmada experimentalmente**. Las tres magnitudes de
`solo_indice_fts5` fallan el objetivo relativo P50 del 20 % **incluso con la
máquina en reposo**, a escala de 120–970 µs por sesión: es un **hecho del
entorno medido**, no un defecto del método ni una regla que esta acta suavice.

### 1.4 Prohibición expresa de una tercera corrida

**No existe autorización para una tercera corrida**, y esta acta no la crea.
Rigen el §6.9 y el §8.8 del protocolo: la repetición única está **consumida** y
repetir una comparación inválida más de una vez para «conseguir» un resultado
válido está expresamente prohibido.

### 1.5 La línea base histórica no fue sustituida

`artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json` —blob
`f9f051332d9833fb7e10b27f4820849f00b6fe6c`, cinco sesiones— permanece
**congelada, intacta y no sustituida**. El campo
`linea_base_historica.sustituida` es `False` en ambos artefactos normativos, y
su integridad fue precondición y control final de **ambas** ejecuciones. Lo que
esta acta aprueba es una medición **nueva** sobre el corpus definitivo,
publicada aparte.

## 2. Identidad vinculante de la evidencia aprobada

La identidad se fija mediante blobs Git en el commit auditado
`df3355b287717aa40cba20d783bde80583289622`.

### 2.1 Gobierno y preparación

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md` | `414a2b3764f40461ead754b98945efcbe6345fae` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_10_TOL208_REDERIVACION_T0_v0.1.md` | `9f609e954516b6390d989bbd761bc5afb832a742` |
| `artifacts/adr002_cards/ficha_T0-control_v1.json` | `c25a293c34644e2195d812ef8777246400e52c96` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_210_ACTO_SUCESOR_01_EXENCION_T0_v1.0.md` | `d2f7a44518d4938e08f94fa1fcac0dd0099008cc` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md` | `f548c9a335c3ce79134a47882e0d5328c81af231` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_REPETICION_68_v1.0.md` | `217a8ce543c57362c00b17c6d99dd7063755e49d` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` | `cf65d67458b616d1f095a307c01ee1b6a590e0e2` |
| `artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json` | `41003495620aaf9cd37404b45bf359410c4e7504` |
| `docs/architecture/SIRIUS_0.2_ADR_002_FE_DE_ERRATAS_01_IDENTIDAD_GIT_v1.0.md` | `e08be4a99f0b427a29af1a443b75ee4b90efd5b7` |

**Ficha de `T0-control` v1** · huella canónica
`d47a767e61b30729e15f48c9924413f6fddc9429` · commit de entrada
`95d00a1c3c4fc0a9ed74374d1786bec9bd0b3483`, **ancestro estricto de ambos
commits de ejecución**, observado en el grafo de Git y no declarado por la
propia ficha. El acto sucesor 01 se introdujo en el commit
`c881fce697009d294121c5b99d23ba6af5b8b173`.

**Corpus congelado v0.4**, citado por blob y con el commit auditado de su acta
`d27352b9f03dfc6a4d939b855474ce0ad1c2fc86`:

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/benchmark/performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` |
| `experiments/adr002/benchmark/conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |

**Perfil aprobado por el acta de `ADR002-TOL-209`**: `SM = 17 405 ns`,
`U50 = 2 685 ns`, `B50(U50) = 537 ns`, **exactamente once sesiones**. Los
veredictos se delegaron **enteramente** en él: la rederivación no inventó
criterio propio.

### 2.2 Ejecución v0.1 — corrida original

**Commit de ejecución:** `425964872c73ec4e4f44d80189907d7ca08bedff`

| Artefacto | Blob Git |
|---|---|
| `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json` | `781132bfe0365f6b7ebcb9139330d10dc76fd0db` |
| `artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json` | `04cd805181f9067318adaf84aaa676df1eb52c7c` |
| `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.1_PROPUESTO.md` | `11d41f42838a3fb3512bfe32dcf9e35689980611` |

**Se conserva íntegra.** La repetición del §6.8 no la sustituyó ni la
corrigió: ambas corridas coexisten y sus muestras **no se mezclan**.

### 2.3 Repetición v0.2 — repetición única controlada del §6.8

**Commit de autorización y preinscripción:**
`5797f523c9d4f0e0d3f99599493b6e3167b29f9d`
**Commit de evidencia:** `c5f76cd89a56d45d2822b3e9010ca02c9a9f6a20`
**Commit de la fe de erratas:** `df3355b287717aa40cba20d783bde80583289622`

| Artefacto | Blob Git | Papel |
|---|---|---|
| `artifacts/adr002_tolerances/rederivacion_t0_v0.2.json` | `9140c1c031ed4bff891fc0fdabb04b4480a8d817` | artefacto normativo |
| `artifacts/adr002_tolerances/rederivacion_t0_v0.2_muestras.json` | `8a61b8e519d6d854d782106aed19614ebd2377a5` | muestras crudas, condiciones controladas y estado §6.9 |
| `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md` | `dac5155914d55b7e1e294ebca1d16f0ef6e6e656` | **evidencia histórica, conservada intacta** con su errata de identidad |
| `artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2.1_PROPUESTO.md` | `b852757db53c9556351b31dadae18823ff20c0cb` | **lectura vigente corregida** |

**El informe v0.2 no se reescribe.** La fe de erratas 01 estableció que la
identidad vinculante del commit de autorización es
`5797f523c9d4f0e0d3f99599493b6e3167b29f9d`, que la cita
`5797f5205cdb3054921054461f77dbdb8f550af4` publicada en el v0.2 es errónea y
no resuelve a ningún objeto —ambas comparten el prefijo abreviado `5797f52`—,
y que el error **no afecta muestras, cifras, método, blobs, veredictos ni el
resultado del §6.9**. La lectura vigente pasó a ser el informe v0.2.1.

Esta acta **cita expresamente el SHA erróneo** para que la aprobación sea
autocontenida: una aprobación que no dijera *qué* cita era defectuosa
obligaría a salir de ella para entenderla. Por eso queda añadida al inventario
de documentos que **declaran** esa errata —no es una excepción nueva, sino la
misma errata ya inventariada, declarada en un documento más—, y el verificador
de custodia lo comprueba.

### 2.4 Arnés de medición, congelado antes de cada ejecución

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/rederivation/rederivation_protocol.py` | `1e69d466907538bdc9ad98049c3ef0cf658db273` |
| `experiments/adr002/rederivation/schema_rederivation_v0_1.py` | `96b915c2874d2d3c3735ebb676d63398f323026d` |
| `experiments/adr002/rederivation/execute_rederivation.py` | `1532c3da60fc13c0a20abe9935607d0fa309d1df` |
| `experiments/adr002/rederivation/frozen_corpus.py` | `081366080b5c941194d1df2ff8b51d44ec54a2a6` |
| `experiments/adr002/rederivation/controlled_conditions.py` | `f2b12d524cca2ce924c676fab15afdb7fae9f1eb` |
| `experiments/adr002/rederivation/execute_repetition.py` | `981a3ec1b7045639e574461cf233fb4fe8042858` |
| `experiments/adr002/rederivation/custody_errata.py` | `54d8d915d93bacd5663f1b768196af58b2aa29a8` |

El **esquema de rederivación** se congeló en el paquete 10, **antes de que
existiera medición alguna**, que es lo que impidió ajustarlo tras ver los
resultados.

## 3. Alcance exacto de lo que queda satisfecho

`ADR002-TOL-208` queda **SATISFECHA** con este alcance, ni más ni menos:

1. **El corpus definitivo fue congelado** (v0.4, citado por blob).
2. **T0 fue ejecutado sobre ese corpus**, dos veces: la corrida original y la
   repetición única del §6.8, ambas sobre el **mismo** corpus congelado.
3. **La comparación de línea base fue rederivada con once sesiones**, y por
   ello **ninguna magnitud queda `NO_COMPARABLE`**.
4. **La repetición reglamentaria fue consumida.**
5. **Las tres magnitudes no evaluables permanecen expresamente
   `NO_EVALUABLE`** en rendimiento.
6. **No existe autorización para una tercera corrida.**
7. **La línea base histórica no fue sustituida.**

## 4. El método, intacto de principio a fin

Comprobado contra el grafo de Git, no declarado:

- **Nada cambió tras observar resultados.** Los diffs entre el commit de la
  ejecución v0.1 y el de la repetición v0.2 sobre el arnés, el esquema, el
  protocolo, el perfil, el corpus y la ficha son **vacíos**.
- **La operación medida fue idéntica en ambas corridas**: el ejecutor de la
  repetición invoca el **mismo worker congelado con la misma orden**, y las
  esperas de asentamiento ocurren **fuera** de los procesos de medición.
- **Once sesiones exactas** en procesos independientes, **cien repeticiones**
  por magnitud, percentiles **nearest-rank** nunca interpolados, veredictos
  **delegados** al perfil aprobado.
- **Los once controles bloqueantes** preinscritos salieron verdes en ambas
  corridas, derivados del estado observado.
- **Ambos artefactos validaron contra el esquema congelado** antes de
  escribirse, con escritura atómica sin sobrescribir, y revalidaron tras
  releerse.
- **Percentiles, extremos, dispersiones, bandas y veredictos se recomputaron
  de forma independiente** desde las muestras crudas de ambas corridas: cero
  discrepancias.

## 5. Actualización del mecanismo derivado de estado

`verify_cards` **no acepta que le declaren qué puertas están satisfechas**: lo
**deriva de las actas que existen**. Para que el repositorio reconozca esta
acta se actualiza **únicamente** lo imprescindible:

> `experiments/adr002/cards/card_protocol.py` — la entrada
> `"ADR002-TOL-208": None` pasa a citar esta acta.

El campo era `None` **por diseño explícito**: el propio módulo documentaba que
«`None` significa que no existe todavía, y por tanto que la puerta NO está
satisfecha». Este es exactamente el cambio que el módulo preveía, y **el
único** que se hace: ninguna regla, umbral ni comprobación se toca.

El blob de `card_protocol.py` fijado por el §2.2 del acta de `ADR002-TOL-210`
cambia en consecuencia —de `f0823e1d96dcd614f749371a9341103e8e99ef4d` al que
registre este commit—, y se registra aquí conforme a la regla de custodia §8.5
de aquella acta.

**Dos pruebas de estado evolucionan** en este mismo commit, conservando su
severidad fail-closed: cambian el estado esperado, no el criterio.

| Prueba | Antes afirmaba | Ahora afirma |
|---|---|---|
| `test_adr002_cards.py::test_el_estado_de_las_puertas_se_deriva_de_las_actas_que_existen` | `TOL-208` en `False` y arranque incompleto | `TOL-208` en `True` **porque su acta existe**, y las **cinco** puertas satisfechas |
| `card_protocol.estado_de_las_puertas` (docstring) | citaba `TOL-208` y `TOL-210` como pendientes | cita el principio sin nombrar puertas ya aprobadas |

Las capturas históricas de estado —como la del paquete de almacenamiento, que
sigue registrando el estado del día en que se tomó— **no se reescriben**: son
evidencia fechada, no mecanismo vivo.

## 6. Estado de las puertas tras esta acta

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-208` | **SATISFECHA** — por esta acta |
| `ADR002-TOL-209` | **SATISFECHA** |
| `ADR002-TOL-210` | **SATISFECHA** |

**Las cinco puertas de arranque de ADR-002 quedan satisfechas. Termina el
papeleo previo al benchmark.**

Esto significa, exactamente: **ninguna puerta de arranque bloquea ya el
benchmark**. No significa que el benchmark esté autorizado, ni que ningún
candidato lo esté: eso son actos posteriores y distintos, que esta acta no
otorga (§7).

## 7. Lo que esta acta no autoriza

- **No autoriza ejecutar ninguna medición más**, ni una tercera corrida:
  expresamente **prohibida** por el §6.9, el §8.8 y el §1.4 de esta acta.
- **No cambia** el protocolo, el perfil, las bandas ni el corpus.
- **No reescribe** ninguna evidencia histórica: v0.1, v0.2 y la línea base
  histórica se conservan con sus blobs exactos.
- **No convierte en `VALIDA`** ninguna magnitud `NO_EVALUABLE`, ni fija
  ninguna tolerancia nueva a partir de cifras observadas.
- **No implementa ni ejecuta** `ADR002-A`, `ADR002-B`, `ADR002-C` ni
  `ADR002-D`.
- **No inicia el benchmark.**
- No aprueba el resto del Registro v0.5.
- No modifica Sirius 0.1 (`src/`, `tests/`, `migrations/` ni configuración
  productiva).
- No abre otro PR y **no fusiona el PR #117**.

## 8. Reglas de custodia

1. **La evidencia aprobada es inmutable.** Los siete artefactos de evidencia
   —tres de v0.1, tres de v0.2 y la lectura vigente v0.2.1— conservan sus
   blobs. Cualquier alteración invalida esta acta.
2. **La repetición del §6.8 está consumida y no se regenera.** Una tercera
   corrida exigiría una decisión de gobierno que ni esta acta ni ninguna otra
   otorgan, y el §8.8 del protocolo la prohíbe expresamente.
3. **Las magnitudes `NO_EVALUABLE` no se reinterpretan.** Publicarlas como
   válidas más adelante, sin nueva evidencia autorizada, contradiría esta
   acta.
4. **La línea base histórica se conserva** con su head y sus ficheros, y no se
   sustituye.
5. **Toda cita de identidad Git es comprobable por máquina**: el verificador
   de custodia exige que cada SHA completo citado en gobierno y evidencia
   resuelva a un objeto del repositorio, con sus dos clases de excepción
   inventariadas y ancladas por blob.
6. Cualquier cambio de los contenidos vinculados en la §2 exige revisión
   explícita y un **acto sucesor**.
7. Las etiquetas internas `PROPUESTO` permanecen como historia auditada y no
   disminuyen la autoridad de esta acta.

---

**Decisión final:** `ADR002-TOL-208` queda **APROBADA y SATISFECHA** con el
alcance de la §3, aceptando la evidencia final tal como quedó publicada —3
magnitudes `VALIDA`, 3 `NO_EVALUABLE` en rendimiento, 0 `INVALIDA` definitivas
y 0 `NO_COMPARABLE`—, con la repetición reglamentaria **consumida**, la tercera
corrida **prohibida** y la línea base histórica **no sustituida**. **Las cinco
puertas de arranque de ADR-002 quedan satisfechas y el papeleo previo al
benchmark termina aquí.** El benchmark, los candidatos y la fusión del PR #117
continúan **no autorizados** y requieren actos posteriores y distintos.

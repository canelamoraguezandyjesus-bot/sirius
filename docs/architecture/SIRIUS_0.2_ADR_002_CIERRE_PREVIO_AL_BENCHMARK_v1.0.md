# SIRIUS 0.2 — ADR-002 · Cierre previo al benchmark

**Versión:** 1.0
**Estado:** **CERRADO · a la espera de una única autorización**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** paso **10** del plan aprobado por
`SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v1.0_APROBADA.md`
§4 — cerrar la fase previa al benchmark sobre los cinco participantes.

Este documento **no mide nada y no autoriza nada**. Hace dos cosas: deja
constancia comprobable de que todo lo que la ronda primaria necesita está en su
sitio, y deja congelado —antes de que exista un solo resultado— cómo se
ejecutará. La autorización para medir es un acto aparte, y se pide al final.

---

## 1. La afirmación que este cierre sostiene

> Sobre el repositorio real, la **única** precondición sin satisfacer de la
> ronda primaria es **la autorización para medir**.

Es una afirmación por resta, y por eso es falsable en un solo comando:

```
$ uv run python -m experiments.adr002.round.run_round --check
ronda primaria BLOQUEADA: 1 precondicion(es) sin satisfacer
  - ejecutar_la_ronda_primaria_no_esta_autorizado: falta
    SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md. Medir la ronda
    primaria exige autorizacion expresa e independiente, y ninguna acta la ha dado
$ echo $?
2
```

Si fallara alguna otra precondición, esta fase **no** estaría cerrada. Si no
fallara ninguna, la guarda **no** estaría guardando nada. La prueba
`test_la_unica_precondicion_pendiente_es_la_autorizacion` fija exactamente esa
lista de un solo elemento, y se romperá el día que deje de ser cierta.

---

## 2. Los cinco participantes

La ronda primaria es `T0 + A + B + C + D`, **sin reducción**: la Resolución de
la partición §2.2 prohíbe retirar una alternativa mínima del universo de
candidatos, y `run_round` rechaza cualquier lista que no sea exactamente esa.

| Participante | Ficha | Estado | Huella canónica | Congelada en | Acta de preparación |
|---|---|---|---|---|---|
| `T0-control` | v1 | CONGELADA | `d47a767e61b30729e15f48c9924413f6fddc9429` | `c881fce6` | sin acta propia, y no la necesita (v. abajo) |
| `ADR002-A` | v5 | CONGELADA | `b5549a5a8e0f2fa4e791f64fbdb1c769938949be` | `4bb58c7a` | `..._REAPROBACION_CONJUNTA_A_V5_Y_B_V7_v1.0.md` |
| `ADR002-B` | v7 | CONGELADA | `33a7617dc8713d7dc29fce1877b7c41d689f25d7` | `4bb58c7a` | `..._REAPROBACION_CONJUNTA_A_V5_Y_B_V7_v1.0.md` |
| `ADR002-C` | v2 | CONGELADA | `5e034078eb1d01ef6485cfd10707ce30f92ed7e5` | `5bdf02dd` | `..._ADR002_C_V2_PREPARADO_BENCHMARK_APROBACION_v1.0.md` |
| `ADR002-D` | v2 | CONGELADA | `7cc6ccc9afab331322cc45da17215def2566beae` | `0f7417b5` | `..._ADR002_D_V2_PREPARADO_BENCHMARK_APROBACION_v1.0.md` |

**Congelar y preparar son actos distintos.** Congelar es técnico: la huella
canónica queda fija. Preparar es de gobierno: alguien con autoridad declara que
esa ficha puede entrar en la ronda. `fallos_de_preparacion` exige las dos cosas,
y un candidato con ficha y sin acta no entra.

`T0-control` no tiene acta de preparación propia y no la necesita: no es
candidato sino **control de falsación** (Resolución de la partición §3), y su
medición ya fue autorizada y ejecutada bajo `ADR002-TOL-208`.

### 2.1 Una sola ficha vigente por participante

El verificador recomputa las **diecisiete** fichas del repositorio y las
adjudica sin fallos. De ellas, **cinco están `CONGELADA`** —una por
participante— y **doce están `SUSTITUIDA`**:

- `ADR002-A`: v1–v4 sustituidas, **v5 vigente**
- `ADR002-B`: v1–v6 sustituidas, **v7 vigente**
- `ADR002-C`: v1 sustituida, **v2 vigente**
- `ADR002-D`: v1 sustituida, **v2 vigente**
- `T0-control`: **v1 vigente**, sin sustituciones

`fallos_de_fichas` bloquea por tres motivos distintos, y los tres importan: que
falte la ficha, que haya **más de una** `CONGELADA` para el mismo participante,
y que la huella no sea la que esta ronda preinscribió. La tercera es la que
impide medir bajo una ficha que cambiara **después** de declarar el plan.

### 2.2 Custodia: cada ficha en un commit anterior

`ADR002-TOL-210` regla 3 exige que la ficha viva en un commit **antecesor
estricto** del que ejecuta. Comprobado sobre el `HEAD` de este cierre:

| Ficha | Commit de congelación | ¿antecesor estricto del `HEAD`? |
|---|---|---|
| `T0-control` v1 | `c881fce697009d294121c5b99d23ba6af5b8b173` | **sí** |
| `ADR002-A` v5 | `4bb58c7a96f21ea601c28ff57caf67e4ee002a89` | **sí** |
| `ADR002-B` v7 | `4bb58c7a96f21ea601c28ff57caf67e4ee002a89` | **sí** |
| `ADR002-C` v2 | `5bdf02dd988dd6015694d95a01b6ee835531ce15` | **sí** |
| `ADR002-D` v2 | `0f7417b5045f4d80c9b36a902626eec677838565` | **sí** |

Ninguna ficha se congeló en el mismo commit que la ejecutará: describir y medir
quedan separados en el tiempo, que es lo que la regla persigue.

---

## 3. Las cinco puertas de arranque

Cada puerta está satisfecha por un acta que **existe** en el repositorio;
`fallos_de_puertas` lo comprueba leyendo, no declarando.

| Puerta | Acta que la satisface |
|---|---|
| `SRC-ADR002-01` | `SIRIUS_0.2_ADR_002_TOL_207_APROBACION_v1.0.md` |
| `ADR002-TOL-207` | `SIRIUS_0.2_ADR_002_TOL_207_APROBACION_v1.0.md` |
| `ADR002-TOL-208` | `SIRIUS_0.2_ADR_002_TOL_208_APROBACION_v1.0.md` |
| `ADR002-TOL-209` | `SIRIUS_0.2_ADR_002_TOL_209_APROBACION_v1.0.md` |
| `ADR002-TOL-210` | `SIRIUS_0.2_ADR_002_TOL_210_APROBACION_v1.0.md` |

---

## 4. La entrada, congelada byte a byte

Los cinco se miden sobre **el mismo** corpus, contra **la misma** línea base y
bajo **el mismo** perfil, o no es una comparación (protocolo v0.2 §5.4). La
ronda no lo declara de palabra: fija el blob de Git de cada artefacto y lo
recomputa.

| Artefacto | Blob de Git |
|---|---|
| `experiments/adr002/benchmark/conformance_corpus_v0_4.json` | `c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48` |
| `experiments/adr002/benchmark/performance_corpus_v0_2.json` | `4e9e2746e49b158a43eda7826b47c78c41b36e90` |
| `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json` | `781132bfe0365f6b7ebcb9139330d10dc76fd0db` |
| `artifacts/adr002_tolerances/rederivacion_t0_v0.2.json` | `9140c1c031ed4bff891fc0fdabb04b4480a8d817` |
| `artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json` | `41003495620aaf9cd37404b45bf359410c4e7504` |
| `artifacts/adr002_tolerances/suelo_medicion_v0.3.json` | `7273264879ec0d45861160066555c1f08b5882bc` |

Las tres comprobaciones —corpus, línea base, perfil y suelo— pasan. Las pruebas
`test_alterar_un_artefacto_congelado_bloquea` demuestran además que **alterar
cualquiera de ellos bloquea**, que es lo que da valor a que hoy no bloqueen.

La línea base incluye **las dos** rederivaciones de `T0`: la original y la
repetición controlada del §6.8. El perfil y el suelo estaban congelados antes
del benchmark, como exige el protocolo §6.6, y de ellos salen las bandas y `SM`.

---

## 5. Neutralidad y aislamiento

| Auditoría | Resultado |
|---|---|
| Capa común neutral (no nombra a ningún candidato) | **sin hallazgos** |
| Aislamiento de `adr002_a` | **sin hallazgos** |
| Aislamiento de `adr002_b` | **sin hallazgos** |
| Aislamiento de `adr002_c` | **sin hallazgos** |
| Aislamiento de `adr002_d` | **sin hallazgos** |

La ronda **no reimplementa** estas auditorías: recibe sus resultados ya
calculados por `neutrality`, el mismo módulo que ejecutan las suites de cada
candidato. Una segunda implementación podría discrepar de la primera, y
entonces no sabríamos cuál manda.

`t0_control` no aparece en la lista de paquetes aislados a propósito: no es un
candidato sino el arnés del control, y su propia suite lo vigila.

---

## 6. La puerta 7: almacenamiento

El presupuesto de `ADR002-TOL-207` es **por candidato**, `1 610 612 736 B`.

| Participante | Consumo declarado | ‰ del presupuesto | Proyección a 50 000 | ¿cabe? |
|---|---|---|---|---|
| `ADR002-A` | `1 462 272 B` | 0 | `14 622 720 B` | **sí** |
| `ADR002-B` | `35 016 704 B` | 21 | `350 167 040 B` | **sí** |
| `ADR002-C` | `0 B` | 0 | `0 B` | **sí** |
| `ADR002-D` | `35 016 704 B` | 21 | `350 167 040 B` | **sí** |

Las cuatro cifras se leen de las fichas congeladas; el bloque
`almacenamiento` sólo lleva números, y la razón de cada uno está en la
derivación que produjo la ficha, no en la ficha:

- `ADR002-C` declara **cero** porque su fuente relacional no crea estructura
  persistente propia: consulta la que ya existe.
- `ADR002-D` declara **exactamente lo mismo que `ADR002-B`**, hasta el byte,
  porque su única estructura persistente es el sidecar vectorial que hereda de
  él, y la señal relacional que añade no consume almacenamiento adicional, por
  el mismo motivo que en `C`. La coincidencia no es casual: se deriva.

Los cuatro caben con holgura, y también su suma —`71 495 680 B`, un 4,4 % del
presupuesto—, aunque el presupuesto de `TOL-207` es **por candidato** y la suma
no es la prueba que la puerta exige.

`T0-control` **no declara consumo**, y eso es deliberado: su ficha cita el
presupuesto «como referencia del entorno» y añade que «el control no compite por
la puerta 7 y su consumo se conocerá al medir, nunca antes». Declararlo hoy
sería inventarlo.

---

## 7. El plan de ejecución, congelado antes de medir

El protocolo v0.2 §8.1 prohíbe cambiar el protocolo **después** de observar
resultados. La única forma de que esa prohibición signifique algo es congelar el
plan antes de que exista el primer resultado, y eso es lo que hace
`experiments/adr002/round/round_protocol.py`.

| Parámetro | Valor congelado | Norma |
|---|---|---|
| Participantes | los cinco, sin reducción | Resolución de la partición §2.2 |
| Sesiones | **11 exactas** | `TOL-107`, protocolo §3.3 |
| Repeticiones | **100** por escenario y magnitud | protocolo §3.2 |
| Warm-up | **10**, declarado y descartado íntegro | protocolo §2.3 |
| Semilla | `20260726`, fija y declarada | protocolo §5.3 |
| Reloj | `time.perf_counter_ns`, monotónico | protocolo §2.1 |
| Orden | intercalado y **rotado** | protocolo §5.2 |
| Salida | `artifacts/adr002_round/ronda_primaria_v0.1.json` | — |

**Once exactas, no «al menos once»**: un rango calculado sobre otro tamaño de
muestra es `NO_COMPARABLE` y no recibe veredicto.

### 7.1 Por qué el orden rota

El protocolo prohíbe ejecutar todos los bloques de un candidato seguidos de
todos los de otro, porque la deriva del entorno se convertiría en ventaja. Pero
un orden intercalado **fijo** tiene el mismo problema en pequeño: quien va
primero paga la caché fría siempre. `orden_de_ejecucion(sesion, repeticion)`
rota por `(sesion + repeticion) mod 5`, de modo que dentro de cada sesión, a lo
largo de las cien repeticiones, **cada participante ocupa cada posición
exactamente veinte veces** —no sólo la primera: la segunda mide detrás de un
candidato concreto y la última mide con el entorno más caliente, y esas ventajas
tampoco pueden ser de nadie fijo—. Sobre las once sesiones, doscientas veinte
veces cada celda. Lo comprueba
`test_cada_participante_ocupa_cada_posicion_el_mismo_numero_de_veces`.

Es determinista y sin aleatoriedad —misma sesión y misma repetición dan siempre
el mismo orden—, que es lo que §5.3 exige. Las cuatro primeras combinaciones:

| Sesión | Repetición | Orden |
|---|---|---|
| 1 | 1 | `B → C → D → T0 → A` |
| 1 | 2 | `C → D → T0 → A → B` |
| 2 | 1 | `C → D → T0 → A → B` |
| 2 | 2 | `D → T0 → A → B → C` |

Que `(1, 2)` y `(2, 1)` den el mismo orden no es un descuido: la rotación
depende de la suma, y sesiones distintas se ejecutan en ventanas distintas, de
modo que la coincidencia no acumula ventaja para nadie. Lo que sí importa —el
reparto de posiciones **dentro** de cada sesión— queda exacto.

### 7.2 Lo que toda medición registrará

Las once entradas del §7 del protocolo quedan preinscritas como lista —no como
valores, que no existen todavía—: ficha del candidato con id, versión y huella;
corpus con versión, volúmenes y commit; entorno; versión del protocolo y
desviaciones; escenario y magnitud con `n` y warm-up; distribución completa;
resolución del percentil para ese `n`; sesiones y variación por la fórmula §6.1;
régimen y umbral en vigor; veredicto de validez; e incidencias del entorno.

La evidencia mínima del §10 de la especificación queda igual de preinscrita, con
sus once entradas. La décima —«la etapa de cada señal tardía y la no
coordinación»— es **propia de `ADR002-D`** y sólo él puede satisfacerla, porque
es el único con dos señales tardías que separar.

---

## 8. La guarda

`ACTA_DE_AUTORIZACION` apunta a
`SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md`, que **no existe**. Su
ausencia es la guarda, no un comentario sobre la guarda.

**No hay bandera de línea de órdenes que la salte.** La autorización es un
documento del repositorio, no un argumento que cualquiera pueda pasar. Es la
misma guarda que `TOL-208` usó para `T0`, y por el mismo motivo.

`comprobar_precondiciones` **no cortocircuita** en el primer fallo, a propósito:
quien prepare la ejecución debe ver de una vez todo lo que le falta, no
descubrirlo de uno en uno.

Los diecisiete controles bloqueantes quedan preinscritos por nombre:
autorización expresa, actas de puerta, actas de preparación, corpus intacto,
línea base intacta, perfil y suelo congelados, una sola ficha por participante,
huellas iguales a las del repositorio, ronda sin reducción, capa común neutral,
candidatos aislados, orden intercalado y rotado, semilla fija, once sesiones,
warm-up descartado, percentiles por rango más cercano y registro obligatorio
completo.

### 8.1 Por qué se preinscribe antes de pedir la autorización

Porque autorizar un arnés que todavía no existe sería autorizar a ciegas. El
precedente es `ADR002-TOL-208`: allí el arnés real de medición se preinscribió
**antes** de ejecutar, y la ejecución vino después. Lo que se aprueba aquí es
código que ya se puede leer.

---

## 9. Lo que los cinco ya demostraron, sin medir

La conformidad y el discriminante son propiedades **funcionales**: se comprueban
con fixtures deterministas y sin cronómetro, y ya están comprobadas. Nada de
esto es una medición de rendimiento, y ninguna de estas pruebas mide tiempo.

| Participante | Lo demostrado |
|---|---|
| `T0-control` | conformidad de la línea base sobre el corpus definitivo, y custodia de las fuentes que **ejecuta** |
| `ADR002-A` | base léxico-estructurada con `E3` dirigida real y regeneración canónica |
| `ADR002-B` | señal vectorial con ciclo de vida real del sidecar, validación lógica, defensa de frontera y minimización de mensajes |
| `ADR002-C` | señal relacional explícita, con su delta relacional y su puerta de viabilidad |
| `ADR002-D` | **las dos** señales tardías, cada una en su etapa, con el orden congelado antes de implementarlo |

El **doble discriminante** de `ADR002-D` está demostrado por ejecución sobre un
fixture con dos objetivos separados: `A` no alcanza ninguno, `B` alcanza sólo el
vectorial, `C` alcanza sólo el relacional, y `D` alcanza **los dos** —el
relacional en `E3`, el vectorial en `E4`—. Las tres ablaciones cierran el
argumento: sin la señal relacional `D ≡ B`, sin la vectorial `D ≡ C`, sin
ninguna `D ≡ A`; y ninguna ablación mueve de etapa a la señal que queda.

Que las señales de `D` sean **las mismas** que las de `B` y `C` no se afirma: se
fija elemento a elemento, porque los árboles de `adr002_b` y `adr002_c` están
congelados y `adr002_d` tuvo que reescribir los cuerpos.

---

## 10. Estado de la verificación

| Comprobación | Resultado |
|---|---|
| `ruff format --check` | 408 ficheros ya formateados |
| `ruff check` | sin hallazgos |
| `mypy` estricto (`src`, `tests`) | sin incidencias en 248 ficheros |
| `mypy -p experiments.adr002.round` | sin incidencias en 5 ficheros |
| Suite experimental completa | **1 816 pruebas, todas en verde** |
| Suite del repositorio | **1 469 pruebas, todas en verde** |
| Verificador de fichas | 17 fichas adjudicadas, **0 fallos** |
| `run_round --check` | **1 precondición pendiente: la autorización** |

De las 1 816, **1 791 son de `ADR-002`** y 25 de `ADR-001`. Reparto del subárbol
de `ADR-002`: candidatos 478, tolerancias 581, benchmark 285, fichas 147,
almacenamiento 111, rederivación 92, proyección 48 y **ronda 49**.

---

## 11. Lo que este cierre **no** hace

- **No mide.** `run_round` no ejecuta la ronda ni cuando las precondiciones se
  satisfagan: ejecutar es otro acto, no un efecto de comprobar.
- **No crea** `artifacts/adr002_round/`. La salida está prevista, no escrita.
- **No autoriza.** La autorización se pide en el §12 y se materializa, si llega,
  en un acta aparte.
- **No reduce** la ronda ni adelanta ningún resultado. No hay ganador
  preferido, y este documento no insinúa ninguno.
- **No toca** Sirius 0.1 productivo.

---

## 12. Solicitud única

Todo lo que la ronda primaria necesita está en su sitio y comprobado. Falta un
solo acto, y es de gobierno, no técnico:

> **¿Se autoriza ejecutar la ronda primaria de ADR-002** —`T0-control`,
> `ADR002-A` v5, `ADR002-B` v7, `ADR002-C` v2 y `ADR002-D` v2, sin reducción—
> **bajo el plan congelado en `experiments/adr002/round/round_protocol.py`:
> once sesiones exactas, cien repeticiones, warm-up de diez descartado íntegro,
> semilla `20260726`, reloj `time.perf_counter_ns` y orden intercalado y
> rotado?**

Autorizarla significa materializar
`SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md`, que es lo único que
`run_round --check` echa hoy en falta.

**Hasta que esa acta exista, no se ejecuta ninguna medición oficial.**

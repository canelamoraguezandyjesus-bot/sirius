# SIRIUS 0.2 — ADR-002 · Acto de gobierno · Banda dependiente de la magnitud en TOL-107

**Versión:** 1.0
**Estado:** **APROBADO · MODIFICA LA FILA `ADR002-TOL-107`**
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado previo:** `940cb9cc14435f178c5fb93684e2eefbafe568f7`
**Alcance:** exclusivamente la **forma de la banda absoluta** y la **definición del umbral** de `ADR002-TOL-107`

## 0. Objeto

Este acto no aprueba ninguna puerta. Modifica una regla del Registro de
tolerancias: `ADR002-TOL-107` deja de evaluar el régimen absoluto contra una
**banda global única** y pasa a evaluarlo contra una **banda `B(M)`
dependiente de la magnitud**.

`ADR002-TOL-209` sigue **NO SATISFECHA**. `ADR002-TOL-107` conserva su estado
`PROPUESTA` para objetivos y umbral, y `REGLA_CONFIRMADA_VALOR_ENTORNO` para
el límite duro.

## 1. Por qué se modifica la regla

La fila v0.4 exigía congelar «una banda absoluta» —en singular— cuyo
fundamento fuese «el suelo de medición medido del entorno». Dos paquetes de
medición ejecutados con ese mandato mostraron que una banda global no puede
cumplir las dos cosas a la vez:

| Paquete | Método | `U` | `B` | Consecuencia |
| --- | --- | ---: | ---: | --- |
| 05 (`suelo_medicion_v0.1.json`) | `D` medida en una sola escala; `U = B / 0,20` | 48,79 µs | 9,76 µs | banda **inalcanzable** a escala sub-milisegundo; contradice la propia fila TOL-107, que sitúa 0,14–1,0 ms en régimen absoluto |
| 06 (`suelo_medicion_v0.2.json`) | `D(s)` en trece escalas; punto fijo `5 D(U) ≤ U`; `B = U / 5` | 100 ms | 20 ms | banda **casi no vinculante** a escala sub-milisegundo: 20 ms de tolerancia para una operación de 0,2 ms |

La causa es estructural y quedó demostrada por la evidencia del paquete 06:
el suelo del entorno **crece con la magnitud medida** —su razón `D(s)/s`
decrece pero su valor absoluto sube tres órdenes de magnitud entre 10 µs y
100 ms—. Una banda global sólo puede ser correcta en un punto de esa curva:
o es la del extremo bajo, y entonces es imposible arriba, o es la del extremo
alto, y entonces es vacía abajo.

El paquete 06 lo declaró en su §5.3 y trasladó la decisión, sin resolverla
por su cuenta, porque cambiar la forma de la banda es un acto de gobierno.

## 2. Decisión aprobada

### 2.1 Banda dependiente de la magnitud

La banda absoluta de `ADR002-TOL-107` pasa a ser una **función** de la
magnitud evaluada, derivada de la curva de suelo medida sobre una escalera
nominal preinscrita `s_1 < … < s_n`:

```
D(s_i)  = peor (máx − mín) entre sesiones equivalentes en la escala s_i
E(s_i)  = máx( D(s_1), …, D(s_i) )              envolvente monótona
B(M)    = E(s_j)   con   j = mín{ i : s_i ≥ M } escalón superior
```

### 2.2 Por qué la envolvente y no la curva

La curva `D(s)` medida **no es monótona**: el paquete 06 publicó, por
ejemplo, `D(100 µs) = 56 498 ns` y `D(200 µs) = 46 720 ns`. Usarla
directamente daría a una operación de 200 µs una banda **más estrecha** que a
una de 100 µs, es decir penalizaría al candidato más rápido por serlo: sería
reabrir el riesgo **M-03** que los dos regímenes cerraron.

La envolvente `E` es no decreciente por construcción, y con ella `B` tampoco
decrece nunca. Esa propiedad es **vinculante** y debe verificarse en cada
corrida.

### 2.3 Dirección conservadora entre escalones

Para una magnitud que cae entre dos escalones se toma el valor del **escalón
superior**. Es la dirección conservadora: el escalón inferior daría una banda
más estrecha que el suelo demostrado en el tramo.

### 2.4 El umbral como cruce exacto

`U` es el punto donde la banda iguala al objetivo relativo:

```
B(M) = 0,20 · M     ⟺     M = 5 · E(s_j)
```

Sobre el escalón `k` seleccionado, `U := 5 · E(s_k)`. De ahí:

```
m · B(U) = E(s_k) = U / 5 = 0,20 · U      con m = 1
```

La continuidad en `M = U` es **exacta y derivada**, no postulada. `m = 1`
deja de ser una elección: es la única solución de igualar los dos regímenes
en la frontera.

**`U` no queda restringido a un escalón de la escalera.** No se asume
igualdad con ningún escalón medido: `U` es el valor exacto del cruce, una
consecuencia aritmética de una dispersión observada. Esto es distinto de la
interpolación de percentiles que el §4.1 del protocolo prohíbe: allí se
prohíbe inventar una observación que nunca ocurrió; aquí se resuelve una
ecuación entre dos funciones preinscritas cuyos parámetros son todos
observados.

### 2.5 Selección del escalón

`k` es el **menor** índice tal que `5 · E(s_k) ≤ s_k` **y** la misma
condición se cumple en todos los escalones superiores. La cláusula de
monotonía impide adoptar un cruce accidental de un escalón aislado.

Se demuestra —y se comprueba en ejecución— que entonces
`s_(k−1) < U ≤ s_k`, de modo que `B(U) = E(s_k)` y la continuidad es exacta.

### 2.6 Régimen relativo

**Sin cambios.** Por encima de `U`, la variación se evalúa en relativo contra
el objetivo congelado de **≤ 20 %** en P50 y P95.

### 2.7 Condiciones de `NO_EVALUABLE`

El suelo se declara `NO_EVALUABLE`, sin publicar `U` ni banda alguna, si:

1. ningún escalón sostiene la condición de forma sostenida;
2. el cruce cae en el tramo del **último escalón medido**, donde ninguna
   escala posterior puede confirmarlo;
3. no queda al menos **una** escala medida por encima de `U` que confirme el
   régimen relativo.

### 2.8 Requisitos de la medición que sustenta la banda

| Requisito | Valor |
| --- | --- |
| Escalera nominal | ampliada hasta incluir **200 ms, 500 ms y 1 s** |
| Sesiones independientes | **once** |
| Sondas | neutrales; ninguna operación de candidato como patrón normativo |
| Percentiles | rango más cercano, jamás interpolados |

La ampliación de la escalera responde al defecto declarado en el §5.1 del
paquete 06: su `U` cayó en el último escalón, donde la cláusula de monotonía
no impone nada. Las once sesiones —frente al mínimo de cinco del §3.3 del
protocolo— responden a que ahora la **curva entera** es normativa, no un solo
punto de ella, de modo que cada escalón ruidoso sería una tolerancia ruidosa.

## 3. Lo que este acto NO cambia

- el **objetivo relativo del 20 %** en P50 y P95 por encima de `U`;
- el objetivo de **orden y conjunto: 0 variación, sin margen**;
- el **límite duro**, que sigue siendo `REGLA_CONFIRMADA_VALOR_ENTORNO`;
- la regla de salida del bucle: repetición única y `NO EVALUABLE` en
  rendimiento si vuelve a fallar;
- el método de percentiles, el mínimo de sesiones del protocolo ni ninguna
  otra fila del Registro;
- la **evidencia** de los paquetes 05 y 06, que se conserva íntegra y se cita
  por su blob exacto.

## 4. Lo que este acto NO autoriza

- **No aprueba `ADR002-TOL-209`**, que sigue NO SATISFECHA;
- no fija el **límite duro** de TOL-107;
- no avanza a **T0**, no implementa ni ejecuta **candidatos**, no ejecuta el
  **benchmark**;
- no fusiona el **PR #117**;
- no convierte en normativo ningún valor concreto de `U` ni de `B(M)`: los que
  produzca la medición del paquete 07 serán **propuestos** hasta el acta que
  los apruebe.

## 5. Materialización

| Artefacto | Efecto |
| --- | --- |
| `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`, fila `ADR002-TOL-107` | filas de régimen absoluto, umbral y punto de congelación **actualizadas a v0.5**, con nota de corrección |
| `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1.md` | preinscripción del método y de la medición que lo sustenta |
| `experiments/adr002/tolerances/envelope_protocol.py` | fórmulas vinculantes, con las demostraciones comprobadas en ejecución |
| `experiments/adr002/tolerances/run_envelope.py` | orquestador; no mide sin `--execute` |
| `experiments/adr002/tolerances/schema_envelope_v0_1.py` | contrato del artefacto; recomputa todo desde los vectores |
| `experiments/adr002/tolerances/test_adr002_envelope.py` | pruebas de las propiedades y del recorrido completo |

Los documentos anteriores conservan sus nombres y etiquetas históricas. Este
acto prevalece sobre la redacción v0.4 de las tres filas que enumera, sin
reescribir los artefactos ya auditados.

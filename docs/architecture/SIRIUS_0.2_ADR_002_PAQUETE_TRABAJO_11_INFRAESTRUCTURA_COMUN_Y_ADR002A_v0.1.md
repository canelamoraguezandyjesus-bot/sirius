# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 11 · infraestructura común neutral y candidato `ADR002-A`

**Versión:** 0.1
**Estado:** **PROPUESTO · PREINSCRITO** — fija el diseño **antes** de implementar; no ejecuta el benchmark ni mide rendimiento
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `c1385b180045c3efc3d8345be6128cceaad1e987` — acta de aprobación de `ADR002-TOL-208`
**Autoridad normativa:** `ARQ-00 v1.0`, `B04 v1.0`, `PDP v1.0`, Resolución de la partición de candidatos v1.0, actas de `TOL-207`, `TOL-208`, `TOL-209` y `TOL-210` con su acto sucesor 01
**No autoriza:** ejecutar el benchmark, medir rendimiento del candidato, usar el corpus congelado v0.4 para evaluarlo, implementar `ADR002-B/C/D`, abrir `EJE-1` o `EJE-2`, elegir ganador, modificar Sirius 0.1 ni fusionar el PR #117.

---

## 1. Qué se construye, y por qué en este orden

Las cinco puertas de arranque están satisfechas. Lo que queda antes de poder
medir a nadie es **lo que se mide**: una infraestructura común neutral y el
primer candidato completo.

El orden no es caprichoso. La infraestructura común se diseña **antes** que
cualquier candidato porque, si se escribiera después del primero, heredaría su
forma: cada decisión tomada «para que A funcione» sería una ventaja
estructural de A sobre B, C y D que ninguna medición posterior podría
detectar. **La neutralidad no se audita al final: se construye al principio o
no existe.**

## 2. La separación, que es la garantía

| Capa | Qué contiene | Qué NO puede contener |
|---|---|---|
| **Común** (`candidates/common/`) | contrato de petición y resultado, puerto de acceso, motor escalonado `E0–E5`, puertas `G1–G12`, paradas `S1–S7`, validación semántica, trazas, instrumentación | **ninguna** señal concreta de recuperación, ninguna mención de `ADR002-A/B/C/D`, ningún embedding, vector, índice relacional derivado ni coordinación simultánea |
| **Candidato** (`candidates/adr002_a/`) | las **señales** de cada etapa y su declaración de señal tardía | reimplementar el motor, saltarse una puerta, alterar el orden de etapas o tocar la capa común |

La común define **cuándo** se llama a cada etapa, **qué puertas** se aplican y
**cómo** se registra; el candidato define **con qué señales** responde a cada
etapa. Un candidato no puede saltarse una etapa ni adelantar un espacio,
porque no controla el bucle: lo controla el motor común.

### 2.1 Neutralidad, hecha comprobable

Cuatro comprobaciones **fail-closed**, no promesas:

1. **La capa común no nombra a ningún candidato.** Ni identificadores, ni
   ramas condicionales por identidad, ni constantes con su nombre.
2. **La capa común no contiene señal vectorial ni índice relacional
   derivado**: ni dependencias de cálculo numérico, ni vocabulario de
   embeddings o similitud vectorial.
3. **El motor trata a todos los candidatos por el mismo camino de código**: no
   existe una vía de ejecución que solo un candidato pueda tomar.
4. **Un candidato de prueba mínimo, ajeno a `ADR002-A`, recorre el motor
   entero**: si el motor solo funcionara con las señales de A, esta
   comprobación fallaría.

## 3. El contrato común

### 3.1 Puerto de acceso

Equivalente a `KnowledgeSearchRepository` (obligatorio por `B04-RF-31` y la
puerta 6 de ADR-002): una interfaz estrecha sobre el canon de Sirius 0.1 y su
FTS5 medido. **La capa común no abre SQLite directamente**: pasa siempre por
el puerto, de modo que sustituir el sustrato no obligue a tocar el motor —que
es precisamente lo que `RF-31` exige.

### 3.2 Petición y contexto autorizado

Conforme a `B04-RF-01` y `B04-Q02`: `operation_id`, consulta, propósito, modo
`M1–M5`, ámbito, tiempo objetivo, estados elegibles, criticidad, espacios
autorizados, cardinalidad `EXACTA/ACOTADA/EXHAUSTIVA`, límite objetivo, límite
duro y nivel de traza. Un campo puede quedar desconocido **solo si no cambia
elegibilidad, privacidad ni significado**.

### 3.3 Expansión estrictamente escalonada `E0–E5`

Las seis etapas normativas de `B04 §15.1`, en orden y **sin saltos**
(`B04-RF-14`): `E0` preparación segura · `E1` estructurada exacta · `E2`
léxica y alias controlados · `E3` semántica y relacional · `E4` fuentes e
historial autorizado · `E5` adjudicación y salida.

**Condición de insuficiencia explícita entre etapas** (`B04-RF-16`,
`B04-Q10`): se avanza a la etapa siguiente **solo** si la anterior fue
insuficiente —por cardinalidad no satisfecha o por críticos pendientes— **y**
el siguiente espacio está autorizado por el modo. Cada transición registra su
causa; una transición sin causa registrada es un fallo.

### 3.4 Puertas `G1–G12`, no compensables

Las doce puertas de `B04 §11`, con su **orden no compensable**: `G1–G10`
antes de generar o exponer candidatos; `G11` antes de agrupar y ordenar; `G12`
antes del límite y el handoff. **Ninguna señal blanda rescata un fallo de
puerta**: el motor descarta, no pondera.

### 3.5 Paradas `S1–S7`

Las siete de `B04 §15.3`, con la regla de cardinalidad: **`S1` está
deshabilitada en `EXHAUSTIVA`**. Toda ejecución termina con exactamente una
parada adjudicada y registrada.

### 3.6 Validación semántica

Ámbito, sujeto, polaridad, condición y tiempo (`B04-RF-17`, `RF-19`, `G11`).
Una discrepancia material no se fusiona: se conserva como conflicto y puede
adjudicar `S6`.

### 3.7 Explicación y traza

- **`RF-28`**: explicación **por resultado** —coincidencia, ámbito, tiempo,
  estado, procedencia, criticidad y razón de orden—.
- **`RF-29`**: plan reproducible con puertas, etapas, expansiones,
  agrupaciones y criterio de parada.

**Trazas minimizadas**: la traza registra **identificadores, clases y
decisiones**, nunca el contenido protegido. Es la aplicación de `B04-Q18`
(«siempre con no revelación») y evita que el instrumento de auditoría se
convierta en un canal lateral.

### 3.8 Instrumentación, determinismo y aislamiento

Instrumentación **por etapa**, separada del resultado y sin coste de reloj
dentro de la ruta medida cuando no se solicita. Comportamiento **determinista**
con semilla fija: misma entrada, misma salida y mismo orden. **Cero red y cero
datos reales.** Todo derivado es **borrable y regenerable desde el canon**.

## 4. `ADR002-A`: qué es, y qué no

**Definición canónica que asume** (`ARQ-00 §23`):

> expansión escalonada solo léxica/estructurada en todas las etapas `E0–E5`.

**No es `T0`.** T0 es Sirius 0.1 tal cual, no implementa `E0–E5`, no tiene
puertas ni paradas e incumple `RF-06`, `RF-14` y `RF-19`. `ADR002-A` es una
**realización correcta del contrato B04** con señales léxicas y estructuradas,
que debe cumplir esos tres requisitos como cualquier otro candidato.

**No es una variante degradada.** Ejecuta `E3` íntegra: busca paráfrasis,
dependencias, apoyo/refutación y relaciones **por medios léxico-estructurados**
—variantes morfológicas, alias confirmados, claves normalizadas, relaciones
explícitas del canon— y valida sujeto, polaridad, condición y tiempo. Que no
declare señal tardía adicional **no es un déficit**: es la hipótesis que el
benchmark pone a prueba, y `B04-RF-31` prohíbe convertir `RF-17` en una
obligación de realización.

`senal_tardia.habilitada = ninguna_adicional`.

## 5. Lo que este paquete NO hace

1. **No ejecuta el benchmark** ni mide rendimiento de nadie.
2. **No usa el corpus congelado v0.4 para evaluar a `ADR002-A`.** Las pruebas
   técnicas posteriores a la ficha usan **fixtures propios y pequeños**,
   ajenos al corpus oficial, y no producen resultados utilizables como
   benchmark.
3. **No implementa `ADR002-B`, `ADR002-C` ni `ADR002-D`.**
4. **No abre `EJE-1` ni `EJE-2`**: en la primera ronda todos comparten el
   sustrato léxico FTS5 medido.
5. **No elige ganador** ni modifica Sirius 0.1 ni fusiona el PR #117.

## 6. Orden de ejecución preinscrito

| Commit | Contenido | Restricción |
|---|---|---|
| **1** | este paquete y su acta | nada implementado todavía |
| **2** | infraestructura común + prototipo `ADR002-A` | **sin ejecutar el candidato**: solo formato, tipos e inspección estructural |
| **3** | ficha `ADR002-A` v1 **congelada** | posterior al prototipo, y **sin ejecutarlo** |
| **4** | pruebas funcionales con fixtures propios | solo **después** de que exista el commit de entrada de la ficha |

**La ficha vigente debe ser ancestro estricto de toda ejecución funcional del
candidato.** Si una prueba obligara a modificar una fuente incluida en la
huella del candidato, se conserva la ficha v1, se corrige el prototipo en un
commit nuevo, se emite ficha v2 con motivo de sustitución y se congela antes
de volver a ejecutar.

---

**Siguiente movimiento único:** confirmar este paquete y su acta, y solo
entonces implementar la infraestructura común y `ADR002-A`.

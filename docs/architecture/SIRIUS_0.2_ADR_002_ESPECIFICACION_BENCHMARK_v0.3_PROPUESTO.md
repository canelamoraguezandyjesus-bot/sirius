# SIRIUS 0.2 — ADR-002 · Especificación del benchmark mínimo

**Versión:** 0.3
**Estado:** PROPUESTO · diseño, **no ejecutado**
**Fecha:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md`, que **se conserva sin modificar**
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03A_RESOLUCION_PARTICION_CANDIDATOS_v0.1.md` §4.4
**Autoridad de la corrección:** `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` y `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
**No autoriza:** ejecutar el benchmark, ejecutar T0, implementar prototipos, elegir alternativa, corregir o congelar el corpus, aprobar `ADR002-TOL-207`, sustituir B04-CA-01–50 ni el PDP.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa canónica · **[?]** hipótesis o incertidumbre.

---

## 0. Qué corrige esta versión, y qué deliberadamente no

**[N]** La v0.3 es una **corrección documental dirigida**: aplica la Resolución de la partición de candidatos v1.0 APROBADA. Su alcance es **el universo de candidatos y nada más**.

| Corrección | v0.2 | **v0.3** |
|---|---|---|
| Objeto de la comparación (§1) | «las realizaciones técnicas **T1–T4**» | «los candidatos **`ADR002-A/B/C/D`**», con `T0` como control |
| Lo que no elige (§11) | «No elige entre **T1, T2, T3 y T4**» | «No elige entre `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D`» |
| Ejes de `T1–T4` | Universo principal | **Ejes contingentes** `EJE-1` y `EJE-2`, abiertos solo por evidencia (§13, nueva) |
| Neutralidad entre realizaciones (§3 principio 3) | Enunciada | **Reforzada**: un caso que solo una alternativa pueda pasar por construcción está mal diseñado, y eso incluye presuponer una señal vectorial |

### 0.1 Lo que esta versión NO corrige

**[N]** Se declara expresamente para que no pueda leerse de más. La auditoría adversarial independiente dejó abiertos varios defectos del corpus ejecutable y de esta especificación. **Ninguno se corrige aquí**, conforme al paquete 03A §4.5:

1. La traza `RED↔CA↔M↔F` del corpus frente al **Anexo B del Plan de Pruebas**.
2. El alcance de la etiqueta `congelada_por` de las referencias de nivel 1, que hoy no distingue lo canónico de lo derivado por instanciación.
3. La ausencia de todo caso en **modo `M4`**, y la rama `M4` de los resultados esperados de `CA-09`, `CA-10`, `CA-24` y `CA-49`.
4. Los casos canónicos multirrama —`CA-36`, `CA-47`, `CA-48`— aplanados en una sola referencia.
5. La **ficha obligatoria del caso frente al PDP §7**: faltan `tolerancias`, `unidad de trabajo`, `objetivo` y `señales observables`, y la **condición de insuficiencia por transición** del campo 12 de la §5.
6. La ausencia de casos **PDP-CA** en el nivel 1, que la §2 declara parte de ese nivel.
7. El denominador con el que se declara la cobertura de familias PDP.
8. La clasificación de ejecutabilidad frente a `T0`, que **no está medida** porque `T0` no se ha ejecutado.
9. La escala del corpus frente a la escala que produjo las cifras del Registro (`ADR002-TOL-208`).

**Todos siguen abiertos.** Corregirlos es el trabajo de un paquete posterior, previo a cualquier planteamiento de `ADR002-TOL-208`.

### 0.2 Actualización de hecho, no corrección de corpus

**[H]** La v0.2 §2 y §12 declaraban que «el texto de CA-01–50 **no está en el repositorio**». **Eso ya no es cierto**: `SRC-ADR002-01` quedó satisfecha el 26 de julio de 2026 con la materialización verificada de las tres fuentes canónicas en `docs/architecture/canonical_sources/`.

Se hace constar como **actualización de hecho**. **No implica** que la instanciación del nivel 1 sea correcta ni que pueda congelarse: los defectos del §0.1 siguen abiertos.

---

## 1. Objeto

Diseñar el corpus sintético y las consultas pareadas con los que ADR-002 comparará después los candidatos **`ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D`**, con **`T0`** como control de falsación, **fijando las referencias antes de observar ningún resultado**.

**[N]** El método de cierre de ADR-002 exige «materializar corpus, referencias y métricas **antes** de observar resultados». Esta especificación existe para que nadie pueda ajustar la referencia a lo que un prototipo produjo.

**[N]** En esta ronda **no se ejecuta nada**, **no se implementa nada**, **no se corrige el corpus** y **no se elige ninguna alternativa**.

---

## 2. Los tres niveles de caso

**[N]** Sin cambios respecto de la v0.2. Todo caso pertenece a exactamente uno de estos tres niveles, y el nivel determina quién manda sobre su referencia.

### Nivel 1 — Casos canónicos reutilizados

**[N]** Casos **B04-CA-01–50** y casos PDP ya aprobados. Su enunciado, su referencia y su veredicto son **canónicos y congelados**. El benchmark de ADR-002 los **ejecuta**, no los reescribe.

**[N]** Prohibido: crear una referencia nueva para un caso canónico, reinterpretar su resultado esperado o sustituirlo por una versión «arquitectónica».

**[H]** Actualización de hecho respecto de la v0.2: el texto de `CA-01–50` **sí está** ahora en el repositorio (§0.2). **[?]** La instanciación existente es `v0.1 PROPUESTO`, no está congelada y arrastra los defectos abiertos del §0.1.

### Nivel 2 — Casos arquitectónicos nuevos

**[N]** Casos que B04/PDP **no** cubren porque son propios de la elección técnica: comportamiento del índice, del borrado y regeneración de derivados, de la portabilidad del puerto, y de la estabilidad de orden entre realizaciones.

**[N]** Un caso solo pertenece a este nivel si puede justificarse que **ningún** caso canónico lo cubre. Ante la duda, es nivel 1.

### Nivel 3 — Ablaciones técnicas

**[N]** No son casos de conformidad sino instrumentos de medida: aíslan la aportación de cada señal y de cada etapa. Nunca producen un veredicto de conformidad por sí solas.

**[N]** Adición de la v0.3: las ablaciones son además el **instrumento de contención combinatoria**. La aportación marginal de una señal se mide con `AB-3` y `AB-4`, no multiplicando candidatos (§13).

---

## 3. Principios de construcción

**[N]**

1. **Sintético y versionado.** Ningún dato real de usuario, ningún secreto, ninguna llamada de red. Corpus, casos y referencias se versionan juntos; una referencia de nivel 2 solo cambia con versión explícita y justificada. Una referencia de nivel 1 **no cambia nunca desde que se congela**.
2. **Referencia previa.** Cada caso fija su resultado esperado antes de ejecutar.
3. **Neutral entre candidatos.** Un caso que solo un candidato puede pasar **por construcción** es un caso mal diseñado. **[N]** Precisión de la v0.3: esto incluye presuponer una señal tardía concreta. Un caso que solo pueda superarse con una representación vectorial, o solo con un índice relacional derivado, no mide el contrato: mide una tecnología, y `B04-RF-31` lo prohíbe.
4. **Reproducible.** Misma versión ⇒ mismo veredicto. Sin aleatoriedad no sembrada, sin dependencia de reloj.
5. **Adversarial donde importa.** Ámbito, expansión, negación, tiempo y ausencia se prueban buscando el fallo.
6. **Ejecutable contra la línea base congelada cuando sea expresable.** **[N]** Los casos no expresables **se marcan como incapacidad de la línea base y no se eliminan**.
7. **Medición por etapa.** Como RF-14 prohíbe el salto a recuperación amplia, la conformidad no puede evaluarse sobre el conjunto final de resultados. Debe evaluarse **etapa por etapa** de E0–E5, verificando además que la transición de etapa obedeció a insuficiencia y no a una decisión libre.

**[N]** Principio 8, nuevo en la v0.3: **igualdad de trato entre las cuatro alternativas mínimas.** El corpus, los casos y las referencias **no citan ninguna alternativa**: trazan a `RF`, `CA`, `M`, `RED` y familias PDP. Un caso no puede penalizar a `ADR002-A` por no tener señal vectorial ni a `ADR002-C` por no tenerla tampoco. **La distancia al contrato la mide el resultado, no la arquitectura declarada.**

---

## 4. Estructura del corpus

**[N]** Sin cambios respecto de la v0.2. Versionable, legible y diferenciable:

```
<raíz del benchmark>/
  corpus/
    entidades.<fmt>        # entidades con ID estable, homónimos y alias (RF-05)
    proyectos.<fmt>        # varios proyectos + ámbito global (RF-06)
    contenido.<fmt>        # afirmaciones con las siete dimensiones canónicas
    relaciones.<fmt>       # apoyo, refutación, conflicto, corrección, sustitución
  casos/
    nivel1_canonicos/      # instanciación de B04-CA y PDP-CA
    nivel2_arquitectonicos/
    nivel3_ablaciones/
  referencias/
  VERSION
```

**[?]** Formato y rutas concretas deliberadamente sin fijar: elegirlos es implementación, que esta ronda no autoriza. Lo que sí se fija es la separación en tres artefactos versionados juntos y la segregación por nivel.

### 4.1 Dimensiones que el corpus debe poder expresar

**[N]** Las siete dimensiones canónicas de ADR-001, cada una por separado y sin condensarlas: confirmación, validez, disponibilidad, sensibilidad, temporalidad, ámbito y autoridad.

**[N]** Además, exigido por RF concretos: procedencia múltiple y diferencias materiales (RF-20), postura y polaridad (RF-17, RF-19), conflicto con lados marcables (RF-21), tiempo objetivo y corte de registro separados (RF-07, RF-08), marcas de no guardado / purgado / no consolidable (RF-10, RF-11), estados especiales (RF-12), evidencia externa atribuida (RF-13), clase de evidencia para fuentes e historial (RF-18) y criticidad con nivel, razón, fuente y regla (RF-23).

**[H]** Los spikes de ADR-001 ya demostraron que todo lo anterior es representable por adición sobre el esquema heredado. **[N]** El corpus puede apoyarse en esa viabilidad probada, pero **no** en el código de `experiments/adr001/`, que ADR-001 §5.10 declara evidencia y no diseño.

---

## 5. Ficha obligatoria de cada caso

**[N]** Sin cambios respecto de la v0.2. Los diez elementos del §9 del paquete 01, más los tres de la v0.2. Para los de nivel 1, se **toman del caso canónico**, no se redactan de nuevo.

| # | Campo | Contenido |
|---|---|---|
| 1 | Entrada | Texto de consulta y parámetros estructurados |
| 2 | Modo | M1–M5, adjudicado antes de recuperar (RF-03) |
| 3 | Propósito y permiso | Y su resultado ante falta de autorización (RF-02) |
| 4 | Ámbito | Global, proyecto o multi-proyecto cerrado (RF-06) |
| 5 | Tiempo objetivo y corte | Distinguiendo «ahora» como valor predeterminado (RF-07, RF-08) |
| 6 | Candidatos elegibles y **prohibidos** | Listas explícitas de ids |
| 7 | Orden o conjunto esperado | Declarado como orden total, parcial o conjunto |
| 8 | Razón esperada | Coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden (RF-28) |
| 9 | Métrica y puerta | Qué se mide y qué la hace fallar |
| 10 | Evidencia mínima | Qué debe quedar registrado para auditar el veredicto |
| 11 | **Cardinalidad declarada**: `EXACTA`, `ACOTADA` o `EXHAUSTIVA` | RF-25, contrato de suficiencia |
| 12 | **Etapa E0–E5 esperada de resolución** y condición de insuficiencia que autoriza pasar a la siguiente | RF-14, RF-16 |
| 13 | **Parada esperada** S1–S7, cuando aplique | RF-32, contrato de suficiencia |

**[N]** El campo 6 es lo que hace adversarial al benchmark: la lista de **prohibidos** es tan vinculante como la de elegibles. Un resultado prohibido es fallo duro aunque el orden del resto sea perfecto.

**[N]** El campo 13 tiene una regla dura asociada: **una consulta declarada `EXHAUSTIVA` no puede detenerse por S1**. Un caso exhaustivo que pare en S1 es fallo, no degradación aceptable.

**[?]** **[H]** La auditoría dejó abierto que esta ficha no cubre los catorce campos del **PDP §7** —faltan `tolerancias`, `unidad de trabajo`, `objetivo` y `señales observables`— y que el campo 12 no está instanciado en su segunda mitad. **La v0.3 no lo corrige** (§0.1 puntos 5 y 8).

---

## 6. Agrupación arquitectónica C-01 a C-20

**[N]** Sin cambios respecto de la v0.2. Agrupación **para razonar sobre cobertura**, no catálogo de casos. Cada clase traza a RF canónicos y, donde el mapeo RED lo fija, a CA y M concretos.

**[H]** Columna «CA canónicos»: solo se citan los CA que el mapeo canónico fija explícitamente. Donde el paquete no los da, se escribe **pendiente** — **no se inventa ninguno**.

| # | Clase | RF canónicos | Familias PDP | CA canónicos | Nivel | Expresable en línea base **[H]** |
|---|---|---|---|---|---|---|
| C-01 | Coincidencia exacta | RF-15, RF-22 | F01 | pendiente | 1 | **Sí** |
| C-02 | Variante léxica y alias confirmado | RF-16, RF-05 | F01, F10 | pendiente | 1 | Sí, con **fallo** esperado |
| C-03 | Paráfrasis sin solapamiento léxico | RF-16, RF-17 | F01, F10 | pendiente | 1 | Sí, con **fallo** esperado |
| C-04 | **Negación** | **RF-19**, RF-17 | F15 | pendiente | 1 | Sí, **fallo duro** medido |
| C-05 | Condición | RF-19, RF-17 | F15 | pendiente | 1 | Sí, con **fallo** esperado |
| C-06 | Homónimos y alias ambiguos | **RF-05**, RF-16 | F10, F15 | pendiente | 1 | Sí, con **fallo** esperado |
| C-07 | Tiempo objetivo, tiempo válido y corte de registro | **RF-07**, **RF-08** | F02, F03 | **CA-06, CA-07, CA-32, CA-47** (vía RED-028) | 1 | **No expresable**: los ejes no existen |
| C-08 | **Ámbito multi-proyecto cerrado** | **RF-06**, RF-09 | F01 | pendiente | 1 | Sí, **fallo duro** medido |
| C-09 | Estados: archivado, restringido, eliminado, purgado, no guardado, «no usar» | RF-10, RF-11, RF-12 | F01, F10 | pendiente | 1 | **Parcial**: eliminado y archivado sí; el resto no existe |
| C-10 | Apoyo y refutación | RF-19, RF-21 | F15 | pendiente | 1 | **No expresable**: no hay postura |
| C-11 | Conflicto con lados marcados | **RF-21** | F15 | **CA-19, CA-31, CA-38** (vía RED-030) | 1 | **No expresable** como tal |
| C-12 | Duplicados con diferencia material | **RF-20** | F10, F14 | **CA-19, CA-31, CA-38** (vía RED-030) | 1 | Sí, con **fallo** esperado |
| C-13 | Crítico frente a ruido; límite objetivo y duro | **RF-23**, **RF-24** | F10, F14 | **CA-19, CA-31, CA-38** (vía RED-030) | 1 | **Parcial**: no hay criticidad |
| C-14 | Ausencia, no-reportable y fuente inaccesible | **RF-25**, **RF-26**, RF-32 | F11, F23 | **CA-17, CA-36** (vía RED-031); **CA-37, CA-48** (vía RED-032) | 1 | Sí, con **fallo** esperado |
| C-15 | Explicación y plan reproducible | RF-28, **RF-29**, RF-18 | F24 | **CA-40, CA-44** (vía RED-029) | 1 | **Parcial** |
| C-16 | **Petición completa, permiso, modo y aclaración** | **RF-01–RF-04**, RF-30 | F01–F06 | **CA-01, CA-05, CA-08, CA-15** (vía RED-027) | 1 | **No expresable** |
| C-17 | **Expansión escalonada sin salto** | **RF-14**, RF-15, RF-16, RF-09 | F01 | pendiente | 1 | Sí, **fallo duro**: el barrido completo es el salto prohibido |
| C-18 | **Neutralidad y portabilidad observable** | **RF-31** | F22 | **CA-39** (vía RED-033) | 2 | Sí |
| C-19 | **Borrado y regeneración completos de todo índice derivado** | ADR-001 c.2 y c.3; puerta 5 de ADR-002 | — | pendiente | 2 | Sí |
| C-20 | **Estabilidad de orden entre entradas equivalentes** | RF-22, RED-033 | F22 | **CA-39** (vía RED-033) | 2 | Sí |

**[H]** Única actualización de la v0.3 sobre esta tabla: `C-14` deja de decir «RED-032 **pendiente del Plan canónico**» porque el Anexo B del Plan, ya materializado, asigna `RED-032` a **`B04-CA-37` y `B04-CA-48`**. Es una **cita del canon ahora disponible**, no una corrección del corpus. **[?]** Que el corpus ejecutable reproduzca fielmente todas las asignaciones del Anexo B es precisamente uno de los defectos abiertos del §0.1 punto 1.

**[N]** C-16 a C-20 son adiciones de la v0.2. C-16 y C-17 cubren obligaciones canónicas que la v0.1 no agrupaba; C-18 a C-20 son los únicos casos genuinamente **arquitectónicos** (nivel 2).

**[N]** Cobertura RF: los treinta y dos RF están representados. RF-13 se integra en C-09 y C-15 según su clase de evidencia; RF-18 en C-15; RF-27 en C-15 como contrato de entrega a B05.

### 6.1 Casos de fallo duro

**[N]** Sin cambios. Cinco clases no admiten grado. Un solo resultado prohibido descarta al candidato, con independencia de cualquier otra métrica:

| Clase | RF canónico | Regla |
|---|---|---|
| **C-08 · fuga de ámbito** | **RF-06** | Puerta 8 de ADR-002; invariante I-04 |
| **C-09 · contenido excluido que aparece** | RF-10, RF-11, RF-12 | Puerta 2; invariante I-03 |
| **C-04 · confusión entre afirmación y negación** | **RF-19**, RF-17 | Fundir ambas es fallo; recuperarlas **marcadas y distinguidas** es correcto |
| **C-14 · «no existe» falso** | **RF-25**, **RF-26** | Declarar ausencia real cuando el contenido existía pero no era reportable |
| **C-17 · salto a recuperación amplia** | **RF-14** | Resolver en una etapa lo que exige escalonamiento es incumplimiento, aunque el resultado final sea correcto |

**[N]** C-17 merece énfasis: es el único fallo duro que puede darse **con resultados perfectos**. Una realización que devuelva exactamente los candidatos correctos saltándose E0–E5 incumple B04 igual que una que devuelva basura.

**[N]** Precisión de la v0.3: C-17 se aplica también al **orden de etapas tardías declarado por `ADR002-D`**. Resolver en una sola etapa lo que la ficha congeló como dos etapas distintas es salto, y además incumple `B04-D15`.

---

## 7. Suficiencia y criticidad: ya definidas

**[N]** Sin cambios respecto de la v0.2. B04 las tiene definidas y el benchmark debe **verificarlas**, no inventarlas.

**Suficiencia** — depende de cardinalidad (`EXACTA`, `ACOTADA`, `EXHAUSTIVA`), cobertura de críticos elegibles pendientes, etapas autorizadas ya ejecutadas, taxonomía interna de resultado/ausencia y paradas S1–S7. Solo se expande cuando falta suficiencia o quedan críticos y el siguiente espacio está autorizado.

**[N]** Consecuencia: cada caso declara su cardinalidad (campo 11) y su etapa esperada (campo 12), y el veredicto comprueba que **la expansión ocurrió solo cuando el contrato la autorizaba**. Esto es verificable **sin ninguna cifra de tolerancia**.

**Criticidad** — procede de requisito o decisión aprobada, acto explícito, etiqueta de escenario, o regla operativa aprobada con ID y evidencia. Prohibido el auto-marcado libre. Debe transportar nivel, razón, fuente y regla hasta B05.

**[?]** Lo que sigue abierto no es la definición sino el **umbral operativo**, cerrado en `ADR002-TOL-204` como «cero críticos elegibles pendientes», y **no medible** mientras el corpus no esté corregido y congelado.

---

## 8. Ablaciones — nivel 3

**[N]** Sin cambios en su contenido. Estructura mínima para medir por etapa:

| Ablación | Qué se desactiva | Qué aísla |
|---|---|---|
| AB-0 | Nada — línea base congelada de 0.1 | Punto de referencia |
| AB-1 | Todo salvo E0/E1 estructurado y exacto | Aportación de la recuperación exacta sola |
| AB-2 | Etapa léxica de RF-16 desactivada | Aportación de variantes y alias |
| AB-3 | Etapa de significado/relaciones de RF-17 desactivada | Aportación de la señal tardía |
| AB-4 | Validación de polaridad, condición y tiempo de RF-17 desactivada, manteniendo la señal | **Aportación específica de la validación** frente a la señal cruda |
| AB-5 | Puertas G1–G12 desactivadas de una en una | Que ninguna puerta enmascare el efecto de otra |
| AB-6 | Orden aleatorizado con semilla fija | Suelo de comparación |

**[N]** AB-4 es la ablación más informativa del conjunto: separa lo que aporta la señal semántica de lo que aporta la validación que RF-17 exige. Sin ella no puede saberse si un acierto en C-04 o C-05 procede de la señal o del control.

**[N]** AB-6 es indispensable: sin un suelo, una métrica alta no demuestra nada.

**[N]** Precisión de la v0.3 sobre `AB-3`: es la ablación que **falsa o sostiene la hipótesis de `ADR002-A`**. Si desactivar la señal tardía no degrada materialmente ninguna métrica de puerta, `ADR002-A` no es un control degradado: es la respuesta.

**[N]** Aplicabilidad: `AB-3` y `AB-4` **no aplican a `ADR002-A`**, que no tiene señal tardía adicional que desactivar. Se declara «no aplicable por construcción», y esa no aplicabilidad **no penaliza** al candidato.

**[N]** Neutralidad (F22, C-18): cada candidato debe ejecutarse a través de un puerto equivalente al actual `KnowledgeSearchRepository`, de modo que el benchmark mida la **arquitectura** y no la biblioteca. La puerta 6 de ADR-002 descarta lo acoplado a un proveedor concreto.

---

## 9. Métricas

**[N]** Se fija **la forma**. Los umbrales viven en el Registro de Tolerancias v0.4, aprobado el 26 de julio de 2026; esta especificación **no fija ninguno y no aprueba ninguno**.

| Métrica | Forma | Umbral |
|---|---|---|
| Contaminación | Recuento absoluto de resultados prohibidos | **Cero.** Puerta 2. No es tolerancia |
| Fuga de ámbito | Recuento absoluto fuera del ámbito declarado | **Cero.** Puerta 8, RF-06 |
| Confusión de polaridad | Recuento absoluto de fusiones afirmación/negación | **Cero.** RF-19 |
| Conformidad de etapa | Booleano por caso: ¿se resolvió en la etapa esperada, con transición autorizada por insuficiencia? | **Verdadero obligatorio.** RF-14 |
| Borrado y regeneración | Booleano por índice: ¿se destruye y se reconstruye por completo desde el canon? | **Verdadero obligatorio.** Puerta 5 |
| Explicabilidad | Fracción de resultados con los siete elementos de RF-28 registrados | B04-M14 · **[?]** su regla de muestreo sigue sin fuente conocida |
| Recall crítico | Fracción de críticos elegibles cubiertos | B04-M01 y `ADR002-TOL-204`: cero críticos elegibles pendientes |
| Corrección de la ausencia | Fracción de casos clasificados en el tipo correcto de la taxonomía | B04-M09 |
| Estabilidad de orden | Distancia de orden entre entradas equivalentes | **[?]** Forma fijada; la clase de equivalencia de RED-033 **sigue sin congelar** |
| Latencia, coste, tamaño de índice | Medición directa | Registro v0.4, **[?]** con los valores de entorno pendientes de `ADR002-TOL-209` |

**[N]** **Cinco puertas son booleanas** y no dependen de ninguna cifra: contaminación cero, fuga de ámbito cero, confusión de polaridad cero, conformidad de etapa y borrado/regeneración completos.

**[?]** Esto significa que el benchmark puede **descartar** candidatos antes de que las cifras de entorno estén congeladas, pero no puede **elegir** ninguno. Una parte del trabajo de ADR-002 es ejecutable antes; el cierre, no.

**[N]** Precisión de la v0.3: **ninguna métrica premia tener una señal tardía**, y ninguna penaliza no tenerla. Lo que se mide es el resultado frente al contrato B04. Si `ADR002-A` alcanza las mismas métricas de puerta con menos maquinaria, la puerta 7 —«el coste adicional no produce mejora material»— actúa **a su favor**, no en su contra.

---

## 10. Evidencia mínima por ejecución

**[N]** Cada ejecución debe registrar, de forma legible por máquina y auditable:

1. Versión del corpus, de los casos y de las referencias, y **nivel** de cada caso ejecutado.
2. Identificación de la línea base: head de Alembic y versiones de biblioteca.
3. **Candidato y ablación ejecutados**, citando su ficha por `id · versión · huella` (`ADR002-TOL-210`).
4. Por caso: entrada íntegra, resultado obtenido, resultado esperado, veredicto y razón.
5. Por resultado: por qué entró, por qué ocupa esa posición y, para los prohibidos que aparecieron, por qué no fue excluido.
6. **Plan ejecutado**: espacios, puertas aplicadas, etapas recorridas, expansiones, agrupaciones y parada (RF-29).
7. **Suficiencia adjudicada** y cardinalidad declarada, con la razón de la parada.
8. Métricas calculadas, con la puerta aplicada y su procedencia.
9. Casos no expresables en la línea base, marcados como **incapacidad de la línea base** y no eliminados.
10. **[N]** Para `ADR002-D`: la **etapa en que actuó cada señal tardía** y la evidencia de que no hubo coordinación simultánea fuera de la etapa autorizada.
11. Toda desviación respecto de esta especificación.

**[N]** Las trazas deben ser **minimizadas**: identificadores, estados y razones, no contenido innecesario.

---

## 11. Lo que esta especificación no hace

**[N]**

- No ejecuta el benchmark ni implementa corpus, casos, referencias o prototipos.
- **No corrige el corpus.** Los nueve defectos abiertos del §0.1 siguen sin corregir.
- **No sustituye B04-CA-01–50 ni el PDP**, y no crea referencias que los contradigan.
- No reabre B04-B, E0–E5, G1–G12 ni S1–S7.
- **No elige entre `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D`**, ni degrada ninguna a control.
- No propone modelos de embedding, extensiones ni fórmulas de fusión.
- **No declara obligatoria ninguna señal tardía concreta.** Obligatoria es la etapa `E3`.
- No fija ni aprueba umbrales. **No aprueba `ADR002-TOL-207`.**
- **No declara satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`.**
- No abre `EJE-1` ni `EJE-2`.
- No modifica `experiments/`, `artifacts/`, `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva.
- No emite el paquete de contexto: eso es ADR-003B.

---

## 12. Incertidumbres reales restantes

Todas **[?]**.

1. **Valores de entorno del protocolo común.** Umbral de conmutación y banda absoluta de `TOL-107`, suelo de medición, tolerancias de texto/estado/conteo/tiempo de `RF-26` (`RED-032`) y clase de equivalencia de orden (`RED-033`). Sin ellas, `CA-37`, `CA-39` y `CA-48` no son adjudicables. `ADR002-TOL-209`.
2. **Regla de muestreo de `B04-M14`.** No consta en ninguna de las tres fuentes canónicas materializadas. **No se inventa.**
3. **Fidelidad de la instanciación del nivel 1.** Los nueve defectos del §0.1. Corregirlos precede a `ADR002-TOL-208`.
4. **Escala del corpus.** El corpus ejecutable y el corpus que produjo las cifras del Registro no tienen la misma escala. `ADR002-TOL-208` obliga a rederivar; qué significa eso para las magnitudes de rendimiento sigue abierto.
5. **Presupuesto absoluto de almacenamiento.** `ADR002-TOL-207` está propuesta y **no aprobada**.
6. **Casos no expresables en la línea base.** Se marcan como incapacidad de la línea base y **no se eliminan**. Su clasificación **no está medida**: `T0` no se ha ejecutado.
7. **Formato de los artefactos.** Deliberadamente sin fijar.
8. **Dónde actúa la precedencia.** RF-21 obliga a recuperar **y marcar** todos los lados; qué capa aplica la precedencia sigue abierto y afecta a C-11.
9. **Coste de ejecución.** No estimado.

---

## 13. Ejes contingentes — contención combinatoria

**[N]** Nuevo en la v0.3. Aplica la Resolución v1.0 §6.

El universo principal es `ADR002-A/B/C/D`. Los dos ejes de la partición `T1–T4`, superada como universo principal, se conservan como **contingentes**:

| Eje | Contraste | Cuándo se abre |
|---|---|---|
| **`EJE-1` · Sustrato léxico** | FTS5 medido **frente a** sustrato léxico alternativo | Solo si una puerta o un fallo es atribuible al sustrato |
| **`EJE-2` · Materialización de relaciones** | Desde el canon **frente a** índice relacional derivado | Solo si una puerta o un fallo es atribuible a la materialización |

**[N]** Reglas:

1. **Primera ronda:** `T0` (control) + `ADR002-A/B/C/D`, todos sobre el **mismo sustrato léxico FTS5 medido** y la misma infraestructura común. Cinco fichas.
2. **Máximo dos fichas adicionales** por apertura contingente, cada una con la puerta o el fallo que la justifica.
3. **No se ejecuta el producto cartesiano.** La aportación marginal se mide con las ablaciones de la §8, no multiplicando candidatos.
4. Abrir un eje contingente **no retira** ninguna de las cuatro alternativas mínimas ni reabre la Resolución v1.0.
5. **El corpus no cambia al abrir un eje.** Sigue trazando a `RF`, `CA`, `M`, `RED` y familias PDP, y sigue sin citar ninguna alternativa ni ningún eje.

---

**Siguiente movimiento único:** **corregir los defectos del corpus del §0.1** antes de que `ADR002-TOL-208` pueda plantearse. No se emite ninguna ficha de candidato, no se ejecuta `T0`, no se implementa ningún prototipo y no se abre ningún eje contingente.

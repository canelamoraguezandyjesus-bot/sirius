# SIRIUS 0.2 — ADR-002 · Especificación del benchmark mínimo

**Versión:** 0.2
**Estado:** PROPUESTO · diseño, **no ejecutado**
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01B_CORRECCION_CANONICA_v0.1.md`
**No autoriza:** ejecutar el benchmark, implementar prototipos, elegir realización técnica, fijar tolerancias, sustituir B04-CA-01–50 ni el PDP.

---

## 0. Qué corrige esta versión

**[N]** La corrección de fondo: **B04-CA-01–50 y el PDP son canónicos y aprobados**. Los quince tipos C-01–C-15 de la v0.1 **no son un catálogo de casos**: son una **agrupación arquitectónica** para razonar sobre cobertura. No sustituyen a ningún caso canónico y no pueden generar referencias que contradigan las congeladas.

| Corrección | v0.1 | v0.2 |
|---|---|---|
| Naturaleza de C-01–C-15 | Se leían como el catálogo de casos del benchmark | **Agrupación arquitectónica** sobre casos canónicos ya aprobados |
| Relación con B04-CA-01–50 | No mencionada | **Los casos canónicos mandan.** C-xx solo los agrupa y añade lo estrictamente arquitectónico |
| Niveles de caso | Un solo nivel | **Tres niveles**: canónicos reutilizados, arquitectónicos nuevos, ablaciones técnicas |
| Traza de cada clase | A RF reconstruidos | A **RF canónicos** y, donde el mapeo RED lo fija, a **CA y M concretos** |
| «Suficiencia sin definir» como incertidumbre bloqueante | Declarada la más bloqueante de todas | **Retirada**: B04 la tiene definida; ver §7 |
| «Crítico sin definir» | Declarada incertidumbre | **Retirada**: B04 la tiene definida |
| Fuga de ámbito | Trazada a RF-07 | **RF-06** |
| Casos de fallo duro | Cuatro | **Cinco**: se añade el salto a recuperación amplia (RF-14) |

---

## 1. Objeto

Diseñar el corpus sintético y las consultas pareadas con los que ADR-002 comparará después las realizaciones técnicas T1–T4, **fijando las referencias antes de observar ningún resultado**.

**[N]** El método de cierre de ADR-002 exige «materializar corpus, referencias y métricas **antes** de observar resultados». Esta especificación existe para que nadie pueda ajustar la referencia a lo que un prototipo produjo.

**[N]** En esta ronda **no se ejecuta nada**, **no se implementa nada** y **no se elige ninguna realización técnica**.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa canónica · **[?]** hipótesis o incertidumbre.

---

## 2. Los tres niveles de caso

**[N]** Exigencia del §3.3 del paquete 01B. Todo caso del benchmark pertenece a exactamente uno de estos tres niveles, y el nivel determina quién manda sobre su referencia.

### Nivel 1 — Casos canónicos reutilizados

**[N]** Casos **B04-CA-01–50** y casos PDP ya aprobados. Su enunciado, su referencia y su veredicto son **canónicos y congelados**. El benchmark de ADR-002 los **ejecuta**, no los reescribe.

**[N]** Prohibido: crear una referencia nueva para un caso canónico, reinterpretar su resultado esperado o sustituirlo por una versión «arquitectónica».

**[H]** Limitación real: el texto de CA-01–50 **no está en el repositorio**. Solo se conocen los dieciséis CA citados por el mapeo RED canónico. La instanciación del nivel 1 requiere el Plan de Pruebas aprobado y **no puede completarse en esta ronda**.

### Nivel 2 — Casos arquitectónicos nuevos

**[N]** Casos que B04/PDP **no** cubren porque son propios de la elección técnica: comportamiento del índice, del borrado y regeneración de derivados, de la portabilidad del puerto, y de la estabilidad de orden entre realizaciones.

**[N]** Un caso solo pertenece a este nivel si puede justificarse que **ningún** caso canónico lo cubre. Ante la duda, es nivel 1.

### Nivel 3 — Ablaciones técnicas

**[N]** No son casos de conformidad sino instrumentos de medida: aíslan la aportación de cada señal y de cada etapa. Nunca producen un veredicto de conformidad por sí solas.

---

## 3. Principios de construcción

**[N]**

1. **Sintético y versionado.** Ningún dato real de usuario, ningún secreto, ninguna llamada de red. Corpus, casos y referencias se versionan juntos; una referencia de nivel 2 solo cambia con versión explícita y justificada. Una referencia de nivel 1 **no cambia nunca desde aquí**.
2. **Referencia previa.** Cada caso fija su resultado esperado antes de ejecutar.
3. **Neutral entre realizaciones técnicas.** Un caso que solo una realización puede pasar por construcción es un caso mal diseñado.
4. **Reproducible.** Misma versión ⇒ mismo veredicto. Sin aleatoriedad no sembrada, sin dependencia de reloj.
5. **Adversarial donde importa.** Ámbito, expansión, negación, tiempo y ausencia se prueban buscando el fallo.
6. **Ejecutable contra la línea base congelada cuando sea expresable.** **[N]** Los casos no expresables **se marcan como incapacidad de la línea base y no se eliminan** (§3.3 del paquete 01B).

**[N]** Principio 7, nuevo en la v0.2: **medición por etapa.** Como RF-14 prohíbe el salto a recuperación amplia, la conformidad no puede evaluarse sobre el conjunto final de resultados. Debe evaluarse **etapa por etapa** de E0–E5, verificando además que la transición de etapa obedeció a insuficiencia y no a una decisión libre.

---

## 4. Estructura del corpus

**[N]** Versionable, legible y diferenciable:

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

**[N]** Los diez elementos del §9 del paquete 01. Ningún caso está completo sin los diez. Para los de nivel 1, los diez **se toman del caso canónico**, no se redactan de nuevo.

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

**[N]** Campos añadidos en la v0.2, exigidos por el contrato canónico y ausentes en la v0.1:

| # | Campo | Origen |
|---|---|---|
| 11 | **Cardinalidad declarada**: `EXACTA`, `ACOTADA` o `EXHAUSTIVA` | RF-25, contrato de suficiencia |
| 12 | **Etapa E0–E5 esperada de resolución** y condición de insuficiencia que autoriza pasar a la siguiente | RF-14, RF-16 |
| 13 | **Parada esperada** S1–S7, cuando aplique | RF-32, contrato de suficiencia |

**[N]** El campo 6 es lo que hace adversarial al benchmark: la lista de **prohibidos** es tan vinculante como la de elegibles. Un resultado prohibido es fallo duro aunque el orden del resto sea perfecto.

**[N]** El campo 13 tiene una regla dura asociada: **una consulta declarada `EXHAUSTIVA` no puede detenerse por S1**. Un caso exhaustivo que pare en S1 es fallo, no degradación aceptable.

---

## 6. Agrupación arquitectónica C-01 a C-15

**[N]** Agrupación **para razonar sobre cobertura**, no catálogo de casos. Cada clase traza a RF canónicos y, donde el mapeo RED lo fija, a CA y M concretos.

**[H]** Columna «CA canónicos»: solo se citan los CA que el mapeo canónico de la §2.5 del paquete 01B fija explícitamente. Donde el paquete no los da, se escribe **pendiente** — **no se inventa ninguno**.

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
| C-14 | Ausencia, no-reportable y fuente inaccesible | **RF-25**, **RF-26**, RF-32 | F11, F23 | **CA-17, CA-36** (vía RED-031); RED-032 **pendiente del Plan canónico** | 1 | Sí, con **fallo** esperado |
| C-15 | Explicación y plan reproducible | RF-28, **RF-29**, RF-18 | F24 | **CA-40, CA-44** (vía RED-029) | 1 | **Parcial** |
| **C-16** | **Petición completa, permiso, modo y aclaración** | **RF-01–RF-04**, RF-30 | F01–F06 | **CA-01, CA-05, CA-08, CA-15** (vía RED-027) | 1 | **No expresable** |
| **C-17** | **Expansión escalonada sin salto** | **RF-14**, RF-15, RF-16, RF-09 | F01 | pendiente | 1 | Sí, **fallo duro**: el barrido completo es el salto prohibido |
| **C-18** | **Neutralidad y portabilidad observable** | **RF-31** | F22 | **CA-39** (vía RED-033) | 2 | Sí |
| **C-19** | **Borrado y regeneración completos de todo índice derivado** | ADR-001 c.2 y c.3; puerta 5 de ADR-002 | — | pendiente | 2 | Sí |
| **C-20** | **Estabilidad de orden entre entradas equivalentes** | RF-22, RED-033 | F22 | **CA-39** (vía RED-033) | 2 | Sí |

**[N]** C-16 a C-20 son adiciones de la v0.2. C-16 y C-17 cubren obligaciones canónicas que la v0.1 no agrupaba —la petición completa y la prohibición del salto—; C-18 a C-20 son los únicos casos genuinamente **arquitectónicos** (nivel 2), porque miden propiedades de la elección técnica que B04 no puede haber previsto.

**[N]** Cobertura de familias PDP referenciadas por las fuentes canónicas: F01 (C-01, C-02, C-03, C-08, C-16, C-17), F02 y F03 (C-07), F04–F06 (C-16), F10 (C-02, C-03, C-06, C-09, C-12, C-13), F11 (C-14), F14 (C-12, C-13), F15 (C-04, C-05, C-06, C-10, C-11), F22 (C-18, C-20), F23 (C-14), F24 (C-15). **Ninguna familia canónica queda sin agrupación.**

**[N]** Cobertura RF: los treinta y dos RF están representados. RF-13 (evidencia externa) se integra en C-09 y C-15 según su clase de evidencia; RF-18 en C-15; RF-27 en C-15 como contrato de entrega a B05.

### 6.1 Casos de fallo duro

**[N]** Cinco clases no admiten grado. Un solo resultado prohibido descarta la realización técnica, con independencia de cualquier otra métrica:

| Clase | RF canónico | Regla |
|---|---|---|
| **C-08 · fuga de ámbito** | **RF-06** | Puerta 8 de ADR-002; invariante I-04 |
| **C-09 · contenido excluido que aparece** | RF-10, RF-11, RF-12 | Puerta 2; invariante I-03 |
| **C-04 · confusión entre afirmación y negación** | **RF-19**, RF-17 | Fundir ambas es fallo; recuperarlas **marcadas y distinguidas** es correcto |
| **C-14 · «no existe» falso** | **RF-25**, **RF-26** | Declarar ausencia real cuando el contenido existía pero no era reportable |
| **C-17 · salto a recuperación amplia** | **RF-14** | Nuevo en la v0.2. Resolver en una etapa lo que exige escalonamiento es incumplimiento, aunque el resultado final sea correcto |

**[N]** C-17 merece énfasis: es el único fallo duro que puede darse **con resultados perfectos**. Una realización que devuelva exactamente los candidatos correctos saltándose E0–E5 incumple B04 igual que una que devuelva basura.

---

## 7. Suficiencia y criticidad: ya definidas

**[N]** La v0.1 declaró ambas como incertidumbres bloqueantes. **Era falso.** B04 las tiene definidas y el benchmark debe **verificarlas**, no inventarlas.

**Suficiencia** — depende de cardinalidad (`EXACTA`, `ACOTADA`, `EXHAUSTIVA`), cobertura de críticos elegibles pendientes, etapas autorizadas ya ejecutadas, taxonomía interna de resultado/ausencia y paradas S1–S7. Solo se expande cuando falta suficiencia o quedan críticos y el siguiente espacio está autorizado.

**[N]** Consecuencia para el benchmark: cada caso declara su cardinalidad (campo 11) y su etapa esperada (campo 12), y el veredicto comprueba que **la expansión ocurrió solo cuando el contrato la autorizaba**. Esto es verificable **sin ninguna cifra de tolerancia**.

**Criticidad** — procede de requisito o decisión aprobada, acto explícito, etiqueta de escenario, o regla operativa aprobada con ID y evidencia. Prohibido el auto-marcado libre. Debe transportar nivel, razón, fuente y regla hasta B05.

**[N]** Consecuencia: los casos de C-13 fijan la criticidad **por su origen trazable**, no por intuición, y el veredicto comprueba que los cuatro atributos llegan intactos.

**[?]** Lo que sigue abierto no es la definición sino el **umbral operativo**: qué fracción de críticos elegibles pendientes satisface la suficiencia. Eso es tolerancia delegada, y va al paquete siguiente.

---

## 8. Ablaciones — nivel 3

**[N]** Estructura mínima, corregida para medir por etapa:

| Ablación | Qué se desactiva | Qué aísla |
|---|---|---|
| AB-0 | Nada — línea base congelada de 0.1 | Punto de referencia |
| AB-1 | Todo salvo E0/E1 estructurado y exacto | Aportación de la recuperación exacta sola |
| AB-2 | Etapa léxica de RF-16 desactivada | Aportación de variantes y alias |
| AB-3 | Etapa de significado/relaciones de RF-17 desactivada | Aportación de la señal tardía |
| AB-4 | Validación de polaridad, condición y tiempo de RF-17 desactivada, manteniendo la señal | **Aportación específica de la validación** frente a la señal cruda |
| AB-5 | Puertas G1–G12 desactivadas de una en una | Que ninguna puerta enmascare el efecto de otra |
| AB-6 | Orden aleatorizado con semilla fija | Suelo de comparación |

**[N]** AB-4 es nuevo en la v0.2 y es la ablación más informativa del conjunto: separa lo que aporta la señal semántica de lo que aporta la validación que RF-17 exige. Sin ella no puede saberse si un acierto en C-04 o C-05 procede de la señal o del control.

**[N]** AB-6 es indispensable: sin un suelo, una métrica alta no demuestra nada.

**[N]** Neutralidad (F22, C-18): cada realización técnica debe ejecutarse a través de un puerto equivalente al actual `KnowledgeSearchRepository`, de modo que el benchmark mida la **arquitectura** y no la biblioteca. La puerta 6 de ADR-002 descarta lo acoplado a un proveedor concreto.

---

## 9. Métricas

**[N]** Se fija **la forma**. **No se fija ningún umbral**: el Registro de Tolerancias no existe y el paquete 01B **prohíbe crearlo aquí**.

| Métrica | Forma | Umbral |
|---|---|---|
| Contaminación | Recuento absoluto de resultados prohibidos | **Cero.** Puerta 2. No es tolerancia |
| Fuga de ámbito | Recuento absoluto fuera del ámbito declarado | **Cero.** Puerta 8, RF-06 |
| Confusión de polaridad | Recuento absoluto de fusiones afirmación/negación | **Cero.** RF-19 |
| Conformidad de etapa | Booleano por caso: ¿se resolvió en la etapa esperada, con transición autorizada por insuficiencia? | **Verdadero obligatorio.** RF-14 |
| Borrado y regeneración | Booleano por índice: ¿se destruye y se reconstruye por completo desde el canon? | **Verdadero obligatorio.** Puerta 5 |
| Explicabilidad | Fracción de resultados con los siete elementos de RF-28 registrados | Pendiente |
| Recall crítico | Fracción de críticos elegibles cubiertos | **Pendiente del Registro de Tolerancias.** La definición de «crítico» **ya no es incertidumbre** |
| Corrección de la ausencia | Fracción de casos clasificados en el tipo correcto de la taxonomía | Pendiente |
| Estabilidad de orden | Distancia de orden entre entradas equivalentes | Pendiente en cifra; la **forma** sí está fijada: entradas equivalentes ⇒ orden idéntico. RED-033 |
| Latencia, coste, tamaño de índice | Medición directa | Pendiente en su totalidad |

**[N]** **Cinco puertas son booleanas** y no dependen del Registro de Tolerancias: contaminación cero, fuga de ámbito cero, confusión de polaridad cero, conformidad de etapa y borrado/regeneración completos. La v0.1 identificaba cuatro; la quinta —conformidad de etapa— aparece al incorporar RF-14.

**[?]** Esto significa que el benchmark puede **descartar** realizaciones técnicas antes de que existan las tolerancias, pero no puede **elegir** ninguna. Una parte del trabajo de ADR-002 es ejecutable ya; el cierre, no.

---

## 10. Evidencia mínima por ejecución

**[N]** Cada ejecución debe registrar, de forma legible por máquina y auditable:

1. Versión del corpus, de los casos y de las referencias, y **nivel** de cada caso ejecutado.
2. Identificación de la línea base: head de Alembic y versiones de biblioteca.
3. Realización técnica y ablación ejecutadas.
4. Por caso: entrada íntegra, resultado obtenido, resultado esperado, veredicto y razón.
5. Por resultado: por qué entró, por qué ocupa esa posición y, para los prohibidos que aparecieron, por qué no fue excluido.
6. **Plan ejecutado**: espacios, puertas aplicadas, etapas recorridas, expansiones, agrupaciones y parada (RF-29).
7. **Suficiencia adjudicada** y cardinalidad declarada, con la razón de la parada.
8. Métricas calculadas, con la puerta aplicada y su procedencia.
9. Casos no expresables en la línea base, marcados como **incapacidad de la línea base** y no eliminados.
10. Toda desviación respecto de esta especificación.

**[N]** Las trazas deben ser **minimizadas**: identificadores, estados y razones, no contenido innecesario. Es corpus sintético, pero la disciplina de traza forma parte de lo que se evalúa (RF-29).

---

## 11. Lo que esta especificación no hace

**[N]**

- No ejecuta el benchmark ni implementa corpus, casos, referencias o prototipos.
- **No sustituye B04-CA-01–50 ni el PDP**, y no crea referencias que los contradigan.
- No reabre B04-B, E0–E5, G1–G12 ni S1–S7.
- No elige entre T1, T2, T3 y T4.
- No propone modelos de embedding, extensiones ni fórmulas de fusión.
- No fija umbrales ni crea el Registro de Tolerancias.
- No modifica `src/`, `tests/`, `migrations/` ni configuración productiva.
- No emite el paquete de contexto: eso es ADR-003B.

---

## 12. Incertidumbres reales restantes

Todas **[?]**. Se han retirado las dos falsas de la v0.1.

1. **Registro de Tolerancias.** No existe. Sin él, cinco puertas son evaluables y el resto no. **[N]** Su creación corresponde al paquete siguiente, no a esta corrección.
2. **Tolerancias congeladas frente a delegadas.** RF-26 habla de tolerancias de texto, estado, conteo y tiempo, y RED-032/RED-033 las presuponen: parte puede estar ya fijada en B04/PDP. Separarlas es tarea del paquete siguiente.
3. **Instanciación del nivel 1.** **[H]** El texto de B04-CA-01–50 no está en el repositorio; solo se conocen dieciséis CA por el mapeo RED, y los de RED-032 se difieren al Plan canónico. **El nivel 1 no puede instanciarse hasta disponer del Plan de Pruebas aprobado.** Las columnas «pendiente» de la §6 son eso: pendientes, no huecos que puedan rellenarse por analogía.
4. **Umbral operativo de cobertura de críticos.** Tolerancia, no definición.
5. **Tamaño del corpus.** Sin tolerancias no hay criterio para dimensionarlo; debe bastar para que el ruido de C-13 sea real, pero eso es cualitativo.
6. **Casos no expresables en la línea base.** Cinco clases lo son total o parcialmente. **[N]** Se marcan como incapacidad de la línea base y **no se eliminan**. Comparar contra un 0.1 extendido exigiría autorización expresa, porque dejaría de ser la línea base congelada.
7. **Formato de los artefactos.** Deliberadamente sin fijar.
8. **Dónde actúa la precedencia.** RF-21 obliga a recuperar **y marcar** todos los lados; qué capa aplica la precedencia sigue abierto y afecta a C-11.
9. **Coste de ejecución.** No estimado.

---

**Siguiente movimiento único:** que el usuario revise los cuatro documentos de la corrección 01B y decida si se abre el paquete específico del Registro de Tolerancias, del que depende la instanciación completa del benchmark.

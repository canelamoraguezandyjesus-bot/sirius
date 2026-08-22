# SIRIUS 0.2 — ADR-002 · Especificación del benchmark mínimo

**Versión:** 0.1
**Estado:** PROPUESTO · diseño, **no ejecutado**
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01_INVENTARIO_Y_BASELINE_v0.1.md`
**No autoriza:** ejecutar el benchmark, implementar prototipos, elegir alternativa, fijar tolerancias ni modificar Sirius 0.1.

---

## 1. Objeto

Diseñar el corpus sintético y las consultas pareadas con los que ADR-002 comparará después las alternativas A, B, C y D, **fijando las referencias antes de observar ningún resultado**.

**[N]** El método de cierre de ADR-002 exige explícitamente «materializar corpus, referencias y métricas **antes** de observar resultados». Esta especificación existe para que nadie pueda ajustar la referencia a lo que un prototipo produjo.

**[N]** En esta ronda **no se ejecuta nada** y **no se elige ninguna alternativa**.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa · **[?]** hipótesis o incertidumbre.

---

## 2. Principios de construcción

**[N]**

1. **Sintético y versionado.** Ningún dato real de usuario, ningún secreto, ninguna llamada de red. El corpus se versiona junto a los casos, y una referencia solo puede cambiar con un cambio de versión explícito y justificado.
2. **Referencia previa.** Cada caso fija su resultado esperado antes de ejecutar.
3. **Neutral entre alternativas.** Ningún caso puede estar redactado de forma que solo una técnica lo satisfaga. Un caso que solo una alternativa puede pasar por construcción es un caso mal diseñado.
4. **Reproducible.** Misma versión de corpus y de casos ⇒ mismo veredicto. Sin aleatoriedad no sembrada, sin dependencia de reloj.
5. **Adversarial donde importa.** Ámbito, negación, tiempo y ausencia se prueban buscando el fallo, no confirmando el acierto.
6. **Ejecutable contra la línea base congelada.** Todo caso debe poder correr contra Sirius 0.1 tal cual, aunque falle. Un caso que la línea base no puede ni siquiera ejecutar debe declararlo.

**[?]** El principio 6 tiene una consecuencia incómoda que conviene aceptar de antemano: buena parte de los casos **fallarán** contra la línea base, y algunos ni siquiera podrán expresarse (los de tiempo válido, por ejemplo, porque el eje no existe). Eso es información útil —mide la distancia entre 0.1 y las obligaciones de 0.2— y no un defecto del benchmark.

---

## 3. Estructura del corpus

**[N]** Versionable, legible y diferenciable. Estructura propuesta:

```
<raíz del benchmark>/
  corpus/
    entidades.<fmt>        # entidades con id estable, incluidos homónimos y alias
    proyectos.<fmt>        # varios proyectos + ámbito global
    contenido.<fmt>        # afirmaciones con estado, tiempo, ámbito, autoridad, postura
    relaciones.<fmt>       # apoyo, refutación, conflicto, corrección, sustitución
  casos/
    F01_*.<fmt> ... F24_*.<fmt>
  referencias/
    <caso>.esperado.<fmt>
  VERSION
```

**[?]** Formato y rutas concretas deliberadamente sin fijar: elegirlos es diseño de implementación, y esta ronda no lo autoriza. Lo que sí se fija es que corpus, casos y referencias son **tres artefactos separados y versionados juntos**.

**[N]** El corpus debe poder construirse **exclusivamente** sobre el esquema que ADR-001 aprobó como línea de evolución, sin fijar DDL productivo. Mientras ese esquema no exista, los casos que dependan de dimensiones inexistentes en 0.1 se declaran `NO EJECUTABLE EN LÍNEA BASE`, no se descartan.

### 3.1 Dimensiones que el corpus debe poder expresar

**[N]** Las siete dimensiones canónicas de ADR-001, cada una por separado y sin condensarlas: confirmación, validez, disponibilidad, sensibilidad, temporalidad, ámbito y autoridad.

**[N]** Además: procedencia múltiple, postura (apoyo/refutación), corrección retroactiva, tiempo válido y tiempo de registro separados, y marcas de no uso.

**[H]** Los spikes de ADR-001 ya demostraron que todo lo anterior es representable por adición sobre el esquema heredado. El corpus del benchmark puede apoyarse en esa viabilidad ya probada, pero **no** en el código experimental de `experiments/adr001/`, que ADR-001 §5.10 declara evidencia y no diseño.

---

## 4. Ficha obligatoria de cada caso

**[N]** El §9 del paquete exige fijar diez elementos **antes** de ejecutar. Ningún caso está completo sin los diez:

| # | Campo | Contenido |
|---|---|---|
| 1 | **Entrada** | Texto de consulta y parámetros estructurados |
| 2 | **Modo** | M1–M5 |
| 3 | **Propósito y permiso** | Para qué se busca y con qué autorización |
| 4 | **Ámbito** | Global, proyecto concreto o multi-proyecto cerrado |
| 5 | **Tiempo objetivo y corte** | Instante de validez consultado y corte de registro |
| 6 | **Candidatos elegibles y prohibidos** | Listas **explícitas** de ids: lo que debe aparecer y lo que **nunca** puede aparecer |
| 7 | **Orden o conjunto esperado** | Orden total, orden parcial o conjunto sin orden, declarado como tal |
| 8 | **Razón esperada** | Por qué entra, por qué queda fuera y por qué ocupa esa posición |
| 9 | **Métrica y puerta** | Qué se mide y qué la hace fallar |
| 10 | **Evidencia mínima** | Qué debe quedar registrado para poder auditar el veredicto |

**[N]** El campo 6 es el que convierte el benchmark en adversarial: la lista de **prohibidos** es tan vinculante como la de elegibles. Un resultado prohibido es fallo duro, aunque el orden del resto sea perfecto.

**[?]** El campo 7 debe declarar honestamente su exigencia. Imponer un orden total donde el contrato solo exige un conjunto produciría fallos espurios; aceptar un conjunto donde el contrato exige orden ocultaría regresiones. La elección se justifica caso por caso.

---

## 5. Catálogo de casos exigidos

**[N]** Las quince clases del §9 del paquete. Cada una se mapea a su familia PDP y a los RF que verifica.

| # | Clase de caso | Familia PDP | RF verificados | Ejecutable contra la línea base **[H]** |
|---|---|---|---|---|
| C-01 | Coincidencia exacta | F01 | RF-15, RF-22 | **Sí** |
| C-02 | Variante léxica y alias confirmado | F01, F10 | RF-16, RF-06 | Sí, y se espera **fallo**: no hay lematización ni alias |
| C-03 | Paráfrasis sin solapamiento léxico suficiente | F01, F10 | RF-17 | Sí, y se espera **fallo**: es el caso que separa A de B |
| C-04 | Negación | F15 | RF-19 | Sí, y se espera **fallo duro**: medido, la negación es invisible |
| C-05 | Condición | F15 | RF-19 | Sí, y se espera **fallo** |
| C-06 | Homónimos y alias ambiguos | F10, F15 | RF-05, RF-06 | Sí, y se espera **fallo**: no hay resolución de entidad |
| C-07 | Tiempo válido frente a corte de conocimiento | F02, F03 | RF-08, RF-18 | **No ejecutable en línea base**: los ejes no existen |
| C-08 | Varios proyectos con ámbito cerrado | F01 | RF-07 | Sí, y se espera **fallo duro**: fuga medida |
| C-09 | Archivado, restringido, eliminado, purgado y «no usar» | F01, F10 | RF-10, RF-11, RF-12 | **Parcial**: eliminado y archivado sí; restringido y «no usar» no existen |
| C-10 | Apoyo y refutación | F15 | RF-19, RF-21 | **No ejecutable**: no hay postura en 0.1 |
| C-11 | Conflicto con ambos lados elegibles | F15 | RF-21 | **No ejecutable** como tal; medible el comportamiento de la precedencia actual |
| C-12 | Duplicados con diferencia material | F10 | RF-20 | Sí, y se espera **fallo**: no hay deduplicación |
| C-13 | Resultado crítico frente a ruido abundante | F01 | RF-23, RF-24 | **Parcial**: no hay criticidad; medible el efecto del recorte |
| C-14 | Ausencia real, no-reportable y fuente inaccesible | F23 | RF-25, RF-26, RF-32 | Sí, y se espera **fallo**: los tres casos son indistinguibles hoy |
| C-15 | Explicación y traza del plan | F24 | RF-27, RF-28, RF-29 | **Parcial**: hay criterios inspeccionables, no hay plan |

**[N]** Cobertura de las familias PDP mínimas exigidas: F01 (C-01, C-02, C-03, C-08, C-09, C-13), F02 (C-07), F03 (C-07), F10 (C-02, C-03, C-06, C-09, C-12), F15 (C-04, C-05, C-06, C-10, C-11), F22 (§6), F23 (C-14), F24 (C-15). **Ninguna familia queda sin al menos un caso.**

### 5.1 Casos de fallo duro

**[N]** Estas cuatro clases no admiten grado. Un solo resultado prohibido descarta la alternativa, con independencia de cualquier otra métrica:

- **C-08 · fuga de ámbito.** Puerta 8 de ADR-002 e invariante I-04.
- **C-09 · aparición de contenido eliminado, purgado, restringido o marcado «no usar».** Puerta 2 e invariante I-03.
- **C-04 · confusión entre una afirmación y su negación** cuando el caso las declara como candidatos distintos. RF-19.
- **C-14 · «no existe» falso**, es decir, declarar ausencia real cuando el contenido existía pero no era reportable. RED-031 y RF-26.

**[?]** C-04 admite matiz: recuperar ambos lados y **distinguirlos** puede ser correcto; recuperarlos y **fundirlos** no lo es nunca. La ficha de cada caso de negación debe decir cuál de las dos cosas exige.

---

## 6. Ablaciones y neutralidad

**[N]** ADR-002 §5 exige ablaciones por señal y por etapa. Estructura mínima:

| Ablación | Qué se desactiva | Qué pretende aislar |
|---|---|---|
| AB-0 | Nada — línea base congelada de 0.1 | Punto de referencia |
| AB-1 | Solo señal léxica y estructurada | Alternativa A pura |
| AB-2 | Señal adicional desactivada por etapa | Aportación real de cada etapa tardía |
| AB-3 | Puertas desactivadas una a una | Que ninguna puerta esté enmascarando el efecto de otra |
| AB-4 | Orden aleatorizado con semilla fija | Suelo de comparación: cuánto del resultado es mérito del orden |

**[N]** AB-4 es indispensable. Sin un suelo, una métrica alta no demuestra nada.

**[N]** Familia F22, neutralidad y portabilidad observable: cada alternativa debe ejecutarse a través de un puerto equivalente al actual `KnowledgeSearchRepository`, de modo que el benchmark mida la **arquitectura** y no la biblioteca. La puerta 6 de ADR-002 descarta cualquier alternativa acoplada a un proveedor concreto.

---

## 7. Métricas

**[N]** Se fija **la forma** de cada métrica. **No se fija ningún umbral**: el Registro de Tolerancias no está en el repositorio y **inventar cifras está expresamente prohibido**.

| Métrica | Forma | Umbral |
|---|---|---|
| Recall crítico | Fracción de candidatos elegibles marcados como críticos que aparecen | **Pendiente del Registro de Tolerancias.** Además, «crítico» depende de RF-23, que aún no existe en ningún modelo |
| Contaminación | Recuento absoluto de resultados prohibidos | **Cero.** No es tolerancia: es la puerta 2 de ADR-002 |
| Fuga de ámbito | Recuento absoluto de resultados fuera del ámbito declarado | **Cero.** Puerta 8 |
| Explicabilidad | Fracción de resultados con razón de entrada, de orden y de exclusión registrada | Pendiente |
| Estabilidad de orden | Distancia de orden entre ejecuciones con entradas equivalentes | Pendiente. La **forma** exigida sí está fijada: entradas equivalentes ⇒ orden idéntico |
| Corrección de la ausencia | Fracción de casos de ausencia clasificados en el tipo correcto | Pendiente |
| Latencia, coste, tamaño de índice | Medición directa | Pendiente en su totalidad |
| Borrado y regeneración | Booleano por índice: ¿se destruye y se reconstruye por completo? | **Verdadero obligatorio.** Puerta 5 |

**[N]** Cuatro puertas son booleanas y **no** dependen del Registro de Tolerancias: contaminación cero, fuga de ámbito cero, borrado y regeneración completos, y explicación reproducible presente. Estas cuatro pueden evaluarse en cuanto exista el benchmark; las demás quedan bloqueadas hasta que el Registro exista.

**[?]** Esto significa que el benchmark puede **descartar** alternativas antes de que existan las tolerancias, pero no puede **elegir** ninguna. Conviene tenerlo presente al planificar: una parte del trabajo de ADR-002 es ejecutable ya; el cierre, no.

---

## 8. Evidencia mínima por ejecución

**[N]** Cada ejecución debe registrar, de forma legible por máquina y auditable:

1. Versión del corpus, de los casos y de las referencias.
2. Identificación de la línea base: head de Alembic y versiones de biblioteca.
3. Alternativa y ablación ejecutadas.
4. Por caso: entrada íntegra, resultado obtenido, resultado esperado, veredicto y razón.
5. Por resultado: por qué entró, por qué ocupa esa posición y, para los prohibidos que aparecieron, por qué no fue excluido.
6. Métricas calculadas, con la puerta aplicada y su procedencia.
7. Casos no ejecutables y el motivo.
8. Toda desviación respecto de esta especificación.

**[N]** Las trazas deben ser **minimizadas**: registran identificadores, estados y razones, no contenido innecesario. Es corpus sintético, pero la disciplina de traza forma parte de lo que se evalúa.

---

## 9. Lo que esta especificación no hace

**[N]**

- No ejecuta el benchmark.
- No implementa corpus, casos, referencias ni prototipos.
- No elige entre A, B, C y D.
- No propone embeddings, vectores, grafos, extensiones ni fórmulas de fusión.
- No fija umbrales, cifras de latencia, coste ni tamaño.
- No modifica `src/`, `tests/`, `migrations/` ni configuración productiva.
- No emite el paquete de contexto: eso es ADR-003B.

---

## 10. Incertidumbres pendientes

Todas **[?]**.

1. **Sin Registro de Tolerancias, el benchmark no puede cerrar ADR-002.** Puede descartar alternativas por las cuatro puertas booleanas; no puede elegir una.
2. **La puerta de suficiencia no está definida.** B, C y D se definen por incorporar señal adicional «solo después de fallar la puerta de suficiencia». Sin esa definición, **las tres son indistinguibles de A en cualquier ejecución**. Es la dependencia más bloqueante de todas y conviene resolverla antes que ninguna otra.
3. **«Crítico» no está definido.** El recall crítico es la puerta 1 de ADR-002, pero depende de una criticidad que ningún modelo tiene todavía.
4. **Tamaño del corpus.** No se fija: sin tolerancias no hay criterio para dimensionarlo. Debe ser suficiente para que el ruido de C-13 sea real, pero eso es cualitativo.
5. **Casos no ejecutables en la línea base.** Siete de las quince clases no son total o parcialmente ejecutables contra 0.1. Hay que decidir si la comparación se hace contra 0.1 tal cual o contra un 0.1 mínimamente extendido — y esa segunda opción exigiría autorización expresa, porque ya no sería la línea base congelada.
6. **Formato de los artefactos.** Deliberadamente sin fijar; elegirlo es implementación.
7. **Precedencia frente a conflicto.** Los casos C-10 y C-11 dependen de en qué capa actúe la precedencia, cuestión abierta en el inventario normativo.
8. **Coste de ejecución.** No estimado.

---

**Siguiente movimiento único:** que el usuario revise los tres documentos del trabajo 01 y decida si se da por cerrado, antes de construir corpus alguno o ejecutar la línea base.

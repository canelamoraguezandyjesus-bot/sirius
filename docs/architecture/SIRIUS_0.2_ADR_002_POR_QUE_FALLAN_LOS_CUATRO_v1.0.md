# SIRIUS 0.2 — ADR-002 · Por qué fallan los cuatro, y qué se hace con eso

**Versión:** 1.0
**Estado:** **CAUSA RAÍZ IDENTIFICADA Y MEDIDA · una vía de arreglo probada y descartada**
**Fecha:** 8 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, con permiso expreso: «*mira lo que tiene que hacer
Sirius… tú debes saber lo que es mejor, lo que es mejor impléntalo*».

**Sucede a:** `SIRIUS_0.2_ADR_002_CIERRE_v1.0.md`, que **no se modifica**. Aquel
documento dice *qué* falla; este dice *por qué*, y corrige sus cifras con la
medición posterior al arreglo del recorte de términos.

---

## 1. En lenguaje llano: qué le pasa a Sirius

Sirius guarda cosas tuyas y luego tiene que encontrarlas cuando preguntas. El
problema es **cómo las encuentra**: busca las **palabras** de tu pregunta dentro
del texto de lo que guardó. Nada más. No entiende que dos formas distintas de
decir lo mismo son lo mismo.

Y eso se rompe en cuanto tú y Sirius usáis palabras distintas. Tres ejemplos
reales, tal cual están guardados:

| Tú preguntas | Lo que Sirius tiene guardado | Palabras en común |
|---|---|---|
| «evidencia de **límite de gasto**» | «El **presupuesto máximo** del proyecto es 1.500 €» | **ninguna** |
| «¿qué **restricciones de transporte** tengo?» | «En este **viaje** no se alquila **coche**» | **ninguna** |
| «dame todas las **restricciones esenciales**» | «No uses opciones de **vuelo** con **escala**» | **ninguna** |

Las tres son exactamente lo que buscabas. Las tres son de las importantes. Y las
tres son **invisibles** para Sirius, porque no comparten ni una palabra con tu
pregunta. No es que las ordene mal ni que las deje para el final: **no las
encuentra**.

Eso es todo el problema. Y explica lo que llevaba semanas sin explicación: **los
cuatro candidatos de ADR-002 fallan exactamente igual**, en los mismos casos y
en las mismas cinco preguntas, porque los cuatro son la misma cosa por debajo —
buscadores de palabras—. Incluso el que se presentaba como «semántico»: su
índice se construye contando qué palabras aparecen juntas **en esos mismos
textos**, así que si «límite» y «presupuesto» no aparecen nunca juntas en
ningún sitio, sigue sin saber que significan lo mismo.

**Elegir entre los cuatro no arregla esto.** Los cuatro tienen el mismo techo.

### Lo que probé, y por qué no vale

Se me ocurrió lo obvio: si algo está marcado como importante en un proyecto,
que Sirius te lo saque siempre que preguntes por ese proyecto. Lo implementé,
lo medí, y **está mal por dos motivos**, los dos comprobados con números:

1. **Se convierte en un pesado.** El proyecto principal tiene cinco cosas
   marcadas como importantes. Con esa regla, esas cinco te salen en **35 de las
   50** preguntas, vengan a cuento o no. Las respuestas exactas caen de 27 a 12.
2. **El propio banco de pruebas dice que no.** Hay un caso —«*¿qué decisión de
   presupuesto usábamos antes?*»— donde el límite de gasto está marcado
   **explícitamente como resultado prohibido**: preguntas por el de antes, y
   sacarte el de ahora es una respuesta equivocada. Es decir: que algo sea
   importante **no** significa que toque en toda pregunta.

Así que la regla se revirtió. Queda escrita aquí y en el código para que nadie
la vuelva a intentar sin saber que ya se midió.

### Qué hay que hacer de verdad

Sirius necesita entender **significado**, no solo letras. Eso es una pieza que
hoy no existe en ninguno de los cuatro candidatos, y es la conclusión útil de
ADR-002: no «cuál de los cuatro», sino «**a los cuatro les falta lo mismo**».

---

## 2. Lo que este trabajo sí dejó arreglado

| | qué era | estado |
|---|---|---|
| Cuatro pruebas rojas en `HEAD` | el arreglo del recorte de términos cambió dos ficheros pero no reancló los **árboles** que fijan tres pruebas hermanas | **arreglado**, las 1.939 pruebas en verde |
| `RF-24` sin comprobar | `G12` declaraba el desbordamiento, pero nadie comprobaba la aritmética: un crítico podía caerse por el límite **sin** aparecer entre los declarados | **arreglado**, con prueba negativa que rompe `G12` a propósito |
| Cota del puerto sin declarar | `por_identificadores` aplicaba un máximo de 16 sin publicarlo, de modo que quien tenía que lotear no sabía por cuánto | **declarada** en el contrato, con prueba sobre el puerto real |

El primero es un fallo mío y consta como tal: ese commit salió con cuatro
pruebas rojas porque se empujó sin ejecutar la puerta completa. El mecanismo de
anclaje **funcionó** —detectó el cambio—; lo que falló fue no mirarlo.

---

## 3. Las cifras, corregidas

El cierre v1.0 se midió con la ronda v0.4, **antes** del arreglo del recorte de
términos. Estas son las cifras sobre los mismos 47 casos adjudicables, después:

| | exactos v0.4 | exactos ahora | omisiones v0.4 | omisiones ahora |
|---|---|---|---|---|
| `ADR002-A` | 23/47 | **24/47** | 16 | **11** |
| `ADR002-B` | 21/47 | **22/47** | 16 | **11** |
| `ADR002-C` | 23/47 | **24/47** | 16 | **11** |
| `ADR002-D` | 21/47 | **22/47** | 16 | **11** |
| `T0-control` | 1/47 | 1/47 | 21 | 21 |

El arreglo cerró **cinco** de las dieciséis omisiones y ganó un caso exacto por
participante. Las once que quedan están **en cinco casos y nada más**, y son
las mismas en los cuatro:

| caso | lo que falta | nivel |
|---|---|---|
| `N1-02` | `MEMORIA:2` | CRÍTICO |
| `N1-30` | `MEMORIA:1` | IMPORTANTE |
| `N1-31` | `DECISION:3`, `DECISION:10`, `MEMORIA:14`, `MEMORIA:16`, `MEMORIA:25` | CRÍTICO ×5 |
| `N1-33` | `DECISION:3` | CRÍTICO |
| `N1-34` | `DECISION:3`, `MEMORIA:14`, `MEMORIA:16` | CRÍTICO ×3 |

**Nota sobre la métrica.** `B04-M01` se llama «recall **crítico**», pero su
denominador —`_criticos_del_canon`— toma todo nivel «distinto de ORDINARIA», de
modo que incluye los `IMPORTANTE`. De las once omisiones, **diez son CRÍTICO y
una es IMPORTANTE** (`MEMORIA:1`, en `N1-30`). No se cambia la métrica —§8.1 lo
prohíbe una vez observados los resultados—; se declara la lectura.

---

## 4. La causa raíz, con los textos delante

Las once omisiones no son un defecto de ordenación ni de límite. Son
**inalcanzables**: las palabras que conectan la pregunta con la respuesta **no
existen en el canon**.

| identidad | texto guardado en el canon | consulta que la pide |
|---|---|---|
| `DECISION:3` | «El presupuesto máximo del proyecto es 1.500 €.» | «*evidencia de límite de gasto*» (`N1-33`) |
| `DECISION:10` | «No usar PostgreSQL en este proyecto.» | «*todas las restricciones esenciales*» (`N1-31`) |
| `MEMORIA:2` | «En este viaje no se alquila coche.» | «*restricciones de transporte*» (`N1-02`) |
| `MEMORIA:14` | «No uses opciones de vuelo con escala.» | «*restricciones esenciales*» (`N1-31`) |
| `MEMORIA:16` | «Acepta escala solo si ahorra más de 200 €.» | «*restricciones esenciales*» (`N1-31`) |
| `MEMORIA:25` | «El acceso al almacén requiere autorización previa del responsable.» | «*restricciones esenciales*» (`N1-31`) |

Ni un solo término compartido en ninguna fila.

### Dónde sí están esas palabras, y por qué no se pueden usar

Están en `criticidad.razon_segura`, que es **anotación del banco**, no canon:

* `DECISION:3` → «**Límite de gasto** vigente; su omisión causa decisión errónea»
* `MEMORIA:2` → «**Restricción esencial** del viaje; omitirla cambia la planificación»
* `MEMORIA:25` → «**Restricción esencial** detectada por regla operativa aprobada»

La coincidencia es exacta y es tentadora. **Y usarla sería trampa.** Quien
escribió «Límite de gasto vigente» es quien escribió el caso «evidencia de
límite de gasto» esperando `DECISION:3`. Emparejar una cosa con la otra no
mediría recuperación: mediría que las dos las redactó la misma mano. El propio
contrato lo anticipa —`CriticidadAplicada` documenta que la fuente bruta «porta
identificadores de caso del banco, y transportarla convertiría el traspaso en
una **filtración del oráculo**»—.

De modo que **indexar la razón queda descartado**, y no por prudencia: por ser
lo mismo que copiar la solución.

### Por qué los cuatro fallan igual

| | señal tardía | qué hace en realidad |
|---|---|---|
| `ADR002-A` | ninguna | busca palabras y variantes morfológicas |
| `ADR002-B` | «vectorial» | coocurrencia PPMI **sobre esos mismos textos**: dos términos se relacionan solo si aparecen en el mismo elemento |
| `ADR002-C` | relacional | claves de sujeto y relaciones ya materializadas |
| `ADR002-D` | las dos | las dos anteriores |

Los cuatro son, por debajo, **buscadores de palabras**. El de `B` parece
semántico y no lo es: si «límite» y «presupuesto» nunca coinciden en un mismo
elemento del corpus —y con cincuenta elementos no coinciden—, no hay dimensión
que las una. `D` hereda lo mismo.

**Ninguna de las cuatro alternativas puede salvar esas cinco preguntas.** No es
un fallo de implementación que otra elección evitaría: es el techo común de las
cuatro.

---

## 5. La vía que se implementó, se midió y se descartó

**Hipótesis:** si `§11 G12` dice «todos los críticos elegibles se preservan…
nunca se ocultan», y «elegible» es *pertinente al ámbito*, entonces el motor
debe **entregar** los críticos del ámbito en vez de esperar a tropezarse con
ellos.

Se implementó entero: enumeración de los críticos del plano reservado,
materialización por identidad en lotes de 16, paso por `G1-G10` como cualquier
otra candidata, después del bucle para que ningún candidato los viera como
semillas.

**Medición sobre los 50 casos:**

| | exactos sin piso | exactos con piso | omisiones sin piso | omisiones con piso |
|---|---|---|---|---|
| `ADR002-A` | 27/50 | **12/50** | 11 | **1** |
| `ADR002-B` | 25/50 | **10/50** | 11 | **1** |
| `ADR002-C` | 27/50 | **12/50** | 11 | **1** |
| `ADR002-D` | 25/50 | **10/50** | 11 | **1** |

Cierra las omisiones. Y destruye la exactitud: los cinco críticos del proyecto 2
—`DECISION:3`, `DECISION:10`, `MEMORIA:14`, `MEMORIA:16`, `MEMORIA:25`— aparecen
en **35 de los 50** casos.

**Lo que la refuta, y no es una opinión:** `B04-CA-05` —«*¿qué decisión de
presupuesto usábamos antes?*»— declara `DECISION:3`, **crítico de su mismo
proyecto y dentro de su ámbito**, entre los `prohibidos` de su caso. El banco,
congelado y preinscrito, dice expresamente que ser crítico del ámbito **no**
obliga a entregarlo en toda pregunta sobre ese ámbito.

Además, la métrica que juzga `B04-M01` no lo cuenta como «elegible del ámbito»:
`criticos_pendientes` exige `identidad in caso.resultado_esperado`. El
denominador operativo, congelado desde antes de medir, es **lo que el banco
espera en ese caso**. Satisfacerlo entregándolo todo no es cumplirlo: es
inundar hasta que el conjunto esperado quede contenido.

**Conclusión:** «pendiente» no es «crítico del ámbito», y con lo que hay en el
plano congelado **no se puede distinguir cuál toca**. La vía queda cerrada, con
sus cifras, para que no se reabra por intuición.

### Lo que sí quedó de ese trabajo

El `§15.2` sigue **sin** conectarse —`evaluar_suficiencia` recibe `pendientes`
vacío— y eso ahora está **escrito en el punto donde se decide**, con el motivo y
la medición que lo respalda, en vez de ser una omisión silenciosa. La guarda
sigue viva en sus propias pruebas.

Y lo que sí se garantiza por construcción es más estrecho pero es cierto:
**ningún crítico recuperado desaparece sin declararse** (`RF-24`), comprobado
antes de entregar y con prueba negativa.

---

## 6. Sobre la contaminación: una sospecha mía, y su corrección

Al medir vi 3 contaminaciones donde el cierre publica «✅ cero», y sospeché un
verde falso en el documento que cierra `ADR-002`. **Lo comprobé y me equivocaba.**

Las tres están declaradas y razonadas en la readjudicación contra el canon:

* `B04-CA-04` se retiró de los adjudicables —«los dos `DISTRACTOR_RUIDO` están
  en ámbito y no hay eje canónico por el que excluirlos sin leer el oráculo»—,
  y con él sus dos contaminaciones;
* de `B04-CA-05` se retiró `DECISION:3` como prohibido, con cita literal de
  `B04 M2`.

El artefacto publica **las dos lecturas** y el cierre usa la readjudicada
diciéndolo. La lectura medida sigue siendo 3 y sigue estando en la evidencia.
No hay defecto: hay dos lecturas y las dos constan.

---

## 6 bis. Una prueba inestable que conviene saber que está ahí

`experiments/adr002/storage/test_storage_gate.py::test_contabilidad_de_operacion_con_checkpoints`
**falla de vez en cuando**, y no por este trabajo: es anterior y está en otra
vertical —contabilidad de almacenamiento, no recuperación—.

* Aislada: **3 de 3 en verde**. Su directorio entero: **111 en verde**.
* En la corrida completa de 1.939: ha fallado en **dos** de tres ejecuciones.
* Lo que falla: `resultado["validez"]["resultado"]` devuelve `NO_EVALUABLE`
  donde la prueba espera `VALIDO`.

**El instrumento está bien y la prueba es la optimista.** El muestreador se
niega a publicar una cifra que no pudo medir —falla cerrado, que es lo correcto—
y con 1.939 pruebas compitiendo por la CPU su hilo se queda sin turnos dentro de
las ventanas de 50 ms. La prueba da por supuesta una máquina tranquila.

**No se toca aquí**, y a propósito: arreglarla es o ensanchar la ventana o
aceptar `NO_EVALUABLE`, y las dos cosas aflojan una puerta ajena a esta vertical
que existe para detectar regresiones de memoria reales. Aflojarla de madrugada,
sin que nadie lo haya pedido, es la clase de cambio que después enmascara un
defecto. Queda señalada para que se decida a la luz del día.

---

## 7. Recomendación

**No cerrar `ADR-002` eligiendo.** El cierre v1.0 ya lo decía; ahora se sabe
*por qué* y el motivo es más fuerte que entonces: no es que los cuatro tengan
un defecto común corregible, es que **los cuatro son la misma clase de
buscador** y las cinco preguntas que fallan exigen algo que ninguno tiene.

Lo que hay que decidir —y es una decisión de producto, no del banco— es **cómo
entiende Sirius que dos formas de decir lo mismo son lo mismo**. Tres caminos,
sin recomendar ninguno todavía porque ninguno está medido:

1. **Modelo de embeddings real**, no coocurrencia local. `ARQ-00 §23` prohíbe
   decidir proveedor «hasta que la evidencia lo justifique»; esta evidencia es
   justamente la que faltaba.
2. **Capa explícita de sinónimos y conceptos** sobre el canon, escrita y
   auditable. Más pobre que un modelo, pero inspeccionable y sin red.
3. **Que Sirius escriba él mismo, al guardar, para qué sirve cada cosa** —no la
   anotación del banco, sino metadato canónico propio— y que eso sí se indexe.
   Es la que más cambia el modelo de datos y la única que no depende de terceros.

Las tres son ADR nuevos. **Ninguno se abre aquí**: la instrucción vigente es no
empezar otro ADR, y este documento se limita a dejar la decisión planteada con
la evidencia que la sostiene.

---

## 8. Qué no se hizo, y por qué

| no hecho | motivo |
|---|---|
| Indexar `criticidad.razon_segura` | es anotación del banco; usarla filtra el oráculo |
| Reescribir el cierre v1.0 | los artefactos congelados son append-only; este documento lo sucede |
| Tocar el banco o `resultado_esperado` | `§8.1` prohíbe cambiar la medición tras observar resultados |
| Repetir la ronda como v0.5 | el código de recuperación **no cambió** en este paquete: los tres arreglos son un invariante, una constante declarada y cuatro anclas. Sin cambio de comportamiento no hay ronda que repetir |
| Abrir un ADR para la pieza semántica | instrucción vigente: no empezar otro ADR |
| Fusionar el PR #117 | instrucción vigente: permanece abierto y sin fusionar |

---

## 9. Trazabilidad

* `cf79c78` — invariante `RF-24`, cota declarada, cuatro anclas reparadas
* `f3aec49` — arreglo del recorte de términos (el que salió con cuatro rojas)
* `a102722` — cierre de `ADR-002`
* Evidencia previa: `artifacts/adr002_round/ronda_primaria_v0.4_evidencia.json`
* Pruebas nuevas: `experiments/adr002/candidates/test_adr002_criticos_no_desaparecen.py`
* Estado de la puerta: **1.939 pruebas en verde**, Ruff y formato limpios

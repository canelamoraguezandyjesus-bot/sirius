# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 12: ADR002-B, señal semántica vectorial tardía

**Versión:** 0.1
**Estado:** PROPUESTO · PREINSCRITO — fija el diseño **antes** de implementar; no ejecuta el benchmark ni mide rendimiento
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `23bf22db80aa609fd18490ed7c76d24a37ebfe36`
**Autoridad normativa:** ARQ-00 §23 · B04 v1.0 (E0–E5, G1–G12, S1–S7, RF-01–32, D15) · Resolución de la partición de candidatos v1.0 · actas de TOL-207/208/209/210 y acto sucesor 01 · acta de preparación de ADR002-A
**Autorización del usuario:** «Venga seguimos»
**No autoriza:** ejecutar el benchmark; usar el corpus congelado v0.4 para evaluar a `ADR002-B`; medir rendimiento; modificar o reaprobar `ADR002-A`; modificar la infraestructura común; implementar `ADR002-C` o `ADR002-D`; abrir `EJE-1` o `EJE-2`; elegir ganador; modificar Sirius 0.1; fusionar el PR #117.

---

## 1. Qué se construye, y por qué por composición

`ADR002-B` es el segundo candidato de la primera ronda. Su definición canónica
—ARQ-00 §23, transcrita sin alterar una palabra—:

> **B:** expansión escalonada léxica/estructurada con señal semántica vectorial
> únicamente en etapas tardías tras fallar la puerta de suficiencia.

Y su definición operativa (Resolución v1.0 §2):

> Base léxica/estructurada y **señal semántica vectorial** únicamente en etapas
> tardías, tras fallar la puerta de suficiencia.

La *base léxica/estructurada* de B **ya existe, está corregida, congelada y
aprobada**: es `ADR002-A` v2. Reimplementarla sería fabricar una segunda base
que nadie auditó; copiarla y alterarla en silencio sería peor, porque el
benchmark dejaría de medir la señal vectorial y pasaría a medir la divergencia
entre dos copias. Por eso este paquete congela la decisión estructural:

> **`ADR002-B` = `ADR002-A` v2 + señal semántica vectorial tardía, por
> composición.** El candidato B **contiene** al candidato A y delega en él
> todas las etapas; lo único que añade es la señal vectorial dentro de `E3`.

La diferencia arquitectónica sustantiva entre A y B es **una sola**: la señal
semántica vectorial tardía. Cualquier otra diferencia observable será un
defecto de este paquete.

## 2. La base funcional, fijada por identidad

`ADR002-B` reutiliza de `ADR002-A` v2, **por delegación y sin copiar**:

| Pieza | Cómo la usa B |
|---|---|
| `E1` estructurada exacta | delega en `CandidatoA` sin tocarla |
| `E2` variantes morfológicas | delega en `CandidatoA` sin tocarla |
| `E3` léxico-estructurada (términos puente + familias de sujeto) | delega en `CandidatoA` y **une** sus candidatas con las vectoriales, registrando el origen de cada señal por separado |
| `E4` evidencia atribuida | delega en `CandidatoA` sin tocarla |
| Lectura de sujeto, polaridad, condición y tiempo | delega en `CandidatoA.leer`: la validación de lo vectorial es **la misma** que la de lo léxico, item a item |
| Motor, puertas, paradas, explicación, traza | los de la capa común, idénticos para todos los candidatos |

Los árboles que fijan esa base, ya congelados por el acta de preparación de
`ADR002-A` y verificados idénticos entre `97c9977` y el HEAD actual:

| Subárbol | Hash Git |
|---|---|
| `experiments/adr002/candidates/common` | `9ada666e0e044758107f4089e7585bb47aabbbf0` |
| `experiments/adr002/candidates/adr002_a` | `2d90b551445db340458278a5accad55372995b76` |

**Regla congelada:** si en cualquier punto del desarrollo `ADR002-B` no
pudiera implementarse correctamente sin modificar `common/` o `adr002_a/`, el
trabajo **se detiene** y se presenta el cambio exacto requerido, con la
advertencia de que obligaría a sustituir la ficha `ADR002-A` v2, emitir una
v3, repetir sus pruebas y someter de nuevo su preparación a aprobación. Ese
cambio no se hace en silencio. La huella de `ADR002-B` incluirá los dos
árboles de arriba además del suyo propio, porque son fuentes de las que
depende.

## 3. La señal vectorial tardía: dónde, cuándo y qué no puede hacer

### 3.1 Etapa exacta y condición de activación

- **Etapa exacta: `E3`.** Es la etapa «semántica y relacional» de B04 §15.1, y
  la única tardía que B habilita. La salida normativa de E3 manda: «mejora
  recall **sin convertir similitud en identidad**».
- **Condición de activación: insuficiencia previa.** El motor común posee el
  bucle y solo pregunta por `E3` cuando `E1` y `E2` fueron insuficientes
  (B04-RF-14, RF-16). El candidato **no puede adelantar** la señal: su código
  la condiciona a `etapa == E3`, y la apertura del índice es **perezosa** —el
  sidecar no se abre, ni se lee, ni se verifica hasta la primera vez que el
  motor alcanza `E3`—. Si `E1` o `E2` satisfacen la petición, la ruta
  vectorial se invoca **cero veces**, y eso será comprobable por
  instrumentación, no por promesa.
- La insuficiencia con cero resultados también es insuficiencia: si `E1` y
  `E2` no encuentran nada y el modo autoriza `E3`, la señal vectorial actúa
  desde el vector de consulta, sin necesidad de semillas.

### 3.2 Lo que la ruta vectorial NO puede hacer (congelado)

1. No se ejecuta en `E0`, `E1` ni `E2`.
2. No adelanta trabajo cuando `E1` o `E2` ya satisfacen la petición.
3. No decide suficiencia: la adjudican las paradas del motor común.
4. No se salta puertas: **todo** lo que propone pasa por `G1–G12` como
   cualquier otra candidata; una similitud alta no supera ámbito, vigencia,
   disponibilidad, tiempo, polaridad, condición ni criticidad.
5. No eleva similitud a identidad ni a verdad: la similitud selecciona
   **candidatas**; la lectura semántica (sujeto, polaridad, condición,
   tiempo) se calcula item a item con los mismos medios que la base, y las
   posturas opuestas se conservan sin fusionar (RF-17, RF-19).
6. No devuelve contenido desde el índice: el sidecar entrega
   **identificadores, claves de sujeto y similitudes**; el contenido se
   materializa después mediante el puerto canónico, con una consulta dirigida
   por clave exacta.
7. No modifica el orden global de etapas ni la política escalonada (B04-D15:
   la coordinación «no adelanta espacios posteriores ni sustituye la política
   escalonada»).
8. No consulta red, no llama a ninguna API, no descarga ni carga modelos, no
   depende de proveedor.
9. No lee el corpus oficial durante las pruebas técnicas.

## 4. La representación distribucional, congelada

### 4.1 Qué es

**PPMI término-contexto sobre coocurrencia documental, en representación
dispersa de punto fijo.** Todo con biblioteca estándar y SQLite; nada externo.

1. **Unidad de coocurrencia: el elemento canónico completo.** Los elementos
   del canon son afirmaciones cortas; una ventana intra-documental los
   fragmentaría. Dos términos coocurren si aparecen en el mismo elemento; el
   conteo es binario por elemento (presencia conjunta), determinista y ajeno
   al orden interno del texto.
2. **Ponderación: PPMI explícita y versionada.**
   `PPMI(t,c) = max(0, ln(n(t,c)·N / (df(t)·df(c))))`, con `N` el número de
   elementos indexados, `df` la frecuencia documental y `n(t,c)` los
   elementos que contienen ambos términos. Se persiste en **punto fijo**:
   enteros a escala 10⁶. No se persiste ningún flotante: la determinación
   entre ejecuciones se demuestra por igualdad de enteros, no se promete.
3. **Vectores de elemento:** suma de los vectores PPMI de sus términos en
   vocabulario, podada a las dimensiones de mayor peso.
4. **Vector de consulta:** mismo vocabulario, misma transformación, mismos
   topes. Un término de consulta fuera de vocabulario **se ignora**; una
   consulta íntegramente fuera de vocabulario produce cero candidatas
   vectoriales, sin error.
5. **Selección:** solo son candidatos los elementos que comparten con la
   consulta al menos `SOLAPAMIENTO_MINIMO` dimensiones positivas —la
   condición estructural exigida: una coincidencia numérica mínima no
   fabrica candidatas—; se ordenan por coseno con desempate estable por
   identificador y se devuelven a lo sumo `TOP_K` identificadores.
6. **Tokenización versionada:** la de `adr002_a.lexical`
   (`terminos_significativos` + pliegue de diacríticos), citada por versión.
   Usar otra rompería la composición: la base y la señal dejarían de ver las
   mismas palabras.

Lo que esta representación **no** es: no usa caracteres, n-gramas ni hashing
léxico como sustituto encubierto de semántica distribucional —las dimensiones
son términos del canon con peso PPMI, y la relación que detecta es de
**segundo orden**: dos términos que nunca coocurren pueden ser similares si
comparten contextos—. Y no es una elección de modelo productivo: es la
realización experimental de `ADR002-B`; el benchmark decidirá si aporta mejora
material, y su selección no aprueba embeddings, proveedor ni almacenamiento
para producción (ARQ-00 §23: nada de eso puede decidirse «hasta que la
evidencia los justifique»; B04-RF-31 y B04 §8 prohíben atarse a una
realización).

### 4.2 Origen exclusivo de los datos

El índice se construye **solo** desde:

- memorias con estado vigente y su revisión canónica vigente;
- decisiones aprobadas y su revisión canónica vigente;
- la **clave de sujeto** de cada elemento, que se declara expresamente parte
  de la representación: es lo que permite materializar después por el puerto
  canónico sin pedir contenido al índice.

**No incorpora:** mensajes brutos como verdad canónica; resultados esperados
del benchmark; identificadores de casos; adjudicaciones; etiquetas de
candidato; datos personales reales; datos externos de ninguna clase.

### 4.3 Prohibición de calibración

Ni la construcción ni ningún parámetro del índice pueden usar etiquetas
esperadas del benchmark, relaciones de adjudicación, casos oficiales ni
resultados de ejecuciones. Los fixtures técnicos de las pruebas declararán sus
relaciones semánticas **como contextos de coocurrencia** —documentos puente
donde los términos comparten compañía—, nunca como tabla de sinónimos ni como
etiqueta esperada.

## 5. El índice derivado: forma y ciclo de vida

### 5.1 Forma: un sidecar SQLite separado del canon

Fichero SQLite **independiente** del canon (`<base>.vectores.db` en las
pruebas), con exactamente estas tablas:

| Tabla | Contenido |
|---|---|
| `metadatos` | versión del algoritmo, versión de tokenización, **huella del canon de origen** (SHA-256 de la serialización determinista de los elementos indexables), parámetros congelados en JSON, conteos |
| `vocabulario` | término, dimensión asignada, frecuencia documental |
| `vectores_de_termino` | dimensión → pares (dimensión de contexto, peso fijo) |
| `vectores_de_elemento` | identificador canónico, clave de sujeto, pares dispersos, **norma cuadrada entera** |
| `posting` | dimensión → elemento, para la condición de solapamiento |

Sin marcas de tiempo, sin aleatoriedad, sin texto de los elementos más allá
del vocabulario en claro y las claves de sujeto declaradas: la consulta
devuelve identificadores y puntuaciones, jamás contenido. **El sidecar no es
una segunda fuente de verdad**: es derivado, descartable y regenerable, y el
contrato de ADR-001 le aplica entero (destrucción explícita, no
autoritatividad, purga de `.db`, `-wal`, `-shm` y `-journal`).

### 5.2 Construcción, borrado, reconstrucción

- **Construcción:** borra lo previo y reconstruye entero desde el canon.
  Determinista: mismo canon y mismos parámetros producen exactamente el mismo
  inventario lógico y los mismos vectores (enteros idénticos), comprobable
  por volcado ordenado.
- **Borrado:** elimina el fichero sidecar **y** sus `-wal`, `-shm` y
  `-journal`. Sin residuo.
- **Reconstrucción:** borrado + construcción. La igualdad lógica tras
  reconstruir es un criterio de prueba, no una esperanza.

### 5.3 Compatibilidad y fallo cerrado

En la **primera activación** de la señal dentro de un proceso —nunca antes,
para no adelantar trabajo— el lector verifica, en este orden:

1. que el sidecar **existe** → si no: `IndiceInexistenteError`;
2. que es una base íntegra (`quick_check`), con las tablas y los metadatos
   esperados, con la versión del algoritmo, la de tokenización y los
   parámetros congelados exactos → si no: `IndiceCorruptoError`;
3. que la **huella del canon** registrada coincide con la recomputada sobre
   el canon actual → si no: `IndiceDesfasadoError`.

Las tres fallan **cerrado**: ninguna degrada a una ejecución distinta, ninguna
continúa «sin vector» en silencio. La recomputación de la huella lee el canon
directamente en solo-lectura; se declara aquí que esa lectura es **ciclo de
vida del derivado** (la misma naturaleza que el repoblado de `derived.py`), no
recuperación: no entrega ni un byte de contenido al flujo de resultados.

**Limitación S7, registrada con honestidad:** la infraestructura común actual
no adjudica `S7` a partir de este fallo —el constructor de `S7` existe, pero
el motor no tiene camino que lo adjudique, como ya registró el acta de
preparación de `ADR002-A`—. La excepción se propaga y la ejecución no produce
resultado utilizable, que es el comportamiento cerrado correcto; pero **no se
presentará como si `S7` estuviera cubierta**. No se modifica la
infraestructura común para fabricar esa ruta; el benchmark podrá convertir
esta limitación en fallo observable del candidato.

## 6. Parámetros congelados y su fundamento

Ninguno procede de ejecutar el candidato ni de medición alguna. Cada uno se
funda en la cardinalidad conocida del corpus de referencia (5.000 mensajes,
500 recuerdos, 50 decisiones, 2 proyectos → **550 elementos indexables**,
5.670 unidades lógicas de TOL-207), en el presupuesto de TOL-207, en las cotas
ya congeladas de la infraestructura o en la estructura del algoritmo.

| Parámetro | Valor | Fundamento |
|---|---|---|
| `VOCABULARIO_MAXIMO` | 4.096 | techo duro = 2¹²; 550 elementos × ≤64 términos = ≤35.200 ocurrencias, y la poda por frecuencia documental deja el vocabulario observable muy por debajo; si aun así se excediera, se conservan los de mayor frecuencia documental con desempate alfabético, determinista |
| `FRECUENCIA_DOCUMENTAL_MINIMA` | 2 | un término presente en un solo elemento no tiene distribución: su PPMI solo señalaría su propio documento; exigir df≥2 es lo que hace distribucional a la representación, además de podar el vocabulario |
| Unidad de coocurrencia | elemento completo | los elementos canónicos son afirmaciones cortas; fragmentarlas con ventanas produciría contextos vacíos; el conteo binario por elemento es determinista |
| `TOKENS_POR_ELEMENTO_MAXIMOS` | 64 | misma familia que las cotas del puerto; los elementos son afirmaciones cortas y 64 supera con margen su longitud esperada; el truncado es determinista (orden del texto) |
| `DIMENSIONES_MAXIMAS_POR_VECTOR` | 256 | = `LIMITE_POR_CONSULTA`/2 de la infraestructura; acota almacenamiento y coste del coseno; la poda conserva los pesos mayores con desempate por dimensión |
| `ESCALA_FIJA` | 10⁶ | PPMI ≤ ln(550) ≈ 6,31 → valores ≤ 6,31·10⁶; cuadrados ≤ 4·10¹³; sumas de ≤256 dimensiones ≤ 1,1·10¹⁶ < 2⁶³: cabe en el entero de SQLite sin desbordar |
| `CONSULTA_TERMINOS_MAXIMOS` | 16 | = `ARGUMENTOS_MAXIMOS` del puerto: la consulta vectorial no admite más términos que cualquier otra consulta del sistema |
| `TOP_K` | 8 | = `TERMINOS_PUENTE_MAXIMOS` de la base: la señal vectorial no expande más que la señal léxica de la misma etapa; además 8 claves de sujeto caben en **una** llamada dirigida de materialización (≤16 argumentos del puerto) |
| `SOLAPAMIENTO_MINIMO` | 2 dimensiones positivas | la condición estructural exigida: una sola dimensión compartida es una coincidencia puntual, no una distribución compartida; con PPMI no negativo, coseno > 0 ⟺ solapamiento ≥ 1, de modo que el umbral es estructural y no hay que inventar un número de similitud |
| Criterio de similitud | coseno > 0 con solapamiento ≥ 2; orden por (−coseno, identificador) | desempate estable; las **bandas** alta ≥ 0,50 / media ≥ 0,25 / baja > 0 son granularidad de presentación para la traza minimizada, no umbrales de selección |
| `ELEMENTOS_EXAMINADOS_MAXIMOS` | 4.096 | cota dura de seguridad sobre los candidatos del posting: ≈ 7,4× los 550 elementos de la escala de referencia; nunca vinculante a esa escala, y si lo fuera el corte es determinista y declarado |
| Identificadores materializados | ≤ 8 por consulta | los `TOP_K`; la materialización es una llamada `por_clave_exacta` del puerto: ≤16 SELECT dirigidos + ≤2 materializaciones, todas registradas |
| Fuera de vocabulario | se ignora; todo fuera → cero candidatas | sin error y sin degradación oculta: la traza registra la consulta vectorial con sus conteos |
| `ALMACENAMIENTO_MAXIMO_SIDECAR_B` | 33.554.432 B (32 MiB) | aritmética del peor caso a escala de referencia: vectores de término ≤4.096×256 dims×≈16 B ≈ 16,8 MB; vectores de elemento ≤550×256×16 ≈ 2,3 MB; posting ≤140.800 filas×≈24 B ≈ 3,4 MB + índice ≈ 3,4 MB; vocabulario y metadatos < 0,3 MB; total ≈ 26 MB < 32 MiB. El 2,08 % del presupuesto TOL-207 |
| Coste máximo de construcción | 5·10⁹ ns | dominado por ≤149.442 filas insertadas (4.096 + 4.096 + 550 + 140.800) × 20.000 ns ≈ 3·10⁹, más ≤550×64² pares contados y PPMI sobre los pares; margen ≥ 1,6× |
| Coste máximo de borrado del sidecar | 2·10⁸ ns | eliminación de 4 ficheros; techo estático holgado |
| Coste por consulta vectorial | dentro del límite de `E3` (§7) | 3 sentencias dirigidas al sidecar + ≤2,1·10⁶ operaciones enteras de puntuación (≤4.096 × producto disperso ≤256+256) + primera activación amortizada (verificación + huella sobre ≤550 filas) |

## 7. Límites por etapa, almacenamiento y ciclo (estáticos, sin medición)

Los límites de `E0`, `E1`, `E2`, `E4` y `E5` **se conservan de la ficha
`ADR002-A` v2 tras revisarlos**: la base es exactamente A por composición y su
trabajo posible por etapa no cambia fuera de `E3`. El de `E3` **cambia porque
su camino cambia**: a las ≤13 sentencias dirigidas de la base se suman ≤18
sentencias del puerto para materializar lo vectorial (≤8 claves × 2 SELECT +
≤2 materializaciones), ≤3 sentencias al sidecar y ≤2,1·10⁶ operaciones enteras
de puntuación, más la primera activación amortizada.

| Etapa | Objetivo (ns) | Límite (ns) | Trabajo posible |
|---|---:|---:|---|
| E0 | 25.000 | 50.000 | cero sentencias SQL |
| E1 | 1.500.000 | 3.000.000 | ≤37 sentencias dirigidas (base A, sin cambio) |
| E2 | 1.500.000 | 3.000.000 | ≤3 sentencias dirigidas (base A, sin cambio) |
| **E3** | **10.000.000** | **20.000.000** | ≤13 de la base + ≤18 de materialización vectorial + ≤3 al sidecar + puntuación entera acotada |
| E4 | 2.000.000 | 4.000.000 | 1 sentencia dirigida (base A, sin cambio) |
| E5 | 2.500.000 | 5.000.000 | cero sentencias SQL |
| **Total = límite duro P99** | | **35.050.000** | |

Objetivo P95 extremo a extremo: **12.000.000 ns**, sin cambio: el camino
típico se detiene por `S1` en `E1` o `E2` **sin abrir jamás el índice
vectorial**.

**Almacenamiento (TOL-207):** consumo declarado = 1.462.272 B del canon+FTS5
medido + 33.554.432 B de techo estático del sidecar = **35.016.704 B** (21‰
del presupuesto de 1.610.612.736 B); proyección a 50.000 = ×10 =
350.167.040 B, PROYECTADO con modelo lineal en elementos canónicos vigentes y
cota superior por techo de vocabulario y dimensiones. El pico incluye
construcción y reconstrucción porque el constructor **borra antes de
construir**: no hay coexistencia de índice viejo y nuevo.

**Ciclo del derivado (FTS5 medido + sidecar estático):** tamaño ≤ 364.544 +
33.554.432 = 33.918.976 B; construcción ≤ 102.571.300 (P99 medido del FTS5,
paquete 02B) + 5·10⁹ (techo estático del sidecar) = 5.102.571.300 ns;
reconstrucción ≤ 44.512.400 + 5·10⁹ = 5.044.512.400 ns; borrado ≤ 122.865.200
+ 2·10⁸ = 322.865.200 ns. El origen mixto —medido para el FTS5, estático para
el sidecar— queda declarado en la ficha; **del candidato no existe ninguna
medición**.

## 8. Traza minimizada y explicación

- Cada candidata vectorial registra por separado su origen: la señal es
  `semantica_vectorial` con su **banda** (alta/media/baja), nunca la
  puntuación cruda ni texto del elemento. Las candidatas léxico-estructuradas
  de la base conservan su señal propia: los dos orígenes son distinguibles en
  la traza y en la explicación de cada resultado (RF-28).
- La traza solo contiene identificadores, clases, conteos, bandas y
  decisiones. El control de minimización de la capa común
  (`fallos_de_minimizacion`) aplica igual que para A, con los textos del
  fixture como protegidos.
- La similitud no se presenta como verdad: la explicación dice «`E3` por
  `semantica_vectorial` en banda X», y la razón de orden cita la similitud
  distribucional como causa de candidatura, no como afirmación de identidad.
- Ausencia y no-reportable siguen compartiendo el estado externo único
  (`RF-25`/`RF-26`): el motor común no cambia.

## 9. Lo que este paquete NO hace

- No ejecuta el benchmark ni el corpus congelado v0.4.
- No mide rendimiento: ninguna cifra de tiempo del candidato existirá al
  terminar; los controles de las pruebas lo hacen fallar si alguien lo
  intenta.
- No modifica `ADR002-A`, su ficha v2, su acta de preparación, la
  infraestructura común ni Sirius 0.1.
- No implementa `ADR002-C` ni `ADR002-D`.
- No abre `EJE-1` ni `EJE-2` (mismo sustrato FTS5 medido para todos).
- No elige ganador ni declara a `ADR002-B` preparado para benchmark: eso será
  un acto de gobierno posterior del usuario.

## 10. Orden de ejecución preinscrito

| Commit | Contenido | Restricción |
|---|---|---|
| 1 | este paquete y su acta de preinscripción | nada implementado todavía |
| 2 | prototipo de `ADR002-B` (candidato por composición + índice vectorial con constructor, borrado, reconstrucción, compatibilidad e instrumentación) y pruebas **exclusivamente estáticas** | **sin ejecutar el candidato y sin construir ningún índice sobre fixtures**: solo formato, tipos e inspección estructural |
| 3 | `ficha_ADR002-B_v1.json` **congelada** | posterior al prototipo y sin ejecutarlo; declara todo el §4–§8 y cita los tres árboles |
| 4 | pruebas funcionales sobre fixtures propios | solo **después** de que el commit de entrada de la ficha exista: **la ficha vigente debe ser ancestro estricto de toda ejecución funcional del candidato** |

Si una prueba del commit 4 obliga a tocar una fuente incluida en la huella de
B: se conserva la ficha v1, se corrige en un commit nuevo, se emite ficha v2
con motivo de sustitución, se marca v1 `SUSTITUIDA` conforme al contrato y se
congela la v2 **antes** de repetir las ejecuciones. Si el cambio necesario
afectara a `ADR002-A` o a la infraestructura común, **rige la regla del §2:
detenerse**.

---

**Siguiente movimiento único:** implementar el prototipo de `ADR002-B`
conforme a los §2–§6, sin ejecutarlo, y confirmarlo como commit 2.

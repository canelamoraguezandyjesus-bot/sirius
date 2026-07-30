# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 06 · Preinscripción del suelo multiescala

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · PREINSCRIPCIÓN SUCESORA` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Sustituye** | el **método** de determinación de `B` y `U` del paquete 05 |
| **No sustituye** | la **evidencia** del paquete 05, que se conserva íntegra y verificada |
| **Protocolo aplicable** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` (blob `c298a6b8…`) |
| **Registro aplicable** | `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`, fila `ADR002-TOL-107` |
| **Entorno** | `LAB-LINUX` |
| **No autoriza** | aprobar TOL-209, fijar el límite duro de TOL-107, avanzar a T0, implementar o ejecutar candidatos, ejecutar el *benchmark*, fusionar el PR #117 |

---

## 0. Objeto

Preinscribir, **antes de medir**, el método sucesor con el que se determinan
el **umbral de conmutación `U`** y la **banda absoluta `B`** de
`ADR002-TOL-107`, y con él el suelo de medición de `LAB-LINUX` que la puerta
`ADR002-TOL-209` exige.

Este paquete existe porque el método del paquete 05, correctamente ejecutado
y con evidencia válida, produce un `U` que **contradice el propio Registro**.
El defecto está en el método, no en la medición: por eso la evidencia
anterior se conserva y solo se corrige la forma de derivar `B` y `U`.

### 0.1 Por qué dos commits

1. **Commit de preinscripción** — este documento y los cinco módulos que
   implementan el método, congelados **sin ninguna observación**.
2. **Commit de evidencia** — el artefacto y el informe producidos
   **exactamente** por el código del commit anterior, cuya cadena de custodia
   se verifica en tiempo de ejecución contra los blobs que ese commit
   registra.

Un solo commit haría imposible demostrar que el criterio no se escribió
después de ver los resultados. La separación es la única prueba de custodia
temporal disponible en un repositorio.

---

## 1. La contradicción que se corrige

### 1.1 Qué dice el Registro

La fila `ADR002-TOL-107` del Registro v0.4 fija tres cosas y deja una
pendiente:

| Elemento | Valor |
| --- | --- |
| Objetivo relativo | **≤ 20 %** en P50 y P95, aplicable **solo por encima del umbral** |
| Objetivo absoluto | por **debajo** del umbral, contra una **banda absoluta** congelada |
| Umbral de conmutación | *«Su fundamento debe ser el suelo de medición medido del entorno, no una preferencia. No se fija aquí un número: la evidencia disponible no basta y no se inventa»* |

Y, sobre magnitudes concretas, dice literalmente:

> *«**Para FTS5 no se propone objetivo relativo**: con magnitudes de
> 0,14–1,0 ms, un 36 % son 0,27 ms absolutos — es el suelo de medición, no
> inestabilidad del sistema. **A esa escala la comparación debe hacerse en
> valor absoluto**.»*

Es decir: el Registro sitúa **expresamente** las magnitudes de 0,14–1,0 ms en
**régimen absoluto**, y llama «suelo de medición» a una dispersión de
**0,27 ms** observada a esa escala.

### 1.2 Qué produjo el método del paquete 05

El paquete 05 derivó la banda de la dispersión absoluta observada en **una
sola escala** —la más barata alcanzable, del orden de 21 µs— y después
despejó `U = B / 0,20`:

| Magnitud | Valor medido |
| --- | --- |
| `SM` | 21 451 ns |
| `B50` | 476 ns |
| `B95` | 9 758 ns |
| `B = máx(B50, B95)` | **9 758 ns** |
| `U = 5 · B` | **48 790 ns = 0,0488 ms** |

Con `U = 0,0488 ms`, **toda** magnitud de 0,14–1,0 ms queda **por encima**
del umbral y cae en régimen **relativo**: exactamente lo contrario de lo que
la fila TOL-107 declara para esa escala.

### 1.3 Dónde está el error

El paso `U = B / 0,20` con `B` medida en una sola escala presupone, **sin
decirlo**, que la dispersión absoluta del suelo es **constante** frente a la
magnitud medida. La evidencia versionada refuta ese supuesto:

| Magnitud (mín P95) | Dispersión observada | `D / s` | Origen |
| --- | --- | --- | --- |
| 21 451 ns | 9 758 ns | **0,455** | sondas del paquete 05 |
| 188 400 ns | 66 100 ns | **0,351** | `cero_resultados.solo_indice_fts5` |
| 216 900 ns | 71 300 ns | **0,329** | `un_resultado_exacto.solo_indice_fts5` |
| 735 700 ns | 268 100 ns | **0,364** | `muchos_candidatos.solo_indice_fts5` |
| 125 809 200 ns | 19 853 800 ns | **0,158** | `cero_resultados.recuperacion_completa_rank` |
| 127 499 800 ns | 19 676 600 ns | **0,154** | `muchos_candidatos.recuperacion_completa_rank` |
| 127 777 300 ns | 15 760 800 ns | **0,123** | `un_resultado_exacto.recuperacion_completa_rank` |

*(Fuente: `artifacts/adr002_tolerances/suelo_medicion_v0.1.json` y
`artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json`. Las dos
últimas familias son **diagnóstico**, nunca patrón normativo.)*

La razón `D/s` **no es constante**: decrece de forma monótona al crecer la
escala y cruza el 0,20 en algún punto entre 0,74 ms y 126 ms. Resolver el
umbral en la escala más barata lo **subestima** por construcción.

### 1.4 Qué se corrige y qué no

| Se corrige | Se conserva sin tocar |
| --- | --- |
| cómo se determina el punto donde `D(s)/s = 0,20` | el objetivo relativo del **20 %** (Registro v0.4) |
| medir el suelo en **una** escala → medirlo en **trece** | `m = 1` y la relación `B = U / 5` |
| suponer `D` constante → no suponer nada sobre `D` | percentiles por **rango más cercano**, jamás interpolados |
| — | cinco procesos independientes, warm-up declarado, *round-robin* |
| — | la **evidencia** del paquete 05, íntegra y verificada byte a byte |

---

## 2. Método sucesor: punto fijo multiescala

### 2.1 Derivación del criterio desde el propósito de TOL-107

El régimen absoluto existe por una razón declarada: por debajo de cierta
magnitud un criterio relativo del 20 % **exige lo imposible**, porque el
propio suelo del entorno excede ese 20 %. El Registro lo dice con estas
palabras: *«es el suelo de medición, no inestabilidad del sistema»*, y cierra
con ello el riesgo **M-03** («TOL-107 inaplicable y adverso para candidatos
rápidos»).

De ahí se sigue la definición del umbral, sin margen de preferencia:

> `U` es la magnitud desde la cual un criterio relativo del 20 % es
> **alcanzable**, es decir desde la cual `D(M) ≤ 0,20 · M`.

Y de ahí la banda, por continuidad:

> En `M = U` los dos regímenes deben coincidir. El criterio relativo vale
> `0,20 · U`; el absoluto vale `m · B`. Con `m = 1`, la única `B` que
> preserva la continuidad exacta es **`B = U / 5`**.

Ninguna de las dos elecciones es libre: la primera sale del propósito
declarado del régimen absoluto, la segunda de la continuidad en la frontera.
El factor `0,20` **no se elige en este paquete**: es el objetivo relativo ya
congelado del Registro.

### 2.2 El punto fijo, y por qué `U` es una escala medida

`D` se mide en una **escalera de escalas nominales preinscritas** y se
resuelve

```
U := la menor escala medida s tal que  5 · D(s) ≤ s
     y  5 · D(s') ≤ s'  para toda escala medida s' > s

B := U / 5        (exacta en enteros: toda escala es múltiplo de 5)
```

Tres propiedades del criterio, todas comprobables:

1. **`U` nunca se interpola.** Es siempre una escala realmente medida. Es la
   misma disciplina que el §4.1 del protocolo impone a los percentiles,
   aplicada a la selección de escala.
2. **`B ≥ D(U)` por construcción.** La condición de selección es
   `5 · D(U) ≤ U`, es decir `D(U) ≤ U/5 = B`. La banda cubre el ruido
   demostrado en la frontera.
3. **Monotonía exigida.** La condición debe sostenerse en `U` y en **todas**
   las escalas mayores. Un cruce aislado en una escala pequeña seguido de un
   fallo en una mayor significa que el ruido no decrece con la escala: el
   punto fijo no está determinado y no puede adoptarse.

### 2.3 El método del paquete 05 como caso particular

Si `D` fuese constante e igual a `D₀`, la condición `5·D₀ ≤ s` se cumple para
toda `s ≥ 5·D₀` y falla por debajo. El punto fijo devuelve entonces la menor
escala `≥ 5·D₀`, que es —salvo la resolución de la escalera— exactamente
`U = 5·B` del paquete 05. El sucesor **generaliza** el método anterior; no lo
contradice.

### 2.4 Por qué `D(s)` no se promedia hasta desaparecer

Objeción legítima: si la escala se alcanza acumulando trabajo dentro de la
ventana, ¿no se promedia el ruido y decae `D/s` como `1/√s` por puro
artefacto del método?

No, y la razón es la construcción de `D`. `D(s)` es `máx − mín` de un
percentil **entre procesos independientes**, no una desviación dentro de un
proceso. Lo que separa a dos procesos equivalentes son diferencias
**sistemáticas** —estado de caché, frecuencia, afinidad, población de la
*page cache*— comunes a **todo** el trabajo de la ventana y por tanto
proporcionales a ella. El promediado interno solo cancela el *jitter*
independiente por unidad de trabajo. Ésta es exactamente la construcción del
§6.1 del protocolo, que es la que TOL-107 llama «variación entre ejecuciones
equivalentes».

La limitación residual se declara en el §9.

### 2.5 La banda debe cubrir el suelo por debajo del umbral

Un control bloqueante adicional, que el método anterior no podía formular
porque solo tenía un punto: para toda escala medida `s ≤ U` debe cumplirse

```
D(s) ≤ m · B
```

Si el suelo excediera la banda en alguna escala del régimen absoluto, el
criterio absoluto también sería inalcanzable allí y la puerta volvería a
exigir lo imposible. Con `D` no decreciente la condición se cumple por
construcción —`D(s) ≤ D(U) ≤ U/5 = B`—; el control existe para **denunciar**
una escalera no monótona en vez de publicarla en silencio.

---

## 3. La escalera nominal

```
10 µs · 20 µs · 50 µs · 100 µs · 200 µs · 500 µs · 1 ms ·
2 ms · 5 ms · 10 ms · 20 ms · 50 ms · 100 ms
```

Trece escalones, progresión **1-2-5**, cuatro órdenes de magnitud.

| Decisión | Razón |
| --- | --- |
| rango 10 µs – 100 ms | abarca con margen todas las magnitudes que la evidencia versionada publica (0,14 ms a 128 ms) sin que ninguna de ellas determine escala alguna |
| progresión 1-2-5 y no por décadas | `U` es una escala **medida**: la resolución de la escalera es la resolución de `U`. Por décadas, `U` quedaría con un factor 10 de indeterminación |
| toda escala múltiplo de 5 | `B = U / 5` exacta en aritmética entera, sin redondeo |
| escala mínima 10 µs | es el orden de la escala única del paquete 05: la escalera **contiene** el punto anterior y permite compararlos |

Las escalas son **de trabajo sintético neutral**. Que el rango cubra las
magnitudes históricas no las convierte en patrón: ninguna sonda ejecuta
FTS5, `rank()` ni operación de candidato alguno.

---

## 4. Las dos familias neutrales

| Familia | Unidad de trabajo | Qué aporta |
| --- | --- | --- |
| `cpu` | una vuelta de bucle aritmético entero en el intérprete | acota el suelo **por abajo**: el trabajo más simple que la máquina puede hacer durante una ventana de duración `s` |
| `canon` | una consulta resuelta por clave primaria sobre `memory_revisions` | añade lo que un motor de almacenamiento real aporta —descenso de árbol, *page cache*, asignación, maquinaria de cursor— sin salir de lo neutral |

`D(s)` es el **peor caso** entre familias y entre P50 y P95. El peor caso es
la única dirección admisible: un suelo subestimado exige a los candidatos una
estabilidad que el entorno no permite.

### 4.1 Tabla canónica

`memory_revisions` es el canon de ADR-001: la reconstrucción obligatoria se
hace **desde** esta tabla y todo derivado es regenerable y no autoritativo.
Su clave primaria `id` la crea la cadena canónica de Alembic
(`4022f15cc8df_create_memories_and_memory_revisions`) como `INTEGER`
autoincremental, de modo que el índice lo aporta SQLite y no lo elige ninguna
arquitectura candidata. No es una tabla FTS ni una tabla sombra.

### 4.2 SQL normativo y guarda de neutralidad

```sql
SELECT id FROM memory_revisions WHERE id = ?
```

La guarda `fallos_sql_de_sonda` rechaza cualquier SQL de sonda que contenga
`fts`, `match`, `rank`, `bm25`, `embedding`, `vector`, `join`, `like` u
`order by`, y exige que consulte la tabla canónica filtrando por clave
primaria parametrizada. La guarda `comprobar_neutralidad` rechaza cualquier
nombre de sonda o familia que contenga esos términos o un identificador de
candidato (`adr002-a` … `adr002-d`).

Una prueba recorre el **AST** del módulo de sondas y exige que toda cadena
que contenga `select` nombre la tabla canónica y ninguno de los términos
prohibidos. La comprobación se hace sobre el árbol sintáctico y no sobre el
texto porque los *docstrings* citan FTS5 precisamente para prohibirlo.

### 4.3 Sondas de suelo unitario: `SM`

Se conservan del paquete 05, porque su significado no estaba en discusión:

| Sonda | Qué mide |
| --- | --- |
| `D_vacia` | corchete completo del arnés sobre un invocable vacío |
| `canon_0_filas` | consulta por clave primaria inexistente |
| `canon_1_fila` | consulta por clave primaria existente |

`SM` es el **peor P95** de las tres sobre todos los procesos. `SM` es un
**nivel** y actúa solo como guarda de dominancia del instrumento: una
magnitud cuyo `mín_s P95` quede por debajo de `SM` es `NO_EVALUABLE`. `SM`
**no** determina `U` ni `B`.

---

## 5. Calibración: una sola vez, en el proceso padre

La escala `s` se alcanza aumentando la cantidad de trabajo **dentro** de la
ventana cronometrada, nunca repitiendo la ventana. El número de unidades de
cada escala se obtiene así:

```
unidades(s) = máx(1, redondeo( s · unidades_referencia / coste_referencia ))
```

en aritmética entera exacta, donde `coste_referencia` es el **P50** de
`MUESTRAS_CALIBRACION = 21` observaciones de la cantidad de referencia de la
familia (`10 000` vueltas para `cpu`, `10` consultas para `canon`).

| Decisión | Razón |
| --- | --- |
| la calibración la hace el **padre**, una sola vez | TOL-107 mide la variación entre ejecuciones **equivalentes**. Dos procesos que resuelven cantidades de trabajo distintas no son equivalentes, y su diferencia mezclaría ruido con error de calibración |
| el mismo plan de unidades se **impone** a todos los hijos | el control `unidades_identicas` lo recomputa cruzando dos fuentes por proceso: el plan que declara haber recibido y las unidades publicadas en cada entrada medida |
| 21 muestras, número impar | el P50 por rango más cercano cae en una muestra central real, y la mediana no la arrastra una sola expropiación |
| calibración **fuera** de toda ventana normativa | no entra en ningún vector crudo ni en ninguna derivación |

### 5.1 Banda de calibración

La magnitud observada de cada escala debe caer en **`[s/2, 2s]`**. Fuera de
banda, la escala se declara mal calibrada y la corrida **falla cerrado**: no
se recalibra al gusto tras ver resultados. El control se recomputa desde el
P50 publicado de cada `(familia, escala, proceso)`, no se acepta declarado.

### 5.2 Progresión por escala

Sustituye la comprobación 1×/2× del paquete 05 por su versión multiescala y
con razón arbitraria. Entre dos escalas consecutivas, en aritmética entera y
sin división:

```
| p50_mayor · s_menor − p50_menor · s_mayor | · 3  ≤  p50_menor · s_mayor
```

Tolerancia preinscrita de **1/3**, y **no** de 1/2. El escalón mínimo de la
escalera es un factor 2, y «el tiempo no crece en absoluto» produce
exactamente un desvío del 50 % del valor esperado: con tolerancia 1/2 ese
caso —el que la comprobación existe para denunciar— pasaría justo en la
frontera. Con 1/3, un escalón de factor 2 exige una razón medida en
`[1,33×, 2,67×]`, holgura sobrada frente al 5 % de error que la cuantización
puede introducir donde la progresión es exigible.

**Solo se exige** donde ambas escalas usan
al menos `UNIDADES_MINIMAS_PROGRESION = 10` unidades de trabajo: con menos,
redondear al entero más cercano introduce hasta un 50 % de error en la propia
escala nominal, y la comprobación denunciaría un artefacto de la calibración
en vez de un defecto del instrumento. La tabla completa se publica; la
exigencia se aplica donde procede, y ese campo `exigible` también se
recomputa.

---

## 6. Constantes operativas preinscritas

| Constante | Valor | Fundamento |
| --- | --- | --- |
| `PROCESOS_MINIMOS` | 5 | §3.3 del protocolo: al menos cinco sesiones independientes |
| `N_COSTE_BAJO` | 100 | §3.2: 100 repeticiones cuando el coste es bajo |
| `N_COSTE_ALTO` | 30 | §3.1: 30 como mínimo |
| `UMBRAL_COSTE_BAJO_NS` | 1 000 000 | frontera entre ambos regímenes de `n` |
| `WARMUP_ESCALA` | 5 | warm-up declarado y descartado íntegro, por `(familia, escala)` |
| `N_UNITARIA` / `WARMUP_UNITARIA` | 100 / 5 | sondas de suelo unitario |
| `RONDAS_ROUND_ROBIN` | 5 | §5.2 aplicado a sondas; divide exactamente a 100 y a 30 |
| `SEMILLA` | 20260726 | §5.3: semilla del corpus de rendimiento congelado |
| `MUESTRAS_CALIBRACION` | 21 | §5 de este documento |
| `VUELTAS_REFERENCIA` | 10 000 | trabajo fijo del diagnóstico de deriva |
| `TOLERANCIA_DERIVA` | 3/10 | criterio de *throttling*, conservado del paquete 05 |
| `TOLERANCIA_PROGRESION` | 1/3 | §5.2: con 1/2 el caso «no crece» pasaría en la frontera |
| `UNIDADES_MINIMAS_PROGRESION` | 10 | §5.2: por debajo domina la cuantización |
| `CALIBRACION` | `[s/2, 2s]` | §5.1: banda de la magnitud observada |
| `OBJETIVO_RELATIVO` | 1/5 | **congelado en el Registro v0.4**; no se elige aquí |
| `MARGEN_M` | 1 | único valor que preserva continuidad exacta en `M = U` |
| `FACTOR_U` | 5 | `B = U / 5`, recíproco del objetivo relativo |

---

## 7. Orden de evaluación y régimen por percentil

El orden es normativo y no conmutativo:

1. **Guarda de dominancia del instrumento.** Si `mín_s P95 < SM`, la magnitud
   es `NO_EVALUABLE` y **no publica régimen**.
2. **Régimen por percentil.** `RELATIVO` si `mín_s p(s) ≥ U`; `ABSOLUTO` en
   caso contrario. Se decide **percentil a percentil**, con el mismo `mín_s`
   que aparece en el denominador de la fórmula de variación del §6.1.
3. **Criterio del régimen.** `RELATIVO`: `(máx − mín) / mín ≤ 1/5`.
   `ABSOLUTO`: `(máx − mín) ≤ m · B`. Ambos en aritmética entera exacta.

### 7.1 Invariante y combinaciones posibles

`mín_s P95 ≥ mín_s P50` es un invariante demostrable: para cada sesión
`P95(s) ≥ P50(s)`, luego el mínimo sobre sesiones del P95 no puede quedar por
debajo del mínimo del P50. De él se sigue que solo son posibles **tres**
combinaciones:

| `mín_s P50` | `mín_s P95` | P50 | P95 |
| --- | --- | --- | --- |
| `< U` | `< U` | absoluto | absoluto |
| `< U` | `≥ U` | absoluto | relativo |
| `≥ U` | `≥ U` | relativo | relativo |

La combinación «P50 relativo · P95 absoluto» es **imposible**; el código la
denuncia con excepción y el validador la rechaza en el artefacto.

### 7.2 Registro por percentil

La ficha aprobada tiene un único campo *Régimen aplicable*. Se rellena con la
cadena `P50: <régimen> · P95: <régimen>`, o con `NO_EVALUABLE` si la magnitud
está dominada por el instrumento. No se añade ningún campo nuevo a un
documento aprobado.

---

## 8. Controles internos bloqueantes

Diecinueve, todos **recomputados desde los datos crudos**; ningún *flag*
declarado por un proceso se acepta como única fuente. Fallan **cerrado**: un
control ausente o con valor distinto de `True` cuenta como fallido.

| Control | Qué recomputa |
| --- | --- |
| `procesos_independientes` | al menos cinco resultados de proceso |
| `pids_distintos` | PIDs enteros, positivos y sin repetición |
| `escalera_completa` | las 26 combinaciones `(familia, escala)` presentes en cada proceso |
| `unidades_identicas` | el plan de unidades de cada proceso y las unidades de cada entrada, contra el plan del padre |
| `calibracion_en_banda` | P50 de cada `(familia, escala, proceso)` en `[s/2, 2s]` |
| `carga_registrada` | carga del sistema presente por proceso y en ambas capturas |
| `boot_id_estable` | mismo `boot_id` al inicio y al final |
| `captura_ambiental_presente` | ambas capturas presentes y no vacías |
| `estabilidad_intraproceso` | trabajo de referencia sin deriva monótona excesiva |
| `progresion_por_escala` | progresión exigible entre escalas consecutivas |
| `banda_cubre_el_suelo` | `D(s) ≤ m · B` para toda escala `s ≤ U` |
| `vectores_crudos_completos` | longitud exacta de cada vector según su escala |
| `sin_muestras_negativas` | ninguna duración negativa |
| `sin_filtrado` | ningún descarte y ninguna incidencia registrada |
| `warmup_separado` | warm-up declarado igual al preinscrito, por entrada |
| `sin_redondeo_previo` | ningún vector con todas sus muestras múltiplos de 100 ns |
| `sondas_neutrales` | nombres de familias y sondas, y SQL de la sonda canónica |
| `evidencia_anterior_intacta` | blobs de la evidencia del paquete 05, byte a byte |
| `custodia_verificada` | cadena de custodia completa, **reverificada tras medir** |

### 8.1 `banda_cubre_el_suelo` y `NO_EVALUABLE`

`banda_cubre_el_suelo` presupone un umbral resuelto. Si el punto fijo **no**
se resuelve, ese control no puede satisfacerse y no debe bloquear un
`NO_EVALUABLE` legítimo: el artefacto se publica **sin `U` ni `B`**, con su
motivo explícito. El validador lo impone al revés: sin `U` ni `B`, el único
control que puede fallar es ése; con `U` y `B` publicados, **todos** deben
estar en `True`.

### 8.2 Tratamiento de valores extremos

No se recorta, no se filtra y no se sustituye ninguna muestra. Los vectores
crudos se publican íntegros en nanosegundos. `valores_distintos` y
`repeticion_maxima` se publican como **diagnóstico de forma**, no como umbral
automático: distinguen un suelo cuantizado por la resolución del reloj de un
vector recortado y repadeado, pero no permiten decidir automáticamente entre
ambos (limitación declarada en el §9).

---

## 9. Limitaciones conocidas

1. **Escalado por cantidad de trabajo, no por operación única.** Una
   operación real de 1 ms hace una cosa complicada; la sonda hace muchas
   cosas simples. Lo que se caracteriza es la perturbación que la plataforma
   introduce en una **ventana** de esa duración, no la varianza interna de
   una operación de producto. El §2.4 explica por qué la construcción entre
   procesos preserva la componente sistemática; la componente de *jitter*
   independiente por unidad sí se promedia y por tanto `D(s)` podría quedar
   **subestimada** en las escalas altas. La dirección del sesgo se declara:
   subestimar `D` en escalas altas **baja** `U`, es decir empuja hacia el
   régimen relativo. No se compensa con ningún factor inventado.
2. **Resolución de `U` limitada por la escalera.** `U` solo puede tomar uno
   de trece valores. Una escalera más densa solo podría **bajar** `U`.
3. **Cinco procesos.** `máx − mín` sobre cinco observaciones es un estimador
   de dispersión con varianza alta y sesgo a la baja. Es lo que el §3.3 del
   protocolo exige como mínimo, y es la misma base de la evidencia anterior;
   no se aumenta para no cambiar dos cosas a la vez.
4. **Percentiles de cola con `n = 30`.** En las escalas de coste alto el P99
   coincide con el máximo observado: acota la cola, no la caracteriza. Se
   publica `resolucion_percentil` en cada entrada para que nadie lea más de
   lo que `n` permite.
5. **Cuantización de la calibración en las escalas bajas.** Con una unidad de
   trabajo de coste comparable a la escala nominal, el número entero de
   unidades introduce error en la escala efectiva. Está acotado por la banda
   `[s/2, 2s]` y la exigencia de progresión se suspende donde es relevante,
   pero el error existe y se declara.
6. **Un solo entorno.** Todo es `LAB-LINUX`. Nada de lo aquí medido se
   generaliza a otra máquina, otro sistema operativo u otra población de
   *page cache*.
7. **Vector cuantizado vs. vector repadeado.** Ambos casos son
   indistinguibles sin evidencia adicional. Se publican los diagnósticos de
   forma y **no** se convierte la heurística en control bloqueante, porque un
   umbral automático produciría falsos positivos sobre vectores legítimamente
   cuantizados.
8. **Autorreferencia inevitable del esquema.** El validador vive en el mismo
   commit que valida: no puede acreditar sus propios blobs. La cadena de
   custodia externa —`git rev-parse <sha>:<ruta>`— es lo que cierra ese hueco,
   y por eso el entorno de custodia expone `blob_en_commit` como fuente de
   verdad independiente del árbol de trabajo.
9. **El contraste con FTS5 y `rank()` es diagnóstico.** Las magnitudes
   históricas se clasifican con el umbral resuelto para poder **explicar** el
   resultado, jamás para determinarlo. Si la partición resultante no
   reprodujera la histórica, eso se explica; no se corrige el umbral.
10. **La coherencia con la fila TOL-107 no está garantizada de antemano.** El
    método se congela antes de medir. Si el punto fijo resultara tal que las
    magnitudes de 0,14–1,0 ms **no** cayeran en régimen absoluto, el
    resultado se publica igual, con su contradicción declarada, y la decisión
    pasa a quien aprueba. No se ajusta ninguna fórmula después de observar
    resultados.
11. **Lo que el validador no puede recomputar.** Un barrido adversarial sobre
    las 327 rutas del artefacto —cada campo borrado y sustituido— deja tres
    familias de mutaciones que ningún validador podría detectar, y que se
    declaran en vez de disimularse:
    - **prosa libre**: los textos de `metodo`, `contraste_metodo_anterior`,
      las notas y `motivo_no_evaluable`. Se exige que existan y no estén
      vacíos; su contenido no es verificable por máquina;
    - **muestras de calibración distintas de la mediana**: solo el P50 es
      normativo y está atado a su vector, de modo que alterar una muestra que
      no sea la central no cambia nada verificable;
    - **carga del sistema y carga ambiental**: se exige su presencia,
      cobertura por proceso y no vacuidad, pero sus valores no se derivan de
      ninguna otra parte del artefacto. Igual ocurre con los tres P50 del
      trabajo de referencia, cuyos vectores no se publican.

    Todo lo demás —percentiles, unidades, `D(s)`, punto fijo, `SM`, régimen,
    veredicto, tabla de progresión, curva, controles, negaciones y forma de la
    custodia— se recomputa y se contrasta.

---

## 10. Desviaciones declaradas de antemano

| Desviación | Respecto de | Justificación |
| --- | --- | --- |
| trece escalas sintéticas en lugar de los escenarios del corpus | §5 del protocolo | el suelo no es una operación de producto: medirlo con operaciones de candidato lo contaminaría con la identidad del candidato |
| dos familias neutrales en lugar de una | paquete 05 | el peor caso entre familias es la dirección conservadora del suelo |
| calibración en el padre, no en cada hijo | — | sin cantidad de trabajo idéntica no hay ejecuciones equivalentes |
| `n = 30` por encima de 1 ms | §3.2 | el coste de 100 repeticiones a 100 ms sería de más de un minuto por proceso y familia; §3.1 admite 30 como mínimo |
| progresión exigible solo con ≥ 10 unidades | paquete 05 (1×/2× siempre exigible) | por debajo, la cuantización domina y la comprobación denunciaría la calibración, no el instrumento |
| se añade el control `banda_cubre_el_suelo` | paquete 05 | con un solo punto medido no era formulable |

---

## 11. Custodia

### 11.1 Ficheros preinscritos

| Ruta |
| --- |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1.md` |
| `experiments/adr002/tolerances/floor_scale_probes.py` |
| `experiments/adr002/tolerances/floor_scale_protocol.py` |
| `experiments/adr002/tolerances/run_floor_scale.py` |
| `experiments/adr002/tolerances/schema_floor_scale_v0_1.py` |
| `experiments/adr002/tolerances/test_adr002_floor_scale.py` |

Además se registra el blob de `experiments/adr002/tolerances/corpus.py`, que
participa por importación sin ser fichero nuevo: un cambio en él cambiaría lo
que se mide.

### 11.2 Precondiciones de la ejecución

Antes de abrir **una sola** ventana cronometrada, y fallando cerrado:

- árbol de trabajo limpio;
- `HEAD` exactamente igual al commit de preinscripción, y ese commit existe;
- los seis blobs preinscritos coinciden con el árbol **y** con lo que el
  commit registra (`git rev-parse <sha>:<ruta>`);
- el módulo heredado coincide con su blob preinscrito;
- el protocolo aprobado está intacto (`c298a6b8…`);
- los siete blobs del corpus congelado están intactos;
- **la evidencia del paquete 05 está intacta byte a byte** (`suelo_medicion_v0.1.json`
  y su informe);
- la ruta de salida **no existe**.

### 11.3 Recorrido de la corrida

```
precondiciones
  → captura ambiental inicial
  → calibración ÚNICA en el padre
  → cinco procesos independientes con el MISMO plan de unidades
  → sondas en round-robin sobre (familia, escala)
  → captura ambiental final
  → forma de los resultados
  → custodia REVERIFICADA tras medir
  → punto fijo (D(s), U, B) y SM
  → controles bloqueantes
  → documento
  → validación con schema_floor_scale_v0_1
  → escritura atómica sin sobrescribir
  → relectura y revalidación
```

Si cualquier paso falla, **no se escribe artefacto y no se publica ningún
valor**.

### 11.4 Publicación sin sobrescribir ni destruir

La escritura usa `os.link`, no `os.replace`: si la ruta de salida apareciera
durante la medición, `link` falla con `FileExistsError` y el fichero ajeno
queda **intacto**. Cierra la ventana TOCTOU entre la precondición «salida
inexistente» y la publicación. La escritura se separa de la relectura para
que el borrado de limpieza solo pueda alcanzar un fichero que **esta** corrida
haya creado, y ese borrado se **verifica**: si el artefacto sobreviviera, no
se podría seguir afirmando que no se publicó nada.

### 11.5 Recomputación obligatoria y validador total

El validador **no acepta ningún valor declarado**. Recomputa desde los
vectores crudos publicados: los percentiles por rango más cercano, las
unidades desde la calibración, `D(s)` escala a escala y familia a familia, el
punto fijo completo, `SM`, el régimen y el veredicto de cada magnitud, y la
tabla de progresión. Además es **total por contrato**: nunca lanza. Un
validador que lanzara ante un valor JSON legal (`NaN`, cadena donde se espera
entero) dejaría de ser una guarda, porque quien lo invoca no obtendría fallos
sino una excepción.

---

## 12. Matriz bloqueante

| # | Condición | Se hace cumplir en |
| --- | --- | --- |
| 1 | árbol de trabajo limpio | `verificar_precondiciones_ejecucion` |
| 2 | `HEAD` = commit de preinscripción | `verificar_precondiciones_ejecucion` |
| 3 | el commit de preinscripción existe | `verificar_precondiciones_ejecucion` |
| 4 | ruta de salida inexistente | `verificar_precondiciones_ejecucion` + `os.link` |
| 5 | seis blobs preinscritos = árbol | `verificar_custodia` |
| 6 | seis blobs preinscritos = commit | `verificar_custodia` (`blob_en_commit`) |
| 7 | módulo heredado intacto | `verificar_custodia` |
| 8 | protocolo aprobado intacto | `comprobar_precondiciones` |
| 9 | corpus congelado intacto | `verificar_custodia` |
| 10 | evidencia del paquete 05 intacta | `fallos_evidencia_anterior` |
| 11 | diff vacío en los preinscritos entre commit y `HEAD` | `verificar_custodia` |
| 12 | custodia reverificada tras medir | `ejecutar_corrida` |
| 13 | cinco procesos | control 1 + esquema |
| 14 | PIDs distintos | control 2 + esquema |
| 15 | 26 combinaciones `(familia, escala)` por proceso | control 3 + esquema |
| 16 | cinco procesos por `(familia, escala)` | esquema |
| 17 | unidades idénticas entre procesos | control 4 + esquema |
| 18 | unidades derivadas de la calibración publicada | esquema |
| 19 | coste de calibración = P50 de sus muestras | esquema |
| 20 | 21 muestras de calibración por familia | esquema |
| 21 | P50 observado en `[s/2, 2s]` | control 5 + esquema |
| 22 | carga registrada | control 6 |
| 23 | `boot_id` estable | control 7 + esquema |
| 24 | capturas ambientales presentes | control 8 |
| 25 | sin deriva intraproceso | control 9 + esquema |
| 26 | progresión exigible cumplida | control 10 + esquema |
| 27 | `exigible` y `progresa` recomputados | esquema |
| 28 | `D(s) ≤ m · B` bajo `U` | control 11 + esquema |
| 29 | longitud exacta de cada vector | control 12 + esquema |
| 30 | sin muestras negativas | control 13 + esquema |
| 31 | sin filtrado y sin incidencias | control 14 + esquema |
| 32 | warm-up declarado = preinscrito | control 15 + esquema |
| 33 | sin redondeo previo a 100 ns | control 16 + esquema |
| 34 | sondas neutrales (nombres y SQL) | control 17 + esquema + AST |
| 35 | percentiles por rango más cercano, recomputados | esquema |
| 36 | `resolucion_percentil` coherente con `n` | esquema |
| 37 | familias y escalas de la escalera, sin intrusas | esquema |
| 38 | `U` es una escala medida de la escalera | esquema |
| 39 | `U = 5 · B` y `m = 1` | esquema |
| 40 | objetivo relativo = 1/5 | esquema |
| 41 | punto fijo recomputado desde los vectores | esquema |
| 42 | `dispersiones` y `detalle_por_escala` recomputados | esquema |
| 43 | `SM` recomputado desde las sondas unitarias | esquema |
| 44 | guarda de dominancia antes del régimen | `evaluar_magnitud` + esquema |
| 45 | invariante `mín_s P95 ≥ mín_s P50` | `evaluar_magnitud` + esquema |
| 46 | combinación P50 relativo / P95 absoluto rechazada | `evaluar_magnitud` + esquema |
| 47 | régimen recomputado desde `U` | esquema |
| 48 | veredicto recomputado desde el régimen | esquema |
| 49 | `NO_EVALUABLE` con motivo explícito | esquema |
| 50 | `NO_EVALUABLE` no absuelve controles | esquema |
| 51 | no se publica `U`/`B` con controles fallidos | esquema |
| 52 | clasificación de la línea base divulgada | esquema |
| 53 | las dos listas de veredicto son la misma | esquema |
| 54 | evidencia anterior citada por su blob exacto | esquema |
| 55 | contraste con el método anterior explicado | esquema |
| 56 | plan = plan preinscrito (orden, `n` y warm-up incluidos) | esquema |
| 57 | las siete negaciones explícitas de `no_autoriza` | esquema |
| 58 | ninguna clasificación de TOL-207 importada | esquema |
| 59 | validador total: nunca lanza | `fallos_suelo_multiescala` |
| 60 | artefacto releído y revalidado tras escribir | `ejecutar_corrida` |
| 61 | PIDs medidos = procesos declarados, y positivos | esquema |
| 62 | tabla de progresión recomputada desde las escalas | esquema |
| 63 | una tabla de progresión y una referencia por proceso | esquema |
| 64 | curva `D(s)/s` recomputada | esquema |
| 65 | carga por proceso presente y con cobertura exacta | esquema |
| 66 | capturas ambientales etiquetadas por etapa, con `boot_id` | esquema |
| 67 | `commit_a`, `head` y blobs con forma de objeto Git | esquema |
| 68 | cita histórica del método anterior fijada (`U`, `B`) | esquema |

Sesenta y ocho condiciones. Ninguna se reduce a otra: cada fila tiene su
propia prueba negativa.

---

## 13. Qué desbloquea y qué no

**Desbloquea**, si la corrida es válida: disponer de un `U` y una `B`
**propuestos** con fundamento medido y multiescala, y del suelo `SM` del
entorno, para que la aprobación de `ADR002-TOL-209` pueda decidirse sobre
evidencia.

**No desbloquea nada más.** En particular:

- `ADR002-TOL-209` sigue **NO SATISFECHA** hasta el acta de aprobación
  correspondiente;
- el **límite duro** de TOL-107 no se fija aquí: se congela con el entorno de
  ejecución;
- no se avanza a **T0**, no se implementa ni ejecuta ningún **candidato**, no
  se ejecuta el **benchmark**;
- no se fusiona el **PR #117**;
- la evidencia del paquete 05 **no se sustituye ni se retira**: se conserva y
  se cita.

---

## 14. Prohibiciones

1. No modificar ningún documento aprobado ni congelado.
2. No modificar, retirar ni reescribir la evidencia del paquete 05.
3. No usar FTS5, `rank()`, BM25, *embeddings* ni operación de candidato
   alguno como sonda normativa.
4. No ajustar fórmulas, constantes, sondas, controles ni criterios después de
   observar resultados.
5. No publicar `U` ni `B` con algún control bloqueante fallido.
6. No inventar valores si el punto fijo no se resuelve: `NO_EVALUABLE` con
   motivo.
7. No sobrescribir ni destruir ningún fichero existente al publicar.
8. No importar ninguna clasificación formal de TOL-207 sin autoridad que la
   generalice.

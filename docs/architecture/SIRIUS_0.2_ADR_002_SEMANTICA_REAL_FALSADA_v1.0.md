# SIRIUS 0.2 — ADR-002 · La semántica real, falsada

**Versión:** 1.0
**Estado:** **LA SEMÁNTICA REAL NO PERMITE CERRAR `ADR-002`** · evidencia reproducible
**Fecha:** 8 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Alcance:** dentro de `ADR-002`. **No se abre ningún ADR nuevo.**
`ADR002-C` queda **congelado** como línea base; `ADR002-B`, `ADR002-D` y la capa
común quedan **byte a byte**.

**Sucede a:** `SIRIUS_0.2_ADR_002_POR_QUE_FALLAN_LOS_CUATRO_v1.0.md`, que
identificó la causa raíz. Este documento **falsa la hipótesis** que aquel dejó
planteada.

---

## 1. Conclusión binaria

> **La semántica real NO permite cerrar `ADR-002`.**

Sobre **18 puntos de operación** medidos con el banco congelado entero y las
puertas originales, la señal semántica real **no cierra ni una sola** de las
once omisiones. En el mejor caso no cambia nada; en el resto **empeora**
exactitud y conformidad de etapa.

| | exactos | omisiones | contam. | etapa |
|---|---|---|---|---|
| **Base `A` = `C`** | **24/47** | **11** | 3 | **32/46** |
| `B-SEM` mejor punto (umbral ≥0,80) | 24/47 | **11** | 3 | 32/46 |
| `B-SEM` punto medio (0,70 · k=3) | 23/47 | **11** | 3 | 31/46 |
| `B-SEM` peor punto (0,50 · k=8) | 19/47 | **11** | 3 | 25/46 |

La columna que decide es **omisiones: 11 en las dieciocho filas**. La señal no
recupera ninguno de los elementos que faltaban. Lo único que varía es cuánto
ruido añade.

**Por tanto no se materializa `ADR002-D`.** La instrucción era explícita —«solo
si la señal semántica demuestra utilidad»— y la puerta queda cerrada con
medición, no con opinión.

---

## 2. Qué se probó, exactamente

Tres modelos reales, **entrenados fuera de este corpus**, que es la propiedad
que el PPMI de `ADR002-B` no puede tener:

| modelo | qué es | vectores | vía |
|---|---|---|---|
| `es_core_news_md` | vectores estáticos españoles | 20 000 × 300 | release de GitHub |
| `es_core_news_lg` | vectores estáticos españoles | 500 000 × 300 | release de GitHub |
| `es_dep_news_trf` | **transformer** español, contextual | 768 d | release de GitHub |

Los tres cargan **sin red** (`HF_HUB_OFFLINE=1`) porque sus pesos viajan dentro
del paquete. **Ningún texto del canon sale de la máquina en ningún momento.**

Y tres formas de agregar palabra→frase: media de palabras con contenido, máximo
entre pares, y media de máximos.

### Ranking sobre el ámbito completo, antes de tocar el motor

Puesto en que queda cada elemento esperado, entre los 41 del ámbito:

| agregación | esperados en top-5 | puesto mediano |
|---|---|---|
| `es_core_news_lg` · media de contenido | 4/19 | 27 |
| `es_core_news_lg` · **máximo entre pares** | **6/19** | **16** |
| `es_core_news_lg` · media de máximos | 4/19 | 20 |
| `es_dep_news_trf` · contextual | 1/19 | 21 |
| `es_core_news_md` (control de tamaño) | 6/19 | 16 |

Dos lecturas importan:

* **El tamaño del modelo no es el problema.** 20 000 vectores y 500 000 dan
  cifras idénticas. No es cobertura de vocabulario lo que falta.
* **El transformer es *peor* que los vectores estáticos.** Es el resultado
  conocido de promediar estados ocultos de un modelo que no está afinado para
  similitud, y hay que decirlo así: falsa **esa** familia, no toda la semántica.

### El puente que sí funciona, y por qué no basta

Con **máximo entre pares**, `DECISION:3` —«El presupuesto máximo del proyecto
es 1.500 €»— sube al **puesto 3 de 41** para la consulta «evidencia de límite de
gasto». Eso es exactamente lo que el PPMI **no puede** hacer, porque «límite» y
«presupuesto» no coinciden en ningún elemento del corpus. **El mecanismo
funciona.**

Pero esa agregación **no es expresable como índice vectorial**: máximo entre
pares exige conservar los vectores de todas las palabras de cada elemento y
compararlas en tiempo de consulta. No es un *embedding* por elemento, es otra
estructura y otro coste. El índice —que es lo que `ADR-002` pide medir— obliga a
un vector por elemento, y ahí solo caben las agregaciones que promedian, que son
las que no funcionan.

---

## 3. Las once omisiones no son un problema, son dos

`N1-31` pide «todas las restricciones esenciales» y espera cinco elementos que
no se parecen entre sí en nada: hablan de presupuesto, de PostgreSQL, de vuelos,
de escalas y de un almacén. **Lo que comparten es *ser* restricciones**, y eso es
una categoría, no un parecido. Ninguna similitud lo captura.

Lo que sí lo captura es la lectura **estructural** que la capa de `ADR002-A` ya
calcula desde hace mucho para `RF-17` y `RF-19` —polaridad negativa y condición
declarada—, y que no se inventó para esto:

| | marcados | de los 5 esperados | ruido |
|---|---|---|---|
| lectura estructural existente | 4 de 41 | **3** | 1 |
| mejor agregación semántica (top-8) | 8 de 41 | 1 | 7 |

Los dos que la lectura estructural no marca son «El presupuesto **máximo**…» y
«…**requiere autorización** previa», es decir un tope y una exigencia: dos
formas de restricción que el detector actual no conoce porque solo mira negación
y condicional.

**Conclusión de esta sección:** parte de las once omisiones pertenece a la señal
**relacional/estructural** —territorio de `ADR002-C`—, no a la semántica. Tratar
las once como un solo problema fue el error de partida, y por eso ninguna señal
única las cierra.

---

## 4. El prototipo, que queda materializado

Aunque el resultado sea negativo, el instrumento queda construido y probado,
porque la hipótesis podrá reabrirse con otro modelo:

| pieza | qué hace |
|---|---|
| `adr002_b/semantica.py` | índice semántico: se construye entero desde el canon, se borra sin residuos, se regenera **idéntico byte a byte**, y falla cerrado ante formato, modelo o canon que no cuadren |
| `adr002_b/codificadores.py` | **el único sitio donde se nombra un modelo.** Un codificador determinista sin dependencias para el ciclo de vida, y los reales con importación perezosa |
| `adr002_b/candidate_semantico.py` | `ADR002-B-SEM`: la base de `A` con la señal semántica **solo en `E3`**, con apertura perezosa del índice |
| `test_adr002_semantica.py` | 12 pruebas que corren en cualquier máquina, sin descargar nada |

**El proveedor queda fuera por construcción.** `semantica.py` habla con un
protocolo de tres miembros y no sabe quién lo implementa; el sidecar guarda
**cuál** modelo lo construyó y **se niega a abrirse con otro** —hay una prueba
que lo comprueba—. Cambiar de modelo es cambiar el objeto que se pasa a
`construir`, y nada más.

**`ADR002-B`, `ADR002-C`, `ADR002-D` y la capa común no se han tocado.** El
candidato nuevo es un módulo aparte precisamente para no obligar a emitir ficha
sucesora antes de saber si la señal servía. El orden fue: primero la evidencia,
después el congelado —que ya no procede—.

### Controles que hacen atribuible el resultado

* **`B-SEM` con la señal apagada da exactamente lo mismo que `ADR002-A`**
  (24/47, 11 omisiones, 3 contaminaciones, 32/46). Sin este control, cualquier
  diferencia podría venir del arnés y no del candidato. Es también una prueba
  automática.
* **Lo que la señal propone pasa por las mismas puertas.** Con umbral −1 propone
  de todo, y nada fuera de ámbito llega a la salida: `G4` lo detiene.
* **La señal solo aporta en `E3`** y el índice **no se abre** cuando `E1`/`E2`
  bastan, comprobado sobre el contador.

---

## 5. Lo que no se hizo, y por qué

| no hecho | motivo |
|---|---|
| Materializar `ADR002-D` = `C` + esta señal | la instrucción lo condiciona a que la señal demuestre utilidad; demuestra lo contrario |
| Tocar corpus, `resultado_esperado`, razones de criticidad o adjudicación | prohibido, y además `§8.1` impide cambiar la medición tras ver resultados |
| Usar `criticidad.razon_segura` | es anotación del banco; usarla es filtrar el oráculo |
| Tabla manual de sinónimos | se descartó incluso como control: para estos casos habría que escribirla mirando las respuestas esperadas, y entonces no mide nada |
| Elegir el mejor punto del barrido | se publica **la curva entera**; quedarse con el mejor tras ver los resultados es lo que `§8.1` prohíbe |
| Abrir un ADR nuevo | prohibido explícitamente |
| Fusionar el PR #117 | prohibido explícitamente |
| **Medir coste y latencia de `B-SEM`** | ver abajo |

### Coste y latencia: no medidos, y por qué

El encargo pedía que un candidato superviviente conservara también **coste y
latencia**. **No los he medido**, y es una omisión deliberada que conviene dejar
escrita en vez de que se note por su ausencia:

* `B-SEM` **no sobrevive** al primer filtro —cierra cero omisiones y degrada
  exactitud—, y la condición era medir eso *después* de sobrevivir;
* la latencia de esta ronda se mide con el protocolo del `§6.8`: once sesiones
  independientes, cien repeticiones y un orden rotado congelado. Ejecutarlo
  contra un candidato ya descartado gastaría el presupuesto de medición en algo
  cuya conclusión no cambiaría.

Lo que sí puede afirmarse sin cronómetro, porque es estructural: el índice
semántico ocupa **196 KiB** para los 97 elementos y su construcción exige cargar
un modelo de 500 000 vectores —**568 MiB** en disco— que hoy ninguno de los
cuatro candidatos necesita. Ese coste es real y habría que contarlo si la
hipótesis se reabriera.

---

## 6. Autorización: lo que haría falta para reabrir esto

No se ha consumido ningún servicio de pago, no se ha seleccionado proveedor
productivo y **ningún dato del corpus ha salido de la máquina**. Los tres
modelos entraron como paquete y se ejecutaron en local.

La hipótesis que queda **sin falsar** es la de un **codificador de frases
afinado para similitud** (familia *sentence-transformers*, `E5`, `LaBSE`). No se
pudo probar aquí por una razón concreta y comprobada:

* `huggingface.co` responde **403 Forbidden** por política del proxy de salida;
* los modelos de esa familia se distribuyen ahí y **no** viajan dentro de
  ningún paquete de PyPI ni de ninguna release de GitHub alcanzable.

**Qué haría falta, exactamente:**

1. **Acceso de lectura a `huggingface.co`** —solo descarga de pesos—, o bien el
   fichero del modelo colocado a mano en la máquina.
2. **Qué datos saldrían: ninguno.** El modelo se ejecuta en local igual que los
   tres probados. La descarga es de entrada; no hay envío.
3. **Coste máximo: cero.** Los modelos de esa familia son de descarga libre. Si
   en su lugar se quisiera un servicio de embeddings de pago, ahí sí habría
   coste y **haría falta autorización aparte**; no se ha hecho ni se propone.
4. **Desacoplamiento: ya resuelto.** Sería una clase más en `codificadores.py`,
   el único fichero que nombra modelos. `semantica.py`, el candidato, el motor y
   las puertas no cambiarían ni una línea.

---

## 7. Qué recomiendo, con lo medido

La evidencia apunta a que **el camino no es un solo tipo de señal**. Las once
omisiones se reparten en dos familias y cada una pide una cosa distinta:

* **sinonimia** (`N1-33`, `N1-30`): la semántica real **sí** la salva —puesto 3
  de 41— pero solo con una agregación que no cabe en un índice vectorial;
* **categoría** (`N1-31`, y parte de `N1-34`): la lectura **estructural** ya
  existente acierta 3 de 5 con un solo falso positivo, y solo le faltan dos
  formas de restricción que hoy no reconoce —el tope y la exigencia—.

La ampliación más barata y más segura que sugiere esta medición es **extender el
detector estructural de `ADR002-A`** a esas dos formas. No necesita modelo, no
necesita red, no necesita proveedor y es auditable línea a línea. **No la he
implementado**: cambiar `adr002_a` obliga a ficha sucesora y a repetir la ronda,
y eso es una decisión de alcance que no me corresponde tomar sola.

---

## 8. Reproducir

```bash
# 1. Entorno aislado; el venv del proyecto queda intacto
uv venv /tmp/venv-sem --python 3.14
VIRTUAL_ENV=/tmp/venv-sem uv pip install --python /tmp/venv-sem/bin/python \
    spacy numpy -e /home/user/sirius
VIRTUAL_ENV=/tmp/venv-sem uv pip install --python /tmp/venv-sem/bin/python \
    "es_core_news_lg @ https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.8.0/es_core_news_lg-3.8.0-py3-none-any.whl"

# 2. El ciclo de vida y los controles, sin modelo y en cualquier maquina
uv run pytest experiments/adr002/candidates/test_adr002_semantica.py -q
```

* Commits: `cf79c78` (invariante `RF-24` y anclas), `ae89ac6` (causa raíz),
  y este paquete.
* Estado de la puerta: Ruff, formato, mypy y las pruebas, **en verde**.

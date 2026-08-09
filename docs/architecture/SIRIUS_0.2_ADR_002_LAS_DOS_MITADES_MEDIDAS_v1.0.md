# SIRIUS 0.2 — ADR-002 · Las dos mitades, medidas

**Versión:** 1.0
**Estado:** **UNA VÍA APROBADA POR MEDICIÓN, UNA APLAZADA CON DATOS**
**Fecha:** 9 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Alcance:** dentro de `ADR-002`. No se abre ningún ADR. No se toca el corpus, ni
`resultado_esperado`, ni las razones de criticidad, ni el motor, ni ningún
candidato congelado. Todo se mide en arnés aparte.

---

## 1. El resultado, en una tabla

Base de comparación: `ADR002-A` sobre los 47 casos adjudicables.

| | exactos | omisiones críticas | contaminación | **fuga de ámbito** | etapa |
|---|---|---|---|---|---|
| **base** | 24/47 | 11 | 3 | 0 | 32/46 |
| **① ampliar la consulta** | **26/47** | **7** | 3 | **0** | **32/46** |
| ② etiquetar, fundido con el texto | 18/47 | **4** | 3 | **3** ⚠️ | 28/46 |
| ③ etiquetar, como señal tardía | 21/47 | 9 | 3 | **1** ⚠️ | 27/46 |
| ④ ampliar + etiquetar tardío | 22/47 | 5 | 3 | 0 | 27/46 |

**Solo la ① mejora sin degradar nada.** Es la única fila que iguala o supera a la
base en las cinco columnas a la vez, y la única con **cero casos que empeoren**.

---

## 2. ① Ampliar la consulta — **aprobada**

Antes de buscar, la pregunta se amplía con sinónimos naturales. No cambia cómo se
guarda nada, no toca el motor, y se apaga con un interruptor.

**Qué arregla, en concreto:**

| pregunta | lo que no encontraba | ahora |
|---|---|---|
| «¿Qué restricciones de transporte tengo?» | «En este viaje no se alquila coche» | ✅ exacto |
| «[interna B05] evidencia de límite de gasto» | «El presupuesto máximo es 1.500 €» | ✅ exacto |

**El punto débil, cuantificado.** Las escribí yo, habiendo visto ya las respuestas
esperadas. Para acotarlo se repitió la medición retirando las siete palabras que
el propio fichero congelado señalaba como sospechosas de estar dirigidas
(`presupuesto`, `tope`, `maximo`, `limite`, `requisito`, `vehiculo`, `coche`):

| | exactos | omisiones | etapa |
|---|---|---|---|
| base | 24/47 | 11 | 32/46 |
| ampliación completa | 26/47 | 7 | 32/46 |
| **sin las palabras sospechosas** | **25/47** | **10** | **33/46** |

**Aun bajo la crítica más dura sigue mejorando**, y la conformidad de etapa incluso
sube. El efecto es real; su tamaño exacto queda pendiente de que las escriba quien
no haya visto el banco —que es lo que hará el modelo de Sirius en producción—.

Congelada antes de medir en `artifacts/adr002_round/ampliacion_de_consulta_v0.1.json`
(commit `5f62f9a`).

---

## 3. ②③ Etiquetar al guardar — **aplazada, con el defecto identificado**

La idea: que Sirius anote «de qué va» cada nota al guardarla, para que las
preguntas de **categoría** —«dame todas mis restricciones esenciales»— dejen de
depender de adivinar al buscar.

### El experimento fue ciego de verdad

Las etiquetas las escribió un agente que recibió **únicamente los 97 textos**,
inline en el encargo, con prohibición expresa de leer nada. **Ejecutó con
`tool_uses: 0`**: no tocó el disco, luego no pudo ver las consultas ni las
respuestas esperadas ni las razones de criticidad.

Y funcionó como mecanismo. Escribió, sin haber visto jamás la pregunta:

| nota | etiqueta escrita a ciegas |
|---|---|
| «El presupuesto máximo del proyecto es 1.500 €» | «**límite de gasto**, tope económico…» |
| «En este viaje no se alquila coche» | «**restricción de transporte**…» |
| «No usar PostgreSQL en este proyecto» | «**restricción tecnológica**…» |

Congeladas antes de medir en `artifacts/adr002_round/etiquetado_en_ingesta_v0.1.json`
(commit `76eca6d`).

### Es lo mejor cerrando omisiones… y aun así no vale

Baja las omisiones de **11 a 4** —ninguna otra vía se acerca— pero:

* **rompe el aislamiento de ámbito** (fuga 3 fundido, 1 como señal tardía), que es
  **fallo duro**: significa devolver algo de otro proyecto;
* cuesta exactitud (24 → 18 fundido, 24 → 21 tardío);
* baja la conformidad de etapa (32 → 28 / 27).

### El defecto, identificado — **y mi primer diagnóstico era falso**

Escribí aquí que el problema eran las etiquetas genéricas: el corpus tiene 40
notas de relleno y el agente las etiquetó a todas casi igual, así que parecía
evidente que inundaban. **Se midió y no era eso.**

Se filtraron las etiquetas por **especificidad** —la noción clásica de frecuencia
documental inversa: un término que comparten `K` o más elementos se descarta— y se
barrió el umbral entero:

| cota | elementos etiquetados | exactos | omisiones | fuga | etapa |
|---|---|---|---|---|---|
| sin etiquetas | 0 | 26/47 | 7 | 0 | 32/46 |
| < 2 (solo términos únicos) | 55 | 22/47 | 5 | 0 | 27/46 |
| < 3 | 55 | 22/47 | 5 | 0 | 27/46 |
| < 5 | 61 | 22/47 | 5 | 0 | 27/46 |
| < 10 | 73 | 22/47 | 5 | 0 | 27/46 |
| < 20 | 95 | 22/47 | 5 | 0 | 27/46 |
| sin filtrar | 95 | 22/47 | 5 | 0 | 27/46 |

**Idéntico en las siete filas.** Descartar cuarenta elementos del etiquetado no
cambia ni un caso. La hipótesis quedó falsada por completo.

### El defecto real

Mirando **qué** casos se pierden, el patrón es inequívoco:

| caso | pregunta | antes | con etiquetas |
|---|---|---|---|
| `N1-11` | «¿Qué sabes del expediente retirado?» | no devolvía nada — **correcto** | devuelve `MEMORIA:11` |
| `N1-18` | «¿Qué dice el anexo técnico requerido?» | no devolvía nada — **correcto** | devuelve dos |
| `N1-24` | «¿Cada cuánto revisamos el alcance?» | no devolvía nada | devuelve uno |
| `N1-36` | variantes fuera de ámbito | no devolvía nada | devuelve tres |
| `N1-48` | — | zanjado antes de expandir | devuelve uno |

**Las etiquetas le quitan a Sirius la capacidad de decir «no tengo eso».** Cada
nota lleva seis etiquetas abstractas —«dato confidencial», «información
incompleta», «norma de proceso»— y con ese vocabulario **cualquier** pregunta
encuentra algo plausible.

Eso no es un problema de precisión: es peor que no encontrar. `RF-25` y `RF-26`
obligan a declarar la ausencia cuando la ausencia es real, y una memoria que
siempre contesta algo está inventando.

### La causa técnica

`FTS5 MATCH` **no puntúa**: o casa o no casa. Con texto real eso rara vez importa
porque casar es difícil; con seis etiquetas abstractas por elemento, casar es
trivial y todo pasa el corte.

### Cuarto diseño: puntuar con `bm25()` y exigir un mínimo — **falsación definitiva**

`bm25()` sí puntúa. Se ordenó por puntuación, se exigió un mínimo, y se barrió el
umbral entero:

| mínimo exigido | exactos | omisiones | contam. | fuga | etapa | **acierta la ausencia** |
|---|---|---|---|---|---|---|
| **sin etiquetas** | **26/47** | **7** | 3 | 0 | **32/46** | **38/47** |
| ≥ 0 | 23/47 | 7 | 3 | 0 | 28/46 | 35/47 |
| ≥ 2 | 23/47 | 7 | 3 | 0 | 28/46 | 35/47 |
| ≥ 4 | 25/47 | 7 | 3 | 0 | 31/46 | 37/47 |
| ≥ 6 | 26/47 | 7 | 3 | 0 | 32/46 | 38/47 |
| ≥ 8 | 26/47 | 7 | 3 | 0 | 32/46 | 38/47 |
| ≥ 10 | 26/47 | 7 | 3 | 0 | 32/46 | 38/47 |
| ≥ 14 | 26/47 | 7 | 3 | 0 | 32/46 | 38/47 |

El arreglo **funciona exactamente como se diseñó**: puntuar y exigir un mínimo
elimina el daño, y a partir de 6 la columna de ausencia vuelve a 38/47.

Pero elimina el daño **eliminando las etiquetas**. De 6 en adelante las cifras
son idénticas, columna por columna, a no tenerlas: ninguna etiqueta llega a
dispararse nunca. Y en el otro extremo, cuando sí se disparan, hacen daño.

**Y la columna que decide: las omisiones se quedan en 7 en las ocho filas.** Las
etiquetas no cierran **ni una sola** omisión adicional en **ningún** punto de
operación. No hay compromiso que buscar: no hay nada que ganar.

### Veredicto: el etiquetado como señal de recuperación queda **falsado**

Cuatro diseños, los cuatro medidos con el banco entero y las puertas reales:

| diseño | resultado |
|---|---|
| ① fundido con el texto indexado | rompe el aislamiento de ámbito (fuga 3) |
| ② señal tardía | cuesta exactitud, fuga 1 |
| ③ filtrado por especificidad | idéntico a ②; **falsó mi diagnóstico del defecto** |
| ④ puntuado con `bm25` y mínimo exigido | o daña, o es inerte; **cero omisiones cerradas en toda la curva** |

Y hay que decir la parte incómoda: **el mecanismo sí funciona** —el agente ciego
escribió «límite de gasto» para «El presupuesto máximo es 1.500 €» sin haber
visto la pregunta—. Lo que no funciona es **usarlo para buscar**. La etiqueta
correcta existe; el buscador no sabe distinguir cuándo esa etiqueta significa
algo y cuándo es ruido, porque la etiqueta no tiene con qué compararse.

Eso apunta a que su sitio, si lo tiene, no es la recuperación sino otro lado
—decidir qué mostrar, o agrupar—, y eso es una pregunta distinta que no se abre
aquí.

**Se para. Cuatro intentos, cuatro medidos, y el tercero además falsó mi propia
explicación del segundo.** Queda escrito para que nadie lo reintente creyendo que
es cuestión de afinar un parámetro: se barrieron todos.

---

## 4. Lo que esto dice de `ADR-002`

Las once omisiones son **dos problemas**, y ahora está medido por partida doble:

| mitad | qué la arregla | evidencia |
|---|---|---|
| **sinonimia** («límite de gasto» ↔ «presupuesto máximo») | ampliar la consulta | ✅ +2 exactos, −4 omisiones, cero regresiones |
| **categoría** («todas mis restricciones») | etiquetar al guardar | ⚠️ −7 omisiones pero rompe ámbito |

Ninguna de las cuatro alternativas de `ADR-002` ataca ninguna de las dos, porque
las cuatro son buscadores de palabras. Eso ya estaba medido; esto lo confirma
desde el otro lado.

---

## 5. Lo que NO se ha hecho, y por qué

| | motivo |
|---|---|
| Implementar la ampliación en Sirius productivo | cambia comportamiento; requiere aprobación explícita |
| Un tercer diseño de etiquetado | la regla dice parar tras dos; el defecto queda escrito para el siguiente |
| Medir latencia y coste | la ampliación añade una llamada al modelo por consulta: hay que medirlo antes de adoptarla |
| Probar el híbrido con `sqlite-vec` | la extensión **funciona aquí** (v0.1.9, KNN real, verificado y refutado sin éxito), pero llenarla exige embeddings, y OpenAI y HuggingFace están bloqueados **desde esta máquina de pruebas** |
| Repetir la ronda oficial | ningún código del experimento cambió |

---

## 6. Reproducir

```bash
uv run python -m experiments.adr002.round.execute_round --help   # el arnes oficial
```

* `artifacts/adr002_round/ampliacion_de_consulta_v0.1.json` — las ampliaciones íntegras
* `artifacts/adr002_round/etiquetado_en_ingesta_v0.1.json` — las 97 etiquetas ciegas
* Ambos congelados **antes** de medir, en commits anteriores a este.

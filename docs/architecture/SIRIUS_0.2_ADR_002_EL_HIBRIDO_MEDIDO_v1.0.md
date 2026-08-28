# Sirius 0.2 · ADR-002 · El híbrido, medido

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

---

## Lo que se hizo, en una frase

Se construyó el motor híbrido que la investigación recomendaba —buscar por palabras y por
sentido a la vez, y fusionar las dos listas por `RRF`—, se congeló **antes** de medirlo, se midió,
y la medida **refutó la razón por la que se había construido**.

---

## 1. El motor

Tres piezas, todas nuevas y ninguna tocando nada congelado:

| pieza | qué hace |
|---|---|
| `hibrido/fusion.py` | La fórmula `RRF`: cada lista aporta `1/(k+puesto)` y los aportes se suman. |
| `hibrido/buscador.py` | El candidato: corre la vía léxica y la semántica en `E3` y las fusiona. |
| `hibrido/codificador_openai.py` | Un tercer codificador detrás del mismo puerto de tres miembros. |

`RRF` no mira las puntuaciones, mira **el puesto**. Es deliberado: el `bm25` de `FTS5` da
negativos sin cota y el coseno da entre −1 y 1; para sumarlos habría que normalizarlos, y eso
exige conocer distribuciones que cambian con cada consulta. Por puesto no hace falta nada de eso,
y además premia **el acuerdo**: algo que sale segundo en las dos listas gana a algo que sale
primero en una y no aparece en la otra.

Trece pruebas, ninguna necesita modelo instalado.

---

## 2. Lo que afirmé al construirlo

> Concatenar condena a la señal semántica a las últimas posiciones. Si la vía léxica llena el
> cupo, lo que la semántica proponga se recorta **antes de que ninguna puerta lo mire**. Medido
> así, un acierto semántico y la ausencia total de señal semántica son indistinguibles.

Sonaba bien. Era falso en este banco.

---

## 3. Lo que dice la medida

**El límite nunca ata.**

| qué se midió | resultado |
|---|---|
| Casos que no declaran límite | **45 de 50** — su límite duro es el canon entero, 97 |
| Casos que sí declaran límite | 5; dos lo fijan al número exacto que su propia respuesta espera |
| Casos que llegan a recorrer `E3` | 21 de 50 |
| Candidatas que `E3` propone | máximo 43, **media 5,1** |
| Casos donde algo añadido al final caería fuera del límite duro | **0 de 21** |

Concatenar no pierde nada aquí. Luego fusionar **no puede ganar nada aquí**.

**Comprobado también por el otro lado.** No basta con decir «la señal estaba callada». Se repitió
el barrido con señal **activa**, umbrales de coseno de 0,25 a 0,65:

- concatenar y fusionar dan **cifras idénticas en los cinco puntos**;
- y salidas idénticas caso a caso, no solo agregados iguales.

La inercia de la fusión no depende de que la señal calle. Aunque proponga, el orden no decide
nada, porque no se recorta nada.

---

## 4. Lo que sí queda establecido

| corrida | exactos | omisiones | contaminación | fuga | etapa | ausencia ok |
|---|---|---|---|---|---|---|
| línea base (solo léxica) | 24/47 | 11 | 3 | 0 | 32/46 | 36/47 |
| híbrido concatenado | 24/47 | 11 | 3 | 0 | 32/46 | 36/47 |
| híbrido fusionado | 24/47 | 11 | 3 | 0 | 32/46 | 36/47 |
| línea base + ampliación | **26/47** | **7** | 3 | 0 | 32/46 | **38/47** |
| híbrido fusionado + ampliación | 26/47 | 7 | 3 | 0 | 32/46 | 38/47 |

1. **El cauce corre entero** sobre el banco real, de punta a punta.
2. **La fusión no mete ruido propio**: con señal nula, salida idéntica a la línea base en los 47
   casos, comparada caso a caso.
3. **La ampliación de consulta sigue siendo lo único que mueve el resultado.**
4. **Queda una sola variable**: si un codificador entrenado para recuperar encuentra lo que los
   tres modelos locales no encontraron.

---

## 5. Por qué el motor se conserva igual

Porque es correcto y no cuesta nada, y porque **la premisa refutada es del banco, no de la
fusión**. En cuanto un límite ate de verdad —un canon grande, una petición acotada, una interfaz
que pida cinco resultados— el recorte vuelve a morder y el orden decide qué sobrevive.

Lo que no se puede es seguir vendiendo la fusión como la solución al problema de ADR-002. No lo
es. La razón refutada se queda **escrita dentro del módulo**: borrarla lo dejaría pareciendo mejor
justificado de lo que está.

---

## 6. Lo que no se metió, y por qué

Se evaluó añadir una extensión de índice vectorial a `SQLite`. **No entra.** La versión disponible
resuelve el vecino más próximo **por fuerza bruta**, exactamente igual que el lector que ya existe:
sobre 97 elementos devuelve el mismo resultado. Solo cambiaría la velocidad, y aquí la búsqueda no
es el coste dominante. A cambio habría que añadir una dependencia binaria y regenerar el fichero
de bloqueo del proyecto. Entra cuando el canon crezca lo bastante para que el coste se note, y
entonces será **otra implementación de la misma lectura**.

---

## 7. Un defecto del arnés congelado, encontrado por accidente

Esto salió solo porque una señal aleatoria propuso algo que ningún candidato había propuesto antes.

**La única identidad global del canon se cuenta como fuga de ámbito** —fallo duro del §6.1— **sin
que ninguna puerta se haya saltado nada**.

- `MEMORIA:1` es `MEM-001`: «El usuario prefiere que redactes en tono directo y sin adornos».
- **La proyección** la trata como global: `project_id` nulo, `ejes.ambito` = `GLOBAL`. Por eso `G4`
  la deja pasar en cualquier ámbito, y lo dice por escrito: «un item global es visible desde
  cualquier ámbito: no pertenece a uno».
- **La métrica** `fuga_de_ambito` numera los proyectos del corpus por su posición. `PRJ-GLOBAL`
  ocupa la primera, así que le asigna el proyecto `'1'` y la considera fuera de ámbito en toda
  consulta acotada a otro proyecto.

Nunca afloró porque ningún candidato de la ronda publicada llegó a entregarla en un caso acotado.

**Por qué importa ahora:** un modelo semántico real puede proponerla con mucha facilidad —es una
memoria de tono, cercana a casi cualquier consulta—. Si lo hace, la corrida marcará fuga de ámbito
y quien lea la cifra concluirá que la vía semántica queda descalificada por fallo duro **cuando no
lo está**.

**Qué se ha hecho:** no se ha tocado la métrica congelada. Sigue contando lo que contaba. El guion
de la corrida separa el recuento en «fuga real» y «fuga por el item global» y lo imprime.

**Qué queda pendiente:** decidir cuál de las dos lecturas es la correcta y corregir la que no lo
sea. Es una decisión sobre el arnés congelado y no se toma sin acto.

---

## 8. Paso 3: lo que hay que ejecutar donde está la clave

```
python -m experiments.adr002.hibrido.medir_con_openai
```

La clave se toma de `OPENAI_API_KEY` o del almacén donde Sirius ya la guarda. **No se escribe en
ningún sitio**: ni en el índice, ni en el artefacto, ni en un mensaje de error.

**Qué sale de la máquina:** los 97 textos del canon experimental y una consulta por caso. El canon
es un corpus **inventado** para medir —faros, viajes, presupuestos de proyectos que no existen—,
no las memorias de nadie. No sale ninguna identidad, ninguna criticidad, ninguna anotación del
banco ni el resultado esperado de ningún caso.

**Qué cuesta:** menos de 150 llamadas cortas. Por debajo de un céntimo.

**Cómo está protegida la medida:**

- el umbral **se barre entero** y se publica la curva completa; elegir después el punto que mejor
  sale sería fijar la medida sobre el resultado, que es lo que el §8.1 prohíbe;
- la corrida **comprueba que reproduce la línea base publicada** (24 exactos, 11 omisiones, 3
  contaminaciones) y avisa en grande si no la reproduce, porque entonces la comparación no vale;
- `resultado_esperado` se usa **solo para puntuar al final**, igual que en todas las rondas.

**Qué hay que traer de vuelta:** un único fichero, `resultado_semantica_real.json`.

El guion se ensayó entero aquí con un codificador sustituto, así que no va a reventar al llegar.

---

## 9. Estado

- PR #117: **abierta y sin fusionar**.
- `ADR002-C`: congelado como línea base, intacto.
- Corpus, `resultado_esperado`, razones de criticidad y adjudicación: **sin tocar**.
- `criticidad.razon_segura`: **no leída**.
- Quality: verde.

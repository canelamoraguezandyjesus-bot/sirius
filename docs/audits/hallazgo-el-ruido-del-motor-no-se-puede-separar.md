# El ruido del motor no se puede separar de la señal — 20-09-2026

Responde a `arranque-de-donde-sale-el-ruido-del-motor.md`, escrita antes de
medir. Determinista, sin Ollama, sobre `main` en `66f11424`, con petición
declarada. 47 llamadas para 47 casos.

## El resultado

```
[17/47 exactos; 162 de mas; 78/81 hallados; criticas=0]

ELEMENTOS DE MAS del motor (110):     ELEMENTOS ESPERADOS del motor (68):
  fts/-/-/proj   106  (96.4%)           fts/-/-/proj    65  (95.6%)
  fts/-/-/-        4  ( 3.6%)           fts/-/-/-        3  ( 4.4%)
```

Las cuatro señales son `fts_match`, `category_match`,
`subject_matches_query`, `project_matches_active`.

**El 96% del ruido y el 96% de la señal entran por la misma puerta y con la
misma combinación exacta**: coincidencia léxica más proyecto activo, sin
categoría y sin asunto.

```
quitar fts/-/-/proj  ->  -106 de mas,  PIERDE 65 esperados
quitar fts/-/-/-     ->  -  4 de mas,  PIERDE  3 esperados
```

## Lo que dice el criterio de parada, escrito antes

Decía: hay propuesta concreta si un grupo explica >= 60% **y** quitarlo no
pierde ninguna crítica ni ningún hallado. El grupo explica el 96.4%, pero
quitarlo **pierde 65 de los 78 hallados**.

Y la regla dura, escrita por encima de todo: *no se propone nada que pierda una
omisión crítica o baje los 78/81 hallados.*

**No hay palanca simple en el motor. La línea se cierra con un negativo
medido.**

## Lo que este negativo enseña, que es más que el negativo

**Con las señales que el motor registra hoy, el ruido y la señal son
indistinguibles.** No es que la puerta esté mal calibrada: es que **no hay nada
en lo que registra que separe los 65 que se quieren de los 106 que no**.

De ahí salen exactamente dos caminos, y ninguno es «afinar el ranking»:

1. **Una señal que el motor hoy no tiene.** Algo que distinga, entre los
   candidatos con coincidencia léxica en el proyecto activo, los que responden
   a la pregunta de los que solo comparten una palabra.
2. **Que discrimine el filtro de relevancia.** Que es exactamente para lo que
   existe, y explica por qué el banco completo con filtro real da 218 elementos
   de más donde la búsqueda sola da 487.

Esto reencuadra el filtro. Deja de ser «la pieza que además mete ruido» y pasa
a ser **la única pieza capaz de separar lo que la búsqueda no puede**. Y su
medición solo se puede hacer con Ollama.

## Contraste con la predicción

| predicción | resultado |
|---|---|
| el grupo dominante será el admitido solo por coincidencia léxica | **acertada en la identidad** |
| ...y será entre el 45% y el 75% de los 110 | **FALLADA** — es el 96.4%, muy por encima de la banda |
| quitarlo pondrá en riesgo elementos hallados (70%) | **ACERTADA** — se lleva 65 de los 78 |

La banda fallada importa: predije un reparto y hay **concentración casi total**.
Eso es peor noticia que lo que esperaba, porque un reparto habría dejado algún
subgrupo separable y la concentración no deja ninguno.

## Y un dato incómodo que estaba escrito antes de medir

Con la petición declarada —el techo de lo que un intérprete perfecto puede
comprar— la búsqueda da **17/47 exactos**. El suelo de D1 es **29/47**.

**Arreglar el intérprete es necesario pero no suficiente.** Aunque fuera
perfecto faltarían 12 aciertos, y este hallazgo dice que no van a salir de
podar el motor.

(Matiz: ese 17/47 es sin filtro. Qué da la petición declarada **con** el filtro
real no se sabe y no se puede saber aquí. Es, hoy, la pregunta abierta más
valiosa del proyecto, y se responde en la máquina del propietario con una sola
orden.)

## Dónde queda el mapa después de las cuatro investigaciones de esta noche

| línea | estado |
|---|---|
| intérprete / cardinalidad | **bloqueada** — necesita §15.2 o que el propietario enuncie el criterio (entrada 119) |
| siembra | **cerrada** — no es el problema, 4.9% con petición declarada (entrada 118) |
| ranking del motor | **cerrada** — negativo medido, ruido y señal inseparables (esta) |
| filtro de relevancia | **abierta, y solo medible en su máquina** |

El trabajo determinista que se podía hacer sin él está hecho. Lo que queda
necesita o una decisión suya o su ordenador.

# De dónde sale la cardinalidad del banco — 20-09-2026

Responde a la nota de arranque
`arranque-de-donde-sale-la-cardinalidad-del-banco.md`, escrita antes de mirar.

## Respuesta corta

**No es el caso de D7 punto 6.** La cardinalidad **sí** procede de una regla
declarada del canon del producto, no de una regex inventada para el fixture.
Así que atacarla tiene sentido — con dos salvedades que salen abajo y que
cambian el alcance de cualquier encargo.

## La cadena de procedencia, con sus citas

1. `peticion_p2` (modo, propósito, permiso, tiempo_objetivo, corte_registro,
   **cardinalidad**, límite) se portó al banco **«sin modificar»** desde
   `cases_v0_5.json` del laboratorio (ADR-111, commit `dfdcdaff` de
   `evidence/adr001-spikes`). No se tocó ningún `caso`, `resultado_esperado`
   ni adjudicación.
2. En el laboratorio, esos valores se derivaron de **B04 §15.2**, «la regla de
   cardinalidad», citada por los informes de preparación del corpus.
3. Solo **1 de los 50 casos** trae la cardinalidad literal en su texto
   canónico; el resto se marcó como **derivado**, no como canónico
   (`INFORME_CORRECCION_CORPUS_v0.2:44`). Hubo un defecto por marcar como
   canónicas las inferidas —`M-07 · cardinalidad y parada inferidas como
   canónicas`— y se cerró.

Esa disciplina es justo lo que faltaba en D7 punto 6: aquí **se distinguió lo
derivado de lo canónico** en vez de pasar una regla mecánica por juicio.

## El criterio del canon, y por qué importa

Dos fuentes independientes dicen lo mismo:

- `INFORME_ENDURECIMIENTO_CORPUS_v0.3:115` — «Cardinalidad `EXHAUSTIVA`
  justificada: **la instanciación cierra el conjunto sobre el universo
  declarado**».
- `validacion_corpus_v0.4.json` — «**EXHAUSTIVA declaran dominio y cierre
  calculable**».

El canon clasifica por **la forma del conjunto de respuesta**: es `EXHAUSTIVA`
cuando la respuesta cierra un conjunto sobre un dominio declarado.

## El defecto concreto: medimos con un criterio distinto del que pedimos

La instrucción del intérprete
(`src/sirius/adapters/ollama_query_intent_classifier.py:170-174`) define:

```
- EXACTA: la pregunta busca un dato concreto («¿qué formato de informe uso?»).
- ACOTADA: la pregunta pide una cantidad concreta («dame las tres…»).
- EXHAUSTIVA: la pregunta pide todo lo que haya de un tema.
```

Eso es un criterio sobre **la gramática de la pregunta**. El canon usa uno
sobre **la forma de la respuesta**. Son criterios distintos, y el modelo aplica
el nuestro correctamente mientras se le puntúa con el otro. En los dos
sentidos:

| caso | consulta | canon | modelo |
|---|---|---|---|
| CA-08 | «¿Cuál es **el** presupuesto de Beta?» | EXHAUSTIVA | EXACTA |
| CA-17 | «¿Qué política de teletrabajo tenemos en Alfa?» | EXHAUSTIVA | EXACTA |
| CA-14 | «¿De qué se ocupa Juan?» | EXHAUSTIVA | EXACTA |
| CA-50 | «¿Qué **condiciones** de acceso al almacén hay?» | EXACTA | EXHAUSTIVA |
| CA-49 | «¿Hay **algo sobre** mi preferencia de reuniones?» | EXACTA | EXHAUSTIVA |

«¿Cuál es *el* presupuesto?» **es** un dato concreto según nuestra propia
instrucción. El modelo no se equivoca: contesta otra pregunta.

## Salvedad 1 — el techo duro: `ACOTADA` se parte en dos, y una mitad no se puede inferir

Los cinco casos `ACOTADA` no son iguales:

| caso | n | tipo | ¿el número está en la consulta? |
|---|---|---|---|
| CA-38 | 10 | `DURO` | **SÍ** — «máximo 10» |
| CA-44 | 5 | `DURO` | **SÍ** — «máximo duro 5» |
| CA-30 | 3 | `OBJETIVO` | no, pero la consulta **enumera tres cosas** |
| CA-26 | 10 | `OBJETIVO` | **NO** — «Enumera las restricciones esenciales» |
| CA-34 | 10 | `OBJETIVO` | **NO** — «Prepara el contexto de planificación de Alfa» |

Los `DURO` son derivables del texto. Los `OBJETIVO` son **una cuota que el caso
asigna**, no algo que la pregunta diga: que «prepara el contexto» valga 10 es
una **política de producto**, no una inferencia. Ningún intérprete, por bueno
que sea, puede sacar ese 10 de esa frase.

Cualquier encargo sobre cardinalidad tiene que **excluir CA-26 y CA-34 de su
objetivo**, o estará persiguiendo algo imposible. Y qué política fija esos
`OBJETIVO` es **decisión del propietario**, no de un encargo.

## Salvedad 2 — §15.2 no está en el repositorio

Ninguno de los ocho DOCX de `docs/canonical/` contiene «B04» ni
«cardinalidad» (comprobado extrayendo el texto de los ocho). **El documento
que define el criterio de aceptación de un campo central no vive en el
repositorio.** El criterio de arriba viene de dos fuentes secundarias —los
informes de preparación—, no del primario.

No se inventa lo que dice §15.2. Se registra que no consta aquí.

## Corrección de una afirmación mía publicada hoy

En la entrada 114 y en su documento de evidencia escribí que **«`ACOTADA` no
se produce nunca»**. **Es falso.** `CA-38` no aparece en la lista de fallos de
la corrida limpia, lo que significa que el modelo **sí** le asignó `ACOTADA`.
Lo correcto es: de los cinco `ACOTADA`, el modelo acierta el que trae el
número explícito en forma de «máximo N», y falla los otros cuatro.

## Contraste con la predicción

| predicción (escrita antes de mirar) | resultado |
|---|---|
| «es juicio, no regla mecánica de palabras clave» | **ACERTADA** |
| «espero que `ACOTADA` se asignara donde la consulta trae un número explícito» | **FALLADA** — solo 2 de 5; tres son cuota del caso |
| probabilidad de «es mecánica entera»: 30% | no se cumplió, y menos mal |

## Veredicto

**Atacable, con el alcance recortado**: alinear la instrucción del intérprete
con el criterio de §15.2 —forma del conjunto de respuesta, no gramática de la
pregunta— puede atacar los ~13 casos de confusión `EXACTA`/`EXHAUSTIVA`. Los
tres `OBJETIVO` quedan fuera por imposibles, y lo que haya que hacer con ellos
es decisión del propietario.

Pendiente de él, además: que §15.2 entre en el repositorio, o que se registre
que no va a entrar y por qué.

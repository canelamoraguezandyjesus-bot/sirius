# §15.2 encontrado: el encargo del intérprete se desbloquea — 20-09-2026

Corrige y cierra `hallazgo-la-cardinalidad-no-se-deriva-del-conjunto-esperado.md`
(entrada 119), que concluyó que el encargo quedaba bloqueado «hasta que §15.2
entre en el repositorio o el propietario enuncie el criterio».

## La corrección

Escribí que **«§15.2 no está en el repositorio»**. Es **falso, y el error fue
mío por mirar en un solo sitio**: comprobé los ocho DOCX de
`docs/canonical/` en `main` y di el salto a «no está en el repositorio».

Está en la rama `evidence/adr001-spikes`, en
`docs/architecture/canonical_sources/SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`
— B04, el Bloque 04 de Búsqueda y Recuperación, v1.0 **APROBADO**.

La lección, y no es pequeña: **«no está» es una afirmación sobre todo el
repositorio, y yo solo había mirado una rama.** El mismo tipo de salto que la
disciplina de este proyecto persigue en todo lo demás.

## El texto literal de §15.2

| Cardinalidad | Definición | Regla de parada |
|---|---|---|
| **EXACTA** | «Busca **uno o varios objetivos identificados** o una **respuesta cerrada**.» | S1 permitido solo cuando todos los objetivos están resueltos y no quedan críticos elegibles pendientes. |
| **ACOTADA** | «Busca **N resultados, una lista definida** o exploración con **límite/criterio explícito**.» | S1 permitido al cumplir la cuota y criterios; la salida declara que no es exhaustiva cuando proceda. |
| **EXHAUSTIVA** | «Busca **todos los elementos que cumplen una condición**.» | **S1 deshabilitado.** Deben agotarse los espacios autorizados. |

Y §15.3 lo confirma desde el otro lado: S1 «solo para EXACTA o ACOTADA…
**nunca se aplica a EXHAUSTIVA**».

## El par que estaba atascado, resuelto

- **`CA-08`** «¿Cuál es el presupuesto de Beta?» → **EXHAUSTIVA**. «Presupuesto
  de Beta» es **una condición**, y la respuesta son **todos** los elementos que
  la cumplen — son dos, y los dos se esperan.
- **`CA-50`** «¿Qué condiciones de acceso al almacén hay?» → **EXACTA**. Es
  **una respuesta cerrada**, un objetivo identificado.

**El criterio no es singular contra plural. Es determinación contra
extensión**: ¿la pregunta señala objetivos determinados o una respuesta
cerrada, o enuncia una condición cuya extensión completa hay que agotar?

## Qué le falta a nuestra instrucción, campo por campo

`src/sirius/adapters/ollama_query_intent_classifier.py:170-174` dice hoy:

```
- EXACTA: la pregunta busca un dato concreto («¿qué formato de informe uso?»).
- ACOTADA: la pregunta pide una cantidad concreta («dame las tres…»).
- EXHAUSTIVA: la pregunta pide todo lo que haya de un tema.
```

1. **`EXACTA`** pierde «**o varios** objetivos identificados» y pierde «**o una
   respuesta cerrada**». Al reducirlo a «un dato concreto» se convierte en un
   criterio sobre **la cardinalidad gramatical de la pregunta**, que es
   exactamente el error que se mide: el modelo dice EXACTA a lo que suena
   singular y EXHAUSTIVA a lo que suena plural.
2. **`ACOTADA`** pierde «**una lista definida**» y «**criterio explícito**», y
   se queda solo en «pide una cantidad concreta». Por eso el modelo solo la
   produce cuando ve un número.
3. **`EXHAUSTIVA`** dice «todo lo que haya de **un tema**» donde el canon dice
   «todos los elementos que cumplen **una condición**».

## Esto revisa un límite que yo mismo había declarado

En el hallazgo de la cardinalidad escribí que `CA-26` («Enumera las
restricciones esenciales del expediente Gamma») y `CA-34` («Prepara el contexto
de planificación de Alfa») eran **cuota de producto, no inferencia**, y que
había que excluirlas del objetivo de cualquier encargo.

**Con §15.2 delante, eso solo vale para su `limite.n`, no para su
cardinalidad.** «Enumera las restricciones esenciales» encaja en «**una lista
definida** o exploración con **criterio explícito**»: es `ACOTADA` **por el
criterio**, no por traer un número. Lo que sigue sin ser inferible es el 10.

Así que el encargo puede atacar **la cardinalidad de los 47 casos**, y solo el
`limite.n` de los tres `OBJETIVO` queda fuera de su alcance.

## Estado

**El encargo queda DESBLOQUEADO.** El criterio ya no hay que inventarlo ni
pedirlo: está escrito, aprobado y citable con fichero y sección.

Sigue habiendo una decisión del propietario, pero **ya no bloquea el trabajo**:
qué política fija los `limite.n` de los `OBJETIVO`. Y queda una deuda
documental: B04 v1.0 APROBADO, que define criterios de aceptación vivos, vive
en una rama de evidencia y no en `main`.

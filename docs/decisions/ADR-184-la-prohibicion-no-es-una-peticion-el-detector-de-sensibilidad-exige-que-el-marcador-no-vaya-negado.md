# ADR-184 — La prohibicion no es una peticion: el detector de sensibilidad exige que el marcador no vaya negado

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

> **Este ADR es también la nota de arranque de la rama** (ADR-001, skill
> `disciplina-evidencia`). Las secciones «Nota de arranque» y «Criterio de
> parada» se escribieron y se empujaron **antes** de tocar una línea de
> `src/`, y antes de medir nada: el commit que las trae no contiene ningún
> cambio de código.

## Contexto y problema

`_detectar_sensibilidad` (`src/sirius_engine/intent_interpreter.py`) decide si
una orden del propietario tiene que parar y pedir su decisión. Compara cuatro
tuplas de marcadores léxicos contra el texto normalizado de la orden. La
comparación —hoy `_marcador_presente`, una frontera de palabra sobre el texto
entero— responde a una sola pregunta: **¿aparece el marcador?** No a la que
importa: **¿la orden PIDE esa operación?**

Una frase que **prohíbe** la operación contiene exactamente el mismo marcador
que una que la pide. El detector no las distingue, así que el despachador
clasifica la orden como `operacion_destructiva_o_irreversible`, crea el trabajo
en `NEEDS_DECISION` y sale con código 3 sin despachar
(`dispatch_cli.main`, rama `CREAR_Y_ESCALAR`).

Reproducido el 12-09-2026. El run 34726666071 de `despachar-orden.yml` paró con
esa causa sobre una orden cuya única frase sensible era una salvaguarda. El
trabajo quedó anotado en el diario `estado-del-motor` como
`WI-20260912-235558` (commit `e51072e`), sin incidencia detrás. La última frase
de esa orden, literal del diario:

> «No borres ni reescribas ninguna entrada historica del registro: un defecto
> nunca **se borra**, y las cifras fechadas de ADR-174 son evidencia y no se
> tocan.»

El marcador que disparó la puerta es `borra`, dentro de «un defecto nunca se
borra» — una frase que dice justo lo contrario de pedirlo. Comprobado sobre el
árbol de `main` (673b2f4) con el texto literal del diario:

    (<CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE>,
     "el mensaje contiene 'borra': causa operacion_destructiva_o_irreversible")

La misma orden, con la salvaguarda reescrita en términos afirmativos y sin
cambiar su significado, pasó sin tocar el detector y creó la incidencia #597.

El defecto se protege a sí mismo de ser reportado: describirlo en lenguaje
natural obliga a nombrar sus marcadores, y eso vuelve a disparar la puerta. Por
eso la orden que pidió este trabajo (#601) está escrita con rodeos.

## Nota de arranque (ADR-001, antes del primer cambio de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en la
   comparación: `_marcador_presente` recibe el marcador y el texto, y devuelve
   un booleano que **no puede** depender del contexto porque la función no
   mira más que la presencia. El arreglo va una capa por encima, en
   `_detectar_sensibilidad`, que sí tiene delante el texto normalizado entero y
   por tanto **puede observar la negación que precede al marcador**. Esa es la
   razón de que el arreglo funcione ahí y no dentro de la comparación: el sitio
   del arreglo ve lo que el sitio del fallo no puede ver.
2. **¿Qué NO va a garantizar esto?** No va a entender la frase. Sigue siendo el
   apaño léxico v0 que ADR-043 declara provisional a la espera del intérprete
   con modelo que pide arquitectura §11. La lista de lo que el criterio nuevo
   **no** detecta se escribe en «Lo que este criterio NO detecta», y se escribe
   entera aunque incomode.
3. **Criterio de parada, decidido ANTES de medir y de ver ningún resultado:**
   - Mido sobre las órdenes que guarda el diario `estado-del-motor` cuántas
     cambian de clasificación con el criterio nuevo, y **reviso a mano, una a
     una, TODAS las que cambien**.
   - **Si alguna de las que dejan de parar pedía de verdad la operación**, el
     criterio queda descartado entero: no se ajusta la ventana ni se parchea la
     lista de negadores. Se para y se escala al propietario con
     `BLOCKED_BY_DECISION`.
   - **Si el criterio nuevo no cambia la clasificación de `WI-20260912-235558`**
     —el caso reproducido—, el criterio no sirve para lo que se pide y se
     descarta.
   - Regla de las dos rondas: dos rondas seguidas con defectos de la misma
     familia → se para y se busca la raíz, no se sigue parcheando.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Un intérprete con
   modelo que entienda la oración; es el [M] de arquitectura §11 y está fuera
   del alcance de esta incidencia. Lo que sí se puede hacer imposible **en el
   nivel léxico** es que el texto que PROHÍBE y el que PIDE produzcan la misma
   clasificación: lo fija una prueba con el texto **literal** de
   `WI-20260912-235558` tomado del diario, no con una paráfrasis cómoda.

## Criterio de parada (escrito ANTES de decidir)

El del punto 3 de la nota de arranque, íntegro. Se publicó en este mismo
fichero, en el commit que abre la rama, antes de medir y antes de escribir
código.

## Decisión

[pendiente: se completa tras la medición]

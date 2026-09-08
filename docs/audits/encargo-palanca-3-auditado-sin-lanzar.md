<!-- Copia de trabajo, NO es un encargo vivo. -->

## Work ID

WI-20260908-P3

## Bloque

ENCARGO

Perfil: implementer@2

## Objetivo

Que el filtro use la cardinalidad que la petición ya trae: con EXACTA n recorta a n, y con EXHAUSTIVA poda por relevancia

## Contexto

Es la **palanca 3 de ADR-148**, la última de las tres, y va detrás de P1 (ADR-164, en `main`), H2 (ADR-166, en `main`) y H1 (ADR-168).

**LA PALANCA 2 NO ENTRA, y esto corrige lo que decían los borradores anteriores de este encargo.** Se cerró el 08-09 con un resultado **medido y negativo**: con el arnés fechado a fondo daba `16/47; 164; 73/81; 0` frente a `17/47; 162; 74/81; 0` de `main`, peor en tres columnas y mejor en ninguna; y con los ejes del corpus puestos, su rama y `main` daban **exactamente lo mismo**, que es lo que probó que el andamiaje ya existe y lo que falta son los ejes. Así que **este encargo NO depende de P2 ni debe esperarla**, y la pregunta que P2 dejó abierta —guardar los ejes en vez de derivarlos— es una decisión de esquema del propietario, fuera de alcance aquí.

**Dos mediciones distintas, y NO se pueden mezclar. Este encargo llevaba la
confusión dentro y la corrijo aquí antes de lanzarlo:**

- `scripts/diagnosticar_busqueda_del_banco.py` imprime `SIN FILTRO`: mide **la
  etapa de búsqueda sin el filtro de relevancia**. Es exactamente **la entrada
  de esta palanca** —lo que el filtro recibe y tiene que podar—, y por eso es
  la línea base correcta para saber de qué se parte.
- **Pero el RESULTADO de esta palanca no se mide ahí**, porque ese diagnóstico
  corre sin filtro y esta palanca ES el filtro. El resultado se mide en la vía
  completa, con `scripts/medir_banco_con_ollama_real.py`.
- Para calibrar: la vía completa publica hoy `29/47; 50; 0; 63/81` y **ya
  alcanza el suelo D1** (`29/47, ≤21, ≤1, ≥63/81`; el `≤21` se cuenta sobre los
  31 casos con contenido). El criterio del propietario para abrir la puerta es
  bastante más estricto que D1.
- **Cualquier cifra que se publique lleva al lado de qué medición sale.**
  Mezclarlas produce números que parecen buenos por comparar poblaciones
  distintas; me pasó el 08-09 y está registrado en la bitácora.

**La línea base NO se hereda escrita: se vuelve a medir al lanzar**, porque `main` se mueve. Como referencia de dónde estaba al redactar esto —medido, no recordado, sobre el head de H1 `2c21f599` con `scripts/diagnosticar_busqueda_del_banco.py`—: suelo `--peticion` = `17/47 exactas; 162 de más; 78/81 hallados; 0 críticas`; techo `--ejes --peticion` = `21/47; 144; 78/81; 0`. Nótese que el `20/47 … 144` que circulaba por documentos viejos ya no es el techo: es `21/47`. La cifra sobre la que se escribe la predicción es la que se mida al empezar, no ésta.

Las «de más» son ruido: elementos recuperados que el caso no pedía. El criterio del propietario para la memoria es **0 de más**, así que ésta es la palanca que tiene que cerrar esa distancia, sea cual sea el número del que parta.

**La cardinalidad y la puerta: comprobado en el árbol, porque este encargo llevaba aquí la misma frase de más que ya falló dos veces en esta línea.** Lo cierto, verificado línea a línea:

- `Peticion` **sí** declara `cardinalidad: Cardinalidad`, `limite_objetivo`, `limite_duro` y `objetivos` (`src/sirius/domain/staged_engine_contracts.py`), y el motor **sí** la honra: `_cardinalidad_semantica` la lee en `src/sirius/domain/staged_engine.py:246-248`.
- **Pero en producción hoy todo llega como `EXHAUSTIVA`.** El intérprete de P1 está cableado (`src/sirius/composition_root.py:541`), y su clasificador se construye **solo si `category_matching_enabled` está abierta**; con la puerta cerrada —el estado por defecto y el que este encargo NO puede cambiar— se construye `InterpreteDePeticion(intent_classifier=None)`, que emite la política uniforme: modo `M1` y **cardinalidad `EXHAUSTIVA` siempre** (`src/sirius/application/rank_relevant_knowledge.py:135-161`).

Dos consecuencias que hay que tener delante desde el primer día:

1. **La rama «EXACTA → recorta a `n`» no se dispara en la producción de hoy.** Se dispara en el laboratorio —que es lo que mide `--peticion`, sustituyendo la política uniforme por la petición real de cada caso— y detrás de la puerta abierta. Eso no invalida el trabajo: la línea entera existe para ganarse esa puerta. Pero significa que **las pruebas tienen que construir la `Peticion` explícitamente**, no confiar en que el camino por defecto traiga una cardinalidad distinta de `EXHAUSTIVA`; si una prueba «pasa» sin construirla, casi seguro no está probando nada.
2. Y significa que **el instrumento de medida correcto es el diagnóstico con `--peticion`**, no una ejecución por el camino ordinario.

Lo que falta, entonces, es que **el filtro use** la cardinalidad para decidir cuánto recortar.

**Y hay una consecuencia de diseño que conviene saber antes de empezar, comprobada en el árbol:** el contrato del puerto es

```python
def filter_candidates(self, query_text: str, candidates: Sequence[RankedKnowledge]) -> Sequence[RankedKnowledge]
```

(`src/sirius/ports/relevance_filter.py:33-35`). **El filtro no recibe la `Peticion`, ni la cardinalidad, ni el límite**: solo el texto de la consulta y los candidatos. Así que esto no es «que el filtro use un dato que ya tiene»: hay que **hacer que el dato le llegue**, y eso toca el contrato del puerto y sus dos llamadas en `src/sirius/application/context.py:372` y `:399`.

Dos límites del contrato que **no** se pueden romper al hacerlo, y que el propio puerto declara: el filtro **decide qué conservar y nunca reordena** —el orden es responsabilidad de `sirius.domain.relevance`—, y **falla abierto**: ninguna implementación propaga una excepción; ante cualquier fallo devuelve los candidatos intactos. Recortar por cardinalidad tiene que respetar las dos cosas, y hay que decir en el ADR cómo se garantiza que un fallo del modelo no acabe recortando por accidente.

## Dónde vive el ruido, medido (para que el trabajo apunte donde pesa)

Reparto de cardinalidad de los 47 casos: **29 EXACTA, 13 EXHAUSTIVA, 5 ACOTADA**. O sea que «recortar a n» aplica a la **mayoría** de los casos, no a un rincón.

Los seis casos con más ruido con `--peticion`, con su cardinalidad al lado. **Medidos el 08-09 y vueltos a medir sobre el head de H1 (`2c21f599`): salen idénticos**, o sea que ni H1 ni H2 mueven el reparto del ruido. El reparto de arriba está **contado** sobre `peticion_p2` del corpus, no recordado:

| caso | de más | cardinalidad |
|---|---|---|
| `B04-CA-17` | 34 | EXHAUSTIVA |
| `B04-CA-28` | 20 | EXHAUSTIVA |
| `B04-CA-35` | 16 | **EXACTA** |
| `B04-CA-34` | 13 | ACOTADA |
| `B04-CA-03` | 12 | EXHAUSTIVA |
| `B04-CA-44` | 8 | ACOTADA |

Dos lecturas, las dos útiles:

- **`B04-CA-35` es EXACTA y trae 16 de más.** El motor ya honra la cardinalidad en su etapa de puertas —`_cardinalidad_semantica`, `parada_por_limite_duro`, `g12.dentro_del_limite` y `omitidos_por_limite`, en `src/sirius/domain/staged_engine.py`—, así que **si un caso EXACTA sale con 16 de más, ahí el recorte no está ocurriendo**. Por qué, hay que averiguarlo y decirlo: es la diferencia entre «el filtro tiene que recortar» y «ya hay un recorte que no se aplica».
- **El ruido gordo está en EXHAUSTIVA** (34 + 20 + 12 de los seis peores), donde por definición **no hay número que recortar**: ahí la única vía es la poda por relevancia, que es la mitad del objetivo de este encargo y la que depende del modelo.

`omitidos_por_limite` es el observable que permite distinguir las dos cosas sin adivinar: si un elemento se fue por el límite, está ahí.

### El reparto COMPLETO de lo que el filtro recibe, no solo los seis peores

Medido sobre el head de H1 (`2c21f599`) con `--peticion`, o sea **la entrada de
esta palanca**: de los 47 casos, **19 no traen ninguna de más** y **28 traen al
menos una**. De esas 28, veintisiete no pierden nada y sus «de más» suman 159,
repartidas así, del caso más ligero al más pesado; la 28ª es `B04-CA-30`, que
trae las 3 restantes hasta 162 y además pierde `MEM-001` (es uno de los tres
casos de decisión, así que su ruido no se cuenta aquí):

```
1 1 1 1 1 1 1  2 2 2 2  3 3 3 3  4 4  5 5 5  6  8  12 13 16 20 34
```

Dos cosas que esto dice y la tabla de los seis peores escondía:

- **Siete casos traen exactamente UNA de más, y quince traen tres o menos.** La
  cola larga no es donde está el volumen, pero **quitar un único elemento
  equivocado y quitar treinta y cuatro no son el mismo problema**: el primero
  se decide ítem a ítem y el segundo es un criterio de corte. Conviene saber
  cuál de los dos se está resolviendo en cada momento.
- **El volumen sí está en la cabeza**: los seis peores (34, 20, 16, 13, 12, 8)
  suman 103 de las 162.

**Lo que NO se puede hacer con estos números, y lo digo porque yo lo intenté**:
traducirlos a una predicción sobre `aciertos_exactos` del suelo D1. Ese `29/47`
se mide en la **vía completa** y estas 162 son de la **etapa de búsqueda**; son
poblaciones distintas y compararlas da números halagadores y falsos. La
predicción de este encargo se escribe sobre la medición **con el filtro
dentro**, y punto.

## Qué hacer

- Con **EXACTA n**: el filtro recorta a n.
- Con **EXHAUSTIVA**: poda por relevancia, sin número fijo.
- Con **ACOTADA**: respeta el límite que la petición declara.

## La medición manda sobre el modelo, y eso está decidido de antemano

La predicción se escribe **después de medir la línea base sobre el `main` del día y antes de ejecutar la medición con Ollama real**, y se publica en el ADR. El objetivo real es **0 de más**; el listón intermedio que este encargo tiene que declarar es a cuánto baja el ruido con `qwen3:4b-instruct` partiendo de la cifra medida. Escribirla sobre las 144 de más sería predecir sobre un número que no es el de partida.

Si el 4B no llega, **el modelo se decide con número, no con opinión**: se mide también con un modelo mayor usando `--modelo` de `scripts/medir_banco_con_ollama_real.py`, y se registran las dos cifras. Esa comparación es un comando en la máquina del propietario, no en CI. Lo que este encargo NO puede hacer es dar por bueno un resultado peor que la predicción sin registrarlo, ni cambiar de modelo sin la medida que lo justifique.

## Casos de aceptación

- Una prueba, vista fallar antes del cambio, que fije que con EXACTA n el filtro devuelve n, y otra que fije que con EXHAUSTIVA no recorta a un número fijo. Deterministas, con un doble del modelo: sin Ollama en CI.
- El comando exacto para la medición con Ollama real, y la predicción escrita ANTES de ejecutarla, sobre la línea base medida: cuánto ruido queda con el 4B, 0 críticas perdidas, y sin bajar ninguna de las otras tres columnas respecto de esa línea base. La cierra el propietario.
- Si el 4B queda por encima de 20 de más, se registra la cifra, se mide el modelo mayor y **se para para decisión del propietario** sobre qué modelo se adopta: el coste de un modelo mayor es suyo, no del ciclo.

## Reglas de evidencia que este encargo hereda del ciclo (deudas 19 y 21)

- **Ninguna afirmación sin la comprobación al lado.** Este borrador se revisó antes de lanzarlo y traía cifras escritas de memoria que el árbol desmintió; si algo de lo de arriba no cuadra con el árbol, **manda el árbol** y la diferencia se registra en vez de acomodarse.
- **La línea base se mide al empezar; no se hereda de otro documento**, ni siquiera de ADR-148.
- **Toda medición que decida si la palanca pasa viene con una contra-medición que aísle el arnés** —corpus, cargador y guiones de recuento—, porque el arnés no tiene guardianes propios (deuda 21). Y si la contra-medición sustituye un dato del arnés, lo sustituye **por ítem y no por una constante**, salvo que se declare por qué la constante basta: una constante hizo infravalorar H2 el 08-09.
- **Ninguna cifra que dependa de `created_at` se publica sin su condición al
  lado** (deuda 27, descubierta el 08-09 en la ronda 2 de H1): en el banco el
  cargador escribe `ejes_p2.valid_from` dentro de `created_at`, así que las dos
  son la misma fecha ítem a ítem y **cualquier predicado sobre `created_at`
  parece medir vigencia y mide registro**. El corpus no declara ninguna fecha
  de registro, así que esto no tiene arreglo dentro del arnés. Esta palanca no
  toca fechas, pero si en el camino aparece una cifra que sí, la condición
  viaja con ella.
- **La sección de validación del ADR** lleva la terna de `pytest`, el código de salida y el ancla al árbol, **actualizada en CADA corrección** (ADR-145, ADR-154, en la forma de ADR-159). Es el defecto más repetido del ciclo: seis rondas en dos encargos.

## Requisitos y pruebas de aceptación

Las validaciones obligatorias de esta incidencia, en verde con UNA SOLA invocación de `scripts/check.ps1`, y **al menos una prueba determinista que fije lo que el objetivo pide y que se haya visto FALLAR antes del cambio** (ADR-001), con su mutación transcrita en el ADR.

Como mínimo:

1. Una prueba, vista fallar, de que con **EXACTA n** el filtro recorta a `n`.
2. Una prueba, vista fallar, de que con **EXHAUSTIVA** no recorta a un número fijo sino que poda por relevancia.
3. Una prueba que fije que el filtro **sigue sin reordenar** —el orden es de `sirius.domain.relevance`— y que **sigue fallando abierto**: ante cualquier fallo interno devuelve los candidatos intactos, nunca una excepción ni un recorte accidental.
4. Una prueba que fije las **0 omisiones críticas**, no solo medirlas.
5. El recuento del banco transcrito **antes y después**, con la línea base medida al empezar y ninguna de sus columnas empeorando salvo las «de más», que es lo que este encargo viene a bajar.

Todas deterministas y con un doble del modelo: **sin Ollama en CI**. Ninguna prueba puede reducirse, saltarse ni falsearse para conseguir verde; si el criterio no se alcanza, se para y se registra.

## Límites

- No se toca el corpus, `resultado_esperado` ni ninguna adjudicación del banco.
- **Nunca se lee ni se indexa `criticidad.razon_segura`.**
- **Ninguna poda puede perder una crítica**: las 0 omisiones críticas son innegociables y hay que fijarlas con una prueba, no solo medirlas.
- La puerta `category_matching_enabled` NO se abre en este encargo: abrirla es la decisión final de la línea y exige los cuatro números del banco bien.
- El adaptador del modelo local sigue siendo localhost-only y fail-open.
- Ni `.github/**` ni ningún workflow cambian.
- Validaciones obligatorias con UNA SOLA invocación de `scripts/check.ps1`, con terna, código de salida y ancla al árbol (ADR-145, ADR-154), en la forma de ADR-159.
- ADR con nota de arranque antes del primer commit de código, y `siguiente_adr.py` re-ejecutado tras `git fetch` justo antes de abrir la PR; si se renumera, cambiar también el TÍTULO de la PR (deuda 18).

## Base y dependencias

ADR-148, ADR-164 (P1: la que hace que la cardinalidad viaje en la `Peticion`), ADR-166 (H2) y ADR-168 (H1). **NO depende de la palanca 2, que se cerró con negativo medido y no entra.** Referencias autorizadas: sesion-cli.

## Alcance permitido

El uso de la cardinalidad en el filtro, sus pruebas y su ADR. Nada más.

## Fuera de alcance

Los huecos H1-H4, abrir la puerta de la memoria, y cualquier cambio no descrito arriba.

## Validaciones obligatorias

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
- `git diff --check <base>..<head>` — **CON EL RANGO, no a secas.** Sin
  argumentos compara solo el árbol de trabajo contra el índice, así que en un
  checkout limpio devuelve 0 aunque el rango confirmado tenga errores de
  espacios: no demuestra nada. Comprobado el 08-09 y señalado por la revisión
  de ADR-168 (CODEX-001). Se transcribe el comando **con las dos revisiones** y
  su código de salida.

## Rama base

main

## Condiciones de parada

- `READY_FOR_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`
- Merge automático prohibido.

## Salvaguardas

- No cambiar Producto, Arquitectura Técnica, ATD ni documentos canónicos sin decisión explícita.
- No hacer push directo a `main`.
- No reducir, saltar ni falsear ninguna prueba para conseguir verde.
- No hacer merge automático: el merge sigue siendo un gesto explícito del propietario (contrato §8, sin cambios).

# ADR-177 — La ampliación por categoría entra por una señal explícita de la petición, no por la subcadena «contexto»

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: el propietario, al fusionar la PR de la incidencia #581.

## Nota de arranque (escrita ANTES de tocar código)

Las cuatro preguntas de ADR-001, decididas antes de ver ningún resultado del
cambio:

1. **¿Qué afirmo?** Que la ampliación por categoría (el bloque `siembra`,
   M20/M14, `rank_relevant_knowledge`) puede pasar a activarse por un campo
   booleano propio de la `Peticion` **sin que cambie ni una de las peticiones
   que hoy la activan**: las 2 del banco (`B04-CA-33` y `B04-CA-34`, únicas
   con propósito `ensamblar_contexto_b05`) y todas las de producción salvo
   las no autorizadas.
2. **¿Con qué lo compruebo?** Con tres pruebas deterministas vistas fallar
   antes del cambio (un propósito con «contexto» y sin señal **no** amplía;
   la señal **sí** amplía con un propósito arbitrario; la traducción del
   banco enciende la señal exactamente para `ensamblar_contexto_b05` y
   `PERMISO_SIN_AUTORIZAR` la apaga) y con el recuento del banco
   `scripts/diagnosticar_busqueda_del_banco.py --peticion` antes y después.
3. **¿Qué resultado me haría estar equivocado?** Que el recuento del banco se
   mueva **en una sola cifra**. Esa es la predicción, publicada aquí antes de
   la segunda medición.
4. **¿Qué queda fuera?** Cambiar qué peticiones activan la ampliación
   (`B04-CA-30`/`MEM-001` es un hueco medido que el propietario decidió el
   12-09-2026 no pagar), abrir `category_matching_enabled`, los ejes y
   cualquier cambio de ranking.

## Criterio de parada (escrito ANTES de decidir)

Si el recuento `--peticion` posterior al cambio difiere del anterior en
cualquiera de sus cuatro cifras, **el cambio no es equivalente** y se para: no
se acomoda el criterio ni se reajusta la tabla cerrada para que cuadre, se
explica caso a caso qué peticion cambió de lado y por qué. Si dos rondas de
revisión traen defectos de la misma familia, se para y se busca la raíz.

## Contexto y problema

**Hueco H4 de ADR-148.** Un camino de recuperación entero —el bloque
`siembra` de `RankRelevantKnowledgeUseCase._rank_via_staged_engine` (M20,
ADR-129), que suma a lo admitido toda identidad no ordinaria del ámbito— se
encendía porque un **texto libre contenía una subcadena**:

- `PROPOSITO_DE_CONTEXTO: Final = "contexto"` y
  `pide_contexto(proposito) -> PROPOSITO_DE_CONTEXTO in proposito.casefold()`
  (`src/sirius/domain/relevance.py`, en el árbol base `433fb11` líneas 160 y
  349-358).
- Un solo consumidor:
  `if self._category_matching_enabled and pide_contexto(peticion.proposito):`
  (`src/sirius/application/rank_relevant_knowledge.py:583`).
- Tres constructores rellenan `Peticion.proposito`: el intérprete
  (`PROPOSITO_RECUPERACION_ORDINARIA = "recuperacion de contexto relevante
  (B6b)"`), la política uniforme (el mismo literal) y la traducción del banco
  (`tests/acceptance/staged_engine_case_translation.py`, que pasa
  `peticion_p2["proposito"]` tal cual).

De ahí salían **dos decisiones que nadie tomó**:

1. **Toda petición de producción amplía**, porque al literal del propósito le
   tocó llevar dentro la palabra «contexto». Si mañana alguien reescribe ese
   literal como «recuperación relevante (B6b)» —una mejora de redacción, sin
   más— la ampliación se apaga en todo el producto sin que ninguna prueba lo
   diga.
2. **`PERMISO_SIN_AUTORIZAR` la apaga**, pero de rebote: la regla del permiso
   vacía el propósito (`proposito_efectivo`) y el vacío no contiene la
   subcadena. Es el comportamiento que se quiere, obtenido por accidente.

En el banco, de los siete propósitos declarados solo `ensamblar_contexto_b05`
contiene «contexto», así que la ampliación se activaba en **2 de 47** casos:
`B04-CA-33` y `B04-CA-34`.

## Decisión

**`Peticion` gana un campo booleano propio, `amplia_por_categoria`, apagado
por defecto, y el consumidor lee ese campo y nada más.** `pide_contexto` y
`PROPOSITO_DE_CONTEXTO` se retiran del dominio: ningún consumidor decide ya
por subcadena sobre texto libre.

Los tres constructores lo fijan, **con el criterio escrito al lado**:

- **La traducción del banco** (`staged_engine_case_translation.py`), por
  **pertenencia** a `PROPOSITOS_QUE_AMPLIAN_POR_CATEGORIA`, una lista cerrada
  cuyo contenido es exactamente `{"ensamblar_contexto_b05"}` — el mismo
  patrón que `_modo`, `_cardinalidad` y los vocabularios de las puertas, y el
  mismo que ADR-170 usó para la pertenencia de `DEC-001` a su lista cerrada.
  Un propósito nuevo no amplía por accidente de redacción: hay que añadirlo
  ahí, y eso es justamente lo que se quiere que cueste.
- **El intérprete y la política uniforme**: **encendida**
  (`AMPLIACION_POR_CATEGORIA_ORDINARIA = True`,
  `_AMPLIACION_DE_LA_RECUPERACION_ORDINARIA`). El porqué, que hasta hoy no
  estaba escrito en ninguna parte: esta política es **uniforme**, no infiere
  intención y declara la misma petición para cualquier consulta, así que lo
  único honesto que puede pedir es la recuperación **más amplia**, dejando el
  recorte a quien sabe recortar —el filtro de relevancia (ADR-125) con el
  rescate RF-25/RF-26 (M19b) y el presupuesto de contexto—. El coste de
  recuperar de más es ruido que el filtro poda; el de recuperar de menos es
  una identidad crítica que no llega nunca.
- **`PERMISO_SIN_AUTORIZAR` la apaga en los dos sitios, ahora
  explícitamente**: `ampliacion_efectiva(permiso, amplia_declarada)` en el
  intérprete y la condición sobre `permiso` en la traducción del banco. Una
  operación que no está autorizada a recuperar tampoco lo está a recuperar
  más — dicho, no deducido de un propósito vacío.

**Lo que esta decisión NO hace: cambiar qué peticiones amplían.** El primer
cuerpo de la incidencia #581 pedía además que `B04-CA-30`
(`responder_al_usuario`) recuperase `MEM-001` sin empeorar ninguna columna
del banco. Medido sobre `main` (`5fc5fdc`) sustituyendo solo la regla de
activación en el consumidor:

| regla | sin ejes | con ejes |
|---|---|---|
| subcadena (la de antes de este ADR) | 17/47; 162; 78/81; 0 | 21/47; 144; 78/81; 0 |
| `responder_al_usuario` o la anterior | 7/47; 309; 79/81; 0 | 8/47; 293; 79/81; 0 |
| siempre | 0/47; 368; 79/81; 0 | 0/47; 352; 79/81; 0 |

`MEM-001` entra en `B04-CA-30` con las dos reglas nuevas, y las dos hunden
los aciertos exactos y disparan los elementos de más: **las dos condiciones
no se pueden cumplir a la vez con una regla de clase de propósito**. El
propietario decidió el 12-09-2026 no pagarlo; `B04-CA-30` queda como hueco
medido, con su precio escrito, reabrible el día que haya una señal más fina
que el propósito.

## Opciones consideradas

1. **Campo booleano explícito en `Peticion`, fijado por quien la construye**
   (la decisión). Hace visible y comprobable lo que hoy es un efecto del
   texto, sin mover una sola petición de lado.
2. **Vocabulario cerrado de propósitos también en producción**, en vez de un
   booleano. Descartada: los tres constructores de producción declaran **un
   solo** propósito, así que el vocabulario tendría un miembro y seguiría
   atando la activación a la redacción de un literal — el mismo defecto con
   otra forma. En el banco sí es lo correcto, porque ahí hay siete propósitos
   declarados por el fixture y la pertenencia es la traducción honesta de lo
   que había.
3. **Dejar `pide_contexto` y encender el campo desde él.** Descartada: no
   retira la decisión por subcadena, solo la esconde un nivel más abajo.

## Comprobación que la sostiene

### 1. Predicción, publicada ANTES de medir

En la nota de arranque de arriba, escrita y **comiteada antes del primer
cambio de código** (`55d6995`): *el banco no se mueve en una sola cifra*.

### 2. Recuento del banco, antes y después

Etapa de búsqueda con peticiones reales y **sin filtro de relevancia**
(`scripts/diagnosticar_busqueda_del_banco.py --peticion`, configuración
`ejes=no peticion=real`). No es comparable con el arnés determinista ni con
la medición con Ollama, que miden otra cosa.

```
$ uv run python scripts/diagnosticar_busqueda_del_banco.py --peticion
# sobre el árbol de 433fb11 (main, antes del cambio)
[ejes=no peticion=real] SIN FILTRO: 17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0
EXIT=0

# sobre el árbol de fa2c6f8 (la rama, con el cambio completo)
[ejes=no peticion=real] SIN FILTRO: 17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0
EXIT=0
```

Las cuatro cifras son idénticas, y también lo es el desglose: `RESUMEN
[ejes=no peticion=real]: distintos no encontrados=3; ocurrencias=3; criticas
perdidas=0 []`, `extras: total=162; media=3.4; casos con 0 extras=19;
peores=[('B04-CA-17', 34, 0), ('B04-CA-28', 20, 0), ('B04-CA-35', 16, 0),
('B04-CA-34', 13, 10), ('B04-CA-03', 12, 0), ('B04-CA-44', 8, 5)]`. La
predicción se cumple y el criterio de parada no se activa.

### 3. Las pruebas, vistas FALLAR antes del cambio (ADR-001)

**Mutación A** — devolver la condición del consumidor a la subcadena:

```python
# src/sirius/application/rank_relevant_knowledge.py
- if self._category_matching_enabled and peticion.amplia_por_categoria:
+ if self._category_matching_enabled and "contexto" in peticion.proposito.casefold():
```

```
$ uv run pytest tests/integration/test_rank_relevant_knowledge.py -k "..." -q
3 failed, 57 deselected in 1.01s
```

Las tres: `test_un_proposito_con_la_palabra_contexto_no_siembra_sin_la_senal`
(el propósito arbitrario «poner el contexto en su sitio» vuelve a sembrar y
el resultado deja de ser vacío),
`test_la_senal_explicita_siembra_sea_cual_sea_el_texto_del_proposito`
(`assert [] == [1]`: con el propósito «consultar» la siembra no aporta nada)
y `test_siembra_seeds_nothing_without_the_explicit_signal` (apagar la señal
deja de apagar la siembra, porque quien decide vuelve a ser el texto).

**Mutación B** — que la traducción del banco no encienda nunca la señal
(`amplia_por_categoria = False and (…)`):

```
$ uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -k "traduccion_enciende or traduccion_apaga" -q
2 failed, 43 deselected in 1.34s
```

`test_la_traduccion_enciende_la_ampliacion_exactamente_en_los_dos_casos_de_contexto`
falla con `set() != frozenset({'B04-CA-33', 'B04-CA-34'})`, y
`test_la_traduccion_apaga_la_ampliacion_sin_permiso` con `assert False is
True` sobre el caso que sí debe ampliar — esa mitad es la que impide que la
prueba del permiso pase por la razón equivocada.

Con el código real, las dos mutaciones revertidas, las cinco pasan.

### 4. Que el conjunto activado es el MISMO, no solo que el recuento no se mueve

`test_la_traduccion_enciende_la_ampliacion_exactamente_en_los_dos_casos_de_contexto`
recorre las **47** filas y compara dos conjuntos calculados en la misma
prueba: el que produce la lista cerrada y el que producía **la regla
retirada** (subcadena sobre el propósito declarado, con el permiso). Son
iguales, y son `{B04-CA-33, B04-CA-34}`. Recorre el banco entero, no los dos
casos nombrados, para fallar también si un tercero se enciende.

### 5. Las 0 omisiones críticas, fijadas y no solo medidas

`_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO: Final[int] = 0`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`), afirmado sobre el
**camino de código real de producción** —`RankRelevantKnowledgeUseCase` /
`ContextBuilder` tal como `composition_root` los construye—, que es
exactamente el que construye la petición con `_peticion_ordinaria` y por
tanto el que esta decisión gobierna. Si la señal se apagara en producción, la
siembra dejaría de rescatar y esa cota rompería. Su gemela del motor portado,
`_MAXIMO_OMISIONES_CRITICAS_MOTOR: Final[int] = 0`, cubre el arnés.

### 6. La prosa que el cambio dejaba falsa (deuda 28)

Corregida en el mismo trabajo, no en otro. Son **once** pasajes de prosa:
nueve docstrings y dos comentarios de documentación Sphinx (`#:`). Diez
están en `src/` y `scripts/`. De esos diez, ocho salen del barrido de esos dos
árboles enteros, y la lista es completa **solo dentro del alcance de ese
barrido**, que es el literal `pide_contexto` —lo que escribe el literal, no lo
que describe el mecanismo sin nombrarlo—: `for f in $(git ls-tree -r
--name-only 433fb11 -- src/ scripts/); do n=$(git show 433fb11:$f | grep -o
'pide_contexto' | wc -l); [ "$n" -gt 0 ] && echo "$n $f"; done` devuelve
exactamente los cuatro ficheros que los contienen:
`scripts/medir_variantes_de_criticidad.py` (1),
`src/sirius/application/interpret_query_request.py` (1),
`src/sirius/application/rank_relevant_knowledge.py` (4) y
`src/sirius/domain/relevance.py` (7). Los **tres** que ese barrido no podía
devolver describían el mecanismo viejo sin nombrar el literal: los encontró la
lectura, no el `grep`. Son el traductor del banco
(`tests/acceptance/staged_engine_case_translation.py`) y, ya en la ronda 11,
los dos de `rank_relevant_knowledge.py` que enumeraban «lo que decide la regla
del producto» dejando fuera la tercera regla: el docstring de módulo (línea 44)
y el de `_peticion` (línea 288), que decían «permiso y propósito por regla del
producto» y ahora dicen «permiso, propósito y ampliación por categoría
(ADR-177)», lo mismo que ya decía el docstring gemelo de
`InterpreteDePeticion.interpretar`. Los **nueve
docstrings** son: el de módulo de `relevance.py` y el de
`RankedKnowledge.seeded`; el de `_rank_via_staged_engine` en
`rank_relevant_knowledge.py`; el de **módulo** de `interpret_query_request.py`
y el de `interpretar` en ese mismo fichero; el de módulo del traductor del
banco (quinta traducción no obvia); y el de módulo de
`scripts/medir_variantes_de_criticidad.py:29-38`, cuyo único cambio en toda
esta PR es justamente ese: decía que la siembra de M20 la activaba «el
PROPÓSITO de la petición (`pide_contexto`)» y ahora dice que la activa la
señal explícita; y los dos de `rank_relevant_knowledge.py` que añade la
ronda 11. Los **dos comentarios de documentación** son los bloques
`#:` que anteceden a `_PROPOSITO_RECUPERACION_ORDINARIA`
(`rank_relevant_knowledge.py:87-106`) y a `PROPOSITO_RECUPERACION_ORDINARIA`
(`interpret_query_request.py:79-91`): no son docstrings —Python no los liga al
objeto, los recoge Sphinx por la sintaxis `#:`— y por eso se cuentan aparte,
aunque para lo que aquí importa hagan el mismo trabajo que un docstring,
declarar por escrito qué hace el literal.

A los once se suman las referencias a `pide_contexto` que las pruebas
escribían sobre el árbol base `433fb11`. Esa cifra sale del mismo
barrido, aplicado a **todo** `tests/` y no a un puñado de ficheros elegidos
—`for f in $(git ls-tree -r --name-only 433fb11 -- tests/); do n=$(git show
433fb11:$f | grep -o 'pide_contexto' | wc -l); [ "$n" -gt 0 ] && echo "$n $f";
done`—, que devuelve ocho ficheros y 53 ocurrencias. De ellas este trabajo
corrige **22**: `tests/unit/test_relevance_domain.py` (13, las cuatro pruebas
de la función retirada se sustituyen por el candado
`test_el_dominio_ya_no_expone_ninguna_regla_de_subcadena_sobre_el_proposito`),
`tests/unit/test_peticion_ordinaria.py` (6),
`tests/integration/test_rank_relevant_knowledge.py` (2) y
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` (1: la línea 284
decía que «para las 47 consultas (M16, ADR-124), `pide_contexto` es cierto
para…», y pasa a decir lo mismo sobre `Peticion.amplia_por_categoria`, con la
mención histórica al mecanismo viejo marcada como tal).

Las **31** restantes se quedan escritas, y aquí está por qué cada una. Son de
**dos clases distintas**, y conviene no mezclarlas:

- **Referencias al experimento** (11): frases cuyo sujeto es
  `experiments/adr002/lateral/categoria.py:_pide_contexto`, la pieza del
  laboratorio que sigue existiendo y sobre la que este cambio no dice nada.
  Son el arnés de examen
  `tests/acceptance/staged_engine_category_and_relevance.py` (8), que replica
  esa pieza y no producción; `tests/automation/test_citas_de_los_adr.py` (2,
  el mapa de citas de esa misma pieza, cuya clave es literalmente esa ruta); y
  `tests/acceptance/fixtures/relevance_filter_frozen_run.json` (1, la nota de
  una corrida congelada, que también nombra esa ruta).
- **Historial inmutable de decisiones sobre producción** (20):
  `tests/automation/fixtures/diario_ola_criticidad.jsonl`, el diario de la ola
  M20. Estas **sí** hablan de producción —el registro de M20 ordena «porta
  `pide_contexto` y `PROPOSITO_DE_CONTEXTO` al dominio
  (`src/sirius/domain/relevance.py`)» y describe el bloque `siembra` con
  `pide_contexto(peticion.proposito)`—, y por eso no valía la categoría que
  esta sección les daba antes. Se quedan escritas por un motivo distinto del
  de las once anteriores: un diario registra lo que se decidió **entonces**,
  no lo que es cierto ahora, y reescribirlo para que cuadre con el código de
  hoy lo destruiría como evidencia. La corrección de ese registro es esta
  ficha, no una edición del diario.

El criterio de conteo es el literal `pide_contexto`; no se suma
`PROPOSITO_DE_CONTEXTO`, que añadiría 2 en `test_peticion_ordinaria.py`. Cada
cifra sale del barrido transcrito arriba sobre el árbol base que esta ficha
declara, no del cuerpo de la incidencia #581: el 14/7/4 que esta sección
transcribía antes no sale de `433fb11` ni de `5fc5fdc`, y esa —heredar una
cifra en vez de re-medirla sobre el árbol declarado— es la raíz común que la
segunda ronda de revisión señaló. El 21 que esta sección transcribió desde la
ronda 3 hasta la 8 tenía la misma raíz en su forma más fina: la cifra sí se
midió sobre `433fb11`, pero sobre tres ficheros elegidos a mano, y se presentó
como si viniera de `tests/` entero. Por eso el barrido va escrito con el árbol
al que se aplica: una lista solo puede declararse completa sobre el alcance
del barrido que la produjo.

Y por eso la ronda 11 añade **cuatro** pasajes de pruebas que este trabajo
también dejaba falsos y que el barrido del literal no podía alcanzar, porque
describen el mecanismo viejo sin escribirlo: el docstring del banco de
evidencia (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:3087-3089`),
gemelo del comentario `#:` que este trabajo sí corrigió 2.800 líneas más arriba
en ese mismo fichero, que atribuía la siembra en las 47 consultas al «mismo
propósito fijo»; el docstring de
`test_produccion_emite_la_peticion_derivada_de_la_consulta_no_la_uniforme`
(`tests/integration/test_rank_relevant_knowledge.py:1839-1841`), que llamaba al
propósito «el que activa la siembra de M20» tres párrafos por encima del
`assert peticion.amplia_por_categoria is True` que este trabajo le añadió; y las
dos concesiones «aunque el propósito declare contexto» de
`test_siembra_never_seeds_an_ordinary_candidate` y
`test_siembra_rejects_a_critico_decision_scoped_to_a_different_project`
(mismas líneas 1394 y 1426 del árbol de la ronda 10), que ahora conceden sobre
la señal. Los cuatro se corrigen a texto, sin mover un assert.

El barrido que los encuentra no es el del literal, y conviene dejar escrito
qué alcance tiene el que sí llega. Sobre el árbol base `433fb11`,
`for f in $(git ls-tree -r --name-only 433fb11 -- src/ scripts/ tests/); do git
show "433fb11:$f" | awk -v f="$f" '{l[NR]=$0} END{for(i=1;i<=NR;i++) if
(tolower(l[i]) ~ /prop[^ ]*sito/){lo=(i>3?i-3:1);hi=(i+3<NR?i+3:NR);w="";for
(j=lo;j<=hi;j++) w=w" " tolower(l[j]); if (w ~ /siembra|amplia|amplía|activa/)
print f":"i}}'; done` devuelve **70** líneas, y los cuatro pasajes de arriba
están entre ellas —igual que el traductor del banco—, pero también decenas que
nada tienen que ver (el «propósito» del despachador del motor, el de
`studio_capture`, el arnés de examen). Es un **localizador para leer**, no un
productor de listas: de sus 70 candidatas solo la lectura separa las que
afirman el mecanismo viejo. Lo que la ronda 11 sí deja cerrado con un criterio
mecánico es la ausencia de atribución causal al propósito:
`grep -rn -E 'prop[oó]sito[^\n]{0,80}(activa|enciende|produce|dispara|hace
que|declara contexto)|(activa|enciende|dispara)[^\n]{0,60}prop[oó]sito'
--include='*.py' --include='*.md' src scripts tests` devuelve sobre el head una
sola línea de este territorio,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:3087`, y ahí el sujeto
es el `peticion_p2.proposito` **del arnés de examen**, que esta PR deja intacto
a propósito y del que la frase sigue siendo cierta.

Ninguna de las 22 se ha relajado. En esos cuatro ficheros quedan escritos sobre
el head **cinco pasajes**, y ninguno afirma ya la regla vieja: el candado de
`tests/unit/test_relevance_domain.py:583-597`, que comprueba que el dominio ya
no expone `pide_contexto` ni `PROPOSITO_DE_CONTEXTO`; y cuatro menciones
históricas dentro de sendos docstrings o comentarios, que cuentan cómo era
antes —`tests/integration/test_rank_relevant_knowledge.py:1672`,
`tests/unit/test_peticion_ordinaria.py:44`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:293` y
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:3093` (esta última la
añade la ronda 11, al marcar como histórica la gemela del docstring del banco)—.
El comando que los **localiza** —no el que produce la cifra— es
`git grep -n 'pide_contexto\|PROPOSITO_DE_CONTEXTO' -- tests/unit tests/integration tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`,
que devuelve **9** líneas sobre el head porque suma los dos literales. Bajo el
criterio de conteo que esta sección declara —el literal `pide_contexto`, sin
sumar `PROPOSITO_DE_CONTEXTO`— las ocurrencias son **7**:
`git grep -c 'pide_contexto' -- tests/unit tests/integration tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
devuelve 3 en `test_relevance_domain.py`, 1 en `test_peticion_ordinaria.py`, 1
en `test_rank_relevant_knowledge.py` y 2 en el banco. Las 7 se agrupan en los
cinco pasajes porque el candado concentra 3 en sus líneas 583-597. Cifra y
comando, con su criterio al lado: es lo que esta sección exige del barrido del
árbol base y no se cumplía aquí.

El arnés de examen
(`tests/acceptance/staged_engine_category_and_relevance.py`) conserva sus ocho
`pide_contexto`: replica
`experiments/adr002/lateral/categoria.py:_pide_contexto`, no producción, y
sus cotas no cambian.

Queda **una** ocurrencia viva que este trabajo deja falsa y que aquí no se
corrige: `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:2053`
escribe, como criterio de aceptación de M16, que «una prueba confirma que el
`proposito` declarado por toda llamada real activa `pide_contexto`». Ese
criterio ya no lo puede cumplir nada: la prueba que lo satisfacía
(`tests/unit/test_peticion_ordinaria.py::test_purpose_activates_pide_contexto_with_or_without_an_active_project`)
pasa en esta PR a llamarse
`test_la_ampliacion_por_categoria_viene_encendida_con_proyecto_activo_y_sin_el`
y afirma sobre `amplia_por_categoria`, y `pide_contexto` ya no existe en
producción. Se deja sin corregir porque la salvaguarda de la incidencia #581
prohíbe cambiar la Arquitectura Técnica sin decisión explícita del
propietario, y no la hay. El día que esa decisión exista, lo que hay que
escribir en la línea 2053 es el criterio equivalente sobre la señal explícita:
que una prueba confirma que toda llamada real construye la petición con
`amplia_por_categoria` encendida, y que una petición construida sin pasar por
`ContextBuilder` no se ve afectada porque la señal la fija `rank()` mismo.

Las otras dos menciones del mismo documento **no** entran, y conviene decir
por qué para que nadie las arrastre a esa corrección: la línea 1625 describe
el `pide_contexto` **del arnés**
(`tests/acceptance/staged_engine_category_and_relevance.py:403-409`), que esta
PR deja intacto a propósito y que por tanto sigue siendo cierta; y la 1633
(«ninguna función de producción llega a inspeccionar con `pide_contexto`») ya
era falsa **antes** de este trabajo, por M20/ADR-129, y lo que este cambio
hace con ella es volverla cierta. La única línea que este trabajo deja falsa
es la 2053.

### Validación obligatoria

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153), con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154). Su
cola va **anclada al árbol sobre el que se corrió**: el de `967a7a20`. Lo que
los commits posteriores añaden sobre ese árbol medido es solo prosa, y aquí va
enumerado para que el ancla sea auditable, porque enunciarlo de menos ya costó
un hallazgo: (1) el commit que transcribe la cola añade, además de la
transcripción que sigue, el reanclado de `beffc7a1` a `967a7a20` en la
explicación de la distancia entre recuentos, doce líneas más abajo en esta
misma sección; (2) la ronda 11 corrige docstrings, comentarios `#:` y esta
ficha —la sección 6, la de alternativas y «La lección»—, sin una sola línea
ejecutable de `src/**` ni de `tests/**`, así que no añade ni retira ningún caso
recolectado y la terna sigue siendo la de su árbol; y (3) el último commit de
la ronda 11 añade la transcripción de la cadena que esa ronda corrió sobre el
árbol de `0878b95f`, la que va más abajo.

```
6391 passed, 17 skipped, 2 xfailed in 477.56s (0:07:57)
EXIT_CODE_CHECK=0
```

La ronda 11 volvió a correr la cadena entera sobre **su** árbol, el de
`0878b95f`, y va anclada igual —no sustituye a la de arriba, la acompaña:

```
6391 passed, 17 skipped, 2 xfailed in 499.27s (0:08:19)
EXIT_CODE_CHECK=0
```

Que la terna coincida al caso es la comprobación de lo que la enumeración de
arriba afirma: la ronda 11 no movió una línea ejecutable, así que no podía
mover el recuento. Lo único que este commit añade sobre el árbol de `0878b95f`
es esta transcripción.

**Esa terna es la de su árbol y no pretende ser la del head vigente**, y ésta
fue la corrección de fondo de la ronda 8: las dos rondas anteriores fallaron por
lo mismo —una con `f6ed801`, la siguiente con `6c248ea`—, y el defecto no
estaba en el SHA elegido sino en la forma de afirmar algo sobre «lo posterior»
a un ancla que esta ficha no controla. Sesiones ajenas a esta vertical empujan
sobre la rama fusiones de `main` que suben el total recolectado sin mover una
línea de H4, y esta ficha no lleva —ni debe llevar— la cuenta de cuántas han
entrado: cualquier recuento escrito aquí lo desmiente la fusión siguiente. Así
que esta sección **no afirma nada sobre los commits que vengan después**. La
regla que sí se sostiene entre fusiones es ésta: la cifra del head publicado es
**la que
reporta la ejecución de Quality de ese head**, y ahí es donde hay que leerla,
no aquí. Para `cea84f1f`, la ejecución de Quality —run 34726068458, conclusión
`success`; es de Quality, no una corrida local de `check.ps1`— reportó
`5461 passed, 17 skipped, 2 xfailed in 509.08s`, cifra que sigue siendo la de
**su** árbol y no la de este head; la de un head posterior será otra y se lee
en su propio run. La distancia entre aquel 5461 y el 6391 de `967a7a20` la
explica entera la tercera fusión de `main` (`a8bb7b6...5ae16624`, ADR-179 con
su `tests/automation/test_piezas_con_llamante.py` parametrizado), que el
compare de abajo ya tiene verificada: ningún fichero de `src/sirius/`,
`tests/unit/`, `tests/integration/` ni `tests/acceptance/`.

Que las fusiones suben la terna **sin tocar H4** sí es comprobable, y conviene
dejarlo escrito porque una ronda anterior lo daba por imposible: ancló
`5392 passed, 17 skipped, 2 xfailed` al árbol de `f6ed801`, anterior a la
primera fusión, y la presentó como vigente. Lo comprobable se enuncia como
**regla**, no como inventario, porque un inventario caduca con la fusión
siguiente igual que caducaba el ancla: **cada fusión de `main` se comprueba en
su propio compare —`gh api
repos/canelamoraguezandyjesus-bot/sirius/compare/<antes>...<después> --jq
'[.files[].filename]'`, donde `<antes>` es el commit de la rama previo a esa
fusión— y ninguno devuelve un solo fichero de `src/sirius/`, `tests/unit/`,
`tests/integration/` ni `tests/acceptance/`**, que es donde está todo lo que H4
cambia. Quien audite un head posterior corre ese compare para la fusión nueva;
esta sección no hay que reescribirla, y no dice cuántas fusiones lleva la rama.

Los compares ya verificados quedan como evidencia **anclada al árbol sobre el
que se corrieron**, no como lista cerrada de lo que la rama ha recibido:

- `f6ed8014...836f2b8d` devuelve `src/sirius_engine/reflect.py`,
  `src/sirius_engine/tablero.py`, `src/sirius_engine/tablero_cli.py`,
  `tests/engine/test_tablero.py`, `tests/engine/test_tablero_cli.py`,
  `tests/automation/test_sirius_comment_upsert.py`,
  `tests/automation/test_serializacion_del_motor.py`,
  `tests/engine/test_reflect.py`, `tests/engine/test_reflect_cli.py`,
  `pyproject.toml`, `scripts/automation/sirius_issue.sh` y
  `.github/workflows/tablero-de-incidencia.yml` —ADR-175 (#588) y ADR-176
  (#589) llegando **desde `main`**—.
- `6c248ea9...cea84f1f` devuelve `MEMORIA.md`, esta ficha, la ficha de
  ADR-180, `scripts/siguiente_adr.py` y
  `tests/automation/test_registro_de_decisiones.py` (+130/−1, cinco pruebas
  nuevas) —ADR-180 (#595) llegando **desde `main`**—.
- `a8bb7b6...5ae16624` devuelve `MEMORIA.md`, la ficha de ADR-179 y
  `tests/automation/test_piezas_con_llamante.py` (+712/−71) —ADR-179 (#593)
  llegando **desde `main`**—.

Ni uno solo de esos ficheros vive en los cuatro directorios de H4. Lo que la
terna mide de más son casos ajenos que entran con la fusión, no cobertura nueva
de esta vertical.

**La base contra la que se mide esta rama no se clava: se calcula.** Es la
base de mezcla del head con `main` —`gh api
repos/canelamoraguezandyjesus-bot/sirius/compare/main...<head> --jq
'.merge_base_commit.sha'`—, que para `cea84f1f` devuelve `f6fa1e68` (ADR-180,
#595) y que la siguiente fusión volverá a mover. Sobre esa base el diff de la
rama es exactamente el trabajo de H4 más `MEMORIA.md`. El desglose de «+3
netos» de más abajo sigue siendo exacto como cuenta de lo que **este trabajo**
aporta sobre su base, con una salvedad que no depende de ningún SHA: en cuanto
la base incluye ADR-174 (#587) —y toda base posterior lo hace—, esta ficha
aporta además un caso parametrizado,
`test_todo_adr_obligado_declara_su_leccion[ADR-177-la-]` de
`tests/automation/test_mina_de_lecciones.py` (`_adr_obligados()` recorre
`docs/decisions/ADR-*.md` y parametriza sobre todo ADR con número
`>= PRIMER_ADR_CON_LECCION`, que es 174, y 177 lo es), así que lo que suma
sobre la base son **+4**, no +3. La duración cambia, como cualquier medición
de reloj en un runner distinto.

La quinta validación, **sobre el rango de la rama y no sin argumentos**
(deuda 25), se corre **sin segunda revisión**: compara contra el **árbol de
trabajo** —el contenido final de la rama, incluida esta misma sección, y no un
head ya superado— la base de mezcla que devuelva `gh api
repos/canelamoraguezandyjesus-bot/sirius/compare/main...<head> --jq
'.merge_base_commit.sha'` **para el head que se consulte**. Es la comprobación
barata que sí puede cubrir el árbol entero, y lo cubre.

La transcripción que sigue va **anclada al árbol sobre el que se corrió** —el
de trabajo de esta ronda— y su argumento es el SHA que aquella llamada
devolvió cuando se capturó, no «la base de este head»: esto último sería falso
en cuanto entrase otra fusión, que es exactamente lo que ya ocurrió una vez con
esta línea. Que siga sirviendo no depende de que el SHA sea la base vigente,
sino de que toda base anterior es antepasado de la vigente y por tanto el rango
cubierto es un **superconjunto** del de la rama —comprobado, no supuesto:
`gh api repos/canelamoraguezandyjesus-bot/sirius/compare/f6fa1e68...673b2f4`
devuelve `status: ahead`, `behind_by: 0` y `merge_base_commit.sha:
f6fa1e6884d558a04fa29c8b72e6c740339bbf2d`—.

```
$ git diff --check f6fa1e68
EXIT=0
```

## Consecuencias

- **Ninguna petición cambia de lado.** Las cuatro cifras del banco son las
  mismas, y el conjunto de casos que amplían es el mismo conjunto, no solo el
  mismo tamaño.
- **Dos decisiones dejan de ser accidentes.** Que producción amplíe siempre y
  que una operación sin autorizar no amplíe están ahora escritas, con su
  porqué, y fijadas por pruebas. Reescribir el literal del propósito ya no
  puede apagar la ampliación en todo el producto.
- **Retirar la subcadena cierra una clase de defecto, no una instancia.** El
  dominio ya no expone ninguna función que decida un camino de recuperación
  leyendo texto libre, y una prueba lo fija por ausencia.
- **El coste está en el banco, no en producción**: añadir un propósito nuevo
  al fixture ya no basta para que amplíe; hay que declararlo en la lista
  cerrada. Es deliberado.
- `B04-CA-30`/`MEM-001` **sigue siendo un hueco**, ahora con su precio medido
  y escrito arriba. Este ADR no lo cierra ni lo empeora.

## Alternativas descartadas y por qué

Las tres de «Opciones consideradas». La que más cerca estuvo es el
vocabulario cerrado también en producción: descartada porque con un único
propósito declarado seguiría atando la activación a la redacción de un
literal, que es exactamente el defecto que H4 viene a cerrar.

De la invocación se transcribe la cola capturada —la terna de `pytest` y el
código de salida—; el `0` solo sale si `ruff format --check .`,
`ruff check .` y `mypy src tests` pasaron antes, porque el guion corta en el
primero que falle (ADR-153). La terna sube de las 5369 que midió `3f9f752`
—el árbol al que ADR-170 ancla esa ejecución; `433fb11` es el commit con el
que aquella rama entró en `main`, y es el **árbol base sobre el que esta ficha
midió** el banco, el barrido de prosa y este delta de 5369 → 5372, no «la base
de la rama»: eso es lo que calcula
`gh api …/compare/main...<head> --jq '.merge_base_commit.sha'` para el head que
se consulte, como ya dice la sección «Validación obligatoria»— a 5372
porque este trabajo añade **tres** casos netos al total recolectado:

- **+2** en `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` (la
  traducción que enciende y la que apaga);
- **+2** en `tests/integration/test_rank_relevant_knowledge.py` (tres
  añadidas —los dos casos de aceptación y el candado de la señal— y una
  retirada, la que pedía un propósito de contexto);
- **+1** en `tests/unit/test_interpret_query_request.py` (la regla escrita
  del intérprete);
- **0** en `tests/unit/test_peticion_ordinaria.py` (dos renombradas, ninguna
  añadida ni retirada: la que fijaba el propósito por la subcadena pasa a
  fijar la señal —`test_la_ampliacion_por_categoria_viene_encendida_con_proyecto_activo_y_sin_el`—
  y el candado estructural
  `test_no_caller_can_override_the_purpose_nor_the_category_widening` extiende
  al campo nuevo lo que ya afirmaba del propósito: que la firma de
  `_peticion_ordinaria` no lo admite como argumento, así que ningún llamante
  puede inyectarlo);
- **−3** en `tests/unit/test_relevance_domain.py` (cuatro retiradas con la
  función, y un candado añadido en su lugar);
- **+1** que no sale de ningún fichero de pruebas: `_adrs()` devuelve
  `REGISTRO.glob("ADR-*.md")` y parametriza
  `test_toda_ruta_citada_por_un_adr_existe`
  (`tests/automation/test_citas_de_los_adr.py:394`), así que esta misma
  ficha añade exactamente un caso recolectado.

+2 de los ficheros de pruebas y +1 de la ficha son los +3 que 5369 → 5372
exigía sobre la base vieja `433fb11`. Sobre la base de mezcla del head
—`f6fa1e68` para `cea84f1f`, y cualquiera posterior, porque todas incluyen ya
ADR-174— son **+4**, porque esta ficha aporta además el caso de
`test_mina_de_lecciones.py` que la sección «Validación obligatoria» desglosa.
Ninguna prueba se ha relajado; ninguna cota del arnés se mueve.

## La lección

- familia: `prosa-que-el-cambio-deja-falsa`
- sin esto se repetiría: retirar un símbolo de producción y dejar vivas las frases que lo daban por cierto; al quitar `pide_contexto` quedaron falsos los once pasajes de prosa que la sección 6 de esta ficha enumera, 22 referencias del literal en las pruebas más otros cuatro pasajes de pruebas que describían el mecanismo sin nombrarlo, y el criterio de aceptación de M16 de la Arquitectura Técnica; y el barrido que las buscó en `scripts/` y `tests/` no miró en `docs/evolution/` ni podía ver lo que no escribe el literal, así que una lista solo se declara completa sobre el alcance del barrido que la produjo y el resto se dice cubierto por lectura.
- lo hace cumplir: ninguna prueba: nada en este repositorio vigila la coherencia de la prosa de `docs/` con el árbol, y la ocurrencia que queda viva está en la Arquitectura Técnica, que la salvaguarda de #581 prohíbe tocar sin decisión del propietario.

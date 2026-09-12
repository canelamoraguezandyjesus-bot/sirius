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

Corregida en el mismo trabajo, no en otro: el docstring de módulo de
`relevance.py` y el de `RankedKnowledge.seeded`; los de
`_PROPOSITO_RECUPERACION_ORDINARIA` y `_rank_via_staged_engine` en
`rank_relevant_knowledge.py`; el de `PROPOSITO_RECUPERACION_ORDINARIA` y el
de `interpretar` en `interpret_query_request.py`; el de módulo del traductor
del banco (quinta traducción no obvia); y las **21** referencias a
`pide_contexto` que las pruebas escribían sobre el árbol base `433fb11`
—`tests/unit/test_relevance_domain.py` (13, las cuatro pruebas de la función
retirada se sustituyen por el candado
`test_el_dominio_ya_no_expone_ninguna_regla_de_subcadena_sobre_el_proposito`),
`tests/unit/test_peticion_ordinaria.py` (6) y
`tests/integration/test_rank_relevant_knowledge.py` (2)—. El criterio de
conteo es el literal `pide_contexto`; no se suma `PROPOSITO_DE_CONTEXTO`, que
añadiría 2 en `test_peticion_ordinaria.py` y daría 23. Cada cifra sale de
`git show 433fb11:<ruta> | grep -o 'pide_contexto' | wc -l` sobre el árbol
base que esta ficha declara, no del cuerpo de la incidencia #581: el 14/7/4
que esta sección transcribía antes no sale de `433fb11` ni de `5fc5fdc`, y esa
—heredar una cifra en vez de re-medirla sobre el árbol declarado— es la raíz
común que la segunda ronda de revisión señaló.

Ninguna se ha relajado. Sobre el head quedan escritas tres menciones y
ninguna afirma ya la regla vieja: el candado de
`tests/unit/test_relevance_domain.py:583-597`, que comprueba que el dominio ya
no expone `pide_contexto` ni `PROPOSITO_DE_CONTEXTO`; y dos menciones
históricas dentro de sendos docstrings, que cuentan por qué la prueba fallaba
antes —`tests/integration/test_rank_relevant_knowledge.py:1670` y
`tests/unit/test_peticion_ordinaria.py:44`—. Medido con
`git grep -n 'pide_contexto\|PROPOSITO_DE_CONTEXTO' -- tests/unit tests/integration`.

El arnés de examen
(`tests/acceptance/staged_engine_category_and_relevance.py`) conserva su
propio `pide_contexto`: replica
`experiments/adr002/lateral/categoria.py:_pide_contexto`, no producción, y
sus cotas no cambian.

### Validación obligatoria

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153), con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154),
anclada **al árbol de `5f1f346`** —el head de la ronda 3 de corrección, con
el código, las pruebas y esta ficha ya corregidas; lo único posterior es esta
misma sección de validación, que no toca código ni pruebas y por tanto no
puede mover la terna—:

```
5372 passed, 17 skipped, 2 xfailed in 716.83s (0:11:56)
EXIT_CODE_CHECK=0
```

La terna no se mueve respecto de la ronda 2 (`393f5aab`, donde midió
`5372 passed, 17 skipped, 2 xfailed in 528.58s`) porque la única prueba que
esta ronda toca es una que ya existía: gana una aserción, no un caso. La
duración sí cambia, como cualquier medición de reloj en un runner distinto.

La quinta validación, **sobre el rango de la rama y no sin argumentos**
(deuda 25), se corre **sin segunda revisión**: así compara la base contra el
**árbol de trabajo**, que es el contenido final de la rama incluida esta
misma sección, y no contra un head ya superado. Es la comprobación barata
que sí puede cubrir el árbol entero, y lo cubre:

```
$ git diff --check 433fb11
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
que aquella rama entró en `main`, y es la base del rango de ésta— a 5372
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
exige. Ninguna prueba se ha relajado; ninguna cota del arnés se mueve.

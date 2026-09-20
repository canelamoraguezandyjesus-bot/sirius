# ADR-203 — El banco mide tambien el camino de puerta cerrada: la linea base que faltaba

- Estado: APROBADO
- Fecha: 2026-09-19
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Nota de arranque (escrita ANTES del primer commit)

Las cuatro preguntas de ADR-001, respondidas antes de tocar nada.

1. **¿Dónde vive el hueco y dónde va el arreglo?** El hueco vive en el
   **instrumento**, no en el sistema medido: `_ejecutar_banco_paquete_completo`
   (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) clava
   `category_matching_enabled=True` en los dos colaboradores, así que el banco
   de 47 casos solo sabe medir el camino ABIERTO. El arreglo va exactamente
   ahí: un parámetro de palabra clave en el arnés y una bandera en
   `scripts/diagnosticar_busqueda_del_banco.py`. El sitio del arreglo **sí**
   puede observar lo que arregla: la ausencia de la cifra de puerta cerrada se
   observa corriendo el propio guion y viendo que no hay forma de pedirla.
   Producción (`rank_relevant_knowledge.py`, `context.py`,
   `composition_root.py`, `memory_gates.py`) **no se toca**: si hiciera falta
   tocarla, esto para con `BLOCKED_BY_DECISION`.
2. **¿Qué NO garantiza esto?** (a) No abre ni cierra ninguna puerta real: los
   valores por defecto de `memory_gates.py` y `settings.json` siguen intactos.
   (b) No dice que el motor «aporte X»: da el minuendo que faltaba, y la resta
   la hace quien registre el umbral de D7 punto 6. (c) La cifra de puerta
   cerrada **no es comparable** con una de puerta abierta sacada con
   `--peticion`, `--ejes` o `--cupo`: en el camino cerrado
   `_rank_via_current_pipeline(query_text)` solo recibe el texto, no hay
   `Peticion`, y esas tres palancas no pueden influir. Por eso el guion
   **rechaza** la combinación en vez de imprimir un número engañoso. (d) No
   mide latencia, ni con Ollama, ni el banco de `test_local_performance.py`.
3. **Criterio de parada (decidido antes de ver ningún resultado).** Paro y no
   sigo empujando si ocurre cualquiera de estas: (i) el recuento del banco con
   `--peticion` deja de ser `17/47; 162; 78/81; 0` después del cambio —eso
   sería haber movido el comportamiento de hoy, que es justo lo que el
   parámetro promete no mover—; (ii) para que el modo nuevo dé un número hace
   falta tocar `src/sirius/application/` o `composition_root.py`
   (→ `BLOCKED_BY_DECISION`); (iii) dos rondas de revisión con defectos de la
   misma familia (ADR-001 §2) → buscar la raíz, no parchear.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** El fallo temido es
   publicar una cifra de puerta cerrada contaminada por banderas que allí no
   pueden actuar. Lo que lo hace imposible no es una nota al pie: es el
   rechazo con código de salida distinto de 0 **antes de medir nada**, con su
   prueba (`tests/automation/test_diagnosticar_busqueda_del_banco.py`). Lo que
   queda solo improbable es que alguien copie a mano una cifra vieja a un
   documento; contra eso solo hay la regla de escribir el comando al lado.

### Predicción, publicada ANTES de medir

No conocemos ninguna de las cuatro cifras del camino cerrado. Escribo lo que
espero y por qué; si sale distinto se registra tal cual y **no** se ajusta la
predicción después de verla.

El camino cerrado es `_rank_via_current_pipeline`: FTS5 + asunto + proyecto
activo, sin índice de categoría, sin índice de criticidad y **sin siembra**.
La comparación honesta es contra la puerta abierta **sin banderas** (ADR-148:
`0/47; 487; 72/81; 0`), que comparte condición —ninguna petición declarada—.

- **Aciertos exactos: 0/47.** Sin siembra y sin categoría es aún más difícil
  clavar el conjunto exacto que con ella; la puerta abierta ya saca 0.
- **Elementos de más: bastantes menos que 487**, en el orden de 150-350. La
  siembra por categoría es lo que mete ruido a paletadas en el camino abierto.
- **Hallados: menos de 72/81**, en el orden de 50-70. Lo que la siembra añade
  de ruido también añade aciertos; al quitarla se pierden algunos.
- **Omisiones críticas: > 0**, probablemente entre 1 y 6. Es la cifra que más
  me inquieta y la razón de medirla: el índice de criticidad
  (`solo_por_criticidad`) solo existe en el camino abierto, así que la puerta
  cerrada no tiene quien rescate una crítica que el orden no alcanza.

## Contexto y problema

ADR-185 partió la puerta única de la memoria en tres interruptores
(`staged_engine_enabled`, `query_intent_enabled`, `relevance_filter_enabled`)
para poder abrirla por pasos y atribuir a cada pieza lo que aporta. Pero el
instrumento con el que se mide —el banco de 47 casos a través de
`_ejecutar_banco_paquete_completo`— solo sabía medir **un** lado de esa puerta:
clavaba `category_matching_enabled=True` a mano en los dos colaboradores
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`), así que las cuatro
cifras que se citan siempre —`17/47; 162; 78/81; 0`— son todas del camino
ABIERTO.

El camino CERRADO es el que ejecuta hoy el Sirius del propietario, porque las
cuatro claves de `src/sirius/config/memory_gates.py` nacen apagadas: con
`category_matching_enabled=False`, `rank_con_cupo` se va por
`_rank_via_current_pipeline` (`src/sirius/application/rank_relevant_knowledge.py`),
el filtro-y-orden de S7.5/M9. De ese camino **no había ninguna medida**. Sin
ella, «el motor aporta X» no se puede afirmar: falta el minuendo.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3: (i) si el recuento del banco con
`--peticion` deja de ser `17/47; 162; 78/81; 0` después del cambio, parar —eso
sería haber movido el comportamiento de hoy—; (ii) si para dar el número hace
falta tocar `src/sirius/application/` o `composition_root.py`,
`BLOCKED_BY_DECISION`; (iii) dos rondas con defectos de la misma familia, buscar
la raíz.

Ninguna se activó: (i) la corrida posterior al cambio es **idéntica byte a
byte** a la anterior (ver abajo), y (ii) no se tocó una sola línea de
`src/`.

## Opciones consideradas

1. **Un parámetro en el arnés y una bandera en el guion** (lo elegido): el
   instrumento aprende a pedir el otro camino; el sistema medido no cambia.
2. **Un guion nuevo que reimplemente el camino cerrado**: se descarta en
   «Alternativas descartadas».
3. **Abrir el interruptor en `settings.json` y medir a mano las dos veces**:
   fuera de alcance —abrir una puerta es una decisión del propietario— y
   además no deja nada reejecutable.

## Decisión

**El instrumento aprende el otro camino; el sistema medido no se toca.**

1. `_ejecutar_banco_paquete_completo` gana `motor_por_etapas: bool = True`. Con
   `False`, los dos colaboradores se construyen como los construye
   `composition_root` con **todas** las claves de `memory_gates.py` apagadas
   —el estado de producción de hoy—: `category_matching_enabled=False`, los dos
   vocabularios vacíos, el techo de criticidad en `None` y
   **`relevance_filter_port=None`**. No es «con `staged_engine_enabled` apagado»
   y nada más: en `composition_root` el caso de uso toma sus tres parámetros de
   `puertas.motor_por_etapas`, pero el `ContextBuilder` toma
   `relevance_filter_port`, `max_criticality_category` y
   `category_matching_enabled`
   de `puertas.filtro_de_relevancia` —la clave que `memory_gates.py` documenta
   como «el filtro de relevancia local y el camino de puerta abierta del
   ContextBuilder»—, así que el parámetro único de este arnés mueve las dos
   claves a la vez. El puerto de relevancia entra en esa lista por **CODEX-001**
   (revisión de la PR #651): la primera versión dejaba puesto el doble
   `_FiltroDeRelevanciaQueNuncaDescarta` también en el modo cerrado, así que
   `_rank_related_knowledge` ejecutaba `_apply_relevance_filter`, una rama que
   la producción cerrada no ejecuta jamás. Que conservara el mismo conjunto era
   una propiedad del doble, no de la construcción que la etiqueta afirmaba
   medir; las cifras coinciden (se vuelven a medir abajo, salida idéntica byte a
   byte), pero ahora las sostiene el cableado fiel y no una coincidencia. Lo que
   sigue limitando lo que la resta puede atribuir es el modo `True`: ver la
   limitación conocida en «Consecuencias».
   El valor por defecto es el comportamiento de hoy, así que ningún llamador
   existente —los tres guiones y las pruebas— cambia de resultado.
2. `scripts/diagnosticar_busqueda_del_banco.py` gana `--puerta-cerrada`, que
   **rechaza la ejecución con código 2, antes de medir nada**, si se combina con
   `--peticion`, `--ejes` o `--cupo`. Por el camino cerrado
   `_rank_via_current_pipeline(query_text)` solo recibe el texto de la consulta:
   no hay `Peticion`, esas tres palancas no pueden influir, y el número saldría
   idéntico al de `--puerta-cerrada` a secas pero pareciendo comparable con uno
   de puerta abierta que sí las usa. El fallo es ruidoso a propósito, no una
   nota al pie.
3. Con `--puerta-cerrada` el guion tampoco construye su propio doble contador
   (CODEX-001): pasa `relevance_filter_port=None`, y el detalle por caso sale de
   `obtenido_por_caso` en vez de las entradas registradas del filtro. Sin filtro,
   lo que devuelve `_rank_related_knowledge` **es** el conjunto tras precedencia
   —el mismo que en puerta abierta entraría al filtro—, así que el detalle dice
   lo mismo y la construcción medida deja de tener una rama de más.
4. Y esa ausencia se comprueba **sobre el argumento real** (CODEX-001, segunda
   vuelta). La primera versión de esta guarda instanciaba el doble contador
   igualmente y miraba luego sus `entradas`: como en modo cerrado ese doble no
   se conecta a nada, sus entradas están vacías **pase lo que pase dentro del
   arnés**, así que la guarda decía «sin filtro» también si el arnés volviera a
   fabricarse el suyo —la regresión exacta de CODEX-001— y el guion habría
   publicado como cerrada una medición que no lo era. Ahora `_medir` envuelve
   `ContextBuilder` con un espía que delega en la clase real y anota qué
   `relevance_filter_port` recibió, y `_incoherencia_del_puerto_de_relevancia`
   —función pura, probada sin medir el banco— rechaza tanto un puerto presente
   como la ausencia de toda observación: sin observación no hay guarda.

## Comprobación que la sostiene

Todo lo de abajo, sobre el árbol de esta rama con el cambio de este encargo
aplicado —base `main` en `3062a31`, `src/` intacto respecto de esa base—. El
ancla no enumera los commits de la rama a propósito: `main` se integra por
squash, así que los SHA de rama no sobreviven a la fusión, y la regla
comprobable que sí sobrevive es «`3062a31` más el diff de este encargo, sin
tocar `src/`».

### La línea base que faltaba

```
uv run python scripts/diagnosticar_busqueda_del_banco.py --puerta-cerrada   # salida 0
[puerta=cerrada] SIN FILTRO: 10/47 exactos; 218 de mas; 57/81 hallados; omisiones criticas=10
```

Vuelta a capturar tras CODEX-001, con el cableado ya fiel (`--puerta-cerrada`
sin filtro de ninguna clase): la salida **completa** del guion —cabecera, las
líneas de detalle y el resumen final— es idéntica byte a byte a la de antes de
la corrección (`diff` de las dos capturas, descontando las líneas `INFO` de
alembic, sin diferencias). Es decir: la cifra que este ADR publica ya no
depende de que el doble conservara el conjunto, y además no cambió al dejar de
depender de ello.

La única corrida que comparte condiciones con ella —misma ausencia de petición
declarada— es la de puerta ABIERTA **sin banderas**. ADR-148 la cita como
`0/47; 487; 72/81; 0`; vuelta a medir aquí en vez de citarla de memoria, sobre
este árbol, sale lo mismo:

```
uv run python scripts/diagnosticar_busqueda_del_banco.py                    # salida 0
[ejes=no peticion=fija] SIN FILTRO: 0/47 exactos; 487 de mas; 72/81 hallados; omisiones criticas=0
```

La comparación honesta, entonces, es esta, y solo esta:

| | puerta CERRADA | puerta ABIERTA, sin banderas |
|---|---|---|
| aciertos exactos | **10/47** | 0/47 |
| elementos de más | **218** | 487 |
| hallados | **57/81** | 72/81 |
| omisiones críticas | **10** | 0 |

Lo que **no** dice esta tabla: que abrir el motor «mejore» o «empeore». Son dos
de las cuatro cifras a favor de cada lado, medidas sin filtro de relevancia
—este guion no ejecuta el filtro, que es quien en producción quita ruido— y sin
petición declarada. El umbral que decide sigue siendo el de D7 punto 6, que no
está registrado y que este ADR no toca. Lo que la tabla da es el **minuendo**
que hasta hoy no existía.

Y lo que tampoco dice: nada sobre `--peticion`, `--ejes` ni `--cupo` en el lado
cerrado. Allí esas palancas no pueden actuar, y por eso el guion ni siquiera
deja pedirlas.

### La predicción, contrastada

La nota de arranque de arriba se escribió antes de medir. Contrastada sin
retocarla:

| | predicho | medido | |
|---|---|---|---|
| aciertos exactos | 0/47 | **10/47** | **fallada** |
| elementos de más | 150-350 | 218 | acertada |
| hallados | 50-70 | 57 | acertada |
| omisiones críticas | 1-6 (`> 0`) | **10** | dirección acertada, rango fallado |

La que más enseña es la primera, y se falló entera. Razoné que sin siembra ni
categoría sería «aún más difícil clavar el conjunto exacto», y es al revés: la
siembra del motor por etapas **añade** elementos a las 47 consultas, así que
rompe el acierto exacto de los casos que el filtro-y-orden ya clavaba. La
puerta cerrada saca 10 exactos porque recupera poco, no porque acierte mejor —
y los 218 contra 487 dicen lo mismo desde el otro lado. La cuarta se falló en
magnitud por la misma razón invertida: sin índice de criticidad nadie rescata
la crítica que el orden no alcanza, y eso cuesta 10 ocurrencias, no 6.

### Identidad: ningún llamador de hoy cambia de resultado

El recuento del banco, con el mismo comando antes y después del cambio:

```
uv run python scripts/diagnosticar_busqueda_del_banco.py --peticion         # salida 0, las dos veces
[ejes=no peticion=real] SIN FILTRO: 17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0
```

No solo coinciden las cuatro cifras: la salida completa del guion —las 47
líneas de detalle incluidas— es **idéntica byte a byte** (`diff -q` de las dos
capturas, sin diferencias), y lo mismo para la corrida sin banderas.

### Las pruebas, vistas FALLAR

**Antes del cambio** (árbol de `3062a31`, con las pruebas nuevas ya escritas):

```
uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -k "puerta_cerrada or los_dos_colaboradores"
→ 2 failed, 1 error: TypeError: _ejecutar_banco_paquete_completo() got an
  unexpected keyword argument 'motor_por_etapas'
uv run pytest tests/automation/test_diagnosticar_busqueda_del_banco.py
→ 1 error: ImportError: cannot import name
  '_BANDERAS_INCOMPATIBLES_CON_PUERTA_CERRADA'
```

**Mutación 1 — el parámetro no llega a `ContextBuilder`** (se deja
`category_matching_enabled=True` en el segundo colaborador y se corrige todo lo
demás):

```
FAILED test_el_estado_de_la_puerta_llega_a_los_dos_colaboradores[False]
       - assert True is False
1 failed, 2 passed
```

Lo que esta mutación enseña, y es la razón de que la prueba de cableado exista
al lado de la de comportamiento: **la prueba de comportamiento la deja pasar**.
Con el motor apagado en el caso de uso, las 47 consultas ya toman el camino
cerrado, y el `category_matching_enabled=True` colgado del `ContextBuilder`
solo cambia qué rama del candado se ejecuta —hoy ni siquiera eso, porque tras
CODEX-001 el modo cerrado no construye filtro y `_apply_relevance_filter` no
llega a llamarse—. Una ejecución así no es ninguno de los dos caminos de
producción, y sin la prueba de cableado se publicaría su cifra creyéndola la de
puerta cerrada.

**Mutación 2 — el parámetro no llega a `RankRelevantKnowledgeUseCase`**:

```
FAILED test_con_el_motor_apagado_el_banco_toma_el_camino_de_puerta_cerrada
       - AssertionError: assert 'MEM-002' not in frozenset({'MEM-001', 'MEM-002'})
FAILED test_el_estado_de_la_puerta_llega_a_los_dos_colaboradores[False]
2 failed, 1 passed
```

**Mutación 4 — el modo cerrado vuelve a recibir el doble de relevancia**
(CODEX-001; se restituye `else _FiltroDeRelevanciaQueNuncaDescarta()` sin
condicionar al estado de la puerta, que es exactamente lo que hacía la primera
versión de esta rama):

```
uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -k dos_colaboradores
FAILED ...::test_el_estado_de_la_puerta_llega_a_los_dos_colaboradores[False]
       - assert <..._FiltroDeRelevanciaQueNuncaDescarta object at 0x7f59db844190> is None
1 failed, 1 passed, 46 deselected
```

Y la lección de esta cuarta es la misma que la de la primera, un nivel más
abajo: la prueba de **comportamiento** también la deja pasar, porque el doble
conserva el conjunto. Solo la prueba de cableado distingue «la construcción de
producción cerrada» de «una construcción que da hoy el mismo número».

**Mutación 5 — la guarda mira un contador desconectado en vez del argumento
real** (en `_medir`, el espía anota `filtro` —que en modo cerrado es `None`—
en lugar de `kw.get("relevance_filter_port")`), que es exactamente lo que
hacía la primera versión de esta guarda:

```
uv run pytest tests/automation/test_diagnosticar_busqueda_del_banco.py -k argumento_real
FAILED ...::test_la_puerta_cerrada_vigila_el_argumento_real_de_context_builder[True]
       - assert None is not None
1 failed, 1 passed, 14 deselected
```

**Mutación 6 — la guarda ve el puerto presente y se calla** (`if presentes:`
pasa a `if False:`):

```
uv run pytest tests/automation/test_diagnosticar_busqueda_del_banco.py -k "guarda or argumento_real"
FAILED ...::test_la_guarda_de_puerta_cerrada_se_queja_de_lo_que_debe[observados1-object]
FAILED ...::test_la_guarda_de_puerta_cerrada_se_queja_de_lo_que_debe[observados2-object]
FAILED ...::test_la_puerta_cerrada_vigila_el_argumento_real_de_context_builder[True]
3 failed, 3 passed, 10 deselected
```

**Mutación 7 — la regresión de CODEX-001, de punta a punta**: se restituye en
el arnés `else _FiltroDeRelevanciaQueNuncaDescarta()` sin condicionar al estado
de la puerta (la mutación 4) y se corre el guion de verdad. Con la guarda
anterior el guion habría terminado en 0 y publicado la cifra como cerrada;
ahora:

```
uv run pytest tests/automation/test_diagnosticar_busqueda_del_banco.py -k mide_la_puerta_cerrada_a_secas
RuntimeError: con la puerta cerrada ContextBuilder no debia recibir filtro de
relevancia, y recibio 1: ['_FiltroDeRelevanciaQueNuncaDescarta']
FAILED ...::test_el_guion_mide_la_puerta_cerrada_a_secas
```

Esta es la que da sentido a las otras dos: la guarda no solo se queja en una
prueba unitaria, sino que **detiene la publicación de la cifra** cuando el
cableado del arnés deja de ser el de producción cerrada.

**Mutación 3 — el guion avisa pero mide igual** (se quita el `return 2` y se
deja el mensaje), vuelta a capturar sobre el árbol de esta ronda:

```
uv run pytest tests/automation/test_diagnosticar_busqueda_del_banco.py -q
FAILED test_el_guion_sale_con_error_y_sin_medir_nada - AssertionError: assert 0 != 0
1 failed, 15 passed
```

Las quince que siguen pasando son justo las que miran el mensaje, la tabla de
banderas y la guarda del puerto: un aviso impecable con código de salida 0 no
detiene a nadie, y esa es la propiedad que la prueba del guion protege. (Eran
nueve antes de que la segunda vuelta de CODEX-001 añadiera las seis pruebas de
la guarda del puerto de relevancia.)

### Validaciones obligatorias

Las cuatro con una sola invocación de `scripts/check.ps1`, y
`git diff --check` con **las dos revisiones**; comandos y códigos de salida
transcritos en la PR.

## Consecuencias

- El banco sabe medir los dos lados de la puerta, y el lado cerrado tiene por
  fin una cifra: `10/47; 218; 57/81; 10`.
- Cuando el propietario abra `staged_engine_enabled`, la comparación se puede
  hacer con el mismo instrumento y el mismo corpus, no con dos mediciones de
  origen distinto.
- **Limitación conocida: el modo `True` no abre solo el primer interruptor.**
  Porque `_ejecutar_banco_paquete_completo` reproduce con un único parámetro dos
  claves de `composition_root` —`motor_por_etapas` en el caso de uso y
  `filtro_de_relevancia` en el `ContextBuilder`—, el modo `True` abre también el
  camino de puerta abierta del `ContextBuilder`, y este encargo **no** entrega un
  tercer modo que reproduzca «solo `staged_engine_enabled` abierto». Lo que hace
  usables las dos cifras publicadas es que en el modo cerrado ese segundo camino
  no existe —`relevance_filter_port=None`, como en `composition_root`
  (CODEX-001)—, no una separación entre las dos claves que el instrumento
  garantice en el modo abierto. Así que la resta entre `0/47; 487; 72/81; 0`
  y `10/47; 218; 57/81; 10` es la distancia entre dos configuraciones completas
  —la producción de hoy contra el paquete completo—, y presentarla sin más como
  «lo que aporta el motor por etapas» sería la familia
  `instrumento-que-solo-mide-un-lado` que ADR-185 existe para evitar. Aislar el
  aporte del motor a solas exige antes un modo del arnés que separe las dos
  claves.
- Nada se abre ni se cierra: `memory_gates.py`, `settings.json`, `STATUS.md` y
  la Arquitectura Técnica quedan como estaban. El umbral de D7 punto 6 sigue
  sin registrar.
- Queda una obligación nueva para quien cite la cifra cerrada: compararla
  **solo** con la corrida sin banderas. El guion hace imposible producirla
  contaminada, pero no puede impedir que alguien la copie a mano al lado de la
  cifra equivocada.

## Alternativas descartadas y por qué

- **Un guion nuevo que reimplemente el camino cerrado.** Reimplementar es medir
  otra cosa: el valor de `_ejecutar_banco_paquete_completo` es que construye los
  colaboradores como los construye `composition_root`, y una copia se desvía en
  cuanto producción cambia. Por eso el parámetro va dentro del arnés y el guion
  lo reutiliza, igual que ya hacía con las tres palancas.
- **Dejar que `--puerta-cerrada --peticion` midiera, con una advertencia
  impresa.** Habría dado un número —el mismo, porque la petición no puede
  influir— con una etiqueta que invita a compararlo con la cifra de puerta
  abierta `--peticion`. La advertencia solo se lee si se lee la salida entera; el
  código de salida distinto de 0 no se puede no ver.
- **Tocar `composition_root` para exponer las dos construcciones y que el arnés
  las llamase.** Es cambiar el sistema medido para poder medirlo, y está fuera
  del alcance del encargo: si hiciera falta, tocaba parar.

## La lección

- familia: `instrumento-que-solo-mide-un-lado`
- sin esto se repetiría: publicar «la pieza X aporta tanto» citando solo la
  cifra del camino con X encendido, porque el instrumento no sabía medir el
  camino sin ella y nadie notó que faltaba el minuendo.
- lo hace cumplir: `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`

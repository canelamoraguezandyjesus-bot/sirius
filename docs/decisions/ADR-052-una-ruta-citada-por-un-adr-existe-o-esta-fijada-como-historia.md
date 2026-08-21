# ADR-052 — Una ruta citada por un ADR existe, o está fijada como historia

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: §5 de `docs/implementation/DONDE_ESTAMOS_2026-08-21.md`, «las cuatro guardas», guarda 4
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-032 y `tests/automation/test_registro_de_decisiones.py` (de donde se copia el patrón de excepción fijada por nombre), ADR-047 (registro de defectos, la guarda 3 de la misma lista)

## Contexto y problema

El método de este repositorio (ADR-001) exige que cada afirmación traiga la
comprobación que la sostiene. Un ADR cumple esa regla citando ficheros: «lo
demuestra `tests/engine/test_governance.py`», «el fallo vivía en
`src/sirius_engine/governance.py`». Esa cita es el puente entre la afirmación y
su prueba.

**El puente se cae solo.** Cuando el código se mueve o un fichero se borra,
nadie vuelve a los ADR a comprobar si sus citas siguen abriéndose. La evidencia
no se contradice: se pudre en silencio. Quien lea el ADR dentro de seis meses
verá una afirmación con una comprobación que ya no puede abrir, y no tendrá
forma de saber si el fichero se movió, si se borró a propósito o si nunca
existió.

No es hipotético. En el árbol de `bbfb625` (el commit en que entró el mapa) había
**tres citas rotas**, y una era del día anterior: ADR-045 citaba
`docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`, que vivía en una rama sin
fusionar y no existía en `main`. La ADR-047 la trajo a `main` un día después,
por otro motivo, y la arregló sin querer. Es exactamente la clase de arreglo con
la que no se puede contar.

## Nota de arranque (ADR-001), con su orden dicho

Cuatro preguntas y criterio de parada. **Honestidad sobre el orden:** la medición
del corpus se hizo ANTES de escribir esto, porque el encargo lo pedía así
(«Primero MIDE»). Lo que se escribió antes de decidir nada —diseño, excepciones,
qué se arregla y qué se fija— es lo que sigue. Vale menos que si el criterio
hubiera precedido también a la medición, y queda dicho en vez de disimulado.

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en los ADR: una
   cita que ya no se abre. El arreglo NO puede vivir ahí —un documento no se
   comprueba a sí mismo—, así que vive fuera, en la batería:
   `tests/automation/test_citas_de_los_adr.py`. Puede observar el fallo que
   arregla porque no depende de que nadie recuerde nada: lee el directorio
   entero de `docs/decisions/`, así que un ADR nuevo queda cubierto el día que
   se escribe.
2. **¿Qué NO garantiza esto?** Cuatro cosas, dichas antes:
   - No comprueba que la cita sea *pertinente*, solo que la ruta exista. Un ADR
     puede citar `src/sirius_engine/gate.py` para algo que ese fichero ya no
     hace, y esta guarda pasa en verde.
   - No comprueba rutas dentro de bloques de código ni de órdenes pegadas: ahí
     hay salidas de comandos, ejemplos y rutas de otras máquinas, y perseguirlas
     es la vía más corta a una prueba que grita en falso.
   - No comprueba nombres de módulo (`domain/work_item.py` sin su `src/...`
     delante), ni ramas (`origin/main`), ni repositorios de terceros
     (`astral-sh/setup-uv`). No sabe distinguirlos con certeza, así que no los
     mira.
   - No mira ningún otro documento del repositorio. Solo `docs/decisions/`.
3. **Criterio de parada (escrito ANTES de decidir el diseño y las excepciones).**
   Esta guarda vale si, y solo si, cumple las tres:
   - **Determinista y sin modelo.** Lee ficheros y comprueba si una ruta existe.
     Si para funcionar hiciera falta que algo razone, no sirve.
   - **Cero falsos positivos en el corpus de hoy.** Sobre los 45 ADR de `main`,
     toda ruta que la prueba señale tiene que estar rota **de verdad**, una por
     una, comprobada a mano. Si aparece una sola señal falsa, se estrecha la
     regla hasta que desaparezca, aunque el precio sea dejar escapar citas rotas
     reales. Una prueba que grita en falso se acaba ignorando, y entonces no
     protege de nada. **Mejor que se escape una cita rota que gritar en falso.**
   - **No vacua.** Meter una cita rota tiene que hacerla fallar; y tiene que
     seguir fallando aunque el corpus real esté limpio, cosa que se comprueba
     con texto sintético dentro de la propia prueba.
4. **¿Qué haría el fallo imposible en vez de improbable?** Esto ya lo hace
   imposible **para la clase que mira**: la prueba corre en Quality sobre el
   árbol fusionado, así que ninguna cita rota —de las que sabe ver— llega a
   `main` en verde. Lo que sigue siendo posible es una cita rota *que la regla
   conservadora no mira* (dentro de un bloque de código, o sin raíz del
   repositorio delante). Eso es una renuncia deliberada, no un descuido: está en
   el punto 2 y es el precio del criterio de parada.

## La medida, antes de decidir nada

Con el barrido **máximo** —todo token con pinta de ruta en cualquier parte del
ADR, incluidos bloques de código y salidas pegadas—, sobre los 45 ADR de `main`
(`450df1b`):

```
$ python3 medir_todo.py          # regla laxa, para saber qué se escapa
rutas_distintas=106 citas=156 rotas=1
  ROTA tests/automation/test_lectura_de_etiquetas.py
       <- ['ADR-027-...-del-objeto-de-la-incidencia.md',
           'ADR-028-...-invariante-permanente.md']
```

Con la regla **conservadora** que se implementa (solo `código en línea` fuera de
bloques, un solo token, con raíz del repositorio delante):

```
$ python3 medir.py
documentos=45 rutas_distintas=97 citas=138 rotas_distintas=1
```

Y sobre el árbol de `bbfb625`, que es el que midió el mapa:

```
$ git archive bbfb625 | tar -x -C <scratchpad>
$ python3 medir_todo_viejo.py
rutas_distintas=103 citas=151 rotas=2
  ROTA docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md  <- [ADR-045]
  ROTA tests/automation/test_lectura_de_etiquetas.py   <- [ADR-027, ADR-028]
$ ls docs/decisions/ADR-*.md | wc -l
44
```

Dos rutas rotas en tres citas, sobre 44 documentos: **44 documentos, 3 citas
rotas**, que es exactamente lo que el mapa dijo. La cifra de citas del mapa (76)
no se reproduce y no se finge que sí: contaba rutas de otra manera. Lo que se
comprueba aquí es la afirmación que importa —cuántas están rotas— y esa sale
igual.

**Hoy en `main` queda una ruta rota, citada por dos ADR.**

### La diferencia entre lo laxo y lo conservador, dicha con número

156 citas ve la regla laxa; 138 ve la conservadora. **Se dejan de mirar 18
citas a propósito** (órdenes tipo `git checkout -- src/...`, rutas dentro de
bloques pegados). Las 18 se comprobaron a mano y **ninguna está rota hoy**, así
que la renuncia no esconde nada ahora mismo; podría esconder algo mañana, y eso
es el precio aceptado en el criterio de parada.

### Que la prueba no gritará en falso en CI

Riesgo real: una ruta que existe en este disco pero no en el clon de Quality
(algo ignorado por git). Se midió una por una, comparando `Path.exists()` con
`git ls-files`:

```
$ python3 tracked.py
fin          ← ninguna discrepancia entre disco y árbol de git
```

Ninguna de las 106 rutas citadas existe solo en el disco. En particular
`.claude/evidencia`, que parecía la sospechosa, está seguida por git
(`.claude/evidencia/.gitignore`, `.claude/evidencia/README.md`).

## Opciones consideradas

1. **No hacer nada** y confiar en que alguien revise las citas al mover código.
   Es lo que hay hoy, y produjo tres citas rotas en 44 documentos.
2. **Comprobar toda ruta que aparezca en cualquier parte del ADR** (la regla
   laxa). Ve 18 citas más. Pero mete dentro las salidas de comandos pegadas y
   las rutas de ejemplo, que es donde vive el falso positivo, y basta uno para
   que la guarda se empiece a ignorar.
3. **Comprobar solo `código en línea` fuera de bloques, con raíz del repositorio
   delante, y fijar por nombre lo borrado a propósito**: elegida.
4. **Arreglar las citas rotas de hoy sin guarda.** Deja el mismo agujero abierto
   para mañana; es justo el arreglo con el que ADR-045 tuvo suerte.

## Decisión

**La tercera.** `tests/automation/test_citas_de_los_adr.py` recorre
`docs/decisions/ADR-*.md` y falla si un ADR cita una ruta del repositorio que no
existe. Una cita solo cuenta si supera **todos** estos filtros, y cada uno está
puesto contra un falso positivo concreto que se vio en el corpus:

| Filtro | Contra qué falso positivo |
|---|---|
| Fuera de los bloques ` ``` ` | salidas de comandos y ejemplos pegados |
| Solo `código en línea` entre acentos graves | prosa que menciona un fichero de pasada |
| Un único token, sin espacios | `git checkout -- src/...`, `uv run pytest tests/... -q` |
| Sin `://`, `*`, `{`, `<` | URLs, globos (`.github/**`), plantillas (`repos/{o}/{r}`) |
| Con raíz del repositorio delante | ramas (`origin/main`, `feat/...`), repositorios de terceros (`astral-sh/setup-uv`), rutas relativas al paquete (`domain/work_item.py`), módulos de Python (`domain/escalation.CausaEscalado`) |
| Sufijos `:123`, `:67-81`, `::test_x` recortados | citas con número de línea o identificador de pytest |

Y **una excepción fijada por nombre**, `BORRADOS_A_PROPOSITO`, con el mismo
patrón que `DUPLICADO_HISTORICO` en `test_registro_de_decisiones.py`: una ruta
borrada a propósito que un ADR cita **como historia**, junto con la lista exacta
de los ADR que pueden citarla. La lista es cerrada: si un ADR nuevo cita esa
ruta, la prueba falla hasta que alguien venga aquí y diga por qué.

### La única excepción de hoy, explicada

`tests/automation/test_lectura_de_etiquetas.py`, citada por **ADR-027** y
**ADR-028**. No se arregla, y no se puede arreglar: el fichero no se movió, se
borró, y **borrarlo es la decisión que ADR-028 registra**.

```
$ git log --oneline --all --diff-filter=ADR -- tests/automation/test_lectura_de_etiquetas.py
a163fc2 Retirar la prohibición del endpoint de etiquetas: la premisa no se sostenía (#188)
0b1e66e Las etiquetas se leen del objeto de la incidencia, no de /issues/{n}/labels (#187)
```

- **ADR-028**, línea 73, es literalmente el acta de la muerte: «**Se borra
  `tests/automation/test_lectura_de_etiquetas.py` entero.**» Exigir que esa ruta
  exista sería exigir que no se hubiera tomado la decisión que el ADR registra.
- **ADR-027**, línea 70, la creó, y ADR-028 decidió expresamente **no
  reescribirla**: «ADR-027 no se reescribe: se le añade un puntero de una línea.
  Borrar el rastro eliminaría justo lo que sirve.» Reescribir la cita ahora
  contradiría esa decisión.

Ninguna otra. No hay más excepciones porque no hay más citas rotas.

## Comprobación que la sostiene

### La prueba primero, vista fallar

Escrita la prueba contra el árbol tal cual está y corrida **antes** de fijar la
excepción (con la lista de borrados a propósito vacía). Salida literal, recortada
al final:

```
$ uv run pytest tests/automation/test_citas_de_los_adr.py -q
E  AssertionError: ADR-028-una-averia-transitoria-no-justifica-una-invariante-
   permanente.md cita rutas que ya no existen:
   ['tests/automation/test_lectura_de_etiquetas.py']. Si el fichero solo se
   movió, actualiza el ADR. Si se borró a propósito y el ADR lo cita como
   historia, añádelo a BORRADOS_A_PROPOSITO explicando por qué.
=========================== short test summary info ===========================
FAILED ...::test_toda_ruta_citada_por_un_adr_existe[ADR-027-las-etiquetas-se-
        leen-del-objeto-de-la-incidencia.md]
FAILED ...::test_toda_ruta_citada_por_un_adr_existe[ADR-028-una-averia-
        transitoria-no-justifica-una-invariante-permanente.md]
FAILED ...::test_toda_ruta_citada_por_un_adr_existe[ADR-052-una-ruta-citada-
        por-un-adr-existe-o-esta-fijada-como-historia.md]
3 failed, 68 passed in 0.15s
```

Tres fallos, uno por ADR que cita el fichero muerto —incluido este mismo, que lo
cita al explicar la excepción—. Con la excepción puesta: `71 passed in 0.12s`.

### Las mutaciones

Seis, y las dos direcciones que exigía el encargo son la 1 y la 2. Las otras
cuatro apuntan al riesgo que de verdad mata a esta guarda, que no es dejar
escapar una cita rota sino gritar en falso:

| # | Mutación | Esperado | Resultado |
|---|---|---|---|
| 1 | Añadir a ADR-001 la cita «src/sirius_engine/no_existe.py» entre acentos graves | falla | **falló**: `1 failed, 70 passed` |
| 2 | Añadir a ADR-001 la cita válida `src/sirius_engine/governance.py` | pasa | **pasó**: `71 passed` |
| 3 | Quitar el filtro de bloques de código | falla | **falló al segundo intento**: ver abajo |
| 4 | Quitar el recorte de sufijos («:95», «::test_x») | falla | **falló**: `10 failed, 61 passed` |
| 5 | Vaciar la lista de borrados a propósito | falla | **falló**: `3 failed, 68 passed` |
| 6 | Sustituir la raíz del repositorio por «lleva una barra» | falla | **falló**: `24 failed, 47 passed` |

**La mutación 3 cazó una prueba vacua, y se cuenta tal cual pasó.** A la primera,
quitar el filtro de bloques **no rompió nada**: el bloque del ADR sintético no
tenía acentos graves dentro, así que no había nada que extraer de él con filtro o
sin él, y `test_una_ruta_dentro_de_un_bloque_de_codigo_no_se_mira` no probaba
nada. No es un caso rebuscado —ADR-039 y este mismo ADR pegan salidas con
acentos graves dentro de un bloque—, así que se corrigió el caso sintético y la
mutación pasó a fallar: `2 failed, 69 passed`. La prueba vale ahora; antes no.

La mutación 6 es la que mide cuánto sujeta el filtro más importante. Sin la raíz
del repositorio delante, **17 de los 46 ADR** darían falso positivo, y estas son
las «rutas rotas» que anunciaría:

```
['origin/main', 'origin/HEAD']                       ← ramas
['astral-sh/setup-uv'], ['actions/cache']            ← repositorios de terceros
['domain/work_item.py', 'ports/notification.py', …]  ← relativas al paquete
['domain/escalation.CausaEscalado']                  ← un módulo, no un fichero
['if/elif'], ['START/STATUS/RESULT/CANCEL']          ← prosa con barra
['/root/.local/share/sirius'], ['docProps/core.xml'] ← fuera del repositorio
```

Esas 17 son la razón de ser del filtro, y la prueba de que el criterio de parada
—cero falsos positivos— no era retórica.

### Determinista y sin modelo

La prueba importa `re`, `pathlib`, `collections.abc` y `pytest`. No sale a la
red, no invoca nada, no lee ninguna variable de entorno, no llama a `git`. Los 71
casos corren en 0,13 s. Seguirá funcionando igual el día en que el ciclo lo mueva
un modelo pequeño y barato.

### Validaciones

```
$ uv run ruff format --check .
432 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 413 source files

$ uv run pytest tests/automation/test_citas_de_los_adr.py -q
71 passed in 0.13s

$ git diff --check --cached
(sin salida)
```

La batería completa **no se corre aquí a propósito**: un intento anterior de esta
tanda murió por falta de memoria (exit 137) al lanzar varias baterías completas a
la vez en el mismo contenedor. La valida Quality sobre el árbol fusionado, que es
donde importa.

## Consecuencias

- Ninguna cita rota **de las que la regla mira** vuelve a llegar a `main` en
  verde.
- Mover un fichero citado por un ADR ahora cuesta actualizar el ADR. Es el coste
  buscado: es exactamente el momento en que la evidencia se estaba pudriendo sin
  que nadie lo notara.
- Borrar un fichero citado por un ADR obliga a decidir en voz alta: o el ADR se
  actualiza, o la ruta entra en `BORRADOS_A_PROPOSITO` con su explicación. Ese
  es el único sitio donde esta guarda pide pensar, y es donde toca.
- La lista de excepciones es cerrada por ADR además de por ruta: un ADR nuevo
  que cite un fichero muerto rompe la prueba. Es fricción a propósito.
- Se acepta que citas rotas dentro de bloques de código o sin raíz del
  repositorio delante sigan pasando. Está en el punto 2 de la nota de arranque y
  medido arriba: 18 citas, ninguna rota hoy.

## Alternativas descartadas y por qué

- **Comprobar también los bloques de código.** Ve 18 citas más y mete dentro las
  salidas pegadas y las rutas de ejemplo. Un solo falso positivo convierte la
  guarda en ruido que se ignora; el criterio de parada lo prohibía por
  adelantado.
- **Adivinar si un fichero se movió y proponer el destino** (por nombre de
  base, por `git log --follow`). Deja de ser determinista en cuanto hay dos
  candidatos, y una guarda que a veces acierta es peor que una que solo señala.
- **Extender la guarda a todo `docs/`.** `docs/implementation/` está lleno de
  documentos de plan que citan a propósito rutas que aún no existen. Sería el
  falso positivo garantizado. Los ADR son distintos: su sección «Comprobación
  que la sostiene» describe algo que **ya** pasó.
- **Ignorar toda ruta borrada, sin lista.** Convierte el borrado en la vía fácil
  para poner la prueba en verde, que es justo el fallo que ADR-047 vino a
  impedir en el registro de defectos.

---

## Adenda (21-08-2026) — la categoría espejo, prevista y colocada en el sitio equivocado

**Este ADR predijo el fallo y se equivocó al decidir a quién le pasaba.** En
«Alternativas descartadas» escribió, para justificar no extender la guarda a
todo `docs/`:

> «`docs/implementation/` está lleno de documentos de plan que citan a propósito
> rutas que aún no existen. Sería el falso positivo garantizado. **Los ADR son
> distintos**: su sección "Comprobación que la sostiene" describe algo que **ya**
> pasó.»

El supuesto duró horas. La primera vez que la guarda corrió sobre un `main` con
todo dentro, falló:

```
ADR-055 cita rutas que ya no existen: ['src/sirius_engine/ports/worker.py']
```

Y ADR-055 cita ese fichero **precisamente para decir que todavía no existe**:

> «no existe todavía ni la puerta que arranca un trabajador (`ports/worker.py`
> no está)»

Ahí la ausencia del fichero no invalida la afirmación: **es** la afirmación.
Exigir que exista sería exigir que el ADR mintiera.

Un ADR **sí** cita rutas futuras, y no en su sección de comprobación: lo hace en
«Consecuencias» y al acotar el alcance, para explicar dónde termina lo que
decide. Eso es exactamente lo que hace un ADR bueno.

### La decisión de la adenda

Se añade `TODAVIA_NO_EXISTEN`, **separada** de `BORRADOS_A_PROPOSITO`, con la
misma forma: ruta → lista cerrada de los ADR autorizados a citarla.

Se separan en vez de reutilizar una sola lista porque no son lo mismo:

| | `BORRADOS_A_PROPOSITO` | `TODAVIA_NO_EXISTEN` |
| --- | --- | --- |
| Historia | existió y se borró | no ha existido nunca |
| Cuándo caduca | nunca: el pasado no cambia | **cuando el fichero se cree** |

Esa segunda fila es lo que hace que fundirlas fuera un error: una excepción de
«todavía no existe» **tiene fecha de caducidad**, y metida en la lista de
borrados sobreviviría en silencio a la creación del fichero, dejando esa ruta
sin vigilar para siempre. Por eso la adenda trae además
`test_una_excepcion_de_todavia_no_existe_se_retira_cuando_el_fichero_nace`: el
día que `ports/worker.py` exista, la batería exige quitar la excepción.

### Lo que esto dice del criterio de parada original

El criterio decía: «mejor que se escape una cita rota que tener una prueba que
grita en falso». Se cumplió — la guarda gritó en falso el primer día, y el
arreglo fue **estrechar** la guarda, no forzar el documento. Lo que faltaba no
era prudencia, era una categoría; y la prueba de que el criterio servía es que
señaló la dirección correcta cuando llegó el caso.

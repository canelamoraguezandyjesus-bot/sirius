# ADR-170 — DEC-001 entra por pertenencia a su lista cerrada: portar los miembros del origen y que G4 decida por pertenencia

- Estado: PROPUESTO
- Fecha: 2026-09-11
- Aprobación: la fusión de esta PR por el propietario.
- Esta ficha es además la **nota de arranque** de la rama (ADR-001, skill
  `disciplina-evidencia`): las cuatro preguntas, el criterio de parada y la
  **predicción** de abajo se escribieron y se publicaron **antes del primer
  commit de código** (commit de esta ficha sola, anterior a cualquier cambio
  en `src/` o en la fixture) y **antes de medir** el resultado.

## Contexto y problema

Hueco **H5 de ADR-148**, incidencia #582 (`WI-20260911-H5`). No lo nombra
ADR-148: se contaba dentro de los cinco de H1, y H1 (ADR-168) demostró
midiendo que la sexta ocurrencia de `B04-CA-22` no era de vigencia sino de
**ámbito**.

El caso es `B04-CA-22` («¿Qué decisiones eran válidas entre enero y marzo?»,
ámbito `PRJ-BETA`). Espera seis decisiones; tras H1 entran cinco y falta
`DEC-001`. Son **dos capas**, y hay que resolver las dos.

### Capa 1: el dato no llega, y existe

`DEC-001` es el único ítem `MULTI_PROYECTO_CERRADO` de los 97 del banco
(`project: LISTA-CERRADA-AB`, `ejes_p2.ambito: MULTI_PROYECTO_CERRADO`). La
fixture no declara miembros de lista cerrada en ningún ítem, y el cargador lo
dice en su propia nota (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia
.py`, `_ejes_declarados`: `miembros_de_ambito=()`). `G4` recibe una lista sin
miembros y se niega con la razón correcta: «lista cerrada sin miembros
resueltos: la duda no abre ambito». La puerta está bien; le falta el dato.

El dato existe, estructurado, en el origen que la propia fixture cita
(`fuente.commit` = `dfdcdaff04dcba10939cc0b0569c55b6a636296f`, rama
`evidence/adr001-spikes`):

```python
# experiments/adr002/benchmark/build_corpus.py:82-88
{
    "id": "LISTA-CERRADA-AB",
    "nombre": "Lista cerrada Alfa+Beta v1",
    "alias": [],
    "tipo": "MULTI_PROYECTO_CERRADO",
    "miembros_lista_cerrada": ["PRJ-ALFA", "PRJ-BETA"],
},
```

Y la adjudicación del origen lo usa así: «pertenece a `LISTA-CERRADA-AB`;
Gamma no es miembro y no hereda» (`cases_v0_5.json`, CA-03, donde `DEC-001`
es señuelo fuera de ámbito). **Portar es restaurar, no inventar**: lo que se
perdió fue al proyectar a JSON (`experiments/adr002/projection/build.py` no
expone la tabla de membresía).

### Capa 2: aunque el dato llegara, `G4` lo excluiría

La rama multiproyecto de `_g4` (`src/sirius/domain/staged_engine_gates.py`)
decidía con `all(peticion.ambito.autoriza(m) for m in miembros)`:
**contención** —«todos los miembros de la lista caben en tu ámbito»—. Lo que
el origen describe es **pertenencia** —«tu ámbito es uno de los miembros»—.

| caso | `all()` | `any()` | lo que el origen adjudica |
|---|---|---|---|
| `B04-CA-22`, ámbito `PRJ-BETA` | False | True | debe entrar |
| ámbito Gamma (CA-03 del origen) | False | False | no debe entrar |

`any` reproduce la adjudicación en los dos sentidos; `all` falla el positivo.
`all` no era un descuido sino una postura de confidencialidad, coherente con
«la duda no abre ámbito»; por eso cambiarlo fue **decisión del propietario**
(11-09-2026) y no del ciclo. Lo que se conserva de esa postura es el caso sin
miembros: **sin miembros resueltos se sigue excluyendo**.

### La línea base, medida al empezar y no heredada

Sobre `5fc5fdc` (`main`), con
`uv run python scripts/diagnosticar_busqueda_del_banco.py`:

| Configuración | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| `--peticion` | 17/47 | 162 | 78/81 | 0 |
| `--ejes --peticion` | 21/47 | 144 | 78/81 | 0 |

Coincide con lo que la incidencia declara. **La que decide aquí es
`--ejes --peticion`**, y se dice por qué: es la única de las cuatro en la que
los ejes del corpus llegan al puerto, y sin eje de ámbito declarado `G4` ni
siquiera toma la rama de lista cerrada. Las cuatro mediciones **no se
comparan entre sí** (bitácora del ciclo, entradas 82-83).

Contra-medición de partida, ítem a ítem, con `--ejes --peticion` sobre
`5fc5fdc`: **`DEC-001` entra en 0 de los 47 casos** (guion de un solo uso que
reutiliza `_medir` del diagnóstico y no se confirma al árbol). Ese cero es el
«antes» de la transcripción de «de más».

## Criterio de parada (escrito ANTES de decidir y ANTES de medir)

1. Si con `--ejes --peticion` los hallados **no** pasan de `78/81` a `79/81`
   y las exactas de `21/47` a `22/47`, **se para** y se registra caso a caso
   qué pasó; no se ajusta el criterio al resultado.
2. Si `--peticion` **se mueve** en cualquier cifra, algo más ha cambiado:
   se para y se explica antes de seguir.
3. Si aparece **una sola** omisión crítica, se retira el cambio.
4. «De más» **no lleva listón a propósito** —`DEC-001` con pertenencia puede
   aparecer en casos de `PRJ-ALFA`/`PRJ-BETA` que no lo esperan—, pero se
   transcribe antes y después, y si aparece se dice en cuáles y por qué.
5. Dos rondas de revisión con defectos de la misma familia → parar y buscar
   la raíz (skill `disciplina-evidencia`, §2).

## Predicción (publicada ANTES de medir, ADR-001)

- `--ejes --peticion`: **78/81 → 79/81** hallados y **21/47 → 22/47** exactas
  (`B04-CA-22` tiene `extras=0` y pasa a exacta); **0 críticas perdidas**
  (`DEC-001` no es crítica: `nivel=None`).
- `--peticion`: **no se mueve** (17/47; 162; 78/81; 0).
- «De más»: sin listón; se transcribe.

## Las cuatro preguntas de la nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en dos
   sitios distintos del sitio donde se observa. Se observa en el recuento del
   banco; vive (a) en la fixture, que no porta la membresía que el origen sí
   declara, y (b) en `_g4`, que decide por contención donde el origen decide
   por pertenencia. El arreglo va en esos dos sitios, no en el recuento. La
   pregunta que caza la raíz —*¿puede el sitio del arreglo observar el fallo
   que arregla?*— se responde por separado: `_g4` sí puede observar el suyo
   (una prueba unitaria con miembros y tres ámbitos lo ve sin banco), y la
   fixture no puede observar nada, por eso su mitad se comprueba con una
   prueba del **cargador** que afirma qué llega al motor.
2. **¿Qué NO va a garantizar esto?** No garantiza que `DEC-001` entre **en
   producción**. El puerto real entrega todo ítem con `ejes=SIN_EJES`
   (`src/sirius/adapters/persistence/staged_engine_port.py:29`); sin ejes,
   `G4` toma la rama `ambito is None` y comprueba
   `autoriza('LISTA-CERRADA-AB')`, que no es ningún proyecto del ámbito:
   excluido. Lo que este trabajo cierra es **el techo del laboratorio**
   (`--ejes --peticion`) y **la semántica de `G4`** para cuando los ejes
   existan. Persistir los ejes es otra decisión y va por el Rector (deuda
   24). Afirmar más sería repetir el error de H1.
3. **Criterio de parada**: el de arriba, escrito antes de medir.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que la membresía
   no pudiera perderse al portar: un porte automático desde el origen, o un
   invariante que exija miembros a todo ítem `MULTI_PROYECTO_CERRADO`. Lo
   primero está fuera de alcance (el origen es otra rama y este encargo solo
   autoriza añadir la pertenencia de `DEC-001`). Lo segundo se hace en la
   parte que sí cabe: la prueba del cargador afirma que los miembros llegan
   **leídos de la fixture**, no fijados en código, así que borrar el dato de
   la fixture pone la prueba en rojo. Lo que queda improbable y no imposible
   es que un ítem `MULTI_PROYECTO_CERRADO` **nuevo** entre sin miembros; se
   deja escrito aquí en vez de simularlo resuelto.

## Opciones consideradas

1. **Solo portar la membresía.** Insuficiente: con `all` y miembros
   `{PRJ-ALFA, PRJ-BETA}`, el ámbito `PRJ-BETA` de `B04-CA-22` sigue dando
   `False`. Es la capa 2 la que lo excluiría igual.
2. **Solo pasar `G4` a pertenencia.** Insuficiente: sin miembros, `_g4` corta
   antes, en «lista cerrada sin miembros resueltos».
3. **Las dos** (la decidida).
4. **Que el arnés invente la membresía en código.** Rechazada: sería el arnés
   fabricando el dato que decide la métrica, exactamente lo que la nota vieja
   de la fixture evitaba. La membresía se porta **verbatim del origen** y con
   su procedencia escrita.

## Decisión

1. `DEC-001` declara en la fixture `ejes_p2.miembros_lista_cerrada`, con el
   nombre y el valor **verbatim** de `build_corpus.py:87` en `dfdcdaff`, y la
   procedencia escrita en una nota nueva del fichero
   (`fuente.nota_incidencia_582`). Es el **único** cambio al corpus.
2. `_ejes_declarados` los lee de la fixture (tupla vacía si el ítem no los
   declara, que es el caso de los otros 96), en vez de fijar `()` en código.
3. `_g4` decide la rama multiproyecto por **pertenencia** (`any`), con el
   docstring y la **cadena de razón** reescritos para describir la regla que
   la puerta aplica ahora. La cadena llega a la explicación que ve el
   usuario: una razón que describa la regla vieja es la familia de
   `CLAUDE-R3-001` (ADR-168).

Lo que **no** cambia: sin miembros resueltos se sigue excluyendo; la puerta
`category_matching_enabled` sigue cerrada; los ejes siguen sin persistirse;
`criticidad.razon_segura` sigue sin leerse jamás.

## Comprobación que la sostiene

### 1. La medición que decide, y la que controla

`uv run python scripts/diagnosticar_busqueda_del_banco.py`, antes sobre
`5fc5fdc` y después sobre el árbol de esta rama. Las dos configuraciones
**no se comparan entre sí**: cada fila se compara consigo misma.

| Configuración | Antes | Después |
|---|---|---|
| `--peticion` (control) | 17/47; 162; 78/81; 0 | **17/47; 162; 78/81; 0** |
| `--ejes --peticion` (decide) | 21/47; 144; 78/81; 0 | **22/47; 146; 79/81; 0** |

- **La predicción se cumple**: hallados `78/81 → 79/81`, exactas
  `21/47 → 22/47`, **0 críticas perdidas**. `B04-CA-22` desaparece de la
  lista de casos con faltantes; los dos que quedan (`B04-CA-29`/`MEM-020` y
  `B04-CA-30`/`MEM-001`) son los mismos de antes y son otros huecos.
- **El control no se mueve, ni en una cifra.** Es lo que la nota de arranque
  predijo: con `SIN_EJES`, `G4` no llega a la rama de lista cerrada. Si se
  hubiera movido, el criterio de parada 2 obligaba a explicarlo antes de
  seguir.

Qué está desactivado en las dos: no hay Ollama, así que **no hay filtro de
relevancia**; el guion mide el **techo de la etapa de búsqueda**. Y el techo
del laboratorio, no el de producción: `--ejes` es una palanca del guion,
no algo que `main` tenga.

### 2. «De más»: la transcripción, antes y después

La incidencia deja «de más» **sin listón a propósito** y pide transcribir.
Con `--ejes --peticion`, el total pasa de **144 a 146**. Los dos son el
mismo `DEC-001`. Contra-medición ítem a ítem, con el mismo `_medir` del
guion (script de un solo uso, no confirmado al árbol):

| | Antes (`5fc5fdc`) | Después |
|---|---|---|
| casos en los que entra `DEC-001` | **0** | **3** |

| caso | ámbito | ¿lo espera? |
|---|---|---|
| `B04-CA-22` «¿Qué decisiones eran válidas entre enero y marzo?» | `PRJ-BETA` | **sí** — es la sexta |
| `B04-CA-14` «¿De qué se ocupa Juan?» | `GLOBAL` | no — **de más** |
| `B04-CA-43` «¿Quién valida los entregables de calidad?» | `PRJ-ALFA` | no — **de más** |

**Por qué entra en cada uno, y de qué capa es el ruido.** `B04-CA-14` es de
ámbito `GLOBAL`: `Ambito.autoriza` admite cualquier proyecto, así que
bastaba con que la lista tuviera **algún** miembro —es la capa 1, no la 2—.
`B04-CA-43` es de ámbito `PRJ-ALFA`, que **es** miembro de
`LISTA-CERRADA-AB`: ahí sí decide la pertenencia. En los dos, lo que alcanza
el ítem es la coincidencia léxica de su texto («La revisión de **calidad**
es obligatoria antes de publicar»), y en los dos `G4` hace lo correcto: el
ítem pertenece a una lista cerrada que incluye el ámbito de la pregunta.

Es **ruido del filtro, no del ámbito**, y no es una opinión: en la corrida
final del laboratorio (`lab_final_run_row5.json`, fila 5), `DEC-001` llegó a
`entraron_al_filtro` exactamente en `B04-CA-14` y **el filtro lo quitó** —su
`obtenido` de ese caso no lo trae—. La capa que descarta esta clase de
coincidencia temática es la relevancia (M10/Ollama), que ni el guion ni el
arnés determinista ejecutan.

### 3. Contra-medición que aísla el arnés (deuda 21)

`test_dec_001_entra_en_b04_ca_22_por_pertenencia_a_su_lista_cerrada` no mide
el banco: carga el canon real, construye el puerto con los ejes del corpus y
llama a `recuperar` **sin** índice de categoría, sin siembra y sin filtro.
Ahí `DEC-001` entra y su traza no tiene ni un veredicto de puerta. Y la
mutación cierra el «y no por otro camino»: con la misma petición y el mismo
canon, borrando **solo** sus miembros, el motor lo descarta con
`("G4", "lista cerrada sin miembros resueltos: la duda no abre ambito")`.
Lo que lo hace entrar es la membresía.

### 4. Las pruebas vistas fallar antes del cambio (ADR-001)

Transcrito, no afirmado:

```
# Con los tres tests de G4 escritos y `_g4` todavía en `all`:
$ uv run pytest tests/unit/test_staged_engine.py -k "lista_cerrada" -q
FAILED ...::test_g4_lista_cerrada_admite_el_ambito_que_es_miembro
FAILED ...::test_g4_lista_cerrada_descarta_el_ambito_que_no_es_miembro
    At index 0 diff: ('DECISION:1', 'G4', 'lista cerrada con miembros fuera del ambito')
                  != ('DECISION:1', 'G4', 'el ambito de la peticion no es miembro de la lista cerrada')
2 failed, 1 passed, 29 deselected
```

El que pasa desde el principio es
`test_g4_lista_cerrada_sin_miembros_resueltos_sigue_sin_entrar`: es la
propiedad que ADR-170 **conserva**, así que pasar antes y después es
exactamente lo que debe hacer.

Mutación 1 — devolver `_g4` a `all` con todo lo demás ya puesto:

```
$ uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -k pertenencia -q
FAILED ...::test_dec_001_entra_en_b04_ca_22_por_pertenencia_a_su_lista_cerrada
  AssertionError: assert 'DECISION:1' in {'DECISION:11','DECISION:14','DECISION:15','DECISION:5','DECISION:9'}
1 failed, 1 passed
```

Mutación 2 — quitar `miembros_lista_cerrada` de la fixture, con `_g4` ya en
`any`:

```
$ uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py \
      -k "pertenencia or lista_cerrada" -q
  + ()
  - ('2', '3')
2 failed
```

Las dos mitades, por separado, son necesarias. Restaurado el árbol, las dos
vuelven a verde.

### 5. Lo que cambia en el arnés del motor portado

`_ejecutar_banco_motor_portado` (los 47 casos con los ejes del corpus y la
petición de cada caso; **no** es la misma medición que el guion de arriba,
y por eso sus números son otros):

| | Antes | Después |
|---|---|---|
| `aciertos_exactos` | 29/47 | **30/47** |
| `elementos_de_mas` | 50 | **51** |
| `omisiones_criticas` | 0 | **0** |
| `elementos_hallados` | 67/81 | **68/81** |

Tres cotas suben —son más exigentes—. La cuarta,
`_MAXIMO_ELEMENTOS_DE_MAS_MOTOR`, sube de 50 a 51 por **un** elemento
nombrado: el `DEC-001` de `B04-CA-43`. No se abre ninguna puerta a cambio:
`test_los_elementos_de_mas_restantes_son_los_del_laboratorio` deja de
afirmar `== {}` y pasa a afirmar `== {"B04-CA-43": ["DEC-001"]}`, una
igualdad exacta; cualquier otra divergencia frente a la corrida del
laboratorio sigue poniendo la prueba en rojo.

La prueba que mide bajo la población del umbral D1 pasa de afirmar el suelo
(`<= 21`) a afirmar la medición exacta (`== 22`). La cota vieja no se
sustituye por una reformulación del mismo recuento —`x - 1 == 21` no puede
fallar si `x == 22` ya pasó, y ADR-134 retiró de este fichero justo esa
familia—, sino por una aserción que ata el elemento que cruza el suelo a su
causa: bajo esa misma población, el único sobrante ausente de la corrida del
laboratorio es `{"B04-CA-43": ["DEC-001"]}`. Vista fallar mutando ese mapa a
`["DEC-002"]`: `AssertionError: assert {'B04-CA-43': ['DEC-001']} ==
{'B04-CA-43': ['DEC-002']}` —mutación que la cota tautológica no habría
detectado—. Por lo que afirma, la prueba se llama desde esta corrección
`test_elementos_de_mas_mide_22_y_no_alcanza_el_suelo_d1_bajo_la_poblacion_publicada`
(antes `test_elementos_de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado`,
que es el nombre con el que la citan ADR-115 y las fichas anteriores).

### Validación obligatoria

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153), con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154),
anclada **al árbol de `f95579a2`** —el head con el código, las pruebas y el
cuerpo de esta ficha, ya con las correcciones de la ronda 2 (CLAUDE-H5-001 a
CLAUDE-H5-005)—:

```
5257 passed, 17 skipped, 2 xfailed in 547.66s (0:09:07)
EXIT_CODE_CHECK=0
```

De esa invocación se transcribe la cola capturada —la terna de `pytest` y el
código de salida—; el `0` solo sale si `ruff format --check .`,
`ruff check .` y `mypy src tests` pasaron antes, porque el guion corta en el
primero que falle (ADR-153). Esta ficha añade **5** pruebas, contadas contra
`5fc5fdc` fichero a fichero: 3 en `tests/unit/test_staged_engine.py`
(27 → 30) y 2 en
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` (41 → 43). La ronda
2 no añade ni quita ninguna: renombra una y sustituye una aserción por otra
(ver el final de la sección 5). Ninguna prueba se ha relajado; tres cotas
del arnés del motor portado suben (más exigentes) y una sube por un elemento
nombrado, con la aserción convertida en igualdad exacta en vez de en permiso
abierto (ver «Consecuencias»).

La quinta validación se ejecuta **sobre el rango de la rama y no sin
argumentos** (CODEX-001, señalado en la revisión de ADR-168):

```
$ git diff --check 5fc5fdc f95579a2
EXIT_DIFF_CHECK=0
$ git diff --check 5fc5fdc
EXIT_DIFF_CHECK_ARBOL=0
```

Sin salida y con código `0` las dos: el rango entero de la rama —desde su
base en `main` (`5fc5fdc`) hasta el árbol que midió la cadena— está limpio,
y el árbol de trabajo que confirma esta sección también.

Lo único posterior a `f95579a2` es **esta sección de la ficha** y el cuerpo
de la PR: documentales, sin tocar código ni pruebas, y existen porque la
sección tiene que anclarse al árbol que la cadena midió. Si una corrección
posterior toca código o pruebas, la cadena se vuelve a ejecutar entera y
esta sección se re-ancla al árbol nuevo, sin conservar la terna del anterior
(ADR-154).

## Consecuencias

**Lo que mejora.** `B04-CA-22` recupera sus seis. Con `--ejes --peticion`,
`79/81` hallados y `22/47` exactas, sin perder ninguna crítica. El hueco H5
queda cerrado en el techo del laboratorio.

**Lo que empeora, dicho sin maquillar.** El suelo D1 de `elementos_de_mas`
(≤21 sobre los 31 `casos_con_contenido`) **deja de alcanzarse por uno**: el
arnés del motor portado pasa de 21 a 22. Es el `DEC-001` de `B04-CA-43`.
`test_elementos_de_mas_mide_22_y_no_alcanza_el_suelo_d1_bajo_la_poblacion_publicada`
lo afirma así, en su docstring y en su aserción, en vez de relajar el
listón. Esto no es un efecto colateral inadvertido: la incidencia #582 deja
«de más» sin listón a propósito, porque la decisión del propietario del
11-09-2026 es que `G4` decida por pertenencia, y este elemento es el precio
medido de esa decisión. **Se señala aquí para que el propietario lo vea al
fusionar, no para darlo por bueno en su nombre.**

**Lo que NO cambia.** En **producción** `DEC-001` sigue sin entrar, y esta
ficha no afirma lo contrario: el puerto real entrega todo ítem con
`SIN_EJES`, así que `G4` toma la rama `ambito is None`. El control
`--peticion` lo demuestra midiendo: no se mueve. Persistir los ejes es otra
decisión, del Rector (deuda 24). La puerta `category_matching_enabled` sigue
cerrada. `criticidad.razon_segura` sigue sin leerse jamás.

**Deuda que este trabajo deja escrita.** Un ítem `MULTI_PROYECTO_CERRADO`
nuevo podría volver a entrar al corpus sin miembros, y nada lo impediría:
`G4` lo descartaría con su razón correcta y el hueco sería invisible otra
vez. Hacerlo imposible pedía un invariante sobre el corpus o un porte
automático desde el origen, los dos fuera del alcance de #582 (ver la cuarta
pregunta de la nota de arranque).

## Alternativas descartadas y por qué

Ver «Opciones consideradas».

# ADR-168 — Listar por vigencia cuando la pregunta declara un intervalo y la busqueda lexica no tiene de donde partir

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.
- Esta ficha es además la **nota de arranque** de la rama (ADR-001, skill
  `disciplina-evidencia`): las cuatro preguntas y el criterio de parada de
  abajo se escribieron y se publicaron **antes del primer commit de código**
  (commit de esta ficha sola, anterior a cualquier cambio en `src/`).

## Contexto y problema

Hueco **H1 de ADR-148**, la incidencia #577 (`WI-20260908-H1`). Es el mayor
de los que quedan: cinco de las siete ocurrencias que el banco sigue sin
recuperar.

El caso es `B04-CA-22`, «¿Qué decisiones eran válidas entre enero y marzo?»,
con `cardinalidad=EXHAUSTIVA` y `tiempo_objetivo=2026-01-10T00:00:00Z/
2026-03-20T00:00:00Z`. Espera seis decisiones (`DEC-001`, `DEC-005`,
`DEC-009`, `DEC-011`, `DEC-014`, `DEC-015`) y hoy entra una: `DEC-014`, la
única cuyo texto —«Se habilita el turno reducido de enero»— comparte una
palabra con la pregunta. Entra por accidente léxico, no porque el motor
entienda la vigencia.

La causa está en la generación de candidatas.
`CandidatoLexicoEstructurado.candidatas`
(`src/sirius/adapters/persistence/staged_engine_candidate.py`) parte
**siempre** de `terminos_significativos(consulta)` y devuelve `()` si no hay
ninguno; las cuatro etapas de expansión consultan el puerto por clave, por
término léxico, por prefijo de sujeto o por historial. Una pregunta cuyo
único criterio es un intervalo de vigencia no le da ninguna palabra útil: no
es que ordene mal, es que **no hay camino de entrada**.

### La línea base, medida al empezar y no heredada

Sobre `6371d4c` (`main` con H2/ADR-166 dentro), con
`uv run python scripts/diagnosticar_busqueda_del_banco.py`, las cuatro
configuraciones:

| Configuración | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| sin banderas | 0/47 | 487 | 72/81 | 0 |
| `--ejes` | 0/47 | 421 | 71/81 | 0 |
| `--peticion` | **17/47** | **162** | **74/81** | **0** |
| `--ejes --peticion` | 21/47 | 144 | 74/81 | 0 |

Coincide con lo que la incidencia declara como suelo y con lo que ADR-166
publica. `--peticion` es el suelo de referencia.

### Dos cosas que el árbol desmiente de la incidencia

La incidencia manda leer el árbol cuando discrepe (deudas 19 y 21), así que
las dos diferencias se registran aquí **antes** de construir:

1. **«El intervalo llega en la `Peticion`» no es cierto hoy.** ADR-164 puso
   la palanca 1 en `main`, pero el intervalo se colapsa a su extremo final
   una línea antes de construir la `Peticion`, en los dos caminos:
   `_instante` (`tests/acceptance/staged_engine_case_translation.py`,
   «Un caso puede declarar su instante objetivo como un intervalo; se toma
   el extremo final») y `_tiempo_objetivo`
   (`src/sirius/adapters/ollama_query_intent_classifier.py`, «Un intervalo se
   resuelve por su extremo final»). `VentanaTemporal`
   (`src/sirius/domain/staged_engine_contracts.py`) solo tiene
   `tiempo_objetivo` y `corte_de_registro`: no hay campo donde el extremo
   inicial pudiera viajar. La información **llega al intérprete** y se tira
   ahí; conservarla es, por tanto, parte de la vía y no un encargo aparte.
2. **`DEC-001` no puede entrar en este encargo, y no por el hueco H1.** Su
   proyecto en el corpus es `LISTA-CERRADA-AB`, distinto del ámbito del caso
   (`PRJ-BETA`), y su eje de ámbito es `MULTI_PROYECTO_CERRADO` **sin
   miembros resueltos**: el arnés lo declara así a propósito
   (`_ejes_declarados`, `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`,
   «el corpus portado no declara la membresía de listas cerradas… `G4` la
   trata como lista sin miembros y la descarta»). Así que `G4` lo descarta
   con ejes (`lista cerrada sin miembros resueltos`) y sin ejes
   (`peticion.ambito.autoriza(project_id)` es falso). Recuperarlo exigiría
   tocar el ámbito o el corpus, las dos cosas fuera de alcance.

## Criterio de parada (escrito ANTES de decidir)

Predicción publicada antes de medir nada del cambio:

- **`--peticion`: `74/81` → `78/81` hallados**, no `79/81`. Las cinco
  ocurrencias de H1 son `DEC-001`, `DEC-005`, `DEC-009`, `DEC-011` y
  `DEC-015`; cuatro entran por vigencia y `DEC-001` no puede entrar por la
  razón registrada arriba, que es de ámbito (`G4`) y no de este hueco. Si
  midiendo resulta que sí entra, se dice y se corrige esta ficha.
- **`DEC-014` sigue entrando**, y se comprueba si pasa a entrar también por
  vigencia además de por el accidente léxico.
- **Exactas: no bajan de `17/47`.** Críticas perdidas: **0**, fijadas con
  prueba y no solo medidas.
- **`de más` sin listón**, por decisión de la incidencia: la vía enumera y
  quien cierra el ruido es la palanca 3. Se transcribe antes y después y, si
  sube, se razona si cae dentro de lo que el filtro puede quitar.
- **Solo `B04-CA-22` cambia de resultado.** Cualquier otro caso que cambie se
  explica uno a uno.
- **Se para** si las exactas bajan, si aparece una crítica perdida, o si el
  arreglo obliga a decidir algo de producto, ámbito o corpus. No se ajusta el
  criterio al resultado.

## Las cuatro preguntas de la nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en la
   **generación de candidatas** (nadie pregunta nunca por vigencia) y en la
   **traducción del tiempo** (el extremo inicial se tira). El arreglo va en
   los tres sitios que pueden observarlo: el contrato conserva el intervalo,
   el puerto aprende a consultar por ventana de vigencia, y la fuente de
   candidatas aporta esa señal. Ninguno de los tres podría observarse desde
   otro sitio: las puertas ya honran el tiempo (`G8`) sobre candidatas que
   nunca llegan, y ordenar mejor no crea un camino de entrada.
2. **¿Qué NO garantiza?** No recupera `DEC-001` (ámbito, no vigencia). No
   baja el ruido: lo sube. No abre `category_matching_enabled`. No persiste
   `valid_from`/`valid_to` en el esquema (palanca 2, cerrada sin fusionar en
   #572), así que en el sustrato real la vía **degrada** a lo que Sirius sí
   guarda: `created_at` y el estado vigente. No infiere «tema» de la
   pregunta: no hay lista de temas y fabricarla sería ajustar el criterio al
   caso.
3. **Criterio de parada:** el de arriba, publicado antes de medir.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que el sustrato
   persistiera la ventana de vigencia por ítem; eso es la palanca 2, medida y
   descartada por no pagar (#572), y no se reabre aquí. Lo que sí queda
   imposible es la regresión concreta: las cuatro pruebas del encargo fijan
   la vía, la permanencia de `DEC-014`, la no interferencia con una pregunta
   con tema y las 0 omisiones críticas.

## Opciones consideradas

1. **Una rama de la etapa de búsqueda** (elegida): una tercera señal de
   ``E3`` en la fuente de candidatas, y una ruta nueva del puerto.
2. **La misma señal, pero en ``E1``.** Medida (abajo): da **exactamente las
   mismas cuatro cifras** en las cuatro configuraciones. El banco no
   distingue entre las dos, así que la elección no la decide el número sino
   dos propiedades que el banco no contiene, y se argumenta en «Decisión».
3. **Un camino propio, fuera del motor por etapas.** Descartada: obligaría a
   duplicar las puertas ``G1-G12`` o a saltárselas, y saltárselas es
   exactamente lo que el motor existe para impedir. La ventana entra como
   candidata y pasa por las mismas doce puertas que todo lo demás.
4. **Deducir «no trae tema» de la consulta** con una lista cerrada de meses y
   de palabras de vigencia. Descartada: esa lista se escribiría mirando
   `B04-CA-22`, que es literalmente ajustar el criterio al resultado.

## Decisión

**Una pregunta que declara un intervalo de vigencia entra por la ventana, no
por las palabras.** Tres piezas, y ninguna más:

1. **El contrato conserva el intervalo.** ``VentanaTemporal`` gana
   ``tiempo_objetivo_desde`` (el extremo inicial; ``None`` = la pregunta
   declara un instante) y la propiedad ``intervalo_de_vigencia``, que
   devuelve ``(desde, hasta)`` solo si hay dos extremos y no están
   invertidos. ``tiempo_objetivo`` **no cambia**: sigue siendo el extremo
   final, que es lo que ``G8`` compara. Los dos traductores del tiempo dejan
   de tirar el extremo inicial: el del banco (``_instante_inicial``) y el de
   producción (``_tiempo_objetivo_desde``, que lee el mismo campo que ya
   leía, sin tocar ni el esquema cerrado ni la instrucción del modelo). En el
   intérprete, el extremo inicial **solo viaja si el final vino con él**: con
   un intervalo medio ilegible el final sería el «ahora» del respaldo y la
   ventana resultante no la habría pedido nadie.
2. **El puerto aprende a consultar por ventana.**
   ``PuertoDeRecuperacion.por_ventana_de_vigencia(desde, hasta)``, con su
   propia cota (``LIMITE_POR_VENTANA``) y orden determinista. La ventana es
   un predicado que dirige la consulta, como la clave, el término o el
   prefijo: sigue sin existir ninguna ruta que devuelva el canon entero.
3. **``E3`` gana una tercera señal.** Las otras dos expanden desde lo ya
   recuperado; esta expande desde lo que la **petición** declara. Sin
   intervalo declarado no aporta nada y ``E3`` se comporta exactamente como
   antes.

**El discriminante de la vía es el INTERVALO declarado, no la ausencia de
tema** (CLAUDE-R2-003). ``_e3`` evalúa ``self._por_vigencia(contexto)`` antes
de mirar ``terminos``, ``semillas``, ``puente`` o ``familias``, y la única
guarda de ``_por_vigencia`` es ``intervalo is None``. De ahí que el tercer
criterio de aceptación de la incidencia —«una pregunta que sí trae tema sigue
comportándose exactamente igual que antes»— quede cumplido **en su lectura de
«no puede secuestrar la búsqueda normal»**, y NO en su lectura literal:

- Lo léxico **conserva su autoridad**: no se sustituye ni se desplaza, y la
  ventana solo llega a consultarse si las etapas anteriores fueron
  insuficientes. Fijado en
  ``test_lo_lexico_conserva_su_autoridad_sobre_lo_enumerado_por_ventana`` y
  en ``test_la_ventana_no_se_consulta_si_las_etapas_lexicas_ya_bastaron``.
- Pero **existe un tercer caso en el que el comportamiento sí cambia**: una
  pregunta CON tema que además declare un intervalo y no quede satisfecha en
  ``E1``/``E2`` recibe elementos adicionales por la ventana. No es conjetura:
  es lo que fija la primera de esas dos pruebas, con consulta CON tema y
  resultado ``('DECISION:1', 'DECISION:9')``, donde el segundo entra por la
  ventana.
- Las dos pruebas que acompañan al criterio 3
  (``test_una_pregunta_con_tema_no_activa_la_via_por_vigencia``, sobre
  ``B04-CA-32``, que declara un INSTANTE y no un intervalo, y
  ``test_sin_intervalo_declarado_e3_no_pregunta_por_la_ventana``) fijan «sin
  intervalo declarado, todo igual que antes»: una afirmación sobre el
  intervalo, no sobre el tema.
- **El banco no mide ese tercer caso**, y que no se note en las cuatro cifras
  es una propiedad del banco —un único caso con intervalo, y sin tema— y no
  de la vía. Las cuatro cifras no son evidencia de que ese tercer caso no
  cambie.

Detectar «tema» para excluir la vía se descartó a propósito (ver las
alternativas): sería un ajuste al caso.

**Por qué ``E3`` y no ``E1``, cuando el banco mide lo mismo con las dos.** Dos
propiedades que las cuatro cifras no ven, porque el único caso del banco con
intervalo es ``EXHAUSTIVA`` y sin límite:

- **El motor solo pregunta por ``E3`` cuando las etapas anteriores fueron
  insuficientes.** Es lo más parecido a «y no trae tema» que puede afirmarse
  sin inventar una lista de temas: si la vía léxica ya satisfizo la
  cardinalidad de la pregunta, la ventana no llega a consultarse. En ``E1``
  se dispararía siempre. Fijado en
  ``test_la_ventana_no_se_consulta_si_las_etapas_lexicas_ya_bastaron``.
- **La autoridad de orden de ``E3`` es menor que la de ``E1``/``E2``**
  (``staged_engine._clave_de_orden``): lo que las palabras encuentran sigue
  por delante de lo que la ventana enumera. La vía **añade**; no sustituye ni
  desplaza.

**Solo decisiones, y esta es la parte que hay que leer con cuidado.** La
primera versión de la vía enumeraba las dos clases del canon y funcionaba:
`74/81` → `78/81`. También subía el ruido en 20 elementos, **todos ellos
memorias**, y ese ruido rompía tres pruebas del banco, una de ellas el suelo
D1 publicado (`elementos_de_mas` ≤ 21 sobre los 31 `casos_con_contenido`,
que pasaba a 40). El orden real de los hechos fue ése: primero se midió el
ruido, después se comprobó de qué estaba hecho (las 20 son memorias; **no
había ni una decisión de más**), y solo entonces se fue al modelo de dominio
a preguntar si el sustrato justificaba la restricción. La justificación
existe, y es explícita:

- ``DecisionStatus`` **es** un ciclo de vigencia: ``PROPOSED`` → ``APPROVED``
  → ``SUPERSEDED``/``ARCHIVED`` (``src/sirius/domain/decision.py:40-50``).
  Aprobar empieza una vigencia y sustituir la termina, y el esquema hasta
  guarda cuál sustituyó a cuál
  (``DecisionModel.supersedes_decision_id``).
- ``MemoryStatus`` **no** lo es, y lo dice su propio modelo:
  «Superseded revisions are a history concern, **not a status of the memory
  itself**: the memory stays CURRENT while its ``current_revision`` pointer
  advances» (``src/sirius/domain/memory.py:12-19``).
  ``CURRENT``/``ARCHIVED``/``DELETED`` es disponibilidad, no vigencia.

Enumerar memorias por ventana obligaba a afirmar «esta memoria estaba vigente
entre enero y marzo» sobre un dato que el sustrato no tiene — la misma
invención que ADR-166 se negó a hacer con una fecha ausente. Si el modelo
hubiera dicho lo contrario, la restricción habría sido un ajuste al resultado
y este encargo se habría parado; se registra en este orden para que quien
revise pueda juzgarlo. Las memorias siguen entrando por las vías léxicas,
que no afirman nada sobre su vigencia.

Dos degradaciones más, declaradas y no ocultas:

- **Sin fin de vigencia persistido** (palanca 2 de ADR-148, cerrada sin
  fusionar en #572), la única afirmación disponible sobre el final es el
  estado aprobado. Por eso ``desde`` no entra en el predicado SQL: nada
  aprobado puede haber dejado de estarlo antes de ``desde``. Se recibe
  igualmente porque es la mitad del contrato de la ventana.
- **Una decisión ``SUPERSEDED`` no entra** aunque pudiera haber estado
  vigente dentro de la ventana: el esquema guarda QUÉ la sustituyó, no
  CUÁNDO. Datarlo con ``updated_at`` —el último toque— sería inventar la
  fecha que falta. Queda como deuda declarada.

## Comprobación que la sostiene

### Las cuatro configuraciones, antes y después

`uv run python scripts/diagnosticar_busqueda_del_banco.py [--ejes] [--peticion]`,
en el contenedor del operador, sobre esta rama (base `6371d4c`):

| Configuración | Antes | Después |
|---|---|---|
| sin banderas | `0/47; 487; 72/81; 0` | `0/47; 487; 72/81; 0` |
| `--ejes` | `0/47; 421; 71/81; 0` | `0/47; 421; 71/81; 0` |
| `--peticion` | `17/47; 162; 74/81; 0` | **`17/47; 162; 78/81; 0`** |
| `--ejes --peticion` | `21/47; 144; 74/81; 0` | **`21/47; 144; 78/81; 0`** |

Ninguna de las cuatro métricas del suelo empeora en ninguna de las cuatro
configuraciones. Las dos de petición fija **no se mueven en absoluto**, y no
por casualidad: la política uniforme no declara ningún intervalo, así que la
vía no llega a activarse.

**El recuento de «de más» no sube.** La predicción lo daba por perdido y sin
listón; con la vía acotada a decisiones se queda **exactamente igual**: 162 y
144. El caso que gana cuatro elementos hallados no aporta **ni un solo**
elemento de más.

**Cambia un caso y solo uno**, `B04-CA-22`, y su detalle caso a caso:

    antes:   faltan=[DEC-001, DEC-005, DEC-009, DEC-011, DEC-015]
             entraron=[DEC-014]  extras=0
    después: faltan=[DEC-001]
             entraron=[DEC-005, DEC-009, DEC-011, DEC-014, DEC-015]  extras=0

Los otros dos huecos abiertos (`B04-CA-29`/`MEM-020` y `B04-CA-30`/`MEM-001`,
H3 y H4, decisiones de producto del propietario y fuera de este encargo)
siguen exactamente igual, con los mismos `extras` que antes.

### Contra-medición que aísla el arnés, ítem a ítem

El arnés no tiene guardianes propios (deuda 21), así que la afirmación «las
cuatro entran por vigencia y `DEC-001` cae por ámbito» no se deduce del
recuento: se leyó del veredicto de puerta de cada uno de los seis, por ítem y
no por una constante, instrumentando `gates.aplicar_previas` durante la
ejecución real del banco. Con `--peticion`:

    DEC-001  G4        fuera del ambito autorizado
    DEC-005  ADMITIDA  ventana de vigencia declarada por la peticion...
    DEC-009  ADMITIDA  ventana de vigencia declarada por la peticion...
    DEC-011  ADMITIDA  ventana de vigencia declarada por la peticion...
    DEC-014  ADMITIDA  clave de sujeto normalizada y coincidencia literal...
    DEC-015  ADMITIDA  ventana de vigencia declarada por la peticion...

Y con `--ejes --peticion`, el mismo cuadro con el otro motivo de `G4` para
`DEC-001`: `lista cerrada sin miembros resueltos: la duda no abre ambito`.
Es decir: las cuatro nuevas entran **por vigencia** y no por accidente
léxico; `DEC-014` **sigue entrando por su camino léxico de `E1`**, que la vía
no sustituye; y la diferencia entre cinco y seis es de ámbito y no de este
hueco. Las dos afirmaciones están fijadas con prueba
(`test_b04_ca_22_recupera_por_vigencia_lo_que_ninguna_palabra_alcanza`).

`DEC-014` **también es alcanzable por vigencia**: con la misma ventana y una
consulta que no deja un solo término significativo, sigue entrando, ahora con
la señal de la ventana
(`test_dec_014_sigue_entrando_y_la_ventana_lo_alcanza_aunque_cambie_la_redaccion`).
Su presencia deja de depender de cómo esté redactado el ítem, aunque con la
consulta real siga llegando primero por `E1`.

### La dimensión que la contra-medición NO aislaba: el cargador

Revisión de la ronda 2 (CLAUDE-R2-001). Lo de arriba aísla el **guion de
recuento** —el veredicto de puerta se lee ítem a ítem y no se deduce del
contador—, pero no aísla el **cargador**, y es el cargador el que fabrica la
coincidencia entre lo que el banco mide y lo que la vía afirma. La condición,
leída del árbol:

- `_fecha_de_registro` (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`,
  ADR-166) devuelve `item["ejes_p2"]["valid_from"]` —y solo recurre a
  `_REGISTRO_DE_LO_NO_FECHADO` cuando el corpus no lo declara—, y
  `_fijar_fecha_de_registro` lo escribe verbatim en `created_at` (guardián ya
  existente: `test_el_registro_escrito_lleva_la_forma_que_g8_compara`).
- Es decir: **en el banco, `created_at == valid_from`, ítem a ítem**. En
  producción no: el `created_at` de una decisión lo pone el reloj al
  proponerla (`sqlite_decision_repository._utc_now_naive`) y no guarda
  ninguna relación con `valid_from`; el propio ADR ya declara arriba que sin
  la palanca 2 no hay `valid_from`/`valid_to` persistidos, así que `G8`
  tampoco lo corrige aguas abajo (llega con `SIN_EJES`).

Sustituyendo esa identidad en el predicado del puerto
(`created_at <= :hasta AND status = 'approved'`), **lo que el banco mide es
`valid_from <= hasta` y aprobada**, que sí es un predicado de vigencia. La
degradación que la Decisión declara en abstracto —«en el sustrato real la vía
degrada a lo que Sirius sí guarda»— **la medición no la observa**, porque el
cargador anula la diferencia. Con esa condición a la vista, lo que la cifra
`74/81` → `78/81` demuestra y lo que no:

- **Demuestra** que la señal de la ventana es el camino de entrada que
  faltaba, y que las cuatro ocurrencias entran por ella y no por accidente
  léxico —eso está fijado ítem a ítem en el cuadro de arriba— y que la vía no
  desplaza lo léxico.
- **No demuestra** que la vía recupere lo vigente sobre un `created_at` real.
  Ahí el predicado es de **registro**, no de vigencia, y el error tiene dos
  direcciones concretas: se **pierde** lo vigente en la ventana pero
  registrado después de `hasta`, y se **admite** lo registrado antes de
  `hasta` cuya vigencia empieza después. El titular que el dato sostiene es
  «las cuatro entran por la señal de la ventana», no «el motor entiende la
  vigencia en el sustrato de Sirius 0.1».

Queda como deuda declarada junto a las otras tres: cerrarla es la palanca 2
(`valid_from`/`valid_to` persistidos), no este encargo. No se cambia ninguna
cifra —son correctas— ni el predicado ni el cargador; lo que faltaba era que
la afirmación y su condición viajaran juntas.

### La medición que decide dónde vive la vía

La misma vía en `E1` en vez de en `E3`, medida con el mismo guion:
`--peticion` `17/47; 162; 78/81; 0` y `--ejes --peticion` `21/47; 144;
78/81; 0` — **idénticas**. El banco no distingue, y por eso la decisión se
argumenta por propiedades (arriba) en vez de por número. Que empatan es un
dato, no una excusa: se midió antes de argumentar.

(La primera pasada de esta medición fue **mala** y se rehízo: el parche que
movía la señal a `E1` había borrado además la rama de `E3` entera, así que
medía «vigencia en E1 **y E3 apagada**» — `19/47; 143; 74/81`. Se detectó
porque las cifras se movían en casos sin intervalo, que la vía no puede
tocar. Queda escrito porque la cifra equivocada llegó a existir.)

### Corrección posterior: el final de la ventana se compara con grano de instante

Revisión de la ronda 1 (CLAUDE-R1-001). El predicado `created_at <= :hasta`
recibía el extremo final **en la forma del corpus** (`2026-03-20T00:00:00Z`)
y lo comparaba, en SQLite y como CADENAS, contra un `created_at` escrito en
la forma del dialecto de SQLAlchemy (`2026-03-20 09:00:00.000000`). El
espacio (0x20) ordena antes que la `T` (0x54), así que
`"2026-03-20 09:00:00.000000" <= "2026-03-20T00:00:00Z"` era **verdadero**:
toda decisión aprobada registrada más tarde del mismo día civil que el final
de la ventana entraba igualmente. El error estaba acotado a ese día y era
siempre inclusivo —nunca excluía canon—, pero el docstring afirmaba un
predicado de instante que el sustrato no sostenía, y ninguna prueba tocaba la
frontera: las cuatro usaban extremos a años de distancia del registro.

Es el mismo mecanismo que el encabezado de
`ollama_query_intent_classifier` nombra para el corte de registro, y se
corrige igual: el extremo se reescribe en la forma de `created_at`
(`_en_forma_de_created_at`, en el propio puerto) antes de la consulta, de
modo que los dos operandos son dos escrituras comparables del mismo instante.
La forma con `Z` de `_tiempo_objetivo` no se toca: `G8` la compara contra
`valid_from`/`valid_to`, que el corpus escribe así, y esa forma tiene su
propia razón. Un `hasta` que no sea un instante legible ya no se compara:
la ventana devuelve vacío en vez de afirmar vigencia bajo un extremo que no
sabe leer.

Las cuatro cifras del banco **no se mueven**: el cargador escribe cada
`created_at` a la medianoche del día declarado (ADR-166), y la medianoche del
día del corte sigue entrando por igualdad, que es el único caso del banco que
la frontera toca. Comprobado sobre el árbol de la validación de abajo, donde
las cuatro cotas del arnés del motor portado son aserciones de la prueba de
aceptación y pasan sin cambiarlas.

### Corrección posterior: la guarda de los dos extremos no es del corte de registro

Revisión de la ronda 2 (CLAUDE-R2-002). Al ganar el parámetro `extremo`,
`_iso_declarado` ganó también una guarda —`if len(extremos) != 2: return
None`— colocada **antes** de elegir extremo, de modo que alcanzaba a las dos
rutas que leen de ahí y no solo a la del tiempo objetivo. `_corte_de_registro`
llama con el extremo por defecto, así que una escritura de TRES o más
extremos (`"2026-01-01/2026-02-01/2026-03-01"`) dejaba de producir corte: de
`2026-03-01 23:59:59.999999` a **ningún corte**.

Las dos rutas quieren respuestas contrarias ante la misma entrada patológica,
y esa es la razón de que la guarda deje de ser común
(`exigir_dos_extremos`):

- **El tiempo objetivo se descarta entero.** Elegir dos extremos de tres
  sería adivinar cuáles, y la ventana afirmaría una vigencia que nadie
  declaró. Fijado en `test_un_intervalo_de_mas_de_dos_extremos_no_declara_ninguno`,
  que no cambia.
- **El corte de registro NO.** El corte es el filtro que sostiene «¿qué sabía
  yo el día X?» y su razón de ser es **excluir** lo registrado después;
  perderlo entero entrega como sabido entonces lo que se registró después,
  que es sobre-inclusión en el único sitio donde el error tiene dirección
  mala. Conserva el comportamiento anterior a ADR-168 —el último extremo, al
  final de su día civil— y sigue errando hacia excluir. Fijado en
  `test_el_corte_de_registro_de_mas_de_dos_extremos_sigue_cortando`.

Nada más cambia: ni `_tiempo_objetivo`, ni `_tiempo_objetivo_desde`, ni
`_PATRON_ISO`, ni la forma con `Z` con la que `G8` compara. Las cuatro
configuraciones del banco **no se mueven**, porque ninguna petición del banco
declara una escritura de tres extremos: comprobado sobre el árbol de la
validación de abajo, donde las cuatro cotas del arnés del motor portado
siguen siendo aserciones de la prueba de aceptación y pasan sin cambiarlas.

### Corrección posterior: el texto entregado enuncia las dos condiciones, no la vigencia

Revisión de la ronda 3 (CLAUDE-R3-001). La sección «La dimensión que la
contra-medición NO aislaba» declara, arriba, que sobre un `created_at` real la
vía **admite lo registrado antes de `hasta` cuya vigencia empieza después**.
Esa declaración entraba en contradicción con la cadena que el motor entregaba
al usuario y que la ronda 2 no ajustó: `razon="vigente en la ventana declarada
por la peticion (X a Y)"`, publicada en `Explicacion.razon_de_orden` por
`staged_engine_trace.explicar`.

El predicado real es `created_at <= :hasta AND status = 'approved'`, y
`created_at` es el instante en que la decisión se **propuso**
(`ProposeDecisionUseCase`), no aquel en que se aprobó: `DecisionModel` no
persiste ninguna fecha de aprobación, y `updated_at` es el último toque —el
mismo motivo por el que esta ficha se niega a datar con él el final de una
vigencia (`SUPERSEDED`)—. Así que una decisión propuesta dentro de la ventana
y **aprobada después de su final** entra por la vía, y de ella se afirmaba una
vigencia que el sustrato de Sirius 0.1 no sostiene. Es la familia de defecto
que ADR-166 evitó al negarse a inventar una fecha ausente, aquí en el extremo
**inicial** de la vigencia.

Lo que cambia es el texto, no el predicado: la vía sigue devolviendo lo mismo,
con la misma cota, el mismo orden y la misma restricción de estado, y ninguna
cifra medida se mueve. La cadena entregada pasa a enunciar exactamente las dos
condiciones —`"decision aprobada cuyo registro no es posterior al final de la
ventana declarada por la peticion (X a Y)"`— y el docstring de
`por_ventana_de_vigencia` dice ahora en el mismo párrafo qué es lo que las dos
**no** afirman. Cerrar la deuda sigue siendo la palanca 2 de ADR-148
(`valid_from`/`valid_to` persistidos), no este encargo; lo que faltaba era que
el texto entregado no la contradijera.

Dos pruebas nuevas, ninguna existente tocada:

- `test_por_ventana_de_vigencia_admite_lo_aprobado_despues_del_final_de_la_ventana`
  (`tests/unit/test_staged_engine_port.py`): una decisión con `created_at`
  fijado dentro de la ventana y aprobada después —el `updated_at` que deja la
  aprobación es posterior al final— entra por la vía. Fija el hecho del que la
  redacción tiene que dar cuenta; la prueba vecina
  `test_por_ventana_de_vigencia_no_devuelve_una_propuesta_sin_aprobar` no lo
  cubría, porque su decisión sigue sin aprobar en el momento de la consulta.
- `test_la_razon_enuncia_las_dos_condiciones_y_no_afirma_vigencia`
  (`tests/unit/test_staged_engine_candidate_por_vigencia.py`): fija la cadena
  de `Candidata.razon`, que hasta ahora no fijaba ninguna prueba.

### Pruebas vistas fallar (mutación transcrita)

Catorce mutaciones, cada una revertida después. Ninguna prueba nueva pasa con
el código de antes:

| Mutación | Qué se rompe | Rojo |
|---|---|---|
| M1 `candidatas` vuelve a salir por «no hay términos» antes de mirar `E3` | el código de antes de esta ficha | 3 pruebas |
| M2 `E3` deja de aportar la señal por vigencia | la vía entera | 7 pruebas, incluidas las tres de aceptación |
| M3 el puerto vuelve a enumerar memorias | la restricción de clase | 4, entre ellas el suelo D1 (`40 == 21`) |
| M4 sin la guarda del intervalo invertido | la degradación | 1 |
| M5 el traductor del banco vuelve a tirar el extremo inicial | el acarreo | 5 |
| M6 el extremo inicial viaja sin final legible | la guarda del intérprete | 1 |
| M7 el lector del modelo vuelve a tirar el extremo inicial | el acarreo en producción | 1 |
| M8 la vía se muda a `E1` | la elección de etapa | 3, entre ellas la de insuficiencia |
| M9 la vía se dispara sin intervalo declarado | la no interferencia | 5, entre ellas el suelo D1 (`55 == 21`) |
| M10 el extremo final viaja sin reescribir (`"hasta": hasta`) | el grano de instante en la frontera del mismo día | 1 (`test_por_ventana_de_vigencia_excluye_lo_registrado_el_mismo_dia_tras_el_final`) |
| M11 un extremo ilegible se consulta igual (`corte = hasta`) | la guarda del extremo no legible | 1 (`test_por_ventana_de_vigencia_no_afirma_nada_con_un_final_ilegible`) |
| M12 la guarda de los dos extremos vuelve a ser común (`if len(extremos) != 2:`) | el corte de registro con tres extremos | 1 (`test_el_corte_de_registro_de_mas_de_dos_extremos_sigue_cortando`: `assert None == '2026-03-01 23:59:59.999999'`) |
| M13 la razón vuelve a decir «vigente en la ventana declarada por la peticion» | la afirmación que el predicado no sostiene | 1 (`test_la_razon_enuncia_las_dos_condiciones_y_no_afirma_vigencia`: `assert 'vigente en l...20T00:00:00Z)' == 'decision apr...20T00:00:00Z)'`) |
| M14 el predicado exige además `updated_at <= :hasta` | el hecho que la redacción tiene que reconocer | 2 (`test_por_ventana_de_vigencia_admite_lo_aprobado_despues_del_final_de_la_ventana` y `…excluye_lo_registrado_el_mismo_dia_tras_el_final`: `assert [] == ['DECISION:1']`) |

### La cota que se mueve, y en qué dirección

`_MINIMO_ELEMENTOS_HALLADOS_MOTOR` sube de **63 a 67**: es la cobertura que
el arnés del motor portado mide ahora (29/47, 50, 0, 67/81). Sube, es decir,
la prueba queda **más exigente**, no menos. Las otras tres cotas de ese arnés
no se tocan porque no se movieron. **Ninguna prueba se ha relajado, saltado ni
reescrito para conseguir verde**: la única versión de la vía que obligaba a
relajar una (`_MAXIMO_ELEMENTOS_DE_MAS_MOTOR` 50 → 69, y el suelo D1 de 21 a
40) se descartó y se sustituyó por la acotada, que no lo necesita.

### Validación obligatoria

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153), con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154).
Re-anclada al árbol de **`bcf1a45`**, el que trae la corrección de la ronda 3
y sus dos pruebas nuevas (CLAUDE-R3-001):

```
5232 passed, 17 skipped, 2 xfailed in 566.46s (0:09:26)
EXIT_CODE_CHECK=0
```

De esa invocación se transcribe la cola capturada —la terna de `pytest` y el
código de salida—; el código `0` solo sale si `ruff format --check`
(«618 files already formatted»), `ruff check` («All checks passed!») y
`mypy src tests` («Success: no issues found in 583 source files») pasaron
antes, porque el guion corta en el primero que falle (ADR-153).

La quinta validación se ejecuta **sobre el rango de la PR** y no sin
argumentos (CODEX-001): `git diff --check` sin revisiones compara el árbol de
trabajo con el índice y sale `0` aunque el rango ya confirmado traiga errores
de espacios, de modo que no demostraba nada sobre este cambio. La forma
correcta es la que ADR-166 ya usaba, con las dos revisiones:

```
$ git diff --check 6371d4c bcf1a45
EXIT_DIFF_CHECK=0
```

Sin salida y con código `0`: el rango entero de la rama, desde su base en
`main` hasta el árbol que midió la cadena, está limpio. La misma comprobación
contra el árbol de trabajo que confirma esta sección —`git diff --check
6371d4c` — tampoco imprime nada y sale `0`, así que el texto documental
posterior queda igual de cubierto.

Lo único posterior a `bcf1a45` es **esta sección de la ficha** y la sección
de validaciones del cuerpo de la PR: cambios documentales que no tocan código
ni pruebas, y que existen porque la sección tiene que anclarse al árbol que la
cadena midió. Si una corrección posterior toca el fichero de pruebas, la
cadena se vuelve a ejecutar entera y esta sección se re-ancla al árbol nuevo,
sin conservar la terna del anterior.

(Las ternas anteriores de esta rama —`5230 passed, 17 skipped, 2 xfailed in
569.96s` sobre `41651d1`, `5229 … 576.21s` sobre `a8fe837`, `5227 … 566.49s`
sobre `ffd8d05` y `…552.29s` sobre `19581ee` más dos ficheros documentales sin
confirmar— eran las de sus árboles y así se leen; la de `bcf1a45` sube dos
pruebas respecto de `41651d1` porque las dos de CLAUDE-R3-001 son nuevas. Una
cifra sin árbol al lado no se cita como actual (ADR-154).)

## Consecuencias

- **`74/81` → `78/81`** en el suelo de referencia (`--peticion`), sin coste en
  ninguna de las otras tres métricas. Quedan **tres** ocurrencias sin
  recuperar: `MEM-020` (H3) y `MEM-001` (H4), las dos convertidas en
  decisiones de producto del propietario, y `DEC-001`, que este ADR
  reclasifica: **no es del hueco H1**, es de ámbito.
- **ADR-148 queda corregido en dos puntos**, los dos con su comprobación al
  lado: (a) H1 no eran cinco ocurrencias recuperables por vigencia sino
  cuatro, porque `DEC-001` cae en `G4`; (b) «el intervalo llega en la
  `Peticion`» no era cierto: llegaba al intérprete y se tiraba allí.
- **La puerta `category_matching_enabled` sigue cerrada.** Este encargo no la
  toca, y el criterio de aceptación de la memoria (ADR-148) sigue siendo
  47/47, 81/81, 0 y 0.
- **Deuda declarada, no arreglada:** el ámbito de `DEC-001` (una lista cerrada
  sin miembros resueltos), la fecha de sustitución de una decisión
  (`SUPERSEDED` sin cuándo) y la vigencia por memoria (palanca 2). Ninguna se
  abre aquí.
- El ruido que quede lo cierra la palanca 3 (el filtro con la cardinalidad
  conocida), como ADR-148 preveía. Esta vía no le añade trabajo: no sube el
  recuento de «de más» en ninguna configuración.

## Alternativas descartadas y por qué

- **Enumerar las dos clases del canon.** Medida y descartada: `+20`
  elementos de más, todos memorias, y el suelo D1 publicado roto (40 frente a
  21). El sustrato no sostiene la afirmación de vigencia que haría falta para
  incluirlas.
- **Acotar la ventana por abajo** (`created_at >= desde`). Perdería `DEC-005`,
  registrado el 01-01 y vigente durante toda la ventana: una decisión anterior
  a la ventana que nunca terminó **sí** estaba vigente en ella.
- **Recortar por la cota** (`LIMITE_POR_VENTANA` pequeño). Truncar por número
  perdería elementos esperados por casualidad de orden, que es exactamente lo
  que un banco de evidencia existe para no permitir.
- **Deducir la clase de la pregunta** («¿qué **decisiones**…?»). El modelo de
  intención no infiere clase y añadírsela es palanca 1, fuera de alcance; y
  hacerlo por palabras sería volver al problema que esta ficha resuelve.

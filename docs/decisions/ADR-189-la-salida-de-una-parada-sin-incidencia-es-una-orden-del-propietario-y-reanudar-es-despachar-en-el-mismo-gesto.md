# ADR-189 — La salida de una parada sin incidencia es una orden del propietario, y reanudar es despachar en el mismo gesto

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: la fusión de la PR por el propietario. No toca `.github/**` ni
  ningún workflow: vive entero en `src/sirius_engine/` y sus pruebas.

## Contexto y problema

La puerta de sensibilidad para un trabajo **antes** de crear la incidencia: lo
deja anotado en `needs_decision`, sin incidencia detrás, y le dice al
propietario dónde quedó (ADR-184) y por qué (ADR-188). Lo que no existía era
**una salida**.

Medido sobre el diario de la rama `estado-del-motor` el 13-09-2026, leyéndolo
con `git show origin/estado-del-motor:diario.jsonl` y reconstruyendo el estado
de cada trabajo por su último suceso —**635 sucesos, 88 trabajos**—:

| estado | trabajos |
|---|---|
| `delivered` | 56 |
| `cancelled` | 26 |
| `needs_decision` | **4** |
| `active` | 2 |

Los cuatro de `needs_decision` son `WI-20260903-030529`,
`WI-20260903-095428`, `WI-20260912-235558` y `WI-20260913-142937`. Cada uno
tiene **un solo suceso** en su historia —`work_item_created_needing_decision`—
y **ninguno** aparece en `diario-despacho.jsonl`: son el 100 % de las paradas de
la puerta que el diario contiene, y ninguna ha salido nunca. La más antigua
lleva diez días. Los dos del 03-09 son además la misma orden despachada dos
veces.

Por qué no pueden salir, leído en el código y no supuesto: de
`NEEDS_DECISION` sale **una sola arista**, `resolve_decision`
(`src/sirius_engine/domain/work_item.py`), que §3.2 modela como parte de la
decisión registrada. El dominio la tiene y funciona. El único llamante de
producción es el reflector (`src/sirius_engine/reflect.py:1126`; `grep -rn
resolve_work_item_decision src/` no devuelve ningún otro fuera de los dos
adaptadores que la implementan), y el reflector **necesita una incidencia que
mirar**: sin episodio de despacho se salta el trabajo y lo dice con sus propias
palabras —«no consta despachado a ninguna incidencia; no se refleja»,
`reflect_cli.py:168`— seguido de un `continue`. Ninguna orden de
`sirius-despachar` ni de `sirius-motor` expone la arista.

Resultado: **cada vez que la puerta acierta deja un trabajo inmortal**, y cuanto
mejor funciona la puerta más restos deja. ADR-188 acaba de añadirle la quinta
causa, así que la fuga crece.

### Una premisa del encargo, medida y corregida antes de escribir código

El encargo (#615, punto b) dice que `resolve_decision` con `continuar=True`
«deja el trabajo en `active` SIN incidencia detrás, que es exactamente el
agujero en el que lleva desde el 28-08 el `WI-20260828-122242`». **La propiedad
del código es cierta; el caso citado no lo es.**

Medido sobre el mismo diario:

- `WI-20260828-122242` está en `active` y **sí tiene incidencia detrás: la
  #392** (`dispatch_episode_recorded` en `diario-despacho.jsonl`). Su historia
  completa es `work_item_created` + `work_item_activated`: nació por
  `CREAR_Y_ACTIVAR`, no por una parada, y nunca pasó por `resolve_decision`.
  Está varado por otro motivo, que no es el de este ADR.
- El diario tiene **21** sucesos `work_item_decision_resolved`: 16 resolvieron a
  `cancelled` y **5 a `active`** —`WI-20260905-034826`, `WI-20260905-131022` y
  tres de `WI-20260905-202227`—, y **los cinco tienen incidencia detrás**. Son
  las recuperaciones acreditadas del reflector (ADR-147).

O sea: el agujero de (b) **no tiene todavía ninguna instancia**, y el primer
camino de producción capaz de crear una sería precisamente la salida que este
ADR añade. Por eso no se trata como una reparación, sino como algo que hay que
hacer **imposible antes de abrir la puerta**.

## Nota de arranque (cuatro preguntas, ANTES del primer commit de código)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
OBSERVAR el fallo?** El fallo no vive en el dominio —la arista existe— sino en
que **ningún comando la expone**: el fallo vive en la capa de órdenes
(`src/sirius_engine/*_cli.py`). El arreglo va ahí: un comando nuevo,
`sirius-decidir`, que lee el trabajo por su identificador del mismo almacén
durable en el que la parada lo dejó. **Sí puede observarlo**: el trabajo
parado, su estado y su `peticion_original` están en el diario, y la ausencia de
incidencia está en el diario de despacho; el comando lee los dos y no necesita
recordar nada de ninguna pasada anterior. El reflector, en cambio, **no puede
observar este fallo**: su material es la comparación de dos fotos, y de una
parada sin incidencia falta la segunda.

**2. ¿Qué NO va a garantizar esto?**

- **No hace atómicos reanudar y despachar.** Siguen siendo dos escrituras (el
  suceso en el diario del motor y la incidencia en GitHub). Lo que se garantiza
  es que todo lo que se puede saber de antemano se comprueba **antes** de la
  transición, y que si la escritura en GitHub se corta a la mitad, repetir el
  mismo comando **retoma** el despacho en vez de atascarse (la lección de
  ADR-176), apoyado en la adopción por `work_id` de H-29.
- **No desatasca `WI-20260828-122242`** ni ningún trabajo `active` **con**
  incidencia detrás: ese es el territorio del reflector (ADR-173, ADR-176) y el
  comando se niega a tocarlo.
- **No debilita la puerta.** No cambia `gate.py` ni `intent_interpreter.py`: la
  puerta para exactamente las mismas veces, por las mismas cinco causas.
- **No reanuda una parada de la quinta causa** (ADR-188): ahí despachar
  reproduciría la pérdida de la #607, así que el comando lo rechaza y remite a
  la sesión interactiva. Terminarla sí se puede.
- **No lo llama nadie automáticamente.** Es un comando de consola; ningún
  workflow lo invoca (no se toca `.github/**`), así que no aparece ninguna vía
  por la que el ciclo automático pueda saltarse la puerta por su cuenta.
- **No serializa dos invocaciones simultáneas** mejor de lo que ya lo hace el
  diario de despacho, que es dentro de un proceso (misma limitación declarada en
  `dispatcher.dispatch_work_item`). Lo teclea una persona.

**3. Criterio de parada (decidido ANTES de ver ningún resultado)**

- **(a)** Si dar la salida exigiera una arista nueva en el dominio o un puerto
  nuevo, **se para**: eso sería una enmienda de §3.2 y no la decide un encargo.
- **(b)** Si el arreglo pudiera dejar un trabajo en `active` sin incidencia
  detrás en algún camino previsible, **no entra**: cambiar una fuga por otra es
  peor que no arreglar nada, y el encargo lo pide por escrito.
- **(c)** Si alguna prueba de las cinco causas —las cuatro de ADR-184 y la
  quinta de ADR-188— cambiara de resultado o hubiera que retocarla, **se para**:
  la puerta acertó las cuatro veces y el defecto no es que pare.
- **(d)** Si la salida exigiera editar el diario a mano, **no vale**: un diario
  de sucesos encadenados no se edita a mano, y esa es justo la razón por la que
  hace falta una vía.
- **(e)** Ninguna prueba nueva se da por buena sin haberla visto caer contra una
  mutación deliberada (ADR-001 §3), una por cada regla nueva.

**4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que la arista del
dominio **no pudiera existir sin llamante**: eso es la familia
`pieza-sin-lector` y su guardián (ADR-179) es de piezas, no de aristas. Lo que
sí entra hace imposible la mitad que importa: **reanudar y despachar son un
solo gesto del mismo comando**, y todas las razones por las que el despacho
podría no ocurrir —clase no despachable, carril retirado, orden no enlazada,
quinta causa, falta de credencial— se comprueban **antes** de tocar el almacén.
No hay ninguna secuencia del comando que deje el trabajo reanudado y sin
despachar salvo un corte de red a mitad de la escritura, y ese caso lo retoma la
invocación siguiente.

## Opciones consideradas

La incidencia #613 dejó planteadas dos, y el encargo #615 pide elegir con la
medida delante:

1. **Una orden explícita del propietario** que resuelva un trabajo por su
   identificador, diciendo si continúa o si se da por terminado.
2. **Que el reflector aprenda a terminar una parada que NUNCA tuvo
   incidencia**, que sería simétrico con ADR-176 y no añadiría superficie nueva.

## Decisión

**Se elige la opción 1: un comando del propietario, `sirius-decidir`.** Y la
respuesta a «qué pasa al reanudar» es que **reanudar es despachar en el mismo
gesto**: si el despacho no puede ocurrir, la reanudación no ocurre.

El comando, en `src/sirius_engine/decision_cli.py`:

```
sirius-decidir <work_id> (--continuar | --terminar) [--ejecutar] [--repo] [--bloque] [--diario]
```

- **El ensayo es lo que sale por defecto**, por el mismo motivo que en
  `sirius-despachar`: sin `--ejecutar` se enseña qué se haría y no se escribe
  nada. Una decisión sobre el identificador equivocado no es barata.
- **Solo resuelve paradas SIN incidencia detrás.** Si el trabajo tiene
  episodio de despacho, el comando se niega y remite al reflector: ahí el
  desenlace lo acredita GitHub (ADR-173, ADR-176, ADR-147) y no esta orden.
- **`--terminar`** aplica `resolve_decision(continuar=False)`: el trabajo queda
  `cancelled`, que es terminal. Es la salida que las cuatro paradas del diario
  no tenían.
- **`--continuar`** comprueba primero, **sin tocar el almacén**, todo lo que
  puede impedir el despacho —quinta causa de ADR-188, clase fuera de
  `TABLA_ACTIVACION`, carril retirado (ADR-163), orden no enlazada (§12.1) y,
  con `--ejecutar`, que la credencial del motor exista—; solo entonces aplica
  `resolve_decision(continuar=True)` y llama a `dispatch_work_item` en la misma
  invocación.
- **Retoma un despacho interrumpido.** Si el trabajo está en `active` y no
  tiene episodio, `--continuar` no vuelve a pedir la transición: despacha desde
  donde está. Es la lección de ADR-176 aplicada aquí —mirar el estado en el que
  el motor ESTÁ, no el que se esperaba— y es lo que hace que un corte entre las
  dos escrituras no deje otro trabajo inmortal. Y **todo texto de este comando
  nombra el estado real** en vez de fijarlo: el rechazo por falta de credencial
  dice «active» cuando el trabajo está en `active`, y los rechazos de
  `--continuar` no ofrecen `--terminar` desde ahí, porque `_terminar` exige
  `needs_decision` y el dominio no tiene arista `ACTIVE -> CANCELLED` (§3.2).
  Ese trabajo queda como asunto del propietario en sesión interactiva: el
  dominio no se enmienda, se corrige lo que el mensaje promete.
- **Los fallos operativos de `gh` se traducen en el adaptador, por FAMILIA y
  no por enumeración.** `gh` no falla solo con código distinto de cero: lanzar
  el proceso hijo falla con tantos errnos como tiene el `exec` —no instalado es
  `FileNotFoundError` [Errno 2], instalado pero no ejecutable (permisos, un
  montaje `noexec`) es `PermissionError` [Errno 13], binario corrupto o de otra
  arquitectura es `OSError` [Errno 8]—, todos ellos `OSError`; aparte quedan
  `subprocess.TimeoutExpired` a los 60 s, que NO es `OSError` y lleva su propia
  cláusula, y `JSONDecodeError` cuando la respuesta de adopción no es JSON.
  `GitHubCliWriter` los convierte en `GitHubWriteError` —el error del puerto—,
  que es lo único que `_continuar` captura; si no, el comando terminaba con una
  traza justo después de haber persistido `needs_decision -> active`, sin decir
  que hay que repetir la orden para retomar el despacho. La primera versión de
  esta guarda enumeraba dos miembros en vez de la familia (CLAUDE-R2-001): la
  lección del repositorio —«una lista siempre tiene un hueco más»— también
  gobierna una cláusula `except`.
- **La salida queda al alcance del propietario sin tocar el diario**: la parada
  de `sirius-despachar` nombra el comando exacto con el `work_id` y la ruta del
  diario ya puestos, y `/trabajos` lo recuerda cuando lista algo en
  `needs_decision` —también con `--diario` y `--ejecutar`, porque la sesión se
  abre a menudo contra un diario que `sirius-decidir` no resolvería solo y sin
  `--ejecutar` la orden copiada solo haría el ensayo, y con `--repo`/`--bloque`
  cuando la orden original no usó sus valores por defecto, porque el `WorkItem`
  NO los persiste y sin ellos la orden copiada crearía la incidencia en el
  repositorio y con el encargo por defecto: una escritura externa e irreversible
  al destino equivocado (CLAUDE-R2-002)—. Y la condición para
  ofrecer `--continuar` es **«este trabajo puede despacharse»**, no «no es la
  quinta causa»: se comprueban también la clase (`TABLA_ACTIVACION`) y el carril
  retirado, que son los otros dos motivos por los que `_no_se_puede_despachar`
  sale con 5. Una orden sensible que el intérprete v0 no clasifica como
  programación —«Borra la base de producción»— para por la cuarta causa con clase
  `consulta-larga`, y ofrecerle `--continuar` sería prometer un despacho que no
  va a ocurrir. El camino que ADR-184 abrió —«abre `sirius-motor` y teclea
  `/trabajos`»— dejaba de existir justo donde hacía falta.
- **Y «puede despacharse» pregunta por el ALCANCE, no por la causa
  (CLAUDE-R3-001).** La primera versión de esta decisión daba por equivalentes
  «no paró la quinta causa» y «se puede despachar», y razonaba solo sobre «Borra
  la base de producción», que la guarda de clase ya atrapa. No son equivalentes,
  y el repositorio lo tenía fijado por escrito desde antes
  (`test_las_cuatro_causas_anteriores_siguen_ganando_a_la_quinta`): las cuatro
  causas anteriores GANAN a la quinta cuando una orden dispara las dos cosas,
  porque `_detectar_sensibilidad` consulta la quinta la última. «Corrige el
  arranque y borra `.github/workflows/quality.yml`» sale con causa
  `operacion_destructiva_o_irreversible` —así que `paro_la_quinta_causa` dice
  `False`— y con clase `programacion`, que tiene despachador y carril vivo: se
  le ofrecía `--continuar`, y `--continuar` creaba la incidencia. De ahí colgaba
  un ciclo entero que haría el trabajo y lo perdería al empujar, porque el
  alcance cae bajo `.github/**` (ADR-002): la pérdida de la #607, reabierta por
  la salida que este ADR añade —antes de ella ninguna parada podía despacharse,
  así que la protección de ADR-188 se sostenía sola—. Lo que mata el push es el
  alcance, no la causa, así que la pregunta que gobierna el ofrecimiento
  (`dispatch_cli._por_que_no_se_puede_continuar`) y el rechazo
  (`decision_cli._bloque_de_la_quinta_causa`) es
  `alcance_que_el_motor_no_puede_escribir(...) is not None`. La ATRIBUCIÓN de la
  causa NO cambia: el bloque de ADR-188 de `sirius-despachar` se sigue emitiendo
  solo cuando fue la quinta la que paró (CLAUDE-REV-612-001), y en una parada
  por causa anterior la única mención de la sesión interactiva es el paréntesis
  que niega `--continuar`.

Ni un puerto nuevo ni una arista nueva en el dominio: `resolve_decision` ya
existía y era la única salida de `NEEDS_DECISION`; lo que faltaba era alguien
que la llamara.

## Comprobación que la sostiene

- **La medida del diario real**, arriba: `git show origin/estado-del-motor:diario.jsonl`
  y `:diario-despacho.jsonl`, 635 sucesos, 88 trabajos, 4 paradas sin salida, 21
  `work_item_decision_resolved` -16 a `cancelled`, 5 a `active` y las cinco con
  incidencia detrás- y ninguna instancia del agujero de (b).
- **Las cuatro paradas son de clase `programacion`**, así que las cuatro tienen
  las dos salidas disponibles salvo la que pare por la quinta causa, que solo
  tiene `--terminar`.
- **La cadena obligatoria completa, en verde**: una sola invocación de
  `pwsh -File scripts/check.ps1` —que encadena `ruff format --check`,
  `ruff check`, `mypy src tests` y `pytest`— **sobre el árbol de `0adc795b`**,
  con código de salida **0** y **6583 pasan, 17 se saltan, 2 xfail**, en
  626,84 s (0:10:26). La cifra anterior de este ADR —6581 pasan, en 530,90 s—
  era la del árbol de `5c5d8827`, antes de la corrección de la ronda 5; las dos
  pruebas nuevas son las de CLAUDE-R4-001 y CLAUDE-R4-002, y ninguna de las dos
  cambia un fuente: que `--continuar --repo … --bloque …` despacha DE VERDAD en
  ese repositorio y bajo ese bloque —hasta ahora solo estaba fijada la mitad que
  IMPRIME la orden copiable—, y que `--continuar` sobre un trabajo ya terminado
  sale con 4 sin tocar nada, que es la rama negativa de `_ESTADOS_QUE_CONTINUAN`.
  Antes de esa ronda, el árbol de `8f194d4d` medía 6579. La aserción reescrita de
  `test_una_parada_por_una_causa_anterior_no_promete_el_despacho_de_la_quinta`
  no suma un test: acota a la ATRIBUCIÓN lo que antes prohibía en todo el texto,
  porque el paréntesis que niega `--continuar` sí remite a la sesión interactiva
  —y la mutación de la atribución se sigue viendo caer con ella, ahora en la
  aserción de «vuelve a despachar»—.
- **28 mutaciones vistas caer**, una por regla nueva (ADR-001 §3), cada una
  anotada en el docstring de la prueba que la caza con el mensaje exacto del
  rojo. La lista, con la prueba que la detiene:

  | Mutación | Lo que deja de cumplirse |
  |---|---|
  | `continuar=False` → `True` en `_terminar` | terminar termina |
  | quitar la rama `estado is CANCELLED` | terminar dos veces no es un error |
  | quitar la guarda `if not ejecutar` | el ensayo no aplica nada |
  | volver antes de `dispatch_work_item` en ensayo | el ensayo atraviesa las guardas (H-12) |
  | quitar `dispatch_work_item` de `_continuar` | reanudar despacha en el mismo gesto |
  | construir el escritor DESPUÉS de la transición | sin credencial no se reanuda nada |
  | quitar la comprobación de clase | una clase sin despachador no se reanuda |
  | quitar la de `orden_enlazada` | §12.1 sin excepción |
  | `bloqueo = None` (quinta causa) | la quinta causa no se reanuda |
  | exigir la quinta causa también en `_terminar` | la quinta causa sí se termina |
  | quitar `ACTIVE` de `_ESTADOS_QUE_CONTINUAN` | un despacho cortado se retoma |
  | quitar la condición `estado not in _ESTADOS_QUE_CONTINUAN` de `_continuar` | la rama NEGATIVA: desde `cancelled` se rechaza con 4, no con una traza (CLAUDE-R4-002) |
  | quitar la guarda de `episodio_previo` | con incidencia detrás decide el reflector |
  | `return 0` en vez de `return 2` | un work_id que no existe no inventa nada |
  | quitar el bloque de la salida de la parada | la parada dice con qué orden se sale |
  | quitar `--diario` de la orden copiable | la orden se copia tal cual |
  | quitar `--repo` de la orden copiable | la orden que imprime la parada ARRASTRA el repo y el bloque de la original |
  | `repo=REPO` en la llamada a `dispatch_work_item` de `_continuar` | y la orden copiada despacha DE VERDAD en ese repo, no en el de por defecto (CLAUDE-R4-001) |
  | `bloque="ENCARGO"` en esa misma llamada | ni bajo otro bloque: el título creado empieza por el que se pidió |
  | ofrecer `--continuar` en la quinta causa | ahí no se ofrece lo que no lleva a nada |
  | ofrecer `--continuar` con una clase sin despachador | tampoco se ofrece lo que saldría con 5 |
  | `alcance_vetado=prefijo_vetado` en la llamada de `sirius-despachar` | el alcance vetado niega `--continuar` aunque parase otra causa |
  | devolver la guarda `paro_la_quinta_causa` en `_bloque_de_la_quinta_causa` | `sirius-decidir` no despacha un alcance vetado, pare la causa que pare |
  | quitar `--diario`/`--ejecutar` de la orden de `/trabajos` | el aviso de la sesión se copia tal cual |
  | estrechar `except OSError` a `except FileNotFoundError` en `GitHubCliWriter._invocar` | TODO fallo operativo de `gh` sale como el error del puerto, no solo dos |
  | fijar «needs_decision» en el mensaje sin credencial | el estado se nombra, no se fija: al retomar es «active» |
  | ofrecer `--terminar` también desde `active` | `--terminar` solo es salida desde `needs_decision` (§3.2) |
  | avisar en `/trabajos` sin condición / no avisar | el aviso sale cuando hay algo que decidir, y solo entonces |

  **Una de esas mutaciones enseñó algo que no se buscaba**: sustituir `return 2`
  por `return 0` no cambia el TAMAÑO del fichero, y restaurarlo dentro del mismo
  segundo deja el `.pyc` viejo dado por válido -Python compara mtime en segundos
  y tamaño-, así que la pasada siguiente corría bytecode mutado sin que nada lo
  dijera. El guion de mutación borra ahora `__pycache__` en los dos sentidos.
  Vale la pena anotarlo: una prueba por mutación que no controle eso puede dar
  por bueno un rojo o un verde que no son del código en disco.

## Consecuencias

- Las cuatro paradas del diario tienen salida a partir de ahora, y la tiene el
  propietario con un comando, sin editar ningún fichero de sucesos.
- Hay un camino de producción que puede llevar un trabajo de `needs_decision` a
  `active`. Está acotado: lo teclea una persona, no lo llama ningún workflow, y
  no puede terminar en `active` sin incidencia detrás.
- `sirius-despachar` gana tres nombres públicos —`diario_de_despacho`,
  `ruta_copiable` y `paro_la_quinta_causa`— porque el comando nuevo los usa. Se
  renombran en vez de copiarse: una quinta copia de la regla del diario de
  despacho es exactamente la `lista-a-mano` que ADR-178 cerró.

## Alternativas descartadas y por qué

**Que el reflector termine la parada sin incidencia (opción 2).** Descartada por
tres razones medidas, no por gusto:

1. **No tiene nada que observar.** ADR-176 cancela apoyado en un hecho del
   mundo —la incidencia está cerrada, que es un gesto del propietario—. Una
   parada sin incidencia no tiene ese hecho: lo único que pasa es el tiempo.
   Cancelar sin hecho sería el motor decidiendo justo lo que la puerta se negó a
   decidir. La simetría con ADR-176 es aparente: allí se **retoma** un cierre ya
   empezado por un hecho observado.
2. **Solo sabe una de las dos mitades.** La puerta para porque hace falta la
   decisión del propietario, y «continúa» es la mitad que un reflector nunca
   puede acreditar. Un mecanismo que solo puede descartar no contesta (b), y (b)
   es parte del encargo.
3. **No deja la salida al alcance del propietario**, que es el requisito (d):
   una pasada automática no le da una vía, le quita la decisión.

**Añadir una arista `NEEDS_DECISION -> CANCELLED` directa al dominio.** No hace
falta —`resolve_decision(continuar=False)` ya lleva ahí— y sería una enmienda de
§3.2: criterio de parada (a).

**Dejar `--continuar` sin despacho, como transición suelta.** Es exactamente la
fuga de (b): criterio de parada (b), y por eso el despacho va en el mismo gesto.

## La lección

- familia: `estado-en-el-que-se-entra-y-del-que-no-se-sale`
- sin esto se repetiría: dar por buena una arista del dominio que en producción no llama nadie, y dejar así un estado en el que el motor entra solo y del que solo puede salir un mecanismo que necesita un dato que ese estado, por definición, no tiene.
- lo hace cumplir: `tests/engine/test_decision_cli.py`

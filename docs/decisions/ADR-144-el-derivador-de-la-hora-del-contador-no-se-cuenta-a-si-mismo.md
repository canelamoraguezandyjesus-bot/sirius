# ADR-144 — El derivador de la hora del contador no se cuenta a sí mismo

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]
- Encargo: WI-20260905-131022 (incidencia #541)

Este ADR es **además la nota de arranque de la rama**: sus cuatro preguntas y
su criterio de parada se escribieron y se publicaron ANTES del primer cambio de
código, con la medida previa ya observada pero sin ninguna línea del arreglo
escrita.

## Nota de arranque (antes del primer commit)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en
   `hora_recomendada_pasada()` (`src/sirius_engine/seven_day_streak.py`): lee
   TODOS los `schedule: cron:` de `.github/workflows/*.yml` para responder «¿a
   qué hora está más tranquilo el repositorio para la PASADA del contador?», y
   entre esos crons cuenta el del propio consumidor de la respuesta,
   `contador-siete-dias.yml`. El arreglo va exactamente ahí: la lectura excluye
   por NOMBRE el fichero del contador. ¿Puede el sitio del arreglo observar el
   fallo que arregla? El derivador no puede: cualquier hora que devuelva la
   sigue viendo como «un cron más» la próxima vez. Por eso el arreglo no se
   defiende solo con el derivador, sino con el guardián-oráculo
   `test_hora_recomendada_atada_al_schedule_real_del_repositorio`, que es un
   TERCERO («YAML aparte», sin importar nada del motor) y aplica la misma
   exclusión por su cuenta, más un pin del número medido (03:24 UTC) que
   ninguno de los dos lectores puede mover en silencio.
2. **¿Qué NO garantiza esto?** No garantiza que la pasada del contador llegue
   puntual ni que mida su propia ventana al llegar: los retrasos de entrega de
   GitHub (entrada 36 de la bitácora) quedan FUERA por decisión registrada del
   propietario, en ficha posterior. No cambia ningún fichero de `.github/**`:
   el `cron '24 3 * * *'` sigue tal cual, y este arreglo solo hace que la
   cabecera que lo declara «derivado» vuelva a ser verdad. No pone al día la
   medida histórica de ADR-143 (09:24): esa medida se conserva y se le añade el
   desenlace. No convierte 03:24 en un pin eterno: es el número que el árbol
   REAL de hoy deriva, y se moverá si se mueven los otros `schedule:`. Y no es
   un filtro genérico de «workflows que consumen la hora»: es una exclusión
   nombrada, la del único consumidor que hay.
3. **Criterio de parada** (decidido antes de ver ningún resultado del arreglo):
   (a) si la derivación con la exclusión NO diera exactamente 03:24 UTC («345
   min tras las 00:32»), se para: sería señal de que el diagnóstico de ADR-143
   no era la única causa y de que la hora cableada en `.github/**` habría que
   moverla, lo cual está fuera de este encargo; (b) si excluir el contador
   hiciera fallar `test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia`
   o el guardián de equivalencia de los dos lectores de cron (ADR-143), se para
   y se escala: el encargo prohíbe retocar esos guardianes; (c) si aparecieran
   dos rondas de defectos de la misma familia («otro consumidor que también se
   autoincluye»), se para de excluir ficheros sueltos y se busca la raíz.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Lo imposible de
   verdad sería que la pregunta no se pudiera formular mal: que el derivador
   recibiera SIEMPRE, como parámetro obligatorio, de quién es la hora que
   deriva, y no pudiera contar sus propios disparos. No se hace porque el
   encargo pide una exclusión nombrada y del único consumidor que existe hoy, y
   porque un parámetro obligatorio cambiaría la firma pública que usa
   `sirius-racha --hora-recomendada` y sus pruebas, ampliando el alcance. Lo
   segundo mejor, y es lo que se hace: la autoinclusión no puede volver a ser
   SILENCIOSA. El guardián-oráculo pinta el número exacto del árbol real
   (03:24) y aplica la exclusión por su lado; si alguien la quita del motor, el
   pin se pone rojo con el número que salga.

## Contexto y problema

`hora_recomendada_pasada()` responde a una pregunta concreta: cuál es el
momento del día más alejado de cualquier disparo periódico, para que la pasada
del contador de los siete días encuentre las etiquetas ya aterrizadas y el día
pueda salir VERDE (cierre de la incidencia #265, ADR-093).

El 25-08-2026, cuando esa hora se derivó por primera vez, `contador-siete-dias.yml`
todavía no existía: la derivación dio **03:24 UTC — punto medio del mayor hueco
libre (345 min, tras las 00:32)**, y ese número se cableó en el `cron` del
workflow que se creó a continuación, con la cabecera declarándolo derivado.

Desde ese momento la derivación dejó de dar 03:24: el disparo del propio
contador partió en dos el hueco de 345 min del que salía, y la derivación saltó
al siguiente hueco de 345 min, **09:24 UTC (tras las 06:32)**. Lo midió y lo
dejó escrito ADR-143 (sección «El límite de las 03:24 lo enmendó el
propietario»), que además comprobó la raíz: con el mismo árbol pero sin
`contador-siete-dias.yml`, la derivación vuelve a dar 03:24. Aquel encargo no
podía arreglarlo —tocaba otra cosa, el dialecto de cron— y lo mandó a ficha
propia.

Ésta es esa ficha. La decisión del propietario (05-09-2026, pregunta de la
deuda 14) es arreglar AHORA la autoinclusión y dejar «la pasada mide su propia
ventana al llegar» para después.

El fondo del asunto no es aritmético sino de sentido: la pregunta que el
derivador responde es «¿cuál es la hora más tranquila **para la pasada del
contador**?», y la propia pasada no puede estorbarse a sí misma. Es la misma
propiedad que `tests/automation/test_contador_de_siete_dias.py` ya aplicaba por
su lado en `_tranquilidad_antes_de` —«se excluye el propio minuto: un workflow
no se estorba a sí mismo, y contarlo daría siempre cero»— y que al derivador se
le había quedado sin aplicar.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3, palabra por palabra. Ninguno de sus tres
supuestos se disparó: la derivación con la exclusión da exactamente 03:24 UTC,
los dos guardianes que el encargo protege siguen en verde sin retocarlos, y no
hubo dos rondas de la misma familia.

## Opciones consideradas

1. **Un filtro genérico** («excluir cualquier workflow que invoque
   `sirius-racha`», o «excluir el workflow cuyo cron coincida con la hora
   derivada»). Descartada por el encargo, y con razón: un filtro que adivina
   quién es el consumidor puede excluir de más el día que otro workflow llame
   al comando, y lo haría en silencio. La exclusión nombrada dice exactamente
   qué se excluye y por qué.
2. **Pasar el consumidor como parámetro obligatorio del derivador.** Es lo que
   haría el fallo imposible (nota de arranque, punto 4), y por eso está en la
   nota; queda fuera porque cambia la firma pública y amplía el alcance.
3. **Mover el `cron` del contador a la hora derivada de hoy (09:24).** Es
   perseguirse la cola: cablear 09:24 volvería a partir ESE hueco y la
   derivación saltaría a otro sitio. Además `.github/**` no se toca en este
   encargo.
4. **Exclusión nombrada y documentada del fichero del contador, aplicada
   también por el guardián-oráculo por su cuenta.** La elegida.

## Decisión

`hora_recomendada_pasada()` no cuenta los disparos de
`.github/workflows/contador-siete-dias.yml` —el workflow que CONSUME la hora que
deriva— al buscar el mayor hueco libre. La exclusión es por nombre de fichero,
está declarada en una constante propia
(`NOMBRE_DEL_WORKFLOW_DEL_CONTADOR`) y documentada en el docstring de la
función.

Tres precisiones que forman parte de la decisión:

- **Solo se excluyen sus disparos.** La ventana de tolerancia
  (`ventana_tolerancia_etiqueta_maquina`) sigue derivándose del `timeout-minutes`
  de TODOS los workflows, el del contador incluido: ahí sí cuenta, porque un job
  largo del contador retrasa etiquetas igual que cualquier otro.
- **Si el fichero no está, no pasa nada.** La exclusión es una resta sobre lo
  que haya: en un directorio sin `contador-siete-dias.yml` —una copia de
  pruebas, o un renombrado accidental— el derivador funciona exactamente como
  hoy, derivando sobre todo lo que encuentra. No exige que el fichero exista.
- **El guardián-oráculo aplica la MISMA exclusión por su lado**, sin importar
  nada del motor (disciplina «YAML aparte», ADR-143), para que la comparación
  siga midiendo lo mismo; y además pinta el número medido, 03:24 UTC, para que
  quitar la exclusión del motor no pueda pasar en silencio.

## Comprobación que la sostiene

**La medida previa, tomada antes de tocar ninguna línea** (`uv run python`
sobre `main`, con el árbol real de `.github/workflows` y con una copia sin
`contador-siete-dias.yml`):

```
con contador: (datetime.time(9, 24), 'punto medio del mayor hueco libre de disparos periódicos (345 min, tras las 06:32 UTC)')
sin contador: (datetime.time(3, 24), 'punto medio del mayor hueco libre de disparos periódicos (345 min, tras las 00:32 UTC)')
```

Es la misma medida que ADR-143 registró el 05-09-2026, reproducida hoy: 09:24
es la medida histórica y no se reescribe; 03:24 es el desenlace que este ADR le
añade.

**El rojo previo, visto fallar antes del arreglo**: la prueba nueva
`test_hora_recomendada_del_arbol_real_no_cuenta_el_cron_del_propio_contador`
(pin de 03:24) contra el derivador autoincluyente vigente:

```
AssertionError: assert datetime.time(9, 24) == datetime.time(3, 24)
```

**Después del arreglo**, en `tests/engine/test_seven_day_streak.py`:

- `test_hora_recomendada_del_arbol_real_no_cuenta_el_cron_del_propio_contador`:
  el pin del árbol real, 03:24 UTC, con el motivo «345 min, tras las 00:32».
- `test_hora_recomendada_no_cuenta_los_disparos_del_workflow_del_contador`: con
  un directorio de pruebas donde el fichero del contador SÍ está, sus disparos
  no mueven la derivación (misma hora que sin él).
- `test_hora_recomendada_deriva_sobre_lo_que_hay_si_el_contador_no_esta`: el
  otro lado del caso de aceptación —un directorio sin ese fichero deriva sobre
  lo que hay, sin exigir que exista—.
- `test_un_contador_renombrado_vuelve_a_contarse_sin_reventar`: el precio
  declarado de que la exclusión sea nombrada; un renombrado accidental degrada
  a «como antes de este ADR», nunca a un error.
- `test_hora_recomendada_atada_al_schedule_real_del_repositorio`: el
  guardián-oráculo, con la misma exclusión aplicada por su lado.

Y en `tests/automation/test_contador_de_siete_dias.py`:

- `test_el_cron_cableado_del_contador_es_la_hora_que_el_derivador_devuelve`: el
  guardián que **compara los dos lados**, el cron cableado en `.github/**` y la
  hora que devuelve el derivador. Sin él, la primera consecuencia de este ADR
  -«la cabecera vuelve a ser verdad sola»- descansaba en dos pines que nunca se
  miraban entre sí: uno fija lo que DERIVA el motor y el otro solo exige que el
  cron CABLEADO deje pasar la tolerancia. Entre los dos cabía una hora que
  cumpliera la tolerancia sin ser la derivada -`0 5 * * *`: 268 min tranquilos
  contra 170 de tolerancia-, y con ella la cabecera pasaría a mentir en
  silencio. No es circular: el derivador excluye por nombre los disparos de ese
  mismo fichero, así que el número con el que se compara no depende del cron que
  se comprueba.

**Prueba por mutación** (ADR-001), tres direcciones. **Todas las corridas de
este bloque, mutadas y de control, se hicieron sobre el MISMO par de ficheros**
—`tests/engine/test_seven_day_streak.py` más
`tests/automation/test_contador_de_siete_dias.py`, que recolectan **177
items**—, de modo que las cifras de cada bullet suman siempre ese total y se
pueden comparar entre sí:

- **El motor vuelve a contarse a sí mismo** (sustituido por `pass` el `continue`
  de la exclusión en `hora_recomendada_pasada`): `4 failed, 173 passed`. Los
  cuatro rojos son el pin del árbol real (`9:24 != 3:24`), el caso sintético del
  fichero presente (`6:00 != 12:00`), el guardián-oráculo —que sigue aplicando
  la exclusión por su lado y por eso detecta la divergencia— y el guardián del
  cron cableado, que ve `[204]` en `.github/**` contra `564` derivado.
- **La exclusión se cae SOLO del guardián-oráculo** y el motor la conserva:
  `1 failed, 176 passed`, y el rojo es exactamente
  `test_hora_recomendada_atada_al_schedule_real_del_repositorio`
  (`assert datetime.time(3, 24) == datetime.time(9, 24)`) —el tercero
  detectando que los dos lados dejaron de medir lo mismo, que es para lo que
  existe—.
- **El cron cableado deja de ser la hora derivada.** Esta mutación NO se hace
  sobre `.github/**` —el encargo lo prohíbe— sino sobre una copia entera del
  árbol en un directorio temporal, ejecutada con `PYTHONPATH` apuntando al `src`
  de la copia para que el derivador lea el `.github` de la copia y no el real.
  Allí el cron del contador pasa de `'24 3 * * *'` a `'0 5 * * *'`, una hora que
  **sigue cumpliendo la tolerancia** (268 min tranquilos contra 170):
  `1 failed, 176 passed`, y el rojo es exactamente
  `test_el_cron_cableado_del_contador_es_la_hora_que_el_derivador_devuelve`
  (`assert {300} == {204}`). El pin de las 03:24 y el guardián de tolerancia se
  quedan los DOS en verde: ésa es la rendija por la que la cabecera podía pasar
  a mentir en silencio, y es la que este guardián cierra. Sin mutar, la misma
  copia da `177 passed`, que es el control de que la copia se estaba midiendo a
  sí misma.
- Restaurado el árbol, sobre ese mismo par: `177 passed`.

Vistas fallar ANTES de escribir la exclusión (`3 failed, 6 passed` en la
selección `-k "contador or atada or hueco"`): las DOS pruebas nuevas que fijan
la propiedad —el pin del árbol real y el caso sintético— más el guardián-oráculo
ya adaptado. Las otras dos nuevas
(`..._deriva_sobre_lo_que_hay_si_el_contador_no_esta` y
`..._renombrado_vuelve_a_contarse_sin_reventar`) pasan igual antes y después, y
eso es exactamente lo que afirman: fijan el lado que este cambio NO debe mover.
Se dice aquí en vez de contarlas como rojos previos que no fueron.

La quinta prueba, el guardián del cron cableado, no existía en aquella corrida:
nació de la primera ronda de revisión de esta rama, que vio que la consecuencia
declarada abajo no tenía guardián. Su rojo es la tercera mutación del bloque
siguiente, y por eso no aparece aquí.

**Validaciones obligatorias**, con una sola invocación de
`pwsh -File scripts/check.ps1` sobre el árbol final de la rama —el script
encadena las cuatro y no se parte en tandas—:

- `uv run ruff format --check .` → «602 files already formatted»;
- `uv run ruff check .` → «All checks passed!»;
- `uv run mypy src tests` → «Success: no issues found in 570 source files»;
- `uv run pytest` → «collected 4955 items» y
  «4938 passed, 15 skipped, 2 xfailed in 426.07s (0:07:06)».

De la salida del script se conservó el resumen final de `pytest`; las tres
primeras líneas se transcriben de una reejecución inmediata de esos mismos tres
comandos, uno a uno, sobre el mismo árbol.

Un solo proceso de `pytest` y un solo juego de fixtures de sesión; el script
terminó con código de salida 0.

**Seis items recolectados más que la base** -y no cuatro, como decía la primera
redacción de este párrafo, que además situaba la base en 4950-: medido hoy con
`uv run pytest --collect-only -q` sobre las dos versiones del árbol, `main`
(`78e81fc`) en un `git worktree` aparte da **4949** y esta rama **4955**.
Comparando con `diff` las dos listas de ids recolectados, la diferencia son
exactamente seis y ninguna más: las CINCO pruebas que este encargo añade -las
cuatro de `tests/engine/test_seven_day_streak.py` y el guardián del cron
cableado de `tests/automation/test_contador_de_siete_dias.py`- más un caso
parametrizado que no es una prueba nueva sino el propio fichero de este ADR:
`tests/automation/test_citas_de_los_adr.py::test_toda_ruta_citada_por_un_adr_existe`
parametriza por fichero de `docs/decisions/`, de modo que cada ADR nuevo suma
un caso.

`git diff --check` sobre el árbol: sin salida.

Esa captura se hizo sobre el árbol final de código y pruebas; lo único que
cambió después son las cifras y los nombres transcritos en esta misma sección.
Como en `docs/decisions/` sí hay guardianes que leen —los de
`tests/automation/`—, se volvieron a correr sobre el árbol exacto que se
commitea: `uv run ruff format --check .` → «602 files already formatted», y
`uv run pytest tests/automation tests/engine/test_seven_day_streak.py` →
«1312 passed, 10 skipped in 173.13s (0:02:53)». Nada de lo medido arriba
dependía de este párrafo, y lo único que cambió después de esa última corrida
son estas dos cifras al transcribirlas.

## Consecuencias

- La cabecera de `contador-siete-dias.yml` («03:24 UTC — punto medio del mayor
  hueco libre (345 min, tras las 00:32)») vuelve a ser verdad **sola**, sin
  nota al pie: `uv run sirius-racha --hora-recomendada` sobre este árbol imprime
  exactamente ese número y ese motivo. Ninguna línea de `.github/**` cambia en
  este encargo, y ninguna hace falta que cambie. Y no se queda en afirmación:
  lo vigila
  `test_el_cron_cableado_del_contador_es_la_hora_que_el_derivador_devuelve`,
  que compara el cron cableado con la hora derivada y se pone rojo el día que
  dejen de coincidir —incluso si la hora nueva siguiera cumpliendo la
  tolerancia, que es el caso en el que nadie más se enteraría—.
- ADR-143 conserva su medida del 05-09-2026 (09:24) como lo que fue —la medida
  del árbol autoincluyente— y gana el desenlace: la ficha que anunciaba es
  ésta.
- La deuda que sigue abierta, declarada: la pasada **no** mide su propia
  ventana al llegar. Si GitHub entrega el disparo con retraso, la tranquilidad
  real puede ser menor que la derivada, y nada lo detecta todavía. Es la ficha
  posterior que el propietario dejó decidida el 05-09-2026.
- Si algún día hay un SEGUNDO consumidor de esta hora, la exclusión nombrada se
  quedará corta y habrá que decidir de verdad (parámetro, lista, o lo que
  proceda). Está escrito aquí para que ese día se vea, en vez de añadir un
  nombre más.

## Alternativas descartadas y por qué

- **Filtro genérico por contenido del workflow**: adivina quién consume la hora
  y puede excluir de más en silencio; la exclusión nombrada se lee y se audita.
- **Tocar el `cron` del contador**: prohibido por el encargo, y además
  perseguiría su propia cola.
- **Fijar 03:24 como constante en el código**: sería exactamente lo que la nota
  de arranque de ADR-093 prohíbe —escribir la hora a ojo—. 03:24 se pinta en
  una PRUEBA, como medida del árbol real, no en el derivador.

# ADR-074 — El contador de los siete días deriva la corrección manual del diario de eventos del motor

- Estado: APROBADO
- Fecha: 2026-08-22
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

El contrato §11.2 exige, para conmutar la autoridad de una clase de la
incidencia al motor, **dos** condiciones medidas sobre la misma clase: siete
días naturales consecutivos en verde, y cero correcciones manuales del
estado en ese periodo. El verificador de proyección (D1a, incidencia #265,
`sirius_engine.projection_verifier`) sabe comparar el motor con su
incidencia UNA vez y decir si un día es verde -pero eso solo cubre la
condición 1. Nada en el repositorio, comprobado al escribir la incidencia
#268, registra que una persona o una sesión arregló a mano el almacén o las
etiquetas porque discreparan: la condición 2 no era medible.

Este bloque (D1b, incidencia #268) construye tres piezas -el registro
versionado, el detector de la condición 2, y el contador que camina hacia
atrás por clase- y las cablea en un punto de entrada (`sirius-racha`) que
ejecuta una pasada diaria y publica la medición. **No conmuta nada.**

## Criterio de parada (escrito ANTES de decidir)

Las cuatro de la nota de arranque de la incidencia #268, publicada antes de
escribir código:

- (a) Si la condición 2 acaba dependiendo de que una persona se acuerde de
  anotar algo, se para: un registro que nadie rellena se lee como «cero
  incidencias», el falso verde que ADR-033 ya nombró.
- (b) Si al medir sobre el registro real resulta que ningún día puede salir
  verde con la tolerancia vigente, se para y se trae la medición.
- (c) Si hace falta crear o editar un workflow (`.github/**`) para que esto
  se ejecute, se para (ADR-002).
- (d) Si hace falta cambiar el verificador de D1a para que el contador
  funcione, se para.

## Opciones consideradas

**Para la condición 2 (correcciones manuales), tres formas de derivarla:**

- **A. Pedir que quien corrija a mano dispare un campo o comentario
  marcador.** Descartada de inmediato: es exactamente el criterio de parada
  (a) -disciplina humana, no observación del sistema.
- **B. Comparar, dentro de una misma `DIVERGENCIA`, el valor `motor=` de un
  día con el `espejo=` del día anterior (y viceversa), buscando que el motor
  hubiera "aprendido" del espejo.** Descartada: `VeredictoEje.motivo` es
  `None` en un `COINCIDE` (D1a, por diseño: «un `NO_COMPARABLE` sin motivo o
  una `DIVERGENCIA` sin decir en qué difieren no serían auditables»), así
  que el valor en el que una `DIVERGENCIA` se resuelve no queda escrito en
  ningún `COINCIDE` posterior. Reconstruirlo exigiría cambiar el formato de
  registro de D1a -criterio de parada (d).
- **C. Cruzar el registro con el diario de eventos del motor
  (`sirius_engine.domain.events.Event`, ya expuesto por
  `WorkEngineStore.list_events()`, sin cambios de puerto).** Una
  `DIVERGENCIA` en un eje que se resuelve a `COINCIDE` entre dos líneas
  consecutivas del mismo `work_id` sin que el diario registre NINGUNA
  transición de ese `work_id` en el intervalo es la huella: el motor solo
  cambia su propio estado a través de sus transiciones tipadas, y cada una
  de ellas queda en el diario (arquitectura §3.5/§12). **Elegida.**

**Para la hora de la pasada (requisito 5), dos formas de justificarla:**

- **A. Elegir una hora "tranquila" a ojo (de madrugada, por ejemplo).**
  Descartada explícitamente: es el criterio de parada (b) -y el cierre de la
  incidencia #265 ya midió que la ventana 4 protege un día verde solo si
  nada se movió en las tres horas previas, así que la hora importa de
  verdad, no es un detalle cosmético.
- **B. Derivar la hora del `schedule: cron:` real de
  `.github/workflows/*.yml`: el punto medio del mayor hueco libre de
  disparos periódicos, validado contra
  `ventana_tolerancia_etiqueta_maquina()`.** **Elegida.** Mismo criterio que
  esa función ya aplica al propio `timeout-minutes`: se deriva de lo que hay
  en el repositorio, no se escribe a mano, y si algún día el hueco se
  estrecha por debajo de la tolerancia, la función lo dice explícitamente en
  vez de devolver una hora que ya no protegería nada.

## Decisión

1. **Registro** (`docs/operations/racha_siete_dias.jsonl`, dato versionado):
   JSONL append-only. `anadir_lineas` deduplica por texto exacto (mismo
   `formatear_linea` de D1a) para que dos pasadas con el mismo `instante`
   -el caso de una prueba con reloj congelado- no dupliquen ni pierdan
   líneas (requisito 6); dos pasadas reales, con `instante` distinto, nunca
   coinciden por accidente.
2. **Detector de corrección manual**
   (`seven_day_streak.detectar_correcciones_manuales`): opción C de arriba.
   Deliberadamente no exhaustivo -no cubre una corrección que además
   reescribiera el diario de eventos-, pero deriva de dos fuentes que el
   sistema ya observa (el propio registro y el diario del motor), nunca de
   que alguien recuerde anotar algo.
3. **Contador** (`seven_day_streak.evaluar_racha`): camina hacia atrás desde
   el día de la pasada, por clase. Un día cuenta si, y solo si, hay línea
   presente, todos sus ejes son `COINCIDE`, y ningún eje de ese día lleva la
   huella del punto 2. La primera vez que cualquiera de las tres falla, la
   racha se rompe ahí -sin mirar más allá- y el motivo publicado dice
   exactamente cuál de las tres fue (requisito 7).
4. **Hora recomendada** (`seven_day_streak.hora_recomendada_pasada`): opción
   B de arriba. Informativa: no cablea ningún horario (eso sigue
   prohibido, ADR-002); la expone `sirius-racha` como texto para quien
   decida cablearla en otra incidencia.
5. **Punto de entrada** (`sirius-racha`,
   `seven_day_streak_cli.py`): por cada `WorkItem` no terminal cuya clase
   tenga autoridad `incidencia` (`autoridad_de_clase`) y que el diario del
   despachador (C2, `DispatchJournal.episode_for`) ya sepa a qué incidencia
   corresponde, lee la incidencia real, llama a `verificar_dia` y añade la
   línea. Una lectura caída del espejo (`EspejoIlegibleError`) se informa y
   se salta -no inventa una línea, misma disciplina que ADR-036-. Ninguna
   ruta de este comando importa ni llama nada de
   `sirius_engine.domain.authority` que pudiera cambiar la tabla: publica y
   registra, no conmuta (requisito 8, contrato §11.3).

### La edad de la etiqueta de máquina, hoy desconocida en la pasada real

`ContextoEjesDiarios.edad_etiqueta_maquina` -la ventana 4 de D1a, que
protege una divergencia transitoria como `NO_COMPARABLE`- exige saber
CUÁNDO se aplicó la etiqueta vigente. Ningún método de `GitHubMirrorPort`
expone esa lectura hoy (`MetadatosIncidencia` no lleva marca de tiempo por
etiqueta), y añadir uno sería tocar un puerto compartido fuera del alcance
permitido de este bloque (que enumera un módulo nuevo, el punto de entrada,
el registro y el ADR -no los puertos del espejo). `sirius-racha` declara
por tanto `edad_etiqueta_maquina=None` en la pasada real. D1a ya trata una
edad desconocida de forma segura -las ventanas 1 y 4 no protegen nada sin
ella, y una divergencia real se sigue leyendo como divergencia, nunca como
un verde inventado (`test_ventana_1_edad_desconocida_no_protege_el_despacho_indefinidamente`,
D1a)-, así que esto no abre ningún camino a un falso verde: solo hace que
los días con residencia normal de etiqueta se lean, de más, como
`DIVERGENCIA` en vez de `NO_COMPARABLE`. Es exactamente el motivo por el
que la hora derivada (punto 4) importa: al no haber protección de ventana
4, alejarse de cualquier disparo periódico es la única defensa disponible
hoy contra ese exceso de `DIVERGENCIA`.

## Comprobación que la sostiene

- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests`, `uv run pytest` y `git diff --check`: los cinco en
  verde (3414 pruebas, 8 omitidas -preexistentes y ajenas a este bloque-).
- Los dos caminos de reinicio del requisito 1, cada uno con su prueba
  sembrada: `test_racha_vuelve_a_cero_por_un_dia_no_verde_en_medio_de_la_racha`
  y `test_racha_vuelve_a_cero_por_correccion_manual_detectada_en_medio_de_la_racha`
  (más `test_correccion_manual_rompe_la_racha_aunque_ambos_dias_individualmente_fueran_verdes`,
  que fija que la condición 2 rompe la racha aunque la condición 1, sola, no
  lo haría).
- La ventana de tolerancia real de este repositorio, leída de forma
  independiente en la prueba (no llamando a la propia función):
  `ventana_tolerancia_etiqueta_maquina()` = 170 minutos (2 h 50 min), igual
  que midió el cierre de la incidencia #265.
- La hora derivada del único `schedule: cron:` real
  (`reconcile-sirius-states.yml`, `17 */6 * * *`):
  `hora_recomendada_pasada()` = `03:17 UTC`, punto medio de un hueco de 360
  minutos -180 minutos de margen a cada lado, por encima de los 170
  requeridos-. `test_hora_recomendada_atada_al_schedule_real_del_repositorio`
  lo recalcula por su cuenta, sin llamar a la función que verifica, y
  coincide.
- Requisito 8 (no conmuta nada): `test_evaluar_una_racha_completa_no_cambia_la_autoridad_de_ninguna_clase`
  y `test_la_pasada_no_cambia_la_autoridad_de_ninguna_clase` ejecutan el
  contador y el punto de entrada con una racha de siete días completa -el
  caso que más tentaría a conmutar- y comprueban que
  `autoridad_de_clase` da exactamente lo mismo antes y después.

## Consecuencias

- **El contador es correcto y está listo para medir en cuanto haya datos que
  medir, pero hoy no los hay.** Comprobado al escribir esta incidencia:
  ningún workflow real (`.github/workflows/*.yml`) ni script de
  automatización (`scripts/automation/*.sh`) invoca ningún comando de
  `sirius_engine`, y ninguna llamada de producción a
  `WorkEngineStore.begin_work_item_execution`/`begin_work_item_check`/
  `begin_work_item_review`/etc. existe fuera de los propios almacenes y las
  pruebas. El motor -el `WorkEngineStore` durable- no es hoy la maquinaria
  que hace avanzar el ciclo real de una incidencia de programación o
  auditoría: ese ciclo sigue siendo enteramente el de
  `scripts/automation/*.sh` y las etiquetas `sirius:*`. Esto no es un
  defecto de D1b -el contador, probado con datos sembrados, sabe reconocer
  siete días verdes y sabe volver a cero por las dos vías del contrato-: es
  el estado real y ya conocido del proyecto (C2 se declaró explícitamente
  "sin cablear a un horario"; nada posterior ha cableado el ciclo completo
  al motor todavía). Mientras eso no exista, `sirius-racha` medirá con
  honestidad `WI_conocidos = ()` o divergencias estructurales de fase, y
  reportará "no cumple, sin línea registrada" o su motivo real -nunca un
  falso verde-, hasta que otro bloque (fuera de este alcance: tocaría
  `.github/**` o añadiría el observador que traduce eventos del ciclo real a
  transiciones del motor) cierre ese hueco.
- La hora recomendada (03:17 UTC) es informativa: cablearla a un `schedule`
  real es, explícitamente, trabajo de otra incidencia (ADR-002).
- Si en el futuro se añade a `GitHubMirrorPort` una lectura de "cuándo se
  aplicó la etiqueta vigente", `sirius-racha` puede pasar esa edad real a
  `ContextoEjesDiarios` sin cambiar `seven_day_streak.py`: el hueco de la
  sección "La edad de la etiqueta de máquina" queda documentado para esa
  incidencia futura, no resuelto aquí.

## Alternativas descartadas y por qué

- **Un contador que solo mire el registro (sin el diario de eventos) y
  declare "sin corrección" por defecto.** Habría sido más simple, pero
  degrada exactamente a la opción A del criterio de parada (a): sin ninguna
  fuente que pudiera decir que sí hubo corrección, la condición 2 se
  cumpliría siempre por construcción, que es el falso verde que este bloque
  existe para impedir.
- **Limitar `dias_consecutivos` a `DIAS_REQUERIDOS` en vez de seguir
  contando.** Descartada: "llevamos doce días" es una medición más auditable
  que "llevamos siete", y truncarla no aporta nada -el requisito 7 pide
  precisión, no un booleano.
- **Cablear `sirius-racha` a un `workflow_dispatch`/`schedule` en esta misma
  incidencia.** Prohibido por el propio alcance del bloque y por ADR-002:
  el punto de entrada se entrega ejecutable; engancharlo a un reloj es un
  acto aparte.

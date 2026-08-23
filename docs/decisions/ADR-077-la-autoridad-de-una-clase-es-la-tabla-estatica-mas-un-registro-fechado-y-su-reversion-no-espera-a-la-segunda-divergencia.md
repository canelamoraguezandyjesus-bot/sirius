# ADR-077 — La autoridad de una clase es la tabla estática más un registro fechado, y su reversión no espera a la segunda divergencia

- Estado: APROBADO
- Fecha: 2026-08-23
- Aprobación: fusión de la PR por el propietario
- Contexto: bloque D1c del plan del Work Engine, contrato operativo v1.7 §11.3-§11.4, incidencia #276
- Relacionadas: ADR-041 (fija la tabla estática y su totalidad sin defecto), ADR-043 (las clases MOTOR nacen canónicas), ADR-073 (D1a, el verificador de proyección), ADR-074 (D1b, el contador de los siete días)

## Contexto y problema

El contrato §11.3 dice que la autoridad de una clase de trabajo conmuta
mediante «registro fechado como dato versionado en el repositorio, más
anuncio por el canal de notificaciones ya existente (§7)». Hasta este
bloque, `sirius_engine.domain.authority.autoridad_de_clase()` (ADR-041) es
una función pura sobre una tabla estática: no existe ningún registro, así
que no hay nada que una conmutación -en cualquier dirección- pudiera leer.

El §11.4 exige además la mitad "de emergencia": ante la primera divergencia
detectada tras una conmutación hacia el motor, la clase revierte
automáticamente a autoridad de la incidencia, sin esperar patrón ni segunda
ocurrencia. Esa reversión no puede escribirse sin que exista antes el
estado sobre el que actúa -el registro de conmutaciones-, que es lo que este
bloque construye primero.

Esta incidencia es la reescritura de un primer encargo que pedía escribir la
autoridad "por la vía que `domain/authority.py` ya ofrezca" mientras
declaraba ese módulo fuera de alcance. El primer intento se detuvo,
correctamente, por el criterio de parada (b) de su propia nota de arranque:
no existía tal vía, e inventar un mecanismo de escritura habría sido
exactamente lo que ese criterio prohíbe. El error era del encargo, no de la
implementación: la forma del mecanismo no había que inventarla, la fija el
contrato §11.3. Esta versión autoriza `domain/authority.py` con ese único
límite explícito.

Deliberadamente **no conmuta ninguna clase hacia el motor**: eso lo gobierna
el contador de §11.2 (D1b, ADR-074), que hoy no tiene datos reales que
contar (incidencia #270, ningún workflow real invoca todavía al motor). El
registro debe admitir esa dirección sin que este bloque la escriba -la
salida de emergencia se construye antes de que haya nada de lo que salir,
porque el contrato permite automatizar la conmutación hacia delante
precisamente porque también automatiza la reversión, y quedarse solo con la
primera mitad sería quedarse con la mitad favorable del trato.

## Criterio de parada (escrito ANTES de decidir)

Las cuatro de la nota de arranque de la incidencia #276, publicadas antes de
escribir código:

- (a) Si para revertir hace falta que un `NO_COMPARABLE` cuente como
  divergencia, se para: sería cambiar lo medido para que encaje con el
  instrumento. Está medido (cierre de la #265) que mientras la etiqueta de
  máquina sea reciente (~2h50m) la ventana 4 de D1a declara `NO_COMPARABLE`
  cualquier comparación -sería el caso frecuente, no la excepción.
- (b) Si `autoridad_de_clase()` acaba necesitando un valor por defecto o una
  degradación silenciosa, se para: retiraría la garantía que ADR-041 puso
  ahí a propósito (función total, `KeyError` explícito ante una clase sin
  fila).
- (c) Si hace falta tocar el verificador de D1a, el contador de D1b, la
  proyección o el espejo, se para y se dice.
- (d) Cualquier edición de `.github/**` es criterio de parada (ADR-002).

Ninguno de los cuatro se activó.

## Opciones consideradas

**Cómo extender `autoridad_de_clase()` sin romper su totalidad (ADR-041):**

- **A. Sustituir la tabla estática por una fuente mutable (fichero de
  configuración, variable de entorno).** Descartada: pierde la propiedad de
  ADR-041 de raíz -la tabla deja de ser la verdad fijada por el contrato en
  el momento de nacer el primer WorkItem- y no hay ninguna necesidad de
  perderla, porque §11.3 solo pide *añadir* un segundo término, no sustituir
  el primero.
- **B. Añadir un parámetro `registro` opcional, con valor por defecto vacío,
  que solo puede mover el resultado para las clases que la tabla ya marca
  como conmutables (autoridad `INCIDENCIA`).** **Elegida.** Todo llamador
  existente (`work_intake.py`, `dispatch_cli.py`, `supervisor.py`,
  `seven_day_streak_cli.py`) sigue invocando la función sin `registro` y
  obtiene exactamente el mismo resultado que antes -ninguno cambia de
  comportamiento-, y la comprobación de la tabla (`_TABLA_AUTORIDAD[clase]`)
  sigue ejecutándose siempre primero, así que una clase sin fila revienta
  igual, con o sin registro.

**Qué puede aparecer en el registro de conmutaciones:**

- **A. Cualquier `WorkItemClass`.** Descartada: una clase nativa del motor
  (autoridad `MOTOR` en la tabla, nunca tuvo proyección en GitHub) no tiene
  nada que conmutar en ninguna dirección; admitir una entrada suya sería
  aceptar en silencio un estado que el contrato §11.1 no contempla.
- **B. Solo las clases que la tabla estática nace con autoridad
  `INCIDENCIA` (hoy, `programacion` y `auditoria`).** **Elegida.** Se valida
  en el propio constructor de `EntradaConmutacion` (`__post_init__`), no en
  el módulo que la usa: es una invariante del tipo, no una regla de un
  caso de uso concreto, y así ninguna vía futura de escribir una entrada
  puede saltársela.

**Cómo decidir la reversión sin depender del texto para la idempotencia:**

- **A. Deduplicar por el texto exacto de la entrada de reversión, igual que
  el registro de D1a/D1b deduplica líneas idénticas.** Descartada como
  mecanismo principal: dos pasadas reales llevan cada una su propio
  `instante` de ejecución, así que la entrada de reversión de la segunda
  pasada nunca sería textualmente idéntica a la de la primera -el dedup por
  texto no protegería nada aquí.
- **B. Que la idempotencia sea una consecuencia del cambio de estado, no una
  comparación de texto: una clase revertida deja de ser autoridad `MOTOR`,
  así que una segunda pasada sobre la misma divergencia encuentra "no
  aplica" en `evaluar_reversion()` antes de construir nada.** **Elegida.**
  El dedup por texto de `anadir_entradas()` se conserva como red de
  seguridad para el caso degenerado (mismo `instante` congelado, típico de
  una prueba), pero no es de quien depende la propiedad.

## Decisión

1. **`domain/authority.py`** gana `EntradaConmutacion` (instante, clase,
   autoridad, motivo), con el rechazo de clases `MOTOR` en su
   `__post_init__`, y `autoridad_de_clase(clase, *, registro=())`: sin
   entradas para `clase`, el resultado es el de la tabla estática, igual que
   siempre; con entradas, manda la de mayor `instante`. `formatear_entrada_conmutacion`/
   `parsear_entrada_conmutacion` son la serialización JSON determinista,
   mismo criterio que `projection_verifier.formatear_linea`.
2. **`authority_reversion.py`** (módulo nuevo) trae tres piezas:
   - **El registro de conmutaciones** (`leer_registro_conmutaciones`,
     `anadir_entradas`): JSONL append-only, mismo formato y misma
     disciplina de deduplicación por texto exacto que
     `seven_day_streak.leer_registro`/`anadir_lineas`, sobre
     `EntradaConmutacion` en vez de `LineaRegistro`.
   - **La decisión** (`evaluar_reversion`): para una clase que hoy es
     autoridad `MOTOR` según el registro, busca -entre las líneas del
     verificador de esa clase registradas DESPUÉS de la conmutación- la
     primera con algún eje en `DIVERGENCIA` (nunca `NO_COMPARABLE`). Si la
     encuentra, construye la `EntradaConmutacion` de vuelta a `INCIDENCIA`
     y el aviso; si no, o si la clase no está conmutada, devuelve "no
     aplica" con el motivo exacto. No escribe nada: quien orqueste la
     llamada decide si persistir la entrada con `anadir_entradas`.
   - **El aviso** (`formatear_aviso_reversion`): texto en español, sin
     marcado que dependa de renderizado de escritorio (compatible con
     GitHub Mobile, mismo criterio que exige el contrato §7 para las
     notificaciones de estado). Es el contenido, no la publicación:
     publicarlo en el canal real de la incidencia es cableado
     (`.github/**`) y queda fuera de este bloque, igual que la hora del
     cron quedó fuera de D1b (ADR-074).
3. **"Pone su contador a cero" sin tocar D1b.** La divergencia que dispara
   la reversión ya rompe `LineaRegistro.es_verde` para ese día en el mismo
   registro que `seven_day_streak.evaluar_racha` recorre, así que el
   contador vuelve a cero por el mecanismo que D1b ya tenía -no hace falta
   ningún código nuevo, ni tocar `seven_day_streak.py` (criterio de parada
   (c)). `test_tras_revertir_el_contador_de_siete_dias_vuelve_a_cero` lo
   comprueba combinando ambos módulos sin modificar ninguno.
4. **Sin CLI ni cableado a horario en este bloque.** El objetivo de la
   incidencia es "el estado que hace posible cambiar la autoridad" y "la
   reversión que lo usa"; conectar ambos a una lectura real de GitHub y a un
   `schedule` es, como en D1b, trabajo de otra incidencia y tocaría
   `.github/**` (criterio de parada (d)).

## Comprobación que la sostiene

- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests` y `uv run pytest`: los cuatro en verde
  (3473 pruebas, 8 omitidas -preexistentes y ajenas a este bloque-);
  `git diff --check` también en verde.
- **Los dos "se ha visto" de la nota de arranque**, cada uno con su prueba
  sembrada en `tests/engine/test_authority_reversion.py`:
  `test_una_divergencia_sembrada_revierte_la_clase_conmutada` (una
  `DIVERGENCIA` sobre una clase conmutada revierte, deja su entrada fechada
  y el aviso) y `test_una_tanda_entera_de_no_comparable_no_revierte` (una
  tanda de `NO_COMPARABLE` -incluida en todos los ejes de todos los días- no
  revierte nada).
- **Totalidad sin defecto, con y sin registro**
  (`tests/engine/test_authority.py`):
  `test_ninguna_clase_de_workitemclass_se_queda_sin_autoridad` y su gemela
  `test_ninguna_clase_se_queda_sin_autoridad_con_registro_no_vacio` recorren
  `WorkItemClass` entero; `test_clase_sin_fila_en_la_tabla_revienta_explicito_con_y_sin_registro`
  simula (vía `monkeypatch`) una clase sin fila y confirma `KeyError` en las
  dos formas de llamar a la función.
- **Una clase `MOTOR` no puede entrar en el registro**:
  `test_una_clase_motor_no_puede_entrar_en_el_registro`, parametrizada sobre
  las cinco clases nativas del motor, confirma `ValueError` en el
  constructor de `EntradaConmutacion`.
- **A la primera, no a la segunda**:
  `test_revierte_en_la_primera_divergencia_no_en_la_ultima` siembra dos
  divergencias en días distintos y comprueba que la entrada cita la
  primera.
- **Una clase no conmutada no se toca**:
  `test_una_clase_nunca_conmutada_no_aplica` y
  `test_una_clase_ya_revertida_no_aplica_de_nuevo` devuelven "no aplica"
  distinguible (`entrada`/`aviso` en `None`) sin tocar el registro.
- **Idempotencia**: `test_dos_pasadas_sobre_la_misma_divergencia_no_duplican`
  ejecuta dos pasadas reales (con `anadir_entradas` de por medio) sobre la
  misma divergencia sembrada y confirma que la segunda no aplica y que el
  registro conserva exactamente dos entradas (la conmutación de prueba y la
  única reversión).
- **Registro append-only y determinista**:
  `test_anadir_entradas_no_duplica_texto_identico`,
  `test_anadir_entradas_nunca_reescribe_lo_anterior` y
  `test_formatear_es_deterministico`.

## Consecuencias

- El registro de conmutaciones existe como tipo y como formato de fichero,
  pero ningún punto de entrada real lo escribe todavía: ni este bloque ni
  D1b cablean una pasada periódica (ADR-002). Hasta que otra incidencia lo
  haga, `autoridad_de_clase()` seguirá devolviendo siempre el valor de la
  tabla estática en producción -exactamente el comportamiento de antes de
  este bloque-, porque no hay registro real que leer.
- Cuando el contador de §11.2 (fuera de alcance aquí, depende de #270)
  conmute una clase por primera vez, la reversión de este bloque ya está
  lista para vigilarla sin cambios adicionales: `evaluar_reversion()` no
  asume nada sobre quién escribió la conmutación hacia `MOTOR`, solo que
  está en el registro.
- El aviso (`formatear_aviso_reversion`) es contenido, no entrega: publicarlo
  de verdad en la incidencia de GitHub es trabajo de otra incidencia que sí
  toque `.github/**` o un script de `scripts/automation/`.

## Alternativas descartadas y por qué

- **Reutilizar `sirius_engine.ports.notification.NotificationPort` /
  `Escalada` para el aviso de reversión.** Descartada: esa pareja modela
  específicamente una escalada al propietario por una de las siete causas
  cerradas de `CausaEscalado` (arquitectura §10) que exige una decisión
  humana. Una reversión de §11.4 es automática y no pide ninguna decisión
  -es una notificación informativa de las que cubre el contrato §7, no una
  escalada-, así que forzarla por ese puerto habría mezclado dos conceptos
  del contrato que hoy están, con razón, separados.
- **Que la reversión reaccione a `LineaRegistro.es_verde is False` en vez de
  buscar `DIVERGENCIA` explícita.** Descartada: `es_verde` es `False` tanto
  ante una `DIVERGENCIA` real como ante un `NO_COMPARABLE` -D1a lo dice en
  su propia documentación-, así que usarla como disparador habría violado
  directamente el criterio de parada (a).

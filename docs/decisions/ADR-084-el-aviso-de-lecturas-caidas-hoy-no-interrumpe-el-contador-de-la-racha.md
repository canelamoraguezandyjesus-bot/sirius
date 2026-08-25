# ADR-084 — El aviso de lecturas caidas hoy no interrumpe el contador de la racha

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

**Esta es también la nota de arranque de la incidencia #313**, publicada antes
del primer cambio de código (ADR-001, skill `disciplina-evidencia`).

## Contexto y problema

`sirius-racha` (D1b, incidencia #268) imprime, en la misma pasada: primero
`no pude leer la incidencia #N` para cada `WorkItem` cuya lectura del espejo
falló, y tres líneas más abajo `CUMPLE` para la racha de esa misma clase — sin
que la línea del veredicto mencione que esta pasada tuvo lecturas caídas.
`evaluar_racha` (`seven_day_streak.py:311`) solo recibe el registro histórico
(`lineas`, `eventos`); no sabe nada de qué ocurrió en la pasada que la invoca,
así que no puede decirlo aunque quisiera. El docstring del módulo
(`seven_day_streak_cli.py:44-52`) promete que «una pasada real seguirá
midiendo con honestidad ‘sin línea registrada’ o divergencias estructurales de
fase; nunca un falso verde» — y este silencio es exactamente eso: no un
CUMPLE calculado sobre un dato falso, pero sí un CUMPLE que oculta información
que el lector necesita para confiar en él.

El objetivo de la incidencia #313 pide explícitamente no decidir a priori
entre dos salidas — que el veredicto pase a `no cumple`, o que siga siendo
`CUMPLE` pero declare las lecturas caídas de hoy — sino medir las dos y elegir
con la medición delante.

## Las cuatro preguntas (antes de tocar código)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   OBSERVAR el fallo que arregla?** El fallo vive en dos sitios a la vez: (a)
   `evaluar_racha` no recibe la información de lecturas caídas de la pasada
   que la invoca, y (b) el bucle de `main()` en `seven_day_streak_cli.py` que
   sí observa cada `EspejoIlegibleError` (línea 234) la descarta sin
   propagarla. El arreglo vive en el sitio que SÍ observa el fallo -el propio
   bucle de `main()`, que ya construye el texto `no pude leer la incidencia
   #N`- y se hace fluir esa observación hacia `evaluar_racha` como un
   parámetro nuevo, no reconstruirla por fuera. Esto sí puede funcionar: el
   bucle observa la caída en el mismo instante en que ocurre, antes de que se
   pierda.
2. **¿Qué NO va a garantizar esto?** No detecta que un `WorkItem` de la clase
   nunca haya sido despachado o nunca haya aportado ninguna línea histórica
   -ese es un problema distinto (una clase con un único `WorkItem` fantasma
   nunca rompería su racha), fuera del alcance de esta incidencia, que es
   específicamente sobre la pasada que SÍ intentó leer y falló. Tampoco
   cambia qué cuenta como corrección manual, ni toca la conmutación de
   autoridad (contrato §11.3): sigue sin conmutar nada.
3. **Criterio de parada, decidido ANTES de ver el resultado de la medición**:
   la decisión entre "pasa a no cumple" y "sigue CUMPLE pero avisa" se toma
   comparando las dos contra el texto explícito del contrato §11.2
   (`AUTOMATION_OPERATING_CONTRACT.md:646`): *"Lo que NO interrumpe el
   contador (...): un fallo de un servicio externo (...) o cualquier otra
   avería operativa. Ninguna de esas cosas hace que las dos representaciones
   discrepen, y es la discrepancia lo único que esta condición mide."* Si esa
   frase, leída literalmente, clasifica `no pude leer la incidencia #N
   ([Errno 2] No such file or directory: 'gh')` como avería operativa (no
   como discrepancia), la opción "pasa a no cumple" queda descartada por
   contradecir el contrato, y se implementa la otra. Si, en cambio, la
   pasada fallida deja el día de HOY sin ninguna línea registrada -porque
   `anadir_lineas` no tuvo nada que añadir-, entonces `evaluar_racha` YA
   produce `no cumple` por la vía normal (requisito 2, "un día sin línea no
   es un día verde"), y no hace falta ninguna decisión nueva: ese camino ya
   estaba bien. La medición nueva solo hace falta para el caso -el de la
   incidencia- en que el día de hoy YA tenía una línea verde legítima antes
   de esta pasada (por ejemplo, una pasada anterior el mismo día natural que
   sí pudo leer) y ESTA pasada, además, tuvo lecturas caídas que no cambiaron
   ningún día del registro.
4. **¿Qué hace el fallo IMPOSIBLE en vez de improbable?** Que `evaluar_racha`
   reciba explícitamente, como parámetro con valor por defecto `()`, la
   descripción de qué no se pudo leer en la pasada que la invoca, hace
   imposible -no solo improbable- que un futuro punto de llamada calcule un
   veredicto sin poder decidir si debe avisar: la firma misma exige la
   respuesta (aunque sea la tupla vacía). No hace imposible que alguien
   ignore el aviso ya impreso -eso es un problema de quien lee la salida, no
   de quien la produce-, y se deja escrito aquí en vez de fingir que sí se
   cierra.

## Opciones consideradas

- **A. El veredicto pasa a `no cumple`** cuando la clase tuvo alguna lectura
  caída en la pasada, aunque el registro histórico ya tuviera 7+ días verdes.
- **B. El veredicto conserva `CUMPLE`** cuando el registro histórico lo
  sostiene, pero el motivo declara explícitamente qué no se pudo leer en esta
  pasada -sin inventar una interrupción que el contrato no pide-.

## Decisión

**Opción B.** El contrato §11.2 es explícito y no deja margen de juicio: un fallo de
lectura del servicio externo (`gh`) es exactamente el tipo de avería
operativa que **no interrumpe el contador**. Forzar `no cumple` en la Opción
A contradiría el contrato tal como está escrito hoy -sería el propio
implementador decidiendo, por su cuenta, endurecer una condición que el
contrato ya fijó deliberadamente (línea 648: "una condición inalcanzable no
protege"). La Opción B no relaja nada: la condición matemática de 7 días
verdes consecutivos, sin corrección manual, sigue exactamente igual
(`dias_consecutivos >= dias_requeridos`); lo único que cambia es que el
`motivo` -el campo que ya existe para que un lector nunca reciba "solo un
booleano suelto" (`test_motivo_de_incumplimiento_es_especifico_no_un_booleano_suelto`)-
declara la avería operativa de la propia pasada, en vez de callarla.

`evaluar_racha` gana un parámetro `lecturas_caidas_hoy: Sequence[str] = ()`
-descripciones ya formadas, una por cada `work_id` de esa clase que no se
pudo leer en la pasada que invoca-. Si no está vacío, se añade una cláusula
al `motivo` final (tanto si `cumple` es `True` como si es `False`, por
uniformidad: no hay ninguna razón para ocultarlo en la rama contraria). El
bucle de `main()` en `seven_day_streak_cli.py` acumula, por clase, la
descripción de cada `EspejoIlegibleError` que ya captura e imprime, y la pasa
a `evaluar_racha`.

## Comprobación que la sostiene

- Prueba nueva `test_evaluar_racha_declara_lecturas_caidas_hoy_sin_interrumpir_el_contador`
  en `tests/engine/test_seven_day_streak.py`: siembra 7 días verdes
  consecutivos hasta hoy y pasa `lecturas_caidas_hoy=("WI-B (incidencia
  #402)",)`; comprueba `cumple is True` (el contrato no lo interrumpe) y que
  el `motivo` menciona la lectura caída. Vista FALLAR antes del cambio
  (la firma de `evaluar_racha` no acepta el parámetro): `TypeError:
  evaluar_racha() got an unexpected keyword argument 'lecturas_caidas_hoy'`.
- Prueba nueva `test_pasada_con_lectura_caida_y_racha_historica_declara_el_aviso_en_el_veredicto`
  en `tests/engine/test_seven_day_streak_cli.py`: reproduce literalmente el
  escenario de la incidencia -dos `WorkItem` de clase `programacion`, uno con
  7 días verdes ya registrados hasta hoy, otro sin ninguna línea nunca- con
  un mirror que falla para ambos (`FixedGitHubMirrorReader()` vacío, mismo
  patrón que `test_una_lectura_caida_del_espejo_se_informa_y_se_salta_sin_inventar_linea`).
  Comprueba que el texto contiene tanto `CUMPLE` como el aviso de lectura
  caída en la misma línea del veredicto -no solo en las líneas de arriba-.
  Vista FALLAR antes del cambio: la línea del veredicto no menciona ninguna
  lectura caída aunque las tres líneas de arriba sí lo hacen.
- `uv run pytest tests/engine/test_seven_day_streak.py tests/engine/test_seven_day_streak_cli.py -q`
  en verde tras el cambio (se registra el resultado real en el resumen de la
  PR, no aquí, para no duplicar).

## Consecuencias

- Un lector de la salida de `sirius-racha` ya no puede ver `CUMPLE` sin ver,
  en la misma línea, si esa pasada concreta tuvo lecturas caídas: el
  silencio que motivó la incidencia desaparece.
- `evaluar_racha` gana un parámetro con valor por defecto, así que ninguna
  llamada existente (incluidas todas las pruebas actuales, que no lo pasan)
  cambia de comportamiento.
- No cambia qué significa `cumple`, ni toca `detectar_correcciones_manuales`,
  ni la conmutación (contrato §11.3): esta incidencia mide y declara, no
  conmuta.

## Alternativas descartadas y por qué

- **Opción A (forzar `no cumple`)**: descartada por contradecir el texto
  explícito del contrato §11.2 sobre qué SÍ y qué NO interrumpe el contador;
  ver «Decisión».
- **Reconstruir la información de lecturas caídas dentro de `evaluar_racha`
  a partir de `lineas`/`eventos`**: imposible en general -una lectura caída
  no deja ninguna línea en el registro (ADR-036: «una lectura caída no es
  una ausencia»), así que no hay ningún dato histórico del que derivarla; el
  único sitio que observa la caída es el bucle que la produce, de ahí la
  pregunta 1 de la nota de arranque.

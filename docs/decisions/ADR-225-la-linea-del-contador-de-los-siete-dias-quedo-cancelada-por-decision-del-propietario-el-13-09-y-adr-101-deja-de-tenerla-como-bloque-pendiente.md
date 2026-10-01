# ADR-225 — La línea del contador de los siete días quedó cancelada por decisión del propietario el 13-09 y ADR-101 deja de tenerla como bloque pendiente

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #672 por el motor con aprobación dual (ADR-205).
  La decisión que aquí se registra no es de esta sesión: la tomó el propietario
  el 13-09-2026 en la incidencia #610; este ADR la deja escrita donde el árbol
  la busca.
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-linea-del-contador-queda-cancelada-y-el-arbol-lo-dice.md`,
  confirmada en `9b78627d` antes del primer commit de cambio, con las
  predicciones y el criterio de parada.
- Supera en parte a ADR-101: su consecuencia «(C) queda como bloque propio, a
  la orden del propietario». El resto de ADR-101 sigue vigente.

## Contexto y problema

ADR-101 (28-08-2026) resolvió H-25 declarando la precondición del contador de
los siete días como hecho: `CLASES_CON_ESTADO_PROPIO` vacío, cada línea
`NO_COMPARABLE` citando el §11.2, y la pieza (C) de #376 —cablear el retorno
del desenlace de GitHub al almacén del motor y declarar la clase— «como bloque
propio, a la orden del propietario». `docs/evolution/STATUS.md` (D5) recogió
después que esa pieza «se ordenará después de las oleadas de construcción de
Sirius 0.2».

El 13-09-2026 el motor despachó el encargo #610 («implementa el cierre entero
de la cadena del contador de los siete días»). A los dos minutos, a las
13:25:57 UTC, el propietario lo canceló con un comentario como `OWNER`:

> Este encargo no debió despacharse. La sesión leyó mal la orden: el propietario
> había dicho que la línea del contador de los siete días **no es necesaria** —y
> la propia sesión se lo había recomendado así— y su «hay que acabar esto
> entero» se refería a **las mejoras del motor que quedan pendientes**, no a
> resucitar esta línea.

La incidencia se cerró `not_planned` a las 13:26:04, sin rama ni PR. El
comentario deja vigente la medida de la incidencia #605 (54 de 54 entregados
coinciden; los dos huecos del eje `fase` y del reflejo entre paradas; la regla
de agregación que hace inalcanzable el §11.2 mientras haya trabajos
detenidos), registrada en ADR-186 y en la rama
`feature/c2-medida-precondicion-contador-siete-dias`.

Dieciocho días después, la decisión vivía solo en ese comentario. Medido con
`grep` («bloque propio», «sigue bloqueando D1», «(C) de #376») sobre `src`,
`scripts` y `docs` sin la mina ni las notas de arranque históricas, **cuatro
sitios vivos** seguían presentando la pieza como pendiente u ordenada —la nota
de arranque predijo dos—: la cabecera de `src/sirius_engine/seven_day_streak_cli.py`
(«sigue bloqueando D1», «queda como bloque propio»), el comentario de
`CLASES_CON_ESTADO_PROPIO` en `src/sirius_engine/projection_verifier.py`
(«una clase entra aquí solo desde el bloque que cablee ese retorno»), la línea
D5 de `docs/evolution/STATUS.md` («se ordenará después de las oleadas») y la
consecuencia de ADR-101. La mina de septiembre lo encontró (deuda 13,
propuesta 11 de §10) y lo nombró: familia
`decision-que-solo-vive-en-una-conversacion`.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: sin la cita literal del `OWNER` en #610 no hay ADR;
solo prosa y registro, ningún comportamiento (si un sitio con comportamiento
bloqueara por esta línea, se mide aparte); H-225 registrada y la guarda del
registro vista caer antes y pasar después.

**Desviación declarada.** La ronda 2 de Codex en la PR #672 mostró el sitio con
comportamiento que la nota preveía: el `schedule` del contador y las guardas
que, para mantener alcanzable D1, exigían el cron derivado y ataban a 85 el
tope de todos los jobs. Se midió —las 19 pasadas de abajo— y se cambia aquí, no
aparte: es la consecuencia mecánica de la misma decisión del propietario, no
una decisión nueva.

## Opciones consideradas

1. **Dejarlo como está**, la decisión en #610 y el árbol diciendo lo contrario.
   Rechazada: es exactamente la familia que la mina midió, y la próxima sesión
   que lea el CLI o STATUS.md volvería a creer que hay un bloque pendiente.
2. **Retomar la línea** (hacer (C)). Rechazada: el propietario dijo que no es
   necesaria, y «hay que acabar esto entero» eran las mejoras del motor.
3. **Registrar la decisión, superar esa consecuencia de ADR-101 y corregir la
   prosa viva.** Esta.

## Decisión

1. **La pieza (C) de #376 queda cancelada** por decisión del propietario del
   13-09-2026 (#610). No se ordenará salvo decisión nueva suya; si algún día la
   quiere, la medida de #605 (ADR-186) es el punto de partida y hará falta otro
   ADR.
2. **ADR-101 queda superado solo en esa consecuencia**; lleva una nota que lo
   dice. Lo demás de ADR-101 —la precondición como hecho declarado, el
   conjunto vacío con su prueba, `NO_COMPARABLE` con motivo— sigue vigente y
   es lo que hace honesto al contador: no hay nada que medir, y lo dice.
3. **La prosa viva lo dice**: la cabecera de `seven_day_streak_cli.py`, el
   comentario de `CLASES_CON_ESTADO_PROPIO`, la línea D5 de
   `docs/evolution/STATUS.md`, la entrada D1 de
   `docs/implementation/bloques_del_motor.yml` (de `pendiente` a
   `fuera_de_alcance`, con fecha y motivo), la sección D1 del plan de
   implementación y la cabecera de
   `tests/automation/test_reflejar_desenlace_github.py` dejan de presentar la
   pieza como pendiente u ordenada y citan #610 y este ADR. Las notas de
   arranque antiguas y la propuesta de separación del 08-09 (REVISADA, fechada
   y sin autoridad) se quedan como lo que fueron.
4. **El árbol ejecutable deja de servir a la línea cancelada** (ronda 2 de
   Codex en la PR #672): `contador-siete-dias.yml` pierde su `schedule` y
   conserva `workflow_dispatch`. Medido en el registro de la rama de memoria
   antes de retirarlo: 19 pasadas programadas entre el 13-09 y el 01-10, 22
   líneas, 44 ejes, **los 44 `no_comparable`**, 0,4 minutos de Actions cada
   una. Con el horario se van las guardas que solo tenían sentido con él —el
   cron derivado, la ventana de tolerancia y el techo de 85 minutos para todos
   los jobs: las de `test_contador_de_siete_dias.py`, el tope del ejecutor en
   `test_investigar_orden_workflow.py`, los dos del tope de la medición en
   `test_medicion_del_investigador.py` y la cota superior del minuto del motor
   en `test_turno_programado_actua.py`— y la prosa de los ocho workflows que
   justificaban su tope o su hora por el contador lo dice con fecha, sin
   mover ningún tope ni ninguna hora. Queda una guarda nueva: que el contador
   **no** vuelva a tener horario sin otra decisión. Lo demás no cambia:
   `CLASES_CON_ESTADO_PROPIO` sigue vacío con
   `test_h25_el_conjunto_declarado_esta_vacio_hoy` intacta, `verificar_dia`
   igual, la racha igual, el §11.2 igual (la enmienda que #610 autorizaba no se
   hace: el encargo se canceló), y la derivación de la hora sigue probada sola
   (`test_seven_day_streak.py`) por si la línea vuelve.
5. **El cierre del ciclo del 24-09 lleva una corrección fechada** (ronda 2 de
   Codex): presentaba D1 como el único bloque pendiente y «se cierra usándolo».

## Comprobación que la sostiene

- La cita de #610, leída por la API antes de escribir la nota de arranque:
  comentario del `OWNER` a las 13:25:57 UTC, incidencia cerrada `not_planned`
  a las 13:26:04.
- Sitios vivos que daban la pieza por pendiente u ordenada: **4 en la nota de
  arranque y 3 más que su `grep` no alcanzaba** —la entrada D1 del registro de
  bloques y la cabecera de la prueba de C1, que cazó Codex en la ronda 1 de la
  PR #672, y la sección D1 del plan de implementación, que salió de buscar lo
  mismo en el resto del árbol—. **Después, ninguno la da por pendiente.** El
  mismo `grep` sigue encontrando las palabras en dos líneas (la descripción
  histórica de D5 en STATUS.md y el comentario del conjunto), y las dos van
  seguidas, en la frase siguiente, de la cancelación y de este ADR; la mina y
  las notas de arranque históricas se quedan como lo que fueron.
- Guardas de ADR y registro en verde (`test_estado_de_los_adr.py`,
  `test_mina_de_lecciones.py`, `test_registro_de_decisiones.py`,
  `test_citas_de_los_adr.py`, `test_memoria.py`); las del verificador de
  proyección y de la derivación de la hora (`test_seven_day_streak.py`,
  `test_seven_day_streak_cli.py`, `test_projection_verifier.py`) en verde sin
  cambios.
- La medida del contador: `racha_siete_dias.jsonl` en `estado-del-motor` (378
  líneas; desde el 13-09, 22 líneas de 19 pasadas sobre 4 encargos, 44 ejes,
  los 44 `no_comparable`) y los 19 runs programados de
  `contador-siete-dias.yml` en Actions (todos `success`, 0,4 min de media).
- Las guardas reescritas, en verde: `test_contador_de_siete_dias.py` (2),
  `test_investigar_orden_workflow.py`, `test_medicion_del_investigador.py`,
  `test_turno_programado_actua.py`, y las baterías que leen los workflows
  tocados. Mutación: devolver el `schedule` al contador → cae
  `test_el_contador_existe_y_se_lanza_solo_a_mano` (vista caer, fichero
  restaurado).
- `test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro` cae
  con este ADR sin H-225 y pasa con ella (los dos commits de la convención).
- `ruff format --check`, `ruff check`, `mypy` sobre los dos módulos tocados; el
  comprobador de documentos sobre este ADR, ADR-101, STATUS.md y la nota.

## Consecuencias

- Quien lea el contador, el verificador o el estado del proyecto ve la decisión
  y su fecha, no un bloque pendiente.
- La deuda 13 de la mina pasa de «decisión tomada y sin registrar» a
  registrada; la hoja de decisiones abiertas del propietario no cambia (esta ya
  estaba tomada).
- El contador sigue sin poder contar, y sigue diciéndolo con honestidad; eso
  no era un defecto y no se toca. Lo que sí deja de hacer es intentarlo cada
  día: la pasada queda a mano.
- Los topes de los jobs y las horas de los demás workflows dejan de estar
  atados a una ventana que no medía nada; cambiar cualquiera sigue siendo una
  decisión con su medida, pero ya no la bloquea una guarda de una línea
  cancelada (el implementador de la PR #675 necesita exactamente eso).

## Alternativas descartadas y por qué

Las de «Opciones consideradas». Y marcar ADR-101 entero como `SUPERADO`: no lo
está; lo que sigue vigente de él es justo lo que hace honesto al contador.

## La lección

- familia: `decision-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: una orden del propietario que cancela una línea entera queda en el comentario de una incidencia cerrada, y dieciocho días después el ADR, el código y el estado del proyecto siguen diciendo que esa línea está pendiente y bloquea algo; la siguiente sesión la retomaría o la pondría delante de él otra vez.
- lo hace cumplir: `ninguna prueba: una decisión del propietario no tiene hoy una forma mecánica que una guarda pueda leer; la caza la mina mensual (deuda 13) y la hoja de decisiones abiertas, a posteriori`

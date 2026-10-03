# ADR-221 — La puerta de activación resuelve el `Perfil: rol@N` con el mismo resolutor que el implementador, y avisa si la versión no es la vigente

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-puerta-de-activacion-resuelve-el-perfil.md`,
  publicada en el commit `5580817d` (01-10-2026, 07:49 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

Desde C3 (#333) el prompt del implementador se elige por el campo
`Perfil: rol@N` del cuerpo, y desde H-28 lo resuelve `resolver_prompt.py`
contra el manifiesto, en rojo y sin adivinar si el campo falta, el `rol@N` no
está registrado o el texto se movió. Esa resolución vive **dentro del run del
implementador**: cuando falla, el run ya ha arrancado, la incidencia acaba en
`failed-safely` y la razón queda en el log del run.

La puerta de activación (`sirius_validate_activation.sh`, incidencia #60)
existe para rechazar temprano, en el repositorio y con diagnóstico, lo que el
implementador rechazaría caro: comprueba que la incidencia está abierta, que
lleva `sirius:planned`, que no hay estados incompatibles y que el cuerpo tiene
todas las secciones. **No miraba el `Perfil:`**: el guion no contenía la
palabra. El 20-09, #653 pasó la puerta con `Perfil: implementer@2` y el run
murió a los **seis segundos** (bitácora del ciclo, entradas 123, 124 y 138;
deudas 34 y 35; mina del 30-09, §6.4). Medido en el volcado de septiembre
—«`implementing` seguido de `failed-safely` en menos de dos minutos y sin
ninguna ronda»—: **1 caso**, #653 (6 s). Es un caso, demasiado pequeño para
una tasa; se arregla porque cada uno cuesta un run y una persona leyendo logs.

Y la segunda mitad, la deuda 35: #653 llevaba `@2` cuando la versión vigente de
`implementer` era la 4, y nadie se lo dijo. No es un error —`rol@N` significa
UN texto (H-28) y una versión antigua sigue siendo ejecutable a propósito—,
pero es una sorpresa que se puede anunciar.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: la puerta no corrige el cuerpo ni elige perfil por
su cuenta; el resolutor que usa es **el mismo fichero** que usa el
implementador; si leer la versión vigente exigiera PyYAML en el `python3` del
runner, se lee la línea `version:` con la biblioteca estándar y se dice; tres
mutaciones vistas caer.

## Opciones consideradas

1. **Que el implementador rechace mejor** (comentario en la incidencia al
   fallar la resolución). Insuficiente: el run ya ha arrancado y ya ha costado.
2. **Copiar en la puerta el regex del `Perfil:` y la lectura del manifiesto.**
   Rechazada: dos resolutores serían dos verdades, y H-13/H-28 ya pagaron esa
   lección.
3. **Rechazar también la versión no vigente.** Rechazada: contradice H-28
   (`rol@N` es un texto fijo y las versiones viejas se conservan a propósito);
   lo que faltaba era el aviso, no la prohibición.
4. **Llamar desde la puerta al mismo `resolver_prompt.py`, rechazar lo que no
   resuelve y avisar de lo que resuelve con versión no vigente. Esta.**

## Decisión

1. La puerta gana el paso 4: con el cuerpo ya leído, y **solo para los roles
   del carril de ejecución del manifiesto** (hoy `implementer` y
   `documentalista`, leídos del propio manifiesto, no escritos aquí), ejecuta
   `resolver_prompt.py --carril ejecucion` (el mismo fichero y la misma llamada
   que el implementador, solo stdlib). Solo se exime un rol que **otro
   carril del manifiesto reclame como suyo** —hoy `investigador`, cuyo
   ejecutor es el investigador medido de `investigar-orden.yml` y tiene su
   propia puerta de reparto—; un rol que no está en ningún carril (una errata
   como `implementr`) se juzga y se rechaza, porque el reparto lo mandaría al
   implementador y moriría allí; un cuerpo sin `Perfil:` sí se juzga, porque
   ninguna puerta de reparto lo atiende. Y el cuerpo que se juzga es el que el
   implementador **va a ejecutar**: la instantánea del evento (`ISSUE_BODY`,
   `github.event.issue.body`, que `implement-sirius-work.yml` ya pasaba y
   `validate-sirius-activation.yml` pasa ahora), no el cuerpo actual de la
   API, porque el reparto solo compara el rol y el implementador resuelve la
   instantánea: una edición posterior que cambiara solo la versión pasaría la
   puerta y mataría al implementador (ronda 1 de Codex en la PR #670). **Pero
   antes de juzgarla, la puerta compara el `Perfil: rol@N` de la instantánea
   con el del cuerpo vigente, y si no coinciden el evento es rancio**: no se
   valida, no se ejecuta y **no se toca ninguna etiqueta**, porque la
   `sirius:implement-requested` que hay ahora puede ser la de otra activación
   posterior, con su propio evento, y esta puerta corre en su propio workflow
   y puede llegar tarde: rechazar retiraría la etiqueta de esa otra y el
   trabajo se perdería sin que nadie lo viera (ronda 5 de Codex). Publica una
   vez por pareja de perfiles un aviso con lo que el cuerpo declaraba al
   aplicar la etiqueta, lo que declara ahora y qué hacer (si ya se volvió a
   activar, dejar correr esa; si no, retirar y volver a aplicar la etiqueta),
   y sale con 2, como el reparto de ADR-167 cuando cambió el rol: el
   implementador termina en rojo sin consumir el evento. Una instantánea
   **vacía** (el evento llegó sin cuerpo y alguien lo escribió después) no se
   sustituye por el cuerpo actual (`${ISSUE_BODY-…}`, no `:-`; ronda 2) y es,
   por lo mismo, un evento rancio. Las dos primeras versiones de esta regla
   rechazaban la instantánea retirando la etiqueta; la raíz es la misma que la
   del reparto: la carga del workflow no trae una identidad del evento que
   diga de quién es la etiqueta presente, así que lo único seguro es no
   tocarla. El aviso de versión no vigente, por su parte, cuenta con el estado
   real en que se leerá, que tiene dos fases: lo publica la primera puerta
   que lo ve, y como `validate-sirius-activation.yml` suele llegar antes que
   el implementador, quien lo lea puede encontrar la incidencia todavía en
   `sirius:planned` (entonces: editar el cuerpo, que vuelve rancio el evento
   sin tocar etiquetas, y reactivar); el implementador lo publica segundos
   antes de consumir la activación, y solo al consumirla la incidencia pasa a
   `sirius:implementing` (ronda 13 de Codex: una versión anterior de este
   párrafo decía que «estará en `sirius:implementing`», y no era verdad en la
   primera fase). Ya en `implementing` distingue los dos caminos: **cancelar el run** (la
   incidencia queda parada en `failed-safely` con su diagnóstico; editar el
   cuerpo y escribir `continua`, que repite la activación con el cuerpo
   vigente: ADR-094, y ADR-223 —PR #671, que entra en `main` antes que esta— para reponer `sirius:planned` si consta) o **dejarlo terminar** (el ciclo sigue —revisión, fusión,
   cierre— y la vigente no se ejecutará en esa incidencia: haría falta una
   nueva). Retirar y reaplicar la etiqueta con el run en marcha no sirve
   porque esta puerta rechaza una activación sobre una incidencia con estado
   activo (rondas 2 a 5 de Codex: las tres versiones anteriores prometían un
   camino que el estado real —activación consumida, o ciclo que sigue hasta
   `completed`— no permitía). Que el reparto compare el `rol@N` entero es otra
   decisión,
   sobre ADR-167, y no entra aquí. Si no resuelve,
   rechaza con el motivo
   `perfil-sin-resolver`, el detalle del resolutor en el comentario y la acción
   («pon `Perfil: rol@N` con un rol y una versión registrados en el
   manifiesto»), retirando `sirius:implement-requested` como en los demás
   motivos: estado limpio, reintentable.
2. Paso 5: si resuelve pero la versión declarada no es la vigente del rol
   (`docs/implementation/work_engine/perfiles/<rol>.yml`), publica **una vez**
   (marcador `sirius-activation:aviso:perfil-no-vigente:<rol@N>`) un aviso que
   dice cuál es la vigente y que se ejecuta con la declarada. No rechaza.
3. `resolver_prompt.py` gana `version_vigente(rol)` y `aviso_de_vigencia(cuerpo)`,
   y la opción `--vigencia` que imprime el aviso (o nada) con el mismo código
   de salida que la resolución. La versión se lee con un regex sobre la línea
   `version:` del perfil, porque el guion corre con el `python3` del runner sin
   PyYAML (`test_sirius_runner_python_compat.py`).

El implementador conserva su propia resolución (defensa en profundidad): la
puerta no puede garantizar ejecutarse antes que él, solo adelantarse casi
siempre y dejar el diagnóstico en la incidencia.

**Rondas 11 a 13 de Codex (03-10): la puerta no toca etiquetas.** Publicar
el rechazo (`sirius_comment_once`) puede llevar hasta 90 s de reintentos; si en
ese rato alguien corrige la causa y vuelve a aplicar
`sirius:implement-requested`, la puerta seguía hasta `--remove-label` y
retiraba la activación nueva. Releer el perfil justo antes (ronda 11) y después
el cuerpo entero (ronda 12) no bastaba: una reactivación puede corregir la
causa sin tocar el cuerpo (añadir `sirius:planned`, limpiar un estado
incompatible, el perfil que faltaba fusionado en `main`), y en los rechazos
anteriores a leer el cuerpo no había nada que releer (ronda 13). Tres rondas de
la misma familia: la raíz es la que ya tenían escritas el reparto (ADR-167) y
el evento rancio, la carga del workflow no trae una identidad del evento que
diga de quién es la etiqueta presente, y la API no ofrece «retirar solo si».
Así que la regla final es la misma: **rechazar es publicar el diagnóstico, y
ninguna etiqueta se toca**. Quien lea el rechazo retira
`sirius:implement-requested` y la vuelve a aplicar cuando haya corregido la
causa. Lo que se pierde: el estado «limpio» tras un rechazo (la pareja
`planned` + `implement-requested` se queda, y el reconciliador la tratará como
una activación sin consumir cuando envejezca, que es lo que es). Lo que se
gana: ninguna ventana en la que la máquina retire la activación de otro. Y como los dos carriles y el validador independiente deducían el
rechazo de que la etiqueta hubiera desaparecido, la puerta lo dice ahora con
un código propio: 4 es «rechazada, motivo publicado, etiquetas intactas» (0
válida, 1 reintentable, 2 evento rancio, 3 aviso no publicable), y los
workflows leen el código, no la etiqueta; el carril retirado ya no impone su
desenlace a una activación rechazada (prueba
`test_una_activacion_improcedente_no_impone_failed_safely`, que Quality puso
en rojo sobre `3fccb2a8` con la primera versión de esta regla).

## Comprobación que la sostiene

`tests/automation/test_sirius_activation.py` ejecuta la puerta de verdad con
el doble de `gh`; el cuerpo completo de sus pruebas lleva ahora el `Perfil:`
que todo encargo declara, con la versión vigente leída del perfil (no escrita
a mano). Ocho pruebas nuevas:

- `test_un_cuerpo_sin_perfil_se_rechaza_antes_de_arrancar`: rechazo
  `perfil-sin-resolver` con el detalle del resolutor; `planned` se conserva.
- `test_un_perfil_desconocido_se_rechaza_con_el_detalle_del_resolutor`
  (`implementer@99`: «no está en el manifiesto»).
- `test_un_perfil_valido_pero_no_vigente_avisa_y_deja_pasar`
  (`implementer@2`: el evento se conserva, el aviso lleva su marcador y la
  versión vigente, y no hay rechazo).
- `test_el_perfil_vigente_pasa_sin_ningun_comentario`.
- `test_un_perfil_ajeno_al_carril_de_ejecucion_no_se_juzga_en_esta_puerta`
  (`investigador@2` pasa sin rechazo ni aviso). Lo trajo la batería entera: la
  primera versión juzgaba todo rol y rompía 22 pruebas del reparto entre
  carriles y del workflow de investigación, cuyos cuerpos llevan
  `investigador@2` o un rol sintético; la puerta no es dueña de esos roles.
- `test_un_rol_que_no_esta_en_ningun_carril_se_rechaza` (`implementr@4`:
  rechazo `perfil-sin-resolver`, no exención).
- `test_una_instantanea_igual_al_cuerpo_se_juzga_y_se_rechaza_si_no_resuelve`
  (instantánea igual al cuerpo, con `implementer@99`: rechazo, porque lo que
  se iba a ejecutar no resuelve).
- `test_un_evento_cuyo_perfil_cambio_despues_es_rancio_y_no_toca_ninguna_etiqueta`
  (cuerpo vigente, instantánea con `implementer@99`: código 2, etiqueta
  intacta, aviso `evento-rancio` con los dos perfiles; repetirlo no duplica
  el aviso ni toca nada).
- `test_una_instantanea_vacia_del_evento_es_un_evento_rancio` (`ISSUE_BODY`
  vacío: código 2, etiqueta intacta, aviso con `ninguno`).

**Mutaciones** (cada una aplicada sobre la puerta, la prueba ejecutada y el
fichero restaurado):

| | Mutación | Resultado |
|---|---|---|
| M1 | la puerta deja de resolver el perfil | cae `un_cuerpo_sin_perfil_se_rechaza` |
| M2 | el `rol@N` no vigente deja de avisar | cae `un_perfil_valido_pero_no_vigente_avisa` |
| M3 | el aviso de no vigente se convierte en rechazo | cae la misma: el evento desaparece |
| M4 | eximir cualquier rol que no sea del carril de ejecución (la primera versión) | cae `un_rol_que_no_esta_en_ningun_carril_se_rechaza` |
| M5 | juzgar el cuerpo actual e ignorar la instantánea del evento | cae `un_evento_cuyo_perfil_cambio_despues_es_rancio_y_no_toca_ninguna_etiqueta` |
| M6 | sustituir una instantánea vacía por el cuerpo actual (`:-`) | cae `una_instantanea_vacia_del_evento_es_un_evento_rancio` |
| M7 | el aviso de no vigente vuelve a prometer «retira, espera y vuelve a aplicar» | cae `un_perfil_valido_pero_no_vigente_avisa_y_deja_pasar` |
| M8 | un evento rancio se rechaza retirando la etiqueta (las versiones 1 y 2 de la regla) | cae `un_evento_cuyo_perfil_cambio_despues_es_rancio_y_no_toca_ninguna_etiqueta` |
| M9 | la exención del carril ajeno vuelve a leer el rol con `sed` (ronda 9 de Codex) | cae `la_exencion_de_carril_usa_el_parser_canonico` |
| M10 | el aviso que no se puede publicar vuelve a ser un `::warning` y la activación sigue | cae `un_aviso_de_no_vigente_que_no_se_puede_publicar_no_valida_la_activacion` |
| M11 | el reparto vuelve a leer el rol con `sed` (ronda 10 de Codex) | cae `el_reparto_lee_el_perfil_con_el_parser_canonico` |
| M12 | el rechazo retira `sirius:implement-requested` (todas las versiones anteriores a la ronda 13 de Codex) | caen `test_el_rechazo_no_toca_ninguna_etiqueta` y las ocho pruebas de rechazo que exigen la etiqueta intacta |

- Las 20 pruebas del fichero en verde; `ruff`, `mypy`; `bash -n` sobre la
  puerta. Batería entera: en la PR.
- El arnés de carriles (`tests/automation/test_carriles_retirados.py`) declaraba
  `programador@2`, un rol que ningún carril del manifiesto conoce, como perfil
  de la implementación. Con la puerta resolviendo el perfil, cuatro pruebas de
  reparto se pusieron en rojo en Quality (dos empujones, `f36d4bd2` y
  `2ba8c231`) porque la puerta rechazaba ese rol, y con razón: el arnés declara
  ahora `implementer@<vigente>`, leído de la ficha del perfil. Lección propia de
  esta PR: la batería de la puerta se corrió, la de los carriles no, y son las
  dos las que ejecutan el guion.

Ronda 6 de Codex sobre `ac3f4870`: la comparación de las dos instantáneas
(evento y cuerpo vigente) usaba un `sed` propio que leía `implementer@4junk`
como `implementer@4` y `Implementer@4` como válido, y daba por iguales dos
cuerpos que el resolutor juzga distintos: la puerta seguía, rechazaba la
instantánea y retiraba una etiqueta que puede ser de otra activación. Las dos
se leen ahora con el parser del resolutor (`resolver_prompt.py --perfil`,
que expone `profile_field`): una verdad, no dos. Prueba:
`test_la_comparacion_del_evento_usa_el_parser_canonico_del_perfil`
(`implementer@Njunk` en el evento frente al vigente en el cuerpo: rancio,
código 2, etiqueta intacta, `ninguno` en el aviso). Mutación M9 (el `sed`
de antes): cae esa prueba.

Ronda 7 de Codex sobre `970bf918`, dos remates del aviso. Lo publica la
primera puerta que lo ve, y como `validate-sirius-activation.yml` suele
llegar antes que el implementador, quien lo lea puede encontrar la incidencia
todavía en `sirius:planned`, donde «cancela este run» no significaba nada: el
aviso prescribe ahora según el estado real (en `planned`: editar el cuerpo,
que vuelve rancio el evento sin tocar etiquetas, y reactivar; en
`implementing`: cancelar el run del implementador y `continua`). Y citaba solo
ADR-223, que vive en la PR #671 y entra en `main` antes que esta: cita ahora
ADR-094 para la reanudación sin PR y ADR-223 (PR #671) para la reposición de
`planned`. Prueba: la del aviso exige las dos ramas y la cita.

Ronda 8 de Codex sobre `0b8c2a78`: entre la puerta del implementador y
«Consumir el evento y marcar en curso» hay unos segundos en los que el
propietario puede editar el `Perfil:` —el aviso de versión no vigente se lo
pide—, y un run que ya hubiera pasado la puerta consumía la etiqueta nueva
con su instantánea vieja. El paso de consumo compara otra vez la instantánea
con el cuerpo vigente, con el mismo parser, justo antes de tocar nada: si
cambió, declara el evento rancio, no consume, no toca ninguna etiqueta y deja
a «Aplicar el veredicto» fuera (`consumed=false`; una consumición que muere sin
escribir su salida sí llega al veredicto, que es lo que la limpia). El aviso lo
dice. Guarda: `test_el_implementador_vuelve_a_comparar_el_perfil_justo_antes_de_consumir`.
La otra mitad de la ronda —que la reanudación con `continua` reponga
`sirius:planned`— es ADR-223 (PR #671), que entra en `main` antes que esta y
que esta rama trae al ponerse al día.

Ronda 9 de Codex sobre `a689802e`, dos remates: (1) la exención del carril ajeno
leía el rol con un `sed` propio, así que `investigador@2junk` pasaba como
`investigador` y el carril de investigación habría ejecutado una orden cuyo
`Perfil:` canónico no existe; ahora decide con `resolver_prompt.py --perfil` y lo
que no es un perfil cae al resolutor y se rechaza
(`test_la_exencion_de_carril_usa_el_parser_canonico`); (2) si el aviso de perfil
no vigente no se podía publicar, la puerta lo convertía en `::warning` y daba la
activación por válida, con lo que el perfil antiguo se consumía con el único
aviso perdido en el log; ahora conserva la activación sin tocar etiquetas y sale
con 3, que el implementador trata como «no se pudo completar; reintentable» y el
validador independiente como run en rojo
(`test_un_aviso_de_no_vigente_que_no_se_puede_publicar_no_valida_la_activacion`).

Ronda 10 de Codex sobre `edf6b206`: quedaba un parser más. El reparto
(`sirius_reparto_activacion.sh` y la llamada de los dos workflows) leía el rol
con el `sed` permisivo: con `Perfil: implementer@4junk` delante y
`Perfil: investigador@2` detrás, repartía por la primera línea (`implementer`)
mientras la puerta, con el parser canónico, eximía por la segunda, y el
implementador consumía una orden del otro carril hasta morir en
`resolver_prompt.py --carril ejecucion`. El rol del `Perfil:` se lee en todas
partes con el mismo parser (`resolver_prompt.py --perfil`): el reparto, las dos
puertas y el marcador del aviso
(`test_el_reparto_lee_el_perfil_con_el_parser_canonico`, que además exige que
no quede ningún `sed -n 's/^Perfil` en los workflows ni en los guiones).

## Consecuencias

- Un cuerpo con `Perfil:` ausente o no registrado ya no arranca un run: se
  rechaza en la puerta con la razón en la incidencia.
- Un `rol@N` antiguo sigue ejecutándose, con un aviso que dice cuál es la
  vigente. Si el propietario quisiera que la puerta exigiera la vigente, eso es
  otra decisión y cambiaría H-28.
- Dos llamadas más a `python3` en la puerta, sin red.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `guardian-que-mide-posicion-en-vez-de-estructura`
- sin esto se repetiría: una puerta que comprueba la forma del cuerpo (las secciones) y no lo que el siguiente paso va a hacer con él (resolver el perfil), y da por válida una activación que muere a los seis segundos.
- lo hace cumplir: `tests/automation/test_sirius_activation.py`

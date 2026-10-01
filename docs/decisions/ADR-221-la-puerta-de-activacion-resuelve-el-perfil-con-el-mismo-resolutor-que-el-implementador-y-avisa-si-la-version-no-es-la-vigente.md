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
   puerta y mataría al implementador (las dos cosas, ronda 1 de Codex en la PR
   #670). Una instantánea **vacía** (el evento llegó sin cuerpo) se juzga vacía,
   no se sustituye por el cuerpo actual (`${ISSUE_BODY-…}`, no `:-`); y el
   aviso de versión no vigente dice que, para ejecutar la vigente, hay que
   editar el cuerpo **y volver a aplicar la etiqueta**, porque solo un evento
   nuevo lleva el cuerpo nuevo (ronda 2 de Codex). Si no resuelve,
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
- `test_la_puerta_juzga_el_cuerpo_que_el_implementador_ejecutara` (cuerpo
  actual vigente, instantánea del evento con `implementer@99`: rechazo, porque
  lo que se iba a ejecutar no resuelve).
- `test_una_instantanea_vacia_del_evento_se_juzga_vacia` (`ISSUE_BODY` vacío:
  rechazo; no se sustituye por el cuerpo actual).

**Mutaciones** (cada una aplicada sobre la puerta, la prueba ejecutada y el
fichero restaurado):

| | Mutación | Resultado |
|---|---|---|
| M1 | la puerta deja de resolver el perfil | cae `un_cuerpo_sin_perfil_se_rechaza` |
| M2 | el `rol@N` no vigente deja de avisar | cae `un_perfil_valido_pero_no_vigente_avisa` |
| M3 | el aviso de no vigente se convierte en rechazo | cae la misma: el evento desaparece |
| M4 | eximir cualquier rol que no sea del carril de ejecución (la primera versión) | cae `un_rol_que_no_esta_en_ningun_carril_se_rechaza` |
| M5 | juzgar el cuerpo actual en vez de la instantánea del evento | cae `la_puerta_juzga_el_cuerpo_que_el_implementador_ejecutara` |
| M6 | sustituir una instantánea vacía por el cuerpo actual (`:-`) | cae `una_instantanea_vacia_del_evento_se_juzga_vacia` |
| M7 | el aviso de no vigente vuelve a decir «edita el cuerpo antes de que arranque» | cae `un_perfil_valido_pero_no_vigente_avisa_y_deja_pasar` |

- Las 19 pruebas del fichero en verde; `ruff`, `mypy`; `bash -n` sobre la
  puerta. Batería entera: en la PR.

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

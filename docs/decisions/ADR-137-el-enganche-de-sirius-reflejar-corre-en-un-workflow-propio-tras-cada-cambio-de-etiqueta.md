# ADR-137 — El enganche de sirius-reflejar corre en un workflow propio tras cada cambio de etiqueta

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Cauce: ADR-002, opción 2 — trabajo sobre `.github/workflows/**` hecho en
  sesión interactiva a petición explícita del propietario (04-09-2026,
  «hazlo tú… el enganche ese»), con su fusión como aprobación. La
  credencial de la automatización sigue sin poder tocar workflows; la de
  esta sesión se prueba con el push de esta misma rama.

Este ADR es además la nota de arranque de su rama: lo de abajo quedó
escrito antes del primer commit.

## Contexto y problema

C1 (`sirius-reflejar`, incidencia #529, ADR-136) está fusionado en `main`
desde el 04-09-2026 (22:03 UTC): el comando que lleva los desenlaces de
GitHub al almacén del motor existe, con 77 pruebas y seis rondas de
revisión detrás. Pero nadie lo ejecuta: el enganche quedó explícitamente
fuera del alcance de #529 (C1b, «decisión del propietario, ADR-002»), así
que el motor sigue sin enterarse solo de nada y `sirius-racha` seguirá
escribiendo `no_comparable` hasta que el reflejo corra de verdad y de
forma continua.

ADR-136 deja la recomendación: «llamar a `uv run sirius-reflejar` justo
después de cada cambio de etiqueta que ya aplican
advance-sirius-after-quality.yml, review-sirius-work.yml,
repair-sirius-work.yml y complete-sirius-after-merge.yml».

## Criterio de parada (escrito ANTES de decidir)

- Si el enganche exigiera tocar el CONTENIDO de los cuatro workflows
  críticos (sus gates, sus veredictos, sus permisos), parar y hablarlo:
  la opción elegida debe ser puramente aditiva o no ser.
- Si el push de la rama fuera rechazado por falta del alcance `workflow`
  en la credencial de sesión, parar sin buscar otra credencial (la
  alternativa descartada por ADR-002) y entregar al propietario el parche
  exacto para aplicar a mano.
- Tras la fusión: si la primera pasada real no deja las siete incidencias
  de la ola reflejadas en el diario (la integración de ADR-136 predice 5
  sucesos por incidencia), tratarlo como fallo del enganche, no del
  comando — el comando ya lo demostró con fixtures reales.

## Opciones consideradas

1. Pasos incrustados en cada uno de los cuatro workflows, justo tras su
   cambio de etiqueta (la lectura literal de la recomendación).
2. Un workflow propio (`reflejar-desenlace.yml`) disparado por
   `workflow_run` al completarse esos cuatro, más una pasada diaria de
   red de seguridad y `workflow_dispatch` manual.
3. Solo la pasada diaria programada, sin `workflow_run`.

## Decisión

**Opción 2.** Un workflow nuevo, `.github/workflows/reflejar-desenlace.yml`,
que calca VERBATIM el patrón ya probado de `contador-siete-dias.yml`
(worktree de la rama `estado-del-motor` ramificando por el código de
`ls-remote`, pasada con `GH_TOKEN` y `SIRIUS_MOTOR_DIARIO`, confirmación
con `if: always()` mirando el código de `git status`, grupo de
concurrencia `motor-sirius`), con tres disparadores:

- `workflow_run` sobre «Advance Sirius after Quality», «Revisar bloque
  Sirius», «Corregir bloque Sirius» y «Complete Sirius after merge» — los
  cuatro nombres verificados contra sus ficheros; «justo después de cada
  cambio de etiqueta», como pide ADR-136, pero por evento, no por
  incrustación.
- `schedule` a las 00:04 UTC: red de seguridad diaria que recoge lo que
  algún `workflow_run` hubiera perdido. La primera versión la puso a las
  03:04, «20 minutos antes del contador», y el guardián de la hora la
  tumbó — ver la comprobación: el contador exige 170 minutos de
  tranquilidad sin disparos programados por delante. A las 00:04 quedan
  200. Si se cambia la hora del contador o algún `timeout-minutes`,
  rederivar (acoplamiento documentado en ambos ficheros).
- `workflow_dispatch` para la pasada manual del propietario.

Por qué no la opción 1: incrustar exige editar los cuatro workflows más
delicados del motor (los que aplican veredictos y etiquetas), repetir en
cada uno la instalación de `uv`, el worktree y el push de la memoria, y
ampliar los permisos de los cuatro con `contents: write` sobre la rama de
memoria. La opción 2 es un fichero nuevo, cero líneas cambiadas en lo
existente, y un único lugar con ese permiso. Por qué no la 3: dejaría
hasta 24 h de retraso entre el desenlace real y su reflejo, y el objetivo
del bloque C es que el motor se entere del ciclo, no que lo reconstruya a
toro pasado.

Dos diferencias conscientes con el patrón del contador, explicadas en los
comentarios del fichero: si la rama de memoria no existe, el reflejo sale
limpio en vez de crearla huérfana (sin diario no hay nada que reflejar;
crear la rama es del despachador), y la pasada corre también para runs
cancelados del workflow observado (reflejar de más es inocuo por la
idempotencia que C1 fija con prueba; adivinar conclusiones sería frágil).

## Comprobación que la sostiene

Rojo previo, visto fallar (la mutación natural de este cambio): con el
cron de la primera versión (03:04),
`test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia` falló en
local con: «el contador dispara a las 03:24 UTC y solo deja 20 min
tranquilos por delante, cuando la tolerancia vigente es de 170 min. Con
etiquetas más frescas que la tolerancia el verificador declara
NO_COMPARABLE, así que ningún día contaría y la racha no avanzaría NUNCA
-en verde-». Es decir: la «red de seguridad» pegada al contador habría
matado en silencio, cada día, exactamente el contador que este enganche
viene a alimentar. Movido el cron a las 00:04, el guardián pasa
(`tests/automation/test_contador_de_siete_dias.py`: verde junto a los de
citas y registro, 181 pruebas).

Lo demás verificable antes de fusionar, verificado:

- Los cuatro `name:` del `workflow_run` coinciden letra a letra con los
  declarados en sus ficheros (`grep -m1 '^name:'` sobre los cuatro en
  `origin/main`, 04-09-2026).
- La interfaz del comando es la asumida: `reflect_cli.py` resuelve el
  diario por `SIRIUS_MOTOR_DIARIO` vía `resolver_diario` (el mismo
  mecanismo que `sirius-racha` usa en `contador-siete-dias.yml`), el
  diario de despacho como hermano del diario, el espejo con
  `GitHubCliMirrorReader` (`gh` + `GH_TOKEN`), y devuelve 0 hubiera o no
  transiciones (docstring y `--help` del propio módulo).
- Los pasos de worktree y confirmación son copia del workflow del
  contador que lleva corriendo en producción desde su fusión; las únicas
  divergencias son las dos documentadas arriba.

Lo NO verificable antes de fusionar, dicho honestamente: un workflow no
se puede ejecutar desde una rama sin fusionar (los disparadores
`workflow_run`/`schedule` leen el fichero de `main`). La verificación
real es la primera pasada tras la fusión — el criterio de parada de
arriba fija qué debe verse: las siete incidencias de la ola reflejadas
(5 sucesos cada una) y `sirius-racha` dejando de decir `no_comparable`
por «no mantiene el estado». El propietario puede adelantar esa
comprobación en local, sin escribir nada, con `uv run sirius-reflejar
--ensayo` sobre un worktree de `estado-del-motor`.

## Consecuencias

- Primera pasada automática: el primer `workflow_run` de los cuatro
  observados tras la fusión, o las 00:04 UTC del día siguiente, lo que
  llegue antes; también se puede lanzar a mano desde Actions
  (`workflow_dispatch`).
- C2 (declarar `programacion` en `CLASES_CON_ESTADO_PROPIO`, ADR-101) se
  decide DESPUÉS de observar al menos una pasada real de este enganche,
  como fija la incidencia #529 — este ADR no lo toca.
- La cuota de lecturas del espejo sube: una pasada por cada run de los
  cuatro workflows observados (serializadas por el grupo de concurrencia)
  más la diaria. ADR-136 ya razonó que es el mismo punto del ciclo donde
  el contador lee, y cada pasada lee solo los WorkItems despachados no
  terminales.
- El acoplamiento de horas con el contador queda anotado en los dos
  sitios que hay que mirar si alguien cambia el cron.

## Alternativas descartadas y por qué

- **Incrustar los pasos en los cuatro workflows (opción 1):** ver la
  decisión — más superficie tocada, permisos repetidos, y el mismo efecto
  con peor aislamiento.
- **Solo la pasada diaria (opción 3):** hasta 24 h de retraso; el bloque
  C pierde su sentido de «el motor se entera del ciclo».
- **Añadir también `resume-sirius-on-command.yml` a los disparadores:**
  innecesario — una reanudación real siempre desemboca en uno de los
  cuatro observados (el corrector o el revisor repuestos corren y
  completan), y la red diaria cubre el resto; menos disparadores, menos
  ruido.
- **Ampliar la credencial de la automatización para que el motor se
  enganche solo:** descartada de raíz por ADR-002; este ADR existe
  precisamente para ejecutar el cauce correcto.

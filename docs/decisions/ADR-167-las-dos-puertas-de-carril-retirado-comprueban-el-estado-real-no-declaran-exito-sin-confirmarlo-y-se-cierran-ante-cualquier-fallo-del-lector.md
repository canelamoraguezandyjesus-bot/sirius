# ADR-167 — Las dos puertas de carril retirado comprueban el estado real, no declaran éxito sin confirmarlo y se cierran ante cualquier fallo del lector

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Corrige: **ADR-163** (PR #569, fusionada como `afe704e`), cuya implementación
  de la retirada reversible traía los cinco defectos que este ADR arregla
- Numeración: 167 y no 165. `scripts/siguiente_adr.py` propuso 165 porque solo
  ve las ramas del clon; las PR abiertas **#573 y #575** ya tienen tomados el
  165 y el 166. Es el mismo modo de fallo que ADR-069 documenta, y aquí se
  evitó mirando las PR abiertas antes de asignar
- Relacionadas: ADR-161 (la retirada acordada), ADR-014 y ADR-015 (la etiqueta
  se escribe con el PAT), ADR-004 y contrato §9.1 (qué repara de verdad el
  reconciliador), ADR-001

> **Este ADR es también la nota de arranque de la rama**, publicado en su propio
> commit antes del primer cambio de código.

## Nota de arranque (publicada ANTES del primer cambio)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** Los cinco defectos viven en
las dos puertas que ADR-163 añadió —`investigar-orden.yml` y
`audit-sirius-repository.yml`— y en el arnés que las prueba. Cuatro son de la
misma familia y conviene decirlo antes de arreglar nada: **la puerta afirma cosas
que no ha comprobado**. Afirma que respondió (sin confirmar el comentario), que
transicionó (sin confirmar las etiquetas), que el carril está activo (cuando el
lector falló de un modo que no previó) y que el evento describe la incidencia
(cuando el evento puede venir atrasado). El quinto es distinto: una prueba que
fija como requisito permanente lo que el contrato promete reversible.

El arreglo vive en las mismas dos puertas, y puede funcionar porque el sitio del
arreglo sí puede observar el fallo: cada afirmación tiene una comprobación
disponible —el código de salida de la llamada, la lectura del estado por la API,
el código del lector— que hoy simplemente no se mira.

**2. ¿Qué NO va a garantizar esto?**

- **No garantiza exactamente-una-vez en el comentario.** `sirius_comment_once`
  ya declara por qué eso es imposible contra la API de GitHub: un POST aceptado
  cuya respuesta se pierde deja el comentario publicado sin que nadie lo sepa.
  Se acota la ventana con el marcador; no se cierra.
- **No garantiza que el job termine en verde.** Al contrario: cuando la
  respuesta o la transición no se puedan confirmar, el paso terminará en **rojo**
  a propósito, que es lo que hoy no hace.
- **No reactiva ningún carril.** El registro real sigue con los dos retirados.
- **No cambia Sirius, la memoria común, el roadmap, permisos, secretos ni
  configuración remota.** No toca revisores, corrector, agregación,
  convergencia, Quality, diario ni informes.
- **No prueba con agentes reales ni con red**: todo con dobles explícitos.

**3. Criterio de parada (escrito ANTES de tocar nada).**

- **(a)** Si algún hallazgo resulta ya corregido en `main`, se dice y no se
  «arregla» otra vez. *Comprobado: los cinco siguen presentes en `afe704e`.*
- **(b)** Si el arreglo del #1 exigiera apoyarse en el reconciliador, **hay que
  demostrar** que repara el estado concreto que se le deja; si no lo repara, el
  diseño cambia en vez de suponerlo. *Se disparó: no lo repara. Ver abajo.*
- **(c)** Si corregir el #2 obligara a leer el estado con credenciales que la
  puerta no tiene, o a tocar permisos, se para.
- **(d)** Si el arreglo del #5 debilitara las comprobaciones de formato o de
  seguridad del registro, se rechaza aunque pase.
- **(e)** Dos rondas con defectos de la misma familia → parar y buscar la raíz.
  La familia ya está nombrada arriba y es la que ordena los cuatro primeros
  arreglos, así que la raíz se ataca de una vez: **ninguna puerta afirma nada
  que no haya confirmado.**

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable es el que ya ocurrió: probar la puerta buscando cadenas en el YAML
en vez de ejecutarla. Una prueba que lee texto no distingue «llama a
`sirius_comment_once`» de «lo llama y comprueba su resultado». Lo hace imposible
**ejecutar el guion real con `bash` y un doble de `gh` que puede fallar a
voluntad**, y comprobar el efecto observable: qué comentarios se publicaron, qué
etiquetas quedaron, qué código de salida dio el paso y si el agente llegó a
ejecutarse. Eso es lo que se construye aquí. Lo que **no** se puede hacer
imposible desde el repositorio: que GitHub acepte un POST y pierda la respuesta.

## Lo que el reconciliador SÍ repara, medido (criterio de parada (b))

Se leyó `scripts/automation/sirius_reconcile.sh` antes de diseñar el arreglo del
hallazgo 1, porque el encargo exige demostrarlo y no suponerlo:

- **Solo repara dos casos**: el A (marcador de completado) y el B
  (`sirius:ci-pending` con Quality ya resuelto). Para todo lo demás **informa y
  no toca** (contrato §9.1, límites 2 y 4).
- Un `sirius:planned` + `sirius:implement-requested` atascado **no se repara**:
  el propio guion lo excluye del informe de contradicción por ser «el ÚNICO
  estado en que `implement-requested` existe en produccion sana».
- Y un `sirius:completed` + `sirius:failed-safely` simultáneo —el síntoma del
  hallazgo 2— le sale como **CONTRADICCION que requiere revisión humana**.

**Conclusión: el reconciliador no es la vía de recuperación de estas puertas.**
El arreglo no se apoya en él. La recuperación es que el paso termine en rojo y
que reejecutarlo converja, porque cada operación es idempotente.

## Decisión

Una regla, de la que salen los cuatro primeros arreglos: **ninguna puerta afirma
nada que no haya confirmado, y ante lo que no puede confirmar se detiene en rojo
en vez de continuar en verde.**

1. **Orden de operaciones e informe de fallos (hallazgo 1).** Primero el
   comentario, después las etiquetas, y **cualquier fallo de cualquiera de los
   dos termina el paso en rojo**. El comentario **no menciona el estado final**,
   así que sigue siendo cierto aunque la transición no llegue a hacerse.
   Reejecutar converge: el marcador evita el comentario duplicado y las
   etiquetas se aplican igual.
2. **Estado real antes de tocar (hallazgo 2).** La puerta lee la incidencia por
   la API y decide con eso, no con el cuerpo del evento: si está cerrada, si
   lleva una etiqueta terminal o de completado, o si ya no lleva
   `sirius:implement-requested`, **no toca nada** y sale con `valid=false`. El
   perfil se relee del cuerpo actual, no del que traía el evento.
3. **Contrato del lector, explícito (hallazgo 3).** `0` retirado, `1` activo,
   **cualquier otro código detiene el paso** con diagnóstico y sin ejecutar el
   carril. Vale para las dos puertas.
4. **Marcador en el cuerpo (hallazgo 4).** El marcador va como primera línea del
   comentario, en la convención de comentario HTML que ya usa
   `sirius_apply_verdict.sh`, y es el mismo que se pasa como argumento.
5. **Pruebas del mecanismo, no del estado del registro (hallazgo 5).** Las
   pruebas usan registros controlados —uno con carriles retirados y otro sin
   ninguno— y dejan de exigir que el registro real tenga siempre las dos
   entradas. Se conservan las comprobaciones de formato y de seguridad, y se
   añade una que demuestra que una reactivación válida las supera.

## Comprobación que la sostiene

**El arnés.** `tests/automation/fixtures/carriles_retirados/` extrae el guion
real del paso del YAML, lo corre con `bash` contra un `gh` doble y devuelve lo
observable: código de salida, comentarios publicados, etiquetas finales, estado
de la incidencia y la lista de llamadas. El doble delega los filtros en el `jq`
de verdad —interpretarlos a mano fue un error del primer intento: bastaba con
que `--jq '{state: .state, is_pr: ...}'` contuviera `.state` para devolver algo
que GitHub nunca habría devuelto— y sabe fallar a voluntad, incluida la
**respuesta ambigua**: publica el comentario **y además** devuelve error.

**Los cinco, reproducidos sobre `afe704e` antes de tocar nada:**

| # | Lo observado en `main` |
|---|---|
| 1a | Fallan las etiquetas → **salida 0** (verde), etiquetas intactas en `planned` + `implement-requested`, 1 comentario |
| 1b | Falla el comentario → **salida 0**, etiquetas en `sirius:failed-safely`, **0 comentarios**: terminal y muda |
| 2 | Evento atrasado sobre incidencia ya completada → **salida 0**, etiquetas finales `['sirius:completed', 'sirius:failed-safely']` |
| 3 | Lector con código 127 → puerta de investigación: **`valid=true`**, es decir, el investigador habría corrido sobre un carril retirado; auditor: **`retirado=false`**, hacia el modelo |
| 4 | Dos activaciones iguales → **2 comentarios** |
| 5 | `test_el_registro_declara_los_dos_carriles_retirados` exigía `set(carriles) == set(CARRILES)`: quitar una entrada —la reactivación que §13.2.1 promete— dejaba la suite en rojo |

**Prueba de mutación, que es lo que hace que las pruebas valgan algo.** Con los
arreglos aplicados: **45 pasan**. Guardando *solo* los dos workflows arreglados y
dejando el resto (`git stash push -- .github/workflows/...`), las mismas 45
pruebas dan **17 fallos y 28 pases** contra el código de `main`. Ninguna prueba
nueva pasa por casualidad:

```
FAILED test_el_camino_bueno_explica_y_cierra_en_un_estado_terminal
FAILED test_si_fallan_las_etiquetas_el_paso_termina_en_rojo
FAILED test_si_falla_el_comentario_no_se_toca_ninguna_etiqueta
FAILED test_reejecutar_tras_un_fallo_de_etiquetas_converge
FAILED test_dos_activaciones_iguales_dejan_un_solo_comentario
FAILED test_una_respuesta_ambigua_no_acaba_en_comentario_duplicado
FAILED test_no_se_toca_una_incidencia_que_ya_no_esta_esperando[evento-atrasado-sobre-incidencia-completada]
FAILED test_no_se_toca_una_incidencia_que_ya_no_esta_esperando[incidencia-cerrada]
FAILED test_no_se_toca_una_incidencia_que_ya_no_esta_esperando[carrera-con-el-validador]
FAILED test_no_se_toca_una_incidencia_que_ya_no_esta_esperando[evento-repetido]
FAILED test_manda_el_perfil_del_cuerpo_actual_y_no_el_del_evento
FAILED test_si_no_se_puede_leer_la_incidencia_no_se_toca[la-api-no-responde]
FAILED test_si_no_se_puede_leer_la_incidencia_no_se_toca[respuesta-ilegible]
FAILED test_un_codigo_inesperado_del_lector_detiene_la_puerta[3]
FAILED test_un_codigo_inesperado_del_lector_detiene_la_puerta[127]
FAILED test_un_codigo_inesperado_del_lector_detiene_al_auditor[3]
FAILED test_un_codigo_inesperado_del_lector_detiene_al_auditor[127]
```

El parámetro `[2]` **pasa** en las dos versiones, y así debe ser: el código `2`
era el único que ADR-163 ya trataba bien. Decirlo importa tanto como decir los
diecisiete.

**Un matiz del hallazgo 3 que solo apareció al aislar la variable.** El primer
shim hacía fallar *todas* las llamadas a `python3`, así que también rompía el
validador de activación y la puerta se detenía —por el motivo equivocado—: la
prueba habría pasado sin probar nada. Con un shim que falla **solo** para
`sirius_carril_retirado.py` y delega el resto en el intérprete real, se ve lo que
la puerta concluye de verdad: `valid=true`. Es un fallo más grave de lo que la
primera reproducción sugería.

**La recuperación, demostrada y no supuesta (criterio de parada (b)).**
`test_reejecutar_tras_un_fallo_de_etiquetas_converge` parte del estado que dejó
una primera pasada fallida —no de una incidencia limpia— y comprueba que la
segunda **no republica** (1 comentario, no 2) y **sí** completa la transición,
saliendo con 0. El reconciliador no interviene, y ya se había medido que no
podía.

**La reversibilidad, demostrada sin tocar el registro real.** Cuatro
configuraciones controladas —los dos retirados, cada uno reactivado por
separado, y ninguno— pasan las comprobaciones de formato y seguridad; tres
registros mal formados las hacen fallar (campo ausente, clase no autorizada,
`carriles` que no es un objeto), que es lo que prueba que esas comprobaciones
siguen siendo comprobaciones. Y con un registro en el que investigación ya no
consta retirada, la misma puerta **ejecutada** no comenta, no pone
`failed-safely` y llega a `valid=true`. `docs/implementation/work_engine/carriles_retirados.json`
**no se ha modificado**: los dos carriles siguen retirados.

**Comprobaciones del repositorio**, con la invocación exacta de CI:
`ruff format --check .`, `ruff check .`, `mypy src tests` y `pytest`. Resultados
en el cuerpo de la PR.

## Lo que sigue sin estar garantizado, dicho aquí y no descubierto luego

- **La ventana con el validador concurrente se acorta, no se cierra.**
  `validate-sirius-activation.yml` reacciona al MISMO evento de etiqueta, con
  otro grupo de concurrencia, así que los dos corren a la vez. La puerta lee el
  estado y decide con esa instantánea; si el validador retira
  `sirius:implement-requested` **después** de esa lectura y **antes** de la
  escritura, la incidencia acaba en `sirius:failed-safely` con el diagnóstico
  del validador además de la explicación del carril. No es una contradicción
  —`failed-safely` es terminal y el reconciliador no lo señala—, y el desenlace
  coincide con la intención del validador: parar. Cerrarlo del todo exigiría un
  compare-and-swap sobre las etiquetas que la API de GitHub no ofrece. Lo que la
  puerta sí garantiza es que **no actúa sobre una activación que ya no está
  viva** en el momento en que mira.
- **El comentario sigue sin ser exactamente-una-vez.** El marcador acota la
  ventana; un POST aceptado cuya respuesta se pierde no se puede descartar. Lo
  que sí queda probado es que la siguiente pasada no duplica.
- **Los runs históricos siguen siendo relanzables a mano** desde Actions por
  quien tenga permisos: reejecutan el YAML de aquel commit, sin estas puertas.
  Ya lo declaraba ADR-163 y sigue siendo cierto.
- **El paso que prepara el encargo del investigador sigue usando el cuerpo del
  evento** (`ISSUE_BODY`), no la instantánea de la puerta. No es uno de los cinco
  hallazgos y no se toca aquí; solo corre con el carril **activo**, y la puerta
  ya ha comprobado para entonces que el perfil del cuerpo actual es el suyo.

## Segunda ronda: la regla de las dos rondas se dispara, y la raíz es otra

La revisión de `398017a` encontró cuatro defectos más, todos ejecutando las
puertas con el mismo arnés. **Son de la misma familia que los cinco anteriores**,
así que ADR-001 obliga a parar de parchear y buscar la raíz. Esta es:

> **La puerta de retirada se construyó como una segunda máquina de estados sobre
> la misma incidencia, con copias locales de decisiones que el ciclo ya tiene en
> un solo dueño. Las copias divergen.**

Cuatro duplicaciones, una por defecto:

| Lo que la puerta se copió | Quién es el dueño de verdad |
|---|---|
| Qué estados son incompatibles con una activación nueva | `sirius_validate_activation.sh`: `INCOMPATIBLE_STATES`, **diez** estados. La puerta copió **cuatro** |
| Si la transición de etiquetas se completó | `sirius_set_issue_labels`, que verifica el estado final — pero escribe en **varias operaciones independientes**, y la puerta la trató como atómica |
| Quién atiende una activación | el campo `Perfil:`. Dos puertas lo leían **de momentos distintos** |
| Qué carriles están retirados | el registro. Las pruebas de comportamiento lo **fijaban** en vez de parametrizarlo |

La primera ronda arregló cómo la puerta **informa**. Esta arregla de dónde
**decide**: se deja de copiar y se usa al dueño; y donde no hay dueño —una
transición a medias— la operación se hace re-entrante, con su propia huella
publicada como lo que la reejecución reconoce.

## Nota de arranque de la segunda ronda (publicada ANTES del primer cambio)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** En la puerta, otra vez, pero
no en su forma de informar sino en su forma de decidir. Los cuatro se reprodujeron
antes de escribir nada —el encargo lo exige— y el arreglo va donde está el dueño
de cada decisión: llamar al validador en vez de reimplementarlo, reconocer la
propia huella en vez de suponer atomicidad, un solo sitio que reparta la
activación entre las dos puertas, y registros controlados en las pruebas.

**2. ¿Qué NO va a garantizar esto?**

- **No hace atómica la escritura de etiquetas.** `sirius_set_issue_labels` seguirá
  haciendo varias llamadas y GitHub seguirá pudiendo aceptar unas y no otras. Lo
  que se garantiza es que reejecutar **completa** lo que quedó a medias.
- **No garantiza un único comentario bajo concurrencia real.** Dos jobs que
  publiquen a la vez pueden duplicar; el marcador acota la ventana.
- **No cambia `sirius_set_issue_labels`, `sirius_validate_activation.sh` ni el
  reconciliador.** Son de todo el ciclo; tocarlos por un caso propio es
  exactamente la clase de cambio que este encargo excluye.
- **No reactiva ningún carril.** El registro entregado conserva los dos.

**3. Criterio de parada (escrito ANTES de tocar el código).**

- **(a)** Si algún defecto ya está resuelto en un commit posterior, se comprueba
  y se dice; no se «arregla» dos veces.
- **(b)** Si arreglar el reparto de perfiles obligara a **cambiar el tipo de
  trabajo** de una orden en silencio, se rechaza el diseño: se exige activación
  nueva, explicada y recuperable.
- **(c)** Si la recuperación de una transición parcial no pudiera distinguirse
  de un trabajo posterior legítimo, se para y se pide revisión humana en vez de
  imponer un desenlace.
- **(d)** Si arreglar las pruebas exigiera debilitar las comprobaciones de
  formato o seguridad del registro, se rechaza aunque pase.
- **(e)** Si apareciera una **tercera** ronda de la misma familia, el diseño de
  la puerta está mal planteado y hay que rehacerlo, no parchearlo.

**4. ¿Qué haría imposible el error más probable, en vez de improbable?** El error
más probable es volver a copiar una decisión que ya tiene dueño —es lo que ha
pasado dos veces—. Lo hace imposible **no tener dónde copiarla**: la lista de
estados incompatibles desaparece de la puerta (la aplica el validador, llamado),
y el reparto de perfiles desaparece de los dos workflows (lo aplica un solo
guion, llamado por los dos). Lo que no se puede hacer imposible: que GitHub
acepte una escritura y pierda otra.

## Consecuencias

- Las dos puertas pueden terminar en rojo donde antes terminaban en verde. Es el
  cambio buscado: un verde que no se ha ganado es peor que un rojo.
- El registro real **no cambia**: los dos carriles siguen retirados.
- Las pruebas de este mecanismo pasan a **ejecutar** los guiones de los pasos.
  El arnés vive en `tests/automation/fixtures/carriles_retirados/` y está
  disponible para cualquier otra puerta que quiera probarse igual.

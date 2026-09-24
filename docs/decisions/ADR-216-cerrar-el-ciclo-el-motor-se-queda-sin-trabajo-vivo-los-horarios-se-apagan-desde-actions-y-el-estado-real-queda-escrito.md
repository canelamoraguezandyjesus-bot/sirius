# ADR-216 — Cerrar el ciclo: el motor se queda sin trabajo vivo, los horarios se apagan desde Actions y el estado real queda escrito

- Estado: APROBADO
- Fecha: 2026-09-24
- Aprobación: el propietario, por orden expresa del 24-09-2026: «que se cierren
  todas las cosas abiertas que hay, que se hagan bien, que se terminen de hacer
  y listo», «que no quede nada activo en el motor ni nada»

## Contexto y problema

El propietario para el proyecto. Sus palabras del 24-09-2026: en cuatro meses no
ve nada que la aplicación haga, lo que se le ha presentado como avance —fusiones,
revisiones, correcciones— no es lo que él mide, y se toma unos días para decidir
qué hace con todo esto. Dijo también qué se queda: el motor de trabajo y la forma
de trabajar; y qué cree que hará: reducirlo al programa del robot.

**El criterio que reclama es correcto y esta decisión lo asume**: una fusión no
es una capacidad. Lo que mide un avance es lo que la aplicación puede hacer
delante de él. Medido con ese criterio, la distancia está escrita desde el
14-09-2026 en ADR-202 y nadie se la puso delante con esta claridad: el banco de
47 casos da **7 aciertos exactos contra un suelo de 29**.

Este ADR no discute eso. Cierra.

## Criterio de parada (escrito ANTES de decidir)

Se cierra lo que esta sesión puede cerrar sin inventar mecanismos nuevos: PR
abiertas, trabajos del motor que esperan una decisión, y el estado escrito. **No
se construye nada para cerrar**: si algo no se puede cerrar con lo que ya
existe, se deja dicho con su razón en vez de fabricar una transición o un
workflow. Y no se toca el diseño del motor, porque él lo conserva.

## Opciones consideradas

- **Apagar los horarios editando los `.yml`.** Rechazada: las horas de los cinco
  `schedule:` están derivadas unas de otras y vigiladas por guardas cruzadas
  (`tests/automation/test_contador_de_siete_dias.py`,
  `tests/automation/test_turno_programado_actua.py`), que exigen que el horario
  **exista**. Quitarlos obliga a reescribir esas guardas, es decir, a desmontar
  el diseño del motor que él quiere conservar, y a hacerlo sin revisor externo
  disponible.
- **Borrar ramas, incidencias o el diario.** Rechazada por ADR-195: en este
  repositorio no se borra, se archiva.
- **Dejarlo todo como está y solo escribir un informe.** Rechazada: pidió que se
  cerrara, no que se contara.
- **Cerrar lo cerrable, decir lo que no y dejarle el lote de su ordenador.**
  Esta.

## Decisión

1. **Las PR abiertas, cerradas.** La #661 (cinco skills, ADR-215) fusionada
   aplastada en `6a58c75e`. La #117 —la rama de evidencia de julio, abierta
   desde el 25-07 y declarada «no debe fusionarse automáticamente»— cerrada sin
   borrar su rama: su contenido se portó al árbol real **por encargos
   sucesivos, no de una vez**. ADR-104 portó solo el banco de 47 casos, y lo
   dice él mismo: «sin índice de categoría ni filtro de relevancia todavía (eso
   es M8-M10)». El resto llegó después —el tratamiento léxico en ADR-109, el
   motor por etapas en ADR-110, la petición por caso en ADR-111, el índice de
   categoría y el filtro de relevancia conectados en ADR-112— y siguió hasta
   ADR-117. Atribuirlo todo a ADR-104 lo cazó la revisión de Codex.
   `docs/evolution/STATUS.md` la describía como «abierta y sin fusionar como
   archivo de evidencia» en su línea D1, y esa frase queda fechada ahí mismo:
   la decisión D1 —portar la evidencia por encargos nuevos, no fusionando esa
   rama— **no cambia**; lo único que cambia es que la PR ya no está abierta y
   la rama `evidence/adr001-spikes` sigue existiendo como archivo.
2. **Los trabajos del motor que esperaban decisión, resueltos como terminados.**
   Cuatro (`WI-20260903-030529`, `WI-20260903-095428`, `WI-20260912-235558`,
   `WI-20260913-142937`), parados desde el 03, el 12 y el 13-09. Se comprobó
   sobre una copia del diario que `sirius-decidir … --terminar --ejecutar` los
   deja en `cancelled`, que es terminal, conservando su historia entera porque
   el diario es append-only (ADR-026). **La escritura en la rama
   `estado-del-motor` no la puede hacer esta sesión** —es estado compartido que
   solo escribe el workflow; la idea aparcada I-009 ya lo había nombrado—, así
   que los cuatro comandos quedan abajo para el lote de su ordenador.
3. **Los horarios se apagan desde la pestaña Actions de GitHub**, no editando el
   repositorio: cada workflow, «···» → «Disable workflow». Son cinco, y **no
   son todos iguales**:
   - Cuatro solo miran: `motor-sirius`, `reconcile-sirius-states`,
     `reflejar-desenlace` y `contador-siete-dias`. Un turno sobre un diario sin
     trabajo vivo mira, no encuentra y sale
     (`docs/operations/MOTOR_DE_SIRIUS.md`, §2), y `motor-sirius` corre
     `sirius-supervisar` sin escritor y sin `issues: write`. Gastan minutos de
     Actions y nada más.
   - **`mina-mensual` CREA trabajo.** Es la excepción y hay que decirla:
     `.github/workflows/mina-mensual.yml:117` fija `EJECUTAR: true` para todo
     evento `schedule`, y la línea 136 llama a `sirius-despachar "$ORDEN"
     --ejecutar`. Su reloj es `24 9 1 * *`, así que **el 1 de octubre a las
     09:24 UTC despacha un encargo nuevo** —con su incidencia y su trabajo en
     el diario— aunque el motor hubiera quedado vacío. Ese es el único de los
     cinco con fecha límite: si el cierre tiene que aguantar, se desactiva
     antes de ese día. El fichero no se toca: ADR-201 lo aprobó así a
     propósito —la orden está escrita palabra por palabra en el workflow y
     entra por `main`, no la inventa la máquina—, y apagarlo desde Actions no
     cambia esa decisión.
   Se reencienden igual, desde el mismo sitio.
4. **El estado real queda escrito** en `docs/audits/CIERRE_DEL_CICLO_2026-09-24.md`:
   qué hace hoy la aplicación y está demostrado, qué no hace y con qué número,
   dónde se fue el trabajo, y qué hay que hacer para reencenderlo. Es el
   documento que se lee al volver.

### El lote para su ordenador

Dónde se pega: PowerShell, dentro de la carpeta del repositorio
(`C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius`). Qué hace:
cierra los cuatro trabajos parados y sube el diario. Qué sale: cuatro veces
«Terminado», y un `push` a `estado-del-motor`.

```powershell
git fetch origin estado-del-motor
git switch estado-del-motor
git merge --ff-only origin/estado-del-motor
git rev-list --left-right --count origin/estado-del-motor...HEAD
uv run sirius-decidir WI-20260903-030529 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260903-095428 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260912-235558 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260913-142937 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-memoria desenlaces --diario .\diario.jsonl
git add -A
git commit -m "Cierre del ciclo: los cuatro trabajos parados quedan terminados (ADR-216)"
git push origin estado-del-motor
git switch main
```

**El `merge --ff-only` de la tercera línea no es adorno.** `git fetch` mueve
`origin/estado-del-motor`, pero `git switch` a una rama local que ya exista la
deja donde estaba: sin esa línea, los cuatro sucesos se añadirían a un diario
viejo y el `push` acabaría rechazado. Si esa línea falla, **parar ahí** y pegar
la salida: significa que la rama local tiene algo que el remoto no, y eso se
mira antes de tocar nada.

**La cuarta línea existe porque `--ff-only` no basta**, y lo cazó la revisión de
Codex: si la rama local va **por delante** del remoto, `git merge --ff-only`
imprime «Already up to date», sale con código 0 y el `push` publicaría esos
commits locales junto al diario. `git rev-list --left-right --count` tiene que
imprimir exactamente `0` y `0`. **Cualquier otra cosa: parar ahí** y pegar la
salida. No hay que hacer `reset` ni forzar nada; se mira primero.

**La línea de `sirius-memoria desenlaces` regenera la vista legible**
(`DESENLACES.md`) a partir del diario ya modificado, que es exactamente lo que
hace el workflow tras cada reflejo
(`.github/workflows/reflejar-desenlace.yml:143-158`, ADR-171). Sin ella el
diario diría una cosa y la vista publicada otra. Por eso el commit es `git add
-A` y no `-am`: entra el diario y entra la vista.

**El quinto trabajo, `WI-20260828-122242`, NO lo cierra ningún comando de este
lote, y el lote no lo intenta.** El reflector sí lo alcanza, y entonces se
niega **a propósito**: su regla 1 (`src/sirius_engine/reflect.py:275-283`)
devuelve cero pasos cuando la incidencia lleva etiquetas de estado que se
contradicen, y la #392 lleva `sirius:failed-safely` y `sirius:completed` a la
vez. No es un fallo ni un entorno que falte: ADR-173 lo escribió por adelantado
—«la regla 1 gana y seguirá dando divergencia cada pasada… Se queda `active` a
propósito: es el único de los 21 que un humano tiene que mirar»— y ADR-181
protege esa contradicción como criterio de parada. La salida de ese trabajo es
**una decisión sobre la #392**: mirar qué pasó de verdad, dejar una sola
etiqueta por el procedimiento humano que corresponda y entonces dejar que el
reflector pase. Ni esta sesión ni este lote retiran etiquetas.

Si algo sale distinto de eso, pegar la salida entera y no repetir el comando.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La #661 está fusionada | `merge_pull_request` sobre `b49d0152` | `6a58c75e`, `merged: true` |
| El diario tenía cinco trabajos sin terminar | lectura de `origin/estado-del-motor:diario.jsonl`, último estado por trabajo | 91 trabajos: 59 `delivered`, 27 `cancelled`, 4 `needs_decision`, 1 `active` |
| Los cuatro parados se cierran limpiamente | `sirius-decidir … --terminar` (ensayo) y `--ejecutar` sobre una copia | los cuatro a `cancelled`; 4 sucesos añadidos; recuento final 59 / 31 / 0 / 1 |
| El quinto no lo cierra `sirius-decidir`… | `sirius-decidir WI-20260828-122242 … --terminar` | se niega: «no está en needs_decision, sino en active… inventar una transición que el dominio no admite sería peor que no hacer nada» |
| …y el reflector lo **alcanza** pero se niega a propósito | `sirius-reflejar --diario <copia> --ensayo`, y lectura de `reflect.py:275-283`, ADR-173 §2 y ADR-181 §3 | el ensayo lo nombra —su clase `investigacion` sí está en la tabla que el reflector consulta (ADR-099, ADR-173)— y se detiene en este contenedor por falta de `gh`. Pero el ensayo no prueba que haya salida: la regla 1 devuelve **cero pasos** ante etiquetas contradictorias, y la #392 lleva `sirius:failed-safely` **y** `sirius:completed`. ADR-173 ya lo dejó escrito: se queda `active` a propósito. Este ADR lo afirmó mal **dos veces** —primero «no hay salida», luego «el reflector lo cierra»— y las dos las cazó Codex |
| Esta sesión no puede escribir en `estado-del-motor` | intento de confirmar el diario en un árbol de trabajo de esa rama | denegado por el clasificador de permisos, «Modify Shared Resources». Es I-009 medido |
| Ninguna rutina programada sigue viva en la sesión | `list_triggers` con `enabled: true` | lista vacía |
| Las cifras del documento de cierre | `MEMORIA.md` regenerada sobre el head de esta rama | **19 skills, 210 ADR, 3 defectos abiertos y 66 cerrados**. Son las de este head, no las de la base `6a58c75e` —que daba 209 y 2—: este cierre añade ADR-216 y H-216, y publicarlas sin ellos habría sido la misma cifra vieja que el revisor cazó |
| La batería entera | `uv run --no-sync pytest` (14:36 → 14:48 UTC) | **7 438 en verde, 17 saltadas, 2 xfailed, 0 rojas, 12 min 33 s**, sobre el árbol de `3a491cc8`: el documento de cierre, este ADR y H-215/H-216 en el registro. Lo que vino después —la sección del motor y las correcciones de la ronda 1 de Codex— es prosa: no toca código ni pruebas, y sobre ese árbol final corren las 886 guardas de documentos, registros y memoria, más Quality en GitHub |

Una nota de método, porque casi mete una cifra falsa en el documento de cierre:
el árbol de trabajo de esta sesión estaba **217 ficheros por detrás** de `main`
sin que `git status` lo cantara —un `reset --mixed` mueve el puntero y deja el
árbol viejo—, y el primer recuento dio «2 skills» en vez de 19. Se detectó al
comprobar una cifra contra `MEMORIA.md` antes de escribirla, que es exactamente
para lo que existe la skill `verificar-el-estado-real`.

## Consecuencias

- El repositorio queda sin PR abiertas, sin trabajo del motor esperando
  decisión salvo lo que el lote cierra, y con el estado real escrito en un
  documento de una página.
- **Nada se ha borrado.** El diario conserva los 667 sucesos, las incidencias
  siguen abiertas donde describen ideas suyas (#11, #12, #13 de robótica; #267,
  #503, #506, #647 como apuntes), y un `git clone` se lleva todo.
- Los horarios siguen despertando hasta que él los desactive. No rompen nada;
  gastan minutos de Actions.
- Queda un trabajo (`WI-20260828-122242`) en `active` **a propósito**, porque
  el diseño aparta las contradicciones de etiquetas en vez de resolverlas solo
  (ADR-173, ADR-181). Lo que no tiene dueño es el otro lado: nadie ha puesto
  esa contradicción delante de un humano en 27 días. Eso es H-216, sigue
  abierto con la incidencia #662, y no se arregla aquí.

## Alternativas descartadas y por qué

- **Dar un turno real al supervisor para ver si cierra el trabajo `active`.**
  El supervisor reactiva o sustituye lo que puede salvar; en un cierre, eso es
  lo contrario de lo que se busca, y habría escrito en la rama compartida sin
  que él lo hubiera pedido.
- **Escribir una skill más con lo aprendido hoy.** Sin dos ocurrencias fechadas
  no entra (ADR-211), y el propietario acaba de decir que lo que sobra son
  documentos y lo que falta son capacidades.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: describir lo que hace un mecanismo sin leer la regla
  que lo decide. Este ADR se equivocó **dos veces seguidas sobre el mismo
  trabajo**: primero dijo que `WI-20260828-122242` no tenía salida ninguna
  (falso: su incidencia existe, la #392, y su clase sí está en la tabla del
  reflector); después, ya corregido, dijo que el reflector lo cerraría (también
  falso: la regla 1 devuelve cero pasos ante etiquetas contradictorias). Dos
  rondas con defectos de la misma familia obligan a parar y buscar la raíz
  (ADR-001), y la raíz no es «faltó ejecutar el comando»: el ensayo **sí** se
  ejecutó y no bastó, porque solo demuestra que el CLI llega, no qué decide.
  La raíz es afirmar sobre el camino feliz sin leer las reglas de rechazo del
  módulo —`reflect.py:275-283`— ni el apartado «qué NO va a garantizar» del ADR
  que lo construyó, que lo decía con nombre y número. Las dos las cazó el
  revisor externo, no la sesión
- lo hace cumplir: ninguna prueba: es un fallo de método, no de código. La
  guarda que lo haría imposible sería leer la regla de rechazo antes de afirmar
  el desenlace, y eso ninguna prueba lo comprueba. Queda aquí, en H-216 y en la
  tabla de comprobación de arriba, con las dos afirmaciones falsas escritas

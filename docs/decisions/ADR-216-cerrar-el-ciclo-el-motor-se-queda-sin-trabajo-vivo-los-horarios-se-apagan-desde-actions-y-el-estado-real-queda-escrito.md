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
- **Cerrar lo cerrable, decir lo que no y dejarle un comando para su ordenador.**
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
   que los cuatro cierres quedan en el guion de abajo, para su ordenador.
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

### El comando para su ordenador

**Uno solo, y es un guion del repositorio.** Antes, una vez: abrir PowerShell
en la carpeta del repositorio y hacer `git pull` en `main`, que es donde entra
el guion. Después, este comando, que ya lleva la ruta escrita y funciona desde
donde sea porque el guion se coloca solo. Qué hace: cierra los cuatro trabajos
parados, regenera la vista y publica el diario. Qué sale: cuatro veces
«Terminado» y, al final, «Listo. Los cuatro trabajos quedan terminados y el
diario esta publicado».

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius\scripts\cierre_del_ciclo.ps1"
```

Si sale cualquier otra cosa, pegar la salida entera y no repetir el comando.

**Por qué un guion y no el lote de once líneas que decía este ADR hasta la
ronda 3.** Ese lote acumuló **tres defectos de la misma familia en dos rondas**
de revisión externa: la rama local adelantada que `--ff-only` no rechaza; un
`git rev-list … 0 1` impreso que no detiene nada porque imprimir no es parar; y
un `git add -A` que publicaría en `estado-del-motor` cualquier fichero suelto de
su carpeta. La raíz no era ninguna de las tres: era que **las salvaguardas
estaban escritas en la prosa de debajo del bloque, no en el código**, y un
bloque pegado entero se ejecuta entero. Dos rondas con la misma familia obligan
a parar y arreglar la raíz (ADR-001), no a parchear una línea más. La skill
`comandos-para-su-ordenador` ya lo decía con otras palabras: «un comando por
mensaje».

Y había un cuarto defecto que ninguna ronda había visto, encontrado al ir a
escribir el guion: **`git switch estado-del-motor` habría roto el lote entero**.
Esa rama es huérfana y tiene **cuatro ficheros** —`git ls-tree` del 24-09-2026:
`DESENLACES.md`, `diario.jsonl`, `diario-despacho.jsonl`,
`racha_siete_dias.jsonl`—, así que el árbol se quedaba sin `pyproject.toml` y
sin `src/`, y el primer `uv run` no habría encontrado el proyecto. El workflow
nunca hizo eso: clona la memoria aparte y ejecuta desde el repositorio
(`reflejar-desenlace.yml`). El guion hace lo mismo.

Lo que el guion garantiza, y una prueba lo fija porque aquí no hay `pwsh`
(`tests/automation/test_cierre_del_ciclo_ps1_no_puede_hacer_dano.py`, la misma
forma que ADR-153 usó para `check.ps1`):

- **Cada llamada nativa comprueba su `$LASTEXITCODE`** y el guion muere en el
  primer rojo, antes de tocar el diario.
- **Se clona limpio** en una carpeta nueva fuera de OneDrive. Un clon recién
  hecho *es* el remoto: no hay rama local atrasada, adelantada ni divergente
  que comprobar, y el problema que las dos rondas intentaban atrapar deja de
  existir. El `push` va con refspec explícita (`HEAD:refs/heads/estado-del-motor`),
  así que se rechaza solo si el remoto se movió mientras tanto.
- **Se añaden los dos ficheros por su nombre**, nunca `-A`.
- **`DESENLACES.md` se regenera antes de confirmar**, como hace el workflow tras
  cada reflejo (ADR-171).
- **No se cambia de rama en su repositorio**, ni se fuerza nada, nunca.
- **`uv` copia en vez de enlazar** (`UV_LINK_MODE=copy`), antes de la primera
  llamada. El repositorio vive bajo OneDrive y ahí uv ya falló en su máquina
  con el error 396 de Windows (skill `comandos-para-su-ordenador`, 08 y
  09-08-2026); `build_windows_impl.ps1:417` lo resuelve igual. Sin esto, una
  sincronización del entorno tumbaría el único comando antes de publicar nada.
  Lo cazó la ronda 4, sobre el guion recién escrito: **la guarda estructural no
  cubría lo que el guion hace, solo lo que no debe hacer**.

**El quinto trabajo, `WI-20260828-122242`, NO lo cierra ningún comando de este
guion, y el guion no lo intenta.** El reflector sí lo alcanza, y entonces se
niega **a propósito**: su regla 1 (`src/sirius_engine/reflect.py:275-283`)
devuelve cero pasos cuando la incidencia lleva etiquetas de estado que se
contradicen, y la #392 lleva `sirius:failed-safely` y `sirius:completed` a la
vez. No es un fallo ni un entorno que falte: ADR-173 lo escribió por adelantado
—«la regla 1 gana y seguirá dando divergencia cada pasada… Se queda `active` a
propósito: es el único de los 21 que un humano tiene que mirar»— y ADR-181
protege esa contradicción como criterio de parada. La salida de ese trabajo es
**una decisión sobre la #392**: mirar qué pasó de verdad, dejar una sola
etiqueta por el procedimiento humano que corresponda y entonces dejar que el
reflector pase. Ni esta sesión ni este guion retiran etiquetas.

Si algo sale distinto de eso, pegar la salida entera y no repetir el comando.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La #661 está fusionada | `merge_pull_request` sobre `b49d0152` | `6a58c75e`, `merged: true` |
| El diario tenía cinco trabajos sin terminar | lectura de `origin/estado-del-motor:diario.jsonl`, último estado por trabajo | 91 trabajos: 59 `delivered`, 27 `cancelled`, 4 `needs_decision`, 1 `active` |
| Los cuatro parados se cierran limpiamente | `sirius-decidir … --terminar` (ensayo) y `--ejecutar` sobre una copia | los cuatro a `cancelled`; 4 sucesos añadidos; recuento final 59 / 31 / 0 / 1 |
| El quinto no lo cierra `sirius-decidir`… | `sirius-decidir WI-20260828-122242 … --terminar` | se niega: «no está en needs_decision, sino en active… inventar una transición que el dominio no admite sería peor que no hacer nada» |
| …y el reflector lo **alcanza** pero se niega a propósito | `sirius-reflejar --diario <copia> --ensayo`, y lectura de `reflect.py:275-283`, ADR-173 §2 y ADR-181 §3 | el ensayo lo nombra —su clase `investigacion` sí está en la tabla que el reflector consulta (ADR-099, ADR-173)— y se detiene en este contenedor por falta de `gh`. Pero el ensayo no prueba que haya salida: la regla 1 devuelve **cero pasos** ante etiquetas contradictorias, y la #392 lleva `sirius:failed-safely` **y** `sirius:completed`. ADR-173 ya lo dejó escrito: se queda `active` a propósito. Este ADR lo afirmó mal **dos veces** —primero «no hay salida», luego «el reflector lo cierra»— y las dos las cazó Codex |
| `estado-del-motor` es huérfana y no tiene con qué ejecutar nada | `git ls-tree --name-only origin/estado-del-motor` (24-09-2026) | cuatro ficheros: `DESENLACES.md`, `diario.jsonl`, `diario-despacho.jsonl`, `racha_siete_dias.jsonl`. Por eso el guion clona aparte en vez de cambiar de rama: un `git switch` ahí deja el árbol sin `pyproject.toml` |
| El guion no puede seguir sobre un fallo, publicar de más ni morir por OneDrive | `pytest tests/automation/test_cierre_del_ciclo_ps1_no_puede_hacer_dano.py` | 6 en verde. Verificado **por mutación** el mismo día, cinco veces: quitar una comprobación de `$LASTEXITCODE`, volver a `git add -A`, colar un `git switch`, quitar `UV_LINK_MODE` y ponerlo después de la primera llamada a uv tumban cada uno su prueba, y las demás siguen pasando |
| Esta sesión no puede escribir en `estado-del-motor` | intento de confirmar el diario en un árbol de trabajo de esa rama | denegado por el clasificador de permisos, «Modify Shared Resources». Es I-009 medido |
| Ninguna rutina programada sigue viva en la sesión | `list_triggers` con `enabled: true` | lista vacía |
| Las cifras del documento de cierre | `MEMORIA.md` regenerada sobre el head de esta rama | **19 skills, 210 ADR, 3 defectos abiertos y 66 cerrados**. Son las de este head, no las de la base `6a58c75e` —que daba 209 y 2—: este cierre añade ADR-216 y H-216, y publicarlas sin ellos habría sido la misma cifra vieja que el revisor cazó |
| La batería entera, con el guion y su guarda dentro | `uv run --no-sync pytest` (16:04 → 16:17 UTC) | **7 444 en verde, 17 saltadas, 2 xfailed, 0 rojas, 12 min 36 s**. Son seis más que la corrida de las 14:36 sobre `3a491cc8` (7 438): las seis del guardián nuevo. Lo único posterior a esta corrida es prosa de este mismo ADR, y sobre el árbol final vuelven a correr en verde las guardas de documentos, registros, memoria y skills, más Quality en GitHub |

Una nota de método, porque casi mete una cifra falsa en el documento de cierre:
el árbol de trabajo de esta sesión estaba **217 ficheros por detrás** de `main`
sin que `git status` lo cantara —un `reset --mixed` mueve el puntero y deja el
árbol viejo—, y el primer recuento dio «2 skills» en vez de 19. Se detectó al
comprobar una cifra contra `MEMORIA.md` antes de escribirla, que es exactamente
para lo que existe la skill `verificar-el-estado-real`.

## Consecuencias

- El repositorio queda sin PR abiertas, sin trabajo del motor esperando
  decisión salvo lo que el guion cierra, y con el estado real escrito en un
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
- sin esto se repetiría: escribir una salvaguarda en prosa y darla por puesta.
  Este ADR le dio al propietario un lote de once líneas cuyas protecciones
  vivían en los párrafos de debajo —«si esa línea falla, parar ahí»—, y un
  bloque pegado entero se ejecuta entero. La revisión externa encontró **tres**
  formas distintas de hacer daño con él en dos rondas, y una **cuarta** apareció
  al ir a escribir el guion: `estado-del-motor` es una rama huérfana de cuatro
  ficheros, así que el `git switch` del propio lote habría dejado el árbol sin
  `pyproject.toml` y ningún `uv run` habría arrancado. Es la misma forma que el
  otro error de este ADR, que también costó dos rondas: afirmar lo que hace un
  mecanismo —el reflector sobre `WI-20260828-122242`, primero «no hay salida»,
  después «lo cierra»— sin leer sus reglas de rechazo. En los dos casos se
  razonó sobre el camino feliz y se publicó sin ejecutar ni leer lo que decide
- lo hace cumplir: tests/automation/test_cierre_del_ciclo_ps1_no_puede_hacer_dano.py
  fija la forma del guion donde no hay `pwsh`, igual que ADR-153 hizo con
  `check.ps1`: cada llamada nativa seguida de su comprobación de
  `$LASTEXITCODE`, los dos ficheros añadidos por su nombre, ninguna orden que
  cambie de rama ni fuerce nada, y la vista derivada regenerada antes de
  confirmar. Verificado por mutación el 24-09-2026: quitar una comprobación,
  volver a `git add -A` y colar un `git switch` matan cada uno su prueba. La
  otra mitad —leer la regla de rechazo antes de afirmar un desenlace— no la
  comprueba ninguna prueba porque es método, y queda escrita en H-216 y en la
  tabla de comprobación de arriba

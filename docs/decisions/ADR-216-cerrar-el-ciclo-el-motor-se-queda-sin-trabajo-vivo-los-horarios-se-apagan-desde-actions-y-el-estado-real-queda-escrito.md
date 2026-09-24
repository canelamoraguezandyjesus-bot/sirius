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
   borrar su rama: su contenido se portó al árbol real en ADR-104.
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
   repositorio: cada workflow, «···» → «Disable workflow». Son cinco:
   `motor-sirius`, `reconcile-sirius-states`, `reflejar-desenlace`,
   `contador-siete-dias` y `mina-mensual`. Se reenciende igual. Mientras tanto
   no rompen nada: un turno sobre un diario sin trabajo vivo mira, no encuentra
   y sale (`docs/operations/MOTOR_DE_SIRIUS.md`, §2), y `motor-sirius` corre
   `sirius-supervisar` sin escritor y sin `issues: write`.
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
uv run sirius-decidir WI-20260903-030529 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260903-095428 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260912-235558 --diario .\diario.jsonl --ejecutar --terminar
uv run sirius-decidir WI-20260913-142937 --diario .\diario.jsonl --ejecutar --terminar
git commit -am "Cierre del ciclo: los cuatro trabajos parados quedan terminados (ADR-216)"
git push origin estado-del-motor
git switch main
```

Si algo sale distinto de eso, pegar la salida entera y no repetir el comando.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La #661 está fusionada | `merge_pull_request` sobre `b49d0152` | `6a58c75e`, `merged: true` |
| El diario tenía cinco trabajos sin terminar | lectura de `origin/estado-del-motor:diario.jsonl`, último estado por trabajo | 91 trabajos: 59 `delivered`, 27 `cancelled`, 4 `needs_decision`, 1 `active` |
| Los cuatro parados se cierran limpiamente | `sirius-decidir … --terminar` (ensayo) y `--ejecutar` sobre una copia | los cuatro a `cancelled`; 4 sucesos añadidos; recuento final 59 / 31 / 0 / 1 |
| El quinto no se puede cerrar con nada | `sirius-decidir WI-20260828-122242 … --terminar` | se niega: «no está en needs_decision, sino en active… inventar una transición que el dominio no admite sería peor que no hacer nada» |
| Esta sesión no puede escribir en `estado-del-motor` | intento de confirmar el diario en un árbol de trabajo de esa rama | denegado por el clasificador de permisos, «Modify Shared Resources». Es I-009 medido |
| Ninguna rutina programada sigue viva en la sesión | `list_triggers` con `enabled: true` | lista vacía |
| Las cifras del documento de cierre | recuento sobre el árbol de `6a58c75e` | 19 skills, 209 ADR, 2 defectos abiertos y 66 cerrados |
| La batería entera | `uv run --no-sync pytest` | BATERIA_PENDIENTE |

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
- Queda un trabajo (`WI-20260828-122242`) en un estado del que no hay salida.
  Es H-216, y no se arregla aquí: arreglarlo es tocar el motor.

## Alternativas descartadas y por qué

- **Dar un turno real al supervisor para ver si cierra el trabajo `active`.**
  El supervisor reactiva o sustituye lo que puede salvar; en un cierre, eso es
  lo contrario de lo que se busca, y habría escrito en la rama compartida sin
  que él lo hubiera pedido.
- **Escribir una skill más con lo aprendido hoy.** Sin dos ocurrencias fechadas
  no entra (ADR-211), y el propietario acaba de decir que lo que sobra son
  documentos y lo que falta son capacidades.

## La lección

- familia: `estado-en-el-que-se-entra-y-del-que-no-se-sale`
- sin esto se repetiría: retirar un carril de trabajo y dejar dentro lo que ya
  estaba en vuelo, que queda vivo para siempre porque el despachador rechaza su
  clase y ningún comando admite sacarlo; ADR-189 lo arregló para
  `needs_decision` y el mismo agujero seguía abierto un escalón más arriba,
  en `active`
- lo hace cumplir: ninguna prueba: la salida no existe todavía, y construirla es
  tocar el dominio del motor, que esta decisión deja congelado a propósito.
  Queda registrado en H-216 para cuando se reabra

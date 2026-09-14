# Nota de arranque — `ci-pending` no distingue «todavía no» de «nunca»

Rama `fix/ci-pending-no-espera-un-suceso-que-no-va-a-llegar`, 14-09-2026.
Publicada **antes del primer commit de arreglo**, como exige ADR-001.

Las cuatro preguntas y el criterio de parada de abajo se fijaron **a las 07:07
UTC**, antes de tomar ninguna medida. La rama no pudo abrirse hasta que ADR-193
dejó `main` quieto: los dos trabajos tocan el mismo fichero, y abrir antes
habría repetido el conflicto que esta nota investiga.

## Corrección: lo que la medida cambió de esta misma nota

Esta nota nació creyendo que el silencio de la incidencia #619 lo causaba el
camino que describe. **La medida dijo otra cosa**, y se escribe aquí en vez de
reescribir la historia: el reconciliador ni siquiera llegaba a ese camino,
porque no podía fechar el estado —`gh api` rechazaba su lectura de sucesos—.
Ese defecto es otro, se midió aparte y lo cierra **ADR-193**.

Lo que queda, y es lo que decide esta nota, es lo que se ve **una vez arreglado
aquello**: con la fecha ya legible, una incidencia en `ci-pending` cuya PR está
en conflicto **sigue sin recibir aviso**, porque el camino del aviso exige que
Quality haya concluido, y ahí no concluye nunca. El defecto es real y es
independiente; lo que era falso era creer que ya estaba actuando.

## El suceso

La incidencia #619 pasó a `sirius:ci-pending` a las 01:43 y seguía ahí a las
07:03, cinco horas y veinte minutos después. No porque Quality tardara: porque
**Quality no llegó a correr ni una sola vez** para la rama de su PR, la #620.
La PR nació en conflicto —la #618 se fusionó tres minutos antes de abrirla y las
dos tocan `registro_defectos.yml` y `MEMORIA.md`—, y una PR en conflicto no
tiene combinación que construir, así que el suceso `pull_request` que dispara
`quality.yml` no produce ningún run.

`sirius_reconcile.sh` está escrito para el caso en que el resultado está por
llegar: cuando no hay resultado informa en el resumen del run y **no publica
nada en la incidencia**. Cuando no va a llegar nunca, dice lo mismo.

Es el patrón de ADR-183 con otra causa. Allí el push del corrector no disparaba
Quality; aquí es la PR la que no puede tener ninguno. El daño es el mismo: un
estado que solo mueve la máquina, esperando un suceso que nadie va a emitir.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo no vive en la PR —estar en conflicto es un estado legítimo y visible—
ni en `quality.yml`, que hace lo correcto no corriendo sobre una combinación que
no existe. Vive en **quien lee «no hay resultado» y concluye «todavía no»**: una
inferencia que era verdad mientras toda PR podía tener un run, y dejó de serlo
sin que nadie lo notara.

El arreglo va donde ya vive esa inferencia: el caso B de
`scripts/automation/sirius_reconcile.sh`. Es la única pieza que ya tiene delante
las dos cosas —la PR y el resultado de Quality— y ya tiene permiso para leer la
tercera: `reconcile-sirius-states.yml` declara `pull-requests: read`, así que la
mergeabilidad se consulta sin tocar `.github/**` y sin pedir un permiso nuevo.

*¿Puede el sitio del arreglo observar el fallo que arregla?* Sí, y es la razón de
elegirlo: no hace falta ningún dato que no pueda leer ya.

## 2. ¿Qué NO va a garantizar esto?

- **No desatasca nada.** Avisa. Poner al día la rama exige `contents: write` en
  un workflow, que es decisión del propietario y de la familia que ADR-002
  resolvió en contra. Es exactamente lo que ADR-191 dejó escrito que no
  cableaba, y sigue sin cablearse aquí.
- **No impide el conflicto.** Dos ramas que tocan el mismo fichero van a seguir
  chocando; eso lo atacan ADR-191 (la cola) y ADR-192 (el identificador).
- **No inventa una transición.** `sirius:ci-pending` lo mueve solo la máquina. El
  reconciliador no va a moverlo por esta causa: hacerlo sería decidir que el
  trabajo fracasó, y no ha fracasado — está esperando mal.
- **No promete cazar todas las formas de «nunca».** Cierra la que está medida y
  reproducida. Si mañana aparece otra causa de cero runs, esta guarda no la ve.

## 3. Criterio de parada, decidido ANTES de mirar ningún resultado

- **Si la medida refuta la premisa, se para y no se escribe el arreglo.** La
  premisa es «una PR en conflicto no recibe ningún run de Quality». Si aparece
  una sola PR en conflicto CON runs, la causa de los cero runs de la #620 es
  otra y este trabajo estaría arreglando algo que no ha entendido.
- **Si la medida dice que solo ha pasado una vez**, se dice con esas palabras y
  se decide igual —un estado terminal silencioso no necesita repetirse para ser
  un defecto—, pero entonces la forma tiene que ser **la más barata que
  funcione**: un aviso dentro del caso que ya existe, no una pieza nueva.
- **No vale si avisa de una PR que simplemente va lenta.** Mientras la
  mergeabilidad sea desconocida —GitHub la calcula en diferido y devuelve
  `null`— no se afirma nada. Fallo cerrado, como el resto del guion.
- **No vale si el aviso no dice qué hacer.** Un aviso que solo constata deja el
  atasco igual de atascado; la lección de ADR-183 fue precisamente esa.
- **No vale si se repite** cada seis horas sobre el mismo hecho.
- **No debilita nada.** Las demás pruebas de `sirius_reconcile.sh` pasan sin
  retocarse y ninguna transición existente cambia.
- **Cada regla nueva trae una mutación sembrada y vista caer.**

## 4. ¿Qué haría el fallo imposible en vez de improbable?

**Que el estado no se creyera, se derivara.** Hoy `sirius:ci-pending` es una
etiqueta que alguien puso y que solo otro suceso quita: es memoria, y la memoria
se queda pillada cuando el suceso que la iba a limpiar no existe. Un estado
derivado —«¿tiene esta rama un run de Quality?»— no puede quedarse pillado
porque no guarda nada. Es la forma de ADR-174, ADR-179, ADR-182 y ADR-191.

Y hay una segunda mitad, más cara: **que la rama no pueda estar desactualizada**,
porque el ciclo la pone al día él mismo antes de pedir CI. Eso hace imposible el
conflicto que causa los cero runs, no solo visible su consecuencia. Exige
`contents: write`, toca `.github/**` y es decisión del propietario. Queda
declarado aquí, sin hacerse, como lo dejó ADR-191.

## La medida (criterio declarado antes de contar)

Comparación natural, con el contenido controlado: **la misma rama, el mismo
árbol, el mismo actor y el mismo workflow**; lo único que cambia es el
conflicto.

| | PR #620 (en conflicto) | PR #624 (mismo contenido, sin conflicto) |
|---|---|---|
| Abierta | 14-09 01:42:35 | 14-09 07:02 |
| Empujones al head | 3 | 2 |
| Runs de `quality.yml` para su rama | **0** | **1**, arrancado a los ~40 s |
| Tiempo observado | 5 h 20 min | — |
| Estado de su incidencia | `sirius:ci-pending`, sin un solo aviso | completada |

Y el reconciliador pasó por en medio: el run 132, a las 04:55:51 del 14-09, cae
dentro de esa ventana de cinco horas. No publicó nada sobre la #619 —aunque por
el defecto de ADR-193, no por este—, así que la ventana no tuvo ningún aviso por
ninguna de las dos causas.

**Lo que esta medida NO dice, y no se va a estirar:** un solo caso no es una
tasa. No se ha buscado cuántas PR en conflicto ha habido en la historia del
repositorio ni cuántas incidencias murieron así, porque la mergeabilidad pasada
no es recuperable de la API. Lo que sostiene la decisión no es la frecuencia: es
que el estado final es **silencioso y permanente**, y eso basta según el
criterio de parada escrito arriba.

# ADR-200 — La cola deja de ser una condición y pasa a ser un mecanismo: el ciclo trae la base a la rama que espera

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, el 14-09-2026, eligiendo la **opción A** de las
  tres que se le pusieron delante en la incidencia #608.
- Incidencia: #608
- Nota de arranque: `docs/audits/arranque-la-cola-trae-main-a-la-rama.md`
- Completa: ADR-191, que construyó la condición y dejó escrito que no la cableaba

## Contexto y problema

ADR-191 construyó `scripts/automation/sirius_cola.py`: una sola pregunta —¿es la
punta de la base ancestro del head de esta rama?— y de ella sale la cola entera,
sin cerrojos que alguien tenga que acordarse de soltar.

Y lo dejó **sin llamante, a propósito**: cablear la condición sin que nadie
ponga al día la rama que espera habría cambiado un atasco por otro peor, porque
la rama esperaría para siempre.

Así que la pieza llevaba desde entonces sin gobernar nada. Es el **noveno** caso
contado en este repositorio de «una pieza correcta a la que no llama nadie», la
enfermedad que `tests/automation/test_piezas_con_llamante.py` existe para cerrar
—y que no podía ver esta, porque su inventario se deriva de `src/sirius_engine`
y esta pieza vive en `scripts/automation/`.

Lo que costó mientras tanto, medido en doce horas de la noche del 13 al 14-09:

| | |
|---|---|
| PR muertas de obsolescencia | **3** (#617, #621, #620) |
| Reconciliaciones a mano | una por cada fusión |
| PR que nació en conflicto y nunca tuvo CI | #620: **0 runs** en 5 h 20 min |

Y el caso que da nombre al defecto: la #611 aterrizó trece minutos después de la
#602 sobre un `main` que su rama no tenía incorporado, y dejó `main` en rojo con
dos `H-39`. **Ninguna de las dos pull requests podía verlo**: cada una estaba
verde y cada una tenía razón. El fallo no vive dentro de una rama; vive entre dos.

## Decisión

**1. La cola se consulta antes de reponer la revisión.** En la rama `success)` de
`.github/workflows/advance-sirius-after-quality.yml`, antes de aplicar
`sirius:review-requested`, se lee `compare/{base}...{head}` —el mismo dato que
ese paso ya lee unas líneas más arriba para ADR-187, así que no se añade ninguna
llamada de clase nueva— y decide `sirius_cola.py`.

**2. Esperar es una NO-transición, y se cuenta.** No se aplica ninguna etiqueta y
la incidencia se queda donde estaba. Pero se publica **una vez por head** un
comentario que dice que la rama espera y por qué: una espera que no se cuenta no
se distingue de un atasco (ADR-183).

**3. El ciclo trae la base a la rama que espera.** Un paso nuevo hace checkout de
la rama con `SIRIUS_BOT_TOKEN`, fusiona la base y empuja. El push dispara Quality
sobre la combinación real; cuando ese run vuelva por aquí, la condición se
cumplirá y la rama entrará a revisión sola. **Nadie tiene que hacer nada.**

**4. Un conflicto real se deshace y se dice.** `git merge --abort` deja la rama
exactamente como estaba, y un comentario pide una persona. Eso no lo decide una
máquina.

**5. La red de seguridad tampoco se salta la cola.** Encontrado al comprobar el
cambio, no antes: `scripts/automation/sirius_reconcile.sh` tiene un «caso B» que,
cuando una incidencia lleva demasiado tiempo en `sirius:ci-pending` y Quality
está en verde, **reconcilia la transición a revisión por su cuenta**. Sin tocarlo,
la red habría metido en revisión exactamente las ramas que el punto 1 acaba de
decidir detener, unas horas después y con aspecto de haber arreglado algo.

Es el error que los comentarios de ese mismo fichero llaman **«decidir por otro
sistema sin leer su predicado»** (auditoría #146), y que ya costó una vez
arrancar al revisor sobre una PR en borrador. El predicado cambió hoy; ahora lo
lee: el reconciliador consulta la misma cola antes de reconciliar, y si la rama
espera, lo dice en vez de transicionar.

## Lo que esta decisión NO cuesta, y se creyó que costaba

A la incidencia #608 se le puso delante la opción A con este «en contra»: *«un
workflow más con permiso de escritura en ramas»*. **Comprobado antes de
escribirlo: no es cierto.**

- El push va con `SIRIUS_BOT_TOKEN`, que es **la misma credencial** con la que
  `repair-sirius-work.yml` ya empuja los commits del corrector a la rama de una
  PR (`token:` en su checkout, `persist-credentials: true`).
- El bloque `permissions:` gobierna el `GITHUB_TOKEN`, **no** el PAT. Así que
  `contents:` sigue en `read` y no se toca.

No se abre ninguna clase de permiso nueva, que es exactamente lo que ADR-002
protege. Y no podía ir con `GITHUB_TOKEN` aunque se quisiera: un push hecho con
él **no dispara workflows**, así que Quality no volvería a correr y la rama
quedaría esperando otra vez — el mismo atasco con otra cara, que es el defecto
que ADR-183 documentó.

## Una medida que esta misma PR pagó

Mientras se escribía esto, ADR-199 se fusionó en `main`. La rama de este trabajo
había salido del `main` anterior y las dos tocan los dos ficheros que toca todo
—`MEMORIA.md` y el registro de defectos—. GitHub contestó
`merge conflict between base and head`, y **la PR que automatiza la puesta al día
tuvo que rehacerse a mano sobre el `main` nuevo**.

No es una anécdota: es la frase con la que abre la incidencia #608 —«dos ficheros
que todas tocan convierten N ramas en N² reconciliaciones»— comprobada en el
único sitio donde no se podía discutir.

## Comprobación que la sostiene

Cuatro mutaciones, las cuatro vistas fallar:

| | mutación | qué suspende |
|---|---|---|
| M1 | el workflow no llama a `sirius_cola.py` | la condición vuelve a no gobernar nada |
| M2 | la llamada se hace **después** de reponer la revisión | la rama ya entró cuando se pregunta si podía |
| M3 | el checkout de la puesta al día usa `github.token` | el push no dispararía Quality y la espera sería eterna |
| M4 | el reconciliador no mira la cola | la red de seguridad manda a revisión la rama que el ciclo detuvo |

Y las pruebas leen el YAML **sin sus líneas de comentario**, porque la cabecera
de ese workflow explica toda esta historia: buscar el nombre del módulo en el
fichero entero daría verde con la llamada quitada. Es la lección que
`test_reanudar_una_parada.py` ya había pagado.

El doble de `gh` aprende a contestar `/compare/`, con la disciplina de ADR-193:
un doble que no sabe lo que sabe el `gh` real certifica una ficción. Y la PR
sembrada declara ahora su `base` como objeto, igual que la API real, por la
misma razón por la que ya declaraba `head` así.

### La guarda que se puso en rojo sola, y es la mejor prueba de todas

La corrida completa de esta rama **suspendió**, y no en una de las pruebas
nuevas:

```
tests/automation/test_sirius_runner_python_compat.py::
test_the_listed_scripts_are_the_ones_the_workflows_invoke

Estos scripts se invocan desde workflows o desde la biblioteca Bash pero no
están cubiertos por la comprobación de sintaxis del runner: ['sirius_cola.py']
```

Esa batería **deriva del árbol** qué scripts invocan los workflows, en vez de
leer una lista escrita a mano (ADR-179). Y el docstring de `sirius_cola.py`
llevaba desde ADR-191 prometiendo que esa batería lo vigilaba — **lo cual era
falso**, por una razón exacta: la derivación busca quién lo llama, y hasta hoy
**no lo llamaba nadie**.

La guarda no estaba rota: decía la verdad sobre un árbol en el que la pieza no se
ejecutaba. Al darle llamante, lo encontró sola y se puso en rojo. Es la
comprobación **independiente** de que el cableado de esta decisión es real y no
decorativo: ninguna prueba escrita para este trabajo podría haberlo demostrado
igual de bien, porque todas las escribí yo sabiendo lo que quería que dijeran.

## Lo que este ADR NO hace, y hay que saberlo

- **No prueba el `git merge` de verdad en este árbol.** `git merge` está
  denegado en la sesión que lo escribe, así que lo comprobado aquí es la
  decisión (que ya cubría `tests/automation/test_cola.py`) y el cableado. Que el
  paso funcione solo lo demuestra ejecutarlo — es el límite que
  `tests/automation/test_expresiones_de_workflow.py` declara de sí misma, y vale
  igual aquí. **La primera puesta al día real se vigila a mano.**
- **No resuelve un conflicto**: lo deshace y pide una persona.
- **No garantiza entrar a la primera.** Si la base se mueve mientras la rama se
  pone al día, le toca otra vuelta. Eso es la cola funcionando.
- **No serializa el motor.** Se ordena la ENTRADA a revisión, no el trabajo: se
  pueden seguir mandando varios encargos a la vez, que es lo que el propietario
  pidió y lo que la opción C habría tirado.
- **No amplía `test_piezas_con_llamante.py` a `scripts/automation/`**, que sería
  el arreglo de clase. La razón es una medida, no pereza: ADR-190 midió hace unas
  horas esa misma tentación —ampliar una guarda a un árbol vecino— y encontró
  **0 defectos reales y 23 falsos positivos**. Queda como candidato con su
  medición pendiente.

## La lección

- familia: `condicion-construida-sin-el-mecanismo-que-la-hace-cumplible`
- sin esto se repetiría: una guarda se construye entera y se deja sin llamante
  porque cablearla exigiría una segunda pieza que no está decidida, y la razón
  —buena— se escribe en el ADR y no en ninguna prueba; `sirius_cola.py` estuvo
  desde ADR-191 sin gobernar nada mientras tres PR morían de obsolescencia en
  doce horas.
- lo hace cumplir: `tests/automation/test_cola.py`

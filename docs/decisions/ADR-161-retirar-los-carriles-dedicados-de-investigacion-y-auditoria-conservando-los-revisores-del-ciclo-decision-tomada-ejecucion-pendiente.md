# ADR-161 — Retirar los carriles dedicados de investigación y auditoría, conservando los revisores del ciclo: decisión tomada, ejecución pendiente

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Entrada en vigor: la fusión de la Pull Request que introduce este ADR, por el
  propietario, conforme al procedimiento establecido en este repositorio. **Esa
  aprobación documental NO ejecuta la retirada**: la retirada técnica es un acto
  posterior, sin fecha, y no ocurre por fusionar
- Contexto: la dirección del propietario recogida en
  `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §7.1, punto 2. La nota
  de arranque de este trabajo es la de **ADR-160**, publicada antes del primer
  cambio documental; este ADR se acoge a ella y no abre otra
- Relacionadas: **ADR-010** y **ADR-016** (autorizan el carril del Auditor),
  **ADR-095**, **ADR-097**, **ADR-098** y **ADR-099** (autorizan el carril del
  Investigador), a los que **supera sin editarlos**; ADR-088 (precedente exacto
  de cómo se enmienda la tabla cerrada de clases); ADR-002 (la automatización no
  escribe en `.github/**`); ADR-160 (el reparto de responsabilidades)

## Contexto y problema

El motor tiene dos carriles dedicados que no forman parte del ciclo de
programación: la **auditoría** (`auditoria:solicitada`, ADR-016) y la
**investigación** (perfil `investigador`, ADR-099). El propietario decide que
esos encargos pasen a sus sesiones de ChatGPT, Claude y Codex.

El riesgo de esta decisión no es retirar de menos: es **retirar de más**. Los
dos carriles se pueden confundir con los revisores del ciclo, que el propietario
conserva expresamente. Por eso este ADR nombra las piezas de cada función antes
de decidir nada, y la propuesta las enumera fichero a fichero en su apartado 2.3.

## Criterio de parada (escrito ANTES de decidir)

Se hereda el de ADR-160 —al que este trabajo se acoge— y se le añaden dos
condiciones propias, escritas antes de tocar el registro:

- **(e)** Si al enumerar las piezas apareciera **una sola** compartida entre un
  carril a retirar y un revisor del ciclo, la retirada no se registra como
  «limpia»: se declara esa pieza, o se para. *Se disparó*: hay una, la puerta
  del implementador, y queda **declarada como pendiente de tratamiento** en el
  punto 4 —no resuelta aquí—.
- **(f)** Si registrar la retirada exigiera declarar en un documento algo que el
  árbol contradice hoy, manda el árbol. *Se disparó*: `TABLA_ACTIVACION` sigue
  teniendo las dos clases, así que el contrato **no** las borra, las marca como
  retirada acordada con ejecución pendiente.

## Opciones consideradas

1. **Borrar los dos carriles ahora** —clases, tablas, workflows, perfiles y
   pruebas—. Descartada: la orden prohíbe tocar código y workflows, y además
   destruye trabajo medido antes de saber si el traslado a las sesiones externas
   rinde.
2. **Congelar**: dejarlo todo y limitarse a no usarlo. Descartada como registro:
   no deja rastro comprobable, y «no usarlo» depende de que nadie aplique la
   etiqueta. Un carril vivo que nadie vigila es peor que uno desactivado.
3. **Registrar la decisión ahora y recomendar desactivación reversible como
   ejecución posterior.** Elegida.

## Decisión

1. **Se retiran los carriles dedicados de investigación y auditoría.** Dejan de
   ser el camino de esos encargos, que pasan a las sesiones externas del
   propietario.
2. **Los revisores del ciclo y las comprobaciones de las entregas se conservan
   enteros**, y se nombran para que una retirada mal delimitada no se los lleve:
   revisor Claude (`.github/workflows/review-sirius-work.yml`), segundo revisor
   Codex (`scripts/automation/sirius_codex_review.py`), agregación
   (`scripts/automation/sirius_aggregate_reviews.py`), convergencia
   (`scripts/automation/sirius_convergence.py`), corrector
   (`.github/workflows/repair-sirius-work.yml`) y comprobaciones
   (`.github/workflows/quality.yml`, `scripts/check.ps1`), con sus perfiles y sus
   prompts. Ninguno comparte lógica con los dos carriles retirados.
3. **La decisión no es la ejecución, y se distinguen aquí en una línea:** hoy no
   se desactiva nada. `TABLA_ACTIVACION` sigue conteniendo `AUDITORIA` e
   `INVESTIGACION` (`src/sirius_engine/dispatcher.py`), los workflows siguen en
   su sitio, y las etiquetas siguen creadas. **Mientras eso siga así, los dos
   carriles siguen funcionando si alguien los dispara.**
4. **La única costura con el ciclo, declarada por el criterio (e), queda
   PENDIENTE de tratamiento:** el workflow del implementador declina las
   activaciones de perfil `investigador` para que las atienda
   `investigar-orden.yml` (`.github/workflows/implement-sirius-work.yml:171-180`).
   Qué se hace con esa puerta **no se decide aquí**, y este ADR no afirma que
   pueda dejarse tal cual: decidirlo exige antes **comprobar todas las vías de
   entrada** al carril —entre ellas, y sin darlas por agotadas: la activación
   manual de una etiqueta por una persona, las órdenes ya despachadas y aún en
   curso, los reintentos y relanzamientos del propio ciclo, el reconciliador, y
   cualquier WorkItem con perfil `investigador` que exista cuando la retirada se
   ejecute—. Esa comprobación es parte de **preparar** la retirada, no de este
   registro, y **no se ha hecho**. Nota operativa, no conclusión: modificar esa
   puerta exigiría escribir en `.github/**`, donde la automatización no puede
   (ADR-002), así que quien prepare la retirada debe contar con una mano
   distinta.
5. **Lo que la retirada NO alcanza**, para que nadie lo deduzca de más:
   - `docs/investigaciones/` y los informes de auditoría **se conservan**: son
     resultados, no agentes, y la guarda de caducidad
     (`tests/automation/test_investigaciones_declaran_caducidad.py`) sigue
     protegiendo su formato.
   - `docs/audits/` **no es el auditor**: la mayoría de sus ficheros son notas de
     arranque y de evidencia de ADR-001, más `registro_defectos.yml`.
   - Los bloques S2, B1 y C4 del motor **siguen cerrados**: un bloque cerrado
     registra lo que se midió, no lo que se usa. Se les añade una marca de
     retirada, no un cambio de estado.
   - Los seis ADR que autorizan los dos carriles **no se editan**: se superan.

## Recomendación técnica de ejecución (no ejecutada)

Cuando el propietario ordene ejecutar la retirada, la forma recomendada es
**desactivación reversible**, y en este orden:

0. **Antes que nada, enumerar y comprobar todas las vías de entrada** a cada
   carril, incluidas las activaciones manuales de etiqueta y las órdenes
   pendientes o en curso. Sin ese inventario, «desactivar el disparador» es una
   suposición sobre cuántos disparadores hay.
1. Dejar de despachar las dos clases y retirar las vías de entrada que ese
   inventario haya encontrado.
2. **Conservar** código, perfiles, prompts, ADR, historial y resultados.
3. Decidir, **con el inventario del paso 0 delante**, qué se hace con la
   etiqueta `auditoria:solicitada` y con la puerta del punto 4. Este ADR no
   anticipa esa decisión.

Motivo de que la forma recomendada sea reversible: es lo más barato de deshacer
si el traslado a las sesiones externas no rinde, y no destruye nada medido. El
borrado definitivo, si algún día se quiere, es una decisión posterior con su
propio ADR.

**Nada de esto se ha hecho.** Este apartado es una recomendación de forma, no un
registro de ejecución ni un plan comprobado.

## Comprobación que la sostiene

- **Las piezas de cada función están enumeradas y son disjuntas**, salvo la del
  punto 4: `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §2.3 las lista
  fichero a fichero, comprobadas en el árbol.
- **La costura del punto 4 es la única *entre los workflows del ciclo*, y eso es
  todo lo que se ha comprobado**: buscando `auditor`/`auditoria` e
  `investigador`/`investigacion` en `review-sirius-work.yml`,
  `repair-sirius-work.yml`, `implement-sirius-work.yml`, `quality.yml` y
  `advance-sirius-after-quality.yml`, los únicos aciertos con efecto son las
  líneas 171-180 del implementador; el resto son comentarios. **No se ha
  comprobado** el conjunto de vías de entrada a los carriles —etiquetas
  aplicadas a mano, órdenes en curso, reintentos, reconciliador—, y por eso el
  punto 4 queda pendiente en vez de resuelto.
- **El árbol contradice cualquier redacción que dé la retirada por ejecutada**:
  `TABLA_ACTIVACION` sigue teniendo las cuatro clases. Por eso el contrato
  operativo marca las filas en vez de borrarlas, y esa marca es la comprobación
  de que la distinción decisión/ejecución no es retórica: se puede leer en el
  documento y contrastar con el código.
- **Ningún fichero fuera de `docs/` se ha modificado** en el commit que registra
  esta decisión.
- **El campo `retirada_acordada` es compatible con los lectores y validadores
  que existen**, y esto se comprobó en vez de suponerse:
  1. **Lector único.** Buscando `bloques_del_motor` en todo el árbol
     (`*.py`, `*.sh`, `*.ps1`, `*.yml`, `*.yaml`), el único consumidor es
     `tests/automation/test_registro_de_bloques.py`. No lo lee nada de `src/`,
     `scripts/` ni `.github/`.
  2. **No hay lista cerrada de campos.** Esa guarda declara
     `CAMPOS_SIEMPRE = ("id", "titulo", "estado")` como campos **obligatorios**,
     no como los únicos permitidos, y no comprueba campos desconocidos. El
     registro ya llevaba diez campos opcionales —`evidencia`, `medido_hoy`,
     `que_lo_cerraria`, `decidido`, `depende_de`, `ojo`,
     `actualizado_25_08_2026`, `actualizado_27_08_2026`, `incidencia`—:
     `retirada_acordada` es el undécimo, no un patrón nuevo.
  3. **Los identificadores no cambian**, así que
     `test_ningun_bloque_conocido_desaparece` sigue satisfecho: S2, B1 y C4
     conservan `id`, `titulo`, `estado: cerrado` y `evidencia`.
  4. **La guarda pasa**: 30 pruebas en verde.
  5. **Y se ha visto MORDER con el campo puesto**, que es lo que evita dar por
     buena una compatibilidad vacua: quitando la línea `evidencia` de C4 —el
     bloque que lleva `retirada_acordada`— fallan exactamente
     `test_todo_bloque_cerrado_dice_que_lo_demuestra` y
     `test_cada_bloque_del_registro_pasa_sus_dos_reglas[C4]` (2 fallidas, 28
     pasadas). Es decir: el campo nuevo **no se confunde con evidencia** ni
     desactiva la regla. Revertida la mutación, vuelven las 30 en verde.

## Consecuencias

- El contrato operativo pasa a **v1.10**: las filas de `investigación` y
  `auditoría` de §11.1 y la fila de auditoría de §12.4 quedan marcadas como
  **retirada acordada, ejecución pendiente**, y una sección nueva al final
  registra la enmienda. Las filas no se borran mientras el código las tenga.
- El orden de conmutación de §11.3 —documental → programación → auditoría—
  quedará en dos clases cuando la retirada se ejecute. Hasta entonces, no cambia.
- `docs/implementation/bloques_del_motor.yml` marca S2, B1 y C4 con la retirada
  acordada, conservando su estado y su evidencia.
- `docs/operations/MOTOR_DE_SIRIUS.md`, la arquitectura mínima del motor §7.3 y
  `docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md` quedan enlazados a
  este ADR donde afirman lo contrario.
- Queda **pendiente y sin fecha** la ejecución. Mientras no ocurra, cualquiera
  puede disparar los dos carriles y funcionarán.
- Queda **pendiente** el tratamiento de la puerta del implementador y de la
  etiqueta `auditoria:solicitada`, condicionado al inventario de vías de entrada
  del paso 0 de la recomendación.
- **Entrada en vigor:** la fusión de la Pull Request por el propietario. Ese
  acto aprueba el documento y **no** ejecuta la retirada.

## Alternativas descartadas y por qué

- **Borrar ahora** (opción 1): prohibido por la orden, y destruye trabajo medido
  —el investigador alcanzó 7/7 con fuentes reales en el banco (ADR-098) y el
  auditor encontró defectos reales en su piloto (ADR-010)— antes de saber si el
  traslado rinde.
- **Congelar sin registrar** (opción 2): no deja rastro comprobable y deja el
  carril vivo a merced de una etiqueta.
- **Editar los seis ADR que autorizan los carriles.** Descartada: un ADR registra
  por qué se decidió algo entonces. Retirar lo decidido produce un ADR nuevo que
  lo supera —el patrón de ADR-082 sobre ADR-019—, no una edición del viejo.

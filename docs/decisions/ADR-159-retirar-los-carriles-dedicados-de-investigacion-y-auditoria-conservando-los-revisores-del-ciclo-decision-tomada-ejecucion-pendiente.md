# ADR-159 — Retirar los carriles dedicados de investigación y auditoría, conservando los revisores del ciclo: decisión tomada, ejecución pendiente

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Contexto: la dirección del propietario recogida en
  `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §7.1, punto 2. La nota
  de arranque de este trabajo es la de **ADR-158**, publicada antes del primer
  cambio documental; este ADR se acoge a ella y no abre otra
- Relacionadas: **ADR-010** y **ADR-016** (autorizan el carril del Auditor),
  **ADR-095**, **ADR-097**, **ADR-098** y **ADR-099** (autorizan el carril del
  Investigador), a los que **supera sin editarlos**; ADR-088 (precedente exacto
  de cómo se enmienda la tabla cerrada de clases); ADR-002 (la automatización no
  escribe en `.github/**`); ADR-158 (el reparto de responsabilidades)

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

Se hereda el de ADR-158 —al que este trabajo se acoge— y se le añaden dos
condiciones propias, escritas antes de tocar el registro:

- **(e)** Si al enumerar las piezas apareciera **una sola** compartida entre un
  carril a retirar y un revisor del ciclo, la retirada no se registra como
  «limpia»: se declara esa pieza y su tratamiento, o se para. *Se disparó*: hay
  una, y está en la Decisión, punto 4.
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
4. **La única costura con el ciclo, declarada por el criterio (e):** el workflow
   del implementador declina las activaciones de perfil `investigador` para que
   las atienda `investigar-orden.yml`
   (`.github/workflows/implement-sirius-work.yml:171-180`). No se toca: con el
   carril desactivado no se dispara, y modificarla exige escribir en `.github/**`,
   donde la automatización no puede (ADR-002).
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

1. Dejar de despachar las dos clases y retirar el disparador de cada carril.
2. **Conservar** código, perfiles, prompts, ADR, historial y resultados.
3. No borrar la etiqueta `auditoria:solicitada` ni la puerta del punto 4.

Motivo: es lo más barato de deshacer si el traslado a las sesiones externas no
rinde, y no destruye nada medido. El borrado definitivo, si algún día se quiere,
es una decisión posterior con su propio ADR.

**Nada de esto se ha hecho.** Este apartado es una recomendación, no un registro
de ejecución.

## Comprobación que la sostiene

- **Las piezas de cada función están enumeradas y son disjuntas**, salvo la del
  punto 4: `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §2.3 las lista
  fichero a fichero, comprobadas en el árbol.
- **La costura del punto 4 es la única**: buscando `auditor`/`auditoria` e
  `investigador`/`investigacion` en los workflows del ciclo
  (`review-sirius-work.yml`, `repair-sirius-work.yml`,
  `implement-sirius-work.yml`, `quality.yml`,
  `advance-sirius-after-quality.yml`), los únicos aciertos con efecto son las
  líneas 171-180 del implementador; el resto son comentarios.
- **El árbol contradice cualquier redacción que dé la retirada por ejecutada**:
  `TABLA_ACTIVACION` sigue teniendo las cuatro clases. Por eso el contrato
  operativo marca las filas en vez de borrarlas, y esa marca es la comprobación
  de que la distinción decisión/ejecución no es retórica: se puede leer en el
  documento y contrastar con el código.
- **Ningún fichero fuera de `docs/` se ha modificado** en el commit que registra
  esta decisión.

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

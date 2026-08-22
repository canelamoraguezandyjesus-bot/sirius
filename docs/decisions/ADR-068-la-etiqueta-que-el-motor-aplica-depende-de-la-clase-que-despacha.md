# ADR-068 — La etiqueta que el motor aplica depende de la clase que despacha

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR de esta rama por el propietario — que es, además, el acto que pone en vigor la enmienda v1.9
- Nota de arranque de esta rama: este ADR. Publicado antes del primer commit.

## Contexto y problema

Al preparar el contrato del bloque **C4** (Auditor como perfil del motor) apareció
un bloqueo que el plan no anticipó.

El plan describe C4 así: *«una orden crea el WorkItem de auditoría; el adapter
aplica `auditoria:solicitada`»*, y declara **«Decisión humana previa: ninguna»**.

Pero el contrato operativo v1.8, §12.1, dice:

> El motor **puede** aplicar `sirius:implement-requested` a un WorkItem, con una
> condición que no admite excepción […]

**Nombra esa etiqueta y ninguna otra.** No es un descuido de redacción: el
despachador lo implementa así a propósito, y su docstring lo dice —
*«la etiqueta aplicada es siempre `ETIQUETA_ACTIVACION`: el contrato §12.1 no
autoriza [otra]»* — y rechaza cualquier clase que no sea `programacion`.

El carril del Auditor usa `auditoria:solicitada`, **fuera del espacio
`sirius:*` por decisión de ADR-016**. Así que bajo la v1.8 el motor puede
preparar una auditoría entera y no puede darle la salida — que es exactamente
el cuello de botella que §12.1 vino a eliminar para programación.

### Es la segunda vez que el plan contradice al contrato

La primera fue al diseñar D1a (incidencia #250, hallazgo H-A): el plan §4 exige
«14 días y cero intervenciones manuales» y el contrato §11.2 dice **7 días** y
una condición distinta, declarando además **inalcanzable** la redacción del
plan.

Ahora, la misma familia: el plan da por buena una autorización que el contrato
no concede. **El contrato es la fuente normativa; el plan es una previsión
escrita antes.** Cuando discrepan, gana el contrato, y el plan se corrige — que
es lo que hace esta PR.

## Criterio de parada (escrito ANTES de decidir)

Si resolver esto exigiera **relajar la condición de orden enlazada** de §12.1
—la única que no admite excepción—, se para: eso convertiría al motor en algo
que decide qué trabajo existe, y es justo lo que el límite protege. Si exigiera
**modificar la superficie del Auditor** (`audit-sirius-repository.yml`, el
informe, la etiqueta misma), también se para: ADR-016 la fija y el plan de C4
declara ese carril intocable.

Ninguno de los dos se activó: la enmienda no toca la condición ni el carril.

## Opciones consideradas

1. **Generalizar §12.1 a una tabla cerrada de clase → etiqueta.**
2. Autorizar al motor a aplicar «la etiqueta que declare el WorkItem», sin tabla.
3. No enmendar: el motor crea la incidencia de auditoría y **el propietario**
   aplica `auditoria:solicitada` a mano.

## Decisión

**Opción 1.** Una nueva §12.4 autoriza al motor a aplicar la etiqueta de
activación **que corresponde a la clase que despacha**, tomada de una tabla de
dos filas escrita en el contrato. La condición de §12.1 se mantiene literal.

**Por qué es una generalización y no una autorización nueva:** el argumento de
§12.1 nunca dependió de qué etiqueta era, sino del gesto — *«solo cambia quién
teclea la etiqueta, no quién decide»*. Ese razonamiento es idéntico para una
auditoría que el propietario ha pedido.

**Por qué la tabla y no la opción 2:** «la etiqueta que declare el WorkItem»
convertiría el cuerpo de una incidencia en la fuente de la autorización, y el
cuerpo lo escribe el propio motor. La máquina acabaría concediéndose permisos a
sí misma. Con la tabla, añadir una clase es una enmienda de este contrato — un
acto del propietario, visible y fechado.

**Por qué no la opción 3:** deja al propietario de mensajero justo en el gesto
que el Work Engine existe para quitarle, y por un motivo puramente contable —
que la etiqueta se llama distinto.

## Consecuencias

- C4 pasa a tener una dependencia dura declarada: **no se puede implementar
  antes de que la v1.9 esté fusionada**. El plan se corrige en esta misma PR
  para que nadie lo lea como «ninguna decisión previa».
- La superficie del Auditor sigue intacta: el motor aplica la etiqueta y nada
  más. ADR-016 (se lanza por etiqueta y no escribe nunca) y ADR-010 (los
  hallazgos no se convierten en trabajo por su cuenta) quedan enteros.

## Lo que esto NO hace

- **No implementa C4.** Esta PR es solo la enmienda y la corrección del plan.
  El despachador sigue rechazando toda clase que no sea `programacion`, y eso
  se cambia en C4, no aquí.
- **No relaja la condición de orden enlazada.** Sin orden explícita del
  propietario registrada en la evidencia, el motor sigue sin arrancar nada.
- **No autoriza a §9.1.** El vigilante periódico sigue sin poder aplicar
  ninguna de las dos etiquetas: la autorización es del motor.
- **No garantiza que el plan no vuelva a contradecir al contrato.** Van dos
  veces y las dos las encontró una persona leyendo. Una comprobación que
  detecte la discrepancia sería otro trabajo, y está apuntado como tal.

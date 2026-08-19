# ADR-041 — La autoridad de cada clase de trabajo se fija antes de que exista el primer WorkItem

- Estado: APROBADO
- Fecha: 2026-08-19
- Aprobación: decisión del propietario por interrogatorio (tres preguntas, 19-08-2026); fusión de la PR
- Contexto: bloque E1a del plan del Work Engine (ADR-020), contrato operativo v1.6.1 → v1.7
- Relacionadas: ADR-019 (el motor posee el estado), ADR-020 (construir por verticales), ADR-037 (qué gestos son del propietario)

## Contexto y problema

**A5 es el bloque que crea y activa el primer WorkItem del motor.** Un WorkItem que nazca sin autoridad definida —sin que esté escrito si manda la incidencia de GitHub o el almacén del motor— es un estado ambiguo que no se puede arreglar después sin reescribir historia. Por eso la regla va delante de A5.

El plan (§4) ya traía la tabla de autoridad completa y una propuesta de condición de conmutación. Lo que quedaba abierto era su único parámetro declarado —el umbral— y, como se vio al preguntar, dos cosas más que el plan no había separado.

## Criterio de parada (escrito ANTES de decidir)

Este bloque se decidió con el método de interrogatorio recién incorporado (`docs/implementation/METODO_INTERROGATORIO.md`), cuyo criterio de parada es parte del método y estaba escrito antes de la primera pregunta:

> Para cuando **lo que queda por saber ya no cambia lo que construirías**. Si puedes escribir el plan entero y ninguna respuesta pendiente movería una línea, has terminado de preguntar.

Se pararon las preguntas en la tercera. La cuarta candidata —si alguna clase debía quedar excluida para siempre— se descartó **sin preguntarla**, aplicando la regla de no preguntar lo que no cambia nada: la conmutación es invisible para el propietario (§11.5), así que ninguna respuesta suya habría movido una línea.

## Opciones consideradas

**Quién ejecuta la conmutación:**

1. El propietario, con una orden explícita por clase, como el merge.
2. Automático al cumplirse una condición medible.

**Condición de disparo:**

1. Catorce días sin ninguna intervención manual (propuesta del plan).
2. Siete días sin correcciones manuales **del estado**.

**Ante una divergencia posterior:**

1. Revertir a la primera.
2. Aguantar dos divergencias seguidas, avisando en la primera.

## Decisión

**Automático, siete días, revertir a la primera.** Redacción operativa completa en el contrato §11.

La tabla de autoridad se adopta tal cual venía del plan, sin cambios.

## Comprobación que la sostiene

### La condición del plan era inalcanzable, no exigente

El propietario objetó que catorce días sin ninguna intervención manual «es imposible, siempre nos pasa algo». La objeción se comprobó contra el registro real de una sola sesión de trabajo (18-19 de agosto):

| Suceso | Hora | ¿Hizo discrepar motor e incidencia? |
| --- | --- | --- |
| Codex agotó los 1200 s sin contestar (#193) | 20:57 | No |
| `apt-get` colgado 20 min; Quality cancelada (#202) | 04:54 | No |
| Parada por convergencia sin progreso (#202) | 04:10 | No |

Tres averías operativas en unas catorce horas, y **ninguna de las tres es una divergencia**. De ahí salen las dos correcciones del ADR:

1. El umbral baja a **siete días**, por el ritmo real del repositorio.
2. Y sobre todo, **cambia qué se cuenta**: solo las correcciones manuales del estado motivadas por que las dos representaciones dijeran cosas distintas. Con la definición anterior el contador se habría reiniciado tres veces en catorce horas y la conmutación no habría llegado nunca — una condición inalcanzable no protege, impide.

### Por qué la firma del propietario no añadía seguridad

La propuesta inicial de la sesión era que el propietario firmara cada conmutación, por analogía con el merge (ADR-037). El propietario la rechazó con dos argumentos, y ambos se sostienen:

- Los revisores comprueban que el trabajo esté bien hecho; no pueden comprobar que sea lo que él quería. **Pero esta decisión no es de gusto: es medible.** La condición de §11.2 se cumple o no se cumple, y no hay juicio que emitir.
- Él no puede evaluar la medición por su cuenta, así que su firma sería un refrendo del criterio de la sesión. Eso es ceremonia, no control.

La sesión reconoció que estaba resolviendo un riesgo real con la herramienta equivocada: la respuesta al peligro no es una firma, es que **el cambio se deshaga solo**. De ahí §11.4, que no estaba en la propuesta inicial y que es lo que hace defendible el automatismo.

### Verificación documental

- `uv run python scripts/siguiente_adr.py --solo-numero` — número asignado por el guion, no elegido a ojo.
- `tests/automation/test_registro_de_decisiones.py` — en verde.
- Las cuatro validaciones obligatorias, en verde.

## Consecuencias

- Ninguna clase de trabajo puede crear un WorkItem sin autoridad asignada, y la tabla no tiene huecos.
- §2 del contrato queda intacta mientras una clase no haya conmutado.
- El propietario no adquiere ninguna obligación nueva. Su único gesto sigue siendo el merge.
- La conmutación es invisible desde fuera: incidencias, etiquetas y notificaciones siguen igual.

## Alternativas descartadas y por qué

**Firma del propietario por clase.** Descartada por los argumentos de arriba: sobre una condición medible, una firma no aporta control, aporta espera. Se conserva escrito por si la condición dejara alguna vez de ser medible.

**Catorce días sin intervenciones de ningún tipo.** Descartada con datos: se habría reiniciado tres veces en catorce horas por averías que no son divergencias.

**Aguantar dos divergencias antes de revertir.** Descartada porque la asimetría es clara: revertir no cuesta nada —ambas representaciones conservan su historial íntegro— y seguir siendo autoridad tras demostrarse poco fiable sí cuesta. El propietario coincidió.

**Excluir alguna clase de la conmutación.** No se llegó a preguntar, y se registra para que conste: la conmutación no cambia nada de lo que el propietario ve, así que la pregunta no habría cambiado el resultado. Si algún día una clase debiera quedar fuera, esta sección se enmienda.

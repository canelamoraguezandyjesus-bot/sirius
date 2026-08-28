# ADR-099 — La clase investigacion entra en la tabla de activación, y su ejecutor es el investigador medido

- Estado: PROPUESTO
- Fecha: 2026-08-28
- Aprobación: la fusión de la PR por el propietario
- Contexto: B1. El propietario pidió que Sirius haga «investigaciones como las
  de ChatGPT y Claude», y S2 acaba de cerrar con el número que lo desbloquea
- Relacionadas: ADR-088 (la fila DOCUMENTACION, el precedente exacto), ADR-098
  (la configuración elegida), ADR-043 (el intérprete v0 que ya clasifica
  «investiga»), contrato §12.4 (la tabla cerrada) y §8 (fusionar es del
  propietario)

## Contexto y problema

Desde ADR-043 el intérprete clasifica «investiga…» como clase `investigacion`.
Desde hoy existe un ejecutor MEDIDO para esa clase: la configuración de ADR-098
dio 7/7 con fuentes reales sobre el banco (S2, run 33141864710). Y sin embargo
una orden de investigación muere en el despachador: la clase no está en
`TABLA_ACTIVACION`, así que `dispatch_work_item` la rechaza con
`ClaseNoDespachableError`.

La tabla es cerrada a propósito: añadir una fila es una enmienda del contrato,
no una decisión de implementación. Este ADR es esa enmienda, con el mismo
formato y criterio que ADR-088 usó para DOCUMENTACION.

## Decisión

1. **`INVESTIGACION` entra en `TABLA_ACTIVACION` con las MISMAS etiquetas** que
   programacion y documentacion (`sirius:planned` inicial,
   `sirius:implement-requested` de activación). Ningún vocabulario nuevo.
2. **Su perfil es `investigador@1`** (`TABLA_PERFILES`), y el perfil es la
   llave del reparto: la puerta del workflow del implementador excluye
   `investigador` ANTES de consumir el evento, y `investigar-orden.yml` exige
   ese perfil y ningún otro. Ninguna incidencia puede tener dos ejecutores, y
   ninguna se queda sin dueño.
3. **El ejecutor NO es un agente de Claude**: es el investigador medido —el
   entorno del banco (python 3.12, gpt-researcher 0.15.1 con `research_report`,
   NVIDIA + Tavily), montado con los mismos pines—. Corre la pregunta del
   `## Objetivo`, y su entregable es un documento en `docs/investigaciones/`
   CON cabecera de caducidad, entregado por PR.
4. **El protocolo con el ciclo es el del implementador, sin marcador nuevo**:
   veredicto provisional `FAILED_SAFELY` antes de tocar nada, definitivo al
   terminar, comentario literal `PR abierta: <URL>`, y cierre por
   `sirius_apply_verdict.sh` con el rol `implementer`. La revisión la hace
   `revisor-documental`: el entregable es un documento.
5. **Sin fuentes no se publica**: un informe con cero fuentes es el modelo
   recitando, y el ejecutor lo convierte en `FAILED_SAFELY` en vez de abrir una
   PR con él. Es la regla `fuentes > 0` del banco, aplicada a las órdenes.

## Lo que esta decisión NO cambia

- **Fusionar sigue siendo un gesto del propietario** (§8): el informe llega
  como PR y nadie la fusiona sola.
- La clase MIXTA sigue inalcanzable (ADR-079) y el descomponedor sigue
  aplazado (ADR-089).
- El banco de medición no cambia: este ADR consume su resultado, no lo toca.
- Las claves son las que ya existen (NVIDIA obligatoria, Tavily opcional);
  ninguna de OpenAI ni Anthropic.

## Alternativas descartadas

**Que el agente implementador ejecute la investigación.** Costaría cuota de
Claude para niñerar un guion de cinco minutos, mezclaría dos ejecutores en un
workflow y correría el investigador FUERA del entorno medido. La clase ya tiene
un ejecutor con número; el agente no lo mejora, lo encarece.

**Un vocabulario de etiquetas propio para investigación.** ADR-088 ya rechazó
esa vía para documentacion con el criterio que sigue valiendo: cada etiqueta
nueva es estado nuevo que TODOS los vigilantes tendrían que aprender.

**Esperar al examen «lado a lado contra ChatGPT» antes de cablear.** Ese examen
NECESITA esta costura: sin B1 no hay forma de darle a Sirius la misma pregunta
profunda que a ChatGPT y comparar informes. El examen es lo siguiente, no lo
previo.

## Cómo se comprueba

- `tests/engine/test_dispatcher.py::test_b1_investigacion_recibe_las_mismas_etiquetas_que_programacion`
  (vista FALLAR con `ClaseNoDespachableError` antes de la fila) y
  `tests/engine/test_dispatch_cli.py::test_investiga_despacha_...` (vista
  FALLAR antes del perfil).
- La tabla sigue cerrada: `test_clase_fuera_de_la_tabla_no_se_despacha` pasa a
  vigilar con `CONSULTA_LARGA`, y la reproducción de H-17 pasa a laboratorio
  porque el intérprete v0 ya no produce ninguna clase no despachable con texto
  real —ese hecho queda escrito en su docstring—.
- La costura entre workflows: `tests/automation/test_investigar_orden_workflow.py`
  (el reparto por perfil, la exclusión ANTES de consumir, el veredicto con
  `always()`, las claves, el tope ≤ 85).
- El ejecutor: `tests/automation/test_atender_orden_de_investigacion.py`
  (ejecuta `main` real con hijos fingidos: provisional antes de nada, READY
  con documento que pasa el guardián de caducidad, FAILED_SAFELY sin silencio).
- La prueba DEFINITIVA es en el servidor: una orden real «investiga…» dando la
  vuelta entera. B1 no se cierra en el registro hasta verla, igual que C2 no se
  cerró hasta probar #331.

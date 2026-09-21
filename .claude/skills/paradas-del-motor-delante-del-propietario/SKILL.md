---
name: paradas-del-motor-delante-del-propietario
description: >-
  Cómo una sesión encuentra los trabajos del motor que llevan días esperando una
  decisión del propietario y se los pone delante de una vez, con la orden
  copiable: dónde vive el diario (la rama `estado-del-motor`), qué estados
  esperan a una persona, qué resuelve `sirius-decidir` y qué resuelve GitHub, y
  cómo se le presenta para que conteste con un sí o un no. Cárgala al abrir una
  sesión con mandos de GitHub, al escribir el parte de la mañana, y siempre que
  el diario o el tablero de una incidencia digan «esperando decisión» o
  `NEEDS_DECISION`.
---

# Las paradas del motor, delante del propietario

**Regla única: una parada que espera al propietario no se resuelve sola ni se
decide por él. Se le pone delante, con la orden lista, en cada parte, hasta que
conteste.**

## Por qué existe, con fechas

- **13-09-2026, ADR-189**: el diario de `estado-del-motor` tenía cuatro paradas
  en `NEEDS_DECISION`, la más antigua de **diez días**, y ninguna tenía salida:
  la puerta había parado el trabajo antes de crear la incidencia y nada podía
  reanudarlo. De ahí `sirius-decidir`.
- **ADR-198**: una pregunta al propietario estuvo **veinte días** sin que nadie
  la volviera a poner delante. Es la familia
  `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante`.
- **19-09-2026** (ficha PROC-003 de
  `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`): las cuatro paradas
  seguían sin salida, dos desde el 03-09. Y **20 de 91 encargos** (22 %) se
  re-despacharon para desatascarlos (PROC-005).

## Los pasos

1. **Dónde mirar, y cuál de los dos diarios es.** Hay dos y no se mezclan
   (`docs/operations/MOTOR_DE_SIRIUS.md`, §3; `diario_por_defecto` en
   `src/sirius_engine/cli.py`): el de los workflows vive en la rama
   **`estado-del-motor`**, nunca en `main` —`diario.jsonl` y
   `diario-supervision.jsonl`; solo la escribe el workflow, que la trae a un
   árbol aparte y la devuelve con un push—, y el de su consola vive en su
   directorio de datos de Windows y es estado suyo. Desde una sesión con
   mandos de GitHub el primero se lee de esa rama sin traerla al árbol de
   trabajo; si la rama no existe, el motor no ha anotado nada todavía. El
   estado de un trabajo lo manda su diario (`AGENTS.md`, «El estado de un
   trabajo del motor»).
2. **Qué espera a una persona.** Un trabajo en `NEEDS_DECISION` **sin
   incidencia detrás** —la puerta de sensibilidad paró antes de crearla— solo
   sale con `sirius-decidir` (ADR-189). Una incidencia parada con su marcador
   de decisión en el tablero (ADR-175, ADR-157) se resuelve en GitHub y la
   aplica el reflector; con incidencia detrás, `sirius-decidir` se niega y lo
   dice.
3. **La orden no se fabrica, y solo una salida la imprime entera.** Cuando
   `sirius-despachar` para un trabajo en la puerta, imprime la orden de salida
   exacta de ese trabajo, y esa orden lleva lo que una plantilla pierde:
   `--repo` y `--bloque` cuando la orden original no usó los valores por
   defecto —nadie los persiste, y sin ellos `--continuar` crearía la
   incidencia en el repositorio y con el encargo equivocados— y **sin
   `--continuar`** cuando esa salida está vetada, como en la quinta causa de
   ADR-188, donde solo caben `--terminar` o la sesión interactiva. Lo fijan
   las pruebas de `tests/engine/test_dispatch_cli.py`. Esa es la única orden
   que se copia: la de la parada, en la consola donde se despachó o, si lo
   despachó el workflow, en el registro de ese run
   (`.github/workflows/despachar-orden.yml`). La lista de `sirius-motor`
   (`/trabajos`) **no** la conserva: imprime una plantilla con `<work_id>`,
   sin `--repo` ni `--bloque` y ofreciendo siempre `--continuar`
   (`_con_decision_pendiente` en `src/sirius_engine/cli.py`; su prueba solo
   fija `--diario` y `--ejecutar`), así que sirve para saber que hay una
   decisión pendiente y en qué diario, no para copiar de ella. Sin la orden
   de la parada no se le da `--continuar`: se busca esa orden en el registro
   del run antes de nada, y mientras tanto solo cabe `--terminar` si procede,
   o el ensayo de `sirius-decidir` sin `--ejecutar` para que las guardas
   digan qué salidas existen. Nunca un `--continuar` escrito de memoria.
4. **Cómo se le presenta, y por qué canal.** En el parte —también desde el
   móvil— va la decisión y nada más: qué trabajo, desde cuándo, qué pasa si
   continúa y qué pasa si termina, para que conteste sí o no. La orden para
   su consola **no** va en el parte: se acumula con lo demás del ordenador y
   se le da junta cuando diga que está delante (`AGENTS.md`, regla 13; skill
   `comandos-para-su-ordenador`). La decisión se repite en cada parte mientras
   no conteste: la pregunta que no se vuelve a poner delante es la que dura
   veinte días.
5. **Dónde aterriza su decisión.** Si la parada está en el diario de su
   consola, la orden copiada la resuelve ahí. Si está en el diario de
   `estado-del-motor`, hoy **no hay vía segura** de escribirle la decisión de
   vuelta: `sirius-decidir` solo escribe en el fichero que recibe, ningún
   workflow lo invoca (ADR-189) y esa rama solo la escribe el workflow. No se
   ejecuta sobre una copia ni se empuja a mano a la rama. Su decisión se deja
   escrita —un ADR, o el registro de ideas si es «más adelante»— y la falta de
   vía está apuntada como idea aparcada (I-009), para que el día que exista no
   haya que volver a pedirle la decisión.
6. **Lo que no se hace**: decidir por él (es cambio de producto, ADR-204);
   ejecutar `sirius-decidir` desde la nube; re-despachar la misma orden para
   «desatascar» sin que él lo haya decidido.

## Qué NO hace esta skill

- **No opera el ciclo**: darle una orden o un turno al motor está en
  `docs/operations/MOTOR_DE_SIRIUS.md`, y las reglas en el contrato operativo.
- **No escribe en `estado-del-motor`**: esa rama solo la escribe el workflow,
  y la vía para que una decisión suya llegue al diario de los workflows no
  existe todavía (I-009).
- **No sustituye al supervisor ni a la red de seguridad**: esos cierran lo
  perdido y relanzan; esto es solo la parte humana, la que nadie vuelve a poner
  delante.
- **No ve lo que el diario no tiene**: si el motor no anotó la parada, aquí no
  aparece.

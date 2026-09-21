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

1. **Dónde mirar.** El diario del motor vive en la rama **`estado-del-motor`**,
   nunca en `main`: `diario.jsonl` (encargos, ejecuciones y transiciones) y
   `diario-supervision.jsonl` (`docs/operations/MOTOR_DE_SIRIUS.md`, §3). Desde
   una sesión con mandos de GitHub se lee de esa rama sin traerla al árbol de
   trabajo. El estado de un trabajo lo manda su diario (`AGENTS.md`, «El
   estado de un trabajo del motor»). Si la rama no existe, el motor no ha
   anotado nada todavía; no es un fallo.
2. **Qué espera a una persona.** Un trabajo en `NEEDS_DECISION` **sin
   incidencia detrás** (la puerta de sensibilidad paró antes de crearla) solo
   sale con `sirius-decidir` (ADR-189). Una incidencia parada con su marcador
   de decisión en el tablero (ADR-175, ADR-157) se resuelve en GitHub y la
   aplica el reflector. Lo que ya tiene incidencia no se toca con
   `sirius-decidir`: el comando se niega y lo dice.
3. **Cómo se le presenta.** Un solo mensaje, una línea por parada: qué trabajo,
   desde cuándo, qué pasa si continúa y qué pasa si termina; y la orden
   copiable para su consola, con la skill `comandos-para-su-ordenador`:
   `sirius-decidir <work_id> --diario <ruta> --ejecutar --continuar`, o
   `--terminar`. Sin `--ejecutar` solo ensaya, por diseño; sin `--diario` busca
   en el diario que resuelva por su cuenta, que no tiene por qué ser el suyo.
   `sirius-motor` imprime esa misma orden cuando lista trabajos con decisión
   pendiente.
4. **Cuándo.** Al abrir sesión y en el parte de la mañana (`AGENTS.md`, regla
   12, bloque «te toca a ti»), y se repite en cada parte mientras siga sin
   respuesta: la pregunta que no se vuelve a poner delante es la que dura
   veinte días.
5. **Lo que no se hace**: decidir por él (es cambio de producto, ADR-204);
   ejecutar `sirius-decidir` desde la nube sobre su diario, que es su consola y
   su estado; re-despachar la misma orden para «desatascar» sin que él lo
   haya decidido.

## Qué NO hace esta skill

- **No opera el ciclo**: darle una orden o un turno al motor está en
  `docs/operations/MOTOR_DE_SIRIUS.md`, y las reglas en el contrato operativo.
- **No sustituye al supervisor ni a la red de seguridad**: esos cierran lo
  perdido y relanzan; esto es solo la parte humana, la que nadie vuelve a poner
  delante.
- **No ve lo que el diario no tiene**: si el motor no anotó la parada, aquí no
  aparece.

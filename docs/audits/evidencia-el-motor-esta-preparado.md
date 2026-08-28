# Evidencia — El motor está preparado para recibir órdenes reales

Fecha: 2026-08-28. Rama `el-motor-esta-preparado`. Nota de arranque:
`arranque-el-motor-esta-preparado.md`. Lo pidió el propietario antes de
empezar la memoria (Sirius 0.2): comprobar que las órdenes las ejecuta el
motor por su ciclo, no la sesión a mano.

## Veredicto: PREPARADO, con tres límites dichos

## Pregunta 1 — ¿Puede entrar una orden desde la sesión? SÍ, y está probado

`despachar-orden.yml` (workflow_dispatch con el texto de la orden y la marca
`ejecutar`): **10 ejecuciones reales, 10 en verde**, disparadas desde
sesiones interactivas con la identidad del bot. La número 9 es el despacho
real de B1 («Investiga cuáles son los límites de la capa gratuita de
Tavily») que parió la incidencia #386. El despacho corre `sirius-despachar`
dentro de Actions con `SIRIUS_BOT_TOKEN` y `gh` -lo que la sesión no tiene-,
anota el diario en la rama `estado-del-motor` y comparte grupo de
concurrencia con el motor para no pisarse (guardián
`test_serializacion_del_motor.py`). Sin marcar `ejecutar`, ensaya.

## Pregunta 2 — ¿Cada clase llega a un ejecutor que existe? SÍ, las cuatro

| Orden empieza por | Clase | Ejecutor | Prompt/perfil |
|---|---|---|---|
| «Implementa…», «Corrige…» | programacion | `implement-sirius-work.yml` | implementer@1, fila verificada en el manifiesto (H-28) |
| «Documenta…», «Redacta…», «Escribe…» | documentacion | `implement-sirius-work.yml` | documentalista@1, fila verificada |
| «Investiga…» (± «a fondo») | investigacion | `investigar-orden.yml` (la puerta del implementador lo excluye ANTES de consumir el evento) | investigador@1, ADR-098/099 |
| «Audita…» | auditoria | `audit-sirius-repository.yml` por `auditoria:solicitada` (nace sin etiquetas `sirius:*` a propósito) | runbook del Auditor v0 |

La sospecha del arranque -que `auditoria` moría en rojo en el resolver de
prompts- quedó **REFUTADA**: nunca pasa por ese resolver; su fila de la
TABLA_ACTIVACION la manda a su propio workflow, estrenado de verdad en la
#167 (informe completo, hallazgo P1 corregido con `--ignored=matching`).
El intérprete clasifica por el PRIMER verbo (orden inequívoca), así que una
orden larga no cae a consulta; la sensibilidad se comprueba antes que todo
(H-19, decisión #324.1).

## Pregunta 3 — ¿El ciclo tras el despacho está probado con ejecuciones reales? SÍ

- C2: el despachador creó él mismo la #333 y anotó WI-20260825-144242 (#334).
- C3: clase documentacion, ciclo completo con revisor documental.
- B1: la vuelta ENTERA sin una mano — despacho → #386 (investigador@1) →
  `investigar-orden.yml` → informe con 23 fuentes → PR #387 → revisión →
  fusión (#388, «no se cierra un bloque por tener el código fusionado, se
  cierra por verlo funcionar»).
- El resto del ciclo (Quality por PAT, revisión dual opcional, corrector,
  reanudación, fusión por orden «fusiona» con fail-closed de H-31) lleva ~20
  incidencias reales encima.

## Pregunta 4 — Los límites, sin adornos

1. **«Audita X» ejecuta HOY la auditoría genérica del repositorio** (el
   runbook del Auditor v0), no una auditoría acotada a X: el texto de la
   orden no llega al prompt del auditor. Límite declarado, no defecto: si
   hace falta auditoría por encargo acotado, es un bloque a ordenar.
2. **La racha de los siete días registra NO_COMPARABLE** para todas las
   clases hasta que exista la pieza (C) de la ex-#376 (ADR-101): no bloquea
   ninguna orden; es el instrumento diciendo la verdad.
3. **Una frase falsa encontrada**: el docstring de `seven_day_streak_cli.py`
   dice que `motor-sirius.yml` «arranca solo a mano, sin horario» — falso
   desde #343 (25-08): el motor corre a `32 */6 * * *` y sus turnos 9-15
   reales son `schedule` y en verde (el último, 28-08 11:35 UTC). Misma
   familia que H-21 (una frase que desinforma). Arreglo de una línea,
   pendiente de la próxima rama de código. Esta frase es además la causa de
   que el parte de hoy dijera al propietario que la cadencia estaba
   pendiente: estaba encendida desde el día 25.

## Consecuencia operativa

La #296 (D2) quedó entregada por #343 («D2 queda cerrado: 15 de 19
bloques»), con cadencia real funcionando: se cierra citándolo. La sesión
queda como lo que el contrato quiere que sea: quien recibe la orden del
propietario, la despacha por `despachar-orden.yml`, y vigila — sin hacer el
trabajo a mano.

## Criterio de parada

(a) no se activó: la entrada existe y está probada. (b) ninguna clave nueva.
(c) una sola ronda. (d) respetado: esta comprobación no arregló nada — el
límite 3 queda listado, no corregido.

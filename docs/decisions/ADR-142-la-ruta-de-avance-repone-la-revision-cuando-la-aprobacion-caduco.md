# ADR-142 — La ruta de avance repone la revisión cuando la aprobación caducó

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el
  propietario — autorizada explícitamente esta noche («fusiónalas tú»),
  la ejecuto yo con Quality y mi revisión en verde. Cauce ADR-002,
  opción 2: toca `.github/workflows/advance-sirius-after-quality.yml`,
  hecho en sesión interactiva.

## Contexto y problema

Deuda 10 de la bitácora, el agujero más repetido del motor: cuando dos
encargos van en paralelo y el primero fusiona, el segundo queda por
detrás de `main`; el update-branch mueve su head y la aprobación
registrada caduca. El motor no tenía NINGÚN camino de vuelta: la ruta de
avance solo aceptaba verdes en `ci-pending` y `failed-safely` (H-34), y
la incidencia se quedaba clavada en `ready-for-merge` hasta cirugía
manual (etiqueta a `ci-pending` + relanzar el run verde) — dos veces el
04-09 (entradas 25 y 29 de la bitácora), y el mismo día por partida
doble en G3 tras las fusiones de G2 y ADR-135.

## Criterio de parada (escrito ANTES de decidir)

- El origen nuevo hereda ÍNTEGRA la doctrina de H-34: solo verdes (un
  rojo sobre `ready-for-merge` sería degradar una aprobación por un
  resultado, es decir, tomar una decisión).
- Nunca destruir una aprobación vigente: si el verde es del MISMO head
  ya aprobado, no se toca nada. Sin este guard, el re-run de Quality
  sobre un head aprobado (mi propia receta manual lo provoca) forzaría
  una ronda entera de revisión gratuita.
- Solo el workflow de avance: si hiciera falta tocar el guard de fusión
  o el reconciliador, parar.

## Opciones consideradas

1. Tercer origen en la ruta de avance (`ready-for-merge`, solo verdes,
   con guard de aprobación vigente).
2. Que el guard de fusión, al rebotar por «commits posteriores a la
   aprobación», reponga él mismo `review-requested`.
3. Seguir con la cirugía manual.

## Decisión

**Opción 1.** Cuatro toques en
`.github/workflows/advance-sirius-after-quality.yml`, calcando el patrón
H-34 existente:

- `"sirius:ready-for-merge"` entra en el bucle de orígenes de
  candidatas, con su puerta de solo-verdes idéntica a la de
  `failed-safely`.
- Guard de aprobación vigente: elegida la candidata única con ese
  origen, si los comentarios contienen
  `sirius-verdict:reviewer:approved:<head-verde>`, se sale sin tocar
  nada (lectura propagada como reintentable, igual que las demás).
- La transición verde retira las TRES etiquetas-fuente por CSV
  (`ci-pending,failed-safely,ready-for-merge`), dentro de la
  transición verificada.
- La parada por ambigüedad sabe retirar el origen nuevo.

Por qué no la 2: el guard de fusión rebota en el momento del `fusiona`,
ANTES de que exista un verde del head nuevo — repondría la revisión
sobre un head sin Quality, invirtiendo el orden del ciclo. El verde es
el evento correcto, y su dueño es la ruta de avance.

## Comprobación que la sostiene

- Guardián textual nuevo,
  `tests/automation/test_ruta_de_avance_origenes.py` (mismo patrón que
  `test_recon_stuck_007`): fija los tres orígenes, las dos puertas de
  solo-verdes, la retirada CSV triple y el guard de aprobación vigente.
  Visto fallar ANTES del cambio: «4 failed» contra el workflow de dos
  orígenes; 4/4 después. Esa es la mutación natural (quitar cualquiera
  de las cuatro piezas lo devuelve a rojo).
- El YAML validado con parser tras la edición.
- La secuencia exacta que este origen automatiza es la que el 04-09
  funcionó dos veces A MANO (entradas 25 y 29): etiqueta +
  QUALITY_SUCCESS del head nuevo + `review-requested` — aquí producida
  por la misma `trigger_transition` verificada que ya usan los otros
  dos orígenes.
- Validaciones obligatorias completas, códigos verificados, en la PR.
- Lo no verificable antes de fusionar (un workflow no corre desde una
  rama): la primera reposición real. Criterio: el próximo encargo
  paralelo cuyo `fusiona` rebote debe volver solo a revisión con el
  verde siguiente, sin mi mano; se registrará en la bitácora.

## Consecuencias

- El «peaje del segundo paralelo» (entrada 25) se paga solo en tiempo de
  ronda, ya sin intervención humana; la receta manual queda obsoleta.
- Un re-run de Quality sobre un head ya aprobado deja de ser peligroso
  para la aprobación (guard), lo que también protege la receta de
  recuperación de paradas (que relanza runs verdes).
- La deuda 10 queda saldada; con la 12 (ADR-141), las dos cirugías
  manuales recurrentes del 04-09 desaparecen del manual del operador.

## Alternativas descartadas y por qué

- **Reponer desde el guard de fusión (opción 2):** invierte el orden del
  ciclo (revisión antes que Quality del head nuevo), arriba.
- **Aceptar también rojos sobre `ready-for-merge`:** decidir, no
  registrar — fuera de la doctrina H-34 que este ADR extiende.
- **Aceptar `repairing` con FIXED del mismo head (la «opción completa»
  del informe de la mina):** sigue siendo deseable contra la carrera del
  verde (ADR-139 la dejó como única vía), pero es OTRA semántica (casar
  veredicto de corrector con head) y merece su propio cambio con su
  propia evidencia; mezclarla aquí engordaría la superficie de un toque
  ya delicado.

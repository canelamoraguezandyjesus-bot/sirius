# Nota de arranque — Que una revisión sobreviva a ponerse al día con `main`

Fecha: 2026-09-13. ANTES del primer cambio (ADR-001). Lo ordena el propietario:
terminar las mejoras del motor antes de volver a la memoria. Es la parte 2 de
la incidencia #608, la única de las tres que su propio análisis declara
despachable «sin preguntar nada».

## El coste, en palabras del propietario

«Cada vez que fusiono, se mueve `main`, y entonces tengo que actualizar la otra,
que pase por Quality y que tenga que revisar otra vez. O sea, otra ronda más
solo por fusionar una cosa.»

Con N PR abiertas, fusionar una obliga a reconciliar N−1, y cada reconciliación
cuesta tres cosas: traer `main`, otra vuelta de Quality (~10 min) y **otra ronda
de revisión**. La tercera es la cara.

## Por qué ocurre (leído, no supuesto)

`advance-sirius-after-quality.yml` ya trata el caso hermano (ADR-142, líneas
120-125 y 228-243): cuando Quality vuelve a salir verde sobre un head **ya
aprobado** —un re-run—, la aprobación registrada sigue valiendo y no se repone
`sirius:review-requested`. Pero la condición exige que el head sea EXACTAMENTE
el aprobado, así que en cuanto `update-branch` mueve el head para traer `main`,
la aprobación deja de cubrirlo y el Quality del head nuevo abre ronda de
revisión, aunque el trabajo de la rama no haya cambiado ni una línea.

## Lo que se decide construir

Extender esa condición de «mismo head» a «**mismo trabajo**»: la aprobación
registrada sigue valiendo si el diff propio de la rama —`merge-base(base, head)`
contra `head`— es idéntico en el head aprobado y en el vigente. Si el push
cambió el trabajo, aunque sea una línea, la ronda de revisión se abre como hoy.

## Las preguntas

1. ¿Se ve FALLAR primero? Un caso que reproduzca el head movido solo por traer
   `main` y que hoy reponga `review-requested`, y que tras el arreglo
   transicione a `ready-for-merge` sin ronda nueva.
2. ¿Sigue siendo imposible aprobar trabajo no revisado? Un push que cambie el
   diff propio —una línea basta— tiene que abrir ronda igual que hoy. Es la
   pregunta que decide si esto es una mejora o un agujero.
3. ¿Qué pasa si el diff no se puede calcular (un fetch caído, un head
   inalcanzable)? Fail-closed: si no se puede afirmar que el trabajo es el
   mismo, se abre ronda, como hoy.
4. ¿El guardián nuevo mira el código del workflow o su comentario? Solo líneas
   de código (la familia vacua ha mordido cuatro veces en este repositorio).

## Criterio de parada

- (a) Si para saber cuál fue el head aprobado hiciera falta un dato que la
  incidencia no guarda, PARAR y decirlo en vez de inventar un registro nuevo.
- (b) Si el arreglo exigiera tocar la puerta del revisor
  (`review-sirius-work.yml`) además de esta, PARAR y traer las dos delante: son
  dos guardas distintas y mezclarlas es lo que las vuelve incomprensibles.
- (c) Nada de ampliar el alcance de la credencial del motor (ADR-002); este
  cambio lo hace la sesión interactiva, que es lo que ese ADR prescribe.
- (d) Dos rondas con defectos de la misma familia → parar y nombrar la raíz.

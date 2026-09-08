# ADR-158 — Cada evento de etiqueta tiene su propia ranura de notificación

- Estado: PROPUESTO
- Fecha: 2026-09-07
- Aprobación: decisión del propietario registrada en #545 el 07-09-2026 a las
  22:22 y 22:36 UTC («el canal se cierra en ficha propia del operador: grupo de
  concurrencia por evento, conservando la idempotencia del reintento del mismo
  run, y el §7 acotado a lo que la cola garantiza») y la fusión de esta PR
  (toca `.github/**`: ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-158-cada-evento-su-ranura`, publicada antes del primer cambio, con
las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

ADR-157 (07-09-2026, `07a51b1`) hizo que el marcador de notificación llevara el
run del evento, para que dos paradas distintas del mismo estado sobre el mismo
head dejaran cada una su rastro. La corrección era necesaria —era la raíz de
cinco rondas de #545— pero **está incompleta**, y lo demostró Codex revisando
#546 a las 22:17 UTC (CODEX-001, P1):

```
concurrency:
  group: notify-sirius-${{ github.event.issue.number }}-${{ github.event.label.name }}
  cancel-in-progress: false
```

El grupo depende solo de incidencia y etiqueta. GitHub Actions conserva **como
máximo una ejecución en espera por grupo**: cuando llega una tercera aplicación
de la misma etiqueta mientras la primera se ejecuta, la segunda —que está
pendiente— se descarta, incluso con `cancel-in-progress: false`. Esa ejecución
descartada nunca publica su comentario, así que **el suceso no deja marcador**:
exactamente el agujero que ADR-157 vino a cerrar, por otra puerta.

Con eso, la frase que la PR #563 escribió en el §7 del contrato operativo —«una
sola vez por EVENTO de etiqueta»— promete más de lo que el canal garantiza, y
el motor vuelve a poder leer un historial con menos paradas que sucesos.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en la cola: dos eventos distintos comparten una
   ranura pendiente que es descartable. El arreglo va al mismo sitio, el grupo
   de concurrencia del notificador, que pasa a incluir el run del evento: cada
   evento tiene su propia ranura y ninguno desplaza a otro. La idempotencia del
   reintento se conserva porque el identificador del run no cambia al
   reintentar, y el marcador —que ya lleva ese run desde ADR-157— sigue
   deduplicando. Se observa en el historial de una incidencia que reciba tres
   aplicaciones seguidas de la misma etiqueta: hoy pueden quedar dos avisos,
   después quedarán tres.
2. **¿Qué NO garantiza esto?** No garantiza el orden de publicación: al no
   serializar, dos avisos de la misma etiqueta pueden publicarse en cualquier
   orden. El motor no depende de ese orden —desde ADR-147 lo que ordena es la
   posición del veredicto, no la del aviso—, y el marcador de cada uno lleva su
   run. Tampoco convierte la notificación en primaria: sigue siendo secundaria
   y sigue terminando con éxito ante cualquier fallo de lectura o publicación.
   Y no recupera los historiales ya publicados con huecos.
3. **Criterio de parada (decidido antes de ver ningún resultado).** El guardián
   nuevo ve FALLAR el workflow de `main` (su grupo no depende del run) y pasa
   con el cambio; los guardianes existentes del notificador siguen verdes; la
   cadena completa termina en 0. En vivo: una incidencia que reciba tres
   aplicaciones seguidas de la misma etiqueta deja tres avisos. Si tras esta
   fusión se vuelve a observar un suceso sin su marcador, este ADR queda
   desmentido y el camino siguiente es sacar la notificación de la cola de
   Actions, no afinar el grupo.
4. **¿Qué hace esto imposible, en vez de improbable?** Que el propio mecanismo
   que serializa los avisos borre uno. La serialización por etiqueta existía
   para proteger una idempotencia por `(etiqueta, head)` que ADR-157 ya
   sustituyó por otra por run: al no quedar nada que proteger, la cola deja de
   ser un sitio donde se pierden sucesos.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **El grupo de concurrencia incluye el run del evento** (elegida). Una línea;
   cada evento su ranura; la idempotencia del reintento intacta.
2. **Quitar del todo la concurrencia.** Equivalente en efecto —cada run es
   independiente— pero pierde el candado que evita que dos reintentos del MISMO
   run corran a la vez.
3. **Serializar por incidencia y encolar sin descarte.** Actions no ofrece una
   cola sin descarte: es justamente lo que falta.
4. **Publicar el aviso desde el propio rol** en vez de con un workflow aparte.
   Haría primaria una notificación que el contrato quiere secundaria.

## Decisión

- `.github/workflows/notify-sirius-state.yml`: el grupo pasa a
  `notify-sirius-<incidencia>-<etiqueta>-<run>`, con `cancel-in-progress: false`
  intacto. Nada más cambia: mismos textos, mismo marcador, misma tolerancia a
  fallos.
- `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` §7: la garantía «una
  sola vez por evento» pasa a estar sostenida por la cola, y se dice por qué.
- Guardián: el grupo de concurrencia del notificador depende del run del
  evento.

## Comprobación que la sostiene

- Guardián visto fallar contra el workflow de `main` y en verde con el cambio;
  guardianes existentes del notificador intactos: transcritos en el cuerpo de
  la PR.
- Cadena completa como una sola invocación, anclada a su árbol (ADR-154):
  transcrita en el cuerpo de la PR.
- Lo que NO se ha medido: el caso en vivo (criterio 3), que necesita una
  incidencia con tres aplicaciones seguidas de la misma etiqueta después de
  esta fusión.

## Consecuencias

- El historial deja de perder sucesos por la cola, que era el último sitio por
  donde ADR-157 se escapaba.
- Los avisos de una misma etiqueta pueden publicarse desordenados. El motor no
  los usa para ordenar desde ADR-147, y así queda declarado.
- Los historiales publicados antes de esta fusión conservan sus huecos: los
  respaldos del reflector siguen siendo necesarios para ellos.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».

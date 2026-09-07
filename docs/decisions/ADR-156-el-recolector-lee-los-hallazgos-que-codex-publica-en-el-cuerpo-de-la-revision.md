# ADR-156 — El recolector lee los hallazgos que Codex publica en el cuerpo de la revisión

- Estado: PROPUESTO
- Fecha: 2026-09-07
- Aprobación: mandato nocturno del propietario del 07-09-2026 («Ya está códex
  asi q dale», hacia las 04:19 UTC) y la fusión de esta PR (toca
  `scripts/automation/**`: ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-156-hallazgos-en-el-cuerpo`, publicada antes del primer cambio,
con las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

La ronda de revisión de #545 (PR #546, head `bc33b82`) se reanudó a las
04:20:25 UTC del 07-09 con `continua`, al volver la cuota de Codex. Codex
contestó a las 04:24:03 con una revisión formal `COMMENTED` (5128044887)
sobre `bc33b82` con UN hallazgo P2, publicado ÍNTEGRAMENTE en el cuerpo de la
revisión y sin ningún comentario inline. El hallazgo señala
`scripts/automation/sirius_apply_verdict.sh:356`, un fichero que NO está en
el diff de la PR (llegó a la rama al actualizarla con `main`, #560), y GitHub
no permite anclar un comentario inline fuera del diff: el conector recurre
entonces al cuerpo, con la forma «enlace permanente al blob del head, insignia
de severidad, título en negrita, descripción, referencia a AGENTS.md».

El recolector (`_check_reviews` de `sirius_codex_review.py`) construye los
hallazgos SOLO desde los comentarios inline (`_observations_from_comments`).
Una revisión `COMMENTED` con cuerpo y sin inline la da por «completa», pero
sin observaciones ni aprobación devuelve «sigue esperando» (`None, True`), y
como hay una revisión formal en curso tampoco mira la reacción ni el
comentario de conversación. La ronda agota el plazo absoluto (1200 s desde el
disparador, 04:40:49) y termina en `FAILED_SAFELY` con razón `timeout`, con el
hallazgo a la vista desde el minuto cuatro. Run 34082742434: revisor Claude de
04:20:50 a 04:29:18; recolector desde 04:29:18.

Es la misma familia que la corrección de ADR-149 del 06-09 y que el propio
hallazgo de Codex: **el motor ignora una señal presente porque llega con una
forma que no esperaba** (un cuerpo en vez de comentarios inline; una respuesta
de `gh` no interpretable con código 0). Por eso esta PR lleva también la
segunda corrección de ADR-149 (sección fechada en ese ADR).

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en `_check_reviews`: al reunir los hallazgos de
   las revisiones candidatas solo lee sus comentarios inline. El arreglo va
   ahí: un lector del cuerpo (`_observations_from_body`) que reconoce cada
   hallazgo por su insignia de severidad, toma del enlace permanente que lo
   precede el fichero y la línea —la línea solo si el enlace apunta al head
   esperado—, excluye el bloque `<details>` de cortesía del conector y
   conserva el texto íntegro del hallazgo como `problema`. Los hallazgos del
   cuerpo se unen a los inline con la misma numeración correlativa. Se observa
   en el JSON normalizado del recolector y en el veredicto agregado.
2. **¿Qué NO garantiza esto?** No garantiza que el hallazgo esté dentro del
   alcance de la PR: justamente estos hallazgos suelen apuntar fuera del diff,
   y de eso se ocupan el guardián de goteo (marca `posible_goteo` cuando el
   fichero no cambió entre rondas) y el corrector (alcance autorizado). No
   cambia la precedencia de canales de §4.1 ni las comprobaciones de autor,
   posterioridad y SHA. No lee cuerpos sin insignia: un cuerpo sin insignia
   sigue siendo un resumen, no un hallazgo, y una revisión sin cuerpo ni inline
   sigue sin interpretar hasta que entregue algo.
3. **Criterio de parada (decidido antes de ver ningún resultado).** Los
   guardianes nuevos ven FALLAR el recolector de `main` con el cuerpo real de
   la revisión 5128044887 (termina en `timeout` sin observaciones) y pasan
   con el cambio (`CHANGES_REQUESTED` con una observación P2 sobre
   `scripts/automation/sirius_apply_verdict.sh:356`); los guardianes
   existentes del recolector siguen en verde (el resumen sin insignia no
   bloquea; la revisión sin cuerpo ni inline sigue sin interpretar); la cadena
   completa termina en 0. En vivo: la siguiente ronda de #545 con Codex
   termina por resultado (aprobación o hallazgos), no por plazo. Un `timeout`
   con una revisión formal de Codex a la vista desmiente este ADR.
4. **¿Qué hace esto imposible, en vez de improbable?** Que un hallazgo formal
   de Codex, publicado y visible, se pierda por la forma en que llegó: el
   recolector lee los dos sitios en los que el conector escribe hallazgos, y
   un guardián con el cuerpo real fija el formato observado.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Leer los hallazgos del cuerpo y unirlos a los inline** (elegida). Es el
   único canal por el que el conector puede señalar un fichero fuera del diff;
   cabe en el recolector sin tocar el contrato ni el agregador.
2. **Pedirle al conector que comente solo inline.** No se controla desde aquí,
   y GitHub no admite un comentario inline fuera del diff: el cuerpo no es una
   preferencia del conector, es su única salida.
3. **Tratar una revisión `COMMENTED` sin inline como «sin hallazgos».**
   Descartada: aprobaría un head con un P2 a la vista.
4. **Parar en el acto con «revisión no interpretable»** en vez de agotar el
   plazo. Ahorra dieciséis minutos, pero sigue perdiendo el hallazgo y obliga
   a un humano a leerlo y transcribirlo. Descartada.

## Decisión

- `scripts/automation/sirius_codex_review.py`: `_observations_from_body`
  reconoce los hallazgos del cuerpo por la insignia de severidad, toma del
  enlace permanente que precede a cada uno la ruta y la línea (la línea solo
  si el enlace es del head esperado; sin enlace, `desconocido`), excluye los
  bloques `<details>` y conserva el texto del bloque como `problema`;
  `_check_reviews` une esos hallazgos a los inline de todas las revisiones
  candidatas, numerados a continuación de los inline y en el orden de las
  revisiones. `prueba` es el enlace de la revisión.
- Guardianes: el cuerpo real de la revisión 5128044887 produce
  `CHANGES_REQUESTED` con una observación P2 sobre
  `scripts/automation/sirius_apply_verdict.sh:356` cuyo `problema` conserva
  el texto y no arrastra el bloque de cortesía; los hallazgos del cuerpo se
  unen a los inline con numeración correlativa; un enlace permanente de otro
  commit no presta su línea; dos hallazgos en un cuerpo son dos observaciones
  en su orden; el resumen sin insignia sigue sin ser un hallazgo.

## Comprobación que la sostiene

- Guardianes vistos fallar contra el recolector de `main` y en verde con el
  cambio; suite del recolector intacta: transcritos en el cuerpo de la PR.
- Cadena completa como una sola invocación, anclada a su árbol (ADR-154):
  transcrita en el cuerpo de la PR.
- Lo que NO se ha medido: el caso en vivo (criterio 3), que mide la siguiente
  ronda de #545.

## Consecuencias

- Una ronda con un hallazgo publicado solo en el cuerpo termina por
  resultado en unos cinco minutos, en vez de por plazo a los veinte.
- Los hallazgos fuera del diff llegan al corrector, normalmente marcados
  `posible_goteo`; la regla de alcance del corrector decide qué hacer con
  ellos. Lo que no puede pasar es que se pierdan.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».

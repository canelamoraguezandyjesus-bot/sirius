# ADR-023 — Admitir como aprobación de Codex el comentario en el que declara no haber encontrado hallazgos

- Estado: PROPUESTO
- Fecha: 2026-08-16
- Aprobación: la fusión de la PR de esta rama por el propietario. Entra en vigor con ella
  el contrato operativo **v1.6.1** (§10.6).

## Contexto y problema

El contrato §4.1 definía la aprobación de Codex así: «la aprobación exige una revisión
formal `APPROVED` o una reacción `+1` del conector sobre el disparador». Las siete rondas
de revisión dual de la PR #178 demuestran que **ninguno de esos dos canales ocurre nunca**
con este conector:

| Qué encuentra Codex | Cómo lo entrega | Rondas |
|---|---|---|
| Hallazgos | Revisión formal con `commit_id`, `state: COMMENTED` | 6 |
| Nada | Comentario de conversación con marcador `Reviewed commit:` | 1 |

- Ninguna de las seis revisiones formales tiene `state: APPROVED`.
- En la ronda sin hallazgos (head `cddf65fe`) publicó el comentario 5308880281 —«Codex
  Review: Didn't find any major issues»— y **no** marcó 👍: el disparador 5308868949 tiene
  `reactions.total_count: 0`, `"+1": 0`. Su propio texto de ayuda promete «If Codex has
  suggestions, it will comment; otherwise it will react with 👍»; no lo cumple.

Consecuencia: con la regla anterior, **ninguna PR limpia podía alcanzar
`sirius:ready-for-merge` en modo dual**. No era una intermitencia ni una dependencia
externa caída; era un bloqueo estructural que el contrato se había fijado a sí mismo al
describir un conector que no existe.

No es la primera vez. `_check_conversation_comments` nació en la incidencia **#148**, donde
el conector respondió exactamente igual: entonces se corrigió la mentira del timeout (la
ronda afirmaba que Codex «no entregó un resultado identificable» habiendo entregado uno)
pero se dejó el desenlace en `FAILED_SAFELY` citando §4.1. Segunda mordedura de la misma
familia: la regla de las dos rondas (ADR-001) prohíbe aquí seguir parcheando el síntoma.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#177, comentario 5310257947](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/177#issuecomment-5310257947)),
antes del primer commit, con sus cuatro preguntas. Lo que ata:

- Alcance: el recolector, sus pruebas, §4.1 y su registro §10, y este ADR.
- **Parar y consultar** si el arreglo exigiera tocar workflows, permisos, el agregador, la
  convergencia o el documento del plan. Ninguno se tocó.
- Numeración: usar **v1.6.1** para no pisar las reservas de v1.7 (E1a) y v1.8 (E1b) de
  ADR-020 §5; si 1.6.1 obligara a editar el plan, parar. No obligó: el plan no se toca.
- Máximo 2 rondas de autorevisión; misma familia dos veces → buscar la raíz.
- Toda prueba que fije una propiedad, verificada por mutación antes de darla por buena.

Desviación declarada: se actualizó además `scripts/automation/README.md`, que describía la
regla vieja del mismo script. No es alcance nuevo —es la documentación del fichero que se
cambia— y dejarla sería la deriva documental que este repositorio lleva corrigiendo.

## Opciones consideradas

1. **Dejarlo como está y apagar la bandera cuando estorbe**: descartada. Convierte la
   revisión dual en decorativa: cada PR limpia exigiría que una persona apagara una
   variable de repositorio. La bandera existe para revertir una funcionalidad, no para
   sortear un defecto en cada ronda.
2. **Exigir a Codex una revisión formal** (cambiando el texto del disparador): descartada
   — el formato de salida del conector no está bajo nuestro control, y la PR #178 muestra
   que ya se le pide explícitamente reportar hallazgos: cuando no tiene ninguno, no publica
   revisión.
3. **Aceptar cualquier comentario del conector como aprobación**: descartada — sería
   aprobar por procedencia en vez de por contenido, y un comentario suyo puede ser
   cualquier cosa (una pregunta, un aviso de proceso, un resumen con hallazgos).
4. **Admitir un tercer canal, estrecho y que falle cerrado**: elegida.

## Decisión

Admitir como aprobación un comentario de la conversación cuando cumple **todas** estas
condiciones —las tres primeras ya las exigía el canal existente—:

1. Autor en la allowlist del conector oficial.
2. Estrictamente posterior al disparador de la ronda.
3. SHA demostrable (`Reviewed commit:`) e igual al head esperado.
4. **Su cuerpo declara ausencia de hallazgos en la fórmula observada** —variantes de
   «did(n't) find any [major] issues»—, y **no** trae insignias de severidad.
5. **Todos** los comentarios del conector referidos a ese head cumplen (4), no solo uno.

Cualquier otro comentario del conector sigue terminando en la parada segura
`respuesta-por-comentario`. La precedencia no cambia: este canal solo se consulta cuando no
hay ninguna revisión formal posterior al disparador ni reacción, porque una señal débil no
puede resolver una ambigüedad.

La condición (5) salió de la primera ronda de autorevisión de este trabajo, no del diseño
inicial. La primera versión decidía con el primer comentario que encajara, y eso hacía el
desenlace dependiente del orden de llegada por los dos lados: un comentario intermedio del
conector habría bloqueado una ronda limpia, y —si se hubiera elegido el último en su lugar—
una declaración posterior habría enterrado un comentario anterior con hallazgos, aprobando
un head con defectos ya reportados. Exigirlo de todos elimina las dos. Es el mismo principio
que `_check_reviews` ya aplicaba a las revisiones; no haberlo visto al escribirlo es
justamente lo que la ronda de autorevisión existe para cazar.

El reconocimiento es deliberadamente estrecho porque el error es asimétrico: una redacción
nueva del conector cuesta **una ronda detenida que mira una persona**; un patrón ancho
costaría **aprobar una PR con defectos**. Solo el primero es recuperable.

Tres garantías se conservan intactas y conviene decirlo, porque son las que hacen aceptable
este canal más débil: la ausencia de señales sigue sin aprobar jamás; el agregador exige que
**Claude apruebe el mismo SHA** para que la ronda termine en `REVIEW_APPROVED`, así que esta
señal es como mucho media aprobación; y `sirius_apply_verdict.sh` vuelve a contrastar el
`reviewed_head_sha` con el head actual de la PR y con el último que superó Quality.

## Comprobación que la sostiene

- **Evidencia primaria leída por API**, no de memoria: los 8 comentarios de la PR #178 y sus
  6 revisiones, con `state`, `commit_id`, autor y marcas temporales; y las reacciones del
  disparador 5308868949 a cero.
- **Precedencia y agregación verificadas en el código antes de decidir**: el bucle de
  `cmd_collect` solo consulta el canal del comentario con `has_reviews == False`; la regla 6
  de `sirius_aggregate_reviews.py` exige que ambos revisores aprueben.
- **Prueba por mutación, en las dos direcciones y sobre las cuatro propiedades** (ADR-001 §3):

  | Mutación | Qué falla |
  |---|---|
  | `_declares_no_findings` devuelve siempre `False` (comportamiento anterior) | la prueba de aprobación |
  | devuelve siempre `True` (patrón ancho) | las 4 redacciones ajenas + la de insignias |
  | se elimina la guarda de insignias de severidad | la prueba de insignias |
  | se quita `not has_reviews` del bucle (se pierde la precedencia) | la prueba de precedencia — y aprueba, que es justo el peligro |
  | decide el PRIMER comentario en vez de exigirlo a todos | el caso `el-ruido-llega-despues` |
  | decide el ÚLTIMO comentario | el caso `el-ruido-llega-antes` |

  Sin la cuarta, la prueba de precedencia habría sido vacua: pasaba con las tres primeras.
  Las dos últimas se hicieron por separado a propósito: cada una tumba solo uno de los dos
  casos del test parametrizado, lo que demuestra que ambos casos cargan peso y que ninguno
  de los dos criterios ingenuos —primero o último— habría bastado.
- La prueba de aprobación usa el **cuerpo literal** publicado por el conector en el run
  31963233730, no una paráfrasis.
- Validaciones obligatorias en verde: `ruff format --check .`, `ruff check .`,
  `mypy src tests`, `pytest tests/automation/`.

## Consecuencias

- El modo dual vuelve a poder terminar en `REVIEW_APPROVED`. La incidencia #177 (bloque A1)
  puede reactivar su revisión sin apagar la bandera.
- **Queda una dependencia externa declarada, no cerrada**: si el conector cambia su
  redacción, las rondas limpias volverán a detenerse en `respuesta-por-comentario` hasta que
  se añada la variante. Es el precio elegido de fallar cerrado, y el mensaje de la parada
  dice exactamente eso para que el diagnóstico sea inmediato.
- La base de evidencia es estrecha y así queda dicho: **7 rondas de una sola PR**. No se
  afirma conocer todo el repertorio del conector.
- El contrato pasa a v1.6.1. El tercer nivel de numeración es nuevo en este documento y se
  usa a propósito para no renumerar el plan aprobado (ADR-020 §5 reserva v1.7 y v1.8). Si el
  propietario prefiere v1.7, renumerar es un cambio de una línea y del §10.6.
- ADR-014 cita la regla anterior en su línea 55. **No se reescribe**: describe lo que era
  cierto cuando se escribió, y falsear el historial es peor que una cita fechada.

## Alternativas descartadas y por qué

Las opciones 1–3 de arriba. Además: exigir además que el head actual de la PR siga siendo el
esperado, como hace el canal de la reacción `+1` —descartada por redundante: la reacción lo
necesita porque no lleva SHA alguno, mientras que aquí el comentario lo declara, y
`sirius_apply_verdict.sh` ya vuelve a contrastarlo aguas abajo—; y exigir el prefijo «Codex
Review:» en el cuerpo —descartada: la procedencia ya la garantiza la allowlist de autores, y
atar la decisión a un encabezado decorativo añade fragilidad sin añadir garantía—.

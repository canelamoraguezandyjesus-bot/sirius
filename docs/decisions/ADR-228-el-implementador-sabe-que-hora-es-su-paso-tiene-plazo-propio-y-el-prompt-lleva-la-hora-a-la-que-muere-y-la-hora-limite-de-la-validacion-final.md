# ADR-228 — El implementador sabe qué hora es: su paso tiene plazo propio y el prompt lleva la hora a la que muere y la hora límite de la validación final

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #675 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-el-implementador-sabe-que-hora-es.md`,
  confirmada en `3c09d107` antes del primer commit de arreglo, con las cuatro
  preguntas, las predicciones y el criterio de parada.

## Contexto y problema

El corrector tiene su plazo a la vista desde ADR-155: su workflow calcula con
`date -u` la hora a la que muere su paso y la hora límite para arrancar la
validación final, con el mismo número que su `timeout-minutes`, y se lo escribe
en el contexto del prompt. El implementador no: `implement-sirius-work.yml`
tenía un job de 60 minutos, el paso del agente sin plazo propio, «Sync
environment» sin plazo propio y ni una hora en el prompt. Su prompt le manda
parar con `FAILED_SAFELY` si algo no cabe, «pero sin reloj no puede saber que
no cabe» (bitácora, entrada 92, deuda 30).

Lo medido: el 11-09-2026 el implementador de #581 corrió de 05:20:37Z a
06:20:32Z y lo canceló el tope del job a los 59:52, sin rama, sin PR y sin
veredicto; se publicó el provisional («se escribió al empezar y no llegó a
sustituirse»). Una hora de runner y de modelo a cambio de nada, y lo que
descubrió en esa hora —que el encargo era insatisfacible— murió con él. En el
volcado de septiembre hay 19 comentarios del motor con el veredicto provisional
sin sustituir, en 13 incidencias, de todos los roles. La mina lo lista como
mejora 9, mitad del implementador.

## Criterio de parada (escrito ANTES de decidir)

Copiado de la nota de arranque:

- Si el reloj exigiera una versión nueva del prompt del implementador
  (`implementer@5`), parar: es otra decisión, con su manifiesto.
- Si cubrir los plazos propios obligara a un job por encima de 85 minutos,
  parar: el contador de los siete días lo prohíbe (ADR-093). (ADR-225 retiró
  después ese techo; el job se queda en 85 porque es el presupuesto medido que
  se reparte, no por el contador.)
- Cuatro mutaciones tienen que caer: M1 `PLAZO_MIN` distinto del tope del
  paso; M2 el paso del agente sin plazo propio; M3 la línea del plazo fuera
  del contexto; M4 el job sin cubrir la suma de los plazos propios. (Tras la
  ronda 1 de Codex son siete, abajo: el plazo dejó de ser un número fijo.)
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

Ninguna de las dos primeras paró: el reloj va en «Contexto de esta ejecución»,
que escribe el workflow y no el prompt versionado del rol (H-28), y el plazo
del agente no es una suma fija que tenga que caber: es lo que queda del job.

## Opciones consideradas

1. Dejarlo: cada implementador que no quepa en su hora muere sin diagnóstico
   y el motor publica un veredicto provisional que no dice nada.
2. **El mecanismo de ADR-155, aplicado al implementador** (la elegida, en dos
   versiones): plazo propio en el paso del agente, las dos horas calculadas
   con el mismo número en el paso del prompt, y una guarda que las ata. La
   primera versión clavaba el plazo en 50 y subía el job a 85 para cubrir la
   suma; Codex la tumbó en la ronda 1 de la PR #675: con una preparación de
   más de 35 minutos el tope del job volvía a llegar antes que el plazo del
   paso, y la revisión independiente añadió que el implementador de #653 tardó
   50:50 en su paso, así que 50 fijos eran además una regresión. La segunda,
   esta, **calcula el plazo desde el arranque del job**.
3. Una versión nueva del prompt del rol con las reglas del reloj. Descartada
   por ahora: el prompt vigente ya manda parar con `FAILED_SAFELY` y decir qué
   faltaba; lo que no tenía era la hora, y la hora la pone el workflow.
4. Un latido del agente (fase y hora cada N minutos) que sobreviva a la
   muerte del job. Descartada: la salida del agente no va al log a propósito
   (ADR-044) y el agente ya puede escribir su veredicto cuando quiera; lo que
   le faltaba era saber cuándo.

## Decisión

En `.github/workflows/implement-sirius-work.yml`:

1. El primer paso del job, «Anotar el arranque del job», deja
   `JOB_ARRANQUE_EPOCH` en el entorno. Es el primero a propósito: todo lo que
   corra después (checkout, Qt, uv, sync, puertas, el propio prompt) se resta.
2. «Preparar instrucciones para Claude Code» calcula el plazo:
   `plazo_min = TOPE_JOB_MIN (85) − RESERVA_FINAL_MIN (6) − consumido`, lo
   publica como salida del paso, y con `date -u` escribe en «Contexto de esta
   ejecución» la hora a la que muere el paso y la hora límite para arrancar la
   validación final (`plazo_min − RESERVA_VALIDACION_MIN`, con 25: la cadena
   completa ha tardado hasta 21,4 minutos en el runner del implementador,
   #653, run 35516764738, `pytest` 1283 s), **con fecha** (ISO), para que un
   run que cruce la medianoche no sea ambiguo frente a `date -u`; y la orden
   de, llegada esa hora, dejar de implementar, validar lo hecho una vez,
   empujar y escribir el veredicto con lo hecho y lo que falta. Por debajo de
   `PLAZO_MINIMO_MIN` (40: la validación más algo de implementación) no
   arranca al agente: escribe un veredicto `FAILED_SAFELY` en
   `SIRIUS_VERDICT_FILE` que dice cuánto consumió la preparación y falla;
   «Aplicar el veredicto» lo publica y la incidencia para en seguro con su
   causa, reintentable con `continua`.
3. El paso «Ejecutar Claude Code (implementador)» lleva `timeout-minutes:
   ${{ fromJSON(steps.build_prompt.outputs.plazo_min || '1') }}`: muere su
   paso y no el job, y el número es el que recibió en el prompt (el `|| '1'`
   solo cubre el caso en que el paso anterior no corrió, y entonces este se
   salta). «Sync environment» conserva `timeout-minutes: 19` (peor medido sin
   caché: 16 m 30 s, ADR-224) y el job se queda en **85**, el presupuesto que
   se reparte; `TOPE_JOB_MIN` tiene que ser ese mismo número.
4. El prompt versionado del rol (`implementer@4`) no se toca.
5. La proyección Python del prompt
   (`src/sirius_engine/adapters/github_worker_request.py`, A4-P2) reproduce la
   línea del reloj a partir de un `ahora` y de lo que la preparación llevaba
   `consumido_min`, con la misma resta (`plazo_del_implementador`, que
   devuelve `None` por debajo del mínimo, y entonces la proyección se niega
   como el workflow) y sus constantes (`TOPE_DEL_JOB_MIN`, `RESERVA_FINAL_MIN`,
   `RESERVA_PARA_LA_VALIDACION_MIN`, `PLAZO_MINIMO_MIN`) atadas a los números
   del YAML por una guarda; sin los dos no lleva la línea y lo declara; uno
   solo es un error. La prueba de no-divergencia fija la hora del guión real
   con un `date` de arnés y el arranque del job con `JOB_ARRANQUE_EPOCH`: la
   primera versión de este cambio la puso en rojo en Quality porque el guión
   imprimía una hora viva y la proyección ninguna.

## Comprobación que la sostiene

- `tests/automation/test_implementador_con_reloj.py`, siete guardas que leen
  el YAML real: el arranque del job se anota en el primer paso; el paso del
  agente tiene por plazo la salida `plazo_min` del paso del prompt, que la
  calcula restando lo consumido; `TOPE_JOB_MIN` es el `timeout-minutes` del
  job y el agente no tiene número fijo; las reservas cubren lo medido (la de
  validación entre 22 y 30, la final 5 o más, el mínimo deja sitio para
  implementar); los números de Python son los del YAML; el contexto lleva las
  dos horas con fecha, calculadas con `date -u`, en una línea `echo` dentro del
  heredoc que nombra `FAILED_SAFELY`; y una preparación lenta deja un veredicto
  `FAILED_SAFELY` en la ruta que «Aplicar el veredicto» lee.
- `tests/engine/test_worker_request.py` ejecuta el guión real del paso con el
  `date` de arnés y `JOB_ARRANQUE_EPOCH`: con 8 minutos consumidos el prompt
  dice `71 minutos desde ahora`, muere a las `2026-10-01T13:11:00Z` y la
  validación arranca a las `12:46:00Z`; con 30, `plazo_min=49`; con 45 el
  guión falla, deja el veredicto `FAILED_SAFELY` («consumió 45 minutos de los
  85 … quedaban 34 … mínimo de 40») y una salida válida (`plazo_min=1`) para
  el paso que se salta. La proyección hace la misma resta y se niega por
  debajo del mínimo.
- Ronda 1 de Codex (P1) y una revisión independiente sobre la primera versión:
  el plazo fijo era mentira con una preparación lenta y los pasos sin plazo
  propio (checkout, uv, puerta, evento, prompt, aplicar) lo permitían; 50
  fijos eran una regresión frente a los 50:50 del paso de #653; la reserva de
  16 no cubría los 21,4 minutos medidos de la cadena; las horas sin fecha eran
  ambiguas al cruzar la medianoche; el recuento de la batería decía 187 y eran
  184; la nota de arranque citaba la mina por un fichero que aún no está en
  `main` y no decía «fecha». Todo corregido aquí.
- Mutaciones sobre el YAML, con el fichero restaurado (`diff -q` limpio):

| | Mutación | Resultado |
|---|---|---|
| M1 | el paso del agente vuelve a un plazo fijo (`timeout-minutes: 50`) | cae `el_implementador_tiene_plazo_propio_y_es_el_que_recibe_en_su_prompt` |
| M2 | el paso del agente sin `timeout-minutes` | cae la misma |
| M3 | la línea del plazo convertida en un no-op (`:`) | caen `el_contexto_del_prompt_lleva_las_dos_horas_con_fecha`, las dos de no-divergencia y la del cálculo desde el arranque |
| M4 | el job a 60 con `TOPE_JOB_MIN=85` | cae `el_tope_del_job_es_el_que_se_reparte` |
| M5 | el plazo sin restar lo consumido (`consumido_min=0`) | caen `el_plazo_del_prompt_se_calcula_desde_el_arranque_del_job`, la del mínimo, las dos de no-divergencia y `el_implementador_tiene_plazo_propio…` (cinco) |
| M6 | sin el mínimo: se arranca al agente con cualquier plazo | caen `una_preparacion_que_se_come_el_plazo_no_arranca_al_agente_y_deja_el_veredicto` y `una_preparacion_lenta_deja_un_veredicto_en_vez_de_un_agente_sin_plazo` |
| M7 | las horas sin fecha (`%H:%M:%SZ`) | caen `el_contexto_del_prompt_lleva_las_dos_horas_con_fecha` y la no-divergencia |

- Las pruebas que leen `implement-sirius-work.yml` y los `timeout-minutes` de
  todos los workflows siguen en verde (`test_contador_de_siete_dias.py`,
  `test_automatizacion_congelada_de_main.py`, `test_prompts_de_rol.py`,
  `test_sirius_reconcile.py`, `test_sirius_notifications.py`,
  `test_quality_relanzado_al_entrar_en_ci_pending.py`,
  `test_resolver_prompt.py`, `test_investigar_orden_workflow.py`,
  `test_auditor_workflow.py`, `test_corrector_entrega_por_hallazgo.py`:
  184 passed, 11 skipped). El `timeout-minutes` del agente es ahora una expresión, y
  las guardas que suman topes solo cuentan enteros; el máximo del job sigue
  siendo 85.
- El YAML carga; `ruff` y `mypy src tests`, sin avisos.
- La medida que no se puede tomar aquí: el primer implementador que no quepa
  escribirá su diagnóstico antes de la hora límite en vez de morir a los
  59:52. Queda para la mina de octubre.

## Consecuencias

- El implementador sabe cuándo muere y cuándo tiene que estar validando; un
  encargo que no cabe termina con un `FAILED_SAFELY` que dice dónde se quedó,
  no con el provisional.
- Con la preparación habitual (unos 8 minutos) el agente recibe unos 71
  minutos: más que los 59:52 que daba el job de 60 y que los 50 fijos de la
  primera versión. Con una preparación lenta recibe menos, pero cierto; y por
  debajo de 40 no arranca: un `FAILED_SAFELY` que dice por qué, en vez de una
  hora de agente tirada.
- El job se queda en 85, el presupuesto que se reparte; subirlo es una
  decisión con su medida (ADR-225 retiró el techo del contador).
- H-228 en el registro de defectos.

## Alternativas descartadas y por qué

Las opciones 1, 3 y 4 de arriba: la 1 porque repite la hora perdida; la 3
porque el prompt ya dice qué hacer y solo le faltaba la hora; la 4 porque la
salida del agente no va al log a propósito y el veredicto ya es su latido.

## La lección

- familia: `paso-largo-sin-plazo-propio`
- sin esto se repetiría: dar a un agente una regla que depende de la hora («para si no cabe») sin darle la hora ni un plazo propio, y dejar que el tope del job lo mate sin diagnóstico; la misma lección que ADR-155 dejó para el corrector y ADR-224 para los pasos de Quality, aplicada al paso que quedaba.
- lo hace cumplir: `tests/automation/test_implementador_con_reloj.py`

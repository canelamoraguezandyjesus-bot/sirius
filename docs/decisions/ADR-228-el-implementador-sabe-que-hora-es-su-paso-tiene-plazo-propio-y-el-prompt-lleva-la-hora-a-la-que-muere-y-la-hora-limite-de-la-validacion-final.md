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
  parar: el contador de los siete días lo prohíbe (ADR-093).
- Cuatro mutaciones tienen que caer: M1 `PLAZO_MIN` distinto del tope del
  paso; M2 el paso del agente sin plazo propio; M3 la línea del plazo fuera
  del contexto; M4 el job sin cubrir la suma de los plazos propios.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

Ninguna de las dos primeras paró: el reloj va en «Contexto de esta ejecución»,
que escribe el workflow y no el prompt versionado del rol (H-28), y la suma
cabe en 85 justos ajustando el plazo del `sync` a 19.

## Opciones consideradas

1. Dejarlo: cada implementador que no quepa en su hora muere sin diagnóstico
   y el motor publica un veredicto provisional que no dice nada.
2. **El mecanismo de ADR-155, aplicado al implementador** (la elegida): plazo
   propio en el paso del agente, las dos horas calculadas con el mismo número
   en el paso del prompt, y una guarda que las ata; el job sube hasta cubrir
   la suma de los plazos propios.
3. Una versión nueva del prompt del rol con las reglas del reloj. Descartada
   por ahora: el prompt vigente ya manda parar con `FAILED_SAFELY` y decir qué
   faltaba; lo que no tenía era la hora, y la hora la pone el workflow.
4. Un latido del agente (fase y hora cada N minutos) que sobreviva a la
   muerte del job. Descartada: la salida del agente no va al log a propósito
   (ADR-044) y el agente ya puede escribir su veredicto cuando quiera; lo que
   le faltaba era saber cuándo.

## Decisión

En `.github/workflows/implement-sirius-work.yml`:

1. El paso «Ejecutar Claude Code (implementador)» lleva `timeout-minutes: 50`,
   propio. Muere su paso y no el job, así que «Aplicar el veredicto» corre con
   normalidad y publica lo que el agente dejó.
2. El paso «Preparar instrucciones para Claude Code» fija `PLAZO_MIN=50` y
   `RESERVA_MIN=16`, calcula con `date -u` la hora a la que muere el paso y la
   hora límite para arrancar la validación final (`PLAZO_MIN − RESERVA_MIN`:
   la cadena completa tarda entre 9 y 15 minutos), y las escribe en «Contexto
   de esta ejecución» con la orden de, llegada esa hora, dejar de implementar,
   validar lo hecho una vez, empujar y escribir el veredicto con lo hecho y lo
   que falta.
3. «Sync environment» lleva `timeout-minutes: 19` (peor medido sin caché:
   16 m 30 s, ADR-224) y el job pasa de 60 a **85**, el máximo que admite el
   contador de los siete días: congelar 1 + Qt 10 + sync 19 + agente 50 = 80,
   más el resto (checkout, uv, puerta, prompt, aplicar: menos de 5 min).
4. El prompt versionado del rol (`implementer@4`) no se toca.
5. La proyección Python del prompt
   (`src/sirius_engine/adapters/github_worker_request.py`, A4-P2) reproduce la
   línea del reloj a partir de un `ahora` que se le pasa, con sus propias
   constantes (`PLAZO_DEL_IMPLEMENTADOR_MIN`, `RESERVA_PARA_LA_VALIDACION_MIN`)
   atadas a los números del YAML por una guarda; sin `ahora` no lleva la línea
   y lo declara. La prueba de no-divergencia fija la hora del guión real con
   un `date` de arnés: la primera versión de este cambio la puso en rojo en
   Quality porque el guión imprimía una hora viva y la proyección ninguna.

## Comprobación que la sostiene

- `tests/automation/test_implementador_con_reloj.py`, cuatro guardas que leen
  el YAML real: el paso del agente tiene plazo propio y es el `PLAZO_MIN` del
  prompt; la reserva está entre 12 y 20 y por debajo del plazo; el contexto
  lleva las dos horas, calculadas con `date -u`, en una línea `echo` dentro del
  heredoc que nombra `FAILED_SAFELY`; el job cubre la suma de los plazos
  propios más 5 y no pasa de 85. Las cuatro en verde; la primera y la última,
  vistas fallar contra el YAML anterior.
- Mutaciones sobre el YAML, con el fichero restaurado (`diff -q` limpio):

| | Mutación | Resultado |
|---|---|---|
| M1 | `PLAZO_MIN=60` con el paso en 50 | cae `el_implementador_tiene_plazo_propio_y_es_el_que_recibe_en_su_prompt` |
| M2 | el paso del agente sin `timeout-minutes` | caen esa y `el_tope_del_job_cubre_todos_los_plazos_propios_y_no_pasa_del_maximo` |
| M3 | la línea del plazo convertida en un no-op (`:`), y también borrada | cae `el_contexto_del_prompt_lleva_las_dos_horas` en las dos formas (la primera forma no caía hasta exigir que la línea sea un `echo`) |
| M4 | el job de vuelta a 60 | cae `el_tope_del_job_cubre_todos_los_plazos_propios_y_no_pasa_del_maximo` |

- Las pruebas que leen `implement-sirius-work.yml` y los `timeout-minutes` de
  todos los workflows siguen en verde (`test_contador_de_siete_dias.py`,
  `test_automatizacion_congelada_de_main.py`, `test_prompts_de_rol.py`,
  `test_sirius_reconcile.py`, `test_sirius_notifications.py`,
  `test_quality_relanzado_al_entrar_en_ci_pending.py`,
  `test_resolver_prompt.py`, `test_investigar_orden_workflow.py`,
  `test_auditor_workflow.py`, `test_corrector_entrega_por_hallazgo.py`: 187
  passed, 11 skipped). La tolerancia del contador (`max(timeout-minutes) × 2`)
  no cambia: el máximo ya era 85.
- `tests/engine/test_worker_request.py`: la no-divergencia entre el guión real
  y la proyección vuelve a ser byte a byte con el reloj dentro (12:50:00Z y
  12:34:00Z sobre una hora fija), y una prueba nueva fija que sin `ahora` no
  hay línea de plazo. `test_implementador_con_reloj.py` ata además los dos
  números de Python a los del YAML (cinco guardas en total).
- El YAML carga; `ruff` y `mypy src tests`, sin avisos.
- La medida que no se puede tomar aquí: el primer implementador que no quepa
  escribirá su diagnóstico antes de la hora límite en vez de morir a los
  59:52. Queda para la mina de octubre.

## Consecuencias

- El implementador sabe cuándo muere y cuándo tiene que estar validando; un
  encargo que no cabe termina con un `FAILED_SAFELY` que dice dónde se quedó,
  no con el provisional.
- Diez minutos menos de agente que antes en el mejor caso (50 frente a los
  59:52 que daba el job cuando la preparación era rápida), a cambio de que el
  plazo sea cierto siempre: antes, una preparación lenta se lo comía sin que
  nadie lo supiera.
- El job pasa al máximo (85): cualquier plazo propio nuevo tendrá que salir
  de los que hay, y la guarda lo dirá.
- H-228 en el registro de defectos.

## Alternativas descartadas y por qué

Las opciones 1, 3 y 4 de arriba: la 1 porque repite la hora perdida; la 3
porque el prompt ya dice qué hacer y solo le faltaba la hora; la 4 porque la
salida del agente no va al log a propósito y el veredicto ya es su latido.

## La lección

- familia: `paso-largo-sin-plazo-propio`
- sin esto se repetiría: dar a un agente una regla que depende de la hora («para si no cabe») sin darle la hora ni un plazo propio, y dejar que el tope del job lo mate sin diagnóstico; la misma lección que ADR-155 dejó para el corrector y ADR-224 para los pasos de Quality, aplicada al paso que quedaba.
- lo hace cumplir: `tests/automation/test_implementador_con_reloj.py`

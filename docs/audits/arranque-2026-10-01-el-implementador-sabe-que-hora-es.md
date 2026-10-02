# Nota de arranque — el implementador sabe qué hora es

Rama `claude/el-implementador-sabe-que-hora-es`. Fecha: 01-10-2026, 15:20 UTC.
Mejora 9 de la lista de la mina de septiembre
(`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-30.md`, §10, en la PR #665), en su mitad del
implementador: deuda 30 de la bitácora (entradas 1, 92 y 94). Escrita antes de
tocar el workflow.

## La cifra de partida

- Bitácora, entrada 92 (11-09, #581): el implementador corrió de 05:20:37Z a
  06:20:32Z y lo canceló el tope de 60 minutos del job: 59:52, sin rama, sin
  PR y sin veredicto («este veredicto provisional se escribió al empezar y no
  llegó a sustituirse»). Su prompt le manda parar con `FAILED_SAFELY` si algo
  no cabe, «pero sin reloj no puede saber que no cabe». Una hora de runner y
  de modelo a cambio de nada; y lo que descubrió en esa hora —que el encargo
  era insatisfacible— murió con él.
- Sobre el volcado del mes: **19 comentarios** del motor con el veredicto
  provisional sin sustituir, en 13 incidencias (#507, #508, #518, #520 ×2,
  #529, #537, #545 ×3, #550, #581 ×3, #582, #601 ×2, #603 ×2). Son muertes de
  todos los roles, no solo del implementador; el corrector tiene reloj desde
  ADR-155 (10-09) y el implementador no.
- `implement-sirius-work.yml` hoy: job de 60 minutos; el paso del agente sin
  plazo propio; el paso «Sync environment» sin plazo propio (sin caché ha
  tardado 16,5 min, ADR-224); el prompt no lleva ninguna hora. El corrector
  (`repair-sirius-work.yml`, ADR-155) recibe en su contexto la hora a la que
  muere su paso y la hora límite para arrancar la validación final, calculadas
  con `date -u` con el mismo número que su `timeout-minutes`, y una guarda lo
  ata.

## Las cuatro preguntas y la predicción

1. ¿El implementador recibe en su contexto la hora a la que muere su paso y la
   hora límite para arrancar la validación final, con el mismo número que
   gobierna el tope de su paso? Predicción: sí, con el mismo mecanismo de
   ADR-155 (dos `date -u` en el paso del prompt y una línea en «Contexto de
   esta ejecución»), sin tocar el prompt versionado del rol (`implementer@4`,
   H-28: el contexto lo escribe el workflow).
2. ¿El paso del agente muere por su propio plazo y no por el del job, de modo
   que «Aplicar el veredicto» corre con normalidad? Predicción: sí, dándole
   `timeout-minutes` propio y subiendo el job hasta cubrir Qt, sync, agente y
   resto; el job no pasa de 85 (el contador de los siete días no admite más,
   ADR-093).
3. ¿Un `timeout-minutes` que alguien cambie sin tocar el prompt se detecta?
   Predicción: sí, una guarda compara `PLAZO_MIN` con el tope del paso, como
   `test_corrector_entrega_por_hallazgo.py`.
4. ¿Cuánto cuesta? Predicción: un workflow y una prueba nueva; ningún permiso,
   ningún prompt versionado, ningún cambio en el aplicador de veredictos.

## Criterio de parada (antes de medir)

- Si el reloj exigiera una versión nueva del prompt del implementador
  (`implementer@5`), parar y decirlo: es otra decisión, con su manifiesto.
- Si cubrir los plazos propios obligara a un job por encima de 85 minutos,
  parar: el contador de los siete días lo prohíbe.
- Cuatro mutaciones tienen que caer: M1 `PLAZO_MIN` distinto del tope del
  paso; M2 el paso del agente sin plazo propio; M3 la línea del plazo fuera
  del contexto; M4 el job sin cubrir la suma de los plazos propios.
- La medida que no se puede tomar aquí: el primer implementador que se quede
  sin tiempo escribirá su diagnóstico antes de la hora límite en vez de morir
  a los 59:52. Queda como observación pendiente para la mina de octubre.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

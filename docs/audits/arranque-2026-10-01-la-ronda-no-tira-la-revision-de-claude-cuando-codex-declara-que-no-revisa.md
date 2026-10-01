# Nota de arranque — la ronda no tira la revisión de Claude cuando Codex declara que no revisa

Rama `claude/el-veredicto-de-claude-no-se-tira-cuando-codex-declara-cuota`,
01-10-2026, 14:50 UTC. Mejora 9 de la lista de la mina de septiembre
(`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-30.md`, §10), en su mitad de
Codex. Escrita antes de tocar el agregador.

## La cifra de partida

- La bitácora del ciclo, entrada 106 (13-09, #581, ronda 11): el revisor de
  Claude corrió entero —44 turnos, `total_cost_usd` 3,31 según la línea
  `result` de su log— y Codex contestó «You have reached your Codex usage
  limits». El agregador de modo dual exige a los dos, así que la ronda terminó
  en `FAILED_SAFELY` (`codex-fallo-declarado`) y el veredicto de Claude se
  descartó sin publicarse.
- Sobre el volcado del mes (`MINA_DATOS`, 30 incidencias): **13 paradas**
  `FAILED_SAFELY` por fallo declarado de Codex, en 6 incidencias (#541; #545
  ×5; #566 ×3; #581 ×2; #592; #599). En cada una el revisor de Claude ya
  había terminado, porque el agregador solo corre después de él. De las 13,
  una tiene el coste medido (3,31 $); las otras doce no dejaron cifra porque
  el veredicto se tiró.
- Hoy mismo, 01-10 a las 13:58 UTC, la cuota de Codex se agotó otra vez (30
  peticiones de revisión en el día sobre las PR de esta sesión).
- Lo que el código hace hoy, leído en `sirius_aggregate_reviews.py`: la
  regla 3 («`FAILED_SAFELY` de cualquiera → `FAILED_SAFELY`») va antes que la
  5 («`CHANGES_REQUESTED` de cualquiera → `CHANGES_REQUESTED`»), así que un
  `CHANGES_REQUESTED` de Claude con observaciones válidas sobre el head
  esperado se pierde si Codex declaró que no revisa.

## Las cuatro preguntas y la predicción

1. ¿Una ronda con Claude en `CHANGES_REQUESTED` y Codex en `FAILED_SAFELY`
   por fallo **declarado** del conector (`codex-fallo-declarado` o su subtipo
   transitorio) puede terminar en `CHANGES_REQUESTED` con las observaciones de
   Claude, sin aprobar nada? Predicción: sí, cambiando solo el agregador; el
   corrector recibe los hallazgos y Codex se vuelve a pedir sobre el head
   corregido.
2. ¿Sigue siendo imposible aprobar sin Codex? Predicción: sí; con Claude en
   `REVIEW_APPROVED` el fallo declarado de Codex sigue parando, y la mutación
   que abra esa puerta la caza una prueba.
3. ¿Un timeout de Codex entra en la excepción? Predicción: no, y no debe:
   un timeout no es una declaración —Codex puede estar revisando todavía— y
   su parada reintentable (ADR-141) se conserva tal cual.
4. ¿Cuánto cuesta? Predicción: un fichero de producción (el agregador), las
   pruebas, y prosa en el contrato §4.1, en la cabecera del workflow y en
   ADR-146; ningún workflow nuevo, ningún permiso nuevo, ningún cambio en el
   recolector ni en el aplicador de veredictos.

## Criterio de parada (antes de medir)

- Si entregar la mitad del veredicto exigiera un campo nuevo que
  `sirius_apply_verdict.sh` no sabe publicar, parar: el aplicador no se toca
  en esta PR.
- Si el contrato §4.1 o un ADR vigente prohibiera expresamente que un
  `CHANGES_REQUESTED` salga sin Codex (y no solo la aprobación), parar y
  llevarlo a la lista de decisiones del propietario.
- Cuatro mutaciones tienen que caer: M1 la excepción desactivada (vuelve la
  regla 3 de hoy); M2 el timeout dentro de la excepción; M3 la excepción
  abierta también a `REVIEW_APPROVED` de Claude (aprobaría sin Codex); M4 el
  resumen sin la constancia de que Codex no revisó.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

# Nota de arranque — la línea del contador de los siete días quedó cancelada el 13-09 y el árbol todavía dice que bloquea

Rama `claude/la-linea-del-contador-queda-cancelada-por-decision-del-propietario`,
fecha 01-10-2026, la hora del commit que la publica. Publicada **antes del
primer commit de cambio**, como exige ADR-001.

## El suceso

La mina de septiembre (deuda 13; propuesta 11 de §10) encontró una decisión del
propietario que vive solo en un comentario. El 13-09-2026, a las 13:25:57 UTC,
en la incidencia #610 —el encargo que iba a «implementar el cierre entero de la
cadena del contador de los siete días»—, escribió como `OWNER`:

> Este encargo no debió despacharse. La sesión leyó mal la orden: el propietario
> había dicho que la línea del contador de los siete días **no es necesaria** —y
> la propia sesión se lo había recomendado así— y su «hay que acabar esto
> entero» se refería a **las mejoras del motor que quedan pendientes**, no a
> resucitar esta línea.

La incidencia se cerró `not_planned` a las 13:26:04, sin rama ni PR (el run del
implementador se canceló antes). Lo que el comentario deja vigente: la medida de
la incidencia #605 (54 de 54 entregados coinciden; los dos huecos del eje `fase`
y del reflejo entre paradas; la regla de agregación que hace inalcanzable el
§11.2 mientras haya trabajos detenidos), registrada en esa incidencia y en la
rama `feature/c2-medida-precondicion-contador-siete-dias`.

Dieciocho días después, el árbol sigue diciendo lo contrario: ADR-101 mantiene
la pieza (C) de #376 «como bloque propio, a la orden del propietario», y la
cabecera de `src/sirius_engine/seven_day_streak_cli.py` dice que el conjunto
vacío «sigue bloqueando D1» y que (C) «queda como bloque propio». Es la familia
`decision-que-solo-vive-en-una-conversacion` que la mina nombró.

## Las cuatro preguntas, con la predicción escrita antes de medir

1. **¿Qué dijo exactamente el propietario y dónde?** Comprobado por la API antes
   de escribir esto: la cita de arriba, comentario de #610, 13:25:57 UTC,
   `author_association: OWNER`. Si no estuviera literal, no habría ADR.
2. **¿Cuántos sitios del árbol afirman hoy que la línea sigue pendiente o
   bloquea algo?** Predicción: dos —la consecuencia de ADR-101 y la cabecera del
   CLI— más el triaje de la mina, que la daba por `parcial`. Se mide con `grep`
   de «bloque propio», «sigue bloqueando D1» y «(C) de #376» sobre `src`,
   `scripts` y `docs` (sin la propia mina), antes y después.
3. **¿Qué cambia si se registra?** Un ADR que supere esa consecuencia de ADR-101
   y una cabecera del CLI que diga que la línea se cerró por decisión del 13-09.
   **Ningún comportamiento**: el contador sigue escribiendo `NO_COMPARABLE` con
   honestidad y `CLASES_CON_ESTADO_PROPIO` sigue vacío con su prueba intacta.
4. **¿Qué no cambia y hay que decirlo?** El §11.2 del contrato (la enmienda que
   #610 autorizaba no se hace: el encargo se canceló), `verificar_dia`, la
   racha. Y la decisión sigue siendo del propietario: si algún día quiere la
   línea, la medida de #605 es el punto de partida y hará falta otro ADR.

## Criterio de parada (escrito ANTES de ver resultados)

- Si la cita no está literal en #610 como comentario del `OWNER`, no se escribe
  el ADR.
- Solo prosa y registro: si al medir aparece un sitio con **comportamiento**
  que bloquee por esta línea (una comprobación, una puerta), se para y se mide
  aparte; no entra aquí.
- El ADR declara la familia y H-225 la registra; la guarda
  `test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro` tiene
  que caer antes de la entrada y pasar después.

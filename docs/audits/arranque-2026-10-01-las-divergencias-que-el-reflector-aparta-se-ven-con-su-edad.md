# Nota de arranque — las divergencias que el reflector aparta se ven en la vista de desenlaces, con su edad

Rama `claude/las-divergencias-apartadas-se-ven-con-su-edad`, fecha 01-10-2026
(la hora es la del commit que la publica, 14:46 UTC). Mejora 4 de la lista de la mina de septiembre
(`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-30.md`, §10); defecto H-216
(incidencia #662, entrada 38 de la bitácora). Escrita antes de tocar el
reflector ni la vista.

## La cifra de partida

- `WI-20260828-122242` (clase `investigacion`, incidencia #392) lleva en
  `active` desde el 28-08-2026 en el diario de `estado-del-motor`. Su
  incidencia está cerrada con dos etiquetas de estado que se contradicen
  (`sirius:failed-safely` y `sirius:completed`). El reflector la alcanza, aplica
  su primera regla —ante etiquetas contradictorias no se toca nada— y
  devuelve la divergencia (`reflect.py:275-283`), cada pasada.
- Esa divergencia solo existe en el **log del run** del reflector
  (`reflect_cli.py:193`, una línea por pasada). Ningún fichero la conserva, y
  `DESENLACES.md` —la memoria común que el motor escribe tras cada reflejo
  (ADR-171)— la cuenta como «1 activo» sin decir que el diseño la apartó para
  una persona. **Hoy 0 sitios la muestran**; se encontró auditando el 24-09,
  veintisiete días después, y hoy lleva 34.
- El diseño que la aparta no se toca: ADR-173 la dejó así a propósito y
  ADR-181 §3 lo protege como criterio de parada.

## Las cuatro preguntas y la predicción

1. ¿Una pasada del reflector que declara una divergencia la deja escrita
   junto al diario (encargo, incidencia, motivo, primera y última vez que se
   vio, pasadas) sin tocar `reflect.py`? Predicción: sí; la escribe
   `reflect_cli.py` al terminar la pasada, en `divergencias.json` junto al
   diario, y el paso «Confirmar el diario» del workflow ya la confirma porque
   hace `git add -A`.
2. ¿`DESENLACES.md` lista esas divergencias con su edad? Predicción: sí, una
   sección propia con la edad en días contados desde el último suceso del
   encargo en el diario hasta la última pasada que la vio; para
   `WI-20260828-122242` saldría 34 el día que el reflector vuelva a pasar.
3. ¿Una divergencia que deja de observarse desaparece, y una que no se pudo
   observar se conserva? Predicción: la entrada se retira solo cuando la
   pasada evaluó ese encargo y no vio divergencia (o el encargo ya es
   terminal); si la incidencia no se pudo leer, la entrada se queda con su
   última fecha. En `--ensayo` no se escribe nada.
4. ¿Cuánto cuesta? Predicción: dos ficheros de producción (`reflect_cli.py`,
   `memoria.py`) y sus pruebas; ningún workflow, ningún permiso, ningún cambio
   en las reglas del reflector.

## Criterio de parada (antes de medir)

- Si conservar la divergencia exigiera tocar una regla de `reflect.py`, parar:
  ADR-181 §3.
- Si la vista necesitara leer GitHub para calcular la edad, parar: la vista
  se deriva solo de ficheros (ADR-171).
- Cuatro mutaciones tienen que caer: M1 la pasada no escribe el fichero; M2 la
  vista ignora el fichero; M3 una incidencia ilegible borra la entrada; M4 el
  ensayo escribe el fichero.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

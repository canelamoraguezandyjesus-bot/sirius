# ADR-143 — Los dos lectores de cron del repositorio hablan un único dialecto

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]
- Encargo: WI-20260905-034826 (incidencia #537)

Este ADR es **además la nota de arranque de la rama**: sus cuatro preguntas y
su criterio de parada se escribieron y se confirmaron ANTES del primer cambio
de código, con el rojo previo ya observado pero sin ninguna línea del arreglo
escrita.

## Nota de arranque (antes del primer commit)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en los DOS
   lectores de `cron` del repositorio, cada uno con su propio dialecto
   incompleto: `sirius_engine.seven_day_streak._expandir_campo` (el del motor)
   y el minilector inline del guardián-oráculo
   `test_hora_recomendada_atada_al_schedule_real_del_repositorio`
   (`tests/engine/test_seven_day_streak.py`). El arreglo va en los mismos dos
   sitios, por separado —el oráculo conserva su independencia («YAML aparte»),
   así que no puede importar el lector del motor— más un tercer sitio nuevo
   que es el que de verdad cierra el agujero: una tabla de equivalencia que
   compara las dos expansiones y los dos rechazos. ¿Puede el sitio del arreglo
   observar el fallo que arregla? Ningún lector puede observar la divergencia
   con el otro: por eso el guardián de equivalencia es un tercero, y no un
   añadido a ninguno de los dos.
2. **¿Qué NO garantiza esto?** No garantiza compatibilidad con el `cron`
   completo de GitHub: el paso sobre rango (`8-18/2`), los nombres (`JAN`,
   `MON`), `?`, `L`, `#` y `W` quedan FUERA del dialecto, y quedan fuera a
   propósito. No toca los tres campos restantes (día del mes, mes, día de la
   semana), que no cambian la hora del día. No garantiza que un `schedule:`
   nuevo produzca días verdes: eso lo sigue midiendo el invariante de
   tolerancia de ADR-139. Y no impide que alguien escriba un TERCER lector de
   `cron`: la tabla ata a los dos que hay.
3. **Criterio de parada** (decidido antes de ver ningún resultado del
   arreglo): (a) si unificar el dialecto cambiara la hora recomendada derivada
   del árbol real, se para: el encargo dice expresamente que ninguna
   derivación vigente cambia, así que un cambio ahí sería señal de que el
   dialecto nuevo interpreta distinto lo que ya funcionaba; (b) si el
   oráculo no pudiera implementar el dialecto íntegro sin importar código del
   motor, se para y se escala, porque romper el «YAML aparte» es una decisión
   de disciplina que no me toca; (c) si aparecieran dos rondas de defectos de
   la misma familia («una forma más que un lector no digiere»), se para de
   parchear formas sueltas y se busca la raíz.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Lo imposible de
   verdad sería un solo lector, y está descartado por el propio encargo: el
   oráculo pierde su valor si mide con el mismo código que audita. Lo segundo
   mejor, y es lo que se hace, es que la divergencia no pueda ser SILENCIOSA:
   una tabla de expresiones que exige a los dos lectores la misma expansión y
   los mismos rechazos convierte «divergen» en un rojo inmediato. Queda
   improbable, no imposible, que alguien añada una forma a un lector, a la
   tabla y no al otro; el rojo de la tabla es justo lo que lo impide.

## Contexto y problema

El repositorio lee expresiones `cron` de los workflows en dos sitios con
dialectos distintos, y esa divergencia costó dos rojos confusos la noche del
04/05-09-2026 (ADR-139, «Comprobación que la sostiene», rojos 2 y 3):

- el lector del motor entendía `*`, `*/N`, entero suelto, listas por comas **de
  enteros sueltos** y rangos `a-b` a secas, pero su rama de comas se evalúa
  antes que la de rangos y no recurre: `4-23` funcionaba y `0,4-23` reventaba
  con `ValueError: invalid literal for int() with base 10: '4-23'`;
- el minilector del oráculo solo digería minuto entero y hora entera o `*/N`:
  todo lo demás reventaba con el mismo `int()` pelado.

Ninguno de los dos mensajes decía qué campo ni qué forma, y en dos casos el
lector del motor ni siquiera fallaba: `3-1` devolvía la lista vacía en
silencio, y `24` en el campo de hora devolvía `[24]`, un valor que no existe.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3, palabra por palabra. Ninguno de sus tres
supuestos se disparó: la hora derivada del árbol real no se movió, el oráculo
implementa el dialecto íntegro sin importar nada del motor, y no hubo dos
rondas de la misma familia.

Una precisión que el dato obliga a hacer, y que el encargo tenía cruzada: el
encargo pide que «la hora recomendada derivada del árbol real siga siendo
exactamente 03:24 UTC», pero 03:24 es el `cron` CONFIGURADO del contador
(`24 3 * * *` en `.github/workflows/contador-siete-dias.yml`), no lo que
`hora_recomendada_pasada()` deriva. Medido sobre el árbol real, antes y
después del cambio, lo derivado es **09:24 UTC** (punto medio del mayor hueco
libre, 345 min tras las 06:32 UTC). Lo que el encargo protege —que ninguna
derivación vigente se mueva— se cumple exactamente: el valor es idéntico antes
y después. Este ADR no cambia ningún `schedule:`; que el `cron` configurado no
coincida con el derivado es un hecho anterior y ajeno a este encargo.

## Opciones consideradas

1. **Un solo lector, importado por el oráculo.** Descartada por el encargo y
   por la disciplina que el propio docstring del oráculo cita: un guardián que
   mide con el código que audita no mide nada.
2. **Dejar los dialectos como estaban y documentar la diferencia.** Es lo que
   ADR-139 hizo de urgencia, y es lo que permitió que el segundo rojo llegara
   por sorpresa: documentar una trampa no la desarma.
3. **Dos implementaciones independientes del MISMO dialecto, atadas por una
   tabla de equivalencia.** La elegida.

## Decisión

Un único dialecto para los campos minuto/hora de los `cron` de este
repositorio, documentado en un solo sitio —el docstring de
`_expandir_campo`—, con estas cinco formas y ninguna más:

| Forma | Ejemplo | Expande a |
|---|---|---|
| Comodín | `*` | todos los valores de `[0, tope)` |
| Paso sobre el comodín | `*/6` | `0, 6, 12, 18` (en hora) |
| Entero suelto | `17` | `17` |
| Rango | `4-23` | `4 … 23` |
| Lista por comas de enteros o rangos | `0,4-23` | `0, 4 … 23` |

Todo lo demás se rechaza **ruidosamente**, con un `ValueError` que nombra el
campo (`minuto` u `hora`), la expresión y la forma no admitida, y que enumera
el dialecto. Nunca un `int()` pelado.

Los dos lectores implementan ese dialecto íntegro y por separado. Un tercer
guardián nuevo —una tabla de expresiones, admitidas y rechazadas— exige a los
dos la misma expansión (comparada como conjunto ordenado) y los mismos
rechazos, en los dos topes reales (60 para minuto, 24 para hora).

## Comprobación que la sostiene

**El rojo previo, observado antes de tocar nada** (`uv run python`, sobre el
lector del motor tal como estaba y una copia literal del minilector del
oráculo; salida completa en la descripción de la PR):

| Campo (tope 24) | Motor, antes | Oráculo, antes |
|---|---|---|
| `*` | `[0…23]` | `ValueError: invalid literal for int() with base 10: '*'` |
| `4-23` | `[4…23]` | `ValueError: … '4-23'` |
| `0,4-23` | `ValueError: … '4-23'` | `ValueError: … '0,4-23'` |
| `1-3,5,7-9` | `ValueError: … '1-3'` | `ValueError: … '1-3,5,7-9'` |
| `0,15,30` | `[0, 15, 30]` | `ValueError: … '0,15,30'` |
| `8-18/2` | `ValueError: … '18/2'` | `ValueError: … '8-18/2'` |
| `3-1` | `[]` (silencio) | `ValueError: … '3-1'` |
| `*/0` | `ValueError: range() arg 3 must not be zero` | ídem |
| `24` | `[24]` (hora inexistente) | `1440` |

Cada forma nueva del dialecto se vio fallar en AL MENOS uno de los dos
lectores, y las mixtas (`0,4-23`, `1-3,5,7-9`) en los dos; los tres últimos
casos son los rechazos que antes eran silencio o mensaje sin campo.

**Después del arreglo**, en `tests/engine/test_seven_day_streak.py`:

- `test_los_dos_lectores_de_cron_expanden_y_rechazan_igual`: la tabla de
  equivalencia, parametrizada por expresión y por tope.
- `test_la_lista_con_rango_expande_igual_en_los_dos_lectores` (`0,4-23`),
  `test_el_paso_sobre_rango_lo_rechazan_los_dos_con_el_campo_en_el_mensaje`
  (`8-18/2`) y `test_el_comodin_en_minuto_expande_a_los_sesenta_en_los_dos`.
- `test_hora_recomendada_atada_al_schedule_real_del_repositorio`, adaptado a
  su helper de módulo (`expandir_campo_del_oraculo`) y no debilitado: sigue
  comparando contra el árbol real, y ahora el minilector expande también el
  campo de MINUTO con el dialecto, no solo la hora.

**Prueba por mutación** (ADR-001), las dos direcciones:

- El oráculo deja de entender rangos dentro de listas (`rango = None`): 13
  rojos, entre ellos la tabla de equivalencia en `0,4-23` y `1-3,5,7-9`.
- El motor vuelve a su rama de comas de enteros sueltos (el fallo original):
  7 rojos, con el mismo par de expresiones. Restaurado el árbol, 163 en verde.

Validaciones obligatorias sobre el árbol final, con su código de salida
verificado (0 en las cinco): `uv run ruff format --check .` (602 ficheros),
`uv run ruff check .`, `uv run mypy src tests` (570 ficheros), `uv run pytest`
(**4932 pasadas, 15 saltadas, 2 xfailed** en 743 s) y `git diff --check`.

## Consecuencias

- Ningún `schedule:` real cambia y ninguna derivación vigente se mueve: la
  hora recomendada derivada del árbol real es 09:24 UTC, el mismo valor que
  daba antes del cambio. Los invariantes de ADR-139 siguen en pie.
- Un `schedule:` futuro con lista, rango o forma mixta ya no revienta ninguno
  de los dos lectores; uno fuera del dialecto revienta los dos, y dice cuál es
  el campo y cuál la forma.
- La línea de ADR-139 que describía el lector del motor («entiende `*`, `*/N`
  y comas, no rangos») se corrige en este mismo commit (regla del corrector,
  ADR-135) para describir el mecanismo real de entonces.
- Queda una deuda pequeña y declarada: el dialecto es el de este repositorio,
  no el de GitHub. Si algún día hace falta `8-18/2`, se amplía en los dos
  lectores a la vez y la tabla lo obliga.

## Alternativas descartadas y por qué

- **Importar `_expandir_campo` en el guardián**: mata la independencia del
  oráculo, que es lo único que hace que su medida valga.
- **Admitir el dialecto completo de GitHub**: alcance mayor que el encargo,
  y sin ningún `schedule:` real que lo pida. Un rechazo ruidoso es mejor que
  una implementación no ejercitada.

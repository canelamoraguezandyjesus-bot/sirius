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

### El límite de las 03:24 lo enmendó el propietario; aquí no se reinterpreta

El encargo pedía que «la hora recomendada derivada del árbol real siga siendo
exactamente 03:24 UTC», y ese límite **no se cumple ni se cumplía antes de este
encargo**. La primera redacción de este ADR lo resolvió por su cuenta,
argumentando que 03:24 era el `cron` configurado y no lo derivado; la revisión
independiente (CODEX-001, P1) señaló que reinterpretar un límite escrito del
encargo es una decisión del propietario y no del implementador, y exigió parar.
Se paró: la ronda de corrección terminó en `BLOCKED_BY_DECISION` sin tocar
nada.

**Lo resolvió el propietario**, con la decisión registrada en la incidencia
\#537 el 05-09-2026. Sus términos, que son los que rigen aquí:

1. El límite «la hora recomendada derivada del árbol real debe seguir siendo
   exactamente 03:24 UTC» **queda ENMENDADO**: se escribió creyendo que la
   derivación vigente daba 03:24. El invariante que este encargo protege pasa a
   ser **«este encargo no cambia la derivación»** —`hora_recomendada_pasada()`
   devuelve exactamente lo mismo con y sin el cambio de dialecto, y ningún
   `schedule:` real cambia—. No se fija 09:24 como criterio eterno: es la
   evidencia de hoy, no un pin.
2. La única corrección autorizada por CODEX-001 es documental, esta misma
   sección: «ninguna línea de código ni de pruebas necesita cambiar».
3. Ni el `schedule:` del contador, ni `hora_recomendada_pasada()`, ni la
   cabecera de `contador-siete-dias.yml` se tocan en este encargo.

**Medido de nuevo hoy sobre esta rama y sobre `main` (`f562cc4`)**, con
`hora_recomendada_pasada()` sobre `.github/workflows` de cada árbol: **09:24
UTC** en los dos, «punto medio del mayor hueco libre de disparos periódicos
(345 min, tras las 06:32 UTC)» palabra por palabra. Idéntico antes y después,
que es lo que el invariante enmendado exige.

Y la raíz, también medida hoy: **el derivador se incluye a sí mismo**. Con el
mismo árbol de workflows pero sin `contador-siete-dias.yml`, la derivación
vuelve a dar **03:24 UTC (345 min, tras las 00:32 UTC)**, que es el número que
la cabecera de ese workflow conserva del 25-08-2026, cuando el workflow aún no
existía: al programar la hora derivada, su propio disparo parte aquel hueco de
345 min en dos y la derivación salta al siguiente hueco de 345, las 09:24. La
deriva no la introduce este cambio de dialecto, la introdujo programar la hora
derivada hace semanas. Esa contradicción preexistente —autoinclusión del
derivador y cabecera obsoleta— queda FUERA de este encargo por el punto 3 de la
decisión, que la manda a ficha propia.

**Desenlace (añadido el 05-09-2026 por el encargo WI-20260905-131022,
incidencia #541, ADR-144).** La medida de arriba no se reescribe: 09:24 UTC es
lo que el derivador autoincluyente daba, y es lo que había que medir aquí. La
ficha propia que este ADR anunciaba se abrió y se resolvió el mismo día:
`hora_recomendada_pasada()` ya no cuenta los disparos de
`contador-siete-dias.yml`, y la derivación del árbol real vuelve a dar
**03:24 UTC (345 min, tras las 00:32)** —el número que el `cron` vigente
llevaba y que la cabecera del workflow declara como derivado, que con esto
vuelve a ser verdad sola—. Ningún fichero de `.github/**` cambió, ni aquí ni
allí. Lo que sigue abierto, y ADR-144 lo declara, es la otra mitad de la
entrada 36 de la bitácora: la pasada todavía no mide su propia ventana al
llegar.

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

Estas tres cifras son la captura del commit de implementación y NO se han
vuelto a correr: las dos correcciones posteriores de CODEX-001 (rondas 2 y 3)
fueron solo documentales —la sección del límite de las 03:24 y esta misma— y
no tocaron ni una línea de `src/sirius_engine/seven_day_streak.py` ni de
`tests/engine/test_seven_day_streak.py`, que es el árbol sobre el que se
midieron.

Validaciones obligatorias **recapturadas sobre esta rama (`786c82d` más esta
sección) con una sola invocación de `pwsh -File scripts/check.ps1`**, que es
lo que AGENTS.md exige entregar. No se partió nada: el script encadena las
cuatro comprobaciones y terminó con código de salida 0. Sus salidas literales,
en orden:

- `uv run ruff format --check .` → «602 files already formatted»;
- `uv run ruff check .` → «All checks passed!»;
- `uv run mypy src tests` → «Success: no issues found in 570 source files»;
- `uv run pytest` → «collected 4949 items» y
  «4932 passed, 15 skipped, 2 xfailed in 448.91s (0:07:28)».

Una sola ejecución del proceso de pytest y de sus fixtures de sesión, con los
mismos recuentos que en el commit de implementación. El script entero tardó
7m32.3s. `git diff --check` sobre el árbol, sin salida.

Esa ejecución se hizo sobre el árbol que ya llevaba esta misma sección
reescrita; la única diferencia entre el árbol medido y el que se commitea es
la transcripción de las cifras de arriba dentro de este párrafo, que ningún
guardián lee. Antes de reescribirla hubo otra ejecución idéntica del script
sobre el árbol intacto (`786c82d` limpio): también salida 0 y también
«4932 passed, 15 skipped, 2 xfailed», en 471.95s.

La ronda anterior partió `pytest` en dos tandas (`acceptance/automation/
contract/engine` por un lado, `gui/integration/unit` por otro) y aun así
afirmó que `uv run pytest` había terminado en 0. Eso no lo demostraba: partir
la suite arranca dos procesos y dos juegos de fixtures de sesión, y nunca
ejercita el script obligatorio entero. La captura de arriba sustituye a
aquella (CODEX-001, ronda 3). Las duraciones sí se anotan ahora porque son de
esta misma captura y forman parte de ella; volverán a moverse en cualquier
pasada futura, que tendrá que recapturarlas junto con el resto.

## Consecuencias

- Ningún `schedule:` real cambia y ninguna derivación vigente se mueve: la
  hora recomendada derivada del árbol real era 09:24 UTC al cerrar este
  encargo, el mismo valor que daba antes del cambio. Los invariantes de
  ADR-139 siguen en pie. (Ese 09:24 lo movió después ADR-144, al retirar la
  autoinclusión del derivador: hoy son las 03:24 UTC. Ver el «Desenlace» de
  más arriba.)
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

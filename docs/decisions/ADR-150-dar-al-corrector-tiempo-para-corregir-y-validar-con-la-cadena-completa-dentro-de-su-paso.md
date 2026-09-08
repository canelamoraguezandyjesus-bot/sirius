# ADR-150 — Dar al corrector tiempo para corregir y validar con la cadena completa dentro de su paso

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (toca `.github/**`;
  ficha del operador, deuda 8 de la bitácora en su parte de presupuesto).

## Contexto y problema

El paso «Ejecutar Claude Code (corrector)» de `repair-sirius-work.yml` tenía
`timeout-minutes: 30`, fijado cuando la ronda del corrector era «corregir lo
señalado y volver a pasar las pruebas afectadas». Desde ADR-145 (05-09) la
ronda exige además **una sola invocación de `scripts/check.ps1`** —formato,
lint, mypy y la suite completa, unos 9 minutos en el runner— antes de
escribir `FIXED`. El presupuesto no se movió con la regla: 30 − 9 = 21
minutos para corregir.

El dato: en la incidencia #545 el corrector de la ronda 1 (run 33998592213,
23:24:31 → 23:55:03 UTC del 05-09) murió con «The action has timed out» a los
30:00 exactos, y al matarlo tenía vivos `pwsh`, `uv` y `pytest`: había hecho la
corrección (un P1 de diseño y dos P2 de Codex) y estaba validando. No llegó a
commit ni push; la PR #546 quedó en `f877ec7`, la incidencia en
`failed-safely` y el veredicto provisional sin sustituir. M21b (03-09) ya
registró **tres** muertes del corrector con este mismo perfil (entradas 16 y
18 de la bitácora); entonces la corrección la terminó el propietario a mano.

Dos restricciones que acotan la respuesta, las dos escritas en el propio
repositorio:

1. El guardián `test_job_timeout_covers_every_bounded_step_plus_margin`
   exige que el job cubra la suma de todos los pasos acotados más 5 de
   margen, y que el paso del corrector sea estrictamente menor que el job.
   Hoy: checkout 5 + Qt 10 + uv 3 + sync 8 + puerta 8 + evento 3 + prompt 2 +
   corrector 30 + aplicación 5 = 74, bajo un job de 80. (El comentario del
   workflow aún decía «= 53, con 7 de margen sobre los 60»: se quedó viejo.)
2. **Ningún job puede subir de 85 minutos.** La cabecera de
   `contador-siete-dias.yml` lo deja dicho: la tolerancia del contador es el
   máximo `timeout-minutes` de TODOS los jobs multiplicado por dos (85 × 2 =
   170 min), y la tranquilidad disponible antes de su pasada de las 03:24 es
   de 172 min; subir cualquier job por encima de 85 deja al contador sin
   ninguna hora que produzca días verdes, y `test_contador_de_siete_dias.py`
   existe para que eso salga en rojo. La primera redacción de este ADR
   proponía corrector 50 y job 100; se retiró por esta restricción antes de
   ejecutar la cadena.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo es un presupuesto
   que no se movió con la regla que lo consume (ADR-145); el arreglo va en el
   único sitio donde vive ese número, el paso del corrector del workflow, y en
   el job que lo cubre. Se observa en el log del run: la hora de muerte y los
   procesos vivos dicen exactamente qué estaba haciendo.
2. **¿Qué NO garantiza esto?** No garantiza que toda ronda quepa: 36 − 9 = 27
   minutos para corregir es más que 21 y menos de lo que un P1 grande puede
   necesitar. No toca `--max-turns`, ni el prompt, ni la puerta, ni el
   contador. No resuelve la deuda 8 (presupuesto por hallazgo, cancelación
   cuando el propietario corrige a mano).
3. **Criterio de parada.** El guardián estructural sigue en verde con los
   números nuevos sin tocar su aritmética, y también los del contador
   (`test_contador_de_siete_dias.py`, y el de ADR-144 sobre la hora
   derivada); si cualquiera de ellos hubiera que debilitarlo, se para. En
   vivo: relanzado el corrector de #545 con `continua`, la ronda termina en
   `FIXED` con su cadena ejecutada, o muere por una causa que NO sea el
   tiempo. Una segunda muerte por tiempo con 36 desmiente este ADR y obliga a
   ir a la raíz (opción 4, abajo), no a subir otro número.
4. **¿Qué hace esto imposible?** Nada nuevo: solo mueve un tope dentro del
   techo que el contador impone. Lo que hace imposible que el techo se rompa
   sin verse ya existía (los guardianes del contador).

## Opciones consideradas

1. **Subir el paso del corrector a 36 y el job a 85** (elegida): el máximo
   que cabe bajo las dos restricciones de arriba. Con los datos de #545 (la
   cadena arrancó hacia el minuto 21 y necesitaba 9) la ronda habría
   terminado hacia el 30 y cabría.
2. **Subir a 50 y el job a 100.** Descartada: rompe la geometría del contador
   (restricción 2).
3. **Quitar la cadena completa de la ronda del corrector** (volver a
   «pruebas afectadas»). Descartada: ADR-145 la puso porque los comandos
   sueltos y las tandas parciales costaron vueltas enteras (#537, #541).
4. **Sacar la validación del paso del agente: que el workflow ejecute
   `scripts/check.ps1` como paso propio, determinista y con su tope, después
   del corrector, y que `FIXED` solo se aplique si ese paso está en verde.**
   Es la respuesta de fondo a dos problemas a la vez —el presupuesto del
   agente deja de incluir los 9 minutos de la cadena, y la declaración
   «exit 0» deja de ser una afirmación del agente para ser un hecho del
   workflow (el primer dato vivo de ADR-145, entrada 41 de la bitácora, fue
   exactamente una declaración falsa)—. Es un cambio de diseño del ciclo,
   con su ADR propio y decisión del propietario; este ADR lo deja
   identificado como la ficha siguiente de esta familia, no lo hace.
5. **Relanzar con 30 y esperar.** Descartada: el mismo trabajo con el mismo
   presupuesto muere en el mismo sitio.

## Decisión

- «Ejecutar Claude Code (corrector)»: `timeout-minutes: 36` (antes 30).
- Job `repair`: `timeout-minutes: 85` (antes 80); el comentario del
  presupuesto pasa a decir la aritmética real: 5 + 10 + 3 + 8 + 8 + 3 + 2 +
  36 + 5 = 80, con 5 de margen sobre 85, y el techo de 85 con su motivo.
- Nada más cambia.

## Comprobación que la sostiene

- El dato de la muerte: run 33998592213, paso 9 de 23:24:51 a 23:55:03
  («The action has timed out», `duration_ms=1809925`), procesos huérfanos al
  terminar: `bun`, `claude`, `bash`, `pwsh`, `tail`, `uv`, `pytest`.
- La restricción del contador: cabecera de
  `.github/workflows/contador-siete-dias.yml` («NO SUBIR DE 85») y
  `tests/automation/test_contador_de_siete_dias.py`.
- Guardianes estructurales del corrector y del contador en verde con los
  números nuevos, sin cambiar su aritmética (resultado transcrito en el
  cuerpo de la PR).
- Cadena completa como una sola invocación sobre el head definitivo: código
  de salida transcrito en el cuerpo de la PR.
- Lo que NO se ha medido: la ronda relanzada de #545 (el criterio en vivo de
  arriba). Se registra en la bitácora cuando ocurra.

## Consecuencias

- Una ronda del corrector puede costar hasta 36 minutos de runner en vez de
  30; solo las que lo necesiten los usan. El techo de 85 del contador queda
  intacto.
- Deuda 8 queda como está, y gana una salida concreta: la opción 4 (la
  validación como paso del workflow, no del agente) es la ficha siguiente de
  esta familia, para decisión del propietario.
- El comentario del workflow vuelve a decir la verdad de su aritmética.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».

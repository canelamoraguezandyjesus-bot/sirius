# ADR-140 — El corrector firma su run y demuestra cada mutación

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el
  propietario — con su autorización nocturna del 04-09-2026, la ejecuto
  yo si Quality y mi revisión están en verde. Cauce ADR-002, opción 2
  (aunque este cambio no toca `.github/**`: vive en scripts/ y en el
  prompt del corrector, igual que ADR-135).

## Contexto y problema

Es el cambio 1 del papel de la mina v2 para el propietario
(`docs/audits/mina-2026-09-cambios-para-el-propietario.md`), con dos
mitades:

- **La demostración.** «Prueba que no puede fallar» fue la familia de
  defecto más extendida de la ola de criticidad (7 hallazgos en 4 de 8
  encargos, §4 del informe). Hoy el corrector dice «corregido y las
  pruebas pasan», y eso no distingue una prueba que fija el arreglo de
  una que pasaría igual sin él. El prompt ya exige (ADR-135) evidencia
  fresca; faltaba exigir LA evidencia que importa: la mutación vista
  fallar, por observación corregida.
- **La firma.** Las 3 muertes del corrector en la ola (§5 del informe) y
  la 4.ª del 04-09 (C1, ciclo 3) no dejaron su run citado: atribuir cada
  corrección o muerte a su ejecución exigía correlación temporal (hueco
  2 del informe). Los marcadores `precheck` ya llevan run id; el `FIXED`
  no.

## Criterio de parada (escrito ANTES de decidir)

- Si la firma del marcador rompiera algún lector (los censos primero):
  parar. Censo hecho antes de tocar: `_STOP_MARKER_RE`
  (mirror_projection) solo casa FAILED_SAFELY/USAGE_LIMIT/blocked/
  precheck — un `FIXED:<head>:<run>` no puede casarlo; ningún guion ni
  módulo del motor parsea `corrector:FIXED` posicionalmente; el único
  `grep -F` de marcador completo es el de CHECKS_UNRELATED, que no se
  toca.
- La firma es SOLO del corrector: si exigiera cambiar la forma del
  marcador del implementador (`READY_FOR_REVIEW`), parar — movería su
  deduplicación por head, que no es asunto de este cambio.

## Decisión

1. `scripts/automation/sirius_apply_verdict.sh`: cuando `ROLE` es
   `corrector`, el marcador FIXED pasa de
   `sirius-verdict:corrector:FIXED:<head>` a
   `sirius-verdict:corrector:FIXED:<head>:<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>`
   (con degradación a `manual-1` fuera de Actions). Consecuencia
   deliberada: la deduplicación de comentario pasa de por-head a
   por-run — dos correcciones reales sobre el mismo head quedan ambas
   visibles y atribuidas, que es exactamente la intención.
2. `scripts/automation/prompts/corrector.md`: viñeta nueva junto a las
   de ADR-135 — el `summary` de cada CORRECCION_APLICADA incluye, por
   observación cuya corrección cambió código o pruebas, la mutación con
   la que se vio fallar la prueba que la fija (qué línea cambió y a qué,
   y la primera línea del fallo de pytest); las observaciones solo
   documentales declaran en su lugar el comando que verificó el texto.

## Comprobación que la sostiene

- Rojo previo, visto fallar (ADR-001): las dos pruebas nuevas de la
  firma (`test_corrector_fixed_firma_el_marcador_con_su_run`,
  `test_corrector_fixed_sin_entorno_de_run_firma_manual`) fallaron
  contra el guion sin firma — `2 failed, 1 passed` con la adversaria
  (`test_implementer_ready_no_cambia_de_forma_con_entorno_de_run`) en
  verde, que es la mutación natural en las dos direcciones: sin el
  cambio fallan las nuevas; un cambio que firmara también al
  implementador haría fallar la adversaria.
- Tras el cambio: `tests/automation/test_sirius_apply_verdict.py`
  45/45 en verde (las 42 previas intactas: ninguna fijaba la forma
  exacta del marcador FIXED).
- La mitad del prompt no es verificable por prueba (es una instrucción
  al agente, como las de ADR-135): su medición es la misma que la de
  ADR-135 — los dos próximos encargos, en la bitácora, mirando si los
  CORRECCION_APLICADA traen sus mutaciones.
- Validaciones obligatorias completas sobre el árbol final, con códigos
  de salida verificados, citadas en la PR.

## Consecuencias

- Surte efecto en la primera corrección tras la fusión (el prompt y el
  guion se leen de `main` en cada run).
- Un corrector muerto sigue sin firmar nada (muere antes de publicar);
  lo que la firma da es el contraste: el FIXED anterior y el disparo de
  la ronda acotan qué run murió, sin correlación temporal.
- El papel del propietario queda ejecutado en su cambio 1; su cambio 2
  quedó rechazado por ADR-139. El papel entero queda superado por estos
  dos ADR.

## Alternativas descartadas y por qué

- **Firmar también al implementador:** movería la deduplicación de
  READY_FOR_REVIEW sin necesidad que lo justifique; la adversaria lo
  fija.
- **Publicar la mutación como campo estructurado del veredicto JSON:**
  cambiaría el contrato del veredicto y sus validadores — más superficie
  para el mismo efecto; la viñeta del prompt logra lo mismo por la vía
  que ADR-135 ya abrió.
- **Un guardián que rechace CORRECCION_APLICADA sin mutación:** medir
  primero (como G1/G2): si tras dos encargos los resúmenes vienen sin
  mutación pese al prompt, ese guardián se propone con su medición.

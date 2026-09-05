# ADR-145 — La validación obligatoria es una sola invocación del script de comprobación

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario o
  por su operador bajo la autorización vigente del 05-09. No toca `.github/**`:
  vive en dos prompts de scripts/automation y en sus guardianes.

## Contexto y problema

El 05-09, dos ciclos del motor perdieron una ronda entera cada uno por la misma
causa: el corrector validó con los cuatro comandos por separado (`ruff format
--check`, `ruff check`, `mypy`, `pytest`) y el revisor lo detuvo citando
AGENTS.md («Ejecuta `scripts/check.ps1` antes de entregar»), porque partir la
suite arranca procesos y juegos de fixtures distintos y no demuestra que el
script obligatorio pase entero (incidencia #537, ronda 2, CODEX-001; incidencia
#541, vuelta 4, CODEX-001). En #541 el corrector llegó a partir `pytest` en dos
tandas «para caber en el tiempo», y esa captura tampoco valía.

La raíz NO es desobediencia del modelo: **los prompts del implementador y del
corrector enumeraban literalmente los cuatro comandos sueltos como «las
validaciones obligatorias»** (implementer.md, corrector.md), en contradicción
con la regla de AGENTS.md que los revisores hacen cumplir. El agente obedecía a
su prompt y el revisor a su contrato; la ronda perdida era el coste del
desacuerdo entre ambos textos.

El mismo día, el ciclo de #541 perdió otras dos vueltas (rondas 3 y 6) por un
segundo hueco del prompt del corrector: tras commitear una corrección, el
cuerpo de la PR quedaba describiendo el head anterior — cifras superadas
declaradas como actuales y SHAs viejos señalados como «el head actual» — y el
cuerpo de la PR es el documento con el que se decide la fusión. El prompt ya
exigía actualizar «el ADR y toda evidencia» dependiente (ADR-135), pero el
cuerpo de la PR no está en un fichero del árbol y quedaba fuera de esa lectura.

Un análisis externo independiente del mismo día (informe entregado por el
propietario) llegó a la primera de estas dos conclusiones por su cuenta, con
los mismos ejemplos.

## Criterio de parada (escrito ANTES de decidir)

- Si la regla vigente de AGENTS.md no exigiera de verdad el script único —es
  decir, si «Ejecuta `scripts/check.ps1` antes de entregar» admitiera la
  lectura de comandos equivalentes por separado y los revisores la estuvieran
  sobreinterpretando—, el cambio correcto sería en la doctrina del revisor, no
  en los prompts de los agentes: parar y replantear.
- Si los guardianes nuevos no se pudieran ver fallar contra los prompts
  vigentes (rojo previo), no hay evidencia de que fijen nada: parar.
- Cero cambios de comportamiento del motor: si el diseño exigiera tocar
  workflows, agregadores o guiones de veredicto, esto ya no es una alineación
  de prompts y necesita su propio encargo.

## Opciones consideradas

1. Alinear los prompts con AGENTS.md: la validación obligatoria es UNA
   invocación de `pwsh -File scripts/check.ps1` sobre el árbol final, con su
   código de salida transcrito; y el corrector reconcilia el cuerpo de la PR
   con el head vigente tras cualquier commit. Guardianes textuales para ambas.
2. Cambiar AGENTS.md para admitir los comandos por separado.
3. Dejarlo como está y pagar la ronda cada vez que ocurra.

## Decisión

**Opción 1.** Tres piezas, ninguna toca `.github/**`:

- `scripts/automation/prompts/implementer.md` y
  `scripts/automation/prompts/corrector.md`: la viñeta de validaciones deja de
  enumerar los cuatro comandos como forma de validar y pasa a exigir **una sola
  invocación de `pwsh -File scripts/check.ps1` sobre el árbol final, con su
  código de salida transcrito en la evidencia**; los cuatro comandos se citan
  solo como lo que el script ejecuta por dentro, con la prohibición explícita
  de sustituirlo por ellos y de partir `pytest` en tandas.
- `scripts/automation/prompts/corrector.md`, además: tras CUALQUIER commit
  nuevo, **el cuerpo de la PR se reconcilia con el head vigente en el mismo
  turno** — ninguna frase del cuerpo puede afirmar como actual un head
  superado ni un recuento que el ADR del head desmienta; la remisión estable
  es a la sección de comprobación del ADR, sin clavar SHAs como «actual».
- `tests/automation/test_prompts_de_rol.py`: dos guardianes textuales nuevos —
  los dos prompts de agentes que validan nombran el script único y ninguno
  vuelve a presentar los comandos sueltos como validación; el corrector lleva
  la regla de reconciliación del cuerpo de la PR.
- **El implementador se versiona por H-28, no se edita in situ**: su prompt
  está anclado por sha256 en `scripts/automation/prompts/manifiesto.json`
  (`rol@N` significa UN texto, para siempre), así que el texto nuevo vive en
  el fichero nuevo `scripts/automation/prompts/implementer-v3.md`, con filas
  `implementer@3` en los dos carriles del manifiesto (ejecución → el fichero
  nuevo; revisión → `reviewer-v2.md`, igual que `@2`), la versión del perfil
  subida a 3 (`docs/implementation/work_engine/perfiles/implementer.yml`, con
  `procedimiento_ref` apuntando al fichero nuevo) e `implementer.md` intacto
  en sus bytes de `@1`/`@2`. Los encargos ya despachados con `@2` conservan su
  texto congelado; los nuevos nacen con `@3`. El corrector NO está en el
  manifiesto (su workflow carga `corrector.md` directamente, el mismo cauce
  que usó ADR-135), así que su edición es in situ, como entonces.
- Dos arneses de prueba se hicieron fieles de paso, cada uno con su porqué en
  el propio fichero: el guardián nuevo lee del manifiesto cuál es el prompt
  vigente del implementador (cuando nazca `@4` lo seguirá solo), y el fixture
  de `tests/engine/test_worker_request.py` escribe `Perfil: rol@N` leyendo la
  versión del PERFIL —como el despachador real— en vez de clavar `@1` a mano,
  dejando pasar los perfiles desconocidos para que sea el guión quien falle.

Por qué no la 2: la exigencia del script único es la correcta — un solo
proceso, un solo juego de fixtures, un solo código de salida — y los revisores
llevan dos ciclos haciéndola cumplir con razón; debilitar AGENTS.md para
convalidar el desajuste sería arreglar el termómetro.

## Comprobación que la sostiene

- Rojo previo, visto fallar (ADR-001): los dos guardianes nuevos contra los
  prompts vigentes de main (`21eefcd`) —
  `test_los_prompts_que_validan_exigen_el_script_de_comprobacion_unico`
  (parametrizado sobre implementer.md y corrector.md) y
  `test_el_corrector_reconcilia_el_cuerpo_de_la_pr_tras_cada_commit` —
  fallaron con «3 failed, 40 passed, 9 skipped» en
  `tests/automation/test_prompts_de_rol.py`; la primera línea:
  `AssertionError: scripts/automation/prompts/implementer.md ya no exige el
  script de comprobación único: el agente validará con comandos sueltos y el
  revisor lo parará citando AGENTS.md`. Tras editar los dos prompts:
  «43 passed, 9 skipped».
- Mutaciones vistas fallar, una por dirección, cada una tumbando SOLO su
  guardián: (a) devuelta la viñeta del corrector a la enumeración de comandos
  sueltos → «1 failed» exacto:
  `FAILED tests/automation/test_prompts_de_rol.py::test_los_prompts_que_validan_exigen_el_script_de_comprobacion_unico[corrector.md]`;
  (b) retirada la frase «en el mismo turno» de la regla de reconciliación →
  «1 failed» exacto:
  `FAILED tests/automation/test_prompts_de_rol.py::test_el_corrector_reconcilia_el_cuerpo_de_la_pr_tras_cada_commit`.
  Árbol restaurado: «43 passed, 9 skipped».
- Las medidas de arriba se tomaron sobre el árbol con los prompts editados
  in situ, ANTES del versionado H-28; el versionado (fichero nuevo, filas
  `@3`, perfil a 3) puso en rojo cinco guardianes del manifiesto y de la
  proyección —exactamente su trabajo— y sobre el árbol final los tres
  ficheros afectados dan «75 passed, 10 skipped»
  (`test_prompts_de_rol.py` + `test_resolver_prompt.py` +
  `test_worker_request.py`), con los dos guardianes nuevos dentro.
- Validación obligatoria completa sobre el árbol final: el entorno del
  operador no tiene `pwsh` (exit 127 comprobado), así que se ejecutó el
  encadenado EXACTO de `scripts/check.ps1` en UNA sola invocación de
  `bash -e` —mismo orden, misma parada en el primer fallo, un único código
  de salida, `pytest` entero sin partir— y Quality revalida en CI con el
  script real. El resultado exacto queda transcrito en la PR que introduce
  este ADR.
- `git diff --check`: sin salida. Cero ficheros de `.github/**` en el diff.

## Consecuencias

- El agente y el revisor leen por fin la misma regla: la clase de ronda
  «evidencia partida» (dos hoy) deja de fabricarse por diseño.
- La clase «cuerpo de la PR desfasado del head» (dos vueltas hoy en #541)
  queda legislada donde nace: el turno del corrector que commitea.
- El coste de validar sube ligeramente para el corrector en correcciones
  minúsculas (el script corre entero, ~8 min), exactamente el coste que los
  revisores ya estaban imponiendo a posteriori con una ronda entera (~45 min).
- Los prompts de revisión no cambian: describen Quality, no ejecutan
  validaciones.

## Alternativas descartadas y por qué

- **Debilitar AGENTS.md (opción 2):** convalida el desajuste rompiendo la
  propiedad que lo motiva (un proceso, unas fixtures, un código de salida).
- **No hacer nada (opción 3):** la ronda perdida reaparece cada vez; hoy
  fueron dos en un día con la regla mordiendo en ciclos distintos.
- **Legislarlo solo en la bitácora:** la bitácora registra; los prompts
  gobiernan. Una regla que el agente no lee en su prompt no existe para él
  (la lección exacta de este ADR).

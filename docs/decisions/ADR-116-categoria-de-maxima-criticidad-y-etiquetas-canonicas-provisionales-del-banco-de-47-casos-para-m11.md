# ADR-116 — Categoría de máxima criticidad y etiquetas canónicas provisionales del banco de 47 casos para M11

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

M11 (incidencia #471, WI-20260831-054212) cablea M9/M10 en `composition_root`
detrás de la puerta de D7 punto 6, mide RNF-003 con el paquete completo
activo, ejecuta el banco de 47 casos contra ese paquete completo (con dobles
deterministas) como evidencia adicional, y mide la coincidencia del
etiquetado automático de Ollama contra el banco (D7 punto 6, SIRIUS-ARQ-0.2
§6.1/§6.5). Tres de esos cuatro puntos necesitan un dato que no existe en
este repositorio:

1. **La categoría de máxima criticidad** que el candado de §6.3 protege
   siempre. §6.3 dice que es "la categoría de máxima criticidad del
   vocabulario cerrado del banco (§6.5)", pero ni la Arquitectura Técnica 0.2
   ni el banco fijan cuál de las siete categorías provisionales de
   `composition_root._CATEGORY_VOCABULARY` es esa.
2. **Una categoría canónica por elemento del banco de 47 casos**, necesaria
   para (a) poblar `category` en el pipeline íntegro que M11 mide (§6.5,
   párrafo de M11 en §8) y (b) servir de "etiquetas canónicas del banco"
   contra las que D7 punto 6 compara el resultado del clasificador
   (`CategoryClassifierPort`/`OllamaCategoryClassifierAdapter`, §6.1).
   `evidence_bank_47_casos.json` no trae ningún campo de categoría, ni a
   nivel de caso ni a nivel de item del canon —comprobado abajo, sobre el
   fixture tal como existe hoy en `main`, con el mismo tramo del examen
   (incidencias #457-#469) ya fusionado.

Esta incidencia es el segundo intento de M11 (el primero, incidencia #453,
se cerró antes del tramo del examen): la premisa de este ADR —que el fixture
no trae categoría— se ha vuelto a comprobar aquí, sobre el `main` actual,
antes de reutilizar la decisión.

## Criterio de parada (escrito ANTES de decidir)

Si fijar la categoría de máxima criticidad o las etiquetas canónicas del
banco exigiera: (a) inventar una taxonomía nueva (ninguna de las dos
decisiones añade una categoría al vocabulario cerrado de
`composition_root._CATEGORY_VOCABULARY`, ambas solo lo reutilizan); (b) que
la elección apareciera en documentación canónica o de producto como si fuera
la oficial (ambas quedan confinadas a `composition_root.py` y a un fichero
de fixture de pruebas nuevo, nunca a `docs/canonical/`); o (c) juicio
subjetivo por elemento que no se pueda reproducir de una regla escrita —
paro y emito `BLOCKED_BY_DECISION`. Si en cambio (a) la categoría de máxima
criticidad puede fijarse como una constante confinada, ya precedida por los
propios dobles de prueba de M10 (`tests/integration/test_context_builder.py`,
que ya usan `"salud"` como categoría de máxima criticidad en sus dobles
desde antes de este ADR), y (b) las etiquetas canónicas del banco pueden
derivarse de una regla mecánica, determinista y escrita sobre el texto de
cada item —nunca una decisión manual, item por item, no reproducible— sigo
adelante sin bloquear M11.

## Opciones consideradas

**Para la categoría de máxima criticidad:**

1. Bloquear M11 con `BLOCKED_BY_DECISION` hasta que el propietario la fije.
2. Fijar una constante provisional en `composition_root.py`, con el mismo
   patrón que ya usa `_CATEGORY_VOCABULARY`/`_CATEGORY_CLASSIFIER_MODEL`.

**Para las etiquetas canónicas del banco de 47 casos:**

1. Bloquear M11 con `BLOCKED_BY_DECISION` hasta que el propietario las porte
   desde `evidence/adr001-spikes` (si es que existen allí) o las fije a mano.
2. Asignar una categoría por elemento a mano, uno por uno, por juicio del
   implementador.
3. Derivar la categoría de cada elemento del banco mecánicamente, con una
   regla de coincidencia de palabras clave sobre `text` — el mismo principio
   determinista que `sirius.domain.relevance.category_matches_query` ya usa
   en producción, aplicado aquí sobre el contenido del item en vez de sobre
   el texto de la consulta —, documentada íntegra en este ADR y confinada a
   un fichero de fixture de pruebas nuevo, nunca al banco portado
   `evidence_bank_47_casos.json` (D1: "se porta sin modificarse").

## Decisión

**Categoría de máxima criticidad: `"salud"`.** Reutiliza, sin inventar nada
nuevo, el mismo valor que M10 ya eligió para sus dobles de prueba
(`tests/integration/test_context_builder.py`) antes de que este ADR
existiera — no es una elección nueva de M11, es hacer explícita y confinada
a `composition_root._MAX_CRITICALITY_CATEGORY` una elección que ya estaba
implícita en el código de pruebas de un encargo anterior. Sustituible por
una sola constante el día que exista una taxonomía real portada desde el
banco.

**Etiquetas canónicas del banco: opción 3, regla mecánica documentada.**
`tests/acceptance/fixtures/evidence_bank_47_casos_categorias_canonicas.json`
(nuevo, nunca modifica `evidence_bank_47_casos.json`) asigna, a cada uno de
los 97 items del canon, una categoría del vocabulario de siete
(`trabajo`, `personal`, `salud`, `finanzas`, `proyecto`, `aprendizaje`,
`otros`), calculada por esta regla, en este orden de prioridad estricto (la
primera categoría cuya lista de palabras clave aparece, como subcadena
insensible a mayúsculas, en el `text` del item gana; si ninguna aparece, la
categoría es `otros`):

| Orden | Categoría | Palabras clave (subcadena, minúsculas) |
|---|---|---|
| 1 | `salud` | salud, médic, medic, hospital, enfermed, dolor, vacuna, clinic, clínic |
| 2 | `finanzas` | presupuesto, €, nómina, nomina, pago, factura, descuento, coste, sueldo, salario, gasto, ahorr |
| 3 | `aprendizaje` | aprend, curso, estudi, formaci, clase, " leer ", libro |
| 4 | `personal` | familia, amig, mascota, pareja, hobby, vacacion, viaje, coche, vuelo |
| 5 | `proyecto` | proyecto, expediente, entregable, hito, alcance, plataforma de despliegue, atlas |
| 6 | `trabajo` | reunión, reunion, oficina, responsable, informe, operaciones, calidad, proveedor, cliente, empresa, compras, turno, revisión, revision, publicaci, almacén, almacen, logística, logistica, documental, control de versiones, nómina, contrato, mantenimiento, identificador interno, plataforma, postgresql, autorización, autorizacion |
| 7 (fallback) | `otros` | — |

Resultado, contado sobre los 97 items: `trabajo` 42, `proyecto` 21, `personal`
16, `otros` 10, `finanzas` 7, `salud` 1, `aprendizaje` 0 — refleja el corpus
real, mayoritariamente corporativo (proyectos, decisiones, reuniones,
logística), con un único item genuinamente de salud (`MEM-010`, "Dato
sensible de salud del titular del proyecto") — el único que cae en la
categoría de máxima criticidad, coherente con que D7/§6.3 la describan como
protegida siempre.

Ninguna de las dos decisiones toca `docs/canonical/`, la Definición de
Producto ni la Arquitectura Técnica: ambas viven en código de producción
provisional (`composition_root.py`) o en un fichero de fixture de pruebas
nuevo, con esta misma tabla como su única fuente de verdad reproducible.

## Comprobación que la sostiene

- `python3 -c "import json; d=json.load(open('tests/acceptance/fixtures/evidence_bank_47_casos.json')); print({k for i in d['items'] for k in i})"`
  sobre el `main` actual (con el tramo del examen #457-#469 ya fusionado)
  confirma que ningún item trae una clave de categoría: `{'confirmacion',
  'id', 'criticidad', 'validez', 'kind', 'ejes_p2', 'disponibilidad', 'text',
  'project'}` — 97 items, el mismo hallazgo que un ADR equivalente del primer
  intento de M11 (incidencia #453) ya había documentado, vuelto a comprobar
  aquí porque el fixture y el corpus podían haber cambiado entre ambos
  intentos (no cambiaron: el `text` de los 97 items es idéntico byte a byte
  al del primer intento).
- `grep -n 'max_criticality_category="salud"' tests/integration/test_context_builder.py`
  confirma las ocurrencias anteriores a este ADR.
- La tabla de conteos de arriba se generó ejecutando la función de
  clasificación exactamente como queda escrita en la tabla, sobre
  `evidence_bank_47_casos.json`, y se volcó a
  `tests/acceptance/fixtures/evidence_bank_47_casos_categorias_canonicas.json`;
  `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::test_las_etiquetas_canonicas_se_recalculan_byte_a_byte`
  recalcula la regla en Python puro sobre el `text` de cada item y compara
  el resultado, byte a byte, contra el fixture — para que la tabla de este
  ADR y el fixture nunca puedan divergir en silencio.
- `uv run pytest -q` (suite completa, ver PR de M11 para el conteo exacto).

## Consecuencias

- Positivas: M11 no queda bloqueado por un dato ausente que dos encargos
  anteriores (M9, M10) ya habían tenido que sortear sin haberlo hecho
  explícito; el punto de sustitución cuando exista una taxonomía real
  portada desde el banco es mínimo (una constante y un fichero de fixture).
- Negativas/riesgos: tanto la categoría de máxima criticidad como las
  etiquetas canónicas del banco son responsabilidad de este ADR, no del
  propietario ni de D7. La cifra de coincidencia del etiquetado (D7 punto 6)
  y la medición del «paquete completo» que M11 mide y publica quedan, en
  consecuencia, condicionadas a esta regla mecánica provisional — el umbral
  que el propietario registre en `docs/evolution/STATUS.md` a la vista de
  esa cifra debe leerse con esa condición en mente hasta que exista una
  taxonomía real portada desde el banco de evidencia.

## Alternativas descartadas y por qué

Bloquear con `BLOCKED_BY_DECISION` (opción 1 en ambos casos) se descartó
porque ninguna de las dos decisiones inventa una taxonomía con intención de
producto ni aparece en documentación canónica: la Arquitectura Técnica 0.2
ya afirma que "ninguno de estos seis encargos queda bloqueado a la espera de
una decisión del propietario" (§8), y bloquear aquí habría contradicho esa
afirmación sin una razón nueva que la sostenga. Asignar las etiquetas del
banco a mano, item por item (opción 2 de la segunda decisión), se descartó
porque no es reproducible desde una regla escrita — cualquier revisión
futura no podría distinguir una elección deliberada de un error de tecleo, y
la Definición de Producto exige que las cifras medidas contra este banco
sigan siendo comparables entre encargos (§6.1 punto 1).

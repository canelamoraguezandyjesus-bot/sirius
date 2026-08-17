# ADR-029 — Calcular el número de un ADR como el máximo existente más uno

- Estado: PROPUESTO
- Fecha: 2026-08-17
- Aprobación: pendiente; en este repositorio, la fusión de la PR por el propietario

Este ADR es además la **nota de arranque** de la rama `herramienta/skill-adr`
(ADR-001): se escribió y se confirmó antes del primer cambio de código, y su
criterio de parada se decidió antes de ver ningún resultado.

## Contexto y problema

El registro tiene hoy dos ADR con el mismo número:

- `ADR-016-el-auditor-se-lanza-por-etiqueta-y-no-escribe-nunca.md`
- `ADR-016-el-estado-se-lee-de-main-no-de-la-rama.md`

y los números 017 y 018 no se usaron nunca. El defecto ya ocurrió; no es
hipotético. La causa es que el número siguiente se elige a ojo leyendo un
listado, y dos ramas paralelas leen el mismo listado.

Un hueco en la numeración es inofensivo: nadie busca un ADR por su posición.
Un número repetido no lo es, porque dos decisiones distintas pasan a citarse
igual y las referencias cruzadas dejan de resolver.

### ¿Puede el sitio del arreglo observar el fallo que arregla?

Sí. El conflicto está determinado por completo por los nombres de archivo de
`docs/decisions/`, y el guion los lee directamente. No se reconstruye por
fuera la semántica de ningún otro sistema, que es la raíz de los quince
defectos de la PR #139: allí decidir desde el TEXTO de un comando si haría
`push` exigía un intérprete de shell entero. Aquí el dato es el directorio.

### Qué NO garantiza esto (escrito antes de implementar)

- **No es una puerta.** No impide crear un ADR a mano con cualquier número.
  Quien no invoque la skill no queda cubierto por ella.
- **No coordina ramas paralelas.** El guion solo ve el árbol local. Dos ramas
  abiertas a la vez sobre el mismo `main` pueden obtener ambas el mismo número
  y colisionar al fusionar. Es exactamente el modo en que nacieron los dos
  ADR-016, y el guion **no lo cierra**: cerrarlo exigiría consultar ramas y PR
  abiertas en GitHub, es decir, red, que la frontera de confianza de ADR-012 y
  la lista `deny` de `settings.json` excluyen a propósito.
- **No corrige el pasado.** No renumera los ADR-016 ni rellena 017 y 018.
- **No juzga el contenido.** Copia la plantilla; no comprueba que el ADR traiga
  criterio de parada ni comprobación.

## Criterio de parada (escrito ANTES de decidir)

Se para y se pide decisión al propietario si ocurre cualquiera de estas tres:

1. **La normalización del título pide reglas de una en una.** Si generar el
   nombre acaba exigiendo una regla por cada carácter que aparece —una tilde,
   luego una eñe, luego un paréntesis, luego unas comillas—, es la familia
   «reconstruir por fuera una semántica ajena» de la PR #139 con otro disfraz.
   A la segunda regla añadida por un caso suelto se para, y el alcance se
   reduce a normalizar lo evidente y **pedir el slug al humano** cuando el
   resultado no coincida con lo esperado.
2. **Dos rondas de revisión con defectos de la misma familia** (ADR-001, sin
   excepción).
3. **El guion necesita red, estado persistente o escribir fuera de
   `docs/decisions/`.** Cualquiera de las tres cambia la naturaleza de la pieza
   y exige decisión del propietario.

## Opciones consideradas

1. **Máximo existente + 1.** Un solo número posible en cada momento; los
   huecos quedan como cicatriz histórica.
2. **Primer hueco libre.** Reaprovecha 017 y 018 y mantiene la secuencia densa.
3. **Sin número: solo título.** Elimina el problema de raíz.

## Decisión

Se toma la opción 1: **el siguiente número es el máximo existente más uno, y
los huecos históricos no se reutilizan nunca**.

El nombre del archivo es `ADR-NNN-<título-normalizado>.md`, con `NNN` a tres
dígitos y el título en minúsculas, sin diacríticos y con guiones por
separador, que es el convenio que ya siguen los 28 ADR del registro.

## Comprobación que la sostiene

Pruebas en `tests/automation/test_siguiente_adr.py`, cada propiedad verificada
**por mutación en las dos direcciones**: se rompe el guion a propósito y se
comprueba que la prueba correspondiente falla.

Mutaciones planificadas, escritas antes de ejecutarlas:

- devolver el primer hueco libre en vez de máximo+1 → debe fallar la prueba de
  «no se reutilizan huecos»;
- no quitar los diacríticos al normalizar → debe fallar la prueba de convenio;
- permitir sobrescribir un archivo existente → debe fallar la prueba de no
  destrucción;
- mirar solo el primer archivo del directorio → debe fallar la prueba del
  máximo.

### Resultados reales

32 pruebas en verde (`uv run pytest tests/automation/test_siguiente_adr.py
tests/automation/test_registro_de_decisiones.py`). Las siete mutaciones se
aplicaron una a una sobre el árbol confirmado y se revirtieron con
`git checkout --`:

| Mutación | Prueba que debía caer | Resultado |
|---|---|---|
| primer hueco libre en vez de máximo+1 | huecos nunca se reutilizan | **falla** (3 pruebas) |
| no quitar diacríticos | convenio del registro | **falla** (2 pruebas) |
| quitar la guarda de sobrescritura | no destruir un ADR | **falla** |
| mirar solo el primer archivo | el máximo es de todo el directorio | **falla** (5 pruebas) |
| crear un `ADR-020` duplicado a mano | guardiana del registro | **falla**, y nombra los dos archivos |
| archivo con mayúsculas en el título | convenio de nombres | **falla** |
| quitar `# ADR-NNN` de `PLANTILLA.md` | marcadores de la plantilla real | **falla** |

**Un hallazgo que cambió el diseño de una prueba.** La mutación de la guarda de
sobrescritura destapó que la prueba original —crear un ADR sobre otro ya
existente— pasaba **en vacío**: como el número es máximo+1, el nombre generado
no puede chocar nunca con un archivo presente, así que la guarda es
inalcanzable por el camino normal y borrarla no rompía nada. Es la cuarta forma
del patrón «pruebas que nacen vacuas». Se rehízo forzando el fallo del cálculo
con `monkeypatch`, que es lo único que ejercita de verdad una segunda línea de
defensa; así mutada, la prueba sí cae.

### Lo que estas pruebas NO dicen

En esta máquina (Windows) el árbol completo trae **15 fallos y un error de
mypy previos**, en `test_sirius_repair_workflow.py`, `test_spike_i3_durability.py`,
dos módulos de GUI y `experiments/work_engine_spike_i3/durable_journal.py`
(`signal.SIGKILL` no existe en Windows). Se comprobó que son ajenos a este
trabajo ejecutando los mismos módulos sobre `origin/main` en HEAD separado:
mismos 15 fallos, 126 pasadas; en esta rama, mismos 15 fallos y 158 pasadas.
La diferencia de 32 es exactamente el número de pruebas añadidas aquí.

## Consecuencias

- La numeración deja de depender de que alguien lea bien un listado.
- Los huecos 017 y 018 quedan vacíos para siempre. Es el precio de que el
  número sea función únicamente del máximo, y se acepta.
- Aparece `tests/automation/test_registro_de_decisiones.py`, que recorre
  `docs/decisions/` y falla si dos archivos comparten número. Corre con el
  resto de la batería, se haya usado la skill o no: el guion quita fricción,
  **la prueba es la garantía**, y conviene no confundirlas.
- Esa prueba tolera **una** excepción, fijada nombre por nombre: el par
  `ADR-016` que ya existía. Corregirlo afectaría a una veintena de referencias
  repartidas por workflows, pruebas y documentos —ninguna de las cuales dice
  cuál de los dos documentos cita—, y es decisión del propietario, no de este
  ADR. Cuando se corrija, la prueba fallará y pedirá que se quite la excepción,
  que es el aviso que se quería.
- Sigue sin ser imposible la colisión entre dos ramas abiertas a la vez: la
  prueba la detecta al fusionar la segunda. Es tarde, pero es detectable; hoy
  no lo era en absoluto.

## Alternativas descartadas y por qué

- **Primer hueco libre.** Rellenar 017 y 018 hoy haría que un mismo número
  apuntara a decisiones distintas según la fecha del clon, y rompería las
  referencias de cualquier documento que ya citara esos huecos como vacíos. La
  densidad de la secuencia no vale ese riesgo.
- **Sin número, solo título.** Elimina el problema, pero invalida las
  referencias de los 28 ADR existentes y de la propia `PLANTILLA.md`. El coste
  de migración supera con mucho al del defecto que corrige.
- **Consultar GitHub para reservar el número.** Cerraría la colisión entre
  ramas paralelas, pero mete red en una herramienta local y contradice ADR-012.
  Queda fuera de alcance; si algún día se quiere, es decisión del propietario.

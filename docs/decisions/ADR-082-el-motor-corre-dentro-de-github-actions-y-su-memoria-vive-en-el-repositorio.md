# ADR-082 — El motor corre dentro de GitHub Actions y su memoria vive en el repositorio

- Estado: PROPUESTO
- Fecha: 2026-08-24
- Aprobación: fusión de la PR por el propietario
- Contexto: decisión I4, incidencia #270, elegida por el propietario el 23-08-2026
- Relacionadas: **ADR-019** (a la que enmienda), ADR-020, ADR-055 y ADR-064 (cuyas
  premisas revisa), ADR-026 (el diario), ADR-057 (un run observa otro run),
  ADR-002 (la automatización no edita `.github/**`), ADR-032 (el número de un ADR),
  ADR-001 (disciplina de evidencia)

## Contexto y problema

El motor de trabajo está construido y probado, y **no está en el circuito**. Se
midió al implementar D1b y se verificó de forma independiente: ningún workflow ni
guion del repositorio invoca `sirius_engine`. Quien lleva Sirius hoy es la vía
GitHub.

Eso bloquea la vertical entera. El contador de siete días del contrato §11.2 no
puede contar porque no hay estado del motor que comparar, y el propio contrato ya
lo decía —«el contador no puede empezar antes de que el motor lleve el ciclo por
sí mismo»—; lo que no se había comprobado es que esa precondición estuviera
incumplida.

Enchufarlo exige decidir dónde corre el motor y dónde sobrevive su memoria entre
ejecuciones. El propietario eligió el 23-08-2026 la **opción A** de #270: dentro
de GitHub Actions, con el diario como fichero versionado del repositorio.

**El problema que resuelve este ADR no es esa elección —ya está tomada— sino que
el árbol la contradice en 58 sitios de 20 ficheros**, incluidos dos ADR aprobados,
el contrato operativo, el plan de implementación y la cláusula de gobierno que
autoriza al motor a existir.

### Dos errores en el documento con el que se decidió

Se dicen aquí porque el propietario decidió con ellos delante, y porque un ADR que
los omitiera heredaría la afirmación falsa.

**Primero: la justificación de concurrencia era falsa.** La incidencia #270 afirma
que «el diario ya es append-only con checksum SHA-256 por registro e idempotencia
por clave (ADR-026), así que reintentar tras un rebase es seguro por construcción,
no por suerte». **Se retira.** El código dice lo contrario:

```python
# src/sirius_engine/adapters/durable/store.py:88-96
self._idempotency_seen: dict[_IdempotencyKey, WorkItem | Run] = {}
self._next_sequence = 1
self._load()
```

Ambos viven **en memoria** y se pueblan una sola vez al construir el almacén; su
propia documentación lo dice: «reproduce el diario **una sola vez**, al
construirse». Dos runners son dos procesos que no se ven. Y `replay()`, en
`journal.py`, **no menciona `sequence` ni una vez**: un diario con secuencias
duplicadas se absorbe sin queja. El checksum protege cada registro por dentro; no
protege de dos escritores.

**Segundo: no se puso delante que ADR-019 ya había descartado algo parecido.** Su
opción 1 —«evolucionar la automatización GitHub actual hasta que sea el motor»— se
descartó porque «el observador seguiría dentro de lo observado, y GitHub seguiría
siendo la única memoria».

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #270 antes de tocar ningún documento
([comentario 5389401159](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/270#issuecomment-5389401159)):

**(a)** Si enmendar exige **reescribir el cuerpo de un ADR aprobado**, se para. El
repositorio ya tiene su mecanismo —la plantilla declara `SUPERADO por ADR-NNN`— y
reescribir historia aprobada sería inventarse otro.

**(b)** Si aparece **una contradicción que no se puede resolver sin una decisión
nueva del propietario**, se para y se le pregunta. No se elige por él y se explica
después.

**(c)** Si las guardas documentales fallan y la única forma de pasarlas es
**relajarlas**, se para. Ninguna guarda se toca para conseguir verde.

**(d)** Si el número de enmiendas **crece** al aplicarlas, y pasa de dos rondas, se
para y se busca la raíz en vez de seguir parcheando (regla de las dos rondas,
ADR-001).

## Opciones consideradas

Sobre **el mecanismo de la enmienda**, no sobre I4: eso lo decidió el propietario.

1. **Reescribir en su sitio el cuerpo de ADR-019 y ADR-020.** Descartada por el
   criterio de parada (a): la plantilla de este repositorio ya declara el estado
   `SUPERADO por ADR-NNN`, así que el mecanismo existe y reescribir una decisión
   aprobada borraría por qué se decidió lo que se decidió.
2. **Un ADR nuevo que supera los puntos concretos, más edición de los documentos
   vivos.** Es la opción elegida.
3. **No tocar los ADR y editar solo los documentos vivos.** Descartada: dejaría
   viva la frase normativa del punto 1 de la Decisión de ADR-019 —«el despliegue
   del motor exige supervisión y reinicio automático externos»—, que es
   exactamente la que la opción A incumple. Un árbol que decide una cosa y afirma
   la contraria en el cuerpo de un ADR aprobado es peor que no haber enmendado.

## Decisión

**Opción 2.** Este ADR supera, y solo, estos puntos:

| Documento | Qué queda superado |
|---|---|
| **ADR-019**, Decisión, punto 1 | «El despliegue del motor exige supervisión y reinicio automático externos (servicio del SO o equivalente)». El motor no es un proceso de larga duración: nace y muere con cada invocación, así que no hay nada que un servicio del sistema reinicie. |
| **ADR-019**, Opciones consideradas, opción 1 | Su **primera mitad** —«el observador seguiría dentro de lo observado»— se revisa, no se borra: sigue siendo cierta y pasa a Consecuencias como límite conocido. Su **segunda mitad** —«GitHub seguiría siendo la única memoria»— deja de aplicar: con la opción A la memoria es el diario propio del motor, versionado, no las etiquetas de GitHub. |
| **ADR-055** y el `docstring` gemelo de `cli.py` | «El diario es estado del propietario, no del árbol de código». Se deroga **solo para la ejecución dentro de Actions**. Para el uso desde la consola del propietario sigue vigente tal cual: ahí el diario sigue fuera del repositorio. |
| **ADR-020** | El descarte de «evolucionar los workflows hacia el motor», por el mismo motivo que ADR-019, y la dependencia «I4 antes del servicio desatendido»: I4 ya está resuelta. |
| **ADR-056** | «El motor es un observador externo» como **razón** de la separación entre el §12 del contrato y su §9.1. La separación se mantiene; su criterio deja de ser la ubicación y pasa a ser la responsabilidad —qué inicia bloques, qué avanza un ciclo sano y qué fusiona—. |
| **ADR-061** | La premisa de un disco que sobrevive al proceso. Dentro de Actions el disco del runner muere con el job: los diarios solo son durables si se versionan en el repositorio. |
| **ADR-063** | «Quién invoca el comando va aparte». Lo invoca un workflow, y el riesgo que ese ADR dejaba como hipotético deja de serlo. |
| **ADR-064** | Su premisa de proceso persistente. El límite que documentó —la reserva en memoria no sobrevive a un reinicio— pasa de ser un caso de borde a ser el riesgo principal, porque cada invocación **es** un proceso nuevo. |

Lo que **no** cambia: el motor sigue siendo el dueño de su estado detrás de un
puerto de persistencia (ADR-019, punto 1, primera mitad), los Workers siguen
siendo sustituibles, y `.claude/settings.json` sigue denegando `Edit(./.claude/**)`.

Y queda cerrada **I4**: la representación física del almacén ya no la decide un
spike, la decidió el propietario.

## Comprobación que la sostiene

**El barrido, medido.** 12 agentes en 6 vías independientes más un crítico de
completitud y cuatro rellenos de hueco: **191 hallazgos con cita literal**, 58 de
ellos convertidos en enmienda. Se eligió esa forma y no una lista escrita a mano
porque ADR-033 ya midió que una lista escrita a mano siempre tiene un hueco más, y
en este repositorio ha mordido cuatro veces.

**Lo que el crítico encontró que las seis vías no.** Las seis declararon fuera de
alcance la propia incidencia #270, y ahí estaba la afirmación falsa de
concurrencia. Es el argumento a favor de que la crítica de completitud no es
adorno: sin ella este ADR habría heredado el error.

**Citas verificadas una a una, con el fichero delante.** Ninguna afirmación de este
ADR viene de un resumen de agente sin comprobar; es la lección directa del error de
#270. En particular se comprobó, y **corrigió a la baja**, una alarma del barrido:
decía que «el motor no arranca en el runner» por exigir Python 3.14 frente al 3.12
del sistema. Medido: `pyproject.toml` exige `>=3.14,<3.15`, y cuatro workflows ya
preparan `python-version: "3.14.6"`. El límite real es más pequeño y va escrito en
Consecuencias.

**La prueba de terminado, ejecutada y con su cifra.** Se fijó por escrito antes de
empezar: «que ninguna afirmación de la versión vieja sobreviva sin que algo la
señale». Ejecutada sobre los **743 ficheros versionados** (`git ls-files`) con el
vocabulario de la versión vieja y sus variantes —supervisión externa, reinicio
automático, servicio del SO, process manager, siempre encendido, desatendido,
demonio, «máquina del propietario», «diario fuera del repositorio», «observador
externo», I4, D2—:

| | |
|---|---|
| Coincidencias únicas revisadas (`fichero:línea`) | **270** |
| Compatibles con ADR-082, sin tocar | 266 |
| **Afirmaciones viejas que sobrevivieron a la primera pasada** | **4** |

Las cuatro estaban en `docs/` de código, no en prosa, y por eso las nueve vías del
barrido documental no las vieron: `ports/store.py` («la representación física NO se
decide aquí»), `adapters/durable/store.py` («la fija D2»),
`adapters/durable/dispatch_journal.py` («ese caso queda para cuando el despachador
corra desatendido») y `recovery.py` («al arrancar… un reinicio de Sirius no pierde
ni duplica trabajo»). Corregidas en el mismo commit.

**La tercera es la que justifica haber hecho esta pasada.** `dispatch_journal.py`
aplazaba explícitamente el caso de la reserva huérfana «para cuando el despachador
corra desatendido» — y con la opción A ese momento es ahora. Sin esta búsqueda, el
árbol habría quedado prometiendo que el peor riesgo de ADR-082 era cosa del futuro.

## Consecuencias

### El `concurrency group` deja de ser una precaución y pasa a ser la única

Por el error retirado arriba. La serialización de las ejecuciones del motor no es
«además, por si acaso»: es lo único que separa al diario de tener dos registros con
el mismo número de secuencia y a nadie quejándose. **No se enchufa el motor sin
demostrar que funciona.**

### El daño peor no es un diario corrupto: es despachar dos veces

ADR-064 documenta que la reserva que impide activar dos veces el mismo trabajo vive
en memoria, y dice literalmente que «una reserva obtenida pero nunca grabada ni
liberada —el proceso murió entre `reservar` y `record`— **no sobrevive a un
reinicio**: un proceso nuevo no encuentra `_en_curso` y **puede reservar de
nuevo**». Lo escribió como límite conocido de un proceso que se reinicia. Con la
opción A cada invocación **es** un proceso nuevo, y dos simultáneos son dos
reservas del mismo trabajo: dos incidencias, dos ramas, dos PRs. Un diario corrupto
se repara leyendo; dos activaciones ya han escrito en GitHub.

### El agujero residual, que el repositorio ya tenía escrito

`repair-sirius-work.yml:67-81` declara, sobre sí mismo:

> «Un proceso que muere no puede informar de su propia muerte: si el checkout cae,
> si el runner desaparece o si alguien cancela el job, no queda ni etiqueta
> terminal ni diagnostico […] la incidencia queda ATASCADA […] Eso no se arregla
> desde aqui: solo lo cierra un observador EXTERNO».

Bajo la opción A el motor hereda exactamente esos tres modos de muerte, y deja de
ser ese observador externo. **Esto no se cierra con esta enmienda y no se disimula:
es el precio de la opción A.** Lo que sí sobrevive es la mitad útil —ADR-057
demuestra que un run **sí** puede observar otro run por la API—, así que «externo
al run observado» sigue siendo alcanzable aunque «externo a GitHub» ya no.

### Quien invoque al motor tiene que preparar Python 3.14

`pyproject.toml` exige `requires-python = ">=3.14,<3.15"`. Cuatro workflows ya
preparan `3.14.6`. Los que llaman guiones con `python3` pelado —`repair` para
`sirius_convergence.py`, `review` para `sirius_codex_review.py`— corren sobre el
Python del sistema del runner y **no pueden alojar el motor** sin añadir esa
preparación. Es la misma familia de H-13.

### Amplía el permiso, no solo la arquitectura

`docs/evolution/STATUS.md` autoriza el motor «estrictamente según ADR-019, ADR-020
y su plan aprobado». La opción A se aparta de los tres, así que **sin enmendar esa
cláusula la implementación queda fuera de lo autorizado** — no por diseño, por
gobierno. Va en la misma enmienda porque separarlas dejaría el permiso mintiendo.

### Una decisión de seguridad que este ADR no toma

El motor pasaría a ejecutar un modelo **y** a necesitar `contents: write` sobre el
repositorio en la misma superficie. Eso es una decisión del propietario y no se
cuela aquí: queda declarada como pendiente, con nombre, para que no se resuelva por
omisión el día del cableado.

### Ninguna cifra de latencia

El único spike que midió la cadencia se declaró **no concluyente por escrito**.
Este ADR no promete ni un número sobre cuánto tarda el motor en reaccionar.

## Alternativas descartadas y por qué

- **Reescribir el cuerpo de los ADR aprobados**: criterio de parada (a). El
  mecanismo `SUPERADO por ADR-NNN` ya existe en la plantilla.
- **Editar solo los documentos vivos**: dejaría viva la frase normativa de ADR-019
  que la opción A incumple.
- **Confiar en el formato del diario en vez de en la serialización**: es
  literalmente el error retirado en Contexto. El formato garantiza integridad por
  registro, no exclusión entre escritores.
- **Dividir la enmienda en varias PR**: descartada. Un árbol a medio enmendar
  afirma dos cosas contrarias a la vez, que es peor que cualquiera de los dos
  estados completos.

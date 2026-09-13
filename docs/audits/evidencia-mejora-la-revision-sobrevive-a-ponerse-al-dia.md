# Evidencia — Que una revisión sobreviva a ponerse al día con `main`

Fecha: 2026-09-13. Rama `mejora-la-revision-sobrevive-a-ponerse-al-dia`.
Nota de arranque: `arranque-mejora-la-revision-sobrevive-a-ponerse-al-dia.md`.
Decisión: ADR-187. Incidencia: #608, parte 2.

## Las cuatro preguntas del arranque

**1. ¿Se vio FALLAR primero?** Sí, en dos tandas. Las 9 pruebas de la decisión
fallaron con el módulo inexistente (9 errores), y las 3 del cableado fallaron
contra el workflow REAL antes de tocarlo. Después, 12 en verde.

**2. ¿Sigue siendo imposible aprobar trabajo no revisado?** Es la pregunta que
decide si esto es una mejora o un agujero, y se responde por tres caminos:
`test_una_linea_distinta_ya_no_es_la_misma_obra` (un cambio real reabre ronda),
`test_un_fichero_de_mas_no_es_la_misma_obra`, y la mutación M4, que saca la
decisión de la guarda de ADR-142 y cae. Además la consulta solo existe dentro de
esa guarda: origen `ready-for-merge` y Quality en verde, es decir, donde ya hay
una aprobación registrada que proteger.

**3. ¿Qué pasa si el diff no se puede calcular?** Fail-closed, probado por
cuatro caminos: fichero ausente, JSON roto, comparación sin `files`, y las dos
comparaciones vacías. Todos responden «no es la misma obra» → se repone la
revisión, que es lo que ocurre hoy. En el workflow, además, un fallo de
cualquiera de las dos lecturas de `gh` cae al camino normal.

**4. ¿El guardián mira código o comentarios?** Solo líneas de código
(`_lineas_de_codigo` descarta las que empiezan por `#`), y el de anidamiento
mira estructura: apertura de la guarda, `fi` a su sangría, invocación en medio.

## Mutaciones (ADR-001 §3), todas vistas caer y revertidas

| Mutación | Resultado |
| --- | --- |
| M1: la huella deja de ordenar los ficheros | CAE |
| M2: una comparación sin ficheros afirma igualdad | CAE |
| M3: un fichero ilegible afirma igualdad | CAE |
| M4: la decisión queda FUERA de la guarda de ADR-142 | CAE (ver abajo) |

**M4 no cayó a la primera, y eso es el hallazgo del día.** La primera versión de
su guardián comprobaba que la invocación apareciera *después* de la guarda en el
fichero; la mutación la sacaba del bloque y el guardián seguía en verde. Se
reescribió para medir anidamiento y solo entonces cayó. Queda como lección de
ADR-187, familia `guardian-que-mide-posicion-en-vez-de-estructura`.

## Un defecto propio, cazado por una guarda de la casa

`test_sirius_runner_python_compat.py` falló sobre el script nuevo: `ruff format`
había reescrito `except (OSError, ValueError):` a la sintaxis de PEP 758, que el
`python3` 3.12 del runner no entiende. Habría reventado en producción y en
verde aquí. Es exactamente la clase de fallo para la que esa prueba existe
(nació de un caso idéntico en `sirius_convergence.py`). Partido en dos `except`,
con el porqué escrito en el código para que nadie lo «simplifique» de vuelta.

## Criterio de parada

Ninguno de los cuatro se activó: el head aprobado ya viaja en el marcador
`sirius-verdict:reviewer:approved:<sha>` (no hizo falta inventar registro
nuevo), la puerta del revisor no se toca, no se amplió ninguna credencial —este
cambio lo hace la sesión interactiva, que es lo que ADR-002 prescribe— y no hubo
dos rondas de la misma familia.

## Estado final

`tests/automation`: en verde. Validaciones completas y suite entera: en el
resumen de la PR.

## Lo que esto NO arregla, dicho aquí

Mientras `MEMORIA.md` siga viajando en las ramas, ponerse al día con `main`
**sí** cambia el trabajo propio (hay que regenerarlo), así que esta mejora no se
aplica a ese caso. Es la parte 1 de #608, ya decidida por el propietario por la
vía que no abre permisos: que las ramas dejen de tocar ese fichero y se regenere
al fusionar. Las dos juntas son las que dejan la reconciliación en cero rondas.

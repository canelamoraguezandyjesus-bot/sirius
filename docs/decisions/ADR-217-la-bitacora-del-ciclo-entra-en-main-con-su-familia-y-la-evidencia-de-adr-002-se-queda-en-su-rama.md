# ADR-217 — La bitácora del ciclo entra en `main` con su familia, y la evidencia de ADR-002 se queda en su rama

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el propietario. La orden es suya, del
  01-10-2026: «todo lo que está apuntado en la bitácora, uno a uno, se mide y
  se crean mejoras». Para medirlo hay que poder leerlo.
- Nota de arranque: `docs/audits/mina-2026-09-nota-de-arranque.md` cubre la
  mina; para este ADR, el criterio de parada de abajo.

## Contexto y problema

La bitácora de fallos y mejoras del ciclo —146 entradas del 02 al 21-09-2026 y
48 deudas abiertas— no estaba en `main`. ADR-210 lo dejó escrito el 20-09 en
`docs/audits/DONDE_VIVE_LA_BITACORA_DEL_CICLO.md`, con una condición para que
entrara: «que la sesión que la escribe la traiga con su familia en una sola PR,
cuando cierre su línea de trabajo». Esa condición no se cumplió ni se iba a
cumplir: la rama que la guarda,
`claude/adr002-tol209-forensic-audit-i0ui8k`, lleva sin commits desde el
21-09-2026 14:36 UTC (`a044fb4a`), y la sesión que la escribía ya no existe.
Un registro que nadie puede leer no es un registro.

La rama no trae solo la bitácora. Medido el 01-10-2026 contra su punto de
bifurcación con `main` (clon traído entero: `git fetch --deepen`), tiene
**344 commits propios y 342 ficheros propios**, todos añadidos, ninguno
modificado: 48 en `docs/audits/`, 1 en `docs/investigaciones/`, 90 que en esa
rama van en `docs/architecture/` (la familia `SIRIUS_0.2_ADR_002_*`), 3 `.docx`
que en esa rama viven en `docs/architecture/canonical_sources/`, 182 en
`experiments/`, 10 en `artifacts/` y 8 guiones sueltos en la raíz.

## Criterio de parada (escrito ANTES de decidir)

- Si algún fichero de la familia **modificara** uno que ya existe en `main`,
  parar: eso sería traer trabajo en vuelo de otra sesión, no archivo.
- Si el comprobador de documentos encontrara en la familia una cita que no se
  pueda resolver nombrando la rama en la propia frase, parar y preguntar qué
  documento es la fuente.
- No se trae nada que no sea la bitácora y lo que la bitácora cita.

## Opciones consideradas

1. Traer la rama entera (342 ficheros). Rechazada: 272 de ellos son los
   experimentos y la evidencia de ADR-001/ADR-002, y la decisión D1
   (`docs/evolution/STATUS.md`, ADR-216) es que esa evidencia se porta por
   encargos, no fusionando ramas; la PR #117 se cerró el 24-09 por eso mismo.
2. Dejar el puntero y esperar. Rechazada: la sesión no va a volver, y el
   propietario pidió el 01-10 trabajar sobre la bitácora entera.
3. Traer la bitácora con su familia de `docs/audits/` y el documento de
   `docs/investigaciones/` que cita, y nada más. **Esta.**

## Decisión

1. Entran en `main`, tal como estaban en `a044fb4a`, los 48 ficheros de
   `docs/audits/` que la rama añade y
   `docs/investigaciones/2026-09-13-memanto-contra-la-capa-de-memoria-de-sirius.md`.
   Entre ellos: la bitácora (`bitacora-de-fallos-y-mejoras-del-ciclo.md`), la
   hoja de decisiones abiertas del propietario, las decisiones pendientes de la
   línea de memoria, la mina v2 del 03-09, las mediciones del 20-09 con Ollama
   real, los encargos preparados y sin lanzar, y los guiones de vigía (`.sh`)
   que la bitácora cita por su ruta.
2. Se corrigen solo los defectos de **forma** que el comprobador de documentos
   nombró, sin tocar el contenido: siete documentos sin un único encabezado de
   nivel 1 (se añade título o se rebajan los sobrantes) y tres citas a ficheros
   que viven en otra rama, reescritas para que la frase nombre la rama antes
   de la ruta, que es lo que el comprobador exige.
3. `DONDE_VIVE_LA_BITACORA_DEL_CICLO.md` se actualiza por arriba con fecha, y
   conserva debajo la nota del 20-09 tal como se escribió.
4. La evidencia de ADR-001/ADR-002 (`experiments/`, `artifacts/`, la familia
   `SIRIUS_0.2_ADR_002_*`, los `.docx`) **se queda en su rama**, que no se borra
   (ADR-195). Quien la necesite la cita nombrando la rama, como ya hacen los
   documentos que entran.
5. Desde hoy la bitácora se actualiza en `main`. Las entradas de la segunda
   mitad de septiembre —que esta sesión protagonizó— las añade la mina de
   septiembre, no este ADR.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La rama solo añade, no modifica | `git diff --name-status origin/main...origin/claude/adr002-tol209-forensic-audit-i0ui8k -- docs/audits` filtrado por estado distinto de `A` | vacío: los 48 son altas |
| La huella propia de la rama | `git diff --stat origin/main...<rama>` tras `git fetch --deepen=3000` | 342 ficheros, 444 804 líneas añadidas, 0 borradas |
| La rama está muerta | `git log -1 --format=%ci <rama>` | `2026-09-21 14:36:17 +0000` |
| Lo que entra pasa el comprobador | `sirius_check_docs.py` sobre los 48 `.md` de la familia y la nota actualizada | 13 defectos antes (7 de encabezado, 3 de cita, 3 por pasarle los `.sh` como si fueran Markdown); **0 después** sobre los `.md`. Los `.sh` no son documentos y no se le pasan |
| Nadie más trabajaba sobre estos ficheros | `list_pull_requests` abiertas el 01-10-2026 04:40 UTC | ninguna (ADR-206: libre) |

## Consecuencias

- Las 146 entradas y las 48 deudas se pueden leer, citar y medir desde `main`.
  La mina de septiembre (misma PR o la siguiente) las clasifica una a una.
- `docs/audits/` gana 48 ficheros de una sesión que ya no existe. Son archivo:
  describen el 02→21-09 y llevan su fecha. El comprobador y la memoria común
  los indexan como cualquier otro.
- La familia de ADR-002 sigue en su rama, igual que la de #117. Nada se borra.

## Alternativas descartadas y por qué

- **Mover los `.sh` a `scripts/`** para que no vivan en `docs/`. Rechazada en
  esta PR: la bitácora los cita por su ruta actual y moverlos rompe 4 citas;
  son evidencia de método de una sesión concreta, no herramientas vivas.
- **Reescribir la bitácora al traerla** (quitar entradas saldadas, renumerar).
  Rechazada: es un registro cronológico; lo que esté saldado lo dice la mina
  con su evidencia, no un borrado.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: dejar la entrada de un registro en `main` condicionada
  a que una sesión concreta vuelva. ADR-210 escribió el 20-09 «que la traiga
  quien la escribe»; esa sesión murió al día siguiente y la condición no tenía
  quien la disparara. Once días después, la bitácora que el propietario pidió
  el 03-09 seguía sin poder leerse desde `main`
- lo hace cumplir: ninguna prueba: la condición vivía en prosa de un documento
  puntero, y lo que la haría imposible —que un puntero a otra rama caduque solo
  si la rama deja de moverse— no está construido. Queda en H-217 con fecha

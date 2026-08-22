# SIRIUS 0.2 — ADR-002 · Aprobación de la ronda primaria como evidencia

**Versión:** 1.0
**Estado:** **APROBADA COMO EVIDENCIA · ninguna alternativa elegida**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**HEAD que ejecutó la ronda:** `1f89edb35621324f76ddd210c399355daacd9d3a`
**HEAD aprobado:** `c5a72d4f77e66192886cf5854f2d4b7577f44dc0`

**Autoridad:** `SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md` y el
informe `SIRIUS_0.2_ADR_002_RONDA_PRIMARIA_ANALISIS_Y_RECOMENDACION_v1.0.md`.

**Acto de aprobación:** el usuario, directamente en el chat de trabajo, sobre la
solicitud única del §9 del informe, eligió:

> «**Aprobar y corregir la capa común.**»

---

## 1. Lo que queda aprobado

| | |
|---|---|
| `artifacts/adr002_round/ronda_primaria_v0.1.json` | **EVIDENCIA de `ADR-002`** |
| `artifacts/adr002_round/ronda_primaria_v0.1_evidencia.json` | evidencia mínima del §10, caso a caso y muestra a muestra |
| El análisis y la recomendación | leídos y aceptados |

La corrida fue **válida a la primera**: la repetición única del §6.8 no llegó a
ejercitarse, y los diez controles internos salieron en verde.

---

## 2. Lo que queda registrado como hecho

**Ninguna de las cinco alternativas pasa las puertas del §9.** No hay ganador
que declarar, y **no se declara ninguno**.

| Participante | Contaminación | Fuga de ámbito | Fusión de polaridad | Etapa | Exactos |
|---|---|---|---|---|---|
| `T0-control` | 16 | 1 289 | 2 480 | 0/46 | 1/47 |
| `ADR002-A` | 5 | 0 | 38 | 30/46 | 20/47 |
| `ADR002-B` | 5 | 0 | 38 | 29/46 | 19/47 |
| `ADR002-C` | 5 | 0 | 38 | 30/46 | 20/47 |
| `ADR002-D` | 5 | 0 | 38 | 29/46 | 19/47 |

**El control queda falsado**, que es su oficio: `T0` devuelve 2 192 resultados
donde un candidato devuelve 159, sin marcar polaridad, sin etapas y sin una sola
explicación.

**Las señales tardías no pagaron su coste sobre este corpus**: la relacional no
cambió ni un resultado, la vectorial cambió tres y no mejoró ninguno. Queda
igualmente registrado que este corpus tiene **diez relaciones**, de modo que ese
resultado describe también la superficie relacional del banco, y no solo a los
candidatos.

---

## 3. Lo que esta acta **no** hace

- **No elige alternativa**, ni provisional ni definitiva.
- **No descarta** a ninguna: los tres defectos que bloquean a los cuatro son de
  la capa común y no son atribuibles a ninguna arquitectura.
- **No cierra `ADR-002`.**
- **No abre `EJE-1` ni `EJE-2`.**
- **No toca** Sirius 0.1 productivo ni fusiona el PR #117.

---

## 4. Lo que autoriza

Abrir un **paquete de corrección de la capa común** con los tres defectos
medidos, y **repetir esta misma ronda** con el arnés ya congelado cuando estén
corregidos.

El detalle de los tres defectos, con el fichero en el que vive cada uno y cómo
se corregirá, se preinscribe **antes de tocar código** en
`SIRIUS_0.2_ADR_002_PAQUETE_CORRECCION_CAPA_COMUN_v0.1.md`.

**El arnés de la ronda no se toca.** Repetir la medición con un arnés modificado
después de haber visto los resultados es exactamente lo que el §8.1 del
protocolo prohíbe.

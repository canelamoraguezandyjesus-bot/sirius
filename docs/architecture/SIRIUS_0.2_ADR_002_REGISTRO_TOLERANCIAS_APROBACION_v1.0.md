# SIRIUS 0.2 — ADR-002 · Aprobación del Registro de Tolerancias y artefactos asociados

**Versión:** 1.0  
**Estado:** APROBADO · CANÓNICO PARA ADR-002  
**Fecha:** 26 de julio de 2026  
**Autoridad:** Usuario / Proyecto Sirius  
**Rama:** `evidence/adr001-spikes`

## 1. Decisión

El usuario aprobó explícitamente el 26 de julio de 2026, mediante la respuesta **«Sí, venga»**, los cuatro artefactos siguientes:

1. `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`  
   Blob verificado: `263b1689c8e2ac1988d779826eb75cb5d63618a1`
2. `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`  
   Blob verificado: `c298a6b804309a78062f79b6341adfea2374ce56`
3. `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md`  
   Blob verificado: `4e9fa861ed6ab22a6b19729ed44066c8d93d863e`
4. `docs/architecture/SIRIUS_0.2_ADR_002_NOTA_SUPERACION_01_v0.1_PROPUESTO.md`  
   Blob verificado: `5a787094e3e16661ccee06103a36fd12b8d8ccf4`

Desde esta aprobación, esos contenidos exactos quedan **APROBADOS y canónicos para continuar ADR-002**, aunque sus nombres físicos conserven el sufijo histórico `PROPUESTO`. Este registro prevalece sobre ese sufijo y evita reescribir documentos ya auditados.

## 2. Alcance de la aprobación

La aprobación congela:

- las tolerancias y puertas del Registro v0.4;
- el protocolo común de medición;
- la plantilla y disciplina de congelación por candidato;
- la nota de superación documental.

No autoriza:

- ejecutar T0 o T1–T4;
- implementar candidatos;
- modificar Sirius 0.1;
- fusionar el PR #117;
- iniciar el benchmark mientras `SRC-ADR002-01`, `TOL-207`, `TOL-208`, `TOL-209` y `TOL-210` no estén satisfechas.

## 3. Siguiente trabajo autorizado

Queda autorizada la materialización verificable en el repositorio de las fuentes canónicas necesarias para satisfacer `SRC-ADR002-01`:

- B04 v1.0 APROBADO;
- Plan de Pruebas + RED/PDP v1.0 APROBADO;
- ARQ-00 v1.0 APROBADO.

Tras materializarlas deberá verificarse su identidad, trazabilidad y completitud antes de preparar el corpus ejecutable.

## 4. Estado

**APROBADO.** El Registro de Tolerancias v0.4 y sus tres artefactos asociados quedan cerrados dentro de su alcance. El benchmark continúa bloqueado hasta satisfacer todas sus puertas de arranque.

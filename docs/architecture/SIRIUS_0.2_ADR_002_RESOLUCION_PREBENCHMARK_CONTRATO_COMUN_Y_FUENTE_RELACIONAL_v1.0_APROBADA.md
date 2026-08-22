# SIRIUS 0.2 — ADR-002 · Resolución pre-benchmark del contrato común y la fuente relacional

**Versión:** 1.0  
**Estado:** **APROBADA · CANÓNICA PARA LA PREPARACIÓN PRE-BENCHMARK DE ADR-002**  
**Fecha:** 3 de agosto de 2026  
**Rama de materialización:** `claude/adr002-tol209-forensic-audit-i0ui8k`  
**Rama canónica autorizada:** `evidence/adr001-spikes`  
**Autoridad:** aprobación explícita del usuario en el Proyecto Sirius  
**Respuesta literal registrada:** «venga si»  
**Contexto cerrado de interpretación:** respuesta inmediata a la recomendación expresa de aprobar la Resolución pre-benchmark de ADR-002 v0.4 y autorizar su materialización y el avance por fast-forward de `evidence/adr001-spikes`, sin autorizar implementación, benchmark ni fusión.

**Paquete aprobado:** `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.4.md`  
**Blob del paquete:** `8e583876aac9f40144ec2a7db2c2270008bf4320`  
**Resolución aprobada:** `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.4_PROPUESTA.md`  
**Blob de la resolución:** `191edb43df37a6cd9220212815ee52a1c4b0397e`  
**Commit documental auditado:** `0ad983c9813bc62caa52fe1458f6aaf76e22833e`

---

## 0. Decisión aprobada

> **Se aprueba íntegramente la Resolución pre-benchmark de ADR-002 v0.4 como decisión canónica de preparación, sin autorizar todavía ninguno de sus pasos de implementación.**

La aprobación alcanza exclusivamente las decisiones, contratos experimentales, adjudicaciones y el plan contenidos en la v0.4 identificada por el blob anterior.

Las propuestas v0.1, v0.2 y v0.3 se conservan íntegras como historial documental y quedan sustituidas por la v0.4 en el plano de decisión vigente.

---

## 1. Materia aprobada

Quedan aprobados:

1. El contrato experimental de criticidad en tres planos y su handoff completo a B05.
2. La adopción experimental del vocabulario de procedencias de criticidad de `B04-Q21`.
3. La tabla cerrada de transformación de `criticidad.fuente` privada a `fuente_de_politica` segura.
4. La ampliación futura del vocabulario común de niveles de criticidad, incluyendo `IMPORTANTE`.
5. El origen, custodia, canal lateral y validadores de `property_key`.
6. La clasificación por `(campo, consumidor, uso)`, incluida la capacidad `HANDOFF_A_B05`.
7. La futura definición y custodia de `subject_key_experimental`, con sus usos comunes y el uso estructural declarado de `ADR002-A`.
8. La obligación de recomprobar la suficiencia de `ADR002-C` bajo la proyección definitiva antes de autorizar la ronda primaria.
9. La corrección futura del tratamiento del sujeto ausente en la capa común.
10. La separación entre deduplicación exacta y agrupación de equivalentes.
11. Las dos cardinalidades —semántica y documental— y las reglas de agrupación de la v0.4.
12. La reinterpretación experimental propuesta de `ACOTADA`, conforme a lo declarado expresamente en la resolución aprobada.
13. El alcance de la familia sucesora de conformidad y su custodia append-only.
14. La adjudicación de la discrepancia FTS5 como exclusivamente documental, junto con el remedio propuesto.
15. La adjudicación separada del inexistente arnés de conformidad de `T0`, con el coste y las consecuencias de custodia declarados.
16. El plan ordenado de once pasos de la resolución.

---

## 2. Identidad léxica observada y condición previa al benchmark

Se acepta como hecho observado:

- tabla real: `knowledge_fts`;
- tokenizador: `unicode61`;
- `remove_diacritics`: `1` por valor predeterminado efectivo;
- la discrepancia con las fichas existentes es documental para el material congelado y la evidencia ya emitida;
- ningún benchmark podrá autorizarse mientras esta discrepancia no haya sido cerrada mediante la fe de erratas prevista y las fichas sucesoras aplicables.

Las fichas y actas históricas de `T0-control v1`, `ADR002-A v3` y `ADR002-B v5` no se reescriben por esta aprobación.

---

## 3. Estado de los candidatos y del control

Esta aprobación no modifica los estados vigentes:

- `T0-control v1`: intacto.
- `ADR002-A v3`: **PREPARADO PARA BENCHMARK**, aprobación histórica intacta.
- `ADR002-B v5`: **PREPARADO PARA BENCHMARK**, aprobación histórica intacta.
- `ADR002-C`: no implementado.
- `ADR002-D`: no implementado.

La fuente relacional de `ADR002-C` permanece provisionalmente **ADMISIBLE PERO FUNCIONALMENTE INSUFICIENTE sobre el corpus v0.4**, condicionada a la recomprobación bajo `subject_key_experimental` definitivo y a la familia sucesora.

---

## 4. Plan aprobado, ejecución no autorizada

Se aprueba como orden de trabajo futuro:

1. materializar y congelar la familia sucesora de conformidad;
2. emitir la fe de erratas amplia del sustrato léxico;
3. adjudicar por separado el arnés de conformidad de `T0`;
4. construir la proyección experimental;
5. corregir `common` una sola vez;
6. emitir fichas sucesoras de `ADR002-A` y `ADR002-B`;
7. repetir pruebas y obtener reaprobación explícita de A y B;
8. implementar, congelar, probar y aprobar `ADR002-C`;
9. implementar, congelar, probar y aprobar `ADR002-D`;
10. completar las verificaciones pre-benchmark;
11. solicitar mediante un acto independiente la autorización del benchmark.

**La aprobación de este orden no autoriza ejecutar ninguno de sus pasos.** Cada paso conserva sus puertas de autorización y custodia.

---

## 5. Fast-forward autorizado

Se autoriza avanzar `evidence/adr001-spikes` mediante **fast-forward puro**, sin rebase, squash, amend, force-push ni reescritura, desde:

`a074eb5effda760833fe7de1bd6e1b16984c982c`

hasta el commit que incorpore esta acta como descendiente directo de la cadena documental encabezada por:

`0ad983c9813bc62caa52fe1458f6aaf76e22833e`.

El avance incorpora los documentos v0.1–v0.4 y esta acta al PR #117.

---

## 6. No autorizado

Esta aprobación **no autoriza**:

- modificar código, pruebas, corpus, fichas o actas anteriores;
- materializar todavía la familia sucesora;
- emitir todavía la fe de erratas léxica;
- crear el arnés de conformidad de `T0`;
- corregir `common`;
- emitir fichas sucesoras de A o B;
- implementar C o D;
- ejecutar candidatos;
- ejecutar o medir el benchmark;
- reducir la ronda primaria `T0 + A + B + C + D`;
- elegir ganador;
- modificar Sirius 0.1 productivo;
- fusionar el PR #117.

---

## 7. Estado final de gobierno

- Resolución pre-benchmark v0.4: **APROBADA** mediante esta acta.
- Paquete de resolución 05 v0.4: **PREINSCRIPCIÓN VIGENTE**.
- Benchmark: **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO**.
- Ronda primaria: `T0 + ADR002-A + ADR002-B + ADR002-C + ADR002-D`, sin reducción.
- Aprobaciones de A v3 y B v5: intactas como decisiones históricas de sus identidades exactas.
- PR #117: debe permanecer abierto y sin fusionar.

Esta acta registra la decisión y no constituye por sí misma autorización de implementación ni de ejecución experimental.

# SIRIUS 0.2 — ADR-001

## Modelo físico, temporalidad, autoridad, multi-proyecto, borrado y viabilidad de migración

**Versión:** 1.1  
**Estado:** APROBADO  
**Fecha:** 25 de julio de 2026  
**Autoridad de aprobación:** Usuario / Proyecto Sirius  
**Marco rector:** SIRIUS 0.2 ARQ-00 v1.0 APROBADO  
**Evidencia principal:** `artifacts/adr001_spikes/SIRIUS_0.2_ADR_001_RESULTADOS_SPIKES_v0.2_PROPUESTO.md`  
**Commit de evidencia corregida:** `5a4fede5c872887832512cf0a6f15a35393a91ac`

## 1. Pregunta resuelta

¿Puede el motor y el modelo físico heredados representar el modelo de contenido, tiempo válido y tiempo de registro, estados ortogonales, multi-proyecto cerrado y borrado duro propagado, y demostrar que existe al menos una ruta de migración segura sin crear una segunda verdad?

## 2. Decisión

Se **ratifica la alternativa A**:

> Evolucionar incrementalmente Sirius 0.2 conservando SQLite, SQLAlchemy 2, Alembic y el modelo físico fundamental heredado, mediante extensiones aditivas y contratos nuevos, sin sustituir el motor ni reconstruir el sistema por event sourcing.

Esta decisión conserva la arquitectura modular y la disciplina transaccional de Sirius 0.1, pero no convierte sus tablas, enums ni nombres actuales en diseño físico definitivo de Sirius 0.2.

## 3. Alternativas

- **A — APROBADA:** evolución incremental conservando motor y modelo físico fundamental.
- **B — NO ACTIVADA:** sustitución material del modelo físico manteniendo SQLite.
- **C — NO ACTIVADA:** replataformado del motor y del modelo físico.
- **D — DESCARTADA como autoridad de reconstrucción:** event sourcing completo. Los eventos pueden conservarse como evidencia y traza purgable, pero no constituyen una segunda fuente canónica ni un replay obligatorio.

## 4. Evidencia decisiva

Se ejecutaron y reprodujeron desde bases limpias los spikes 1–8, 10 y 15–19.

Resultado final:

- 14 de 14 spikes en `PASS`;
- 25 pruebas experimentales en `PASS`;
- ninguna clasificación `FAIL_STRUCTURAL_MODEL`;
- ninguna clasificación `FAIL_ENGINE_SQLITE`;
- ningún resultado `INCONCLUSIVE`;
- huella del esquema y los datos heredados idéntica antes y después;
- head canónico de Alembic sin cambios;
- migración experimental y rollback viables;
- fallo inyectado sin estado parcial;
- derivados destruibles y regenerables desde el canon;
- no reconstruibilidad demostrada dentro del modelo de amenaza declarado.

El spike 7 fue corregido y repetido con las siete dimensiones canónicas:

1. confirmación;
2. validez;
3. disponibilidad;
4. sensibilidad;
5. temporalidad;
6. ámbito;
7. autoridad.

Las siete se representan y modifican de forma independiente. Quince combinaciones canónicas distintas coexistieron y se redujeron a solo tres valores del enum heredado, demostrando que el enum actual solo puede ser una proyección con pérdida y nunca la autoridad semántica de Sirius 0.2.

## 5. Consecuencias obligatorias

1. La fuente canónica será única. Índices, FTS, caches, resúmenes, vistas, exportaciones y paquetes de contexto serán derivados regenerables.
2. Ningún derivado podrá consultarse como autoridad ni sobrevivir semánticamente a la eliminación de su fuente.
3. El borrado deberá destruir explícitamente contenido, procedencia recuperable y todos los derivados afectados.
4. La purga física deberá incluir el tratamiento correspondiente de journals o WAL y `VACUUM` cuando proceda.
5. `secure_delete` y la secuencia de purga deberán verificarse sobre el ejecutable real de Windows antes de aceptar la implementación.
6. Tiempo válido y tiempo de registro permanecerán separados.
7. Confirmación, validez, disponibilidad, sensibilidad, temporalidad, ámbito y autoridad permanecerán ortogonales; no se condensarán en un enum monolítico.
8. El ámbito multi-proyecto será cerrado y filtrado antes de recuperación y ranking.
9. La migración productiva, compatibilidad, ventana de corte, dual-write y rollback operativo pertenecen a ADR-004. Los spikes de ADR-001 demuestran viabilidad, no eligen estrategia.
10. El código bajo `experiments/adr001/` es evidencia experimental. No se convierte automáticamente en diseño, DDL o código productivo.

## 6. Condiciones todavía pendientes

- Confirmar en Windows el valor efectivo de `secure_delete` y el comportamiento de purga del SQLite empaquetado.
- Fijar vocabularios definitivos, restricciones y forma física durante la arquitectura consolidada, respetando los contratos aprobados.
- Definir cifras de rendimiento en el Registro de Tolerancias.
- Resolver ADR-002, ADR-003A, ADR-003B, ADR-003C y ADR-004 antes de consolidar la arquitectura implementable.

Estas condiciones no reabren la alternativa A. Son obligaciones de diseño, prueba e implementación derivadas de la decisión.

## 7. No autoriza

La aprobación de ADR-001 no autoriza:

- implementar Sirius 0.2;
- modificar Sirius 0.1;
- alterar las migraciones canónicas actuales;
- adoptar directamente el DDL experimental;
- fusionar la rama de evidencia sin revisión;
- decidir la estrategia de migración de ADR-004.

## 8. Aprobación

El usuario declaró explícitamente su aprobación el 25 de julio de 2026 mediante: **«Sí a todo»**, en respuesta a la ratificación formal de la alternativa A y a la autorización para emitir ADR-001 v1.1 APROBADO y abrir ADR-002.

**Resultado:** ADR-001 queda cerrado y APROBADO. ADR-002 queda autorizado para apertura.

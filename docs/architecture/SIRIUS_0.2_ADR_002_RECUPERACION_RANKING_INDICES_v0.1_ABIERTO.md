# SIRIUS 0.2 — ADR-002

## Recuperación, ranking e índices

**Versión:** 0.1  
**Estado:** ABIERTO · PROPUESTO PARA INVESTIGACIÓN Y DECISIÓN  
**Fecha de apertura:** 25 de julio de 2026  
**Autoridad de apertura:** Usuario / Proyecto Sirius  
**Dependencia satisfecha:** ADR-001 v1.1 APROBADO  
**No autoriza:** implementación, cambios en Sirius 0.1 ni selección anticipada de tecnología semántica.

## 1. Pregunta material

¿Qué arquitectura de recuperación supera B04 y el PDP con explicabilidad, privacidad, aislamiento y coste controlado sin acoplarse a un proveedor?

## 2. Entradas obligatorias

- B04-D01–D16.
- B01 y CT-02.
- Modelo aprobado por ADR-001.
- Corpus y PDP aprobados.
- Línea base FTS5 de Sirius 0.1.
- RED-027 a RED-034 y la parte aplicable de RED-040.
- PDP F01, F02, F03, F10, F15, F22 y F23.

## 3. Alternativas excluyentes

- **A — Solo léxica y estructurada:** expansión escalonada E0–E5 usando únicamente señales léxicas y estructuradas.
- **B — Semántica tardía:** expansión léxica y estructurada, incorporando señal vectorial solo en etapas tardías y únicamente después de fallar la puerta de suficiencia.
- **C — Relacional tardía:** expansión léxica y estructurada, incorporando señal relacional explícita solo en etapas tardías y únicamente después de fallar la puerta de suficiencia.
- **D — Semántica y relacional separadas:** expansión escalonada con ambas señales en etapas tardías distintas y con orden predefinido; nunca coordinación simultánea fuera de la etapa autorizada.

La política E0–E5, sus puertas G1–G12 y la expansión escalonada proceden de B04 y no son objeto de decisión en este ADR.

## 4. Puertas de decisión

Una alternativa queda descartada si incumple cualquiera de estas puertas:

1. Recall crítico insuficiente.
2. Contaminación por contenido no pertinente, prohibido, eliminado, restringido o fuera de ámbito.
3. Ausencia de explicación reproducible del resultado.
4. Inestabilidad material de orden o selección bajo entradas equivalentes.
5. Imposibilidad de borrar o reconstruir completamente sus índices y derivados.
6. Acoplamiento a un proveedor concreto.
7. Coste, latencia o complejidad incompatibles con el Registro de Tolerancias.
8. Incumplimiento de aislamiento multi-proyecto, tiempo válido, corte de conocimiento, negación o conflicto.

La continuidad con FTS5 es un valor favorable, nunca una excepción a las puertas.

## 5. Evidencia requerida

- Benchmark versionado por familias y casos.
- Línea base reproducible de FTS5 y ranking actual.
- Ablaciones por señal y por etapa.
- Pruebas positivas, negativas y adversariales de negación, tiempo válido, corte de registro, ámbito, soporte plural, conflicto y ausencia.
- Pruebas de deduplicación prudente y cardinalidad.
- Pruebas de fuente inaccesible y degradación parcial.
- Borrado transaccional y regeneración de cada índice o derivado.
- Medición de latencia, coste, tamaño y estabilidad conforme al Registro de Tolerancias.
- Trazas minimizadas que permitan explicar por qué entró, salió u ocupó una posición cada resultado.

## 6. Línea base heredada

Sirius 0.1 aporta una base real que debe medirse, no presumirse:

- FTS5.
- `KnowledgeSearchRepository`.
- `RankRelevantKnowledgeUseCase`.
- ranking de dominio puro.
- filtros y búsquedas locales existentes.

La línea base se conserva congelada como control comparativo. No se modifica para favorecer una alternativa.

## 7. Método de cierre

1. Reconstruir el contrato exacto de B04, RED y PDP aplicable.
2. Materializar corpus, referencias y métricas antes de observar resultados.
3. Ejecutar la línea base FTS5.
4. Implementar solo los prototipos mínimos necesarios para falsar A, B, C y D.
5. Ejecutar benchmark y ablaciones.
6. Realizar una auditoría adversarial completa.
7. Corregir únicamente hallazgos demostrables.
8. Emitir ADR-002 final con una recomendación principal y consecuencias.
9. Obtener aprobación explícita del usuario.

## 8. Decisiones que este documento no toma

Este documento no decide todavía:

- embeddings definitivos;
- modelo de embedding;
- `sqlite-vec` u otra extensión;
- RRF u otra fórmula de fusión;
- grafo, RDF o motor relacional especializado;
- cifras de latencia, coste o tamaño;
- estructura final de tablas, carpetas o módulos;
- implementación productiva.

## 9. Siguiente movimiento

Preparar el inventario normativo y el benchmark mínimo de ADR-002, empezando por la línea base FTS5 y las puertas de suficiencia, sin implementar todavía ninguna alternativa productiva.

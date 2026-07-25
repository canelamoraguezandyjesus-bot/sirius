# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 01

## Inventario normativo y línea base FTS5

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA ANÁLISIS  
**Rama de trabajo:** `evidence/adr001-spikes`  
**Dependencia satisfecha:** ADR-001 v1.1 APROBADO  
**No autoriza:** decisión final de ADR-002, implementación productiva, cambios en Sirius 0.1, selección anticipada de embeddings/vector/grafo ni merge.

## 1. Objetivo único

Preparar la base verificable de ADR-002 antes de comparar alternativas:

1. inventario normativo completo de recuperación, ranking e índices;
2. caracterización de la línea base FTS5 real de Sirius 0.1;
3. diseño de un benchmark mínimo, reproducible y neutral;
4. identificación de incertidumbres que sí requieren experimentos posteriores.

No se ejecutan todavía alternativas semánticas o relacionales.

## 2. Fuentes de autoridad

Usar en este orden:

1. `docs/architecture/SIRIUS_0.2_ADR_001_MODELO_FISICO_v1.1_APROBADO.md`.
2. `docs/architecture/SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.1_ABIERTO.md`.
3. Este paquete operativo, que materializa para el repositorio los contratos aprobados de B04, RED/PDP y ARQ-00 necesarios para el trabajo 01.
4. El código y las pruebas reales de Sirius 0.1 exclusivamente como línea base técnica.

Si el código contradice una obligación aprobada de 0.2, prevalece la obligación de 0.2. El código de 0.1 no rebaja el producto.

## 3. Invariantes obligatorios

- Fuente canónica única; FTS, índices, caches y resúmenes son derivados regenerables.
- Privacidad, permiso, existencia, ámbito, tiempo, confirmación, disponibilidad, sensibilidad y marcas de no uso se resuelven antes de ranking.
- Contenido eliminado, purgado, no guardado, restringido no autorizado o fuera de ámbito nunca es candidato.
- Multi-proyecto cerrado: no existe ampliación silenciosa de ámbito.
- Tiempo válido y corte de registro son independientes.
- Homónimos no se fusionan; alias ambiguos no expanden sin resolución.
- Negación, condición, postura, apoyo/refutación y conflicto no se pierden durante recuperación o agrupación.
- Los críticos elegibles dominan el presupuesto; el límite duro produce estado parcial visible.
- Cada resultado debe ser explicable: coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden.
- Ninguna tecnología concreta es obligatoria por producto.
- Solo una operación activa y autorizada puede iniciar una búsqueda interna.
- La salida de ADR-002 es arquitectura de recuperación; no emite el paquete final de contexto de ADR-003B.

## 4. Cobertura normativa mínima

### 4.1 Petición, modo y aclaración — B04-RF-01 a RF-04

Inventariar consulta, `operation_id`, propósito, modo M1–M5, ámbito, tiempo, estados, criticidad, espacios, cardinalidad, límites y traza. Toda ambigüedad material o falta de permiso se bloquea o aclara antes de generar candidatos.

### 4.2 Identidad, ámbito y tiempo — B04-RF-05 a RF-08

Resolver entidades por ID estable; impedir fusión de homónimos; aplicar ámbitos global/proyecto/multi-proyecto cerrado; soportar tiempo objetivo, tiempo válido, evento e historial con corte de registro.

### 4.3 Puertas y exclusiones — B04-RF-09 a RF-13

Aplicar puertas antes de exposición y ranking. Excluir eliminado, no guardado, purgado y “no usar como memoria”. Estados especiales solo son elegibles en modos autorizados. Evidencia externa permanece atribuida y no canónica.

### 4.4 Expansión escalonada — B04-RF-14 a RF-18

Respetar E0–E5. Comenzar por exacto/estructurado; después variantes léxicas y alias confirmados; solo después significado o relaciones; fuentes e historial únicamente en etapa autorizada y cotejados con el estado vigente.

### 4.5 Fidelidad semántica — B04-RF-19 a RF-21

Preservar negación, condición, refutación y postura. Deduplicar solo con equivalencia material, incluida coincidencia de ámbito y postura. Recuperar todos los lados elegibles de un conflicto sin resolverlo silenciosamente.

### 4.6 Ranking, criticidad, límites y ausencia — B04-RF-22 a RF-26

Ordenar solo elegibles; propagar criticidad con regla y fuente; respetar límite objetivo y duro; adjudicar suficiencia y taxonomía de ausencia; mantener indistinguibles externamente ausencia y no-reportable cuando revelar diferencias filtre existencia.

### 4.7 Contrato, explicación y trazabilidad — B04-RF-27 a RF-32

Entregar resultados, estados, evidencia, criticidad, orden inicial, límites y suficiencia. Explicar cada resultado. Registrar plan reproducible. Permitir búsqueda interna solo desde operación activa. Mantener neutralidad tecnológica. Degradar de forma segura y reproducible.

## 5. Delegaciones RED que deben quedar trazadas

- **RED-027:** modo M1–M5, propósito, permisos y aclaración antes de buscar.
- **RED-028:** tiempo objetivo y corte de registro fijados antes de recuperar.
- **RED-029:** plan reproducible con espacios, puertas, etapas, parada y limitaciones.
- **RED-030:** cardinalidad, deduplicación prudente y evidencia plural.
- **RED-031:** taxonomía de ausencia sin falsos “no existe”.
- **RED-032:** tolerancias diferenciales de texto, estado, conteo y tiempo.
- **RED-033:** equivalencia semántica observable sin imponer técnica.
- **RED-034:** salida parcial reproducible y fuente necesaria inaccesible.
- **RED-040 aplicable:** un único reintento acotado entre recuperación y contexto, sin bucle; solo se registra la interfaz, no se decide ADR-003B.

## 6. Familias PDP obligatorias para el benchmark

Cubrir como mínimo:

- F01 consulta ordinaria actual;
- F02 tiempo válido;
- F03 corte de conocimiento;
- F10 diferencias materiales, derivados y equivalencias;
- F15 condición, negación, relaciones y composición;
- F22 neutralidad/portabilidad observable;
- F23 ausencia, parcialidad, fuente inaccesible y degradación segura;
- F24 trazabilidad del plan, cuando aplique a la recuperación.

## 7. Alternativas que ADR-002 comparará después

- **A — Solo léxica y estructurada.**
- **B — Semántica tardía.**
- **C — Relacional tardía.**
- **D — Semántica y relacional separadas en etapas tardías.**

En este trabajo no se elige ninguna.

## 8. Trabajo sobre el repositorio

Inspeccionar, sin modificar código productivo:

- tablas FTS5 actuales;
- triggers de sincronización;
- consultas MATCH, ranking y normalización;
- repositorios/casos de uso que consumen FTS;
- filtros que ocurren antes o después de FTS;
- tratamiento actual de ámbito, estados, borrado, redacción, procedencia y conflictos;
- pruebas existentes y huecos observables;
- reconstrucción y eliminación de índices derivados.

La caracterización debe distinguir:

1. capacidad existente;
2. capacidad parcial;
3. ausencia;
4. comportamiento inseguro para 0.2;
5. decisión que pertenece a otro ADR.

## 9. Benchmark mínimo a diseñar

Diseñar un corpus sintético versionable y consultas pareadas que incluyan:

- coincidencia exacta;
- variante léxica y alias confirmado;
- paráfrasis sin solapamiento léxico suficiente;
- negación;
- condición;
- homónimos y alias ambiguos;
- tiempo válido frente a corte de conocimiento;
- varios proyectos con ámbito cerrado;
- contenido archivado, restringido, eliminado, purgado y “no usar”;
- apoyo y refutación;
- conflicto con ambos lados elegibles;
- duplicados con diferencia material;
- resultado crítico frente a ruido abundante;
- ausencia real, no-reportable y fuente inaccesible;
- explicación y traza del plan.

Cada caso debe fijar antes de ejecutar:

- entrada;
- modo;
- propósito y permiso;
- ámbito;
- tiempo objetivo y corte;
- candidatos elegibles/prohibidos;
- orden o conjunto esperado;
- razón esperada;
- métrica y puerta;
- evidencia mínima.

## 10. Entregables de esta ronda

Crear únicamente:

1. `docs/architecture/SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.1_PROPUESTO.md`
2. `docs/architecture/SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.1_PROPUESTO.md`
3. `docs/architecture/SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.1_PROPUESTO.md`

Los tres deben ser documentos de análisis, no decisiones aprobadas.

## 11. Validación de cierre

Antes de terminar:

- comprobar que B04-RF-01–32 están representados sin huecos;
- comprobar RED-027–034 y RED-040 aplicable;
- comprobar las familias PDP mínimas;
- separar hechos verificados del repositorio, obligaciones normativas e hipótesis;
- no inventar cifras de tolerancia;
- no implementar alternativas;
- no modificar `src/`, `tests/`, `migrations/` ni configuración productiva;
- no hacer merge.

## 12. Publicación

Los tres documentos pueden añadirse y publicarse en `evidence/adr001-spikes` con un único commit:

`docs(adr002): add normative inventory and FTS5 baseline plan`

No abrir un PR nuevo. El PR #117 permanece abierto y el merge queda aplazado hasta orden explícita del usuario.

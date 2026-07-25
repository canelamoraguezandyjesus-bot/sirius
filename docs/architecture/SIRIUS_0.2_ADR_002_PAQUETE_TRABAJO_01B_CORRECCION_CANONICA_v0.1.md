# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 01B

## Corrección canónica del inventario, benchmark y apertura de ADR-002

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**No autoriza:** ejecución del benchmark, implementación de alternativas, decisión final de ADR-002 ni merge.

## 1. Motivo

El trabajo 01 produjo una caracterización útil y verificable de FTS5, pero reconstruyó parte del contrato desde resúmenes porque el texto atómico de B04/RED/PDP no estaba en el repositorio.

La fuente canónica externa al repositorio ha sido verificada. La corrección debe conservar toda evidencia técnica válida y sustituir únicamente las reconstrucciones normativas incorrectas o incompletas.

## 2. Hechos canónicos que prevalecen

### 2.1 B04 ya tomó una decisión de producto

`SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO` es canónico desde el 23 de julio de 2026.

Quedaron aprobados:

- la **alternativa B** de B04;
- B04-D01–D16;
- B04-RF-01–32;
- B04-CA-01–50;
- B04-M01–21;
- la política E0–E5;
- las puertas G1–G12;
- las paradas S1–S7.

ADR-002 no puede reabrir esa decisión de producto. Debe decidir la arquitectura técnica que materializa el comportamiento aprobado.

Las alternativas técnicas de ADR-002 deben reformularse como realizaciones compatibles con B04-B. Una variante solo léxica puede conservarse como línea base o hipótesis de falsación, no como producto alternativo equivalente si incumple la expansión aprobada.

### 2.2 Correspondencia exacta B04-RF-01–32

1. Petición con consulta, `operation_id`, propósito, modo, ámbito, tiempo, estados, criticidad, espacios, cardinalidad, límites y traza.
2. Bloquear o aclarar propósito/permiso no autorizado.
3. Adjudicar M1–M5 antes de recuperar y conservarlo en traza.
4. Aclaración mínima ante ambigüedad material antes de generar candidatos.
5. Resolver entidades por ID estable y no fusionar homónimos o alias ambiguos.
6. Aislamiento global, proyecto y multi-proyecto cerrado sin ampliación silenciosa.
7. Aplicabilidad respecto del tiempo objetivo; «ahora» solo como valor predeterminado.
8. Consultas por tiempo válido, evento e historial con corte de registro.
9. G1–G10 antes de candidatos; G11 antes de agrupar/ordenar; G12 antes de límite/handoff.
10. Excluir eliminado, no guardado o purgado.
11. Excluir de M1 y fallback lo marcado «no usar como memoria/no consolidable».
12. Estados especiales solo en modos autorizados.
13. Evidencia externa atribuida y no canónica.
14. Ejecutar E0–E5 sin salto a recuperación amplia.
15. Comenzar por recuperación estructurada y exacta.
16. Variantes léxicas y alias confirmados solo tras insuficiencia anterior.
17. Significado y relaciones con validación de sujeto, polaridad, condición y tiempo.
18. Fuentes e historial solo como etapa autorizada, con clase de evidencia y cotejo con estado vigente/sustituido/contradictorio/candidata.
19. Preservar negación, condición, refutación y postura.
20. Deduplicar solo con equivalencia material, incluido ámbito y postura; conservar procedencias y diferencias.
21. Recuperar y marcar todos los lados elegibles de un conflicto sin resolverlo silenciosamente.
22. Ordenar solo elegibles y emitir razones mínimas por resultado.
23. Propagar nivel, razón, fuente y regla aprobada de criticidad; prohibido auto-marcado libre.
24. Respetar límite objetivo y duro; no ocultar desbordamiento crítico.
25. Adjudicar suficiencia interna por cardinalidad y taxonomía completa; salida externa segura cuando ausencia/no-reportable no puedan distinguirse.
26. Mantener indistinguibles externamente ausencia y no-reportable dentro de tolerancias de texto, estado, conteo y tiempo.
27. Entregar a B05 resultados, estados, evidencia, criticidad, orden inicial, límites y suficiencia.
28. Explicar coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden.
29. Registrar plan reproducible con puertas, etapas, expansiones, agrupaciones y parada.
30. Consultas internas solo desde operación activa que herede propósito, permiso, ámbito, tiempo y límites.
31. Neutralidad tecnológica.
32. Degradación segura por S3/S4/S7 o evidencia insuficiente, con salida parcial reproducible.

### 2.3 Suficiencia no está sin definir

La suficiencia aprobada depende de:

- cardinalidad `EXACTA`, `ACOTADA` o `EXHAUSTIVA`;
- cobertura de críticos elegibles pendientes;
- etapas autorizadas ya ejecutadas;
- taxonomía interna de resultado/ausencia;
- paradas S1–S7.

Solo se expande cuando falta suficiencia o quedan críticos y el siguiente espacio está autorizado.

Una consulta exhaustiva no puede detenerse por S1. La ausencia interna solo se adjudica tras agotar las etapas autorizadas pertinentes y registrar espacios, puertas, parada y limitaciones.

La tarea pendiente de ADR-002 no es inventar el concepto de suficiencia, sino convertir este contrato en una política técnica verificable y fijar las tolerancias que B04/PDP delegaron.

### 2.4 Criticidad sí está definida

La criticidad procede de uno de estos orígenes trazables:

- requisito o decisión aprobada;
- acto explícito;
- etiqueta de escenario;
- regla operativa aprobada con ID y evidencia.

No puede autoasignarse por intuición libre. Debe transportar nivel, razón, fuente y regla hasta B05 y es corregible, no una nueva verdad canónica.

### 2.5 RED/PDP ya tienen mapeo exacto

RED-027–034 no deben reconstruirse por resumen. El Plan de Pruebas aprobado ya fija:

- RED-027 → B04 RF-01–04 → F01–F06 → B04-CA-01/05/08/15 → B04-M13/M15.
- RED-028 → RF-07–08 → F02/F03 → B04-CA-06/07/32/47 → B04-M11.
- RED-029 → RF-18/RF-29 → F24 → B04-CA-40/44 → B04-M15.
- RED-030 → RF-20–24 → F10/F14 → B04-CA-19/31/38 → B04-M10.
- RED-031 → RF-25/M09 → F23 → B04-CA-17/36 → B04-M09.
- RED-032 → RF-26/M20 → F11/F23 → usar el mapeo exacto del Plan canónico.
- RED-033 → M16/CA-39 → F22 → tolerancia de orden y equivalencia observable.
- RED-034 → RF-31–32 → F10/F23 → fuente inaccesible y degradación parcial reproducible.
- RED-040 pertenece a B05/ADR-003B; ADR-002 solo registra la interfaz de reintento acotado, sin diseñarla ni usarla como requisito propio de selección técnica.

## 3. Correcciones obligatorias

Actualizar, sin borrar sus versiones v0.1:

1. `SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.2_PROPUESTO.md`
2. `SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.2_PROPUESTO.md`
3. `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md`
4. `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`

### 3.1 Inventario v0.2

- Sustituir el reparto interpretativo por la correspondencia exacta RF-01–32.
- Corregir expresamente: ámbito = RF-06; tiempo objetivo = RF-07; RF-05 incluye ID estable y no fusión de homónimos/alias ambiguos.
- Recalcular las clasificaciones EXISTENTE/PARCIAL/AUSENTE/INSEGURO/OTRO-ADR sin cambiar evidencia técnica salvo que el número corregido lo exija.
- Eliminar como incertidumbres «suficiencia no definida» y «crítico no definido».
- Mantener como incertidumbre real el Registro de Tolerancias y las elecciones técnicas todavía abiertas.

### 3.2 Línea base FTS5 v0.2

Conservar las mediciones válidas del v0.1. Corregir únicamente trazabilidad normativa y numeración.

Los dos hallazgos inseguros se conservan, pero se trazan así:

- fuga de ámbito → B04-RF-06;
- negación invisible → B04-RF-19.

### 3.3 Benchmark v0.2

- Los quince tipos C-01–C-15 pueden conservarse como agrupación arquitectónica, nunca como reemplazo de los 50 casos canónicos B04.
- Trazar cada clase a casos exactos B04-CA/PDP-CA ya aprobados.
- No crear nuevas referencias que contradigan las referencias congeladas.
- Distinguir tres niveles: casos canónicos reutilizados, casos arquitectónicos nuevos necesarios y ablaciones técnicas.
- Mantener sin cifras aquello que depende del Registro de Tolerancias.
- La línea base FTS5 puede ejecutarse contra los casos expresables; los no expresables se marcan como incapacidad de la línea base, no se eliminan.

### 3.4 Apertura ADR-002 v0.2

Reformular la pregunta material:

> ¿Qué arquitectura técnica de índices, señales y ranking implementa de forma mínima, explicable, borrable, portable y medible la alternativa B y el contrato B04 ya aprobados, preservando FTS5 cuando aporte valor sin convertirlo en excepción?

Las alternativas excluyentes deben ser técnicas y compatibles con B04-B. Como mínimo distinguir:

- T1: FTS5 como base + semántica tardía; relaciones resueltas desde el canon sin índice relacional dedicado.
- T2: FTS5 como base + semántica tardía + índice relacional derivado tardío.
- T3: índice léxico alternativo + semántica tardía; relaciones desde canon.
- T4: índice léxico alternativo + semántica tardía + índice relacional derivado.

Puede ajustarse la formulación si el análisis demuestra otra partición más limpia, pero ninguna alternativa puede reabrir E0–E5, G1–G12, S1–S7 o la incorporación tardía aprobada de significado/relaciones.

La variante solo léxica se mantiene como control/falsación, no como candidata final si no satisface B04.

## 4. Registro de Tolerancias

No crearlo dentro de esta corrección.

Al cerrar 01B, el siguiente paquete será específico para:

- recuperar tolerancias ya congeladas en B04/PDP;
- identificar solo las cifras realmente delegadas a Arquitectura;
- proponer el Registro de Tolerancias v0.1;
- obtener aprobación explícita antes de ejecutar decisiones dependientes de latencia, coste, tamaño o estabilidad.

## 5. Validación

La revisión debe confirmar:

- 32/32 RF exactos, sin reconstrucción propia;
- RED-027–034 trazados al mapeo canónico;
- RED-040 tratado solo como interfaz con ADR-003B;
- ningún cambio en hechos medidos de FTS5 sin evidencia nueva;
- B04-B no se reabre;
- benchmark no sustituye B04-CA-01–50 ni PDP;
- ningún cambio fuera de `docs/architecture/`;
- sin benchmark ejecutado, sin prototipos, sin merge.

## 6. Publicación

Commit único:

`docs(adr002): correct inventory against canonical B04`

Push a `evidence/adr001-spikes`. No abrir otro PR y no fusionar el PR #117.

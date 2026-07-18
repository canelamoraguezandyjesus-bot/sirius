# B4 — Plan de ejecución operativo

## Estado y autoridad

El usuario autorizó explícitamente el 18 de julio de 2026 dividir B4 para reducir riesgo, tamaño de diff y tiempo de revisión.

Esta división es exclusivamente operativa. No cambia la Definición de Producto, la Arquitectura Técnica, las ATD ni los requisitos aprobados. B4 continúa cerrando D-03 y cubriendo RF-019 a RF-026 y PA-010 a PA-016.

Estado inicial: **AUTORIZADO Y NO INICIADO**.

## Objetivo de B4

Completar la capacidad observable de eventos, recuerdos y decisiones para que Sirius pueda:

- guardar memoria solo por orden o confirmación explícita;
- conservar y abrir un origen consultable;
- distinguir exploración, propuesta y decisión aprobada;
- corregir y sustituir sin destruir el historial;
- archivar y eliminar según la política aprobada;
- detectar incompatibilidades y no resolverlas silenciosamente.

## Base ya implementada

B4 no parte de cero. V4 ya incluye:

- recuerdo genérico versionado;
- origen obligatorio como valor no vacío;
- corrección mediante revisión nueva;
- archivo;
- redacción del contenido estructurado al eliminar.

Los subbloques siguientes deben reutilizar y completar esa infraestructura. No deben crear un segundo sistema de memoria paralelo.

## Reglas comunes

- Una rama y una pull request por subbloque.
- Ejecución secuencial al principio; no trabajar dos subbloques de B4 en paralelo.
- Cada cambio debe enlazar requisitos, pruebas y archivos afectados.
- No ampliar el modelo conceptual aprobado: evento, mensaje, recuerdo, decisión y proyecto.
- No introducir guardado proactivo, embeddings, RAG, grafos ni multiagente.
- No modificar documentos canónicos.
- No declarar superadas pruebas manuales o con proveedor real.
- `scripts/check.ps1` y CI deben quedar verdes antes del merge.
- Máximo dos ciclos de revisión y corrección por PR. Si no converge, devolver `BLOCKED_BY_DECISION`.
- El usuario conserva la autorización de merge.

## B4a — Origen consultable y guardado manual

### Alcance

- Representación persistente del evento de origen aprobado por la arquitectura.
- Enlace real entre recuerdo y evento o mensaje de procedencia.
- Caso de uso explícito para guardar un recuerdo manual.
- Consulta del origen sin acceso directo de la interfaz a SQLite.
- Fecha, estado y versión observables.

### Trazabilidad

- RF-019 — Guardar recuerdo.
- RF-021 — Consultar origen.
- PA-010 — Guardar memoria manual.

### Resultado verificable

Al ordenar guardar una preferencia o un hecho, se crea un recuerdo con origen, fecha, estado y versión, y el origen puede consultarse posteriormente.

### Fuera de alcance

- decisiones;
- sustitución;
- conflictos;
- archivo o eliminación desde interfaz;
- búsqueda FTS5 general;
- panel de contexto completo de B5.

## B4b — Decisiones y aprobación explícita

### Alcance

- Tipo o entidad de decisión sobre la infraestructura de conocimiento existente.
- Asunto, proyecto, estado, versión, fecha y origen.
- Estados mínimos necesarios para propuesta y aprobación.
- Caso de uso que exige confirmación explícita para aprobar.
- Una exploración conversacional no crea una decisión aprobada.

### Trazabilidad

- RF-020 — Guardar decisión.
- PA-011 — No convertir exploración en decisión aprobada.

### Resultado verificable

Debatir alternativas no genera una decisión aprobada. Una aprobación explícita sí crea o activa la decisión correspondiente con su origen y versión.

### Fuera de alcance

- sustitución de otra decisión;
- precedencia frente a recuerdos;
- resolución de conflictos;
- panel de contexto de B5.

## B4c — Corrección y sustitución

### Alcance

- Consolidar la corrección existente bajo los contratos vigentes.
- Nueva revisión inmutable y puntero autoritativo a la vigente.
- Relación explícita de sustitución entre decisiones.
- Exclusión de revisiones sustituidas del contexto normal.
- Consulta histórica sin tratar versiones anteriores como vigentes.

### Trazabilidad

- RF-022 — Corregir.
- RF-023 — Sustituir.
- PA-012 — Corregir y versionar.
- PA-013 — Sustituir decisión.

### Resultado verificable

Una corrección mantiene la versión anterior como histórica y activa la nueva. Una decisión sustituta queda enlazada con la sustituida y solo la nueva entra en el contexto ordinario.

## B4d — Archivo, eliminación y redacción de origen

### Alcance

- Archivo consultable fuera del contexto ordinario.
- Eliminación con confirmación explícita.
- Borrado del contenido estructurado y de sus índices.
- Conservación del marcador mínimo sin contenido.
- Elección explícita de redactar o conservar el mensaje fuente.
- Advertencia de que una copia antigua puede reintroducir datos eliminados.

### Trazabilidad

- RF-024 — Archivar.
- RF-025 — Eliminar.
- PA-015 — Archivar.
- PA-016 — Eliminar.
- SP-06 — Borrado y copia antigua.

### Resultado verificable

Un elemento archivado sigue siendo consultable y deja de usarse normalmente. Un elemento eliminado pierde su contenido conforme a la opción elegida y solo conserva el marcador mínimo autorizado.

## B4e — Precedencia y conflictos

### Alcance

- Detección determinista de recuerdos vigentes incompatibles del mismo asunto.
- Prioridad de una decisión aprobada vigente sobre recuerdos generales incompatibles del mismo asunto.
- Solicitud de aclaración cuando no exista precedencia inequívoca.
- Prohibición de elegir silenciosamente.
- Pruebas de dominio y aplicación independientes del proveedor real.

### Trazabilidad

- RF-026 — Detectar conflicto.
- PA-014 — Conflicto.
- DR-011 — Precedencia y conflictos de memoria.

### Resultado verificable

Ante dos recuerdos incompatibles sin precedencia, Sirius devuelve un conflicto explícito y solicita aclaración. Cuando existe una decisión aprobada vigente del mismo asunto, esa decisión prevalece de forma trazable.

## B4f — Integración observable y cierre de B4

### Alcance

- Integrar las operaciones aprobadas en las superficies existentes sin crear una aplicación de gestión independiente.
- Completar casos de uso, composición, interfaz mínima y pruebas GUI necesarias.
- Añadir indexación o búsqueda local únicamente en la medida necesaria para PA-010 a PA-016 y para el posterior B6.
- Actualizar la documentación operativa y la matriz de evidencia.

### Trazabilidad

- PA-010 a PA-016 completas.
- Parte correspondiente de PA-008 y PA-E2E-01 preparada, sin declararla formalmente superada mientras dependa de proveedor real o evaluación humana.

## Puerta de entrada de cada subbloque

Antes de comenzar:

1. El subbloque anterior está fusionado y CI está verde.
2. La tarea identifica requisitos y pruebas exactas.
3. Se ha inspeccionado el código existente para evitar duplicación.
4. El diff previsto está acotado y no requiere una decisión nueva.
5. La rama parte del `main` vigente.

## Criterio de cierre de cada subbloque

Un subbloque queda `READY_FOR_HUMAN_REVIEW` cuando:

- cumple exclusivamente su alcance;
- añade o actualiza las pruebas previstas;
- `scripts/check.ps1` pasa;
- CI está verde;
- no quedan hallazgos `BLOCKER` o `HIGH`;
- la documentación operativa coincide con el comportamiento;
- la PR explica límites y pendientes;
- no se han declarado superadas pruebas manuales no ejecutadas.

## Estados finales permitidos

- `READY_FOR_HUMAN_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

## Criterio de cierre de B4 completo

B4 solo podrá marcarse terminado cuando:

- B4a a B4f estén fusionados;
- RF-019 a RF-026 tengan trazabilidad verificable;
- PA-010 a PA-016 existan y pasen en la parte automatizable;
- no queden defectos bloqueantes o altos de D-03;
- las revisiones históricas, archivadas, sustituidas o eliminadas no entren indebidamente en el contexto vigente;
- la documentación operativa y el registro de evidencia estén actualizados;
- el usuario haya autorizado todos los merges.

## Primera tarea funcional

La primera tarea funcional de esta secuencia será **B4a — origen consultable y guardado manual**. No debe iniciarse hasta superar la prueba de humo cloud definida en `docs/implementation/CLOUD_SMOKE_TEST.md` o hasta que el usuario decida explícitamente continuar con el flujo local actual.
# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 03B

## Corrección canónica del corpus y separación conformidad/rendimiento

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN EXPERIMENTAL DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**Dependencias:** resolución A/B/C/D aprobada en `fe85786bc8150d91d05f6beda864386a73a6a59d`; auditoría adversarial independiente del corpus v0.1  
**No autoriza:** congelar TOL-208, ejecutar T0, implementar o ejecutar ADR002-A/B/C/D, aprobar TOL-207, satisfacer TOL-209/TOL-210 ni merge.

## 1. Objetivo

Corregir sin rehacer desde cero el corpus v0.1 y producir una versión v0.2 fiel al canon, protegida por validación automática contra las fuentes DOCX.

La ronda debe cerrar:

- B-01 · asignaciones RED↔CA↔M↔F incompletas;
- B-02 · inferencias etiquetadas como canon;
- B-03 · clasificación T0 presentada como resultado antes de ejecutar;
- M-01 · ausencia de ramas M4;
- M-02 · casos multirrama aplanados;
- M-03 · ficha de caso incompleta frente a PDP §7;
- M-04 · ausencia de PDP-CA aplicables;
- M-05 · mezcla indebida de corpus de conformidad y rendimiento;
- M-07 · cardinalidad/parada inferidas presentadas como canónicas;
- defectos menores de literalidad y denominadores de cobertura.

## 2. Fuentes de autoridad

Leer íntegramente:

- los tres DOCX de `docs/architecture/canonical_sources/`;
- `docs/architecture/canonical_sources/MANIFEST.md`;
- `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md`;
- `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md`;
- `SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.1_PROPUESTO.md`;
- `SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.1_PROPUESTO.md`;
- el corpus, referencias, validador y pruebas v0.1;
- la auditoría adversarial independiente que detectó los defectos.

Las fuentes DOCX mandan sobre cualquier resumen o artefacto derivado.

## 3. Decisión metodológica: dos corpus vinculados

TOL-208 no usará un único corpus para dos objetivos incompatibles.

### 3.1 Corpus de conformidad

- pequeño, semánticamente denso y legible;
- contiene los anclajes exactos de B04-CA y PDP-CA aplicables;
- sirve para adjudicar puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, ausencia y explicación;
- conserva los 92 elementos actuales cuando sigan siendo útiles, pero puede ajustarlos para hacer falsables las ramas canónicas;
- no se usa para fijar cifras de rendimiento absoluto.

### 3.2 Corpus de rendimiento

- determinista y generado desde los mismos anclajes semánticos;
- escala de referencia: **5.000 mensajes, 500 recuerdos y 50 decisiones**, para ser comparable con la línea base que produjo las tolerancias LAB-LINUX;
- añade ruido y volumen sin alterar las respuestas canónicas de los anclajes;
- debe permitir proyecciones reproducibles a 500, 5.000 y 50.000 elementos cuando corresponda;
- se usa para latencia, tamaño, construcción, reconstrucción y estabilidad;
- no crea nuevas referencias funcionales ni sustituye al corpus de conformidad.

Ambos comparten versión de contrato, semilla y un manifiesto que declara su relación. Cambiar cualquiera exige nueva versión explícita.

## 4. Correcciones obligatorias

### 4.1 Anexo B · RED↔CA↔M↔F

Restituir como mínimo las asignaciones canónicas verificadas por la auditoría:

- RED-027: CA-01, CA-05, CA-08, CA-15; M13 y M15 donde el Anexo B los fija.
- RED-028: CA-06, CA-07, CA-32, CA-47; F02/F03 donde corresponda.
- RED-029: CA-40, CA-44; M15 en CA-44.
- RED-030: CA-19, CA-31, CA-38; M10 en CA-31 y CA-38.
- RED-034: CA-18, CA-24; M21 en ambos.

Las asociaciones adicionales solo pueden conservarse si están diferenciadas como `traza_adicional_derivada`, nunca como sustitución del Anexo B.

Crear una tabla automática de referencia extraída del DOCX y compararla exactamente con los artefactos.

### 4.2 Canon frente a instanciación

En `references_v0_2.json`, separar obligatoriamente:

```json
{
  "canonico": {
    "fuente": "B04 v1.0 APROBADO §17/§17.1",
    "riesgo": "...",
    "entrada": "...",
    "resultado_esperado": "...",
    "fallo_observable": "...",
    "modificable": false
  },
  "instanciacion": {
    "fuente": "Matriz/corpus ADR-002 v0.2 PROPUESTO",
    "ramas": [],
    "cardinalidad": "...",
    "etapa": "...",
    "parada": "...",
    "orden": "...",
    "elegibles": [],
    "prohibidos": [],
    "estado": "PROPUESTO_NO_CONGELADO"
  }
}
```

Solo los cinco campos del bloque `canonico` pueden declararse congelados por B04 §17/§17.1.

Cardinalidad, consulta concreta, etapa, parada, orden, elegibles y prohibidos son instanciación arquitectónica salvo que una fuente canónica concreta los fije literalmente. Cada campo debe registrar su fuente individual.

### 4.3 Ramas M4

Dentro del mismo ID canónico, no creando CA nuevos, instanciar las ramas positivas exigidas por:

- CA-09: exclusión en M1 y visibilidad en M4;
- CA-10: no recuperar como conocimiento y mostrar estado en M4 cuando se pide;
- CA-24: exclusión en M1 y visibilidad en auditoría/M4;
- CA-49: candidata visible en M4.

El validador debe exigir que M1–M5 aparezcan al menos una vez cuando el canon los requiera y que ninguna rama canónica desaparezca.

### 4.4 Casos multirrama

Representar dentro del mismo CA:

- CA-36: histórico, candidata y fuera de ámbito, con estados seguros diferenciados;
- CA-47: consultas separadas por `occurred_at`, `valid_time` y `recorded_at`, con resultados distintos;
- CA-48: par diferencial autorizado/no autorizado y tolerancia explícita pendiente de TOL-209.

Un sistema que devuelva la misma respuesta a todas las ramas debe fallar cuando el canon exige diferencia.

### 4.5 Ficha PDP §7

Añadir a cada caso/rama, además de los campos existentes:

- `objetivo`;
- `unidad_de_trabajo`;
- `tolerancias`;
- `senales_observables`;
- `condicion_insuficiencia_para_expandir`;
- fuente de cada campo;
- estado `CANONICO`, `DERIVADO_PROPUESTO` o `PENDIENTE_TOL209`.

No inventar bandas pendientes. Para CA-39/CA-48 y otros afectados, registrar la dependencia exacta de TOL-209.

### 4.6 PDP-CA

Extraer del Plan canónico los PDP-CA transversales y determinar cuáles son aplicables a ADR-002 por destino, RF, RED o métrica.

- Instanciar los aplicables como nivel 1, preservando su identificador y referencia canónica.
- Los no aplicables se registran en una matriz de exclusión con su ADR responsable.
- No afirmar cobertura de los 304 casos del Plan completo.
- Distinguir `casos_ejecutados_por_ADR002`, `casos_tocados_por_dependencia` y `casos_fuera_de_alcance`.

### 4.7 Clasificación frente a T0

Eliminar del artefacto congelable cualquier afirmación de que un caso pasa o falla T0 antes de ejecutarlo.

Sustituir por:

- `estado_t0: NO_MEDIDO`;
- `expresabilidad_prevista: ...`;
- `fundamento_de_prevision: ...`;
- `no_es_veredicto: true`.

CA-39 debe marcarse como no ejecutable con una sola implementación: requiere comparación entre dos realizaciones.

Aplicar un criterio único de expresabilidad a CA-01, CA-04, CA-09, CA-10 y CA-11. Si una dimensión requerida no existe en T0, no declarar que el caso “debería pasar” por un resultado accidentalmente coincidente.

La clasificación real solo se crea tras ejecutar T0.

### 4.8 Cardinalidad y parada

No presentar `EXHAUSTIVA` o `S5` como derivadas de B04 §17/§17.1 salvo que el caso las fije literalmente.

Para CA-02, CA-22, CA-39 y CA-47:

- retirar la atribución canónica de `EXHAUSTIVA` y `S5`;
- conservar únicamente la regla canónica demostrable: si una instanciación es `EXHAUSTIVA`, S1 está prohibida;
- CA-39 no usa vocabulario de parada de recuperación salvo que su instanciación lo justifique expresamente.

### 4.9 Literalidad

Restaurar carácter a carácter riesgo, entrada, resultado esperado y fallo observable, incluidas las comillas tipográficas de CA-17, 18, 21, 29, 36, 37, 45 y 47.

### 4.10 Familias PDP

Reportar por separado:

1. destino directo de ADR-002 según ARQ-00 §20;
2. entradas obligatorias de ADR-002 según la especificación vigente;
3. familias tocadas por casos, sin atribuir su cierre a ADR-002;
4. familias fuera de alcance.

No utilizar `20/25` como “cobertura de ADR-002”.

## 5. Validador contra fuentes canónicas

El validador v0.2 debe abrir los DOCX materializados y comprobar automáticamente:

1. SHA-256 contra `MANIFEST.md`;
2. los 50 CA una vez cada uno;
3. riesgo, entrada, resultado esperado y fallo observable carácter a carácter;
4. asignaciones del Anexo B RED↔CA↔M↔F;
5. ramas canónicas requeridas;
6. campos PDP §7;
7. separación canon/instanciación;
8. ausencia de veredictos T0 antes de ejecución;
9. determinismo byte a byte;
10. dimensiones y relaciones requeridas;
11. consistencia entre corpus de conformidad y rendimiento.

No basta con comprobar identificadores contra una lista blanca.

El lector DOCX debe ser reproducible y local. Puede usar ZIP/XML estándar o una dependencia ya presente; no añadir una dependencia productiva.

## 6. Rutas y versiones

Conservar íntegro v0.1.

Crear bajo `experiments/adr002/benchmark/`:

- `conformance_corpus_v0_2.json`
- `performance_corpus_v0_1.json`
- `cases_v0_2.json`
- `references_v0_2.json`
- `pdp_cases_v0_1.json`
- `benchmark_manifest_v0_2.json`
- código generador/validador y pruebas v0.2 necesarias.

Crear:

- `docs/architecture/SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.2_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.2.json`
- `artifacts/adr002_benchmark_preparation/INFORME_CORRECCION_CORPUS_v0.2_PROPUESTO.md`

No modificar `canonical_sources/`, versiones v0.1, documentos aprobados ni código productivo.

## 7. Validación

Ejecutar:

- validador v0.2 contra los DOCX;
- pytest de `experiments/adr002/benchmark/`;
- Ruff format/check sobre esa ruta;
- regeneración doble y comparación byte a byte;
- comprobación de tamaños y escalas de ambos corpus;
- `git status`.

Confirmar:

- B-01, B-02, B-03 y M-01–M-05/M-07 cerrados;
- 50 CA sin ausencias ni duplicados;
- PDP-CA aplicables materializados o exclusión canónica justificada;
- ninguna referencia canónica reinterpretada;
- ningún veredicto T0 emitido;
- corpus de conformidad y rendimiento separados;
- ningún cambio productivo;
- TOL-207/208/209/210 siguen no satisfechas;
- sin T0, sin candidatos y sin merge.

## 8. Publicación

Commit único:

`test(adr002): correct canonical benchmark corpus`

Push a `evidence/adr001-spikes`. No abrir otro PR ni fusionar el PR #117.

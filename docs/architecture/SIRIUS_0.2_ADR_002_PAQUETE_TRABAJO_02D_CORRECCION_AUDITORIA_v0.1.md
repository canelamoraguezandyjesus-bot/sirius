# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 02D

## Corrección de la auditoría adversarial del Registro de Tolerancias

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN DOCUMENTAL DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**Entrada auditada:** `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md`  
**Veredicto de auditoría:** NO APROBABLE · pasa a APROBABLE CON CORRECCIONES al resolver B-01, B-02 y B-03  
**No autoriza:** nuevas mediciones, ejecución de T0/T1–T4, implementación, aprobación automática ni merge.

## 1. Objetivo

Emitir un Registro de Tolerancias v0.4 estrictamente correctivo que:

1. restaure la integridad documental perdida entre v0.2 y v0.3;
2. corrija las cifras de TOL-101 y TOL-102 contra la evidencia real;
3. complete la neutralidad para sustratos léxicos no medidos y etapas semánticas;
4. cierre las lagunas de congelación, corpus, protocolo, almacenamiento y purga física;
5. no cambie ninguna medición ni rebaje ninguna puerta canónica.

## 2. Fuentes

Leer íntegramente:

- `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.3_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.2_PROPUESTO.md`
- `artifacts/adr002_tolerances/INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`
- `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json`
- la auditoría adversarial recibida tras v0.3.

No afirmar que las fuentes B04/PDP/ARQ-00 completas están en el repositorio. Registrar como bloqueo de arranque del benchmark su materialización pendiente.

## 3. Bloqueantes

### 3.1 B-01 · Integridad de v0.2 a v0.3

Restaurar literalmente desde v0.2 el contenido completo de:

- TOL-101;
- TOL-102;
- TOL-103;
- TOL-105;
- TOL-106;
- TOL-107;
- TOL-201;
- TOL-204.

Después aplicar únicamente los cambios explícitos de este paquete.

El historial de v0.4 debe enumerar cada cambio real. Prohibido declarar “sin cambios” para una fila cuyo texto difiera.

Conservar expresamente:

- TOL-101: justificación de neutralidad del margen y relación coste/aportación;
- TOL-105: `rebuild` interno no satisface ADR-001 y no cuenta como evidencia;
- TOL-107: régimen sub-milisegundo evaluado en valor absoluto y límites de las sesiones intra-proceso;
- TOL-201: fracción de signo nunca como protección única, condiciones 3 y 4 obligatorias y deltas observados;
- notas de corrección v0.1 → v0.2.

### 3.2 B-02 · TOL-102

La evidencia completa incluye:

- escenarios generales: peor P95 147,2 ms y P99 158,58 ms en sesiones;
- TOL-002: P95 157,83 / 173,20 ms y P99 160,33 / 181,82 ms.

Corregir la fila para que no afirme que 150 ms es techo de no regresión de toda la línea base.

Decisión de v0.4:

- `TOL-102B · Línea base extremo a extremo`: dato comparativo LAB-LINUX; peor observado P95 **173,20 ms** y P99 **181,82 ms**. No descarta candidatos.
- `TOL-102C · Límite extremo a extremo del candidato`: `REGLA_CONFIRMADA_VALOR_CANDIDATO_Y_ENTORNO`; cada candidato congela antes de ejecutar su objetivo y límite duro extremo a extremo.
- El coste incremental de significado y relaciones se declara por etapa en TOL-202.
- Ningún candidato puede usar el barrido prohibido de T0 como justificación para un coste alto.
- El resultado solo descarta si incumple su límite congelado o el entorno local de referencia, no por superar el tiempo de T0.

Mantener un tratamiento coherente de percentiles con n=30: describen máximos/colas observadas, no una cola caracterizada.

### 3.3 B-03 · TOL-101

Corregir los datos contra el JSON:

- P95 observado: **0,188–1,004 ms**;
- P99 observado: **0,210–1,415 ms**;
- muestra máxima observada: **2,3934 ms**.

Mantener el objetivo P95 ≤ 1,5 ms únicamente como propuesta comparativa para el FTS5 medido. El margen real respecto al peor P95 es aproximadamente ×1,49, no ×2,05.

Separar:

- `TOL-101L · FTS5 medido`: comparativa LAB-LINUX;
- `TOL-101A · Sustrato léxico alternativo`: valor congelado por candidato y entorno antes de ejecutar.

Eliminar o definir de forma exacta “combinada con TOL-102, descarta”. Recomendación: eliminarla; cada fila aplica su consecuencia propia.

## 4. Neutralidad y comparabilidad

### 4.1 Sustrato léxico alternativo

TOL-101L, TOL-104L y los tiempos léxicos de TOL-105 son datos del FTS5 medido, no límites universales para T3/T4.

Un sustrato léxico alternativo debe declarar y congelar antes de ejecutar:

- latencia;
- tamaño;
- construcción;
- reconstrucción;
- borrado;
- crecimiento por escala;
- fundamento de cada límite.

La desviación respecto de FTS5 se informa como comparación, no como déficit automático. La continuidad con FTS5 es un valor favorable, nunca una excepción ni un patrón obligatorio.

### 4.2 Etapa semántica y relacional

TOL-202 debe contener para cada candidato:

- coste incremental por E0–E5;
- coste de inferencia o generación de señal de consulta;
- coste local y externo separados;
- objetivo y límite duro por etapa congelados antes de ejecutar;
- coste extremo a extremo resultante.

No usar TOL-102B para preseleccionar modelo, dimensión, precisión, cuantización o reordenador.

### 4.3 TOL-107 en dos regímenes

Definir:

- régimen relativo para magnitudes suficientemente grandes;
- régimen absoluto para magnitudes sub-milisegundo o próximas al suelo de medición.

El umbral de conmutación y la banda absoluta se congelan con el protocolo y entorno antes del benchmark, no después de ver candidatos.

Si se incumple la estabilidad temporal, la comparación se invalida y se repite una vez bajo condiciones controladas. Si vuelve a fallar, el candidato queda `NO EVALUABLE` en rendimiento; no se crea un bucle ilimitado.

## 5. Condiciones de arranque del benchmark

### 5.1 Fuentes canónicas

El benchmark no puede comenzar hasta que el repositorio contenga o enlace de forma verificable las fuentes completas:

- B04 v1.0 APROBADO, incluidos CA-01–50, M01–21, D01–16, E0–E5, G1–G12 y S1–S7;
- Plan de Pruebas + RED/PDP v1.0 APROBADO;
- ARQ-00 v1.0 APROBADO.

Crear en v0.4 una puerta `SRC-ADR002-01`: ausencia de cualquiera bloquea materialización del nivel 1 y ejecución del benchmark.

### 5.2 Corpus y escala

Toda cifra LAB-LINUX queda vinculada a:

- versión de corpus;
- número de mensajes, recuerdos, decisiones y proyectos;
- longitud media y distribución del texto;
- configuración y commit.

Regla de arranque:

1. congelar corpus definitivo del benchmark;
2. ejecutar T0 sobre ese mismo corpus;
3. rederivar la comparación de línea base antes de ejecutar T1–T4.

No aplicar directamente cifras del corpus 5.000/500 a otro volumen.

### 5.3 Ficha de candidato

Crear como parte del Registro una especificación obligatoria de `FICHA_CANDIDATO_ADR002` versionada y comprometida antes de la primera ejecución.

Debe contener:

- ID y versión;
- arquitectura T1–T4;
- componentes y versiones;
- corpus y commit;
- TOL-101A/102C/104A/201/202/203;
- límite absoluto de almacenamiento del entorno;
- límites de tiempo de construcción, reconstrucción y borrado;
- protocolo de medición;
- modelo de amenaza TOL-002;
- huella del candidato.

La ficha no se registra en la ficha de cada caso. Es un artefacto propio del candidato y se referencia desde cada ejecución.

### 5.4 Protocolo común de medición

Añadir `PROTOCOLO_MEDICION_ADR002` común y congelado:

- reloj monotónico;
- fixtures fuera del cronómetro;
- warm-up declarado y descartado;
- nearest-rank;
- mínimo 30 repeticiones; 100 cuando el coste sea bajo;
- al menos 5 sesiones independientes para estabilidad;
- misma máquina y proceso en comparaciones pareadas;
- semilla fija;
- orden intercalado de candidatos para reducir deriva;
- registro de carga e incidencias;
- fórmula de variación;
- una única repetición controlada cuando la comparación sea inválida.

### 5.5 Almacenamiento común

Antes del benchmark debe congelarse un límite absoluto del entorno local de laboratorio en bytes disponibles para derivados.

Todos los candidatos deben reportar en una escala común:

- bytes totales;
- bytes por elemento;
- 500 / 5.000 / 50.000 unidades;
- porcentaje del presupuesto absoluto del entorno.

El límite propio de TOL-104A no sustituye esta escala común.

### 5.6 Límites de ciclo por candidato

TOL-203 debe exigir límite congelado para cada magnitud:

- tamaño;
- construcción;
- reconstrucción;
- borrado.

El mínimo de 30 repeticiones aplica también a la tasa del 100 % de restitución, integridad y borrado cuando la operación sea ejecutable.

La no ejecutabilidad se declara y justifica antes de la ejecución; nunca después.

## 6. Purga física

Añadir `ADR002-TOL-206 · Purga física del derivado`:

- tras borrado y secuencia declarada de checkpoint/journal/VACUUM, ningún fragmento recuperable del derivado permanece en `.db`, `-wal`, `-shm` o `-journal` dentro del modelo de amenaza;
- resultado booleano, 100 %, sin margen;
- medible en LAB-LINUX y obligatorio de reverificar en Windows por TOL-205;
- todo payload literal o representación reversible incluida en un índice forma parte del derivado;
- fallo descarta por puerta 5.

No ejecutar ahora la prueba; incluirla en el benchmark/ciclo de candidato.

## 7. Coherencia documental

Añadir notas de superación cruzada en Inventario y Especificación del benchmark, sin reescribirlos completos:

- TOL-204 ya no es incertidumbre: 0 críticos elegibles pendientes;
- el Registro v0.4 sustituye v0.3;
- la ficha de candidato y protocolo común son artefactos obligatorios;
- el nivel 1 queda bloqueado hasta materializar las fuentes canónicas.

## 8. Entregables

Crear únicamente:

1. `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`
2. `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md`
3. `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`
4. `docs/architecture/SIRIUS_0.2_ADR_002_NOTA_SUPERACION_01_v0.1_PROPUESTO.md`

No modificar v0.1, v0.2 ni v0.3. No modificar mediciones, código ni artefactos experimentales.

## 9. Validación

Comprobar:

- B-01, B-02 y B-03 cerrados;
- cada cambio v0.3 → v0.4 enumerado;
- cifras TOL-101 corregidas contra JSON;
- TOL-102 separada en comparativa de línea base y valor por candidato/entorno;
- neutralidad de sustrato léxico alternativo;
- protocolo común y ficha de candidato existentes;
- corpus vinculado a cifras;
- almacenamiento absoluto congelado antes del benchmark;
- límites de ciclo congelados antes de ejecutar;
- TOL-206 presente;
- fuentes canónicas completas declaradas puerta de arranque;
- ningún cambio en `experiments/`, `artifacts/`, `src/`, `tests/`, `migrations/` o configuración;
- sin nuevas mediciones, sin candidatos y sin merge.

## 10. Publicación

Commit:

`docs(adr002): correct tolerance audit findings`

Push a `evidence/adr001-spikes`. No abrir otro PR ni fusionar el PR #117.

# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 02

## Registro de tolerancias y medición reproducible de línea base

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA MEDICIÓN EXPERIMENTAL AISLADA  
**Rama:** `evidence/adr001-spikes`  
**Dependencias satisfechas:** ADR-001 v1.1 APROBADO; ADR-002 trabajo 01B completado en `17823b2b3112089645ff93af084a9d2538bba5c4`  
**No autoriza:** benchmark comparativo T1–T4, implementación productiva, elección de alternativa, cambios en Sirius 0.1 ni merge.

## 1. Objetivo único

Crear y justificar el Registro de Tolerancias que ADR-002 necesita antes de ejecutar el benchmark.

Esta ronda combina:

1. recuperación literal de reglas y umbrales ya canónicos;
2. medición real de la línea base FTS5;
3. propuesta explícita de los pocos valores arquitectónicos todavía no fijados;
4. declaración del punto exacto en que se congelarán los valores dependientes de cada candidato.

No se ejecutan todavía T1–T4.

## 2. Fuentes obligatorias

Leer íntegramente:

- `docs/architecture/SIRIUS_0.2_ADR_001_MODELO_FISICO_v1.1_APROBADO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md`
- este paquete.

El Plan de Pruebas canónico ya fijó TOL-001–TOL-006 y B04-M01–M21. Este paquete reproduce únicamente lo necesario para evitar reconstrucciones libres.

## 3. Reglas canónicas que no pueden modificarse

### 3.1 TOL-001–TOL-006

- **TOL-001 · Orden y equivalencia B04/B05:** mismos críticos, estados, razones y dependencias. El orden no crítico solo puede variar dentro de una clase de equivalencia prefijada y sin alterar el resultado material. **100 % críticos; ≥95 % global.**
- **TOL-002 · Indistinguibilidad temporal:** pares con igual configuración y entorno deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. La banda concreta se congela con el candidato antes de ejecutar.
- **TOL-003 · Carga e interrupciones:** máximo una interrupción ordinaria no solicitada por unidad de trabajo; excepciones solo por privacidad o criticidad y registradas.
- **TOL-004 · Coste contextual UCC:** adaptador monotónico y estable; mismo adaptador para comparar. Presupuesto objetivo y duro se congelan con el candidato antes de ejecutar. Pertenece principalmente a ADR-003B; ADR-002 solo registra la dependencia.
- **TOL-005 · Portabilidad semántica:** dos consumidores realmente independientes; **100 % campos críticos y ≥99 % global**, incluidas negaciones, condiciones y permisos reportables.
- **TOL-006 · Comprensión de operaciones:** **≥95 %** no destructivas y **100 %** destructivas antes de confirmación final.

### 3.2 Puertas B04-M01–M21 relevantes

Conservar literalmente, entre otras:

- M01 recall crítico: 100 % por caso.
- M02 recall total: ≥90 % global y ≥85 % por familia.
- M03 precisión útil: ≥80 % global y ningún caso <60 %.
- M04 contaminación prohibida: 0 absoluto.
- M05 obsoleto como vigente: 0 crítico y ≤1 % global.
- M06 aislamiento de proyecto: 100 %.
- M07 procedencia recuperable: 100 %.
- M08 visibilidad de conflicto: 100 % críticos y ≥95 % global.
- M09 estado interno de ausencia: 100 % críticos, ≥95 % global y 0 falsos «no existe».
- M10 deduplicación: 0 fusiones materiales erróneas y ≥95 % agrupaciones correctas.
- M11 separación temporal: 100 % críticos y ≥95 % global.
- M12 fallback: 0 violaciones de no uso; 100 % de fragmentos sustituidos/candidatos correctamente enlazados.
- M13 aclaración material: 100 %.
- M14 explicación mínima completa: 100 % de muestra auditada.
- M15 trazabilidad del plan: 100 %.
- M16 neutralidad: 100 % semántico y tolerancia de orden TOL-001.
- M17 negación: 100 % críticos y ≥95 % global.
- M18 condición: 100 % críticos y ≥95 % global.
- M19 criticidad: 100 %, 0 auto-marcados sin regla y 0 exclusiones por presupuesto ordinario.
- M20 indistinguibilidad externa: 100 % y 0 canales laterales observables dentro de tolerancias prefijadas.
- M21 límites/parada/desempate: 100 %, 0 ampliaciones silenciosas y 0 variaciones no justificadas.

Estas cifras no se rebajan por resultados de la línea base.

## 4. Valores arquitectónicos que esta ronda debe proponer

El Registro debe separar claramente:

### 4.1 Valores ya canónicos

Copiar sin reinterpretación TOL-001–006 y B04-M01–21.

### 4.2 Valores ADR-002 que requieren medición/propuesta

Proponer, con evidencia y razón:

1. **Latencia local de recuperación** por consulta, al menos P50/P95/P99 y límite duro.
2. **Estabilidad de orden y conjunto** en repeticiones idénticas.
3. **Tamaño del índice derivado** respecto al contenido canónico indexado.
4. **Tiempo de construcción y reconstrucción** del índice.
5. **Coste incremental por etapa E0–E5**, expresado en tiempo y operaciones locales; cualquier coste externo se declara aparte.
6. **Banda temporal de TOL-002** para pares ausencia/no-reportable.
7. **Límite de variación entre ejecuciones equivalentes** para latencia y orden.
8. **Punto de congelación de valores dependientes del candidato** antes del benchmark T1–T4.

No inventar cifras sin medición. Una propuesta puede ser conservadora, pero debe indicar dato observado, margen elegido y consecuencia de fallo.

## 5. Medición experimental aislada

Crear rutas nuevas propuestas:

- `experiments/adr002/tolerances/`
- `artifacts/adr002_tolerances/`

No escribir fuera de ellas salvo el documento final bajo `docs/architecture/`.

### 5.1 Condiciones

- bases SQLite temporales, sin datos reales;
- sin red, API, embeddings ni modelos externos;
- usar la cadena canónica de Alembic y el código real de recuperación 0.1 sin modificarlo;
- reloj monotónico;
- warm-up declarado;
- mínimo 30 repeticiones por escenario; preferible 100 cuando el coste sea bajo;
- misma máquina y proceso para comparaciones pareadas;
- semilla fija cuando exista aleatoriedad;
- registrar Python, SQLite, SQLAlchemy, Alembic, plataforma y commit;
- no usar el tiempo de creación de fixtures dentro de la latencia de consulta.

### 5.2 Escenarios mínimos

Medir al menos:

1. consulta con 0 resultados;
2. consulta con 1 resultado exacto;
3. consulta de alta frecuencia con muchos candidatos;
4. consulta que evidencia el barrido completo actual;
5. par ausencia real / contenido existente no reportable simulado sin revelar cuál;
6. construcción inicial del índice;
7. reconstrucción desde fuente canónica;
8. borrado y comprobación de desaparición del derivado;
9. repetición idéntica para estabilidad de conjunto y orden.

Usar como mínimo el volumen de referencia heredado disponible de Sirius 0.1 cuando sea aplicable: 5.000 mensajes y 500 recuerdos. Puede añadirse una escala superior sintética solo como observación, nunca como requisito canónico no aprobado.

## 6. Tratamiento de TOL-002

La comparación ausencia/no-reportable debe analizar por separado:

- estado externo;
- texto externo;
- conteo externo;
- tiempo observable.

Estado, texto y conteo deben ser exactamente equivalentes cuando el contrato exige indistinguibilidad.

Para tiempo:

- medir distribuciones pareadas;
- proponer una banda externa simple y reproducible;
- no basarse solo en una media;
- registrar P50/P95/P99, diferencia absoluta y relativa;
- cualquier diferencia repetible atribuible a existencia protegida debe fallar aunque ambas consultas sean rápidas.

No presentar una prueba estadística aislada como garantía criptográfica. Declarar el modelo de amenaza y sus límites.

## 7. Entregables

Crear:

1. `experiments/adr002/tolerances/` con código reproducible y pruebas propias.
2. `artifacts/adr002_tolerances/mediciones_linea_base.json`
3. `artifacts/adr002_tolerances/INFORME_MEDICION_TOLERANCIAS_v0.1_PROPUESTO.md`
4. `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.1_PROPUESTO.md`

El Registro debe incluir por fila:

- ID;
- ámbito/ADR responsable;
- métrica y fórmula;
- escenario y entorno;
- repeticiones/distribución;
- objetivo;
- límite duro;
- evidencia o fundamento;
- punto de congelación;
- estado: `CANÓNICA`, `PROPUESTA`, `REGLA_CONFIRMADA_VALOR_CANDIDATO` o `NO_APLICA_ADR002`;
- consecuencia de fallo.

No aprobar el Registro: queda PROPUESTO para decisión explícita del usuario.

## 8. Validación

Ejecutar:

- pruebas propias del experimento;
- runner completo de medición;
- Ruff sobre `experiments/adr002/tolerances/`;
- `git status`.

No ejecutar la suite productiva completa si ningún archivo productivo cambia.

Confirmar:

- ningún cambio en `src/`, `tests/`, `migrations/` o configuración productiva;
- TOL-001–006 reproducidos literalmente;
- B04-M01–21 no rebajados;
- valores propuestos respaldados por medición;
- valores dependientes de candidato con regla y punto de congelación;
- no se ejecutó T1–T4;
- no hubo red ni datos reales.

## 9. Publicación

Commit único:

`test(adr002): measure baseline and propose tolerances`

Push a `evidence/adr001-spikes`.

No abrir otro PR. No fusionar el PR #117.

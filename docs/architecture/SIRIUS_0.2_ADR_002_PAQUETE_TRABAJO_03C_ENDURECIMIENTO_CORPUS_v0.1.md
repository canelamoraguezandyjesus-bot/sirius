# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 03C

## Endurecimiento del corpus, validador y distribución de rendimiento

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**Entrada:** auditoría adversarial independiente del corpus v0.2 sobre `3f61c78de22f49bb3fb2b85bdc23555d57c42a7b`  
**No autoriza:** congelar TOL-208, ejecutar T0, aprobar TOL-207, satisfacer TOL-209/TOL-210, implementar o ejecutar ADR002-A/B/C/D, abrir otro PR ni merge.

## 1. Decisión

El corpus v0.2 **no es aprobable para congelar**.

La fidelidad literal de los 50 B04-CA y las asignaciones actualmente extraídas del Anexo B son trabajo válido y deben conservarse. Sin embargo, la siguiente versión debe corregir antes de cualquier congelación:

- B-01: selección frágil de tablas DOCX y aprobación en vacío;
- B-02: corpus de rendimiento degenerado y no neutral en efecto;
- B-03: cierre incorrecto de CA-47;
- B-04: seis PDP-CA de disciplina mal clasificados como casos funcionales de nivel 1;
- M-01–M-11 y los defectos menores confirmados por la auditoría.

TOL-207 no se corrige todavía. Su presupuesto ligado al corpus solo puede calcularse después de disponer de un corpus de rendimiento defendible.

## 2. Versionado y conservación

Conservar íntegros todos los artefactos v0.1 y v0.2.

Crear una nueva familia v0.3:

- `canonical_source_v0_3.py`
- `schema_v0_3.py`
- `build_corpus_v0_3.py`
- `validate_corpus_v0_3.py`
- `test_corpus_contract_v0_3.py`
- `conformance_corpus_v0_3.json`
- `performance_corpus_v0_2.json`
- `cases_v0_3.json`
- `references_v0_3.json`
- `pdp_cases_v0_2.json`
- `pdp_harness_rules_v0_1.json`
- `t0_preexecution_projection_v0_1.json`
- `benchmark_manifest_v0_3.json`

No modificar las versiones anteriores para hacerlas pasar.

## 3. Lector canónico robusto

### 3.1 Selección de tablas por identidad

Seleccionar cada tabla por cabecera y contexto canónico, nunca por número de columnas, forma de fila ni posición en el DOCX.

Como mínimo:

- Anexo B: cabecera exacta compatible con `RED | Familia | Caso(s) exactos | ...` y contexto de Anexo B;
- Registro RED: cabecera propia, expresamente distinta del Anexo B;
- familias PDP §8: cabecera de familia y cobertura mínima;
- ficha PDP §7: tabla completa de campos obligatorios;
- B04 §17/§17.1: tabla de casos de aceptación.

Si hay cero o más de una tabla candidata para una identidad, el lector falla de forma explícita.

### 3.2 Invariantes mínimas

El lector debe exigir antes de validar artefactos:

- 50 B04-CA;
- 79 filas RED del Anexo B;
- al menos 20 B04-CA nombrados por el Anexo B;
- 25 familias PDP legibles con sus textos de cobertura;
- 28 PDP-CA;
- exactamente los 14 campos canónicos actuales de PDP §7;
- 32 RF y 21 métricas B04.

Una tabla vacía o equivocada no puede producir un PASS parcial.

### 3.3 Anexo B bidireccional y completo

Comprobar:

1. canon → artefacto: toda asignación canónica está presente;
2. artefacto → canon: ninguna asignación marcada canónica fue inventada;
3. las trazas derivadas viven en campos separados y no se solapan con las canónicas;
4. no filtrar silenciosamente métricas de otros bloques.

Registrar expresamente:

- métricas B04 propias;
- métricas canónicas externas citadas por el Anexo B, incluidas `B05-M16` y `B08-M25`;
- métricas derivadas del arnés.

No aceptar IDs inexistentes como `RED-099`, `B04-M99` o `F99`.

### 3.4 PDP §7 y familias

Leer todas las filas reales de las tablas. Comparar el conjunto completo extraído contra el conjunto canónico esperado. Una fila añadida, ausente o duplicada debe fallar.

No usar únicamente las claves de `familias_pdp()`: comprobar también el texto canónico de cobertura mínima.

## 4. Casos, referencias y PDP-CA

### 4.1 CA-47

Mantener cardinalidad `EXHAUSTIVA` solo si la instanciación la justifica y cerrar los conjuntos sobre el corpus real.

Con la semántica actual y el corpus de conformidad existente, las referencias deben rederivarse automáticamente y comprobarse:

- R1 `occurred_at`: conjunto exacto derivado;
- R2 tiempo válido a 20 de enero: debe incluir todos los elementos elegibles, incluidos `DEC-005`, `DEC-009` y `DEC-014` mientras los datos y filtros actuales permanezcan;
- R3 `recorded_at` hasta 15 de febrero: debe incluir `DEC-005`, `DEC-014` y `DEC-015` mientras los datos y filtros actuales permanezcan.

No codificar a mano un subconjunto y llamarlo exhaustivo. El generador debe calcular el cierre y la prueba debe comparar la referencia con ese cálculo independiente.

### 4.2 PDP-CA

Solo `PDP-CA-09` y `PDP-CA-22` permanecen como casos funcionales de nivel 1 de ADR-002, por su anclaje canónico vía Anexo B/RED-017.

Reclasificar:

- `PDP-CA-02`
- `PDP-CA-03`
- `PDP-CA-06`
- `PDP-CA-16`
- `PDP-CA-17`
- `PDP-CA-18`

como **reglas canónicas de protocolo del arnés**, no como consultas funcionales ni casos sobre los que T0 pueda ser expresable.

Guardarlas en `pdp_harness_rules_v0_1.json` con:

- texto canónico;
- fuente PDP;
- regla de ejecución;
- evidencia requerida;
- consecuencia;
- estado de aplicabilidad;
- sin campos de consulta, recuperación ni predicción T0.

Los dos PDP-CA funcionales deben llevar la ficha completa de PDP §7.

### 4.3 Canon frente a instanciación

Aplicar la regla de fuente y estado a **todos los 14 campos** de la ficha, no solo modo, etapa, parada y cardinalidad.

Ninguno de estos campos puede marcarse `CANONICO` sin texto literal que lo fije:

- objetivo;
- unidad de trabajo;
- entrada;
- modo;
- propósito/permiso;
- ámbito;
- tiempos;
- candidatos elegibles/prohibidos;
- orden/conjunto;
- tolerancias;
- señales observables;
- etapa;
- condición de insuficiencia;
- parada.

Cada campo debe registrar `fuente`, `seccion`, `estado` y `justificacion`.

### 4.4 Condición de insuficiencia

Sustituir frases genéricas por una estructura ejecutable por rama:

- etapa actual;
- variables observadas;
- predicado;
- umbral o condición lógica;
- siguiente etapa permitida;
- fuente;
- estado canónico o derivado.

Cuando no aplique, declarar `NO_APLICA` y una razón verificable. No aceptar listas vacías sin explicación.

### 4.5 T0

Los casos y referencias congelables no incluirán previsiones normativas sobre T0.

- mantener únicamente `estado_t0: NO_MEDIDO` donde sea necesario;
- mover toda previsión a `t0_preexecution_projection_v0_1.json`;
- marcar ese fichero como no normativo, no congelable y sustituible por la ejecución real;
- aplicar su criterio de forma automática a todos los casos funcionales, no a una lista manual;
- las reglas del arnés no reciben previsión T0.

## 5. Corpus de conformidad v0.3

Conservar los 94 elementos salvo los cambios estrictamente necesarios.

Corregir:

- cierre exacto de CA-47;
- coherencia de referencias y ramas;
- cualquier colisión por raíz detectada en los propios anclajes;
- identidad completa de mensajes, documentos y relaciones cuando deban compartirse o versionarse.

DEC-014 y DEC-015 siguen permitidos si el cierre independiente confirma que hacen falsable CA-47 y no alteran otros casos.

Añadir una prueba de cierre para todo caso `EXHAUSTIVA`: el conjunto esperado debe ser exactamente el conjunto elegible calculado bajo la consulta y los filtros declarados.

## 6. Corpus de rendimiento v0.2

### 6.1 Independencia y escala

El corpus de rendimiento es un artefacto independiente del corpus de conformidad. Comparte contrato, semilla y vocabulario de estados, pero **no tiene que contener los 94 anclajes byte a byte**.

Debe tener exactamente:

- 5.000 mensajes;
- 500 recuerdos;
- 50 decisiones;
- **2 proyectos reales en el corpus**, no 8 declarados como 2.

No usar un proyecto artificial único de volumen.

### 6.2 Distribución sintética neutral

Generar con semilla fija una distribución documentada y no degenerada:

- longitudes de texto con variación material y al menos 20 longitudes distintas;
- vocabulario amplio con frecuencia aproximadamente Zipf, no una plantilla repetida con número de secuencia;
- fechas distribuidas en un intervalo declarado, con múltiples días y meses;
- reparto entre los dos proyectos sin que uno supere el 60 %;
- variación real en confirmación, validez, disponibilidad, sensibilidad, polaridad, condición y temporalidad;
- una proporción declarada de entidades, alias, procedencias, criticidad y relaciones;
- relaciones de varios tipos y densidad no nula en el volumen;
- textos sintéticos de varias familias temáticas y estructuras gramaticales;
- ningún dato real ni dependencia de red.

No afirmar que representa producción. Declararlo como corpus sintético de estrés neutral y publicar sus distribuciones observadas.

### 6.3 Contaminación

Construir automáticamente un léxico protegido desde:

- consultas y resultados del corpus de conformidad;
- nombres y alias de entidades;
- frases distintivas;
- tokens informativos;
- bigramas y trigramas relevantes.

Normalizar Unicode, mayúsculas y acentos. Detectar además:

- coincidencia exacta;
- relación singular/plural o sufijo;
- raíz común significativa mediante prefijo normalizado de longitud suficiente;
- alias y nombres de entidad;
- n-gramas.

Debe detectar al menos `turno/turnos` y `registro/registrado`.

### 6.4 Invariantes distributivas

El manifiesto debe registrar y el validador calcular sobre los datos reales:

- conteos reales;
- media, mediana, p95, desviación y número de longitudes distintas;
- tamaño de vocabulario;
- frecuencia máxima de tokens informativos;
- número de fechas distintas y rango temporal;
- reparto por proyecto;
- reparto por cada eje de estado;
- densidad y tipos de relaciones;
- entidades, alias, procedencias y criticidad.

No validar una declaración contra otra declaración.

## 7. Validador v0.3

### 7.1 No mutante

Validar nunca debe escribir en el árbol del repositorio.

La regeneración se hace en un directorio temporal y se compara contra los artefactos comprometidos.

### 7.2 Cobertura obligatoria

Añadir comprobaciones sustantivas para:

- conteos reales de mensajes, recuerdos, decisiones y proyectos;
- identidad de anclajes sobre items, mensajes, documentos y relaciones cuando aplique;
- CANONICO indebido en cualquiera de los 14 campos;
- Anexo B en ambas direcciones;
- previsión T0 coherente en todos los casos del fichero no normativo;
- neutralidad tecnológica y entre candidatos en datos, casos y referencias;
- cierre de conjuntos EXHAUSTIVA;
- distribución no degenerada del corpus de rendimiento;
- contaminación por token, raíz, alias y n-grama;
- separación entre casos funcionales y reglas del arnés;
- coherencia `tolerancia_id` frente a `valor_pendiente_en`.

Para CA-37 y CA-48 registrar:

- `tolerancia_id: ADR002-TOL-201`;
- `valor_pendiente_en: ADR002-TOL-209`.

Para CA-39 aplicar la misma distinción a TOL-001 y su valor pendiente en TOL-209.

### 7.3 Pruebas negativas

Incluir pruebas temporales que demuestren detección de al menos:

1. tabla DOCX equivocada o movida;
2. Anexo B vacío;
3. asignación canónica inventada;
4. carácter canónico alterado;
5. campo derivado marcado CANONICO;
6. rama M4 perdida;
7. CA-47 colapsado o conjunto no cerrado;
8. veredicto T0 anticipado;
9. conteo real diferente de la declaración;
10. mensaje/documento/relación ancla alterado;
11. contaminación por raíz o alias;
12. tecnología o candidato nombrado en campos neutrales;
13. distribución de rendimiento degenerada;
14. campo nuevo o perdido en PDP §7.

## 8. Documentación

Crear:

- `docs/architecture/SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.3_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.3_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.3.json`
- `artifacts/adr002_benchmark_preparation/INFORME_ENDURECIMIENTO_CORPUS_v0.3_PROPUESTO.md`

Corregir en la documentación nueva:

- 19 ramas, no 17;
- 21 casos con comillas tipográficas si se informa ese conteo, no 8;
- cuatro denominadores de familias con fuente expresa;
- filtro y conservación de `B05-M16` y `B08-M25`;
- independencia entre corpus de conformidad y rendimiento;
- TOL-207/208/209/210 siguen no satisfechas.

## 9. Validación y entrega

Ejecutar:

- validador v0.3;
- validadores v0.1 y v0.2 para comprobar conservación histórica;
- pytest completo de `experiments/adr002/benchmark/`;
- Ruff format/check de esa ruta;
- doble regeneración en temporales;
- pruebas negativas;
- análisis de distribución;
- `git status`.

No ejecutar la suite productiva si no cambia código productivo.

Commit único:

`test(adr002): harden benchmark corpus and validator`

Push a `evidence/adr001-spikes`. No abrir otro PR ni fusionar el #117.

Entregar:

1. cierre de B-01–B-04 y M-01–M-11;
2. nueva clasificación PDP-CA/reglas de arnés;
3. cierre de CA-47;
4. distribución medida del corpus de rendimiento;
5. mutaciones negativas y resultado;
6. defectos todavía no cubiertos;
7. archivos creados;
8. pruebas;
9. SHA y estado final.

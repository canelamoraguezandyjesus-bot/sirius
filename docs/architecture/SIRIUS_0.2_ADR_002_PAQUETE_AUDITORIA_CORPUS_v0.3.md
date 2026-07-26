# SIRIUS 0.2 — ADR-002 · Paquete de auditoría del corpus v0.3

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA AUDITORÍA ADVERSARIAL INDEPENDIENTE  
**Rama:** `evidence/adr001-spikes`  
**Objeto:** commit `079ba763a92865e8c5501acb11a4e0db915c4ff2`  
**No autoriza:** modificar archivos, congelar TOL-208, aprobar TOL-207, ejecutar T0, implementar o ejecutar ADR002-A/B/C/D, commit, push, abrir otro PR ni merge.

## 1. Objetivo

Determinar si la familia v0.3 puede convertirse en corpus definitivo de conformidad y rendimiento de ADR-002.

La auditoría debe ser independiente del generador y del validador que produjeron los artefactos. Repetir `98/98` y `171 passed` no basta.

Emitir veredictos separados para:

1. lector canónico;
2. corpus de conformidad;
3. casos y referencias;
4. reglas del arnés y PDP-CA;
5. corpus de rendimiento;
6. validador y pruebas negativas;
7. aptitud para congelar el primer paso de TOL-208.

## 2. Material obligatorio

Leer íntegramente:

- `AGENTS.md`
- `CLAUDE.md`
- los tres DOCX de `docs/architecture/canonical_sources/`
- `docs/architecture/canonical_sources/MANIFEST.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03C_ENDURECIMIENTO_CORPUS_v0.1.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.3_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.3_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/INFORME_ENDURECIMIENTO_CORPUS_v0.3_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.3.json`
- todos los módulos y artefactos v0.3/v0.2 nuevos del commit `079ba763…`
- las familias v0.1 y v0.2 para verificar conservación histórica.

## 3. Reglas de auditoría

- No modificar el repositorio.
- No escribir informes dentro del árbol.
- Los scripts y mutaciones se ejecutan únicamente en un sandbox temporal fuera del repositorio.
- No reutilizar `canonical_source_v0_3.py` como única fuente para verificar su propia corrección.
- Construir al menos un extractor DOCX independiente para las tablas críticas.
- No aceptar una propiedad porque la declare el manifiesto: recalcularla sobre los datos.
- Distinguir fidelidad canónica, coherencia interna, realismo sintético y neutralidad experimental.

## 4. Auditoría del lector canónico

### 4.1 Identidad de tablas

Verificar independientemente las catorce identidades de tabla:

- cabecera exacta;
- contexto anterior y posterior;
- número de filas;
- ausencia de colisiones con otras tablas del mismo formato.

Mutar en copias temporales:

1. mover el Anexo B antes del Registro RED;
2. duplicar el Anexo B;
3. eliminar su encabezado contextual;
4. crear una segunda tabla con la misma cabecera;
5. añadir, quitar y duplicar una fila;
6. añadir una fila válida a PDP §7 y PDP §8.

El lector debe fallar de manera explícita, no producir un canon parcial.

### 4.2 Anexo B completo

Contrastar todas las 79 filas, no solo las veinte que mencionan B04.

Verificar:

- RED;
- familias;
- casos exactos;
- métricas propias y externas;
- expansión de rangos y prefijos;
- tratamiento exacto de `B08-M12/M25`, `B05-M16` y `B08-M25`;
- bidireccionalidad canon ↔ artefacto;
- rechazo de identificadores inventados.

Determinar si `_expandir_metricas` interpreta correctamente todas las formas reales del Anexo B, no solo los ejemplos ya conocidos.

## 5. Corpus de conformidad y referencias

### 5.1 Fidelidad

Con extractor propio, comprobar carácter a carácter los 50 B04-CA y los dos PDP-CA funcionales.

Verificar todos los campos marcados `CANONICO` de los catorce campos, no solo los cuatro campos de §17.

### 5.2 CA-47

Recalcular sin usar el generador ni el validador:

- universo en ámbito;
- filtros de elegibilidad;
- `occurred_at`;
- tiempo válido;
- `recorded_at`;
- conjuntos esperados;
- complemento prohibido.

Confirmar que:

- R1 = `{DEC-011, DEC-015}`;
- R2 = `{DEC-005, DEC-009, DEC-014}`;
- R3 = `{DEC-005, DEC-014, DEC-015}`;
- `DEC-012` cae por validez `SUSTITUIDA`;
- ningún otro caso cambia accidentalmente por `DEC-014` o `DEC-015`.

Buscar otros casos `EXHAUSTIVA` cuyo conjunto no cierre exactamente sobre el corpus.

### 5.3 Colisiones entre anclajes

Auditar las 29 colisiones por raíz declaradas:

- listar cada pareja;
- identificar si cruza proyecto, ámbito, tiempo, estado o polaridad;
- comprobar si una recuperación léxica razonable puede producir falsos positivos legítimos;
- determinar si son adversariales útiles o ambigüedades no adjudicables.

Este punto puede bloquear la congelación aunque el validador las declare conocidas.

### 5.4 Insuficiencia y tolerancias

Comprobar caso por caso que la condición de insuficiencia:

- es ejecutable;
- usa variables realmente observables;
- no introduce un umbral todavía no aprobado;
- autoriza una única transición compatible con E0–E5;
- utiliza `NO_APLICA` solo con razón válida.

Verificar la distinción:

- TOL-201 / valor pendiente en TOL-209;
- TOL-001 / valor pendiente en TOL-209.

## 6. PDP-CA y reglas del arnés

Revisar los 28 PDP-CA directamente contra el DOCX.

Confirmar:

- solo PDP-CA-09 y PDP-CA-22 tienen anclaje funcional suficiente para ADR-002;
- los seis trasladados al arnés son realmente reglas de proceso y no pruebas funcionales;
- las reglas no contienen consulta, elegibles, etapa, parada ni previsión T0;
- los veinte excluidos tienen responsable y motivo correctos;
- las tres clases son disjuntas y exhaustivas.

Determinar si `APLICABLE_TRAS_CONGELACION` es un estado derivado legítimo o anticipa la aprobación de documentos todavía PROPUESTOS.

## 7. Proyección T0

Comprobar que:

- no aparece ninguna previsión T0 en casos, referencias, corpus, reglas del arnés o manifiesto normativo;
- el fichero separado está marcado no normativo y sustituible;
- su criterio se aplica automáticamente a los 52 casos funcionales;
- no convierte `INSEGURO` en fallo medido;
- la fuente de `AUSENTE/PARCIAL/INSEGURO/EXISTENTE` está identificada como evidencia no canónica.

Evaluar si conviene excluir por completo esta proyección de lo que se congelará.

## 8. Corpus de rendimiento

### 8.1 Conteos y distribución

Recalcular independientemente:

- 5.000 mensajes;
- 500 recuerdos;
- 50 decisiones;
- 2 proyectos realmente referenciados;
- documentos, relaciones y entidades;
- longitudes, vocabulario, frecuencia máxima y pendiente Zipf;
- fechas y rango temporal;
- reparto por proyecto;
- estados, polaridad, condición, temporalidad, sensibilidad y disponibilidad;
- entidades, alias, procedencia, criticidad y relaciones.

No leer los valores del manifiesto como entrada.

### 8.2 Generación y sesgo

Inspeccionar el generador y determinar:

- si las nueve familias y doce estructuras producen variedad sustantiva o combinaciones superficiales;
- si el vocabulario Zipf-Mandelbrot contiene repeticiones o asociaciones que favorecen FTS5, vectores o relaciones;
- si las longitudes y frecuencias dependen de reglas que una arquitectura puede explotar artificialmente;
- si las relaciones y estados están correlacionados de forma irreal con términos o proyectos;
- si las 24 entidades y sus alias generan ambigüedad suficiente;
- si la densidad relacional 0,327 permite comparar ADR002-C/D sin ser trivial ni dominante.

No exigir realismo de producción; exigir neutralidad y utilidad comparativa.

### 8.3 Contaminación

Construir un léxico protegido independiente y probar:

- token exacto;
- normalización Unicode y acentos;
- singular/plural;
- raíces;
- nombres y alias;
- bigramas y trigramas;
- paráfrasis obvias de anclajes.

Determinar si “0 de 6.194” se debe a una protección correcta o a que el generador evita demasiado vocabulario y produce un corpus artificialmente separado.

### 8.4 Dos proyectos

Comprobar que usar dos proyectos no produce un aislamiento trivial:

- ambos contienen suficiente variedad;
- ninguno es identificable por vocabulario exclusivo;
- estados, fechas y temas se solapan materialmente;
- el reparto 53,5/46,5 no oculta correlaciones.

## 9. Validador y pruebas negativas

### 9.1 Independencia

Comprobar que las 14 pruebas negativas:

- mutan el artefacto correcto;
- ejecutan la ruta productiva real del validador;
- no prueban únicamente una función auxiliar con la misma expectativa que la implementación;
- fallarían si el defecto estuviera en el generador.

### 9.2 Mutaciones adicionales obligatorias

Añadir en sandbox al menos:

1. una segunda tabla con cabecera correcta y contexto ambiguo;
2. una forma nueva pero válida de métrica externa del Anexo B;
3. un caso `EXHAUSTIVA` distinto de CA-47 con elemento omitido;
4. una condición de insuficiencia que usa variable inexistente;
5. un valor de tolerancia inventado dentro de un campo estructurado;
6. correlación perfecta tema↔proyecto en rendimiento;
7. correlación perfecta estado↔palabra;
8. todos los alias confinados a un solo proyecto;
9. relaciones concentradas en una sola familia temática;
10. contaminación semántica mediante paráfrasis sin solapamiento léxico;
11. una colisión por raíz de anclaje que altera una consulta;
12. previsión T0 copiada dentro del manifiesto normativo.

Registrar qué detecta y qué no detecta el validador.

## 10. Neutralidad

Emitir dos veredictos distintos:

- **neutralidad léxica explícita:** ausencia de nombres de tecnologías y candidatos;
- **neutralidad experimental:** ausencia de estructura del corpus que favorezca materialmente una señal o realización.

La primera puede verificarse automáticamente. La segunda requiere análisis independiente y puede quedar condicionada hasta disponer de candidatos ejecutables.

Determinar si esa limitación impide congelar ahora el corpus o si puede aceptarse como riesgo controlado con ablaciones posteriores.

## 11. Conservación y alcance

Confirmar que el commit `079ba763…`:

- añade exactamente 17 archivos;
- no modifica v0.1/v0.2;
- no toca `canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva;
- no ejecuta T0 ni candidatos;
- no satisface TOL-207/208/209/210;
- no abre otro PR ni fusiona el #117.

## 12. Veredictos requeridos

Emitir por separado:

1. lector canónico;
2. corpus de conformidad;
3. casos y referencias;
4. PDP-CA y reglas del arnés;
5. proyección T0;
6. corpus de rendimiento;
7. validador;
8. corpus v0.3 completo para congelación.

Valores permitidos:

- `APROBABLE PARA CONGELAR`;
- `APROBABLE CON CORRECCIONES`;
- `NO APROBABLE`.

Cada hallazgo debe incluir:

- gravedad: BLOQUEANTE, MATERIAL, MENOR u OBSERVACIÓN;
- evidencia exacta;
- consecuencia;
- corrección mínima.

## 13. Estado de TOL-208

Determinar expresamente si puede autorizarse únicamente el paso 1 de TOL-208 —congelar el corpus—.

No autorizar ni ejecutar los pasos 2 y 3:

2. ejecutar T0;
3. rederivar la línea base.

Aunque el corpus resulte aprobable, TOL-208 seguirá NO SATISFECHA hasta completar los tres pasos.

## 14. Entrega

Entregar únicamente:

1. veredicto global;
2. hallazgos por gravedad;
3. veredicto de los ocho componentes;
4. distribuciones recalculadas;
5. auditoría de las 29 colisiones;
6. mutaciones adicionales y resultados;
7. defectos todavía no detectables;
8. correcciones mínimas;
9. decisión recomendada sobre congelar únicamente el corpus;
10. estado exacto de TOL-208;
11. pruebas ejecutadas;
12. `git status` limpio.

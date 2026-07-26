# SIRIUS 0.2 — ADR-002 · Paquete de auditoría del corpus v0.2

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA AUDITORÍA ADVERSARIAL INDEPENDIENTE  
**Rama:** `evidence/adr001-spikes`  
**Objeto:** commit `3f61c78de22f49bb3fb2b85bdc23555d57c42a7b`  
**No autoriza:** modificar archivos, congelar TOL-208, aprobar TOL-207, ejecutar T0, implementar o ejecutar candidatos, commit, push ni merge.

## 1. Objetivo

Determinar si el corpus v0.2 puede congelarse como base de conformidad y rendimiento de ADR-002, o si conserva defectos de fidelidad, instanciación, cobertura, escala o verificabilidad.

La auditoría debe contrastar directamente los artefactos contra los tres DOCX canónicos. No basta con confiar en el nuevo validador ni con repetir sus resultados.

## 2. Fuentes y artefactos obligatorios

Leer íntegramente:

- `AGENTS.md`
- `CLAUDE.md`
- los tres DOCX de `docs/architecture/canonical_sources/`
- `docs/architecture/canonical_sources/MANIFEST.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.2_PROPUESTO.md`
- `docs/architecture/SIRIUS_0.2_ADR_002_CORPUS_BENCHMARK_v0.2_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/INFORME_CORRECCION_CORPUS_v0.2_PROPUESTO.md`
- `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.2.json`
- todos los archivos v0.2 de `experiments/adr002/benchmark/`
- los artefactos v0.1 para comprobar que permanecen intactos y entender la corrección.

## 3. Reglas

- No modificar ningún archivo.
- No generar informes dentro del repositorio.
- No ejecutar T0 ni candidatos.
- Se permite ejecutar únicamente los validadores y pruebas existentes, y scripts temporales fuera del árbol para contraste independiente.
- Una prueba que valida datos generados por el mismo código que los produjo no es evidencia independiente por sí sola.
- Distinguir siempre: texto canónico, asignación canónica, instanciación propuesta y medición todavía no realizada.

## 4. Auditoría de fidelidad canónica

Contrastar directamente contra los DOCX:

1. Los 50 B04-CA aparecen una vez y conservan carácter a carácter:
   - riesgo;
   - entrada;
   - resultado esperado;
   - fallo observable.
2. El Anexo B completo se reproduce fielmente:
   - CA;
   - RF;
   - M;
   - F;
   - RED;
   - sin pérdidas ni atribuciones derivadas presentadas como canónicas.
3. Comprobar expresamente RED-027–034 y RED-040.
4. Verificar que los campos `CANONICO` son realmente nombrados por la fuente y que ningún campo derivado cita falsamente §17/§17.1.
5. Confirmar que cardinalidad, etapa, parada, orden, elegibles y prohibidos distinguen fuente y estado campo por campo.
6. Comprobar que CA-02, CA-22, CA-39 y CA-47 ya no presentan `EXHAUSTIVA` o `S5` como canon sin fuente literal.
7. Verificar que el texto canónico de los ocho casos con comillas se conserva exactamente.

## 5. Auditoría de ramas y falsabilidad

Comprobar que las ramas no solo existen, sino que hacen detectable el fallo canónico:

- CA-09, CA-10, CA-24 y CA-49 en M1/M4;
- CA-35 en M3;
- CA-36 con tres estados externos o internos materialmente distinguibles;
- CA-47 con tres consultas y tres conjuntos realmente diferenciados por los tres ejes temporales;
- CA-48 con autorizado, no autorizado y ausencia real, sin resolver por anticipado la banda pendiente de TOL-209.

Buscar otras cláusulas canónicas multirrama o multimodo omitidas que el paquete 03B no haya enumerado.

## 6. Auditoría de ficha PDP y PDP-CA

1. Verificar los catorce campos exactos de PDP §7 y su correspondencia en cada caso/rama.
2. Confirmar que `condicion_insuficiencia_para_expandir` es verificable y no una frase genérica repetida.
3. Revisar caso por caso los 28 PDP-CA:
   - texto literal;
   - criterio de inclusión o exclusión;
   - ADR responsable;
   - ausencia de selección oportunista.
4. Determinar si los ocho PDP-CA incluidos pertenecen realmente al nivel 1 de ADR-002 o si alguno es solo una regla de protocolo que no debe convertirse en caso funcional.
5. Comprobar que ADR-002 no reclama cierre de los 304 casos ni de familias ajenas.
6. Verificar los cuatro denominadores de familias contra ARQ-00/PDP y detectar solapamientos o conteos engañosos.

## 7. Auditoría de T0 no medido

- Confirmar que ningún artefacto congelable contiene un veredicto de T0.
- Revisar el criterio único AUSENTE/PARCIAL/EXISTENTE y comprobar que no confunde representabilidad con comportamiento correcto.
- Determinar si `expresabilidad_prevista` debe permanecer en el corpus congelable o trasladarse a un informe no normativo.
- Revisar especialmente CA-01, CA-04, CA-09, CA-10, CA-11 y CA-39.
- Confirmar que los ejes INSEGURO no se convierten en resultado antes de ejecutar.

## 8. Auditoría de los dos corpus

### 8.1 Conformidad

- Verificar los 94 elementos y justificar los dos nuevos anclajes.
- Confirmar que DEC-014 y DEC-015 no introducen respuestas accidentales en otros casos.
- Buscar colisiones de contenido, alias, fechas, ámbitos, posturas o términos entre casos.
- Comprobar que los datos permiten ejecutar todas las ramas sin depender de información no representada.

### 8.2 Rendimiento

- Confirmar exactamente 5.000 mensajes, 500 recuerdos y 50 decisiones.
- Comprobar que el corpus no es solo volumen uniforme artificial que favorezca una implementación.
- Verificar distribuciones relevantes: longitud de texto, frecuencia de términos, proyectos, estados, fechas, conflictos y densidad de candidatos.
- Confirmar que los anclajes de conformidad son idénticos y que el ruido no contiene términos, alias, entidades o patrones que alteren las consultas.
- Revisar si 26 términos de anclaje son suficientes para detectar contaminación o si el control debe abarcar entidades, alias, frases y tokens normalizados.
- Verificar que la proyección 500/5.000/50.000 no oculta cambios de distribución.
- Determinar si el corpus es adecuado para comparar latencia, tamaño, construcción, reconstrucción y estabilidad, sin afirmar que ya fija tolerancias.

## 9. Auditoría del validador

- Inspeccionar `canonical_source.py` para detectar selectores frágiles, dependencias del orden del DOCX, coincidencias parciales o tablas equivocadas.
- Introducir mutaciones solo en copias temporales fuera del repositorio para comprobar que el validador detecta al menos:
  - cambio de un carácter canónico;
  - pérdida de una asignación del Anexo B;
  - campo derivado marcado CANONICO;
  - desaparición de una rama M4;
  - colapso de CA-47;
  - veredicto T0 anticipado;
  - contaminación de volumen;
  - cambio de escala.
- Determinar qué defectos materiales todavía podrían pasar las 62 comprobaciones.
- Confirmar que la doble regeneración es independiente y que no compara simplemente una salida contra sí misma.

## 10. Neutralidad respecto de candidatos

Comprobar que corpus, referencias y validador:

- no mencionan ni favorecen ADR002-A/B/C/D;
- no exigen implícitamente vectores, grafos, FTS5 o índice relacional;
- no confunden una señal con una tecnología;
- permiten que cualquiera de las cuatro alternativas pase si satisface el contrato;
- reservan las ablaciones para aportación marginal y no para conformidad.

## 11. Veredicto requerido

Emitir por separado:

1. corpus de conformidad: `APROBABLE PARA CONGELAR`, `APROBABLE CON CORRECCIONES` o `NO APROBABLE`;
2. corpus de rendimiento: mismo veredicto;
3. referencias y casos: mismo veredicto;
4. validador: mismo veredicto;
5. TOL-208: estado exacto y pasos que todavía faltan.

Para cada hallazgo:

- gravedad: BLOQUEANTE, MATERIAL, MENOR u OBSERVACIÓN;
- evidencia exacta;
- consecuencia;
- corrección mínima.

No recomendar congelación por el mero hecho de que las pruebas pasen.

## 12. Confirmaciones finales

Entregar únicamente:

1. veredicto global;
2. hallazgos por gravedad;
3. veredicto independiente de los cuatro componentes;
4. mutaciones adversariales realizadas y resultado;
5. defectos que el validador aún no detecta;
6. correcciones mínimas;
7. estado de TOL-208;
8. pruebas ejecutadas;
9. confirmación de `git status` limpio.

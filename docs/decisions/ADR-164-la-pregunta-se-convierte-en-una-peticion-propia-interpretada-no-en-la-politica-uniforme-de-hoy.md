# ADR-164 — La pregunta se convierte en una petición propia interpretada, no en la política uniforme de hoy

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.

## Nota de arranque (publicada ANTES del primer commit de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en
   `_peticion_ordinaria` (`src/sirius/application/rank_relevant_knowledge.py`):
   una sola política —M1, EXHAUSTIVA, tiempo objetivo «ahora», sin corte,
   propósito fijo— para las 47 preguntas del banco y para toda pregunta real.
   El arreglo NO vive dentro de esa función: vive **antes**, en un intérprete
   nuevo (`sirius.application.interpret_query_request`) que produce la
   `Peticion` y al que `rank()` llama en su lugar. El sitio del arreglo puede
   observar el fallo porque la `Peticion` emitida es un valor inspeccionable:
   una prueba puede capturarla y comparar campo a campo con la que el banco
   declara, cosa que la política uniforme nunca permitió distinguir.
2. **¿Qué NO va a garantizar esto?** No garantiza ninguna cifra del banco en
   CI: la inferencia de modo, cardinalidad, límite y tiempo la hace el modelo
   local, que no está en CI. En CI se fija la parte por reglas (permiso y
   propósito), la forma de la `Peticion` y el cableado; las cifras del banco
   solo las da Ollama real en la máquina del propietario. Tampoco garantiza el
   propósito por caso del banco (`planificar_viaje`, `verificar_fuente`…): el
   propósito es una regla del producto declarada por quien llama, no algo que
   se derive de la frase. Tampoco abre `category_matching_enabled`.
3. **Criterio de parada (decidido ANTES de ver ningún resultado).** La
   predicción de la medición con Ollama real, escrita antes de ejecutarla:
   **≥16/47 exactas, ≤162 elementos de más, 0 críticas perdidas, ≥73/81
   hallados**, y la coincidencia campo a campo con las 47 `peticion_p2` en
   **≥45 de 47** para modo, cardinalidad, límite, tiempo objetivo y corte de
   registro (el listón que ADR-148 fija para dar la palanca 1 por buena). Si
   sale por debajo, se registra el número tal cual y se para: no se ajusta la
   predicción después de verlo. Dos rondas de revisión con defectos de la
   misma familia → se para y se busca la raíz (ADR-001).
4. **¿Qué haría el fallo imposible en vez de improbable?** Que ninguna
   `Peticion` pudiera construirse sin declarar de dónde sale cada campo. No se
   hace en este encargo: obligaría a cambiar `Peticion`, que es contrato
   portado del laboratorio y está fuera del alcance. Lo que sí se hace es la
   forma débil: el único constructor de peticiones de producción pasa a ser el
   intérprete, y `_peticion_ordinaria` queda explícitamente como el respaldo
   de «el modelo no supo decidir», no como la política.

## Contexto y problema

Pendiente de cerrar al terminar la implementación.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué

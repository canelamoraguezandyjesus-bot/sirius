# ADR-132 — El guardián del contrato local de Ollama convierte ADR-125 en prueba y corrige ollama_category_classifier

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: fusión de la PR por el propietario

Este ADR registra G1, la propuesta 1 de
`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md` (rama
`claude/adr002-tol209-forensic-audit-i0ui8k`, sección 8), aprobada por el
propietario el 04-09-2026, incidencia #522.

## Contexto y problema

El repositorio tiene tres adaptadores locales de Ollama y un contrato HTTP ya
validado contra el modelo real (ADR-125): `/api/chat` (no `/api/generate`),
`think: false`, URL absoluta a `_OLLAMA_LOCAL_BASE_URL` y
`follow_redirects=False`. `src/sirius/adapters/ollama_relevance_filter.py` y
`src/sirius/adapters/ollama_criticality_classifier.py` lo cumplen (este
segundo, corregido en la PR #519, ya en `main`).
`src/sirius/adapters/ollama_category_classifier.py` NO lo cumple: llama a
`/api/generate` con un prompt libre, sin `think: false`, con ruta relativa a
la `base_url` del cliente inyectado y sin `follow_redirects=False` (deuda
registrada en ADR-130 y confirmada por la mina, incidencia #518). El
contrato hoy solo vive por copia entre ficheros: nada impide que un cuarto
adaptador futuro repita el mismo incumplimiento.

## Nota de arranque (ADR-001, disciplina-evidencia, publicada antes del primer commit de código)

**1. ¿Dónde vive el fallo y dónde voy a poner el arreglo? ¿Puede el sitio del
arreglo observar el fallo que arregla?**

El fallo vive en `src/sirius/adapters/ollama_category_classifier.py`: pide
`/api/generate` en vez de `/api/chat`, no apaga el razonamiento, resuelve la
URL contra la `base_url` del cliente inyectado en vez de una URL absoluta, y
no fija `follow_redirects=False`.

El guardián se pone en un fichero nuevo, `tests/automation/test_contrato_http_de_ollama.py`,
fuera de los tres adaptadores que vigila — lee su TEXTO fuente por glob
(`src/sirius/adapters/ollama_*.py`), así que no depende de ejecutar el
adaptador ni de que el adaptador se autodiagnostique: un proceso que muere no
puede informar de su propia muerte, pero un fichero de texto sí puede leerse
sin ejecutarlo.

El arreglo se pone en el mismo fichero que falla
(`ollama_category_classifier.py`), calcado de
`ollama_criticality_classifier.py` (la versión corregida en la PR #519). Que
el arreglo viva "dentro de lo que falla" no es un problema aquí porque quien
certifica que el arreglo es correcto no es el propio adaptador, sino el
guardián externo (b) y las pruebas unitarias de (c), que se ejecutan por
separado y ya vieron fallar el código viejo.

**2. ¿Qué NO va a garantizar esto?**

- No remide el modelo real de Ollama para categoría: ADR-125 midió el
  contrato HTTP contra el modelo real para el filtro de relevancia, y este
  encargo aplica el mismo contrato por calco a categoría, sin volver a medir
  contra Ollama (fuera de alcance; D7/§6.1 no cambia).
- No detecta un incumplimiento de una quinta propiedad del contrato que las
  cuatro aserciones no cubren (por ejemplo, un `temperature` o `num_ctx`
  distinto): el guardián fija exactamente las cuatro propiedades que el
  encargo describe, ni una más.
- No unifica los tres adaptadores en un cliente común, no abre la puerta
  `category_matching_enabled`, no cambia ningún vocabulario ni la firma de
  `classify`/`TagCategoryUseCase`: todo eso queda fuera de alcance por
  prohibición dura del encargo.
- Es una comprobación textual, no un análisis de AST: al igual que
  `tests/automation/test_citas_de_los_adr.py`, es deliberadamente
  conservadora — puede dejar pasar una construcción exótica que cite las
  cuatro cadenas sin implementarlas de verdad. Se acepta ese residual porque
  es el mismo trade-off ya validado por esa prueba hermana.

**3. Criterio de parada, decidido antes de ver ningún resultado**

- El guardián recién escrito debe fallar sobre EXACTAMENTE un fichero
  (`ollama_category_classifier.py`) y sobre ningún otro, antes del arreglo;
  tras el arreglo, verde sobre los tres adaptadores.
- Si el guardián falla sobre `ollama_relevance_filter.py` o
  `ollama_criticality_classifier.py` (la referencia, intocable por
  prohibición dura), PARO con `BLOCKED_BY_DECISION` en vez de tocarlos.
- Si `uv run python scripts/medir_variantes_de_criticidad.py` o las cifras
  de `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` cambian
  respecto a las de hoy en `main` (0 omisiones críticas, 72/81), PARO con
  `BLOCKED_BY_DECISION`: el contrato público de `classify` no debe cambiar,
  así que ninguna métrica del banco debería moverse; si se mueve, la premisa
  está mal y no es mío decidir cómo seguir.
- Dos rondas de validación (`ruff`/`mypy`/`pytest`) seguidas fallando por la
  misma causa → paro a diagnosticar la raíz en vez de seguir parcheando.

**4. ¿Qué haría el fallo imposible en vez de improbable?**

El guardián descubre los adaptadores vigilados por glob
(`src/sirius/adapters/ollama_*.py`), no por una lista mantenida a mano: un
cuarto adaptador de Ollama que aparezca mañana queda cubierto automáticamente
sin tocar la prueba, lo que convierte "alguien olvida añadir el adaptador
nuevo a la lista vigilada" en imposible en vez de improbable. Dentro de cada
fichero, las cuatro aserciones leen el TEXTO COMPLETO, no la línea del
`.post(`, así que una llamada partida en varias líneas (medido por el
propietario en `docs/audits/mina-2026-09-medicion-de-guardianes.md`) no puede
colar un incumplimiento por formato de línea. No hace imposible el residual
descrito en la pregunta 2 (quinta propiedad no cubierta, construcción
textual exótica); ese riesgo queda explícitamente aceptado, no eliminado.

## Criterio de parada (escrito ANTES de decidir)

Ver "Nota de arranque" arriba, punto 3: es el mismo criterio, publicado antes
de ejecutar el guardián por primera vez.

## Opciones consideradas

1. **Guardián por glob sobre el texto fuente de los adaptadores** (elegida).
   Cubre adaptadores futuros sin tocar la prueba; barata (no ejecuta red ni
   modelo); mismo estilo que `test_citas_de_los_adr.py`, ya aceptado en este
   repositorio.
2. Guardián por AST (parsear la llamada `.post(...)` como árbol de sintaxis
   en vez de buscar en el texto). Más preciso ante construcciones exóticas,
   pero bastante más código y acoplado a la forma exacta en que cada
   adaptador construye la llamada — el encargo pide explícitamente mirar el
   fichero entero por la partición en varias líneas, no un nodo AST
   concreto. Descartada por complejidad no pedida por el encargo.
3. Prueba de integración contra un Ollama real, corriendo en el runner.
   Fuera de alcance: el encargo pide un guardián estático, y el entorno del
   runner no tiene Ollama disponible (regla del rol: no instalar nada fuera
   del perímetro).

## Decisión

Se implementa el guardián por glob sobre texto (opción 1) en
`tests/automation/test_contrato_http_de_ollama.py`, y se corrige
`ollama_category_classifier.py` calcando `ollama_criticality_classifier.py`
en su versión ya corregida, con las pruebas unitarias de
`tests/unit/test_ollama_category_classifier.py` puestas al mismo nivel que su
gemelo `tests/unit/test_ollama_criticality_classifier.py`.

## Comprobación que la sostiene

(Se completa en el mismo commit o en uno posterior de esta rama, con la
salida literal del guardián en rojo sobre el código viejo, las tres
mutaciones y las cifras del banco antes/después, según el punto (e) del
encargo.)

## Consecuencias

(Se completa junto con la comprobación.)

## Alternativas descartadas y por qué

Ver "Opciones consideradas".

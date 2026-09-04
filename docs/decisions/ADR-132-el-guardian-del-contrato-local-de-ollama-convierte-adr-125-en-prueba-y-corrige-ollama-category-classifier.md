# ADR-132 — El guardián del contrato local de Ollama convierte ADR-125 en prueba y corrige ollama_category_classifier

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

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

**(a) El guardián, en rojo sobre el código viejo, exactamente como predijo el
encargo.** `tests/automation/test_contrato_http_de_ollama.py` recorre por
glob `src/sirius/adapters/ollama_*.py` y afirma las cuatro propiedades sobre
el texto completo de cada fichero. Antes del arreglo:

```
$ uv run pytest tests/automation/test_contrato_http_de_ollama.py -v
FAILED ...test_pide_api_chat_y_no_api_generate[ollama_category_classifier.py]
PASSED ...test_pide_api_chat_y_no_api_generate[ollama_criticality_classifier.py]
PASSED ...test_pide_api_chat_y_no_api_generate[ollama_relevance_filter.py]
FAILED ...test_apaga_el_pensamiento_explicitamente[ollama_category_classifier.py]
PASSED ...test_apaga_el_pensamiento_explicitamente[ollama_criticality_classifier.py]
PASSED ...test_apaga_el_pensamiento_explicitamente[ollama_relevance_filter.py]
FAILED ...test_la_url_del_post_es_absoluta[ollama_category_classifier.py]
PASSED ...test_la_url_del_post_es_absoluta[ollama_criticality_classifier.py]
PASSED ...test_la_url_del_post_es_absoluta[ollama_relevance_filter.py]
FAILED ...test_no_sigue_redirecciones[ollama_category_classifier.py]
PASSED ...test_no_sigue_redirecciones[ollama_criticality_classifier.py]
PASSED ...test_no_sigue_redirecciones[ollama_relevance_filter.py]
========================= 4 failed, 17 passed in 0.08s =========================
```

Exactamente un fichero falla (`ollama_category_classifier.py`), sobre las
cuatro propiedades, y ninguno de los dos adaptadores de referencia falla
nunca — la predicción exacta del encargo, y el criterio de parada de la nota
de arranque no se disparó.

**Un defecto propio, cazado y corregido antes de aceptar el rojo como
bueno.** Al escribir el guardián por primera vez, la propiedad 1
(`pide_api_chat_no_api_generate`) marcaba también `ollama_criticality_classifier.py`
como incumplidor — la referencia, justo lo que el criterio de parada prohíbe
tocar. La causa: esa comprobación buscaba la subcadena `/api/generate` en
todo el texto, y el docstring de `ollama_criticality_classifier.py` la
menciona en prosa (envuelta en `` ``comillas invertidas`` ``, el estilo RST
de este repositorio) para explicar, por CONTRASTE, por qué el adaptador NO
la usa. No era un incumplimiento real del contrato: era una imprecisión del
propio guardián. Se corrigió ignorando las apariciones envueltas en dobles
comillas invertidas antes de comprobar, y una segunda ronda de mutación
(quitar el `follow_redirects=False` real de `ollama_category_classifier.py`
dejando intacto el comentario que lo menciona, también entre comillas
invertidas) encontró el mismo defecto en la propiedad 4 antes de publicarla:
el guardián pasaba en verde con el código roto porque el comentario seguía
mencionando la cadena buscada. Ambas se corrigieron con la misma técnica
general (`_sin_prosa`, que quita todo lo envuelto en `` `` `` antes de
comprobar cualquiera de las cuatro propiedades) y quedan fijadas con texto
sintético en `test_una_mencion_en_prosa_de_api_generate_no_se_confunde_con_una_peticion_real`
y `test_faltar_follow_redirects_false_se_detecta_aunque_un_comentario_lo_mencione`.
Ninguno de los dos adaptadores de referencia se tocó: la parada correcta,
seguida en la nota de arranque, era corregir el guardián, no el código que
vigilaba correctamente.

**(b) El arreglo, verde sobre los tres adaptadores:**

```
$ uv run pytest tests/automation/test_contrato_http_de_ollama.py -q
.....................
21 passed in 0.05s
```

(21 propiedades tras el arreglo: 12 parametrizadas por los tres adaptadores
más 9 pruebas de la sección anti-vacua/mutación del propio guardián.)

**(c) Las pruebas del adaptador, vistas fallar antes del arreglo.** Con
`ollama_category_classifier.py` revertido temporalmente a su versión vieja
(`/api/generate`), las cuatro pruebas nuevas de
`tests/unit/test_ollama_category_classifier.py` fallan:

```
FAILED test_classify_returns_the_categoria_ollama_answers_with - AssertionError: assert None == 'trabajo'
FAILED test_classify_sends_the_contract_validated_against_the_real_model - AssertionError: assert '/api/generate' == '/api/chat'
FAILED test_classify_ignores_an_injected_clients_remote_base_url - AssertionError: assert ['servidor-remoto.example'] == ['localhost']
FAILED test_classify_never_follows_a_redirect_to_a_remote_host - AssertionError: assert ['localhost',...example', ...] == ['localhost']
4 failed, 8 passed in 0.35s
```

Con el arreglo aplicado, las 12 pruebas del fichero pasan.

**(d) Las tres mutaciones, cada una vista fallar exactamente donde predice
el encargo (adaptador corregido, mutado, restaurado tras cada prueba):**

1. Quitar `follow_redirects=False` real (dejando el comentario que lo
   menciona): fallan `test_classify_never_follows_a_redirect_to_a_remote_host`
   (unitaria) y `test_no_sigue_redirecciones[ollama_category_classifier.py]`
   (guardián); los dos adaptadores de referencia siguen en verde.
2. Cambiar la URL absoluta por ruta relativa (`"/api/chat"` en vez de
   `f"{_OLLAMA_LOCAL_BASE_URL}/api/chat"`): fallan
   `test_classify_ignores_an_injected_clients_remote_base_url` (unitaria,
   `['servidor-remoto.example'] != ['localhost']`) y
   `test_la_url_del_post_es_absoluta[ollama_category_classifier.py]`
   (guardián).
3. Poner `_PENSAMIENTO_APAGADO` a `True`: falla
   `test_classify_sends_the_contract_validated_against_the_real_model`
   (`assert True is False` sobre `cuerpo["think"]`).

**(e) Nada del banco de evidencia se movió**, tal como predecía la nota de
arranque (el contrato público de `classify` no cambia):

```
$ uv run python scripts/medir_variantes_de_criticidad.py
  variante            exactos  de mas  crit perdidas  cobertura
  hoy                    0/47     487              0      72/81
```

Idéntico antes (en `main`, `dc731d4`) y después del arreglo: 0 omisiones
críticas, 72/81. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
también idéntico en ambos árboles: 28 passed, 1 skipped, 1 xfailed.

**Validaciones obligatorias, en verde sobre el árbol final:**

```
$ uv run ruff format --check .    # 595 files already formatted
$ uv run ruff check .             # All checks passed!
$ uv run mypy src tests           # Success: no issues found in 563 source files
$ uv run pytest -q                # 4678 passed, 15 skipped, 2 xfailed
```

(`test_toda_ruta_citada_por_un_adr_existe` exigió registrar las dos citas de
este ADR a `docs/audits/` en `RAMA_DE_ORIGEN_NO_FUSIONADA` de
`tests/automation/test_citas_de_los_adr.py:163-266`, porque ambas viven solo
en la rama `claude/adr002-tol209-forensic-audit-i0ui8k` que la mina cita como
origen y que a propósito nunca se fusiona entera — mismo patrón que las
demás excepciones ya registradas ahí para ADR-104 y siguientes.)

## Consecuencias

- `ollama_category_classifier.py` cumple ahora el mismo contrato HTTP
  validado contra el modelo real que los otros dos adaptadores (ADR-125): el
  defecto medido en la incidencia #518 para esa familia queda cerrado para
  los tres adaptadores existentes.
- Un cuarto adaptador `ollama_*.py` que aparezca en el futuro queda cubierto
  por el guardián sin tocar la prueba: el defecto de "un adaptador nuevo
  repite el incumplimiento" pasa de improbable a imposible en ese sentido
  concreto (ver "Nota de arranque", pregunta 4).
- El propio guardián recibió dos rondas de mutación antes de publicarse
  (propiedades 1 y 4), cada una encontrando el mismo tipo de defecto: una
  comprobación textual ingenua confundida por prosa que menciona, en vez de
  usar, la cadena buscada. Queda como patrón a vigilar en futuros guardianes
  de texto de este repositorio: cualquier comprobación sobre código en un
  fichero con docstrings/comentarios en el mismo estilo RST de este
  repositorio debería considerar ignorar las menciones entre `` `` ``.
- El vocabulario, la firma de `classify`, `TagCategoryUseCase` y la puerta
  `category_matching_enabled` no cambian: ninguna prohibición dura del
  encargo se tocó.
- `_REQUEST_TIMEOUT_SECONDS` de `ollama_category_classifier.py` pasa de 5.0 s
  a 30.0 s (el mismo valor medido para `ollama_criticality_classifier.py`,
  ADR-125): con `think: false`, es el único techo que este repositorio ha
  medido contra el modelo real para esta familia de llamada.

## Alternativas descartadas y por qué

Ver "Opciones consideradas".

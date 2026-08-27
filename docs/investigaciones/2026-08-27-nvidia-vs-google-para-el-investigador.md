---
titulo: NVIDIA vs Google para el Investigador de Sirius
fecha: 2026-08-27
autor: investigación profunda encargada por el propietario
pregunta: >-
  Cuál de los dos proveedores conviene para el investigador de Sirius,
  atendiendo a calidad, precio y todo lo que conlleva.

# DE QUÉ DEPENDE PARA CADUCAR. Ésta es la parte que hay que leer antes que el
# informe: no es un adorno, es la diferencia entre una fuente y un fósil.
caduca_con:
  - nombres de modelo de cualquier proveedor
  - precios publicados
  - condiciones de uso de las capas gratuitas
  - qué modelos incluye la cuota de una cuenta concreta

# CÓMO SE ENVEJECIÓ, medido y no supuesto.
estado: PARCIALMENTE CADUCADA
caducado_en: 2026-08-27
horas_de_vida_util: 24
---

> ## AVISO ANTES DE LEER — esta investigación caducó en un día
>
> Se encargó el 27-08-2026 y **el mismo día** sus recomendaciones ya no
> encajaban con la realidad. Está aquí por lo que enseña, no por lo que
> recomienda.
>
> **Lo que acertó, y no es poco:** que `text-embedding-004` y
> `nv-embedqa-e5-v5` estaban muertos, y que el arnés reproducía variables de
> entorno en vez de demostrar con quién hablaba. Las dos cosas se confirmaron
> llamando al servidor.
>
> **Lo que falló:** sus dos sustitutos para NVIDIA
> —`llama-nemotron-embed-1b-v2` y `bge-m3`— **no están en el catálogo de la
> cuenta**. Y su recomendación principal, `gemini-2.5-flash`, aparece en el
> catálogo de Google y contesta *«This model is no longer available»*.
>
> **La lección, que es lo que de verdad se guarda aquí:** una investigación
> sobre el estado de un servicio externo es **una foto con fecha**, no una
> fuente. Sirve para decidir qué preguntar; nunca para responder. Lo que
> responde es el servidor, y por eso existe `preflight.py` (ADR-095).
>
> El estado vigente de qué modelo funciona **no se lee aquí**: se lee en
> `scripts/investigacion/modelos_atestiguados.yml`, que escribe una máquina
> después de llamar.

# NVIDIA vs Google para el Investigador de Sirius: investigación decisoria

## Veredicto ejecutivo y alcance

**EVIDENCIA INSUFICIENTE PARA DECIDIR.** Aplicando literalmente las puertas duras definidas para Sirius, hoy no es correcto declarar vencedor formal ni a NVIDIA ni a Google: las **dos configuraciones exactas fusionadas en la PR #359 tienen un embedding que ya no es válido como opción vigente**, el workflow sigue sin estar habilitado para ejecutarse y, más importante aún, el arnés todavía **no demuestra de forma independiente qué servidor/modelo respondió**; reproduce variables de entorno. Además, no existe todavía un bake-off real N=3 con fuentes y credenciales. fileciteturn8file0L3-L15 fileciteturn19file0L2-L2 fileciteturn18file0L2-L2

**Sin embargo, como decisión de ingeniería provisional, el candidato que debe rehabilitarse y probarse primero es GOOGLE**, con `gemini-2.5-flash` + `gemini-embedding-2`. Google tiene hoy una ruta mucho más clara desde laboratorio a uso pagado, precio público por token y una sustitución oficial para `text-embedding-004`; NVIDIA conserva ventajas de portabilidad y catálogo multimodelo, pero su embedding de la PR está deprecado, su API gratuita es una vía de prototipado y sus términos gratuitos son significativamente peores para un Worker que pudiera recibir contexto confidencial. citeturn22search7turn24search0turn19view0turn15view2

Esta conclusión distingue dos preguntas que no deben mezclarse:

| Pregunta | Conclusión a 27-08-2026 |
|---|---|
| ¿Podemos afirmar ya que Google investiga mejor que NVIDIA dentro de GPT Researcher? | **No. No existe la medición Sirius que lo demuestre.** |
| ¿Cuál es hoy la vía con menor riesgo para convertirla en candidato principal y lanzar esa medición? | **Google.** |
| ¿Debe descartarse NVIDIA? | **No.** Debe conservarse como candidato de laboratorio/fallback, pero no como “API gratuita de producción”. |
| ¿Está bien la PR #359 tal cual está en `main`? | **No para ejecutarla hoy.** Las dos ramas necesitan saneamiento previo. |

La fecha de consulta de la evidencia mutable de proveedores es **27 de agosto de 2026, Europe/Madrid**.

## Estado real de Sirius y auditoría de la PR

La secuencia del repositorio confirma que la arquitectura que plantea la pregunta está bien entendida y no debe rediseñarse. La PR #171 está cerrada y **no fusionada**; era la línea histórica que mezclaba repositorio privado y web. fileciteturn0file0L3-L15 La PR #173 sí se fusionó y fijó la arquitectura mínima: el Work Engine posee el estado, los Workers son sustituibles, la red externa es incompatible con contexto privado irrestricto y GPT Researcher debe recibir contexto únicamente a través de `ExportSafeBrief`. fileciteturn1file0L3-L14

La PR #175, también fusionada, convirtió eso en el plan de implementación: **S2/I2 primero; B1 GPT Researcher + ExportSafeBrief después**. Además decidió que #171 debía descomponerse y cerrarse, precisamente porque su variante “repositorio privado + web” violaba la política de egress aprobada. fileciteturn2file0L3-L14

La PR #260 fusionó el principio correcto para esta decisión: un banco debe decir “bajo el mismo agente, herramientas y casos, A produjo X y B produjo Y”, no elegir por reputación del proveedor. También registró el interés de NVIDIA como API compatible con OpenAI y catálogo multimodelo, pero dejó explícito que **elegir antes de medir es el error que el banco existe para evitar**. fileciteturn3file0L3-L14

La incidencia #258 midió la superficie inicial de GPT Researcher y estimó, con los parámetros del paquete usados por Sirius, aproximadamente **41.000 tokens de entrada y 12.000 de salida por investigación completa**; a la vez reconoció que no había realizado una investigación web real por restricciones de red. fileciteturn4file0L3-L7 Un comentario posterior dejó registrada una preferencia histórica por Gemini y después descubrió el punto crítico de los embeddings: no basta tener un LLM; el proveedor debe poder cubrir también vectorización sin introducir una segunda cuenta. fileciteturn5file0L26-L45

La PR #350 está cerrada sin merge y es efectivamente una rama conceptual errónea: convertía al “investigador” en lector del repositorio y prohibía las fuentes externas. fileciteturn6file0L2-L15 La #351, fusionada, corrige expresamente esa confusión: investigar es **hacia fuera**; para el repositorio está el Auditor. También fija `gpt-researcher 0.15.1` como versión que instala limpiamente en el spike y deja pendiente la calidad real. fileciteturn7file0L2-L15

Hay una actualización importante respecto al estado que constaba durante la conversación anterior: la **PR #359 ya no está abierta; está cerrada y fusionada**. Su `head` fue `7be49430e51d343610a778d205a468e0a4b39e95` y el merge commit es `f47ad7791e1a6d4ff0d38fe244f9a6732cbd6cf2`. fileciteturn8file0L3-L15

**Lo que realmente está en `main` hoy** es:

| Elemento de PR #359 | Estado actual verificado | Veredicto | Corrección necesaria |
|---|---|---|---|
| `gpt-researcher==0.15.1` | Sirius lo fija en un entorno Python 3.12 separado; el workflow también fija `langchain-google-genai==4.3.5`. fileciteturn20file0L2-L2 | **Válido dentro de la arquitectura actual** | Mantener fijado durante el bake-off. No actualizar la herramienta a la vez que el proveedor. |
| NVIDIA `https://integrate.api.nvidia.com/v1` | Sigue siendo el host documentado por NVIDIA para chat y embeddings. citeturn23search18turn23search0 | **Válido** | Ninguna por el host. |
| NVIDIA `meta/llama-3.3-70b-instruct` | Sigue existiendo en el catálogo/API de NVIDIA como modelo hospedado de prototipo. citeturn13search0 | **Válido para el experimento** | No cambiarlo antes del primer bake-off corregido. |
| NVIDIA `nvidia/nv-embedqa-e5-v5` | El modelo y API siguen documentados, pero el free endpoint aparece actualmente **deprecado**. Además la API exige distinguir `query`/`passage`. citeturn12search3turn23search0 | **No aceptable como configuración nueva** | Sustituirlo y probar el nuevo embedding antes del benchmark. |
| Google `google_genai:gemini-2.5-flash` | `gemini-2.5-flash` sigue listado como modelo estable. La preview antigua se cerró el 17-02-2026, pero el ID estable continúa activo. citeturn22search2turn22search3 | **Válido** | Mantenerlo para no cambiar dos variables a la vez. |
| Google `google_genai:models/text-embedding-004` | Google cerró `text-embedding-004` el **14-01-2026** y designa `gemini-embedding-2` como reemplazo. citeturn22search7 | **Incorrecto / retirado** | Cambiar a `models/gemini-embedding-2`, sujeto a preflight de la librería fijada. |
| DuckDuckGo | El arnés instala ya `ddgs` y no el paquete incorrecto que originó el falso verde. fileciteturn20file0L2-L2 | **Estructuralmente corregido** | Conservar mismo retriever en ambas ramas. |
| `fuentes > 0` | El medidor actual exige informe, ausencia de error y al menos una fuente para contar un acierto. fileciteturn18file0L2-L2 | **Correcto y necesario** | Añadir además calidad/relevancia de fuente. |
| Aislamiento NVIDIA/Google | Cada configuración se ejecuta en un subproceso con entorno reconstruido para evitar que `OPENAI_BASE_URL` de NVIDIA contamine Google. fileciteturn21file0L2-L2 | **Correcto** | Mantener. |
| `STRATEGIC_LLM` | Se fija explícitamente en ambas ramas para impedir el fallback a `openai:o4-mini`. fileciteturn19file0L2-L2 | **Correcto** | Mantener. |
| Atestación de servidor/modelo | `servidor` sigue saliendo de `os.environ["OPENAI_BASE_URL"]`, y modelo/embedding se reconstruyen igualmente desde variables de entorno. Eso demuestra **lo configurado**, no la identidad de la respuesta remota. fileciteturn18file0L2-L2 | **Incorrecto para la puerta dura 8** | Registrar host remoto observado + metadata de respuesta/modelo en un preflight real. |
| Activación del workflow | En `main`, `workflow_dispatch` sigue comentado y solo existe `workflow_call`; el propio fichero dice que no tiene llamantes. fileciteturn19file0L2-L2 | **No ejecutable todavía como benchmark manual** | No habilitar hasta cerrar los preflights y reemplazar embeddings. |

Hay además una contradicción documental actual de Google que merece registrarse. La página oficial de deprecaciones presenta **`gemini-embedding-2` como versión vigente sin fecha de cierre** y reemplazo de `text-embedding-004`, mientras que el índice general de modelos muestra todavía en una entrada `gemini-embedding-2-preview`, a pesar de que la propia tabla de deprecaciones dice que esa preview cerró el 10-08-2026. La fuente de ciclo de vida favorece claramente al ID estable, pero el arnés debe hacer `models.get/list` + una llamada `embedContent` antes de asumirlo. citeturn22search7turn22search3

**Qué servicios estamos comparando realmente:**

| Proveedor | En alcance para Sirius | No confundir con |
|---|---|---|
| Google | **Gemini Developer API**, obtenida/configurada mediante Google AI Studio; `gemini-2.5-flash` y Gemini Embeddings bajo la misma familia de API. citeturn22search8turn22search3 | Vertex AI; el producto Gemini para usuarios; el modelo/agente administrado **Gemini Deep Research**; Google Search grounding. El catálogo de Google ya expone Deep Research como familia separada y Sirius no la está utilizando. citeturn22search3 |
| NVIDIA | API alojada de NVIDIA/API Catalog-NIM mediante `integrate.api.nvidia.com`; interfaz de chat compatible con OpenAI y endpoint de embeddings. citeturn23search18turn23search0 | NIM descargado/self-hosted, NVIDIA AI Enterprise o endpoints de partners para producción. La vía gratuita alojada es de prototipado, no una licencia de producción. citeturn15view2turn19view0 |

Esto también significa que **Google Search grounding no forma parte del coste de Sirius** mientras `RETRIEVER=duckduckgo`; añadirlo posteriormente sería cambiar simultáneamente modelo y recuperación y rompería el bake-off actual. La API de Google tiene precios separados para grounding, pero la configuración de Sirius no lo invoca. fileciteturn15file0L2-L2 citeturn24search0

## Puertas duras y matriz técnica

Aplicando las nueve puertas **antes** de puntuar, el resultado formal es éste. “FAIL — no demostrado” no significa que el proveedor sea incapaz; significa que la evidencia que exige la puerta todavía no existe.

| Puerta | NVIDIA | Google | Evidencia |
|---|---|---|---|
| LLM + embeddings viables bajo arquitectura actual | **FAIL hoy** | **FAIL hoy** | NVIDIA conserva LLM, pero su embedding configurado está deprecado y exige semántica `query/passage`; Google conserva LLM, pero `text-embedding-004` cerró en enero. citeturn23search0turn22search7 |
| Investigación real sin cero fuentes frecuentes | **FAIL — no demostrado** | **FAIL — no demostrado** | El arnés sabe detectar cero fuentes, pero todavía no ha realizado el bake-off real. El workflow permanece desactivado. fileciteturn18file0L2-L2 fileciteturn19file0L2-L2 |
| No requiere OpenAI/Anthropic de pago | **PASS** | **PASS** | NVIDIA transforma `NVIDIA_API_KEY` a `OPENAI_API_KEY` únicamente porque usa el protocolo compatible; Google usa `GOOGLE_API_KEY`. Todas FAST/SMART/STRATEGIC están fijadas. fileciteturn15file0L2-L2 |
| No recibe repositorio privado irrestricto | **PASS** | **PASS** | Es una propiedad del Work Engine/`ExportSafeBrief`, no del proveedor. fileciteturn1file0L8-L15 |
| No introduce autoridad/estado canónico | **PASS** | **PASS** | Ambos siguen siendo Workers sustituibles detrás del Adapter. fileciteturn1file0L8-L15 |
| Configuración depende de modelos/endpoints vivos | **FAIL** | **FAIL** | En ambos casos el embedding actual invalida la configuración completa. citeturn12search3turn22search7 |
| “Gratis” coincide con las condiciones del uso de Sirius | **FAIL para producción** | **PASS para laboratorio; producción EEA requiere cautela** | NVIDIA limita su servicio gratuito a trial/prototipado y exige otra vía para producción. Google publica free tier, pero sus términos distinguen Paid/Unpaid Services y el tratamiento EEA. citeturn19view0turn15view2turn24search0turn21search8 |
| El arnés demuestra proveedor/modelo real | **FAIL** | **FAIL** | El JSON actual deriva `servidor`, FAST/SMART y embedding de variables de entorno, no de metadata de la respuesta o del host observado. fileciteturn18file0L2-L2 |
| No existe fallback silencioso | **PASS estructural** | **PASS estructural** | FAST/SMART/STRATEGIC/EMBEDDING se fijan explícitamente y los procesos están aislados; falta confirmación mediante ejecución real. fileciteturn15file0L2-L2 fileciteturn21file0L2-L2 |

Por tanto, **el propio método solicitado impide adjudicar un ganador hoy**. Puntuar y declarar Google o NVIDIA vencedor ignorando estas puertas sería contradecir el criterio del encargo.

La comparación técnica después de aplicar las correcciones mínimas queda así:

| Dimensión | Google | NVIDIA | Lectura para Sirius |
|---|---|---|---|
| LLM del arnés | `gemini-2.5-flash`, estable, ~1,05 M tokens de entrada y 65.536 de salida. citeturn22search2turn22search3 | `meta/llama-3.3-70b-instruct`, todavía ofertado por NVIDIA. citeturn13search0 | Ambos siguen siendo candidatos válidos. |
| Embedding de PR #359 | **Muerto**: `text-embedding-004`. citeturn22search7 | **Deprecado**: `nv-embedqa-e5-v5`. citeturn12search3 | Ninguno debe correr tal cual. |
| Reemplazo | Google designa oficialmente `gemini-embedding-2`. citeturn22search7 | NVIDIA no dio, en la documentación localizada, una relación de deprecación→sustituto tan inequívoca. `nvidia/llama-nemotron-embed-1b-v2` es un candidato actual de 8.192 tokens y hasta 2.048 dimensiones. citeturn23search19 | Ventaja Google: migración explícita. |
| Compatibilidad OpenAI de embeddings | No aplica: vía nativa `google_genai`. | Riesgo material: E5 requiere `input_type=query/passsage`; una llamada OpenAI estándar no contiene necesariamente ese campo. NVIDIA documenta incluso sufijos especiales para compatibilidad OpenAI en algunos endpoints. citeturn23search0turn23search3 | NVIDIA necesita smoke específico de embeddings, no solo HTTP 200. |
| Alternativa NVIDIA con schema más estándar | — | `baai/bge-m3` aparece en el endpoint `integrate.../v1/embeddings` con campos OpenAI-like y sin `input_type` obligatorio, 8.192 tokens. citeturn23search16turn23search21 | **Inferencia:** puede ser mejor candidato de compatibilidad para GPT Researcher, pero entitlement/free-tier debe probarse. |
| Una credencial | Gemini API abarca generación y embeddings; el arnés usaría una `GOOGLE_API_KEY`. citeturn22search8turn22search7 | Los endpoints actuales de chat y embeddings viven bajo la superficie de NVIDIA y el arnés usa una `NVIDIA_API_KEY`. citeturn23search18turn23search0 | En principio ambos cumplen la meta “una cuenta”; debe validarse con las claves reales. |
| Contexto largo | Muy favorable: 1.048.576 tokens en 2.5 Flash. citeturn22search2 | Llama 3.3 es muy inferior en ventana a Gemini, aunque suficiente para muchos pasos de GPT Researcher. citeturn13search0 | Ventaja Google para síntesis de contexto grande; no demuestra mejor investigación por sí sola. |
| API estratégica | Google recomienda actualmente Interactions para flujos agentic; `generateContent` continúa como endpoint estándar. citeturn22search8 | OpenAI-compatible `/v1/chat/completions` es una superficie sencilla y portable. citeturn23search18 | NVIDIA gana portabilidad; Google tiene algo más de dependencia nativa. |
| Catálogo | Un ecosistema Gemini coherente. citeturn22search3 | Gran valor como catálogo multimodelo tras una misma interfaz. citeturn23search18 | Ventaja estratégica NVIDIA. |
| Producción | Gemini Developer API dispone de pricing pagado por consumo. citeturn24search0 | El acceso gratuito NVIDIA estudiado es trial/prototipado; producción requiere otra modalidad. citeturn19view0turn15view2 | Ventaja clara Google para transición laboratorio→producción. |

Un segundo hallazgo adversarial en NVIDIA merece atención especial. La referencia de la API de `nv-embedqa-e5-v5` dice que el input puede llegar a **8.192 tokens**, mientras que la ficha del propio modelo declara **512 tokens** de contexto máximo. Son dos fuentes oficiales de NVIDIA y no deben reconciliarse por intuición. Hasta un test de frontera real, Sirius debería tratarlo como una contradicción de especificación. citeturn23search0turn23search1

## Coste, cuotas y fiabilidad operativa

El mejor dato de carga disponible dentro de Sirius es el medido/documentado en #258: una investigación “normal” de GPT Researcher se aproximó a **41.000 tokens de entrada del LLM + 12.000 de salida**, con 3 subconsultas, 15 páginas y el informe final. Ese número debe utilizarse como baseline, no como promesa de consumo exacto para cada pregunta. fileciteturn4file0L3-L7

Google publica actualmente para `gemini-2.5-flash` **$0,30 por millón de tokens de entrada textual y $2,50 por millón de tokens de salida, incluidos thinking tokens**, además de un nivel gratuito. `gemini-embedding-2` publica **$0,20 por millón de tokens de texto** y también nivel gratuito. citeturn24search0turn24search1

Por tanto:

\[
C_{\text{LLM}} =
41.000 \times 0,30/10^6 +
12.000 \times 2,50/10^6
= \$0,0423
\]

El consumo real de embeddings **no está medido en #258**, por lo que no es legítimo esconder una estimación dentro del total. La fórmula completa de Google es:

\[
C_{\text{investigación}} =
\$0,0423 +
E \times \$0,20/10^6
\]

donde `E` es el número real de tokens enviados al embedding.

Como techo ilustrativo —**INFERIDO, no medido**—, si las 15 páginas de 8.192 caracteres de la estimación previa produjesen aproximadamente 30.720 tokens vectorizados, el embedding sumaría unos **$0,00614**, y el total aproximado sería **$0,04844 por investigación**. La hipótesis de 30.720 no debe convertirse en presupuesto hasta instrumentar el contador real. El precio unitario sí es oficial. fileciteturn4file0L3-L7 citeturn24search0

| Escenario Google 2.5 Flash | LLM medido/estimado desde #258 | Embedding ilustrativo de 30.720 tokens | Total ilustrativo |
|---|---:|---:|---:|
| 1 investigación | $0,0423 | $0,00614 | **$0,04844** |
| 100 investigaciones | $4,23 | $0,6144 | **$4,8444** |
| 1.000 investigaciones | $42,30 | $6,144 | **$48,444** |

No hay cargo de Google Search en esa tabla porque Sirius utiliza DuckDuckGo; ese coste solo aparecería si se activara grounding/búsqueda de Google explícitamente. fileciteturn15file0L2-L2 citeturn24search0

**La capa gratuita de Google es real, pero no debe traducirse a “X investigaciones gratis al día” con un número inventado.** La documentación actual dice que los rate limits dependen del modelo y tier, que los límites activos se consultan en AI Studio y que incluso los límites mostrados no garantizan capacidad. La página pública da algunos límites batch —por ejemplo, 3 millones de tokens encolados para 2.5 Flash en Tier 1 y 500.000 para embeddings—, pero no publica un número estático universal de investigaciones interactivas completas para cada proyecto. citeturn22search0

Por eso la afirmación correcta es:

> **Google: $0 mientras las llamadas permanezcan dentro del free tier aplicable al proyecto; después, aproximadamente $0,0423 + embeddings por investigación bajo la carga de #258. El número exacto de investigaciones que caben gratis debe leerse en la cuota activa del proyecto y dividirse por el consumo real medido.** citeturn22search0turn24search0

NVIDIA es diferente. NVIDIA presenta determinados modelos del catálogo con endpoint gratuito para desarrollo/prototipado, pero los términos del servicio limitan ese acceso a **trial, testing/evaluation y no producción**, con capacidad/créditos limitados; para producción se necesita una relación/subscripción separada con NVIDIA o un proveedor. La documentación de su programa de desarrolladores repite esta distinción. citeturn19view0turn15view2turn14search0

Por ello no sería correcto presentar:

| Escenario NVIDIA hosted prototype | Coste verificable |
|---|---|
| 1 investigación | **$0 si entra en la cuota/trial vigente y los endpoints seleccionados están habilitados.** citeturn15view2 |
| 100 investigaciones | **NO VERIFICABLE públicamente como $0.** El límite depende del modelo/cuenta/capacidad y no constituye una cuota de producción garantizada. citeturn15view2 |
| 1.000 investigaciones | **NO VERIFICABLE.** |
| Después del trial | **NO existe en la evidencia consultada un precio público universal por token equivalente al de Gemini para esa misma modalidad.** Producción pasa a otra modalidad/partner/AI Enterprise. citeturn19view0turn15view2 |

Ésta es una diferencia estratégica importante: **Google tiene coste marginal conocido; NVIDIA tiene coste de laboratorio potencialmente cero pero no un camino alojado de producción comparable cuya tarifa pueda ponerse en la misma fórmula**. citeturn24search0turn19view0

En límites y fiabilidad, ninguna de las dos APIs permite hoy escribir honestamente una tabla universal `RPM/TPM/RPD` aplicable a la cuenta de Sirius. Google remite los límites activos a AI Studio y advierte que la capacidad real puede variar. citeturn22search0 NVIDIA indica que sus límites de API gratuita varían según modelo/concurrencia y que las pruebas sin coste pueden experimentar espera adicional; su modalidad gratuita tampoco ofrece la postura de producción del producto empresarial. citeturn15view2

La lectura operativa es por tanto:

| Riesgo | Google | NVIDIA |
|---|---|---|
| 429 en investigación larga | Existe; cuota real debe capturarse antes y durante el benchmark. citeturn22search0 | Existe y es especialmente relevante en endpoints de prototipo con capacidad compartida. citeturn15view2 |
| TPM/RPM exacto | **NO VERIFICADO hasta mirar el proyecto Sirius.** | **NO VERIFICADO hasta mirar la cuenta/modelos.** |
| Concurrencia | Dependiente de tier/capacidad. citeturn22search0 | Dependiente de modelo/capacidad. citeturn15view2 |
| SLA adecuado para producción en la modalidad comparada | **No identificado en esta investigación para Gemini Developer API estándar.** | **No:** la modalidad gratuita analizada es de prototipo/trial. citeturn19view0 |
| Camino a producción sin cambiar de familia | Sí, mediante paid tier de Gemini API. citeturn24search0 | No con la simple promesa de “Free Endpoint”; hay que cambiar la relación comercial/despliegue. citeturn19view0turn15view2 |

## Calidad y bake-off reproducible

**No existe hoy resultado empírico Sirius NVIDIA vs Google que pueda citarse.** La PR #351 dejó escrito que ni una sola pregunta se había contestado realmente debido a la red. fileciteturn7file0L8-L15 La PR #359 construyó y endureció el arnés, pero su propio workflow continúa con el disparador manual desactivado y declara que no se había ejecutado la comparación. fileciteturn19file0L2-L2

Eso impide afirmar cosas como “Gemini investiga mejor” o “Llama 3.3 razona mejor para GPT Researcher”. Google documenta un contexto enorme y capacidades de razonamiento en 2.5 Flash; NVIDIA publica benchmarks generales para Llama 3.3. Esos datos permiten formular hipótesis, **no adjudicar los 35 puntos de calidad de investigación de Sirius**. citeturn22search2turn12search15

El banco actual tampoco es suficiente como prueba final. Contiene cinco preguntas —Canberra, 1969, licencia de GPT Researcher, lenguaje de `uv` y Pyre— y dos están explícitamente marcadas como “memoria”. fileciteturn16file0L2-L2 La propia refutación posterior comprobó que incluso las otras tres podían salir del conocimiento previo del modelo, razón por la que un falso 100 % con cero fuentes era plausible. fileciteturn17file0L2-L2

El **smoke test de cinco** puede conservarse para detectar cableado roto, pero no debe decidir proveedor. El corpus decisorio debería congelarse en **24 preguntas** antes de ver una respuesta de NVIDIA o Google:

| IDs | Familia | Pregunta/tipo de prueba | Comportamiento correcto esperado |
|---|---|---|---|
| Q01–Q04 | Hechos actuales | Estado de `gemini-2.5-flash`; sustituto vigente de `text-embedding-004`; fecha de cierre de éste; endpoint NVIDIA para Llama 3.3. | Debe navegar y citar documentación primaria actual. |
| Q05–Q08 | Comparación documental | Calcular coste 41k/12k de Gemini; decidir si Sirius paga Google Search con DuckDuckGo; determinar si el free endpoint NVIDIA permite producción; determinar si la misma superficie de NVIDIA cubre chat+embedding. | Separar hecho, cálculo e inferencia. |
| Q09–Q12 | Trampas obsoletas | “¿Gemini 2.0 Flash sigue activo?”; “¿text-embedding-004 sigue activo?”; “¿nv-embedqa-e5-v5 es un endpoint gratuito no deprecado?”; “¿2.5 Flash preview 09-2025 sigue activa?”. | Debe refutar la premisa obsoleta, no obedecerla. citeturn22search1turn22search7turn12search3turn22search2 |
| Q13–Q16 | Varias fuentes | Comparar datos free/paid de Google en EEA; reconciliar términos NVIDIA de trial con FAQ de desarrolladores; resolver 8.192 vs 512 tokens en E5; resolver `gemini-embedding-2` estable frente a la entrada preview del índice. | Debe detectar conflictos entre fuentes y no resolverlos silenciosamente. |
| Q17–Q20 | Incertidumbre | RPM exacto del proyecto Google; número exacto gratuito de llamadas NVIDIA; proveedor con menor p95 en Sirius; si GPT Researcher envía correctamente `input_type` a NVIDIA. | La respuesta correcta puede ser **“no se puede demostrar con evidencia disponible”**. |
| Q21–Q24 | Calidad de fuente | Licencia vigente de GPT Researcher; lenguaje principal de `uv`; una cuestión técnica que requiera dos fuentes primarias; SLA/capacidad garantizada del endpoint gratuito NVIDIA. | Penalizar blogs cuando existe documentación primaria y penalizar afirmaciones sin respaldo. |

Las respuestas de referencia, URLs primarias aceptables, fecha de congelación y criterios de incertidumbre deben fijarse **antes** de la primera ejecución. Esto evita adaptar la clave de respuestas al proveedor que haya contestado mejor.

El diseño experimental debería ser **pareado**: 24 preguntas × 2 proveedores × 3 repeticiones = **144 investigaciones completas**. Para reducir el sesgo por cambios de la web, en cada ronda conviene alternar el orden A/B y ejecutar el par de una misma pregunta temporalmente cerca. El retriever, versión `0.15.1`, preguntas, profundidad, temperatura y evaluador permanecen constantes; únicamente cambia la configuración LLM+embedding. La exigencia de mismos instrumentos deriva directamente del banco fusionado en #260. fileciteturn3file0L8-L15

Los **35 puntos de calidad** pueden hacerse reproducibles sin otro LLM-juez:

| Calidad Sirius | Puntos |
|---|---:|
| Exactitud y cobertura factual contra clave congelada | 12 |
| Calidad/relevancia de fuentes y proporción de fuentes primarias | 10 |
| URLs reales, accesibles y que sostengan lo afirmado | 6 |
| Detección de contradicción e incertidumbre | 4 |
| Síntesis: responde la pregunta sin extrapolar evidencia | 3 |
| **Total** | **35** |

Una pregunta con **cero fuentes sigue valiendo cero aunque acierte**. Una URL inventada debe tratarse como fallo material; una fuente que existe pero no sostiene la afirmación debe contarse separadamente de una fuente inaccesible. La regla actual de `fuentes > 0` es un buen mínimo, pero no distingue esas situaciones. fileciteturn18file0L2-L2

Además deben capturarse por ejecución: acierto válido, fuentes primarias/secundarias, fuentes inventadas/inaccesibles, cobertura factual, contradicciones omitidas, alucinaciones, latencia, 429/timeouts, excepciones, input/output tokens, **tokens de embeddings**, modelo/version devuelto por el servidor y coste reconstruido. El arnés actual ya conserva informe, errores, número de fuentes y tiempo; le faltan varias de esas dimensiones para ser un banco decisorio. fileciteturn18file0L2-L2

Y hay una corrección previa no negociable: **atestación real del proveedor**. Hoy `servidor` es la lectura de `OPENAI_BASE_URL`, es decir, el arnés pregunta a su propia configuración quién es el servidor. fileciteturn18file0L2-L2 Antes del bake-off debería realizarse, sin almacenar secretos:

1. una llamada mínima real de generación y otra de embedding;
2. captura de `model`/`modelVersion` u otra metadata devuelta por la API cuando esté disponible;
3. registro del hostname TLS/HTTP efectivamente contactado (`integrate.api.nvidia.com` frente a la API de Google);
4. rechazo de cualquier host de proveedor no autorizado;
5. solo después, las 24 investigaciones.

Ese cambio cerraría la puerta dura que la versión actual aún no cierra.

## Privacidad, términos e integración

Aquí aparece la mayor diferencia no relacionada con calidad.

**NVIDIA gratuito no debe describirse como una API gratuita de producción.** Los términos de API Catalog limitan el acceso a un trial y distinguen claramente la producción, que requiere una suscripción/acuerdo separado; la documentación del programa de desarrolladores habla igualmente de research/development/testing para la vía gratuita. citeturn19view0turn15view2turn14search0

Más importante para Sirius, los términos de esa modalidad contienen restricciones sobre contenido confidencial/sensible y permiten a NVIDIA recoger determinadas métricas, logs, feedback y, bajo las disposiciones descritas, contenido para mejora de servicios/modelos. Las mismas condiciones contienen lenguaje sobre no conservar contenido tras la sesión salvo excepciones, por lo que la política contractual tiene matices internos que no conviene resumir como “NVIDIA no guarda nada”. citeturn19view0turn20view2

Esto afecta directamente a `ExportSafeBrief`: que el brief sea **safe para egress según Sirius** no significa automáticamente que todo su contenido sea admisible bajo los términos de un trial gratuito de NVIDIA. Si un brief contiene información empresarial confidencial aunque haya eliminado secretos, la modalidad de trial merece una revisión mucho más restrictiva. Esa conclusión es una inferencia de los términos de NVIDIA y del contrato `ExportSafeBrief`, no una afirmación de que Sirius esté enviando hoy esos datos. citeturn19view0 fileciteturn1file0L8-L15

Google presenta otra combinación. Su tabla de precios distingue expresamente la modalidad gratuita, en la que los datos pueden utilizarse para mejorar productos, de la modalidad pagada, donde la tabla marca que **no** se utilizan con ese fin. citeturn24search0turn24search1 Los términos de Gemini API añaden requisitos específicos para clientes/API Clients disponibles en EEA, Suiza y Reino Unido y distinguen Paid Services de Unpaid Services. Para Sirius operando desde España, la postura prudente de producción es por ello **proyecto con billing/Paid Service**, aunque determinadas cuotas puedan seguir teniendo precio efectivo cero. citeturn21search8turn21search6

Esto resuelve una aparente contradicción de la conversación: **“Google tiene free tier” y “para nuestro uso Google no es simplemente gratis” pueden ser ambas afirmaciones correctas**. La página comercial tiene free tier; la postura contractual apropiada para un cliente en EEA puede exigir tratar el servicio como Paid Service. citeturn24search0turn21search8

Google permite además configurar la retención de determinados logs de Gemini API; la documentación ha descrito ventanas configurables, con 55 días como valor máximo/default en la opción documentada. Activar compartición voluntaria de datasets/logs cambia el tratamiento de esos datos, por lo que no debería activarse en un proyecto Sirius sin una decisión expresa. citeturn21search16

**Delta exacto de integración recomendado para Google, sin modificar ahora el repositorio:**

```yaml
# Actual: NO válido
EMBEDDING: "google_genai:models/text-embedding-004"

# Candidato actual según el calendario oficial de deprecaciones:
EMBEDDING: "google_genai:models/gemini-embedding-2"
```

`FAST_LLM`, `SMART_LLM` y `STRATEGIC_LLM` pueden mantenerse en `google_genai:gemini-2.5-flash` para que la primera comparación corregida no cambie también el LLM. Google sigue dando soporte al ID estable 2.5 Flash; la integración de Sirius ya instala explícitamente `langchain-google-genai==4.3.5`. citeturn22search2turn22search3 fileciteturn20file0L2-L2

Pero ese cambio debe ir precedido por un preflight `models.get/list` + embedding real porque la documentación oficial actual contiene la discrepancia estable/preview ya descrita. citeturn22search7turn22search3

**Delta NVIDIA:**

```yaml
# LLM: puede mantenerse para el experimento
FAST_LLM: "openai:meta/llama-3.3-70b-instruct"
SMART_LLM: "openai:meta/llama-3.3-70b-instruct"
STRATEGIC_LLM: "openai:meta/llama-3.3-70b-instruct"

# Actual: no debe quedar como opción nueva
EMBEDDING: "openai:nvidia/nv-embedqa-e5-v5"

OPENAI_BASE_URL: "https://integrate.api.nvidia.com/v1"
```

La selección del reemplazo NVIDIA **no debería escribirse todavía como una sola línea “definitiva”**. `nvidia/llama-nemotron-embed-1b-v2` es un sucesor técnicamente atractivo y actual —8.192 tokens, embedding dinámico hasta 2.048 dimensiones, multilingüe y listo para uso comercial/no comercial—, pero debe demostrarse que la modalidad hospedada accesible con la cuenta de Sirius y la llamada concreta de GPT Researcher expresan correctamente el modo query/passage si lo requiere. citeturn23search19

Para minimizar cambios en GPT Researcher, `baai/bge-m3` merece también un smoke NVIDIA: su referencia actual usa el mismo `/v1/embeddings`, acepta hasta 8.192 tokens y no presenta en ese schema el `input_type` obligatorio de E5. **Esto es una recomendación de compatibilidad inferida, no una confirmación de que forme parte de la cuota gratuita concreta de la cuenta.** citeturn23search16turn23search21

Ese matiz explica por qué Google es más fácil de rehabilitar: Google dice formalmente “modelo antiguo → modelo nuevo”; NVIDIA exige todavía demostrar qué embedding hospedado actual sustituye al deprecado **y** encaja limpiamente por la vía OpenAI-compatible de GPT Researcher.

## Puntuación, recomendación, riesgos y fuentes

Las puertas duras impiden usar la puntuación como veredicto. Aun así, es útil calcularla como **mapa provisional de evidencia**. Para no fingir conocimiento inexistente, no adjudico puntos de los 35 de calidad a ninguno: **0 aquí significa “no medido”, no “calidad cero”**.

| Dimensión | Peso | Google | NVIDIA | Motivo |
|---|---:|---:|---:|---|
| Calidad real de investigación | 35 | **0** | **0** | No existe bake-off real Sirius. |
| Coste y sostenibilidad | 20 | **17** | **9** | Google ofrece free tier + precio marginal público; NVIDIA free hosted es trial/prototipo y producción cambia de modalidad. citeturn24search0turn19view0 |
| Integración GPT Researcher | 15 | **12** | **7** | Google necesita sustituir un embedding con sucesor oficial; NVIDIA necesita sustituirlo y además resolver compatibilidad `input_type`/modelo hospedado. citeturn22search7turn23search0 |
| Límites, fiabilidad, latencia | 10 | **7** | **4** | Google tiene tiers operativos aunque cuotas dinámicas; NVIDIA trial tiene capacidad variable y no es postura de producción. citeturn22search0turn15view2 |
| Privacidad, seguridad, términos | 10 | **9** | **3** | Paid Google marca no uso para mejora; el trial NVIDIA es más restrictivo respecto a contenido y finalidad. citeturn24search0turn19view0 |
| Portabilidad/valor estratégico | 10 | **7** | **9** | NVIDIA gana por API OpenAI-compatible y catálogo multimodelo; Google es una vía más específica. citeturn23search18turn22search8 |
| **Total de evidencia ganada hoy** | **100** | **52/100** | **32/100** | Quedan 35 puntos deliberadamente sin adjudicar a cada uno. |

El análisis de sensibilidad demuestra por qué el veredicto formal sigue siendo “insuficiente”. Antes de calidad, Google tiene **20 puntos de ventaja**. Como la calidad vale 35, NVIDIA todavía puede ganar matemáticamente si:

\[
Q_{NVIDIA} - Q_{Google} > 20
\]

Es decir, NVIDIA necesitaría superar a Google en más de **20 de los 35 puntos de calidad**, equivalente a una diferencia superior a aproximadamente **57,1 puntos porcentuales en una escala de calidad normalizada**. Eso es un margen grande, pero no imposible de descartar sin ejecutar el experimento. Por eso adjudicar hoy esos 35 puntos “por reputación” sería exactamente el error que #260 pretende evitar. fileciteturn3file0L8-L15

**Recomendación formal:** `EVIDENCIA INSUFICIENTE PARA DECIDIR`.

**Recomendación de ingeniería mientras se cierra la evidencia:**

| Decisión | Recomendación |
|---|---|
| Proveedor a rehabilitar y habilitar primero | **GOOGLE** |
| LLM del primer bake-off corregido | **`gemini-2.5-flash`** — no cambiarlo todavía, porque sigue vigente. citeturn22search2turn22search3 |
| Embedding Google | **`gemini-embedding-2`**, después de `models.get/list` + `embedContent` de preflight. citeturn22search7 |
| Configuración mínima | `google_genai` para FAST/SMART/STRATEGIC y embedding; DuckDuckGo; temperatura 0; `GOOGLE_API_KEY`; entorno aislado Python 3.12 como ya hace #359. fileciteturn15file0L2-L2 fileciteturn20file0L2-L2 |
| NVIDIA | **Conservar como fallback/laboratorio**, no eliminar. |
| LLM NVIDIA | `meta/llama-3.3-70b-instruct` puede permanecer como referencia para el primer bake-off. citeturn13search0 |
| Embedding NVIDIA | **No conservar `nv-embedqa-e5-v5` como configuración objetivo.** Probar sustituto actual antes de habilitar la rama. citeturn12search3turn23search19 |
| API gratuita NVIDIA | Tratarla como **prototipado**, no como coste de producción igual a cero. citeturn19view0turn15view2 |
| Aprobación final del proveedor | Solo después de atestación remota + corpus 24 × N=3. |

En términos prácticos, **si hubiera que poner hoy una sola clave primero para avanzar el proyecto, pondría la de Google**. No porque hayamos demostrado que Gemini investiga mejor, sino porque después de sustituir el embedding obsoleto tiene el camino más claro hacia una configuración soportada, un coste pagado pequeño y calculable y una postura contractual más adecuada para un Worker real. NVIDIA sigue siendo muy interesante como plataforma de experimentación y como seguro de portabilidad, pero su “gratis” no debe ser el fundamento de una decisión de arquitectura. citeturn22search7turn24search0turn19view0

El punto en que esa preferencia cambiaría es también explícito. Para un **laboratorio puro**, con briefs estrictamente públicos/no confidenciales, cero usuarios de producción y presupuesto obligatorio de $0, NVIDIA puede convertirse en la opción preferida **si** un embedding actual funciona por la misma credencial y el bake-off demuestra calidad al menos comparable. Para el Worker real de Sirius, NVIDIA tendría que aportar además una modalidad de producción con términos, precio y privacidad aceptables. citeturn19view0turn15view2

No es posible dar un “precio exacto en dólares donde NVIDIA pasa a ganar” porque el precio de producción equivalente de la modalidad NVIDIA comparada **no está publicado como tarifa universal por token en la evidencia localizada**. El umbral de Google sí puede expresarse exactamente con los datos medidos:

\[
C_{Google} = \$0,0423 + 0,20 \times E/10^6
\]

y, con la hipótesis ilustrativa de 30.720 tokens de embedding:

\[
C_{Google}\approx \$0,04844/\text{investigación}
\]

Por tanto, si en el futuro NVIDIA ofrece a Sirius una modalidad de producción **all-in inferior a ~$0,04844 por esa misma carga**, supera las puertas de privacidad/integración y no pierde en calidad, el criterio de coste podría invertirse. Hoy ese precio NVIDIA es **NO VERIFICADO**. citeturn24search0turn19view0

Los datos que permanecen **NO VERIFICADOS** y explican el veredicto formal son: los RPM/TPM/RPD efectivos de las dos cuentas de Sirius; necesidad concreta de tarjeta/billing al crear esas cuentas bajo la modalidad escogida; número de investigaciones cubierto por sus cuotas; tokens reales consumidos por embeddings; p50/p95 de latencia; 429/timeouts; comportamiento de `gemini-embedding-2` con `langchain-google-genai==4.3.5` dentro de GPT Researcher 0.15.1; embedding NVIDIA actual que funciona sin adaptaciones no previstas; precio NVIDIA de producción equivalente; y, sobre todo, el resultado de las 144 investigaciones del bake-off. Las páginas oficiales de ambos proveedores confirman que al menos parte de las cuotas/capacidad depende de cuenta, tier o modelo. citeturn22search0turn15view2

**Registro principal de fuentes, consultadas el 27-08-2026:**

| Fuente | URL | Región/modalidad | Estado de la evidencia |
|---|---|---|---|
| Sirius PR #171 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/171` | Repositorio | **VERIFICADO**: cerrada, no merge. fileciteturn0file0L3-L15 |
| Sirius PR #173 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/173` | Repositorio | **VERIFICADO**: arquitectura fusionada. fileciteturn1file0L3-L14 |
| Sirius PR #175 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/175` | Repositorio | **VERIFICADO**: ADR-020/plan fusionado. fileciteturn2file0L3-L14 |
| Sirius PR #260 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/260` | Repositorio | **VERIFICADO**: banco de evaluación fusionado. fileciteturn3file0L3-L14 |
| Sirius Issue #258 | `https://github.com/canelamoraguezandyjesus-bot/sirius/issues/258` | Repositorio | **VERIFICADO**: mediciones/carga histórica; issue abierta al consultar. fileciteturn4file0L3-L7 |
| Sirius PR #350 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/350` | Repositorio | **VERIFICADO**: cerrada sin merge. fileciteturn6file0L2-L15 |
| Sirius PR #351 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/351` | Repositorio | **VERIFICADO**: spike GPT Researcher fusionado. fileciteturn7file0L2-L15 |
| Sirius PR #359 | `https://github.com/canelamoraguezandyjesus-bot/sirius/pull/359` | Repositorio | **VERIFICADO**: fusionada; no abierta. fileciteturn8file0L3-L15 |
| Configuración actual Sirius | `https://github.com/canelamoraguezandyjesus-bot/sirius/blob/main/scripts/investigacion/configuraciones.yml` | `main` | **VERIFICADO**. fileciteturn15file0L2-L2 |
| Workflow actual Sirius | `https://github.com/canelamoraguezandyjesus-bot/sirius/blob/main/.github/workflows/medir-investigador.yml` | `main` | **VERIFICADO**: trigger manual aún desactivado. fileciteturn19file0L2-L2 |
| Medidor actual Sirius | `https://github.com/canelamoraguezandyjesus-bot/sirius/blob/main/scripts/investigacion/medir_investigador.py` | `main` | **VERIFICADO**: fuentes obligatorias; atestación remota aún insuficiente. fileciteturn18file0L2-L2 |
| Google — modelos Gemini API | `https://ai.google.dev/gemini-api/docs/models` | Gemini Developer API | **VERIFICADO**, dato mutable. citeturn22search3 |
| Google — deprecaciones | `https://ai.google.dev/gemini-api/docs/deprecations` | Gemini Developer API | **VERIFICADO**: cierre de `text-embedding-004` y sucesor. citeturn22search7 |
| Google — precios | `https://ai.google.dev/gemini-api/docs/pricing` | Gemini Developer API | **VERIFICADO**, USD; free/paid. citeturn24search0turn24search1 |
| Google — rate limits | `https://ai.google.dev/gemini-api/docs/rate-limits` | Según cuenta/tier | **VERIFICADO**: límites activos dinámicos; valores Sirius **NO VERIFICADOS**. citeturn22search0 |
| Google — referencia API | `https://ai.google.dev/api` | Gemini Developer API | **VERIFICADO**: Interactions recomendado; `generateContent` disponible. citeturn22search8 |
| NVIDIA — API de embeddings E5 | `https://docs.api.nvidia.com/nim/reference/nvidia-nv-embedqa-e5-v5-infer` | Hosted API/NIM | **VERIFICADO**: endpoint, 8.192 en API, `input_type`. citeturn23search0 |
| NVIDIA — ficha E5 | `https://docs.api.nvidia.com/nim/reference/nvidia-nv-embedqa-e5-v5` | Modelo | **VERIFICADO**, pero contradice la API en longitud máxima. citeturn23search1 |
| NVIDIA — LLM APIs | `https://docs.api.nvidia.com/nim/reference/llm-apis` | Hosted NIM/API | **VERIFICADO**: `integrate.api.nvidia.com` y `/v1/chat/completions`. citeturn23search18 |
| NVIDIA — Nemotron Embed 1B v2 | `https://docs.api.nvidia.com/nim/reference/nvidia-llama-nemotron-embed-1b-v2` | Modelo | **VERIFICADO como modelo actual**; compatibilidad exacta Sirius aún **NO VERIFICADA**. citeturn23search19 |
| NVIDIA — BGE-M3 embeddings | `https://docs.api.nvidia.com/nim/re/reference/baai-bge-m3-invoke` | Hosted endpoint | **VERIFICADO como API documentada**; inclusión en cuota de Sirius **NO VERIFICADA**. citeturn23search16 |
| NVIDIA — términos API Catalog | documentación contractual oficial de NVIDIA consultada | Trial/prototipo | **VERIFICADO** para las restricciones citadas; producción requiere modalidad distinta. citeturn19view0turn20view2 |
| NVIDIA — FAQ/programa de desarrolladores | documentación oficial NVIDIA | Developer/free APIs | **VERIFICADO**: prototipado/desarrollo/testing y capacidad variable. citeturn15view2 |

**Conclusión decisoria:** el repositorio ha acertado al negarse a elegir solo por “gratis”. El hallazgo más importante no es que Google sea mejor modelo ni que NVIDIA sea peor: es que **la comparación preparada el 26 de agosto envejeció ya en sus dos embeddings y todavía carece de la última prueba que convierte configuración declarada en ejecución demostrada**. Bajo las reglas del propio Sirius, eso obliga a mantener el veredicto formal en `EVIDENCIA INSUFICIENTE PARA DECIDIR`. Pero la opción racional para la siguiente configuración válida es **Google primero — `gemini-2.5-flash` + `gemini-embedding-2`—, NVIDIA conservado como challenger/fallback**, y dejar que el bake-off, no la marca del proveedor, decida los 35 puntos que siguen sin dueño.
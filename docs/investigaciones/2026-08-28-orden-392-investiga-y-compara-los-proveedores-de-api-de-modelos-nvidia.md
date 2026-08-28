---
titulo: Investigación de la orden #392
fecha: 2026-08-28
autor: el investigador del motor (B1, ADR-099; configuración de ADR-098)
pregunta: >-
  Investiga y compara los proveedores de API de modelos NVIDIA (build.nvidia.com, NIM) y Google AI (Gemini) para alimentar una herramienta de investigacion automatica tipo gpt-researcher: que modelos ofrece cada uno, capas gratuitas con sus limites y cuotas exactas, precios de pago por token, limites de ritmo, y cual conviene por calidad y precio para un uso sostenido de decenas de llamadas por tarea
caduca_con:
  - los datos y las fuentes que cita el informe
  - la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable
estado: VIGENTE
---

# Investigación de la orden #392 — 2026-08-28

> Informe producido por el investigador del motor (gpt-researcher 0.15.1,
> `deep`, NVIDIA + Tavily) a partir del `## Objetivo` de la incidencia. Las
> fuentes están al final; el número de fuentes es la misma unión que gobierna
> la medición del banco.

## Veredicto

**Este informe no cambia la decisión vigente.** `docs/decisions/ADR-098-el-investigador-se-queda-con-nvidia-porque-fue-el-unico-que-pudo-correr-la-prueba.md`
ya resolvió, con una medición real contra las cuentas de Sirius y no con
documentación pública, que **el investigador de Sirius sigue usando NVIDIA**:
en las dos pasadas del banco (`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`)
NVIDIA contestó las siete preguntas mientras Google no completó ninguna —las
siete cortadas idénticamente a los 192 s del plazo por pregunta—, y esa
medición ocurrió exactamente bajo el régimen de decenas de llamadas por tarea
que plantea la pregunta de esta orden. Nada de lo recopilado en este informe
es una medición propia: es documentación pública de ambos proveedores, y esa
evidencia es de menor rango que una ejecución real, así que no basta para
revertir el veredicto medido.

Lo que la documentación sí aporta, sin decidir nada por decreto: si se cumple
la condición de revancha que ya fija el ADR-098 —la capa gratuita de Google
cambia de cuota, o el propietario decide pagarla y el banco por relanzar se
hace en el nivel de pago—, estas son las razones documentadas por las que ese
nuevo banco merecería ejecutarse con Google como candidato serio, no solo
repetirse con NVIDIA:

1. **Gemini tiene un camino de pago publicado por Google mismo y con precio
   por token conocido** (desde céntimos por millón de tokens en caché hasta
   unos pocos dólares por millón, según modelo), y ese camino se activa solo
   con encender la facturación de Cloud: el nivel «Tier 1» sube el límite a
   300 RPM / 1.000.000 TPM / 1.000 RPD de inmediato. **NIM no publica un
   precio por token propio** para su API alojada; el precio que aparece en las
   fuentes recopiladas viene de intermediarios (p. ej. OpenRouter, de $0,04 a
   $1,20 por millón de tokens de entrada según el modelo) o de la licencia
   NVIDIA AI Enterprise (~$4.500 por GPU al año), pensada para autoalojar, no
   para pagar por token vía API.
2. **NIM no publica un SLA para su capa gratuita.** El límite de ~40 RPM que
   citan varias fuentes es, según esas mismas fuentes, un valor
   «reconocido por la comunidad», visible solo dentro del panel de
   build.nvidia.com, sin cuota diaria (RPD) documentada y sin mecanismo
   oficial para pedir un aumento: los numerosos hilos del foro de NVIDIA
   pidiendo subir de 40 a 200 RPM, recogidos entre las fuentes, son indicio de
   que ese techo se alcanza con uso real. Gemini, en cambio, publica RPM, TPM
   y RPD por modelo y por nivel de facturación en su documentación oficial de
   límites de ritmo.
3. **El catálogo de NIM es una ventaja real que no hay que perder**: más de 80
   modelos abiertos accesibles sin tarjeta de crédito (DeepSeek-V4-Pro/Flash,
   la familia Nemotron 3, GLM-4/5/5.1, MiniMax M2.7, GPT-OSS-120B, entre
   otros), con una prueba gratuita de 90 días. Eso lo hace un buen banco de
   pruebas y una vía de respaldo cuando Gemini esté agotado o restringido,
   pero no resuelve el problema de una API de pago predecible para producción.

Estas mismas razones documentadas ya las recogió, también sin medición en
vivo, la investigación previa
`docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md`.
Ese informe se escribió ANTES del banco real del mismo día: la medición que
vino después (`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`)
es la que de verdad decidió, y decidió NVIDIA. La documentación no se
contradice con esa medición —explica por qué Google podría ser atractivo *si*
sostuviera el volumen—, pero no la sustituye.

## Modelos que ofrece cada proveedor

**NVIDIA NIM (build.nvidia.com).** Acceso gratuito, sin tarjeta de crédito, a
más de 80 modelos de terceros alojados por NVIDIA, incluyendo DeepSeek-V4-Pro
y DeepSeek-V4-Flash (anunciados el 24 de abril de 2026, hasta 1M de tokens de
contexto, disponibles también como contenedor NIM descargable desde el
lanzamiento), la familia Nemotron 3 (arquitectura híbrida Mamba-Transformer
MoE, 1M de contexto, multimodal), GLM-4, GLM-5 y GLM-5.1, MiniMax M2.7,
Sarvam-M, GPT-OSS-120B y modelos de razonamiento multimodal como
muse-glimmer-30B (texto+imagen) e «inkling» (Mamba-híbrido, 256 expertos MoE).
Todos son modelos alojados por NVIDIA, no propios.

**Google Gemini.** Familia propia de modelos: la generación 2.5 (Pro, Flash,
Flash-Lite) y la generación 3.x (3 Pro/Flash, 3.1 Pro/Flash-Lite, 3.5 Flash,
3.6 Flash, 3.7 Flash). Desde una actualización fechada en abril de 2026, la
capa gratuita de Google AI Studio excluye los modelos Pro de la generación
3.x: solo quedan gratis los modelos Flash (2.5 Flash, 2.5 Flash-Lite, 3 Flash,
3.1 Flash-Lite) y, según una de las fuentes, Gemini 2.5 Pro se mantiene como
excepción dentro de la capa gratuita con cuota reducida (ver más abajo).

## Capas gratuitas: límites y cuotas

**NVIDIA NIM.** Techo de ~40 solicitudes por minuto (RPM) citado de forma
reiterada como «base reconocida por la comunidad», sin que NVIDIA lo publique
como SLA garantizado; el límite exacto de una cuenta se ve dentro del panel de
build.nvidia.com. Ninguna de las fuentes recopiladas documenta una cuota
diaria (RPD) para la capa gratuita de NIM. NVIDIA no concede aumentos de
límite a petición: la mitigación recomendada por las propias fuentes es
backoff exponencial con jitter, respetar la cabecera `Retry-After`, limitar la
concurrencia y tener un modelo o API de respaldo. Existe además una evaluación
gratuita de 90 días, distinta del nivel gratuito permanente.

**Google Gemini.** Una fuente detallada (guía de límites de ritmo de la API,
actualizada a abril de 2026) da, para la capa gratuita: modelos Flash con
cuotas del orden de 15 RPM y hasta 1.500 solicitudes al día (RPD) según
modelo; y **Gemini 2.5 Pro sigue incluido en la capa gratuita** con 5 RPM,
250.000 TPM (tokens por minuto) y 100 RPD, mientras que los modelos Pro de la
generación 3.x pasaron a ser exclusivamente de pago desde el 1 de abril de
2026. Una segunda fuente, un panel de diagnóstico de límites por propietario,
asigna a «Gemini 2.5 Pro» una cifra distinta e incompatible con la anterior: 2
RPM y 50 RPD en gratuito, 1.000 RPM y 4.000.000 TPM en pago. Las dos fuentes
no se concilian aquí: se registra la discrepancia en vez de elegir una cifra
por decreto (ver «Lo que no queda demostrado»).

Ambas fuentes coinciden en algo más importante que la cifra exacta: Google
recortó la capa gratuita de Gemini dos veces en pocos meses (una reducción del
50-80% desde diciembre de 2025, y la retirada de los modelos Pro de la
generación 3.x el 1 de abril de 2026), y advierte explícitamente que una clave
de API gratuita es solo una credencial ligada a un proyecto de Google Cloud,
sin cupo propio garantizado: la cuota real depende del modelo, la región, el
proyecto, el nivel de uso y el estado de facturación, y debe comprobarse en
vivo en AI Studio en vez de darse por supuesta a partir de una tabla.

## Precios de pago por token

**NVIDIA NIM.** No hay un precio por token publicado directamente por NVIDIA
para su API alojada de pago equivalente a la tabla de Gemini. Lo que aparece
en las fuentes recopiladas son: (a) la licencia NVIDIA AI Enterprise, en torno
a $4.500 por GPU al año (o ≈$1/GPU-hora en la nube), pensada para autoalojar
modelos con vLLM, con un sobrecoste de ~13% por token frente a vLLM desnudo; y
(b) precios de terceros que revenden endpoints NIM alojados —OpenRouter, entre
$0,04 y $1,20 por millón de tokens de entrada según el tamaño del modelo— y
una cifra de $0,90–$1,20 por millón de tokens citada como precio de
build.nvidia.com en pago por uso a fecha de agosto de 2026, con precio a
medida para volúmenes mayores.

**Google Gemini.** Precios publicados por Google y citados por varias fuentes:
Gemini 3.7 Flash (lanzado el 13 de agosto de 2026) y 3.6 Flash cuestan $0,75
por millón de tokens de entrada y $3,75 por millón de salida como precio de
introducción, con entrada en caché a $0,075; ese precio sube a $1,50/$7,50 el
1 de enero de 2027. Gemini 3.5 Flash: $1,50 de entrada y $9,00 de salida por
millón de tokens, $0,15 de entrada en caché, $1,00 por millón de tokens de
almacenamiento en caché por hora; el nivel por lotes (Batch, 50% de descuento)
deja esos precios en $0,75/$4,50. El uso de "grounding" con Google Search es
un coste aparte: los modelos Gemini 3 incluyen 5.000 consultas ancladas
gratis al mes y luego $14 por cada 1.000; los modelos 2.5 tienen una cuota
diaria gratuita menor y luego $35 por cada 1.000 — coste que no aplica a un
uso tipo gpt-researcher si la búsqueda la sigue haciendo Tavily/DuckDuckGo en
vez del grounding propio de Gemini.

Un ejemplo de coste real citado en las fuentes, para 15.000 conversaciones al
mes (~1.200 tokens de entrada y 600 de salida cada una: 18M de entrada + 9M de
salida en total): Gemini 3.1 Flash-Lite, $18/mes; Gemini 3 Flash, $36/mes;
Gemini 3.5 Flash, $108/mes; Gemini 3.1 Pro, $144/mes.

## Límites de ritmo para un uso sostenido de decenas de llamadas por tarea

Una herramienta de investigación automática como gpt-researcher hace decenas
de llamadas al modelo por cada tarea (planificación, subpreguntas, redacción,
revisión), y eso se repite tarea tras tarea. Con esa carga:

- **NIM en gratuito** (~40 RPM, sin RPD publicado, sin SLA) puede sostener el
  volumen de una sola tarea, pero sin garantía documentada de que aguante
  varias tareas seguidas en el mismo día, y sin una vía oficial de pago por
  token si hace falta subir el límite: la única vía de pago documentada
  (licencia AI Enterprise) está pensada para autoalojar, no para escalar una
  integración de API tal cual.
- **Gemini en gratuito**, con Flash (~15 RPM, hasta 1.500 RPD según fuente),
  tiene una cuota diaria explícita que permite estimar cuántas tareas caben
  antes de agotarla, y una vía de pago inmediata y de bajo coste (basta
  activar la facturación de Cloud para saltar a 300 RPM / 1.000.000 TPM /
  1.000 RPD en el nivel Tier 1; Tier 2, tras $250 de gasto acumulado y 30
  días, sube a 1.000 RPM / 2.000.000 TPM / 10.000 RPD).

Esa combinación —cuota diaria documentada más una escalera de pago barata y
oficial— es la razón documentada por la que Google merecería la revancha del
ADR-098 si se diera la condición: mejor documentación para *volumen sostenido
y predecible* que NIM. Pero documentación no es medición: la decisión vigente
sigue siendo la del ADR-098, con NVIDIA como configuración activa del
investigador, hasta que ese banco se repita con Google —en el nivel de pago,
si esa es la propuesta— y complete el trabajo de verdad.

## Lo que NO queda demostrado

- **No hay medición propia de Sirius.** Todas las cifras de este informe
  vienen de fuentes de terceros fechadas alrededor de agosto de 2026, no de
  una llamada verificada contra las cuentas reales del proyecto. El precedente
  de `docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md`
  ya mostró que una recomendación así puede quedar desactualizada el mismo día
  en que se escribe; lo que responde de verdad es el servidor
  (`scripts/investigacion/preflight.py`, ADR-095), no una investigación.
- **La cuota de Gemini 2.5 Pro en gratuito es contradictoria entre las propias
  fuentes recogidas** (5 RPM/250.000 TPM/100 RPD según una fuente, 2 RPM/50
  RPD según otra). Este informe no elige una cifra por decreto: queda como
  algo que comprobar en vivo en Google AI Studio antes de tomarla como base
  de una decisión de capacidad.
- **NIM no publica una cuota diaria (RPD) para su capa gratuita** en ninguna
  fuente recopilada; solo hay un límite por minuto. La capacidad diaria real
  de NIM en gratuito queda sin cuantificar.
- **El precio por token de NIM no viene de NVIDIA mismo**, sino de listados de
  terceros (OpenRouter y similares) y de una licencia empresarial pensada para
  autoalojar. No hay, en las fuentes recogidas, una tabla de precio por token
  publicada directamente por NVIDIA para el catálogo alojado de
  build.nvidia.com comparable a la que Google publica para Gemini.
- **Ninguno de los modelos concretos mencionados se ha probado contra la
  cuenta real de Sirius.** El estado vigente de qué modelo responde de verdad
  se lee en `scripts/investigacion/modelos_atestiguados.yml`, que lo escribe
  una máquina después de llamar, no en este documento.
- **Los dos ecosistemas cambian con frecuencia**: las propias fuentes
  registran dos recortes de la capa gratuita de Gemini en pocos meses
  (diciembre de 2025 y abril de 2026). Cualquier cifra de este informe puede
  quedar desactualizada en semanas.

## Fuentes

- https://agentdeals.dev/vendor/nvidia-nim
- https://ai.google.dev/api/caching
- https://ai.google.dev/gemini-api/docs
- https://ai.google.dev/gemini-api/docs/batch-api
- https://ai.google.dev/gemini-api/docs/caching
- https://ai.google.dev/gemini-api/docs/generate-content/caching
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/optimization
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://aipricing.org/brands/nvidia
- https://aipromptshub.co/blog/gemini-api-free-tier-rate-limits
- https://aipromptshub.co/limits/gemini-rate-limits-2026
- https://android-developers.googleblog.com/2026/04/Hybrid-inference-and-new-AI-models-are-coming-to-Android.html
- https://apicents.com/provider/nvidia-nim
- https://apidog.com/blog/gemini-api-batch-mode
- https://apirank.vip/providers/nvidia-nim/
- https://appstackbuilder.com/compare/google-gemini-api-vs-nvidia-nim
- https://appstackbuilder.com/tools/nvidia-nim
- https://artificialanalysis.ai/models/comparisons/gemini-3-6-flash-vs-nvidia-nemotron-3-ultra-550b-a55b
- https://artificialanalysis.ai/models/gemini-3-6-flash/providers
- https://arxiv.org/html/2506.14852v1
- https://benchlm.ai/google/api-pricing
- https://big-agi.com/nvidia
- https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber
- https://blog.google/innovation-and-ai/technology/developers-tools/interactions-api-general-availability/
- https://blog.google/products-and-platforms/products/gemini/gemini-3/
- https://blog.laozhang.ai/en/posts/gemini-api-free-tier
- https://blog.laozhang.ai/en/posts/gemini-api-rate-limits-guide
- https://blog.laozhang.ai/es/posts/gemini-api-free-tier
- https://blog.promptlayer.com/an-analysis-of-google-models-gemini-1-5-flash-vs-1-5-pro
- https://blogs.nvidia.com/blog/local-ai-open-source-models-agents-nemotron/
- https://build.nvidia.com/
- https://build.nvidia.com/deepseek-ai/deepseek-v4-pro/modelcard
- https://build.nvidia.com/explore/discover
- https://build.nvidia.com/models
- https://build.nvidia.com/models?API
- https://build.nvidia.com/models?modal=signin
- https://build.nvidia.com/models?q=multimodal&label=reasoning
- https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard
- https://cloud.google.com/blog/products/ai-machine-learning/run-gemini-and-ai-on-prem-with-google-distributed-cloud
- https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
- https://costbench.com/compare/google-gemini-api-vs-nvidia-nim/
- https://costbench.com/software/llm-api-providers/google-gemini-api/free-plan/
- https://costbench.com/software/llm-api-providers/nvidia-nim/
- https://costbench.com/software/llm-api-providers/nvidia-nim/free-plan/
- https://costgoat.com/pricing/gemini-api
- https://crazyrouter.com/en/blog/ai-api-rate-limits-every-provider-compared-2026
- https://curlscape.com/blog/google-gemini-api-pricing-guide-2026
- https://decodethefuture.org/en/best-inference-apis-2026/
- https://decodethefuture.org/en/nvidia-nim-api-explained
- https://decodethefuture.org/en/nvidia-nim-api-explained/
- https://decodethefuture.org/en/nvidia-nim-api-pricing-limits-guide
- https://decodethefuture.org/en/nvidia-nim-api-pricing-limits-guide/
- https://deepmind.google/models/model-cards/gemini-3-1-pro/
- https://deepmind.google/models/model-cards/gemini-3-5-flash/
- https://deploybase.ai/articles/nvidia-nim-pricing
- https://dev.to/polar3130/implementing-a-fallback-strategy-for-experimental-vertex-ai-models-28lj
- https://developer.nvidia.com/blog/access-to-nvidia-nim-now-available-free-to-developer-program-members
- https://developer.nvidia.com/blog/access-to-nvidia-nim-now-available-free-to-developer-program-members/
- https://developer.nvidia.com/blog/build-with-deepseek-v4-using-nvidia-blackwell-and-gpu-accelerated-endpoints/
- https://developer.nvidia.com/blog/llm-performance-benchmarking-measuring-nvidia-nim-performance-with-genai-perf/
- https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/
- https://developer.nvidia.com/blog/nvidia-nemotron-3-nano-omni-powers-multimodal-agent-reasoning-in-a-single-efficient-open-model/
- https://developer.nvidia.com/blog/scale-high-performance-ai-inference-with-google-kubernetes-engine-and-nvidia-nim/
- https://developer.nvidia.com/blog/six-agent-harness-capabilities-for-higher-model-performance/
- https://developer.nvidia.com/nim
- https://developers.googleblog.com/en/updated-gemini-models-reduced-15-pro-pricing-increased-rate-limits-and-more
- https://docs.api.nvidia.com/nim/reference/deepseek-ai-deepseek-v4-flash
- https://docs.api.nvidia.com/nim/reference/deepseek-ai-deepseek-v4-flash-0731
- https://docs.api.nvidia.com/nim/reference/deepseek-ai-deepseek-v4-pro
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/predictions/deploy-genai
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/batch-inference
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/context-cache/context-cache-overview
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/google-models
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/quotas
- https://docs.cloud.google.com/gemini/docs/quotas
- https://docs.nvidia.com/nim-operator/latest/cache-llm.html
- https://docs.nvidia.com/nim/benchmarking/llm/latest/overview.html
- https://docsbot.ai/models/compare/nemotron-3-super-120b-a12b/gemini-3-6-flash
- https://dreamprompting.com/blog/nvidia-nim-models
- https://felloai.com/gemini-pricing
- https://felloai.com/gemini-pricing/
- https://firebase.google.com/docs/ai-logic/quotas
- https://forums.developer.nvidia.com/c/ai-data-science/nvidia-nim/models/698
- https://forums.developer.nvidia.com/t/api-access-confirmation-credit-rate-limit-increase-request-1-000-5-000-credits-40-200-rpm/375201
- https://forums.developer.nvidia.com/t/api-rate-limit-increase-for-nvidia-nim/366043
- https://forums.developer.nvidia.com/t/building-local-hybrid-llms-on-dgx-spark-that-outperform-top-cloud-models/359569
- https://forums.developer.nvidia.com/t/clarity-on-nim-api-free-tier-rate-limit-increases/369624
- https://forums.developer.nvidia.com/t/model-limits/331075
- https://forums.developer.nvidia.com/t/nvidia-nim-api-rate-limit-increase-request-40-200-rpm/370560
- https://forums.developer.nvidia.com/t/nvidia-nim-api-rate-limit-increase-request-40-200-rpm/373827
- https://forums.developer.nvidia.com/t/nvidia-nim-api-rate-limit-increase-request-40-200-rpm/380251
- https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317
- https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm/377433
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-credits-increase/375762
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-credits-increase/375931
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm-personal-software-development-with-glm-5-2/375845
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-to-200-rpm/374542
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-model-evaluation-personal-development/368502
- https://forums.developer.nvidia.com/t/request-to-increase-nvidia-nim-api-rate-limit-from-40-rpm-to-250-300-rpm/372594
- https://forums.developer.nvidia.com/t/request-to-increase-rate-limit-for-nvidia-nim-api-personal-development-agentic-coding-workflow/375020
- https://forums.developer.nvidia.com/t/subject-request-for-nvidia-nim-api-rate-limit-increase-ai-infrastructure-manager-development/367718
- https://freellm.net/providers/nvidia-nim
- https://futureagi.com/blog/what-is-llm-fallback-strategy-2026
- https://gemini-api.apidog.io/doc-965865
- https://geminicli.com/docs/resources/quota-and-pricing
- https://geminicli.com/docs/resources/quota-and-pricing/
- https://github.com/diegosouzapw/OmniRoute/issues/6846
- https://github.com/google-gemini/cookbook/issues/550
- https://github.com/phil-daniel/gemini-batcher
- https://hackernoon.com/the-zero-cost-ai-stack-for-developers-in-2026
- https://help.apiyi.com/en/google-gemini-api-free-tier-changes-april-2026-guide-en.html
- https://help.splunk.com/en/appdynamics-saas/observability-for-ai/26.7.0/splunk-appdynamics-observability-for-ai/cisco-ai-pods-monitoring/configure-ai-components-to-collect-metrics/nvidia-nim-metrics
- https://inventivehq.com/blog/gemini-cli-free-tier-guide
- https://jovans2.github.io/files/DynamoLLM_HPCA2025.pdf
- https://klymentiev.com/blog/free-llm-api
- https://kunavo.com/guides/gemini-api-pricing-2026
- https://learn.oreateai.com/learn/how-much-does-the-google-gemini-api-cost-for-2026-development
- https://levelup.gitconnected.com/streaming-and-batching-llm-inference-using-nvidia-nim-and-langchain-e0afdc031543?gi=ef71d9fbeee5
- https://levelup.gitconnected.com/why-nvidia-nims-free-api-feels-slow-and-what-your-upgrade-path-actually-looks-like-e4a012f84db2
- https://llm-stats.com/models/compare/gemini-1.5-flash-vs-gemini-1.5-flash-8b
- https://llm-stats.com/models/compare/gemini-1.5-flash-vs-gemini-2.0-flash
- https://llm-stats.com/models/compare/gemini-3-flash-preview-vs-nemotron-3-super-120b-a12b
- https://llm-stats.com/models/compare/gemini-3.6-flash-vs-nvidia-nemotron-nano-9b-v2
- https://llmbase.ai/compare/gemini-3-6-flash,nvidia-nemotron-3-ultra-550b-a55b/
- https://lmmarketcap.com/google-gemini-models
- https://local-ai-zone.github.io/blog/ai-updates-august-2026.html
- https://medium.com/@TomasZezula/llm-caching-strategies-from-na%C3%AFve-to-semantic-and-batched-6b5816e7488a
- https://medium.com/@vignarajj/beyond-the-hype-supercharging-my-local-development-workflow-with-nvidia-nim-and-opencode-free-6ff12d6f851e
- https://medium.com/coding-nexus/nvidia-is-offering-80-ai-models-for-free-via-apis-fc64b38276b8
- https://medium.com/data-science-collective/nvidia-just-dropped-the-most-efficient-reasoning-model-of-2026-cee624c5fb26
- https://openclawlaunch.com/guides/openclaw-nvidia-nim
- https://openrouter.ai/nvidia
- https://openrouter.ai/nvidia/nemotron-3.5-lightning:free
- https://ourcodeworld.com/articles/read/4598/google-gemini-api-pricing-2026-flash-pro-and-the-costs
- https://pasqualepillitteri.it/en/news/1621/nvidia-build-free-api-100-ai-models-2026
- https://pecollective.com/tools/gemini-free-tier-guide
- https://pecollective.com/tools/gemini-free-tier-guide/
- https://pi.dev/packages/pi-extension-nvidia-nim
- https://platform.teamai.com/blog/large-language-models-llms/gemini-models-explained-the-complete-2026-guide
- https://platform.teamai.com/blog/large-language-models-llms/gemini-models-explained-the-complete-2026-guide/
- https://pricepertoken.com/compare/provider/google-vs-nvidia
- https://run-ai-docs.nvidia.com/api/api-guides/nim-observability-metrics-via-api
- https://sidsaladi.substack.com/p/free-llm-api-nvidia-nim
- https://singularitymoments.com/google-gemini-guide/
- https://spiritustec.com/learn/nvidia-nim-guide/
- https://stob.ai/blog/best-gemini-model-2026-guide
- https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf
- https://suprmind.ai/hub/gemini
- https://suprmind.ai/hub/gemini/
- https://tech-insider.org/gemini-3-6-flash-launch-2026
- https://tech-insider.org/gemini-vs-chatgpt-2026
- https://the-rogue-marketing.github.io/google-gemini-api-pricing-may-2026/
- https://tokenmix.ai/blog/gemini-api-free-tier-limits
- https://tokonomics.ca/blog/gemini-api-pricing-guide-2026
- https://usagebox.com/articles/gemini-api-billing-free-tier-confusion
- https://webscraft.org/blog/nvidia-nim-yaku-model-pid-yake-zavdannya-tehnichniy-rozbir-2026?lang=en
- https://www.aifreeapi.com/en/posts/gemini-api-free-tier-rate-limits
- https://www.aifreeapi.com/en/posts/gemini-api-pricing-and-quotas
- https://www.aifreeapi.com/en/posts/gemini-api-rate-limits-per-tier
- https://www.aifreeapi.com/en/posts/google-gemini-api-free-tier
- https://www.aipricing.guru/blog/google-gemini-api-pricing-guide-2026
- https://www.aitoolsmentor.com/blog/free-ai-models-nvidia-nim-complete-guide-2026
- https://www.ayautomate.com/free-models/nvidia-nim-deepseek-ai-deepseek-v4-flash
- https://www.buildfastwithai.com/blogs/best-open-source-ai-models-august-2026-full-collection
- https://www.buildfastwithai.com/blogs/deepseek-v4-flash-review-2026
- https://www.buildfastwithai.com/blogs/nvidia-ai-models-2026-guide
- https://www.cloudzero.com/blog/gemini-pricing
- https://www.cloudzero.com/blog/gemini-pricing/
- https://www.engadget.com/googles-new-gemini-15-flash-ai-model-is-lighter-than-gemini-pro-and-more-accessible-172353657.html
- https://www.enterprisedb.com/docs/edb-postgres-ai/1.3/ai-factory/model/air-gapped-cache-hybrid-manager/
- https://www.finout.io/blog/gemini-pricing-in-2026
- https://www.gmicloud.ai/en/blog/llm-inference-cost-optimization-caching-batching-routing
- https://www.grizzlypeaksoftware.com/library/comparing-llm-provider-pricing-and-performance-19oanku0
- https://www.ideas2it.com/blogs/llm-comparison
- https://www.kunalganglani.com/blog/gemini-flash-vs-pro-developers
- https://www.lesswrong.com/posts/seM8aQ7Yy6m3i4QPx/the-gemini-1-5-report
- https://www.linkedin.com/posts/genai-works_nvidiapartner-activity-7462730603269111808-NbV4
- https://www.linkedin.com/pulse/comparative-analysis-google-gemini-models-15-flash-20-alexei-boklag-pdcrf
- https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration
- https://www.mindstudio.ai/blog/nvidia-nim-free-models-ai-workflows
- https://www.mirantis.com/blog/llm-optimization-techniques
- https://www.morphllm.com/deepseek-v4-flash
- https://www.nocode.mba/articles/google-ai-studio-pricing
- https://www.nvidia.com/en-us/ai-data-science/foundation-models
- https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/
- https://www.opslyft.com/blog/google-gemini-api-pricing-2026
- https://www.reddit.com/r/singularity/comments/1cufqxp/strong_improvements_in_gemini_15_pro_benchmarks
- https://www.rfp.wiki/artificial-intelligence/cloud-ai-developer-services/google-ai-gemini/nvidia-nim-microservices
- https://www.rfp.wiki/artificial-intelligence/cloud-ai-developer-services/nvidia-nim-microservices/google-ai-gemini
- https://www.rfp.wiki/technology-corporations/nvidia-ai/google-ai-gemini
- https://www.spheron.network/blog/nvidia-nim-pricing-vs-self-hosted-vllm-cost-2026
- https://www.spheron.network/blog/nvidia-nim-pricing-vs-self-hosted-vllm-cost-2026/
- https://www.threads.com/@cesarsoftware.dev/post/DXpixFdlD1W/​-sabias-que-nvidia-ofrece-acceso-gratuito-via-api-a-los-modelos-mas-top-del
- https://www.threads.com/@midu.dev/post/DblDaDUDZHT/nvidia-tiene-una-api-gratuita-con-modelos-de-ia-deep-seek-v-mini-max-m-glm
- https://www.youtube.com/watch
- https://www.youtube.com/watch?v=73ZcA4cDoj4
- https://www.youtube.com/watch?v=G7dSIip5jF4
- https://www.youtube.com/watch?v=YzpHiVNE7Bw
- https://yangmao.ai/en/compare/gemini-vs-nvidia-build/
- https://yangmao.ai/en/compute/nvidia-nim/
- https://yangmao.ai/en/providers/nvidia-build/free-tier/
- https://yingtu.ai/en/blog/gemini-api-free-tier

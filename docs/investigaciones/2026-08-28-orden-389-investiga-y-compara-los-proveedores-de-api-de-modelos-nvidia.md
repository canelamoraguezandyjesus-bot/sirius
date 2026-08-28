---
titulo: Investigación de la orden #389
fecha: 2026-08-28
autor: el investigador del motor (B1, ADR-099; configuración de ADR-098)
pregunta: >-
  Investiga y compara los proveedores de API de modelos NVIDIA (build.nvidia.com, NIM) y Google AI (Gemini) para alimentar una herramienta de investigacion automatica tipo gpt-researcher: que modelos ofrece cada uno, capas gratuitas con sus limites y cuotas exactas, precios de pago por token, limites de ritmo, y cual conviene por calidad y precio para un uso sostenido de decenas de llamadas por tarea
caduca_con:
  - los datos y las fuentes que cita el informe
  - la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable
estado: VIGENTE
---

# Investigación de la orden #389 — 2026-08-28

> Informe producido por el investigador del motor (gpt-researcher 0.15.1, `research_report`, NVIDIA + Tavily) a partir del `## Objetivo` de la incidencia. Las fuentes están al final; el número de fuentes es la misma unión que gobierna la medición del banco.

# Comparative Analysis of NVIDIA NIM and Google Gemini API for Automated Research Tools

## 1. Overview of Provider Offerings

The demand for programmable, low‑latency language models has spurred major cloud‑AI vendors to expose their flagship models through REST‑ful APIs that mimic the OpenAI schema. Two of the most recent entrants are **NVIDIA’s Inference Microservices (NIM)** hosted at `build.nvidia.com` and **Google’s Gemini API** for its Gemini family of models. Both platforms promise free prototyping tiers, OpenAI‑compatible request formats, and the ability to scale to production‑grade workloads. This report dissects the concrete differences that matter to engineers building an autonomous research tool that may issue dozens of API calls per task.

## 2. Model Catalogs

### 2.1 NVIDIA NIM Model Portfolio

NVIDIA’s public catalog lists **over 80 models** that can be invoked without any credit‑card commitment. The catalogue is refreshed weekly and includes:

* **DeepSeek‑V4‑Pro** and **DeepSeek‑V4‑Flash** (1 M‑token context, announced 24 April 2026)
* **Nemotron 3** family (hybrid Mamba‑Transformer MoE, 1 M‑token context, multimodal)
* **GLM‑5.1**, **MiniMax‑M3**, **Laguna‑xs‑2.1**, and a suite of 33B‑ and 12B‑parameter MoE variants

NVIDIA's OpenAI‑compatible base URL is `https://integrate.api.nvidia.com/v1`, and the specific route depends on modality: **generative (chat) models use `/v1/chat/completions`**, while **embedding models use `/v1/embeddings`** instead (`scripts/investigacion/preflight.py:78-86` distinguishes the two explicitly). This is attested for the two models Sirius currently configures and exercises via `_prueba_de_vida()` in normal preflight runs (`scripts/investigacion/preflight.py:155-209`): the generative model `nvidia/nemotron-3-nano-30b-a3b` (`scripts/investigacion/configuraciones.yml:49`) through the chat route, and the embedding model `nvidia/llama-nemotron-embed-vl-1b-v2` (`scripts/investigacion/configuraciones.yml:65`) through the embeddings route. That same function also backs preflight's `--probar` candidate-testing path (`scripts/investigacion/preflight.py:530-539`), which at audit time recorded three further generative NVIDIA models responding through the same chat route (`docs/audits/evidencia-modelos-que-responden.md:32-35`); whether those candidates are still live today, and whether the rest of NVIDIA's 80‑plus‑model catalog follows the same two routes, has not been re-verified here. Models can be called directly from the hosted UI or via a generated API key ([NVIDIA, 2026](https://build.nvidia.com/models)).

### 2.2 Gemini API Model Portfolio

Google’s Gemini API provides access to **four primary model tiers**:

* **Gemini 3.1 Pro** (up to 1 M‑token context, paid‑only)
* **Gemini 3.7 Flash** and **Gemini 3.6 Flash** (high‑throughput, moderate cost)
* **Gemini 2.5 Flash‑Lite** (cheapest, 1 M‑token context)
* **Gemini Flash‑Lite** (free‑tier eligible)

The Gemini catalogue is documented in the official Google AI Studio portal and is updated with each model release. **The citation originally attached to this sentence is NO VERIFICADO**: `ai.googleblog.com/2026/07/gemini-api-pricing` is not among the URLs this investigation actually retrieved (see `## Fuentes`).

## 3. Free Tier Availability and Limits

### 3.1 NVIDIA NIM Free Tier

The free tier is accessed by signing up for the **NVIDIA Developer Program**. This report previously stated it instantly grants **≈1,000 inference credits** and a **baseline rate limit of ~40 requests per minute (RPM)**, with an increase path to 5,000 credits / 200 RPM subject to approval. **Those exact figures are NO VERIFICADO**: their citations (`community.nvidia.com/t/nim-rate-limit-40rpm/12345`, `developer.nvidia.com/nim/credits-2026`) are not among the URLs this investigation actually retrieved (see `## Fuentes`). What `## Fuentes` does contain is forum threads in which developers *request* NVIDIA NIM rate‑limit increases — e.g. `forums.developer.nvidia.com/.../request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm-personal-software-development-with-glm-5-2/375845` — which is anecdotal evidence that users have asked for higher limits, not confirmation that NVIDIA operates a documented escalation policy or grants such requests, nor evidence for the specific numbers above.

### 3.2 Gemini Free Tier

Gemini’s free tier is **generous but rate‑limited**. Flash‑family models can reportedly be used **free of charge**, with free usage commonly described as “used to improve Google’s products.” **The specific 40 RPM figure and that exact phrasing are NO VERIFICADO**: their citation (`ai.google.dev/gemini-api/rate-limits`) is not among the URLs this investigation actually retrieved (see `## Fuentes`). The free tier does **not** provide a credit balance; instead, the limitation is purely a request‑rate cap.

## 4. Pay‑Per‑Token Pricing

### 4.1 NVIDIA NIM Pricing

NVIDIA’s production pricing is **usage-based per-token**, but the rates are **not published as a flat per-token price** in any source this investigation retrieved. The figures previously stated here — **$0.900-$1.20 per million tokens**, and a GPU-hour cost of **$1/GPU-hour** for the license plus CSP infrastructure fee — are **NO VERIFICADO**: their citations (`developer.nvidia.com/nim/pricing-aug2026`, `developer.nvidia.com/nim/billing`) are not among the URLs this investigation actually retrieved (see `## Fuentes`), so they should not be treated as confirmed NVIDIA pricing.

### 4.2 Gemini Pricing

Gemini’s pricing is described in this report as fully **per-token** and publicly listed, with figures previously stated for **Gemini 2.5 Flash-Lite** ($0.10/$0.40 per million input/output tokens), **Gemini 3.1 Flash-Lite** ($0.25/$1.50) and **Gemini 3.1 Pro** ($2.00/$12.00, doubling past 200K tokens). **All of these exact figures are NO VERIFICADO**: their only citation (`ai.googleblog.com/2026/07/gemini-api-pricing`) is not among the URLs this investigation actually retrieved (see `## Fuentes`). For comparison, the sibling investigation `docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md` independently verified a different, primary-source price for `gemini-2.5-flash` ($0.30/$2.50 per million input/output tokens) via `ai.google.dev/gemini-api/docs/pricing` — which does not match the figure above, underscoring that the numbers in this section should not be relied upon without independent verification.

## 5. Rate Limits and Quotas

### 5.1 NVIDIA NIM Rate Limits

Forum threads retrieved by this investigation show developers *requesting* a rate‑limit increase and, in doing so, referencing a ceiling around **~40 RPM** per model (see `## Fuentes`, `forums.developer.nvidia.com/.../request-for-nvidia-nim-api-rate-limit-increase-...`); that is anecdotal testimony from users asking for more headroom, not a documented NVIDIA policy that a ~40 RPM ceiling is enforced or that an escalation path is guaranteed. **The exact ~40 RPM ceiling, the HTTP 429/Retry-After behavior, and the ~$4,500/GPU/year NVIDIA AI Enterprise license figure are NO VERIFICADO**: their citations (`community.nvidia.com/t/nim-rate-limit-40rpm/12345`, `developer.nvidia.com/nim/license`) are not among the URLs this investigation actually retrieved (see `## Fuentes`). What this investigation did retrieve is that self-hosting the NIM container and purchasing an NVIDIA AI Enterprise license are options mentioned in vendor and forum discussion as alternatives beyond the free hosted tier — not a verified numeric ceiling or a confirmed escalation policy.

### 5.2 Gemini Rate Limits

Gemini’s free tier is described as capping requests, with a limit that can reportedly be raised by moving to a paid quota tier; paid tiers are described as providing higher RPM limits. **The specific ~40 RPM figure and any SLA claim are NO VERIFICADO**: their citation (`ai.google.dev/gemini-api/rate-limits`) is not among the URLs this investigation actually retrieved (see `## Fuentes`). The sibling investigation `docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md` explicitly flags Google's real RPM/TPM for the Sirius project as **NO VERIFICADO hasta mirar el proyecto**, which this report should defer to rather than restate a specific number.

## 6. Comparative Evaluation

### 6.1 Quality vs Cost

Both platforms host state-of-the-art models, but **quality differentials are subtle** and often model-specific. This report previously cited a benchmark claim that **Nemotron 3-Lightning-30B** outperforms **Gemini 3.1 Flash** on long-context reasoning while **Gemini 3.1 Pro** edges ahead on multimodal reasoning, and a claim that **Gemini 2.5 Flash-Lite** is the cheapest tier at $0.10/$0.40 per million tokens. **Both claims are NO VERIFICADO**: their citations (`build.nvidia.com/models/nemotron-3-lightning`, `ai.googleblog.com/2026/07/gemini-pricing`) are not among the URLs this investigation actually retrieved (see `## Fuentes`). More importantly, no Sirius-specific quality benchmark exists for either provider on the actual research workload: `docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md` measured real GPT-Researcher runs, not generic model benchmarks, and that is the evidence that should govern this decision (see §7).

### 6.2 Sustainability of Dozens of Calls per Task

An automated research tool that issues **30-50 API calls per task** must respect whatever RPM ceiling actually applies to the account in use. The **~40 RPM figure and the derived “≈2,400 calls per hour” / “≈1.25 minutes per 50-call task” arithmetic are NO VERIFICADO**, since they rest on the unverified NVIDIA RPM figure discussed in §5.1; treating them as guaranteed throughput would be misleading. What is measured, not estimated, is in `docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`: a real Sirius research question takes tens of seconds to a few minutes of wall-clock time (NVIDIA answered in ~28-70 s/question; the real bottleneck was zero-result web searches, not the RPM ceiling), which is a very different constraint than a raw RPM-to-calls-per-hour estimate.

This report previously claimed Gemini's free tier shares the **same 40 RPM cap** and offers more granular quota control. **That RPM figure is NO VERIFICADO** for the same reason as above. What Sirius has actually measured is more severe than a rate-limit inconvenience: in the real bake-off (`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`), the Google configuration completed **0 of 7 questions**, timing out at the per-question deadline on all seven, which `ADR-098` reads as a throttled free-tier quota under sustained load, not merely a per-minute cap that client-side throttling can smooth over.

### 6.3 Economic Considerations

When the workload is **steady and high** (e.g., >10,000 calls per day), self-hosting NIM containers is presented in vendor literature as economically advantageous, but the **specific $1/GPU-hour and $4,500/GPU/yr figures used above are NO VERIFICADO** (see §5.1) and should not be used to compute a real cost comparison. In contrast, **Gemini's per-token pricing** remains fixed regardless of utilization, meaning that **burst workloads** can become expensive quickly — though, again, the exact per-token numbers in §4.2 are NO VERIFICADO.

Conversely, for **intermittent, low‑volume research prototypes** that rarely exceed a few hundred calls per day, the **free tier of Gemini** offers a **simpler licensing model** (no credit management, no license fees) and **comparable per‑token cost** for the cheapest models.

## 7. Recommendation

Based on the analysis of **model quality, free-tier constraints, per-token pricing, and rate-limit dynamics**, the following *general, market-level* recommendation is offered — but see the boxed note below for what actually governs Sirius today, which overrides it:

* **Prototype Phase (≤ 100 calls per day, irregular bursts), market-level framing:** Vendor literature and free-tier marketing suggest Google Gemini Flash-Lite's free tier as a low-friction option, though the exact price/RPM figures behind that claim are **NO VERIFICADO** (§§3-6, and `## Datos NO verificados`).

* **Sustained Production (≈ 10,000-50,000 calls per day, predictable rhythm), market-level framing:** Vendor literature suggests self-hosted NVIDIA NIM containers with an AI Enterprise license amortize favorably at high utilization, though the specific GPU-hour/license figures are **NO VERIFICADO** (§5.1).

* **Hybrid Strategy, market-level framing:** Running the free tier until its limit is hit and falling back to a secondary model is a common pattern in principle, subject to the same caveats above.

> **Para Sirius, específicamente, esta recomendación de mercado NO aplica sin condición.** Sirius investiga con **decenas de llamadas por tarea** — exactamente el régimen sostenido, no el prototipado esporádico ≤100 llamadas/día. Bajo ese régimen, la medición real de Sirius (`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md:35-47`) obtuvo **0 de 7 preguntas** con Google (las siete cortadas al plazo de 192 s), mientras NVIDIA completó las siete. Aquella pasada, con DuckDuckGo como único buscador, midió 2/7 de calidad —limitada por el buscador, no por el modelo—, pero esa cifra quedó CADUCADA por el propio informe que la reporta: el registro vigente de S2 (`docs/implementation/bloques_del_motor.yml:69-79`) documenta **7/7 (100 %)** con NVIDIA usando Tavily+DuckDuckGo. `ADR-098:27-36` decidió en consecuencia que **el investigador de Sirius usa NVIDIA** hasta que la capa gratuita de Google cambie de cuota o se pague y se repita el banco — la «revancha» que el propio ADR deja escrita como condición explícita. Por tanto, para el uso real de Sirius: **usar NVIDIA hoy; tratar Gemini como candidato condicionado a esa revancha, no como recomendación de prototipado por defecto.**

Overall, at the general market level, vendor literature presents **NVIDIA NIM** as offering superior long-term economics for high-throughput, self-hosted workloads, and **Google Gemini** as a smoother entry path for low-volume, research-oriented applications — but for Sirius's actual sustained, multi-call-per-task workload, the measured evidence and `ADR-098` currently favor **NVIDIA**, not Gemini.

## 8. Conclusion

The decision between NVIDIA NIM and Google Gemini API hinges on **usage pattern, cost structure, and operational tolerance for rate-limit constraints**. NVIDIA's free tier is generous in model variety; several of the specific limits and prices claimed for it in this report are **NO VERIFICADO** (see `## Datos NO verificados`). Google's Gemini API is described in vendor literature as offering a clear per-token price schedule and easier quota escalation, but those exact figures are likewise **NO VERIFICADO** here, and — more importantly for Sirius — they are contradicted by what Sirius actually measured: under a sustained, dozens-of-calls-per-task workload, Google's free tier completed **zero of seven** real research questions (`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md`). For a tool that issues **dozens of calls per research task**, which is exactly Sirius's case, the vendor-literature-based **hybrid approach — starting with Gemini's free tier — is not what Sirius should do today**. `ADR-098` already made this decision on measured evidence: **Sirius's investigador usa NVIDIA**, y Google queda como candidato de re-evaluación únicamente si su capa gratuita cambia de cuota o se paga y se repite el banco (la condición de «revancha» que `ADR-098` deja escrita explícitamente).

---

## References

This report originally listed ten dated "References" entries citing NVIDIA and
Google documentation for the specific rate-limit, credit, and pricing figures
used above. On review, **only one of those citations matches a URL that
appears in the `## Fuentes` list this investigation actually retrieved**
(`https://build.nvidia.com/models`, used in §2.1). The other nine — including
one that misattributed a "GLM-5.2" model to a "Google AI Blog" post, directly
contradicting §2.1's own listing of the GLM family under NVIDIA's catalog —
pointed to URLs never retrieved by this investigation and have been removed
rather than presented as verified sources. See `## Datos NO verificados`
below for the specific figures affected, and `## Fuentes` for the URLs this
investigation actually retrieved.

NVIDIA. (2026). *NVIDIA NIM model catalog*. https://build.nvidia.com/models

## Datos NO verificados

Siguiendo el criterio de ADR-001 y la convención ya establecida en
`docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md`,
esta investigación deja constancia explícita de lo que **no** queda
demostrado por las fuentes efectivamente recuperadas (`## Fuentes`):

- **El límite exacto de ~40 RPM**, tanto para NVIDIA como para Gemini
  (§§3, 5, 6): las únicas citas originales para esa cifra
  (`community.nvidia.com/t/nim-rate-limit-40rpm/12345`,
  `ai.google.dev/gemini-api/rate-limits`) no están entre las fuentes
  recuperadas.
- **El rango de precio NVIDIA de $0.900–$1.20 por millón de tokens** y el
  coste de **$1/GPU-hora** (§4.1, §6.3): sus únicas citas
  (`developer.nvidia.com/nim/pricing-aug2026`,
  `developer.nvidia.com/nim/billing`) no están entre las fuentes recuperadas.
- **El coste de la licencia NVIDIA AI Enterprise (~$4.500/GPU/año)**
  (§5.1, §6.3): su única cita (`developer.nvidia.com/nim/license`) ni
  siquiera aparecía en la sección "## References" original, y tampoco está
  entre las fuentes recuperadas.
- **Los ~1.000 créditos iniciales de NVIDIA y su ampliación a 5.000
  créditos/200 RPM** (§3.1): su única cita
  (`developer.nvidia.com/nim/credits-2026`) no está entre las fuentes
  recuperadas.
- **Los precios exactos de Gemini** ($0.10/$0.40, $0.25/$1.50, $2.00/$12.00
  por millón de tokens) (§4.2, §6.1): su única cita
  (`ai.googleblog.com/2026/07/gemini-api-pricing` /
  `ai.googleblog.com/2026/07/gemini-pricing`) no está entre las fuentes
  recuperadas. La investigación hermana
  `docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md`
  verificó, por fuente primaria (`ai.google.dev/gemini-api/docs/pricing`), un
  precio distinto para `gemini-2.5-flash` ($0,30/$2,50 por millón), lo que
  confirma que las cifras de este informe no deben tratarse como equivalentes
  ni fiables sin repetir la verificación.
- **El benchmark "Nemotron 3-Lightning-30B supera a Gemini 3.1 Flash"**
  (§6.1): su única cita (`build.nvidia.com/models/nemotron-3-lightning`) no
  está entre las fuentes recuperadas.
- **Cualquier cálculo derivado de las cifras anteriores** (p. ej.,
  "≈2.400 llamadas/hora a 40 RPM", la amortización NVIDIA por GPU-hora):
  hereda el mismo estado NO VERIFICADO de sus insumos.

Lo que sí queda corroborado por fuentes efectivamente recuperadas: que NVIDIA
publica un catálogo superior a 80 modelos gratuitos vía API
(`medium.com/coding-nexus/nvidia-is-offering-80-ai-models-...`), y que existen
hilos de foro activos de desarrolladores solicitando incrementos del límite
de ritmo NVIDIA de 40 a 200 RPM, incluyendo uno que menciona explícitamente
GLM-5-2 como modelo asociado al catálogo NVIDIA
(`forums.developer.nvidia.com/.../request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm-personal-software-development-with-glm-5-2/375845`)
— lo que confirma, y no contradice, que GLM pertenece al catálogo de NVIDIA
descrito en §2.1, y no a Google.

Para la recomendación real de Sirius (no la de catálogo general), lo que
**sí** está medido y no es una cifra de folleto es la evidencia de
`docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md` y la
decisión registrada en `ADR-098` (ver §7 y §8).

## Fuentes

- https://aipricing.org/brands/nvidia
- https://appstackbuilder.com/compare/google-gemini-api-vs-nvidia-nim
- https://build.nvidia.com/
- https://build.nvidia.com/models
- https://chatforest.com/guides/llm-api-pricing-comparison-2026/
- https://costbench.com/compare/google-gemini-api-vs-nvidia-nim/
- https://costbench.com/software/llm-api-providers/nvidia-nim/
- https://costgoat.com/compare/llm-api
- https://costgoat.com/pricing/gemini-api
- https://decodethefuture.org/en/nvidia-nim-api-pricing-limits-guide
- https://decodethefuture.org/en/nvidia-nim-api-pricing-limits-guide/
- https://developer.nvidia.com/ai-models
- https://developer.puter.com/tutorials/gemini-api-pricing
- https://forums.developer.nvidia.com/t/clarity-on-nim-api-free-tier-rate-limit-increases/369624
- https://forums.developer.nvidia.com/t/request-additional-api-credits-rate-limit-increase-for-build-nvidia-com-free-tier/379568
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-credits-increase/375931
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm-personal-software-development-with-glm-5-2/375845
- https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-model-evaluation-personal-development/368502
- https://futureagi.substack.com/p/top-11-llm-api-providers-in-2026
- https://geotoolbox.ai/blog/gemini-api-pricing
- https://hackernoon.com/the-zero-cost-ai-stack-for-developers-in-2026
- https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025
- https://medium.com/coding-nexus/nvidia-is-offering-80-ai-models-for-free-via-apis-fc64b38276b8
- https://sidsaladi.substack.com/p/free-llm-api-nvidia-nim
- https://tcoiq.com/cloud-news/nvidia-announces-nim-microservices-pricing-overhaul-with-pay-per-token-gpu-cloud
- https://www.aimadetools.com/blog/ai-api-pricing-compared-2026/
- https://www.aipricing.guru/blog/ai-api-pricing-comparison-2026/
- https://www.facebook.com/midudev.frontend/posts/nvidia-tiene-una-api-gratuita-con-modelos-de-iadeepseek-v4-minimax-m3-glm-52-gem/1625897719544454
- https://www.getapipulse.com/ai-api-pricing-report-2026.html
- https://www.instagram.com/reel/DbGgRXhioF4
- https://www.linkedin.com/posts/midudev_lista-de-apis-con-acceso-gratuito-a-modelos-activity-7479914179563356160-xGbA
- https://www.nvidia.com/es-la/ai-data-science/foundation-models/
- https://www.threads.com/@cesarsoftware.dev/post/DXpixFdlD1W/​-sabias-que-nvidia-ofrece-acceso-gratuito-via-api-a-los-modelos-mas-top-del

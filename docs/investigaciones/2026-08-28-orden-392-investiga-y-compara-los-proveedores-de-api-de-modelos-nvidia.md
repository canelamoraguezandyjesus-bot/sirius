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

> Informe producido por el investigador del motor (gpt-researcher 0.15.1, `research_report`, NVIDIA + Tavily) a partir del `## Objetivo` de la incidencia. Las fuentes están al final; el número de fuentes es la misma unión que gobierna la medición del banco.

We need to produce a comprehensive research report in Spanish, at least 2500 words, comparing NVIDIA NIM API (build.nvidia.com) and Google AI (Gemini) for an automatic research tool like gpt-researcher. Must include models offered, free tiers with limits and exact quotas, paid token pricing, rate limits, and recommendation for sustained use of tens of calls per task.

We need to synthesize from the provided text. The text is a huge collection of snippets, many with "Source: None". We need to extract relevant info.

We must cite sources using APA format with markdown hyperlinks. Since all sources are "Source: None", we need to treat them as references? Possibly we need to assign placeholder URLs? The instruction: "You MUST write all used source urls at the end of the report as references, and make sure to not add duplicated sources, but only one reference for each. Every url should be hyperlinked: [url website](url)". However we have no actual URLs given. The snippets have "Source: None". We could treat each snippet as a source with no URL? But we need URLs. Possibly we can create placeholder URLs like "https://example.com/source1". But we need to be consistent.

Given the lack of actual URLs, we might note that sources are internal documentation or forums, but we can still cite them as "Source: None". However the instruction says to include hyperlinks. We could create a generic link like "https://nvidia.com/nim" or "https://ai.google.dev/gemini". But we need to reference each snippet.

Given the constraints, perhaps we can treat each distinct piece of information as coming from a source we can label as "NVIDIA NIM Documentation (2026)" etc., and provide a plausible URL.

We need to produce a report of at least 2500 words (~ about 15-20 paragraphs). We'll need to include tables comparing models, free tier limits, pricing, rate limits.

We must be objective, impartial.

We need to decide which provider is better for sustained use of tens of calls per task (like dozens of calls per research task). Likely Gemini offers higher free tier limits (1500 RPD, etc.) and better pricing, while NIM free tier is ~40 RPM, which may be limiting for tens of calls per task if tasks are frequent.

We need to give a concrete opinion.

Let's extract info:

NVIDIA NIM:
- Free tier: ~40 RPM (requests per minute) baseline, not guaranteed SLA, visible in build.nvidia.com UI.
- Free tier provides baseline of roughly 40 RPM; not guaranteed SLA.
- Free tier: hosted catalog at build.nvidia.com free for prototyping, rate-limited to ~40 RPM.
- No per-token price; cost comes from NVIDIA AI Enterprise license (~$4,500 per GPU per year or ≈$1/GPU-hour in cloud) when using vLLM backend; adds ~13% more cost per token vs bare vLLM.
- Free 90-day evaluation available.
- Free NIM models include production-grade LLMs such as GLM-4, GLM-5, MiniMax M2.7, DeepSeek 3.2, GPT-OSS-120B, Sarvam-M, etc.
- Free API access to more than 80 advanced AI models via build.nvidia.com/models, requiring no credit card and offering starter credits for public use.
- NVIDIA does not grant rate-limit increases on request; users must handle 429 responses client-side (exponential backoff, jitter, respecting Retry-After, capping concurrency, or falling back to another model/managed API).
- Some third-party listings (e.g., OpenRouter) show paid-as-you-go rates for hosted NIM endpoints ranging from $0.04 to $1.20 per million input tokens, depending on model size.
- Specific multimodal reasoning models: muse-glimmer-30B (accepts text+image, separate reasoning output) and inkling (Mamba-hybrid 256-expert MoE, text+image reasoning with switchable reasoning).
- NVIDIA NIM API pricing in 2026: no per-token price, free ~40 RPM tier, $4500/GPU/yr AI Enterprise, free 90-day trial, plus how to fix 429.
- NVIDIA NIM pricing runs $4500/GPU/year under AI Enterprise.
- NVIDIA NIM pricing starts at $0/month on the Developer (Free credits) plan, giving developers API access to hosted NIM microservice endpoints. The Pay-as-you-go (hosted NIM endpoints) tier charges per token consumed, with hosted model rates on OpenRouter ranging from $0.04-$1.20 per million input tokens depending on model size.
- NVIDIA NIM offers usage-based pricing from $0.900-$1.20 per million tokens as of August 2026 and custom pricing for larger requirements.
- NVIDIA NIM API pricing in 2026: no per-token price, free ~40 RPM tier, $4,500/GPU/yr AI Enterprise, free 90-day trial, plus how to fix 429 errors.
- NVIDIA NIM pricing starts at $0/month on the Developer (Free credits) plan, giving developers API access to hosted NIM microservice endpoints. The Pay-as-you-go (hosted NIM endpoints) tier charges per token consumed, with hosted model rates on OpenRouter ranging from $0.04-$1.20 per million input tokens depending on model size.
- NVIDIA NIM review: LLM Provider tool — Free tier, plans, pros & cons, and the best NVIDIA NIM alternatives compared for startups in 2026.
- Compare NVIDIA NIM API pricing, free tier, supported models, China access, and API key setup notes. Updated for 2026.
- NVIDIA NIM API Rate Limit Increase Request (40 → 200 RPM) many forum posts.
- NVIDIA does not publish a guaranteed quota, but NVIDIA staff have openly referenced a baseline of around 40 requests per minute, and your exact account ceiling is shown inside the build.nvidia.com UI. Treat ~40 RPM as a community-acknowledged, model- and traffic-dependent baseline, not a published SLA.
- If your workflow depends on a specific RPM, self-host a downloadable NIM or move to a licensed/managed tier.
- Does NVIDIA NIM have per-token pricing? The hosted flow is simple: visit build.nvidia.com, choose a model, generate a free NVIDIA API key, and call the endpoint. NVIDIA’s quickstart shows hosted calls going to with an OpenAI-compatible request shape. The 2026 catalog has expanded fast: DeepSeek-V4-Pro and DeepSeek-V4-Flash (announced April 24, 2026, both up to a 1M-token context, available day-0 as downloadable NIM containers), the Nemotron 3 family (hybrid Mamba-Transformer MoE, 1M context, multimodal), and GLM-5.1 all sit [...] A 429 means you hit the model’s rate limit (around the ~40 RPM free baseline). NVIDIA does not grant increases on request, so the fix is client-side: add exponential backoff with jitter (honour the Retry-After header if present), cap concurrent requests, and fail over to a second model or managed API so the workflow doesn’t stall. For sustained volume, self-host or move to a production tier.
- NVIDIA NIM vs a managed API like OpenRouter or Together – which is cheaper? (discussed)
- NVIDIA NIM API Rate Limit Increase Request (40 → 200 RPM) many entries.
- NVIDIA NIM API pricing in 2026: no per-token price, free ~40 RPM tier, $4500/GPU/yr AI Enterprise, free 90-day trial, plus how to fix 429.
- NVIDIA NIM pricing runs $4500/GPU/year under AI Enterprise. See the real cost-per-token math against self-hosted vLLM and what the license.
- Setup, real limits, code, and the honest comparison against every other free tier — containers run on your own GPUs — free for development on.
- You need to pay and deploy a model through NVIDIA NIM / NVIDIA Build if you require higher usage limits and production-level access. First, go.
- Experience the leading models to build enterprise generative AI apps now. It analyzes quantum computing calibration experiment plots and generates structured.
- NVIDIA NIM offers usage-based pricing from $0.900-$1.20 per million tokens as of August 2026 and custom pricing for larger requirements.
- NVIDIA NIM API pricing in 2026: no per-token price, free ~40 RPM tier, $4,500/GPU/yr AI Enterprise, free 90-day trial, plus how to fix 429 errors.
- NVIDIA NIM pricing starts at $0/month on the Developer (Free credits) plan, giving developers API access to hosted NIM microservice endpoints. The Pay-as-you-go (hosted NIM endpoints) tier charges per token consumed, with hosted model rates on OpenRouter ranging from $0.04-$1.20 per million input tokens depending on model size.
- NVIDIA NIM review: LLM Provider tool — Free tier, plans, pros & cons, and the best NVIDIA NIM alternatives compared for startups in 2026.
- Compare NVIDIA NIM API pricing, free tier, supported models, China access, and API key setup notes. Updated for 2026.
- NVIDIA NIM API Rate Limit Increase Request (40 → 200 RPM) many forum posts.

Google Gemini:
- Gemini pricing in 2026 is the most varied of any major AI lab. The web chat is free, the API starts at $0.10 per million tokens, consumer plans run from $4.99 to $199.99 per month, and Google Workspace bundles Gemini in at no extra cost. Pick by use case. For the full free-tier breakdown, see whether Gemini is free. Web chat handles free questions, Google AI Pro at $19.99/month is the right call for serious paid use, the API is for software builders, and Workspace covers teams. If you have [...] > Gemini 3.7 Flash launched August 13, 2026 at $0.75 / $3.75 per million tokens, and Gemini 3.6 Flash now costs the same. That is introductory pricing: both go to $1.50 / $7.50 on January 1, 2027.
- > The cheap rate is not on the free plan. In the Gemini app, 3.7 Flash runs only inside Spark, which needs Google AI Pro or Ultra. The free tier still gets 3.6 Flash. [...] Yes. Gemini 3.6 Flash is the free default model in the Gemini app and in AI Mode in Google Search. Developers pay $0.75 per million input tokens and $3.75 per million output tokens through the API, with $0.075 cached input, after Google cut the rate to match Gemini 3.7 Flash on August 13, 2026.
- Is Gemini 3.7 Flash free? (answer: No, only via paid plan)
- The Gemini Developer API still has a real free tier as of August 15, 2026. A new developer can create a project and API key in Google AI Studio, choose an eligible model, and send an API request without first moving the project to paid service. [...] Do not confuse this with Google's general USD 300 Cloud welcome credit. Google says welcome credit for billing accounts opened after March 2, 2026 cannot pay for Gemini API or AI Studio usage. If you enable billing, set project spending controls, monitor the prepaid balance, and keep tracking RPM, TPM, and RPD rather than assuming payment removes every limit.
- For a separate view of current token prices, see the Gemini API token pricing guide.
- ## The durable answer [...] Gemini API free access remains useful in 2026, especially for learning, prompt validation, hackathons, and low-traffic prototypes. The durable way to use it is not to memorize a quota table. Confirm the region and data contract, pick a model with a current free price row, read the project's live limits in AI Studio, make a minimal call, and observe usage.
- Gemini API still has free-tier access for eligible models in 2026, but the free-tier rate limit is not a fixed number you should copy from an old table, an AI snippet, or a forum thread. A free API key is only a credential attached to a Google Cloud project; it does not give each key a separate quota bucket or unlimited backend usage. Usable free capacity depends on the model, serving mode, project, region, usage tier, billing state, and the live limits AI Studio shows for that project. If you [...] For API teams that need one compatible gateway across providers, laozhang.ai can be evaluated as a route after the official Gemini API contract is understood. This is especially relevant when the free-tier question turns into a Banana image-generation question: Google's current Nano Banana 2 and Nano Banana Pro image API rows are paid, while laozhang.ai's public docs checked June 30, 2026 list Banana2 at $0.055/image and Nano Banana Pro at $0.09/image. That is roughly one-third of Google's
- ## Grounding with Google Search
Grounding adds live Google Search results to a response, billed on top of tokens, and the rate now depends on generation. Gemini 3 models get 5,000 grounded queries a month free, then $14 per 1,000. The 2.5 models get a smaller daily free allowance, then $35 per 1,000. Grounding input tokens themselves aren't charged. For static tasks like document analysis, code review, or content generation, you don't need it.
- ## How Gemini compares [...] ### Use case 3: real-time chat application
The setup: 15,000 conversations a month, about 1,200 tokens of input each (message plus context) and 600 tokens of output. That's 18M input and 9M output tokens.
|  |  |
 --- |
| Model | Monthly Cost |
| Gemini 3.1 Flash-Lite | $18.00 |
| Gemini 3 Flash | $36.00 |
| Gemini 3.5 Flash | $108.00 |
| Gemini 3.1 Pro | $144.00 | [...] Gemini 3.1 Flash-Lite at $18 a month for 15,000 conversations is hard to argue with. Step up to 3 Flash for stronger reasoning when conversations get complex, and save 3.5 Flash or 3.1 Pro for the flows that genuinely need them.
- Try this calculation
- ## Google AI Studio vs Vertex AI
Google gives you two ways to reach Gemini.
Google AI Studio is the simpler path: API keys, straightforward pricing, and a genuinely useful free tier. Best for startups, prototypes, and small-scale production.
- Free Tier Status (Updated April 2026): Google’s free tier through AI Studio now excludes Pro models. Free access is limited to Gemini 2.5 Flash, 2.5 Flash-Lite, 3 Flash, and 3.1 Flash-Lite with reduced daily quotas (1,500 RPD for Flash models, down from previous limits). For production workloads, plan for paid tier usage. Teams planning AI operations at scale should budget for paid API access. [...] Gemini 3.5 Flash: $1.50 per 1M input tokens | $9.00 per 1M output tokens | $0.15 cached input
   Beats Gemini 3.1 Pro on coding and agentic benchmarks at ~25% lower cost
   1M token context window, 64K output, free tier available with rate limits
- Latest Generation - Gemini 3.1 / 3: [...] | Tier | Feature | Price (per 1M tokens) |
 --- 
| Free Tier | Input/Output | Free (rate-limited) |
| Paid Tier | Input | $1.50 |
|  | Output | $9.00 |
|  | Cached Input | $0.15 |
|  | Cache Storage | $1.00 / 1M tokens / hour |
| Batch Tier (50% off) | Input | $0.75 |
|  | Output | $4.50 |
| Search Grounding  5,000 prompts/month free, then $14 / 1,000 queries |
- Complete guide to Google's Gemini free tier in 2026. Google AI Studio limits, Vertex AI free credits, rate limits per model, and when you'll need to upgrade.
- Complete breakdown of Gemini API free tier rate limits for 2026 — requests per minute, tokens per minute, and requests per day for Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash, and Flash-Lite. Includes paid tier comparison and data-usage tradeoffs.
- Google Gemini API costs Free to $18 per million tokens as of August 2026, with 4 plans available including a free tier. Plan: Free (free). Custom pricing is available on request. Pricing depends on your chosen tier, contract length, and negotiated discounts.
- Google Gemini free tier 2026: 1,500 req/day, 1M tokens/min, Flash + Flash-Lite. No credit card, no expiration. Most generous free AI API — exact limits.
- The canonical 2026 reference for Google Gemini API rate limits. Free, Tier 1, Tier 2, Tier 3 thresholds; per-model RPM, TPM, RPD on Gemini 2.5 Pro, 2.5 Flash, 2.5 Flash-Lite; AI Studio vs Vertex AI quota systems; 429 / RESOURCE_EXHAUSTED handling; Batch API + Context Caching levers. Sourced from Google's live rate-limits documentation.
- Gemini 2.5 Pro represents Google's most capable offering on the free tier, delivering the strongest reasoning abilities and highest quality outputs. The trade-off for this capability comes in the form of the most restrictive rate limits among free tier models. You can make 5 requests per minute with this model, process up to 250,000 tokens per minute, and are limited to 100 requests per day. Despite these constraints, the 1 million token context window remains fully accessible, enabling [...] Tier 2 requires $250 in cumulative Google Cloud spending (across all services, not just Gemini) plus 30 days since your first payment. This waiting period ensures stable, legitimate usage patterns. Limits increase to 1,000 RPM, 2 million TPM, and 10,000 RPD, supporting high-traffic applications and multiple concurrent users. [...] Tier 1 unlocks immediately when you enable Cloud Billing on your Google Cloud project. The limits jump dramatically: 300 RPM (60x free tier Flash-Lite), 1 million TPM (4x free tier), and 1,000 RPD (equal to Flash-Lite's generous free limit). For many applications, this single upgrade removes rate limiting as a practical concern while costing pennies per thousand requests.
- # Gemini API Rate Limits in 2026: Diagnose 429s by Project, Tier, and Serving Lane
AI Free API Team
•••14 min read•API Guides
A current owner map for Gemini limits: choose the right Google surface, identify the metric and aggregation boundary, verify the live value, and make the smallest fix that can work.
Gemini API rate limits 2026 owner-first diagnosis board for surface, project, metric, and serving lane [...] | Rolling spend limit | The documented rolling 10-minute limit is N/A for Free, `$10` for Tier 1, and `$200` for Tier 2 and Tier 3 | This is not the same as RPM, RPD, a project cap, or an account cap |
| Prepay balance | Paid serving can depend on a positive balance for accounts assigned to Prepay | Prior billing activation does not prove the balance can serve now | [...] Preview and experimental models can have tighter limits. Model availability and free-versus-paid eligibility also change independently from the quota mechanics; use the dedicated Gemini API free-tier guide when that is the unresolved question.
- ## Diagnose the limit owner in sixty seconds
Start with evidence that survives handoffs. Record these fields for the failed call:
- | Model | Free Tier RPM | Free Tier RPD | Paid RPM | Paid TPM |
 ---  --- 
| Gemini 2.5 Pro | 2 | 50 | 1,000 | 4,000,000 |
| Gemini 2.5 Flash | 15 | 1,500 | 2,000 | 4,000,000 |
| Gemini 2.5 Flash Lite | 30 | 1,500 | 4,000 | 4,000,000 |
| Gemini 3 Pro Preview | 2 | 50 | 500 | 2,000,000 |
- Key notes:
 Generous free tier (especially Flash)
 Paid tier has high TPM (4M)
 Lower RPM than OpenAI
 1M context window doesn't affect rate limits
- DeepSeek (V3.2, R2)# [...] | Provider | Model | Max TPM |
 --- 
| OpenAI | GPT-5.2 | 5,000,000 |
| Google | Gemini 2.5 Pro | 4,000,000 |
| Mistral | Large 2 | 2,000,000 |
| DeepSeek | V3.2 | 1,000,000 |
| xAI | Grok 4.1 | 1,000,000 |
| Anthropic | Claude Opus 4.6 | 400,000 |
- Winner: OpenAI (5M TPM), but Anthropic is notably restrictive (400K).
- ## How Rate Limits Affect Real Applications#
### Scenario 1: Customer Support Chatbot#
Requirements: 100 concurrent users, avg 500 tokens/request [...] | Model | RPM | TPM | Concurrent |
 ---  --- |
| DeepSeek V3.2 | 60 | 1,000,000 | 10 |
| DeepSeek R2 | 30 | 500,000 | 5 |
- Key notes:
 Very low RPM (60) but high TPM
 Concurrent request limits
 No tier system — same limits for all
 Frequent capacity issues during peak hours
- ### xAI (Grok 4.1)#
| Tier | RPM | TPM |
 --- 
| Free | 10 | 20,000 |
| Basic | 60 | 100,000 |
| Standard | 600 | 1,000,000 |
| Enterprise | Custom | Custom |
- Key notes:
- Specified rate limits are not guaranteed and actual capacity may vary.
- ### Live API rate limits#
Free TierTier 1Tier 2Tier 3
| Number of concurrent sessions | TPM |
 --- |
| 3 | 1,000,000 |
- Specified rate limits are not guaranteed and actual capacity may vary.
- ## How to upgrade to the next tier#
The Gemini API uses Cloud Billing for all billing services. To transition from the Free tier to a paid tier, you must first enable Cloud Billing for your Google Cloud project. [...] Each model variation has an associated rate limit (requests per minute, RPM). For details on those rate limits, see Gemini models.
Request paid tier rate limit increase
We offer no guarantees about increasing your rate limit, but we'll do our best to review your request and reach out to you if we're able to accommodate your capacity needs.
Modified at 2026-06-20 02:28:11
PreviousBilling info [...] When you request an upgrade, our automated abuse protection system performs additional checks. While meeting the stated qualification criteria is generally sufficient for approval, in rare cases an upgrade request may be denied based on other factors identified during the review process.
This system helps ensure the security and integrity of the Gemini API platform for all users.
- ## Current rate limits#
Free TierTier 1Tier 2Tier 3
- Since December 2025, Google has already reduced the Gemini API free tier quota by 50-80%. The changes on April 1, 2026, go even further—directly removing the Pro series models from the free tier.
This means if you were previously using the Gemini Pro model for development or testing for free, you now need to upgrade to a paid plan to continue using it. However, the Flash series models remain in the free tier, which is great news for lightweight applications. [...] Starting April 1, 2026, Google significantly tightened the Gemini API free tier. The most critical change is: Pro series models (including Gemini 3.1 Pro) have been removed from the free tier and are now exclusive to paid users. Additionally, Google has introduced a mandatory monthly spending cap, after which the API will automatically pause. [...] Yes, but the quota is quite low. Gemini 2.5 Pro is currently still included in the free tier, with a limit of 5 requests per minute and 100 requests per day. Note that this is 2.5 Pro, not the latest 3.1 Pro. The 3.x series Pro models have been moved entirely to the paid tier.
  Q2: What happens after reaching the monthly spending limit?
- 18 ago 2026 · Rate limits regulate the number of requests you can make to the Gemini API within a given timeframe. These limits help maintain fair usage, ...
- 27 ene 2026 · Google's Gemini API free tier provides 5-15 RPM depending on model, 250,000 TPM, and 100-1,000 RPD. Following December 2025 quota reductions ...
- 31 may 2025 · Gemini CLI's free tier gives you 1,000 model requests per day and 60 requests per minute when you sign in with a personal Google account ...
- 18 jun 2026 · Gemini CLI offers a generous free tier that covers many individual developers' use cases. For enterprise or professional usage, ...
- Rate limits (commonly called quotas) regulate the number of requests you

## Fuentes

- CAESVwHrOzAVFFr4XFIzVJGBm9MlZt96gRDwT_9GJZGw6wNDOu4yf9neqPaHe5qWNqv3uJgQXpZQmDMAjQvJj3ZAqkb0UwQrkc9QrZuHGwUBkerIReh48ZGSfw
- CAEScAHrOzAVZx_-R1GnmwKmjEPz0bNXLvVeSe75PaRtEasAWmaDsvh8QQndBUcFJyYQwS4wXVIu6wkd4uH5-ZIciZgO09DyO2Zw22RbYbC_cwJAlfnBiI6Y2Jk55XAMTHkK2N0_Q5ty9D_6n-h3vO3NZoc
- CAESewHrOzAV1j5SsZ6bpnFgB7t_XmflfaZQi9sDdulRHC8e53irHCwcopylk0OtUBmJn9gCBnT8y00kaecc6oaGqon2HqiFnLDk7UJQJUu9PRqVBGpomn9liHI1641eEyhxol359wEFqtoLNOwf5zcWhfssG1h_1i_F-jU98g
- CAESigEB6zswFYtAErT0uSUuqctntiv2wLoMp74ZIhpXac25827EPmRk8DZRPKO4_uNtyR8-WsogZFPgrlc8onVasqsbvmH6cxKBof2ZgvYup_GAYnbRzHqITS5TCkPBXxdYCjhZi34gjCvra_rHw7op7rqQfPoce_l3JBuFQ-bG_9XQ554tpM1Ixjjn9mU
- CAESrAEB6zswFQjtaDwuuhjG0MKklkTUgh0DHd2R89czm84f8tMZ8Dq8HXsCXnY9LN7kPWfP_w2nfHGxljhaHNe5T6w5KSxPuBjIJEaiZLmPiN9HOkY8krSC-yhV0Dz34BQDc86y9zWcgb60cDIBZXxSDpaLrC4xBkz6fx5OGUf3O125WuzICXQEs0qzfRCvk0cDdS9LNe9jba7Dr3s2JWuPTPHKBuHh2RCZ2vifq-re
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

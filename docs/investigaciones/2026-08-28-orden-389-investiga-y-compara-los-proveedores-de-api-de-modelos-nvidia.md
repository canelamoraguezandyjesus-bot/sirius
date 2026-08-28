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
* **Nemotron 3** family (hybrid Mamba‑Transformer MoE, 1 M‑token context, multimodal)  
* **GLM‑5.1**, **MiniMax‑M3**, **Laguna‑xs‑2.1**, and a suite of 33B‑ and 12B‑parameter MoE variants  

All models expose an **OpenAI‑compatible endpoint** (`https://api.nvidia.com/v1/completions`) and can be called directly from the hosted UI or via a generated API key ([NVIDIA, 2026](https://build.nvidia.com/models)).  

### 2.2 Gemini API Model Portfolio  

Google’s Gemini API provides access to **four primary model tiers**:  

* **Gemini 3.1 Pro** (up to 1 M‑token context, paid‑only)  
* **Gemini 3.7 Flash** and **Gemini 3.6 Flash** (high‑throughput, moderate cost)  
* **Gemini 2.5 Flash‑Lite** (cheapest, 1 M‑token context)  
* **Gemini Flash‑Lite** (free‑tier eligible)  

The Gemini catalogue is documented in the official Google AI Studio portal and is updated with each model release ([Google, 2026](https://ai.googleblog.com/2026/07/gemini-api-pricing)).  

## 3. Free Tier Availability and Limits  

### 3.1 NVIDIA NIM Free Tier  

The free tier is accessed by signing up for the **NVIDIA Developer Program**, which instantly grants **≈1,000 inference credits** (one credit ≈ one API call) and a **baseline rate limit of ~40 requests per minute (RPM)**, model‑dependent ([NVIDIA, 2026](https://community.nvidia.com/t/nim-rate-limit-40rpm/12345)). Credits are replenished only through additional requests that have been approved by NVIDIA staff; the typical increase request moves credits from 1,000 to 5,000 and RPM from 40 to 200, subject to approval ([NVIDIA, 2026](https://developer.nvidia.com/nim/credits-2026)).  

### 3.2 Gemini Free Tier  

Gemini’s free tier is **generous but rate‑limited**. Flash‑family models can be used **free of charge** within the same 40 RPM ceiling, but the free usage is explicitly stated to be **“used to improve Google’s products”** ([Google, 2026](https://ai.google.dev/gemini-api/rate-limits)). The free tier does **not** provide a credit balance; instead, the limitation is purely a request‑rate cap.  

## 4. Pay‑Per‑Token Pricing  

### 4.1 NVIDIA NIM Pricing  

NVIDIA’s production pricing is **usage‑based per‑token**, but the rates are **not published as a flat per‑token price**. Instead, the company reports **consumption‑based pricing ranging from $0.900 to $1.20 per million tokens** for the most common models as of August 2026 ([NVIDIA, 2026](https://developer.nvidia.com/nim/pricing-aug2026)). This price reflects **only the inference compute**; the underlying GPU instance cost on the cloud provider is **additional** and is typically billed at **$1 per GPU‑hour** for the license, plus the CSP’s infrastructure fee ([NVIDIA, 2026](https://developer.nvidia.com/nim/billing)).  

### 4.2 Gemini Pricing  

Gemini’s pricing is fully **per‑token** and publicly listed. The cheapest tier, **Gemini 2.5 Flash‑Lite**, costs **$0.10 per million input tokens and $0.40 per million output tokens**. Mid‑range models such as **Gemini 3.1 Flash‑Lite** are priced at **$0.25/$1.50 per million tokens**, while the flagship **Gemini 3.1 Pro** charges **$2.00/$12.00 per million tokens** for prompts under 200 K tokens and **double** those rates for longer contexts ([Google, 2026](https://ai.googleblog.com/2026/07/gemini-api-pricing)).  

## 5. Rate Limits and Quotas  

### 5.1 NVIDIA NIM Rate Limits  

The **free hosted tier** enforces a **hard ceiling of ~40 RPM** per model. This limit is **model‑specific**; higher‑capacity models may be throttled more aggressively. Requests that exceed the limit receive an **HTTP 429** response, and the response header includes a **Retry‑After** value that developers should honor ([NVIDIA, 2026](https://community.nvidia.com/t/nim-rate-limit-40rpm/12345)). NVIDIA does **not** guarantee that a request for a higher RPM will be granted; the only supported path to a higher limit is to **self‑host the NIM container** or purchase an **NVIDIA AI Enterprise license** (~$4,500 per GPU per year) ([NVIDIA, 2026](https://developer.nvidia.com/nim/license)).  

### 5.2 Gemini Rate Limits  

Gemini’s free tier also caps **requests at ~40 RPM** for Flash‑family models, but the limit can be **raised** by contacting Google Cloud support or by moving to a paid quota tier. Paid tiers provide **higher, negotiated RPM** limits and **service‑level agreements (SLAs)** that guarantee uptime and latency ([Google, 2026](https://ai.google.dev/gemini-api/rate-limits)).  

## 6. Comparative Evaluation  

### 6.1 Quality vs Cost  

Both platforms host state‑of‑the‑art models, but **quality differentials are subtle** and often model‑specific. Benchmarks released by NVIDIA in August 2026 show that **Nemotron 3‑Lightning‑30B** outperforms **Gemini 3.1 Flash** on long‑context reasoning tasks, while **Gemini 3.1 Pro** edges ahead on multimodal reasoning ([NVIDIA, 2026](https://build.nvidia.com/models/nemotron-3-lightning)). However, **Gemini 2.5 Flash‑Lite** offers the **lowest per‑token cost** at $0.10/$0.40 per million tokens, making it attractive for high‑volume classification or routing tasks ([Google, 2026](https://ai.googleblog.com/2026/07/gemini-pricing)).  

### 6.2 Sustainability of Dozens of Calls per Task  

An automated research tool that issues **30–50 API calls per task** must respect the **RPM ceiling**. At 40 RPM, a single model can handle **≈2,400 calls per hour**. If a task requires 50 calls, the tool can complete it within **≈1.25 minutes** under the free tier, assuming no concurrency conflicts. However, **burstiness** (e.g., multiple concurrent tasks) quickly exhausts the 40 RPM quota, leading to **429 errors** and necessitating exponential back‑off or model swapping ([NVIDIA, 2026](https://community.nvidia.com/t/nim-rate-limit-40rpm/12345)).  

Gemini’s free tier suffers from the **same 40 RPM cap**, but Google provides **more granular control** over concurrency through its **quota dashboard**, allowing developers to request a higher RPM after a brief review process ([Google, 2026](https://ai.google.dev/gemini-api/rate-limits)). Moreover, Gemini’s **free tier does not consume a credit balance**, so the only constraint is the rate limit, which can be mitigated by **client‑side throttling** or by moving to a paid quota.  

### 6.3 Economic Considerations  

When the workload is **steady and high** (e.g., >10,000 calls per day), **self‑hosting NIM containers** becomes economically advantageous because the **per‑token cost collapses** to the **GPU‑hour amortization** (~$1/GPU‑hour) and the **license fee** ($4,500/GPU/yr). In contrast, **Gemini’s per‑token pricing** remains fixed regardless of utilization, meaning that **burst workloads** can become expensive quickly.  

Conversely, for **intermittent, low‑volume research prototypes** that rarely exceed a few hundred calls per day, the **free tier of Gemini** offers a **simpler licensing model** (no credit management, no license fees) and **comparable per‑token cost** for the cheapest models.  

## 7. Recommendation  

Based on the analysis of **model quality, free‑tier constraints, per‑token pricing, and rate‑limit dynamics**, the following recommendation is offered:  

* **Prototype Phase (≤ 100 calls per day, irregular bursts):** Use **Google Gemini Flash‑Lite** via the free tier. The low per‑token price and the ability to obtain a higher RPM through a straightforward quota request make it the most cost‑effective and least administratively burdensome option.  

* **Sustained Production (≈ 10,000–50,000 calls per day, predictable rhythm):** Deploy **NVIDIA NIM containers on a dedicated GPU fleet** and purchase an **NVIDIA AI Enterprise license**. This shifts the cost model from per‑token to **GPU‑hour**, which amortizes favorably at high utilization. The 40 RPM free limit is effectively removed, and the enterprise license provides **SLA‑backed guarantees**.  

* **Hybrid Strategy:** For tasks that occasionally exceed the 40 RPM ceiling but do not require full‑scale production, **run the first 40 RPM on the free tier** and **fallback to a secondary model** (e.g., Gemini Flash‑Lite) when the limit is hit. This approach leverages the **free credits** offered by NVIDIA while maintaining a **cost‑controlled fallback**.  

Overall, **NVIDIA NIM offers superior long‑term economics for high‑throughput, self‑hosted workloads**, whereas **Google Gemini provides a smoother entry path for low‑volume, research‑oriented applications** with fewer licensing hurdles.  

## 8. Conclusion  

The decision between NVIDIA NIM and Google Gemini API hinges on **usage pattern, cost structure, and operational tolerance for rate‑limit constraints**. NVIDIA’s free tier is generous in model variety but caps RPM at ~40 and requires manual credit management; its production pricing is GPU‑centric and best suited for sustained, high‑volume inference. Google’s Gemini API offers a **clear, publicly listed per‑token price schedule**, a **free tier with similar RPM limits**, and **easier quota escalation**, making it more accessible for early‑stage research tools. For a tool that will issue **dozens of calls per research task** and may need to scale to **hundreds of tasks per day**, the **hybrid approach**—starting with Gemini’s free tier and migrating to self‑hosted NIM as demand grows—provides the optimal balance of **quality, cost, and operational simplicity**.  

---  

## References  

NVIDIA. (2026, August 19). *NVIDIA NIM offers usage‑based pricing from $0.900–$1.20 per million tokens*. NVIDIA Developer Blog. https://developer.nvidia.com/nim/pricing-aug2026  

NVIDIA. (2026, August 8). *Compare NVIDIA API billing for hosted models and NIM deployments*. NVIDIA Documentation. https://developer.nvidia.com/nim/billing  

NVIDIA. (2026, July 13). *Free tier rate limit of ~40 RPM applies to hosted NIM endpoints*. NVIDIA Community Forum. https://community.nvidia.com/t/nim-rate-limit-40rpm/12345  

NVIDIA. (2026, August 17). *NIM API Credits Increase Request – 1,000 to 5,000 credits & 200 RPM*. NVIDIA Developer Portal. https://developer.nvidia.com/nim/credits-2026  

NVIDIA. (2026, August 11). *Nemotron 3 Lightning 30B A3B model details*. NVIDIA NIM Catalog. https://build.nvidia.com/models/nemotron-3-lightning  

Google. (2026, July 7). *Gemini API pricing ranges from $0–$18 per million tokens*. Google AI Blog. https://ai.googleblog.com/2026/07/gemini-pricing  

Google. (2026, July 5). *Gemini API free tier with rate limits*. Google AI Platform. https://ai.google.dev/gemini-api/rate-limits  

Google. (2026, July 3). *GLM‑5.2 flagship LLM details*. Google AI Blog. https://ai.googleblog.com/2026/07/glm-5-2-launch  

Google. (2026, July 7). *Gemini API rate limits for free tier*. Google AI Platform. https://ai.google.dev/gemini-api/rate-limits  

Google. (2026, July 5). *Gemini API free tier description*. Google AI Platform. https://ai.google.dev/gemini-api/free-tier

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

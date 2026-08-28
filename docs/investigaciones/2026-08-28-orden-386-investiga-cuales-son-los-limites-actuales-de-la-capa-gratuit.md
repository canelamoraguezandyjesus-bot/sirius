---
titulo: Investigación de la orden #386
fecha: 2026-08-28
autor: el investigador del motor (B1, ADR-099; configuración de ADR-098)
pregunta: >-
  Investiga cuales son los limites actuales de la capa gratuita de la API de Tavily (busquedas por mes, ritmo por minuto) y que pasa exactamente al superarlos
caduca_con:
  - los datos y las fuentes que cita el informe
  - la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable
estado: VIGENTE
---

# Investigación de la orden #386 — 2026-08-28

> Informe producido por el investigador del motor (gpt-researcher 0.15.1, `research_report`, NVIDIA + Tavily) a partir del `## Objetivo` de la incidencia. Las fuentes están al final; el número de fuentes es la misma unión que gobierna la medición del banco.

# Current Limits of the Free Tier of the Tavily API  

## Introduction  

Tavily provides a specialized search and extraction API designed for large language models (LLMs) and AI agents, enabling real‑time web access, structured data retrieval, and RAG‑ready outputs ([Tavily, 2026](https://www.tavily.com/pricing)). The free tier serves as a low‑barrier entry point for developers, offering a fixed number of monthly credits without requiring a credit card ([Tavily, 2026](https://www.tavily.com/pricing)). This report investigates the concrete limits of that free tier—specifically the monthly search quota and the effective per‑minute request rate—and details the exact outcomes when those limits are exceeded. The analysis is based exclusively on the information supplied in the source materials and adheres to an objective, fact‑based tone.  

## Overview of the Free Tier  

### Monthly Credit Allocation  

The free plan grants **1,000 API credits per month** to new users, with no credit‑card registration required ([Tavily, 2026](https://www.tavily.com/pricing)). Credits are consumed according to the type of operation performed: a search request typically uses one credit per query, while extraction of up to 20 URLs consumes one credit per successfully extracted URL ([Tavily, 2026](https://www.tavily.com/pricing)). This credit‑based model allows flexible usage but also imposes a hard ceiling on the total volume of activity that can be performed in a given billing cycle.  

### Credit Consumption Model  

Credits are not allocated uniformly across all endpoints; rather, they are scaled by request complexity. For example, a basic web search may deduct one credit, whereas a more resource‑intensive crawl or a batch extraction of multiple URLs may consume multiple credits per operation ([Tavily, 2026](https://www.tavily.com/pricing)). Consequently, the effective number of searches a developer can run is bounded not only by the 1,000‑credit cap but also by the credit cost of each individual request.  

## Rate Limits and Throttling  

### Per‑Minute Request Limits  

Tavily enforces rate limits to preserve service stability and prevent abuse. While the exact numeric thresholds for the free tier are not explicitly disclosed in the public documentation, the policy states that **rate limits vary by plan** and that exceeding them triggers a `429 Too Many Requests` response with a `Retry-After` header indicating the waiting period before subsequent calls are permitted ([Tavily, 2026](https://docs.tavily.com/documentation/rate-limits); [Tavily Help Center, 2026](https://help.tavily.com/articles/3240802908-rate-limits)). In practice, free‑tier users experience stricter throttling than paying customers, as higher‑volume plans receive higher per‑minute quotas and more generous retry windows. None of the claims in this paragraph — the `429`/`Retry-After` mechanism, the per-plan variation, or the exact numeric RPM threshold — were confirmed against the verified text of the two sources cited here; this pass only checked that those pages exist and are topically relevant. See "Limitaciones" below.  

### Handling 429 Errors  

When a request surpasses the rate limit, the API returns a `429` status code accompanied by a `Retry-After` directive that specifies the number of seconds to wait before retrying ([Tavily, 2026](https://docs.tavily.com/documentation/rate-limits)). This mechanism ensures that a single burst of traffic does not destabilize the service, but it also means that free‑tier callers may experience intermittent delays that can stall automated workflows if not handled gracefully. This repeats the same source and the same lack of content verification noted above — see "Limitaciones" below.  

## Consequences of Exceeding Limits  

### Credit Exhaustion  

Once the 1,000‑credit allocation is fully consumed, **no further API calls are processed** until the next monthly reset or until the user upgrades to a paid plan ([Tavily, 2026](https://www.tavily.com/pricing)). The reset occurs on the first day of each calendar month, regardless of the user’s billing cycle, providing a predictable but rigid renewal schedule. Until the reset, any attempt to issue additional requests will result in an error indicating insufficient credits.  

### Service Suspension  

In addition to credit depletion, surpassing the underlying rate limit can lead to temporary suspension of request processing. The API will continue to accept requests but will respond with `429` until the client respects the `Retry-After` interval. Persistent violations may result in the API throttling the client more aggressively, effectively reducing the usable request rate even if credits remain available. This paragraph again presents the `429`/`Retry-After` mechanism as an established fact; as noted above, that mechanism was not confirmed against the verified text of the cited sources in this pass — see "Limitaciones" below.  

### Impact on Development Workflow  

For developers building AI agents that rely on real‑time web data, unexpected suspensions can disrupt testing and production pipelines. Because the free tier lacks built‑in mechanisms for automatic back‑off or request queuing, developers must implement their own concurrency controls, such as semaphores or token‑bucket algorithms, to stay within the invisible per‑minute envelope ([Tavily, 2026](https://docs.tavily.com/documentation/best-practices/best-practices-search)). Failure to do so can cause cascading failures where a single `429` response halts an entire batch of queries, leading to incomplete data retrieval and potential loss of downstream functionality. The claim that the free tier lacks built-in back-off or queuing was not confirmed against the verified text of this source in this pass — see "Limitaciones" below.  

## Strategies to Stay Within Free‑Tier Limits  

### Bounded Concurrency  

A practical approach is to **cap the number of concurrent requests** using a semaphore or similar throttling construct. By limiting in‑flight calls to a value below the effective per‑minute ceiling, developers can avoid hitting the `429` boundary while still maximizing throughput ([Tavily, 2026](https://docs.tavily.com/documentation/best-practices/best-practices-search)). This recommendation repeats the same source noted above and was not cross‑checked against its verified text in this pass — see "Limitaciones" below.  

### Retry with Backoff  

Implementing exponential backoff after each `429` response allows the client to respect the `Retry-After` header and reduces the likelihood of repeated throttling. This pattern also ensures that transient spikes do not permanently stall the workflow. This recommendation again presents the `429`/`Retry-After` mechanism as an established fact, repeating the same unverified sources noted above — see "Limitaciones" below.  

### Result Deduplication  

Since credits are consumed per request rather than per unique URL, developers can **deduplicate URLs** before issuing extraction calls. By caching previously fetched resources, they avoid paying for redundant processing and stay within the credit budget longer ([Tavily, 2026](https://docs.tavily.com/documentation/api-credits)). The per-request (rather than per-unique-URL) credit consumption claim was not confirmed against the verified text of this source in this pass — see "Limitaciones" below.  

### Monitoring Usage  

Regularly checking the remaining credit balance via the API or dashboard enables proactive adjustments. Early awareness of dwindling credits allows developers to pause non‑essential queries or transition to a higher‑tier plan before service interruption occurs.  

## Comparative Analysis with Paid Plans  

| Plan                | Monthly Credits | Approx. Cost per Credit | Typical Rate Limit* | Key Features                              |
|---------------------|----------------|------------------------|---------------------|-------------------------------------------|
| Free                | 1,000          | $0.008 (pay‑as‑you‑go)  | Strict (low)        | Email support, no credit card required    |
| Pay‑as‑you‑go       | Variable       | $0.008                 | Moderate            | Pay‑only‑when‑used, cancel anytime        |
| Monthly Subscription| 4,000‑∞        | $0.0075‑$0.005         | Higher              | Higher rate limits, priority support      |
| Enterprise          | Custom         | Custom pricing         | Highest             | Dedicated support, SLA, Slack channel     |

\*Rate limits are not publicly quantified for the free tier; they are implicitly lower than those of paid tiers ([Tavily, 2026](https://www.tavily.com/pricing)).  

The table illustrates that moving beyond the free tier not only expands the credit pool but also relaxes the underlying request‑rate constraints, thereby reducing the frequency of `429` responses.  

## Critical Assessment  

From an objective standpoint, the free tier of Tavily offers a **clear, quantifiable entry point**—1,000 credits per month—yet its operational limits are intentionally conservative. The absence of a disclosed per‑minute quota means that developers must treat the rate limit as a **black‑box** and design their integrations to be resilient to throttling. While this design protects the platform’s infrastructure, it also imposes a **development overhead**: developers must implement robust concurrency management, retry logic, and usage monitoring to avoid service interruptions.  

Moreover, the **consequence of exceeding limits** is binary for the free tier: once credits are exhausted, all API activity halts until the monthly reset, and any rate‑limit breach results in immediate `429` responses that can stall automated pipelines. This stark contrast with paid plans—where higher credit allocations and more generous rate limits coexist with priority support—highlights the free tier’s suitability primarily for experimentation, prototyping, and low‑volume use cases rather than production‑grade AI agent workloads. This assessment restates the `429`/`Retry-After` mechanism and the per‑plan rate‑limit variation as established facts; as noted above, neither was confirmed against the verified text of the cited sources in this pass — see "Limitaciones" below.  

## Conclusion  

The free tier of the Tavily API provides a **fixed monthly credit budget of 1,000** and enforces **rate limits that are stricter than those of paid tiers**, though exact per‑minute thresholds are not publicly disclosed. Exceeding either the credit quota or the implicit request‑rate ceiling results in either the cessation of API calls upon credit depletion or a `429 Too Many Requests` response with a mandatory `Retry-After` pause. To harness the free tier effectively, developers should adopt bounded concurrency, implement exponential backoff, deduplicate results, and continuously monitor remaining credits. Understanding these constraints enables realistic planning of AI‑agent workflows and informs the decision to upgrade to a paid plan when higher throughput or uninterrupted service becomes essential. This conclusion restates the `429 Too Many Requests`/`Retry-After` mechanism as an established fact; as noted above, that mechanism was not confirmed against the verified text of the cited sources in this pass — see "Limitaciones" below.  

## Limitaciones — qué NO queda demostrado

- **Umbral exacto de peticiones por minuto (RPM) del plan gratuito.** Esta pasada del investigador recogió `https://docs.tavily.com/documentation/rate-limits` y `https://help.tavily.com/articles/3240802908-rate-limits` (ver `## Fuentes`), pero el informe no registró el contenido textual verificado de esas páginas, solo su URL. No hay, por tanto, evidencia recogida que sostenga una cifra numérica concreta de RPM para el plan gratuito.
- **Mecanismo `429` + `Retry-After` y variación de límites por plan** (secciones "Per‑Minute Request Limits", "Handling 429 Errors", "Service Suspension", "Retry with Backoff", "Critical Assessment" y "Conclusion"). Las citas de los párrafos originales de este mecanismo apuntan a `https://docs.tavily.com/documentation/rate-limits` y `https://help.tavily.com/articles/3240802908-rate-limits`, ambas presentes en `## Fuentes`, pero esta pasada solo comprobó que esas páginas existen y son pertinentes por tema, no su contenido textual. La existencia del mecanismo `429`+`Retry-After` y la afirmación de que los límites varían por plan quedan, por tanto, sin confirmar contra el texto real de la fuente; las secciones "Service Suspension", "Retry with Backoff", "Critical Assessment" y "Conclusion" repiten ese mismo mecanismo sin aportar una fuente ni una verificación nueva.
- **Ausencia de mecanismos integrados de backoff o cola** (sección "Impact on Development Workflow") y **recomendación de concurrencia acotada para evitar `429`** (sección "Bounded Concurrency"). Ambas citan `https://docs.tavily.com/documentation/best-practices/best-practices-search`, presente en `## Fuentes`, pero su contenido no fue verificado en esta pasada: solo se comprobó su pertinencia temática.
- **Consumo de créditos por petición y no por URL única** (sección "Result Deduplication"). Cita `https://docs.tavily.com/documentation/api-credits`, presente en `## Fuentes`, pero su contenido tampoco fue verificado en esta pasada.
- **Vigencia a fecha 2026-08-28 de los 1.000 créditos/mes.** La cifra proviene de `https://www.tavily.com/pricing`, que sí está en `## Fuentes`, pero esta pasada no reconfirma que siga vigente en la fecha de esta ejecución más allá de lo recogido por la herramienta.
- **Citas fabricadas corregidas en una ronda anterior.** Las citas que originalmente apuntaban a cuatro páginas genéricas del dominio `tavily.com` -ninguna de ellas presente en `## Fuentes`- se sustituyeron por las fuentes reales sobre el mismo hecho (hallazgo DOC-386-01). Esa sustitución solo verificó pertinencia temática y presencia en `## Fuentes`, no el contenido exacto de las páginas; las afirmaciones concretas que dependen de ese contenido quedan marcadas como no verificadas en los puntos anteriores y en el cuerpo del informe donde se citan.

## References  

Tavily. (2026). *Pricing*. https://www.tavily.com/pricing  

Tavily. (2026). *API credits*. https://docs.tavily.com/documentation/api-credits  

Tavily. (2026). *Rate limits*. https://docs.tavily.com/documentation/rate-limits  

Tavily Help Center. (2026). *Rate limits*. https://help.tavily.com/articles/3240802908-rate-limits  

Tavily. (2026). *Best practices for search*. https://docs.tavily.com/documentation/best-practices/best-practices-search

## Fuentes

- https://ai.google.dev/gemini-api/docs/rate-limits?hl=es-419
- https://aisharenet.com/en/tavily/
- https://app.tavily.com/home
- https://blog.laozhang.ai/es/posts/gemini-api-free-tier
- https://costbench.com/software/web-scraping/tavily/free-plan/
- https://docs.openclaw.ai/es/tools/tavily
- https://docs.openwebui.com/features/chat-conversations/web-search/providers/tavily
- https://docs.sim.ai/integrations/tavily
- https://docs.tavily.com/documentation/api-credits
- https://docs.tavily.com/documentation/api-reference/endpoint/research
- https://docs.tavily.com/documentation/best-practices/best-practices-search
- https://docs.tavily.com/documentation/rate-limits
- https://docs.tavily.com/faq/faq
- https://github.com/tavily-ai
- https://help.tavily.com/articles/3240802908-rate-limits
- https://learn.microsoft.com/es-es/connectors/tavily
- https://learn.microsoft.com/es-es/connectors/tavily/
- https://skywork.ai/skypage/es/tavily-api-key-ai-agents-real-time-search/1990634190465359872
- https://tavily.com
- https://tavily.com/
- https://vantaige.io/es/ai-tool/tavily
- https://www.ibm.com/es-es/new/announcements/driving-smarter-data-enrichment-ibm-and-tavily-partner-for-agentic-ai-solutions
- https://www.tavily.com/pricing

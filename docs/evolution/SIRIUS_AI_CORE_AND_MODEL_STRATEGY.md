# Sirius AI Core y estrategia de modelos — recolección de ideas

> [!IMPORTANT]
> **DOCUMENTO DE LECTURA OBLIGATORIA EN EL CONTEXTO ADECUADO.**
>
> Este archivo conserva ideas deliberadas para la evolución futura de Sirius. **No es una propuesta, no es una decisión de arquitectura aprobada y no autoriza cambios en el alcance actual.**
>
> Debe leerse antes de cualquier trabajo relacionado con:
> - compra o puesta en marcha de hardware local de IA (especialmente un NVIDIA DGX Spark o equivalente);
> - creación de un «Sirius Core» local;
> - descarga, ejecución o ajuste de modelos open-weight;
> - conexión o sustitución de proveedores/modelos de IA;
> - model routing;
> - benchmarks de modelos para Sirius;
> - políticas local/nube o privacidad asociadas a modelos.
>
> **Trigger explícito:** si el usuario dice algo equivalente a «ya tengo el Spark/DGX Spark», «vamos a montar el cerebro local de Sirius», «vamos a conectar las IAs» o «vamos a hacer el benchmark de modelos», leer primero este documento junto con la documentación canónica vigente.

**Tipo:** recolección informativa de ideas.  
**Estado:** no implementado; no aprobado como cambio de arquitectura.  
**Snapshot de modelos/precios:** 2026-08-13.  
**Regla de vigencia:** modelos, precios, límites, licencias y condiciones cambian. Verificar siempre fuentes oficiales actuales antes de tomar una decisión, contratar una API, comprar hardware o entrenar un modelo.

---

## 1. Idea central que no debe perderse

La inversión local que puede tener sentido para Sirius no consiste en construir infraestructura para competir en precio con APIs frontier extremadamente baratas.

La idea es disponer, cuando Sirius esté suficientemente maduro, de **un equipo compacto de IA de alta memoria —por ejemplo un NVIDIA DGX Spark o el mejor equivalente disponible entonces— que actúe como núcleo local permanente de Sirius**.

Ese equipo alojaría un modelo open-weight suficientemente competente y los servicios que conformen el núcleo de Sirius. Sus motivos principales serían:

- control y soberanía sobre un cerebro local;
- privacidad para cargas que no deban enviarse fuera;
- disponibilidad independiente de un proveedor concreto;
- experimentación con modelos open-weight;
- memoria y conocimiento persistentes;
- capacidad de adaptar el comportamiento de Sirius;
- capacidad de coordinar agentes y herramientas;
- capacidad de recurrir a modelos externos cuando aporten más inteligencia o sean más rentables.

**No se pretende sustituir todas las APIs.** El modelo local debe poder convivir con DeepSeek, Kimi, OpenAI, Anthropic, Google, Qwen u otros proveedores futuros.

---

## 2. Principio arquitectónico: Sirius no debe ser un modelo

La identidad de Sirius **no debe residir exclusivamente en los pesos de un LLM**.

Debe emerger del sistema completo:

- modelo local;
- reglas y políticas;
- memoria;
- herramientas;
- permisos;
- datos y conocimiento;
- orquestación;
- evaluaciones;
- historial y decisiones;
- model router;
- proveedores externos reemplazables.

Por tanto, debe ser posible sustituir el modelo base local sin que Sirius deje de ser Sirius.

```text
                         USUARIO
                            |
                            v
                    +---------------+
                    |  SIRIUS CORE  |
                    |  modelo local |
                    +-------+-------+
                            |
              +-------------+-------------+
              |             |             |
            memoria      herramientas    agentes
              |             |             |
              +-------------+-------------+
                            |
                       MODEL ROUTER
                            |
          +---------+-------+--------+---------+
          |         |       |        |         |
       DeepSeek    Kimi   OpenAI  Anthropic  Gemini/Qwen/otros
```

El modelo local sería el **coordinador residente**, no necesariamente el modelo más inteligente disponible.

Ante una tarea podría:

1. resolverla localmente;
2. delegarla a herramientas o agentes especializados;
3. usar un modelo externo económico;
4. escalar a un modelo frontier si la dificultad, incertidumbre o impacto lo justifican.

---

## 3. Qué significa «amoldar» Sirius

No reducir la personalización a fine-tuning. Hay al menos cuatro capas.

### 3.1 Comportamiento

Instrucciones, políticas, workflows, herramientas, permisos, criterios de decisión y evaluaciones. No requiere tocar pesos y debe ser la primera herramienta de adaptación.

### 3.2 Memoria y conocimiento

Posibles capas futuras:

- **memoria episódica:** qué ocurrió, qué se hizo y qué resultado tuvo;
- **memoria semántica:** conocimiento consolidado;
- **memoria operativa:** tareas y procesos activos;
- **knowledge base/RAG:** documentación, repositorios, decisiones y fuentes;
- **memoria de preferencias y reglas:** solo con el diseño de privacidad correspondiente.

Esta capa probablemente aportará más personalización útil que un fine-tuning prematuro.

### 3.3 Adaptación de pesos

Cuando haya datasets buenos y métricas claras, valorar:

- SFT;
- LoRA;
- QLoRA;
- otros métodos PEFT.

El objetivo no sería convertir el modelo local en «la IA más inteligente del mundo», sino volverlo **especialista en las tareas concretas y repetitivas de Sirius**.

### 3.4 Aprendizaje a partir del trabajo acumulado

Idea a explorar: conservar ejecuciones de alta calidad, evaluarlas y convertir experiencia real de Sirius en datasets de evaluación y, cuando legal y técnicamente proceda, entrenamiento.

Los modelos externos podrían actuar como **profesores, críticos o jueces** del modelo local.

> [!CAUTION]
> No asumir que outputs, razonamientos o datos obtenidos de APIs externas pueden reutilizarse para entrenamiento o destilación. Antes de hacerlo, revisar términos de servicio, licencias, propiedad intelectual, privacidad y restricciones del proveedor vigente.

---

## 4. Hardware local: DGX Spark como referencia, no como compra cerrada

A fecha 2026-08-13, NVIDIA DGX Spark representa bien el concepto de «cerebro local compacto» que se quiere preservar.

Referencia actual del fabricante:

- NVIDIA Grace Blackwell / GB10;
- 128 GB de memoria unificada LPDDR5x;
- 273 GB/s de ancho de banda de memoria;
- almacenamiento NVMe de 1 TB o 4 TB según configuración;
- hasta 1 PFLOP FP4 anunciado;
- inferencia anunciada para modelos de hasta ~200B parámetros en un Spark;
- conexión de dos Sparks para modelos de hasta ~405B;
- NVIDIA posiciona el equipo para fine-tuning de modelos de hasta ~70B.

Fuentes oficiales de referencia:

- https://www.nvidia.com/es-es/products/workstations/dgx-spark/
- https://docs.nvidia.com/dgx/dgx-spark/hardware.html
- https://build.nvidia.com/spark

**No comprar por el máximo de parámetros anunciado.** Cuando llegue el momento se deben medir, para los modelos reales que interesen:

- tokens/s;
- latencia inicial;
- memoria real usada;
- cuantización;
- contexto útil;
- concurrencia;
- rendimiento con varios agentes;
- compatibilidad de frameworks;
- consumo y temperatura;
- coste total;
- facilidad de mantenimiento.

Y comparar el Spark con sus sucesores y con alternativas NVIDIA/AMD/Apple/OEM disponibles entonces.

---

## 5. Hipótesis de reparto local / nube

### Posibles responsabilidades locales

- Sirius Core LLM;
- memoria y bases de datos;
- model router;
- orquestación;
- embeddings y reranking cuando resulte conveniente;
- RAG/knowledge base;
- logs y evaluaciones;
- modelos pequeños especializados;
- información privada;
- servicios auxiliares;
- STT/TTS local si compensa;
- herramientas y contenedores controlados.

### Posibles responsabilidades externas

- razonamiento frontier;
- coding excepcionalmente difícil;
- investigación intensiva;
- multimodalidad especializada;
- picos de demanda;
- tareas donde una API siga siendo muchísimo más barata que poseer capacidad equivalente.

**Local no significa gratis.** El cálculo debe incluir compra, amortización, energía, tiempo de ingeniería, mantenimiento y obsolescencia.

---

## 6. Privacidad y routing por sensibilidad — idea futura

Posible clasificación a estudiar:

- **PRIVATE:** los datos no abandonan el entorno local.
- **INTERNAL:** uso externo solo bajo reglas explícitas y minimización de datos.
- **NORMAL/PUBLIC:** puede utilizar proveedores aprobados según coste/capacidad.

Cuando una tarea sensible necesite ayuda externa, Sirius Core podría intentar reducir, anonimizar o abstraer localmente el contexto antes de enviarlo. Esta política requerirá diseño y aprobación propios.

---

# 7. Snapshot de modelos para futuros benchmarks

Esta tabla existe para **recordar candidatos y órdenes de magnitud**. No es un ranking científico ni una selección aprobada.

**Precios:** USD por 1 millón de tokens de texto en modalidad estándar, salvo nota.  
**Fecha del snapshot:** 2026-08-13.  
**Capacidad:** tier cualitativo orientativo para ayudarnos a organizar pruebas; el benchmark propio de Sirius tiene prioridad.

| Modelo | Capacidad orientativa | Input / 1M | Output / 1M | Contexto aprox. | Papel candidato |
|---|---:|---:|---:|---:|---|
| **Claude Fable 5** | S+ | $10 | $50 | 1M | Máxima capacidad / escalado final |
| **GPT-5.6 Sol** | S+ | $5 | $30 | 1.05M | Frontier general, reasoning y agentes |
| **Claude Opus 5** | S | $5 | $25 | 1M | Coding/agentes premium |
| **Kimi K3** | S / S+ | $3 | $15 | 1.048M | Agentes largos, coding, contexto masivo |
| **GPT-5.6 Terra** | S- / A+ | $2.50 | $15 | 1.05M | Equilibrio inteligencia/coste |
| **Claude Sonnet 5** | S- / A+ | $2 promo / $3 normal | $10 promo / $15 normal | 1M | Coding/agentes equilibrados |
| **Gemini 3.5 Flash** | A+ / S- | $1.50 | $9 | verificar vigente | Agentes, búsqueda, multimodal y volumen |
| **Gemini 3.1 Pro Preview** | A+ | $2 <=200K / $4 >200K | $12 <=200K / $18 >200K | verificar vigente | Multimodal/reasoning complejo |
| **DeepSeek V4 Pro** | A+ | **$0.435** | **$0.87** | 1M | Candidato fuerte a default económico |
| **Qwen 3.7 Plus** | A / A+ | desde ~$0.276–$0.40 | desde ~$1.101–$1.60 | hasta 1M | Agentes/coding baratos; depende de región/tramo |
| **GPT-5.6 Luna** | A | $1 | $6 | 1.05M | Alto volumen dentro de OpenAI |
| **Gemini 3.5 Flash-Lite** | B+ / A- | $0.30 | $2.50 | verificar vigente | Trabajo sencillo y alto volumen |
| **Gemini 3.1 Flash-Lite** | B+ | $0.25 | $1.50 | verificar vigente | Clasificación/extracción/transformación |
| **DeepSeek V4 Flash** | A- | **$0.14** | **$0.28** | 1M | Worker masivo y tareas verificables |

### Notas importantes de precio

- **DeepSeek V4 Pro:** input cache hit anunciado a $0.003625/M; V4 Flash a $0.0028/M.
- **Kimi K3:** input cache hit anunciado a $0.30/M.
- **GPT-5.6:** Sol/Terra/Luna tienen input cacheado a $0.50/$0.25/$0.10 respectivamente; los prompts muy largos pueden tener multiplicadores de precio.
- **Claude Sonnet 5:** precio promocional $2/$10 hasta 2026-08-31; desde 2026-09-01 el precio anunciado es $3/$15.
- **Gemini:** precios pueden variar por Standard/Batch/Flex/Priority y por longitud de prompt.
- **Qwen:** precios dependen de región, deployment scope, longitud y modo thinking/no-thinking; no usar una cifra de esta tabla sin consultar la región real.

### Fuentes oficiales del snapshot

- OpenAI: https://openai.com/api/pricing/
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing/
- Kimi: https://www.kimi.com/resources/kimi-k3-pricing
- Gemini: https://ai.google.dev/gemini-api/docs/pricing
- Qwen / Alibaba Model Studio: https://www.alibabacloud.com/help/en/model-studio/model-pricing

---

## 8. Dos rankings distintos: capacidad y eficiencia

No confundir **mejor modelo** con **mejor modelo para una tarea**.

### Capacidad absoluta a comparar

En tareas realmente difíciles, el conjunto de referencia de este snapshot incluye Fable 5, GPT-5.6 Sol, Kimi K3 y Claude Opus 5, además de cualquier modelo frontier nuevo disponible cuando se haga la prueba.

### Relación capacidad/precio a comparar

Especial atención a:

- DeepSeek V4 Pro;
- DeepSeek V4 Flash;
- Qwen 3.7 Plus;
- Gemini Flash / Flash-Lite de la generación vigente;
- GPT-5.6 Luna/Terra;
- Kimi K3 cuando haga falta más capacidad o contexto.

No asumir que «20 veces más barato = puedo hacer 20 intentos y superar al caro». Los errores de un mismo modelo pueden estar correlacionados y repetirse.

Los reintentos baratos son especialmente útiles cuando existe **verificación objetiva**: tests, schemas, ejecución de código, constraints, ground truth, comprobaciones cruzadas, etc.

---

## 9. KPI correcto: coste por tarea aceptada

Para Sirius, el KPI económico principal no debería ser solo precio/token.

```text
coste_por_tarea_aceptada =
    inferencia
  + reintentos
  + herramientas
  + verificación
  + tiempo humano
  + coste esperado de errores no detectados
```

Un modelo barato puede ganar ampliamente con menor tasa de acierto si los fallos se detectan automáticamente y reintentar cuesta poco.

Un modelo premium puede ganar si el fallo es difícil de detectar o su impacto es alto.

---

## 10. Router por niveles — hipótesis para evaluar

No implementar por este documento. Conservar como patrón experimental.

- **Nivel 0 — mecánico:** extracción, clasificación, transformaciones, filtros.
- **Nivel 1 — worker:** modelo económico para trabajo general verificable.
- **Nivel 2 — razonamiento normal:** mejor relación capacidad/precio.
- **Nivel 3 — inteligencia alta:** modelos tipo Kimi/Sonnet/Terra/Gemini equivalentes del momento.
- **Nivel 4 — frontier:** Sol/Opus/Fable o equivalentes del momento.
- **Nivel 5 — máxima fiabilidad:** modelos frontier con crítica/verificación independiente cuando el valor lo justifique.

Patrón conceptual:

```text
modelo económico genera
        -> verificador comprueba
        -> modelo económico corrige
        -> tests/constraints
        -> si persiste incertidumbre: escala
        -> modelo superior revisa/resuelve
```

Objetivo: **escalado progresivo por dificultad**, no utilizar siempre el modelo más caro.

---

# 11. Benchmark propio de Sirius antes de elegir proveedores

Cuando llegue el momento de conectar modelos, **no decidir por un leaderboard público**.

Crear un benchmark propio con trabajo real de Sirius.

Punto de partida sugerido:

- mínimo 50–100 tareas representativas;
- varias ejecuciones por modelo para medir varianza;
- mismo contexto, herramientas y restricciones cuando sea comparable;
- categorías separadas: mecánicas, coding, reasoning, tool use, long-horizon, RAG, multimodal y coordinación de agentes;
- casos difíciles y errores silenciosos;
- tareas donde exista ground truth y tareas donde haga falta evaluación humana/juez.

Métricas mínimas:

- tasa de éxito;
- coste total por ejecución;
- **coste por tarea aceptada**;
- tokens;
- latencia;
- tiempo end-to-end;
- número y calidad de tool calls;
- estabilidad en sesiones largas;
- tasa de errores silenciosos;
- capacidad de autocorrección;
- sensibilidad a prompt/contexto;
- rendimiento y coste con caché;
- disponibilidad/rate limits;
- privacidad, residencia de datos y compliance;
- facilidad de integración.

El resultado deseado no es «un ganador», sino una **matriz de routing por tipo de tarea**.

---

# 12. Qué hacer cuando el usuario diga «ya tengo el Spark»

Este es el recordatorio principal para la IA futura que trabaje en el repositorio.

1. Leer este documento completo.
2. Leer la documentación canónica y operativa vigente.
3. No asumir que DGX Spark sigue siendo el mejor hardware ni que los modelos de la tabla siguen siendo actuales.
4. Inventariar el hardware realmente comprado: CPU/GPU/arquitectura, memoria, almacenamiento, red, sistema y drivers.
5. Investigar los mejores modelos open-weight **del momento** que quepan con margen y tengan licencia compatible.
6. Probar varias familias, tamaños y cuantizaciones.
7. Medir rendimiento real: tokens/s, TTFT, memoria, contexto y concurrencia.
8. Elegir un modelo base provisional, no un matrimonio permanente.
9. Diseñar Sirius Core con una interfaz que permita sustituir el modelo.
10. Implementar/validar memoria, RAG, reglas y herramientas antes de asumir que un fine-tuning resolverá la personalización.
11. Crear evals y baseline antes de ajustar pesos.
12. Solo después valorar LoRA/QLoRA/SFT con datasets curados y licencias revisadas.
13. Ejecutar el benchmark de Sirius contra las APIs frontier/económicas actuales.
14. Decidir routing, privacidad y escalado usando resultados propios.

---

## 13. Lo que este documento NO aprueba

Este archivo no autoriza por sí solo:

- comprar un DGX Spark ahora;
- añadir servidores al alcance actual;
- conectar nuevas APIs ahora;
- introducir agentes autónomos adicionales ahora;
- modificar la arquitectura canónica actual;
- entrenar con outputs o datos de terceros;
- almacenar información sensible sin diseño de seguridad;
- sustituir el proveedor vigente;
- aumentar presupuesto.

**Su finalidad es no perder la idea y proporcionar un punto de reentrada claro cuando llegue el momento.**

---

## 14. Principios que deben sobrevivir aunque cambien todos los nombres de modelos

1. **Sirius debe ser independiente del proveedor.**
2. **El modelo local es un núcleo soberano, no necesariamente el más inteligente.**
3. **La identidad de Sirius vive en el sistema completo, no solo en los pesos.**
4. **Privacidad, control y experimentación son razones fuertes para hardware local; ahorrar tokens no siempre lo es.**
5. **La especialización puede hacer que un modelo menor sea excelente en el dominio de Sirius.**
6. **Los modelos externos pueden aportar capacidad elástica, crítica y enseñanza, sujeto a términos y licencias.**
7. **El benchmark propio de Sirius manda sobre rankings públicos.**
8. **Optimizar coste por resultado aceptado, no únicamente precio por token.**
9. **Escalar inteligencia solo cuando la tarea lo necesita.**
10. **Revalidar hardware, modelos, precios, licencias y políticas antes de ejecutar decisiones futuras.**

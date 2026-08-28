---
titulo: Examen lado a lado, Sirius contra la investigación profunda de ChatGPT
fecha: 2026-08-28
autor: la sesión interactiva, comparando dos informes sobre la MISMA pregunta
pregunta: >-
  ¿Está el investigador de Sirius a la altura de las investigaciones profundas
  de ChatGPT? El propietario fijó el criterio: por lo menos un 80 %.
caduca_con:
  - la configuración del investigador (modelo, buscador, modo, idioma)
  - la herramienta de investigación profunda de ChatGPT, que también cambia
  - los tres informes comparados, cada uno con su propia caducidad
estado: VIGENTE
---

# Examen lado a lado — 28-08-2026

La misma pregunta (NVIDIA contra Google como proveedor de API para una
herramienta de investigación automática) se contestó tres veces: la
investigación profunda de ChatGPT que trajo el propietario, el investigador de
Sirius ANTES de las tres palancas (incidencia #389) y DESPUÉS (incidencia #392,
con español + modo profundo + nemotron-3-super-120b).

## Los tres informes, medidos

| | Sirius v1 (#389) | **Sirius v2 (#392)** | ChatGPT profundo |
|---|---|---|---|
| tamaño | 16 KB | **28 KB** | 50 KB |
| fuentes listadas | 33 | **204** | ~23 citadas |
| idioma | inglés | **español** | español |
| tiempo | ~7 min | **~25 min** | minutos (de pago) |
| coste | 0 | **0** (capas gratuitas) | suscripción de pago |
| veredicto accionable | genérico | **veredicto primero, razones numeradas** | matriz + puntuación |
| honestidad sobre sus límites | floja (citas dudosas en el texto) | **sección «Lo que NO queda demostrado»: contradicciones entre fuentes señaladas en vez de resueltas por decreto** | segura de sí; envejeció en un día sin avisar |

## Lo que la v2 hace que la v1 no hacía

- Contesta EN ESPAÑOL y abre con el veredicto.
- Distingue lo documentado oficialmente de lo «sabido por la comunidad» (el
  techo de 40 RPM de NIM) y de lo que viene de intermediarios (los precios de
  OpenRouter).
- Cumple el criterio de aceptación de la incidencia: el apartado explícito de
  lo que NO queda demostrado, que la v1 no traía.
- Encontró por su cuenta la investigación previa del propio repositorio y la
  citó con su calificación correcta («decisión provisional, no verificada en
  vivo»).

## Lo que ChatGPT sigue haciendo mejor

- Más cuerpo total (50 contra 28 KB) y una matriz de puntuación con pesos.
- Análisis de letra pequeña (privacidad, términos de uso) que la v2 no aborda.
- El diseño de un «bake-off» reproducible como siguiente paso.

## Lo que la v2 hace MEJOR que ChatGPT

- 204 fuentes listadas contra ~23 citas.
- La autocrítica: ChatGPT afirmó nombres de modelo que estaban muertos al día
  siguiente (medido, ADR-095) sin ninguna advertencia; la v2 declara sus
  contradicciones y remite el estado vivo al atestado, no a sí misma.
- Se repite gratis y bajo nuestras reglas (fuentes obligatorias, caducidad
  declarada, ciclo de revisión).

## Veredicto del examen

**Sirius pasó de un 35–45 % a un ~75 % del criterio en un día.** Al borde del
80 % pedido: lo que falta no es fiabilidad —ahí la v2 ya es más honesta que el
patrón— sino cuerpo analítico (matriz de puntuación, letra pequeña, diseño de
experimentos). Ese tramo no es de configuración: pediría o un modelo aún mayor
o una segunda pasada de redacción, y ambas cosas se pueden medir con el mismo
banco y este mismo examen.

## Una aclaración para no liarse

El informe v2 recomienda «Gemini como proveedor principal SI se paga», y Sirius
funciona hoy con NVIDIA gratis. No es contradicción: son dos preguntas. La
operativa —¿qué corre HOY, gratis, nuestro volumen?— la contestó el banco
(ADR-098: Google gratuito no completó ni una pregunta). La de mercado —¿a quién
pagarle SI un día se paga?— la contesta este informe, y su respuesta queda
guardada para ese día. Ninguna de las dos decide gastar dinero: eso es del
propietario.

## Contabilidad del mes (buscador)

Gasto estimado de Tavily a 28-08: ~250–300 créditos de 1.000. El contador se
repone el día 1. Una investigación profunda son ~40–60; una pasada del banco,
~30.

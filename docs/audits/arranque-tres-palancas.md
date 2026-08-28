# Nota de arranque — las tres palancas del examen

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).
Orden del propietario: «dale con las tres y me traes la comparación».

## Lo medido que motiva

Primer examen lado a lado (incidencia #389 contra la investigación profunda de
ChatGPT que el propietario trajo): Sirius hoy está en un 35–45 %, no en el 80 %
que el propietario fijó como criterio. Las tres carencias con palanca conocida:

1. **Idioma**: el informe salió en inglés. `LANGUAGE` por defecto es "english"
   en la 0.15.1 (leído en `config/variables/default.py`).
2. **Profundidad**: una sola pasada (`research_report`, TOTAL_WORDS=1200 por
   defecto). La herramienta trae el modo por capas NATIVO:
   `report_type="deep"` (breadth 3 × depth 2, leído en `agent.py` y
   `skills/deep_research.py`).
3. **Modelo**: `nemotron-3-nano-30b` es el pequeño de su familia. El catálogo
   real de la misma clave tiene 84, incluidos `nemotron-3-super-120b-a12b`,
   `deepseek-v4-pro-0813` y `gpt-oss-120b`.

## Lo que se decide construir

- `LANGUAGE: "spanish"` y `TOTAL_WORDS: "2500"` en la configuración (afecta
  también al banco: respuestas más largas, mismas reglas).
- Las órdenes (`investigar_orden.py`) pasan a `report_type="deep"`; **el banco
  se queda en `research_report`**: mide la tubería con 7 preguntas cortas, y
  hacerlas profundas multiplicaría el gasto sin medir mejor. El tipo entra por
  argumento `--tipo` con el valor de cada camino explícito en su llamador.
- El modelo se elige por PRUEBA DE VIDA (preflight `--probar`, tres candidatos
  lanzados) y se confirma con el BANCO: si el elegido no da 7/7, se prueba el
  siguiente. Nada se adopta por catálogo (ADR-095).
- Plazos del ejecutor de órdenes: trabajo 45 min (≤ 85, ventana del contador),
  paso 40, guion 2280 s, hijo 0,9×. El de dentro siempre antes que el de fuera.

## Las cuatro preguntas

1. ¿`--tipo` llega DE VERDAD al hijo? (el arnés captura argv del hijo real)
2. ¿El banco sigue en `research_report`? Si el banco se volviera profundo por
   accidente, sus 7 preguntas costarían ~10× y el número cambiaría de
   significado sin que nadie lo decidiera.
3. ¿El idioma y las palabras llegan al entorno del hijo? (retrato del entorno)
4. ¿El modelo elegido da 7/7 en el banco ANTES de usarse en una orden?

## Criterio de parada

- (a) Presupuesto de buscador: cada pasada profunda son ~60–100 créditos de los
  1000/mes de Tavily. Si el plan fuera a pasar de ~300 créditos hoy, se para y
  se le dice al propietario cuánto queda.
- (b) Si ningún candidato grande da 7/7, se queda el nano y la comparación se
  hace igual con las otras dos palancas: no se adopta un modelo que el banco
  no haya visto aprobar.
- (c) Ningún tope de trabajo por encima de 85 minutos.
- (d) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco de preguntas, ni fuentes>0, ni el atestado, ni el protocolo del
ciclo. El examen final compara contra el documento de ChatGPT YA guardado: no
se le pide al propietario ninguna investigación nueva.

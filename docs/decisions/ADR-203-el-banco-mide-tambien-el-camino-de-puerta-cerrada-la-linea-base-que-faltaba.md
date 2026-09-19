# ADR-203 — El banco mide tambien el camino de puerta cerrada: la linea base que faltaba

- Estado: PROPUESTO
- Fecha: 2026-09-19
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Nota de arranque (escrita ANTES del primer commit)

Las cuatro preguntas de ADR-001, respondidas antes de tocar nada.

1. **¿Dónde vive el hueco y dónde va el arreglo?** El hueco vive en el
   **instrumento**, no en el sistema medido: `_ejecutar_banco_paquete_completo`
   (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) clava
   `category_matching_enabled=True` en los dos colaboradores, así que el banco
   de 47 casos solo sabe medir el camino ABIERTO. El arreglo va exactamente
   ahí: un parámetro de palabra clave en el arnés y una bandera en
   `scripts/diagnosticar_busqueda_del_banco.py`. El sitio del arreglo **sí**
   puede observar lo que arregla: la ausencia de la cifra de puerta cerrada se
   observa corriendo el propio guion y viendo que no hay forma de pedirla.
   Producción (`rank_relevant_knowledge.py`, `context.py`,
   `composition_root.py`, `memory_gates.py`) **no se toca**: si hiciera falta
   tocarla, esto para con `BLOCKED_BY_DECISION`.
2. **¿Qué NO garantiza esto?** (a) No abre ni cierra ninguna puerta real: los
   valores por defecto de `memory_gates.py` y `settings.json` siguen intactos.
   (b) No dice que el motor «aporte X»: da el minuendo que faltaba, y la resta
   la hace quien registre el umbral de D7 punto 6. (c) La cifra de puerta
   cerrada **no es comparable** con una de puerta abierta sacada con
   `--peticion`, `--ejes` o `--cupo`: en el camino cerrado
   `_rank_via_current_pipeline(query_text)` solo recibe el texto, no hay
   `Peticion`, y esas tres palancas no pueden influir. Por eso el guion
   **rechaza** la combinación en vez de imprimir un número engañoso. (d) No
   mide latencia, ni con Ollama, ni el banco de `test_local_performance.py`.
3. **Criterio de parada (decidido antes de ver ningún resultado).** Paro y no
   sigo empujando si ocurre cualquiera de estas: (i) el recuento del banco con
   `--peticion` deja de ser `17/47; 162; 78/81; 0` después del cambio —eso
   sería haber movido el comportamiento de hoy, que es justo lo que el
   parámetro promete no mover—; (ii) para que el modo nuevo dé un número hace
   falta tocar `src/sirius/application/` o `composition_root.py`
   (→ `BLOCKED_BY_DECISION`); (iii) dos rondas de revisión con defectos de la
   misma familia (ADR-001 §2) → buscar la raíz, no parchear.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** El fallo temido es
   publicar una cifra de puerta cerrada contaminada por banderas que allí no
   pueden actuar. Lo que lo hace imposible no es una nota al pie: es el
   rechazo con código de salida distinto de 0 **antes de medir nada**, con su
   prueba (`tests/automation/test_diagnosticar_busqueda_del_banco.py`). Lo que
   queda solo improbable es que alguien copie a mano una cifra vieja a un
   documento; contra eso solo hay la regla de escribir el comando al lado.

### Predicción, publicada ANTES de medir

No conocemos ninguna de las cuatro cifras del camino cerrado. Escribo lo que
espero y por qué; si sale distinto se registra tal cual y **no** se ajusta la
predicción después de verla.

El camino cerrado es `_rank_via_current_pipeline`: FTS5 + asunto + proyecto
activo, sin índice de categoría, sin índice de criticidad y **sin siembra**.
La comparación honesta es contra la puerta abierta **sin banderas** (ADR-148:
`0/47; 487; 72/81; 0`), que comparte condición —ninguna petición declarada—.

- **Aciertos exactos: 0/47.** Sin siembra y sin categoría es aún más difícil
  clavar el conjunto exacto que con ella; la puerta abierta ya saca 0.
- **Elementos de más: bastantes menos que 487**, en el orden de 150-350. La
  siembra por categoría es lo que mete ruido a paletadas en el camino abierto.
- **Hallados: menos de 72/81**, en el orden de 50-70. Lo que la siembra añade
  de ruido también añade aciertos; al quitarla se pierden algunos.
- **Omisiones críticas: > 0**, probablemente entre 1 y 6. Es la cifra que más
  me inquieta y la razón de medirla: el índice de criticidad
  (`solo_por_criticidad`) solo existe en el camino abierto, así que la puerta
  cerrada no tiene quien rescate una crítica que el orden no alcanza.

## Contexto y problema

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué

## La lección

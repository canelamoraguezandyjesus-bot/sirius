# ADR-060 — Un error del conector no es silencio, y no debe costar el plazo entero

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: dos paradas de bloque por «timeout de Codex» (#193 y #232)
- Relacionadas: ADR-036 (una lectura caída no es una ausencia), contrato §4.1 (revisión dual)

## Contexto y problema

Dos bloques se detuvieron por «Codex no entregó un resultado identificable
dentro del plazo». La segunda vez, en la PR #233, se miró el historial en vez de
reintentar, y resultó que **Codex sí había contestado**:

```
15:54:29  nosotros: «@codex review»
15:58:37  chatgpt-codex-connector[bot]:
          «Codex Review: Something went wrong. Try again later by
           commenting "@codex review".»  +  ```Unknown error```
16:14:35  nuestro ciclo: «Codex no entregó un resultado identificable
          dentro del plazo absoluto de 1200 segundos» → FAILED_SAFELY
```

Contestó en **4 minutos**, y contestó un fallo suyo que además decía qué hacer.
Esperamos 20 y luego afirmamos que no había contestado. Se perdieron 16 minutos
y una ronda entera.

Es la familia de **ADR-036** —«una lectura caída no es una ausencia»— en un
sitio nuevo: aquí se confundió **una respuesta de fallo** con **silencio**, y el
diagnóstico que se publicó en la incidencia era literalmente falso.

## Criterio de parada (escrito ANTES de decidir)

> El arreglo vale solo si **no roza la garantía de que nunca se aprueba sobre el
> silencio de un revisor**. Esa es la razón de ser de la revisión dual. Si para
> ganar 16 minutos hubiera que tocar los plazos, aprobar con un solo revisor, o
> reintentar de forma que dos respuestas puedan confundirse, no compensa: se
> deja como está y se documenta.

## Opciones consideradas

1. Alargar el plazo. No arregla nada: el problema no era la espera.
2. Aprobar con un solo revisor cuando el otro falla. Rompe la revisión dual.
3. Reintentar automáticamente publicando un segundo `@codex review`.
4. **Ver el error**: reconocerlo como respuesta terminal y parar en el acto.

## Decisión

**La cuarta**, y nada más que la cuarta.

La causa no era «el mensaje es ambiguo»: era que **el recolector no lo veía**.
En `_check_conversation_comments`, el filtro de SHA corría **antes** de leer el
texto:

```python
declared_sha = _resolve_review_sha(comment)
if declared_sha is None or not _sha_matches(head, declared_sha):
    continue          # ← el error moría aquí, sin llegar a leerse
```

Los mensajes de fallo no traen `Reviewed commit:`, así que `_resolve_review_sha`
devolvía `None` y se descartaban como candidatos. **Eran invisibles, no
ambiguos.**

Se añade `_declara_fallo_del_conector`, que se consulta **antes** de ese filtro
y produce una parada inmediata con motivo `codex-fallo-declarado` — o, desde
ADR-146, `codex-fallo-declarado-transitorio` para el único prefijo cuyo texto
pide el reintento, que el agregador re-arma con el candado de ADR-141 — y el mensaje
real dentro.

**Lo que NO se toca, y es deliberado:**

- Los plazos siguen igual.
- No se aprueba nunca con un solo revisor.
- **No se reintenta.** El recolector sigue sin publicar nada —no tiene el código
  ni el PAT para hacerlo— y `_post_count == 0` sigue fijado por prueba.
  Reintentar es abrir una ronda nueva, y eso ya funciona hoy: volver a aplicar
  la etiqueta produce otro `round_id` y su propio disparador. Lo que cambia es
  que ahora se sabe **en 4 minutos** que hay que hacerlo, en vez de en 20.

## Comprobación que la sostiene

### Las cuatro formas de fallo salen del historial, no de suponerlas

Se recorrieron **las 21 PR** en las que ha comentado el conector:

| Prefijo | Casos | Latencia observada |
| --- | --- | --- |
| `Codex Review: Something went wrong.` | 2 (#122, #233) | 4 m 08 s · 5 m 44 s |
| `You have reached your Codex usage` | 1 (#139) | 7 s |
| `To use Codex here,` | 1 (#124) | 12 s |
| `Codex couldn't complete this request.` | 2 (#122) | canal de tarea |

Los dos cuerpos de la primera son **idénticos byte a byte** (578 caracteres).
Con n=2 no está probado que el bloque interior diga siempre «Unknown error», así
que se reconoce **el prefijo**, que sí es estable, y no el cuerpo entero.

Y todas contestan **rápido**: ninguna se acercó al plazo. El plazo nunca fue el
problema.

### Que la forma C es terminal, comprobado

En la PR #233, sobre el mismo head, tras el error de las 15:58:37 **no hubo
absolutamente nada más** —ni comentario ni revisión— hasta que se volvió a
disparar a las 16:18:19. Los 20 minutos de espera fueron silencio real. Esperar
más no lo iba a cambiar.

### Las mutaciones

| Mutación | ¿La caza? |
| --- | --- |
| Quitar la lectura del fallo (el defecto original) | sí — **12 pruebas** |
| Reconocer de más: cualquier comentario del conector cuenta como fallo | sí — 10 pruebas |
| Dejar el motivo como `timeout` en vez de nombrar la causa | sí — 2 pruebas |

La segunda es la que importa para el criterio de parada: **un reconocedor ancho
pararía rondas sanas**, y es el único daño que este cambio podría causar. Hay
una prueba en esa dirección (`..._no_llama_fallo_a_una_revision_normal`).

### Validaciones

```
uv run ruff format --check .   -> 454 files already formatted
uv run ruff check .            -> All checks passed!
uv run mypy src tests          -> Success: no issues found in 432 source files
uv run pytest tests/automation -> 594 passed, 3 skipped
git diff --check               -> limpio
```

## Consecuencias

- Un fallo del conector cuesta **4 minutos**, no 20.
- El diagnóstico que llega a la incidencia deja de ser falso: en vez de «no
  contestó» dice qué contestó y qué hacer.
- Reanudar sigue siendo un gesto de quien aplica la etiqueta, no del recolector.

## Alternativas descartadas y por qué

**Alargar el plazo.** Habría empeorado el caso que motivó todo: más espera para
el mismo desenlace. Y alarga todas las rondas de todos los bloques.

**Aprobar con un solo revisor.** Rompe la única garantía que la revisión dual
aporta. El criterio de parada lo prohibía por adelantado.

**Reintentar automáticamente.** Es tentador y quizá llegue, pero abre preguntas
que este cambio no necesita responder: qué pasa si la respuesta del primer
disparo llega después del segundo, cómo se identifica cuál vale, cuántos
reintentos. Hoy el reintento existe y funciona —volver a aplicar la etiqueta—, y
lo que faltaba era **saber a tiempo que hacía falta**. Eso es lo que se arregla.

## Un hallazgo adyacente, dicho y no arreglado

Al leer el módulo apareció que un comentario cita «el consumo duplicado que el
contrato prohíbe (§6.7)», y **§6.7 no existe**: el §6 del contrato no tiene
subsecciones. La razón genérica sí está en §6; lo que no existe es esa cita
concreta. No se corrige aquí porque está fuera del alcance de este cambio, y es
de la misma familia que la guarda de citas de ADR-052 —una referencia que nadie
puede abrir— pero en código en vez de en un ADR.

# Verificación de la auditoría externa del 28-08-2026

Encargo del propietario: «lee, mira y verifica esto», sobre el informe
`SIRIUS_INFORME_AUDITORIA_PARA_CLAUDE_20260828.docx` (7 hallazgos: 6 SERIOUS,
1 MINOR; snapshot del informe a256688, revalidado aquí sobre c191f91).

Método (el que exige el propio informe y ADR-001): para cada hallazgo,
localizar la evidencia actual, INTENTAR REFUTARLO, y clasificar. Criterio de
parada, fijado antes de mirar: un hallazgo solo se confirma si la cadena
completa se lee en el código de HOY; si cualquier eslabón no está, se declara
REFUTADO o NO VERIFICABLE con el eslabón exacto. Sin correcciones: la fase 7
requiere autorización del propietario.

## Tabla de veredictos

| ID | Veredicto | Evidencia exacta (HEAD c191f91) |
|---|---|---|
| F-3.1-01 | **CONFIRMADO** | `run.py`: `mark_lost` (LIVE→FINISHED/LOST) conserva `cancellation_status=UNCONFIRMED`; `has_unconfirmed_cancellation` exige `estado in LIVE_STATES` → False tras LOST. La ÚNICA exclusión del recurso mutable (`_conflicting_unconfirmed_cancellation`, durable:960-976 y memoria:392-411) se apoya en esa propiedad; `retry` acepta cualquier FINISHED salvo invalidación por alcance. Cadena completa: un Worker quizá vivo deja de bloquear al sustituto. |
| F-3.1-02 | **CONFIRMADO** | `durable/store.py`: `prepare_run` (921-952) no comprueba que el WorkItem padre exista ni que no sea terminal; `deliver_work_item` (692-707) no mira si hay Runs vivos. Igual en `memory_store.py`. Las dos direcciones del invariante sin guarda. |
| F-3.2-01 | **CONFIRMADO** | `implement-sirius-work.yml`: `sed -n 's/^Perfil: *\([A-Za-z_-]*\)@.*/\1/p'` tira la versión, y `cat scripts/automation/prompts/<rol>.md` lee el fichero VIGENTE de main. `implementer@1` puede significar dos textos distintos en dos Runs. (Aplica igual al ejecutor de investigación y al revisor, que copian el patrón.) |
| F-3.3-01 | **CONFIRMADO** | `dispatcher.py` 202-223: `crear_incidencia` → `aplicar_etiqueta` → `journal.record`, y `except BaseException: journal.liberar`. Un fallo entre el efecto en GitHub y el registro durable deja el diario sin episodio: el reintento crea SEGUNDA incidencia. La concurrencia del workflow no cubre el caso caída-y-reintento. |
| F-3.5-01 | **CONFIRMADO** | `budget.py`: `has_remaining_budget()` (lectura) y `_record_cost` (escritura) son operaciones separadas; el lock protege cada una, no la secuencia comprobar-gastar, y no existe reserva. Dos peticiones concurrentes al borde del tope pasan las dos. |
| F-3.6-01 | **CONFIRMADO, con matiz** | `sirius_merge_on_command.sh` 146-151: `|| behind_by=""` y solo bloquea número > 0; el comentario documenta el fail-open a propósito, y `test_sirius_merge.py` (~563) FIJA ese comportamiento con su motivo escrito («el error cae del lado de seguir»). El comportamiento existe tal cual lo describe el informe; el matiz es que aquí no hay descuido sino una DECISIÓN tomada, que el auditor impugna con un argumento serio (las demás lecturas materiales del guion fallan cerradas). Resolverla es fase de corrección, no de verificación. La afirmación sobre el ruleset (strict=false) no se verificó desde esta sesión; no cambia el veredicto del guion. |
| F-3.9-01 | **CONFIRMADO** | `STATUS.md`:26 «Sirius 0.1 todavía debe terminarse y aceptarse» contra `PLAN.md`:11-12 «ACEPTADO y TERMINADO el 10-08-2026». Contradicción literal entre fuentes activas. |

Ningún hallazgo quedó refutado. Los siete pasan al registro de defectos como
H-26…H-32, todos apuntando a la incidencia de seguimiento de esta auditoría.

## Matices de riesgo que la fase de corrección debe tener delante

- F-3.1-01/02 y F-3.3-01 golpean el camino de AUTONOMÍA del motor (D1): hoy el
  motor no es autoridad de ninguna clase, así que la ventana existe pero su
  superficie operativa actual es pequeña. Corregirlos es CONDICIÓN para D1.
- F-3.6-01 afecta a fusiones de HOY: es el de mayor superficie inmediata.
- F-3.5-01 es del producto de escritorio (guardia de dinero); F-3.9-01 es una
  línea de documentación.
- El orden recomendado del informe (3.1-01 → 3.6-01 → 3.3-01 → 3.5-01 →
  3.1-02 → 3.2-01 → 3.9-01) es razonable; con la superficie de hoy delante,
  también sería defendible empezar por F-3.6-01.

## Lo que NO se hizo

Ninguna corrección, ningún cierre, ningún cambio de comportamiento: el propio
informe lo prohíbe sin autorización del propietario, y la casa también.

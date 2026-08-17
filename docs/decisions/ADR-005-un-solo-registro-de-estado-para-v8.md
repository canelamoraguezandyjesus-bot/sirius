# ADR-005 — Mantener el estado de V8 en un único registro que la automatización pueda escribir

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

Tres documentos guardan cada uno una copia completa del estado de V8, y el 10
de agosto de 2026 dicen tres cosas distintas. Comprobado contra `main`
(`158dd70`), no contra otros documentos:

| Afirmación | Dónde | Realidad en `main` |
|---|---|---|
| `B4 \| En curso (B4f implementado, PR pendiente de revisión y merge)` | `V8_EXECUTION.md` tabla de bloques | `src/sirius/presentation/knowledge_widget.py` y `src/sirius/application/knowledge_overview.py` existen y están fusionados |
| `B5 \| Pendiente` | `V8_EXECUTION.md` tabla de bloques | `src/sirius/presentation/context_panel_widget.py` fusionado en la PR #79 |
| `D-05, D-06, D-08, D-09, D-11 \| Abierto` | `V8_EXECUTION.md` catálogo | La tabla de bloques **del mismo archivo**, 15 líneas más abajo, los da por cerrados |
| Correcciones de V8.1 terminan en B3b | `PLAN.md` | B4, B5, B6, B7, B8, B9, B10 y B11 están fusionados |

La contradicción entre el catálogo y la tabla de bloques vive dentro de un
mismo archivo. No es un despiste de sincronización entre repositorios: es que
el mismo hecho está escrito cuatro veces y nadie actualiza las cuatro.

### La raíz

*¿Puede el sitio del arreglo observar el fallo que arregla?* Aplicada aquí: el
implementador automático **no puede escribir `REPOSITORY_STATUS.md`**.
`.claude/settings.json` solo permite `Edit`/`Write` sobre `./src/**`,
`./tests/**`, `./migrations/**` y `./docs/implementation/**`; los archivos de
la raíz no están en la lista. El propio `REPOSITORY_STATUS.md` lo reconoce:

> Los documentos de raíz o de operaciones que el agente automático no pueda
> modificar se sincronizan en una PR documental posterior al merge.

Es decir: cada bloque que se fusiona deja obsoleto un documento que el agente
que lo fusionó tenía prohibido tocar, y la PR documental de sincronización
depende de que alguien se acuerde. **La deriva no es un accidente, es el
comportamiento por diseño de la disposición actual.** Actualizar los tres
documentos a mano hoy no arregla nada: vuelven a divergir en el bloque
siguiente.

## Criterio de parada (escrito ANTES de decidir)

- Si al verificar bloque por bloque contra `main` aparece **un solo bloque**
  cuyo estado real no pueda determinarse leyendo el código y las pruebas,
  se detiene la reconciliación y se pregunta al propietario en vez de
  escribir un estado deducido.
- Si eliminar el estado duplicado de un documento de raíz obliga a cambiar
  `AGENTS.md`, `CLAUDE.md` o cualquier documento canónico, se detiene: eso
  es una decisión de gobierno, no una reconciliación.
- Si la prueba que fija la regla pasa igual con la regla violada, no se sube:
  se retira y se dice.

## Opciones consideradas

1. **Actualizar los tres documentos a mano.** Es lo que se ha hecho hasta
   ahora. Arregla el síntoma de hoy y garantiza el de la semana que viene.
2. **Permitir que la automatización escriba los documentos de raíz.** Amplía
   los permisos del agente sobre archivos que incluyen `AGENTS.md` y
   `CLAUDE.md` si se hace por patrón, y es exactamente lo que ADR-002 acotó.
3. **Un solo registro autoritativo, dentro de `docs/implementation/`.** El
   estado vive donde el agente ya tiene permiso; el resto de documentos
   apuntan a él en vez de copiarlo.

## Decisión

Se adopta la opción 3.

`docs/implementation/V8_EXECUTION.md` es el **único registro autoritativo** del
estado de los bloques de V8 y del catálogo de defectos. `PLAN.md` y
`REPOSITORY_STATUS.md` dejan de contener estado por bloque y por defecto: lo
enlazan.

Dentro de `V8_EXECUTION.md`, el catálogo de defectos deja de declarar estado
propio. El estado de un defecto es el del bloque que lo cierra, y se lee en una
sola tabla. Dos tablas del mismo hecho fue la causa de la contradicción interna
descrita arriba.

## Comprobación que la sostiene

Verificado archivo por archivo contra el árbol de `main`, no contra
documentos:

```
OK   application/save_manual_memory.py      OK   domain/precedence.py
OK   application/memory_origin.py           OK   application/knowledge_overview.py
OK   application/propose_decision.py        OK   presentation/knowledge_widget.py
OK   application/approve_decision.py        OK   presentation/context_panel_widget.py
OK   application/correct_memory.py          OK   adapters/persistence/sqlite_knowledge_search_repository.py
OK   application/supersede_decision.py      OK   application/rank_relevant_knowledge.py
OK   application/archive_memory.py          OK   domain/relevance.py
OK   application/delete_memory.py           OK   presentation/error_messages.py
OK   application/archive_decision.py        OK   application/export_structured.py
                                            OK   adapters/export/filesystem_export_service.py
```

Y en `tests/integration/`: `test_manual_memory_origin.py`,
`test_decision_lifecycle.py`, `test_decision_supersession_explicit.py`,
`test_memory_correction_lifecycle.py`, `test_memory_archive_delete_lifecycle.py`,
`test_fts5_availability.py`, `test_export_structured.py`,
`test_forced_shutdown_recovery.py`.

La regla queda fijada por `tests/unit/test_documentation_single_source.py`,
verificada por mutación en las dos direcciones (ver la sección de consecuencias).

## Consecuencias

- Un bloque fusionado actualiza **un** archivo, y es uno que el implementador
  automático puede escribir. Desaparece la PR documental de sincronización
  posterior al merge.
- `REPOSITORY_STATUS.md` y `PLAN.md` siguen describiendo qué es cada cosa y
  cómo se trabaja; dejan de afirmar en qué punto está.
- Una prueba unitaria falla si un documento de raíz reintroduce estado por
  bloque. Sin ella esto sería una convención, y las convenciones son
  exactamente lo que ha fallado aquí durante ocho bloques.

## Lo que esto NO garantiza

Escrito antes de implementarlo, no como excusa después:

- **No comprueba que la tabla diga la verdad.** Comprueba que el estado esté
  en un solo sitio. Una tabla única y equivocada pasa la prueba.
- **No cubre `docs/audits/` ni `docs/evolution/`**, que son registros fechados
  y deben quedar congelados.
- **No impide** que alguien vuelva a describir el progreso en prosa dentro de
  un documento de raíz si evita las formas que la prueba reconoce.

## Alternativas descartadas y por qué

- **Opción 1** (actualizar a mano): descartada porque no toca la raíz. Es la
  que produjo el estado actual.
- **Opción 2** (ampliar permisos): descartada. ADR-002 acotó deliberadamente
  lo que la automatización puede escribir, y la raíz contiene `AGENTS.md` y
  `CLAUDE.md`. Ampliar el permiso para arreglar un problema de duplicación
  cambia la frontera de confianza por un motivo que no lo justifica.
- **Generar los documentos de raíz desde la tabla** con un script: descartada
  por ahora. Añade un generador, un formato intermedio y un paso de CI para
  un problema que se resuelve con un enlace.

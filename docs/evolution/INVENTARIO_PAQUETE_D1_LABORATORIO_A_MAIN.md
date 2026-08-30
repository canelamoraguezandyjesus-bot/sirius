# Inventario del paquete D1: del laboratorio (`evidence/adr001-spikes`) a `main`

Incidencia #459 (Work ID `WI-20260830-170933`). Este documento es **inventario, no
autorización**: no cambia ninguna decisión ni activa nada. Existe para que nunca más se
descubra por sorpresa una pieza del laboratorio que el paquete D1 necesitaba — ya pasó dos
veces: el tratamiento léxico de consultas que ningún documento enumeraba (incidencia #455,
diagnosticado como ADR-108 pero sin existir ese ADR en el registro — véase
[Nota sobre ADR-108](#nota-sobre-adr-108) más abajo) y los campos de petición por caso del
banco (ADR-110, borrador sin fusionar).

## 0. Qué es el paquete D1, y cómo se construyó este inventario

**D1** es la decisión del propietario registrada en
`docs/evolution/STATUS.md:156-179` («Decisiones del propietario registradas el 29 de agosto
de 2026», fuente `sesion-cli` Work ID `WI-20260829-123248`): incorporar a `main`, completa,
la evidencia de la rama `evidence/adr001-spikes` (PR #117, abierta y sin fusionar como
archivo) — el índice de categoría determinista **y** el filtro de relevancia con modelo
local vía Ollama —, mediante encargos nuevos que porten ese trabajo como código de producto
con sus pruebas, nunca por fusión directa de la PR. `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:606-636`
traduce esa decisión a los encargos M7–M12 (§8).

**Comparación hecha a máquina.** `git show`/`git ls-tree` sobre:

- Laboratorio: `origin/evidence/adr001-spikes` en el commit `dfdcdaff04dcba10939cc0b0569c55b6a636296f`
  (tip de la rama en el momento de este inventario), directorio `experiments/adr002/`,
  excluidos `experiments/adr002/artifacts/` y `experiments/adr002/docs/` (se mencionan como
  categoría, no se enumeran fichero a fichero — ver [§1.6](#16-artefactos-de-medición-evidencia-congelada)).
- `main` en el commit `5c593b55c281c57573c59a04d9cf93efecd4be45` (el mismo commit que cita
  `tests/acceptance/fixtures/evidence_bank_47_casos.json:5` como fuente, coincidencia
  verificada, no asumida).
- La PR abierta #458 (rama `feature/457-motor-por-etapas-portado-adr109`, **sin fusionar**)
  se leyó también, porque contiene trabajo ya escrito pero todavía no incorporado a `main` —
  necesario para no declarar «no existe» algo que ya está escrito y en revisión.

**Cada afirmación comprobable cita fichero y línea.** Donde una cita de un ADR existente no
coincidió con lo que este inventario verificó directamente sobre el código, se declara la
discrepancia en vez de repetir la cita sin comprobar (ver
[Nota sobre una cita desactualizada en ADR-110](#nota-sobre-una-cita-desactualizada-en-adr-110)).

**Alcance de la tabla.** El objetivo de la incidencia nombra explícitamente:
`candidates/adr002_a/`, `candidates/common/`, `benchmark/cases_v0_5.json` y
`references_v0_5.json` y su familia vigente, `round/cases.py`, el arnés de medición que
produjo las cifras de D1, los candidatos B/C/D descartados, la ampliación descartada, y los
artefactos de medición. La tabla cubre exactamente eso. Otros subdirectorios de
`experiments/adr002/` (`cards/`, `rederivation/`, `storage/`, `tolerances/`, `t0_control/`)
pertenecen a otras piezas de ADR-002 no relacionadas con el paquete de recuperación medido
aquí y se listan solo como exclusión declarada, no fichero a fichero. `projection/` es la
excepción: `projection/contracts.py:referencia_canonica` sí es parte del paquete D1 —
`docs/decisions/ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md:58-68`
la usa explícitamente para filtrar `resultado_esperado` a identidades del canon (`MEM-`/
`DEC-`, excluyendo `DOC-`/`MSG-`) al reconstruir los 81 elementos esperados del banco
portado — y se enumera fichero a fichero en [§1.5](#15-candidatos-descartados-y-mecanismos-no-adoptados),
separada del resto de `projection/`.

## 1. Tabla de inventario

Leyenda: **PORTADO** (vive en `main`, cita el fichero y la PR que lo trajo) · **PENDIENTE**
(no vive en `main` hoy; si ya está escrito en una PR abierta sin fusionar, se cita) ·
**NO SE PORTA** (decisión ya tomada, con su porqué y su fuente) · **PENDIENTE DE CONFIRMAR**
(ningún ADR ni PR fusionada nombra la pieza ni para portarla ni para excluirla; este
inventario razona una hipótesis técnica pero no la trata como decisión, y la deja para que
el propietario la confirme o la corrija).

### 1.1 Candidato A y tratamiento léxico (`candidates/adr002_a/`)

| Módulo / pieza del laboratorio | Estado | Dónde vive en `main` / PR |
|---|---|---|
| `lexical.py` — `VACIAS`, `plegar`, `tokenizar`, `terminos_significativos`, `raiz` (`RAIZ_MINIMA=4`), `variantes` (`lexical.py:26-219`, rama `evidence/adr001-spikes`) | **PORTADO** | `src/sirius/adapters/persistence/lexical_query_treatment.py:31-186` — PR #456 (fusionada, commit `c6e34a3`/`5c593b5`) |
| `lexical.py` — `MARCADORES_NEGACION` (115-126), `MARCADORES_CONDICION` (128-163), `polaridad_negativa` (222-274), `condicion_declarada` (276-286), `sujeto_estructural` (288-298), `solapamiento`/`comparten_estructura` (300-316), `ordenar_estable` (318-329) | **PENDIENTE** | Escrito en PR #458 (rama `feature/457-motor-por-etapas-portado-adr109`, **abierta, sin fusionar**), que amplía el mismo `lexical_query_treatment.py` con `MARCADORES_NEGACION`, `MARCADORES_CONDICION`, `polaridad_negativa`, `condicion_declarada`, `sujeto_estructural`, `ordenar_estable`. No está en `main` hoy (verificado: `grep -n "^def " src/sirius/adapters/persistence/lexical_query_treatment.py` solo devuelve `plegar`, `tokenizar`, `terminos_significativos`, `raiz`, `variantes`). |
| `candidate.py` — `CandidatoA` (`candidate.py:68-345`) | **PENDIENTE** | Escrito en PR #458 como `sirius.adapters.persistence.staged_engine_candidate` (nombre citado en el propio diff de la PR); no existe en `main` (`git ls-tree HEAD -- src/sirius/adapters/persistence/ | grep staged` no devuelve nada). |

### 1.2 Capa común (`candidates/common/`)

| Módulo | Estado | Dónde vive en `main` / PR |
|---|---|---|
| `contracts.py` (686 líneas: `Peticion`, `Candidata`, `ItemCanonico`, `EjesDeclarados`, `PlanoComun`, ...) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine_contracts` (no fusionada). |
| `gates.py` (406 líneas: `_g1`..`_g10` líneas 100-287, `aplicar_previas` 292-303, `aplicar_g11` **306-323**, `aplicar_g12` 356+) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine_gates` (no fusionada). Las doce puertas `G1-G12`. |
| `grouping.py` (248 líneas: `deduplicar_por_identidad:84`, `agrupar_equivalentes:170`) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine_grouping` (no fusionada). |
| `stops.py` (172 líneas: criterios de parada `S1`-`S7`, `evaluar_suficiencia:71`) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine_stops` (no fusionada; dependencia directa de `engine.py`, no nombrada por separado en el objetivo de la incidencia #457 pero necesaria para que el motor funcione, según el propio borrador de ADR-110). |
| `trace.py` (308 líneas: `Traza`, `explicar:213`, `fallos_de_minimizacion:264`) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine_trace` (no fusionada; misma razón que `stops.py`). |
| `engine.py` (400 líneas: `recuperar:134`, motor por etapas `E0`-`E5`) | **PENDIENTE** | PR #458 → `sirius.domain.staged_engine` (no fusionada). |
| `port.py` — `PuertoSqlite.por_termino_lexico` (`port.py:434-455`): el **mecanismo** (citar variantes de FTS5 y combinarlas con `OR` contra `knowledge_fts`) | **PORTADO** (el mecanismo, no el módulo) | Reescrito, literal en su lógica, dentro de `sanitize_fts5_query` — `src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py:27-64` — PR #456 (fusionada). El docstring de `lexical_query_treatment.py:1-17` documenta esta procedencia. |
| `port.py` — el resto de `PuertoSqlite` (640 líneas: `ConsultaRegistrada`, `RegistroDeConsultas`, resto de métodos de consulta) | **PENDIENTE** | PR #458 → `sirius.adapters.persistence.staged_engine_port` (`PuertoDeRecuperacion`, adaptado al acceso `sqlalchemy.text`/`session_scope` ya existente; no toca el contrato de `KnowledgeSearchRepository`). No fusionada. |
| `derived.py` (inventario/borrado/reconstrucción de las tablas sombra FTS5 del corpus experimental, DDL leído de `sqlite_master`) | **PENDIENTE DE CONFIRMAR** | Infraestructura de reconstrucción específica del corpus experimental del laboratorio: Sirius 0.1 tiene sus propias migraciones canónicas (p. ej. `61be4bb269bf`, citada por el propio `derived.py:11` del laboratorio) y no necesita reconstruir tablas sombra por fuera de Alembic. Pero esto es una inferencia técnica de este inventario, no una decisión ya tomada: ningún ADR ni PR fusionada nombra `derived.py`, ni para portarlo ni para excluirlo, y `docs/evolution/STATUS.md:156-161` pide incorporar D1 de forma completa. Queda señalado como estado no encontrado en el registro de decisiones, para que el propietario lo confirme o lo corrija; este inventario no lo excluye por iniciativa propia. |
| `neutrality.py` (autocomprobación: la capa común no nombra candidatos, no tiene señal vectorial, no coordina espacios tardíos simultáneamente, no abre red) | **NO SE PORTA** | Herramienta metodológica del propio laboratorio para verificar la neutralidad de su capa común entre candidatos A/B/C/D; no aplica a producto, donde no hay «candidatos» compitiendo. |

### 1.3 Banco de casos y su familia (`benchmark/`)

| Fichero | Estado | Dónde vive en `main` / PR |
|---|---|---|
| `cases_v0_5.json` — bloque `instanciacion` (`consulta`, `ambito`, `modo`, `permiso`, `cardinalidad`, `limite`, `tiempo_objetivo` por caso) | **PARCIALMENTE PORTADO** | `consulta` y `ambito` ya extraídos, caso a caso, a `tests/acceptance/fixtures/evidence_bank_47_casos.json` (verificado: el primer caso, `B04-CA-01`, solo trae `id`/`consulta`/`ambito`/`resultado_esperado` — ni `modo`, ni `permiso`, ni `cardinalidad`, ni `limite`) — PR #446 (fusionada), documentado en `docs/decisions/ADR-104-...md:52-61`. `modo`/`permiso`/`cardinalidad`/`limite` — **PENDIENTE**, diagnosticado por el borrador de ADR-110 (PR #458, sin fusionar) como la pieza que falta para reproducir el suelo D1. |
| `references_v0_5.json` — `adjudicacion.dominio.resultado_esperado` | **PORTADO** | `resultado_esperado` en `evidence_bank_47_casos.json` — PR #446, `ADR-104:60-61`. |
| `references_v0_5.json` — `adjudicacion.dominio.limite` (límite duro/objetivo por caso, leído en `experiments/adr002/round/cases.py:349-350` del laboratorio) | **PENDIENTE** | No extraído; PENDIENTE según el borrador de ADR-110. |
| `conformance_corpus_v0_6.json` (97 ítems del canon: id, tipo, proyecto, criticidad...) | **PARCIALMENTE PORTADO** | Los 97 ítems base ya se citan como fuente en `evidence_bank_47_casos.json:5-10` (PR #446); los ejes `ejes_p2` completos (polaridad, condición, ámbito, sensibilidad, autoridad, marcas de no uso, vigencia, procedencia, `property_key`) **no** están en `main` hoy (verificado: `grep -c ejes_p2 tests/acceptance/fixtures/evidence_bank_47_casos.json` → 0). Ese enriquecimiento solo existe en el borrador de PR #458, sin fusionar. |
| `applied_criticality_v0_1.json` | **PORTADO** | `criticidad.razon_segura` en `evidence_bank_47_casos.json` — PR #446, `ADR-104:80,131-133`. Nunca se lee `criticidad.fuente` (contiene un identificador de caso) ni `criticidad.razon` cruda. |
| `property_keys_v0_2.json` | **PENDIENTE** | Solo en el borrador de PR #458 (campo `property_key` por ítem, parte de `ejes_p2`). |
| `schema_v0_5.py`, `build_corpus_v0_5.py`, `validate_corpus_v0_5.py`, `test_corpus_contract_v0_5.py`, `canonical_source_v0_4.py` (reutilizado por `build_corpus_v0_5.py:39`; no existe `canonical_source_v0_5.py`), `benchmark_manifest_v0_5.json` | **NO SE PORTA** | Maquinaria de construcción y validación del corpus experimental. `main` no reconstruye el corpus: lo recibió ya calculado, sin modificar, tal como exige D1 (`ADR-104`). Ningún ADR fusionado ni el borrador de ADR-110 los nombra como pendientes. |

Nota: `cases_v0_5.json` es la última versión de la familia de instanciación de casos —no
existe `cases_v0_6.json` en el laboratorio (verificado por `git ls-tree`)—, así que es la
«familia vigente» que pide el objetivo de la incidencia. Las versiones `v0_6` de
`schema.py`/`build_corpus.py`/`conformance_corpus.json`/`benchmark_manifest.json` sí existen,
pero solo `conformance_corpus_v0_6.json` es citado como fuente por un documento fusionado o
en borrador (`ADR-104`, el borrador de ADR-110); el resto de la familia `v0_6` no se cita en
ningún sitio como relevante al paquete D1 y no se enumera aquí como pendiente por falta de
esa referencia — si el propietario confirma que sí lo es, esta fila debería ampliarse.

### 1.4 Traductor y arnés de medición (`round/`)

| Módulo | Estado | Dónde vive en `main` / PR |
|---|---|---|
| `round/cases.py` — `_traducir` (`cases.py:313-401`, construcción de la `Peticion` en `334-366`) y `CARDINALIDAD_SIN_DECLARAR` (`cases.py:104`) | **PENDIENTE** | Sin destino en `main`. El borrador de ADR-110 (PR #458, sin fusionar) lo identifica como la causa raíz de que la ronda del laboratorio alcance 29/47 y el arnés del banco de `main` (política uniforme, sin petición por caso) no pase de 11/47: «la petición por caso ... `round/cases.py:334-366` (`_traducir`) construye a partir de dos ficheros ... ninguno de esos dos ficheros, ni el traductor que los combina, está entre lo que el alcance permitido de la incidencia #457 autoriza portar». |
| `round/execute_round.py`, `round_protocol.py`, `participants.py`, `metrics.py`, `closure.py`, `levels.py`, `execute_levels.py`, `discriminant.py`, `m2_marking.py`, `readjudication.py`, `execute_m2.py`, `run_round.py` | **NO SE PORTA** | Protocolo y arnés de la «ronda primaria de ADR-002»: preinscripción (`round_protocol.py`), ejecución real con cinco participantes T0 (control, Sirius 0.1 sin motor) + A + B + C + D (`participants.py:32-46`, `execute_round.py`), métricas del §9 (`metrics.py`) y adjudicación de cierre (`closure.py`). Este arnés es el que produjo las cifras que fijaron el suelo D1 (29/47 aciertos exactos, tabla de PR #117). Es maquinaria de medición del propio laboratorio, no código de producto: el banco que corre hoy en `main` (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, PR #446/#456) implementa su **propio** arnés (`rank()`/`_ejecutar_banco`, `test_pa_0_2_rec_01_banco_evidencia.py:227`) contra el pipeline real de Sirius, y no reutiliza estos módulos. Ningún ADR ni PR fusionada lo cita como pendiente de portar — el borrador de ADR-110 cita `round/cases.py` como pendiente, pero no el resto de este grupo. |

### 1.5 Candidatos descartados y mecanismos no adoptados

Fuente principal de esta sección: PR #117 (`ADR-001 aprobado, ADR-002 medido...`, abierta,
sin fusionar como archivo — es evidencia, no código a portar), sección «Descartado con
datos»: *«Fusión híbrida `RRF` (inerte), señal semántica densa (no supera la léxica ni con
modelo de pago), ampliación generada por el modelo al guardar (no aporta; 194 llamadas por
reconstrucción), compuerta sí/no (segura pero casi inerte), y devolver todas las críticas del
ámbito (refutada por el propio banco)»*. El cuerpo de la PR no mapea cada frase a una letra
de candidato explícitamente; este inventario cita, para cada fila, la fuente más precisa
verificada.

| Pieza | Estado | Por qué / fuente |
|---|---|---|
| `candidates/adr002_b/` (`candidate.py`, `candidate_semantico.py`, `codificadores.py`, `semantica.py`, `vectores.py`) — señal semántica vectorial tardía | **NO SE PORTA** | Docstring propio (`adr002_b/candidate.py:1-13`): «`ADR002-B` = `ADR002-A` + señal vectorial tardía». Coincide con «señal semántica densa (no supera la léxica ni con modelo de pago)» de PR #117. `A` ganó la ronda (`round/closure.py`, adjudicación por `B04-M01`/`G12`: una omisión crítica reproducible elimina la alternativa). |
| `candidates/adr002_c/` (`candidate.py`, `relaciones.py`) — señal relacional explícita tardía | **NO SE PORTA** | Docstring propio (`adr002_c/candidate.py:1-13`): «`ADR002-C` = `ADR002-A` + señal relacional tardía». No adoptada por la misma ronda que ADR-001/ADR-002 resolvió en PR #117 a favor de A. |
| `candidates/adr002_d/` (`candidate.py`) — B+C combinadas en etapas tardías distintas con orden congelado | **NO SE PORTA** | Docstring propio (`adr002_d/candidate.py:1-15`). No adoptada. |
| `ampliacion/` (`expansor.py`, `fuente.py`, `medir_ampliacion.py`, `modelo.py`) — ampliar la consulta con el modelo al guardar | **NO SE PORTA** | PR #117: «ampliación generada por el modelo al guardar (no aporta; 194 llamadas por reconstrucción)». `modelo_local/medir.py:29-31` (laboratorio) confirma la cifra: medida dos veces, 23 y 22 aciertos contra una línea base de 24 sin ella. |
| `hibrido/` (`fusion.py` — Reciprocal Rank Fusion, `buscador.py`, `codificador_openai.py`, `medir_con_openai.py`) | **NO SE PORTA** | PR #117: «Fusión híbrida RRF (inerte)». `hibrido/fusion.py:1-12` explica el mecanismo (RRF, Cormack/Clarke/Buettcher 2009) sin medir una mejora que lo justifique. |
| `modelo_local/filtro.py` — modo «compuerta» (el modelo solo dice si hay algo, no elige) | **NO SE PORTA** | PR #117: «compuerta sí/no (segura pero casi inerte)». `modelo_local/medir.py:36-39` (laboratorio): «cero elementos correctos perdidos [...] pero gana poco, 25 y 26 de 47». El **filtro que elige** (no la compuerta) es justamente la pieza que M10/PR #452 sí porta como `ollama_relevance_filter.py` (§1.6 más abajo). |
| `lateral/` (`candidato.py`, `categoria.py`, `medir_categoria.py`, `texto.py`) — índices laterales adicionales en `E1` | **NO SE PORTA** | No citado como adoptado por PR #117 ni por ningún ADR fusionado; exploración declarada como tal en su propio docstring (`lateral/candidato.py:1`: «`ADR002-A` más uno o varios índices laterales»), sin resultado publicado que lo respalde. |
| `projection/contracts.py` — `referencia_canonica` (`contracts.py:161-170`, filtra un identificador de corpus a su identidad canónica `MEM-`/`DEC-`, o `None` si no es del canon) | **NO SE PORTA (lógica reconstruida a mano)** | Sí forma parte del paquete D1: `ADR-104:58-68` la usa explícitamente para filtrar `resultado_esperado` a identidades del canon al reconstruir los 81 elementos esperados del banco portado (PR #446). Su lógica quedó materializada, una sola vez y a mano, en el propio contenido estático de `tests/acceptance/fixtures/evidence_bank_47_casos.json` (ya filtrado) — el módulo en sí no vive en `main` como código: no hay script de construcción de fixtures en `main` que lo invoque, así que si el banco necesitara reconstruirse desde cero (más casos, otra versión del canon) habría que volver a aplicar este filtro, a mano o portando el módulo. |
| `projection/contracts.py` — el resto del módulo (planos `Plano`/`FICHEROS`, capacidades `CAPACIDAD_DEL_PLANO`/`CONSUMIDORES_DEL_PLANO`, `estado_de_memoria`, `estado_de_decision`, control de acceso por plano) | **NO SE PORTA** | No citado por `ADR-104` ni por ningún otro ADR fusionado o en borrador; gobierna planos reservados (`ejes_p2`, `reservado`) y control de acceso entre candidatos del laboratorio, ajeno al banco portado. |
| `cards/`, `rederivation/`, `storage/`, `tolerances/`, `t0_control/`, y el resto de `projection/` (`__init__.py`, `build.py`, `conftest.py`, `plane.py`, `projection_manifest_v0_1.json`, `test_adr002_proyeccion.py`) | **NO SE PORTA** | Piezas de otras investigaciones de ADR-002 (fichas de candidato, re-derivación controlada, contabilidad de almacenamiento, bandas de tolerancia de medición, control de falsación T0) no relacionadas con el paquete de recuperación D1 que este inventario cubre. |

### 1.6 Artefactos de medición (evidencia congelada)

**NO SE PORTA.** `experiments/adr002/artifacts/` (excluido explícitamente del alcance de
esta incidencia) y los ficheros `resultado_modelo_local*.json` en la raíz de
`evidence/adr001-spikes` (siete versiones, `v0.1` a `v0.7`) son evidencia de medición
congelada: seis mediciones «conservadas enteras y ninguna pisada» (PR #117, sección
«Custodia de la evidencia»; el arnés del laboratorio «se niega a sobrescribir un artefacto ya
medido»). Nunca se portan como código — se citan como fuente de un hecho medido (así los cita
`ADR-104`, `ADR-109` y el borrador de `ADR-110`), nunca se copian ni se ejecutan en `main`.

## 2. Clasificador y filtro (M8–M10) — ya portados, fuera de `candidates/common/`

El objetivo de la incidencia pide citar, además, las PRs de M8-M10 para el clasificador y el
filtro. No viven bajo `candidates/adr002_a/` ni `candidates/common/` en el laboratorio (son
diseño nuevo de la Arquitectura Técnica 0.2 §6.1/§6.2/§6.3, no un port literal de un módulo
del laboratorio), pero son la otra mitad del paquete D1 (STATUS.md:158-159: «el índice de
categoría determinista **y** el filtro de relevancia con modelo local vía Ollama»).

| Pieza | Estado | Dónde vive en `main` / PR |
|---|---|---|
| Clasificador de categoría (D7) — campo `category`/`category_locked`, `CategoryClassifierPort`, `OllamaCategoryClassifierAdapter`, `TagCategoryUseCase`, `SetCategoryUseCase` | **PORTADO** | PR #448 (M8, fusionada): `src/sirius/ports/category_classifier.py`, `src/sirius/adapters/ollama_category_classifier.py`, `src/sirius/application/tag_category.py`, `src/sirius/application/set_category.py`, `src/sirius/domain/memory.py`, `src/sirius/domain/decision.py`, migración `71bb52f6cc2b`, `docs/decisions/ADR-106-...md`. |
| Índice de categoría determinista — cuarta señal de `RankedKnowledge` | **PORTADO** | PR #450 (M9, fusionada): `src/sirius/domain/relevance.py`, `src/sirius/application/rank_relevant_knowledge.py`. |
| Filtro de relevancia con modelo local vía Ollama — puerto, adaptador, candado | **PORTADO** | PR #452 (M10, fusionada): `src/sirius/adapters/ollama_relevance_filter.py`, `src/sirius/ports/relevance_filter.py`, `src/sirius/application/context.py`. |
| Integración M11 (RNF-003, coincidencia del etiquetado, banco completo) | **PENDIENTE / bloqueada** | PR #454 (abierta, sin fusionar). Contiene los borradores `docs/decisions/ADR-107-...md` y `docs/decisions/ADR-108-...md`, ninguno de los dos aprobado ni fusionado — ver [Nota sobre ADR-108](#nota-sobre-adr-108). El hallazgo bloqueante que M11 encontró (tratamiento léxico ausente en `sanitize_fts5_query`) se diagnosticó en la incidencia #453/#455 y se resolvió parcialmente por las incidencias #455/#456 y #457/#458 (§1.1, §1.2, §1.4 arriba). |

## 3. Hechos operativos verificados

- **El modelo local que el laboratorio usó fue `qwen3:4b-instruct`, servido por Ollama.**
  `experiments/adr002/modelo_local/puerto.py:73` (rama `evidence/adr001-spikes`):
  `MODELO_POR_DEFECTO: Final = "qwen3:4b-instruct"`. Confirmado por
  `experiments/adr002/candidates/test_adr002_modelo_local.py:94-96`
  (`test_el_modelo_por_defecto_cabe_en_una_grafica_de_portatil`, `assert "4b" in
  puerto.MODELO_POR_DEFECTO`) y por el artefacto congelado `resultado_modelo_local_v0.7.json`
  (raíz de `evidence/adr001-spikes`), campo `procedencia_del_modelo`: `{"proveedor":
  "ollama", "modelo": "qwen3:4b-instruct", "huella":
  "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"}`.
- **Las mediciones se ejecutaron contra un Ollama local (`localhost`), ya instalado en la
  máquina que las corrió — hecho histórico, no un estado verificado hoy.**
  `experiments/adr002/modelo_local/puerto.py:67`: `SERVIDOR_POR_DEFECTO: Final =
  "http://localhost:11434"` (nunca un host remoto configurable). PR #117, sección «Lo que
  queda por decidir»: «el filtro exige que Ollama esté arrancado, y `AGENTS.md` obliga a
  detenerse antes de introducir otro proceso» — confirma que la medición dependía de un
  proceso ya en marcha en la máquina de ejecución, no de una instalación nueva del propio
  laboratorio ni de un servicio en la nube. Este inventario no verifica de forma
  independiente *qué máquina física* ejecutó cada medición (ese dato no está en ningún
  fichero versionado accesible) — se declara **no verificado** por esa parte y se deja tal
  como lo afirma el objetivo de la incidencia. Por eso mismo, este hecho histórico **no es
  una instrucción operativa para hoy**: no acredita que Ollama siga instalado en la máquina
  del propietario ni que no haya que instalarlo — ADR-095:89-97 exige consultar el servicio
  para afirmar un estado vivo, y este inventario no lo ha consultado. Cualquier trabajo que
  dependa de tener Ollama arrancado debe comprobarlo en el momento, no asumirlo por esta nota.

## Nota sobre ADR-108

El objetivo de esta incidencia menciona «el tratamiento léxico de consultas que ningún
documento enumeraba (ya pasó dos veces ... ADR-108/109)». Verificado a máquina: **ADR-108 no
existe como fichero fusionado en `main`** (`docs/decisions/` salta de `ADR-106` a `ADR-109`,
confirmado por `ls docs/decisions/`). Existe un borrador, `docs/decisions/ADR-108-el-banco-de-47-casos-no-alcanza-el-suelo-d1-de-29-47-porque-fts5-empareja-con-cualquier-palabra-incluidas-las-vacias.md`,
sin aprobar ni fusionar, dentro de la PR #454 (M11, abierta). El propio historial de `main`
documenta esta corrección: el commit `5507da9` («Ronda 2: corrige citas rotas de línea y
referencias a ADR-108 inexistente», PR #456) sustituyó todas las citas a «ADR-108» por la
incidencia #455 (la fuente real y fusionada del diagnóstico) precisamente porque ADR-108 no
existía en el registro. Este inventario cita, en consecuencia, la incidencia #455 y ADR-109
(fusionado) como fuente del hallazgo bloqueante, y señala ADR-108 como borrador pendiente,
no como decisión vigente.

## Nota sobre una cita desactualizada en ADR-110

El borrador de ADR-110 (PR #458, sin fusionar), en su diagnóstico de `G11`, cita
`experiments/adr002/candidates/common/gates.py:262-278`. Verificado a máquina sobre el commit
`dfdcdaff04dcba10939cc0b0569c55b6a636296f` de `evidence/adr001-spikes`: esas líneas
corresponden a la función `_g9` (sensibilidad), no a `aplicar_g11`. `aplicar_g11` vive en
`gates.py:306-323`, y su cuerpo sí coincide con lo que ADR-110 describe («solo rechaza una
lectura incompleta, no compara polaridad/condición con la consulta»:
`if not lectura.sujeto.strip() or not lectura.medio.strip(): descartes.append(...)`). Este
inventario usa la línea verificada (`306-323`), no la citada en el borrador, y dado que
ADR-110 sigue en estado `PROPUESTO` (sin fusionar), esta discrepancia queda señalada aquí en
vez de corregida en el propio ADR — corregirlo no está en el alcance de esta incidencia
documental. El resto de citas de ADR-110 verificadas por este inventario (`port.py:434-455`,
`round/cases.py:334-366` y `101-103`) sí coinciden con el código actual.

## Resumen por estado

- **PORTADO**: tratamiento léxico base (`VACIAS`/`plegar`/`tokenizar`/`raiz`/`variantes`,
  PR #456), el mecanismo de `por_termino_lexico` dentro de `sanitize_fts5_query` (PR #456),
  `consulta`/`ambito`/`resultado_esperado`/`criticidad.razon_segura` del banco de 47 casos
  (PR #446), el clasificador de categoría (PR #448), el índice de categoría (PR #450), el
  filtro de relevancia con Ollama (PR #452).
- **PENDIENTE**: el resto del tratamiento léxico (polaridad/condición/marcadores), el
  candidato A completo, toda la capa común (`contracts`/`gates`/`grouping`/`stops`/`trace`/
  `engine`/resto de `port`) — todo escrito y en revisión en la PR #458, sin fusionar —, los
  campos de petición por caso (`modo`/`permiso`/`cardinalidad`/`limite`) y `ejes_p2`/
  `property_key` del banco, el traductor `round/cases.py`, y la integración M11 (PR #454,
  bloqueada).
- **NO SE PORTA**: candidatos B, C y D; la ampliación de consulta al guardar; la fusión
  híbrida RRF; el modo «compuerta» del filtro; los índices laterales; la maquinaria de
  construcción/validación del corpus (`build_corpus_*`, `validate_corpus_*`, `schema_*`,
  `canonical_source_*`); el arnés y protocolo de la ronda primaria (`round/execute_round.py`
  y familia, excepto `cases.py`); `neutrality.py` de la capa común; `projection/contracts.py:referencia_canonica`
  (su lógica sí es parte de D1 por `ADR-104`, pero solo quedó reconstruida a mano en el
  fixture estático, no portada como código — ver §1.5) y el resto de `projection/`; los
  demás subdirectorios de ADR-002 ajenos al paquete D1 (`cards/`, `rederivation/`,
  `storage/`, `tolerances/`, `t0_control/`); y todos los artefactos de medición congelados.
- **PENDIENTE DE CONFIRMAR**: `derived.py` de la capa común — ningún ADR ni PR fusionada lo
  nombra, ni para portarlo ni para excluirlo; este inventario razona por qué probablemente no
  hace falta, pero no lo trata como decisión ya tomada (ver §1.2).

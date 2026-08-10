# Trazabilidad de las pruebas de aceptación, personalidad y seguridad

Registro único que enlaza cada prueba del Plan de Pruebas y Trazabilidad
aprobado con las pruebas automáticas que cubren su parte automatizable.
Pertenece a B12.

`tests/unit/test_pa_sp_traceability.py` lo comprueba por máquina: verifica que
estén los 40 identificadores del plan, ni uno menos ni uno inventado, que cada
prueba nombrada **exista de verdad**, y que toda cobertura parcial o manual
declare su motivo. Una matriz que no se comprueba se pudre en cuanto alguien
renombra una prueba, y entonces afirma cobertura que ya no existe.

## Cómo leerla

**Cobertura** dice qué puede demostrar hoy la suite automática:

| Valor | Significa |
|---|---|
| `automática` | La prueba del plan queda demostrada por pruebas automáticas con dobles deterministas |
| `parcial` | Lo automatizable está cubierto, pero la prueba formal exige algo que ninguna suite puede dar |
| `manual` | Nada de esto se puede automatizar |

**Motivo** es obligatorio cuando la cobertura es `parcial` o `manual`, y solo
admite: `proveedor-real`, `windows-real` o `evaluación-humana`.

`hueco` en la columna de pruebas significa que no hay ninguna todavía. Es una
ausencia declarada, no un olvido: se escribe para que se vea.

**Cobertura `automática` no es una PA superada.** Una PA se declara superada en
su ejecución formal dentro de V8.3 y V8.4, con su evidencia. Esta tabla dice
qué está demostrado por máquina, que es una cosa distinta y menor.

## Pruebas de aceptación

| ID | Prueba del plan | Cobertura | Motivo | Pruebas |
|---|---|---|---|---|
| PA-001 | Primera configuración | parcial | proveedor-real | `tests/gui/test_onboarding_window.py::test_onboarding_shows_policy_defaults_and_a_masked_key_field`<br>`tests/gui/test_onboarding_window.py::test_successful_validation_saves_the_key_activates_the_provider_and_opens_the_way_forward` |
| PA-002 | Credencial inválida | parcial | proveedor-real | `tests/gui/test_onboarding_window.py::test_rejected_key_is_not_saved_and_onboarding_stays_in_place`<br>`tests/unit/test_validate_and_save_api_key.py::test_failed_validation_never_writes_the_candidate_key` |
| PA-003 | Guardado previo | automática | — | `tests/integration/test_send_message.py::test_send_message_persists_a_failed_message_with_partial_text_before_any_delta`<br>`tests/integration/test_send_message.py::test_a_cancelled_or_failed_reply_can_be_resent_without_duplicating_the_user_message`<br>`tests/gui/test_conversation_ui.py::test_provider_failure_shows_a_clear_error_and_persists_the_failed_reply` |
| PA-004 | Streaming y cancelación | automática | — | `tests/gui/test_conversation_ui.py::test_response_streams_progressively_before_completion`<br>`tests/gui/test_conversation_ui.py::test_cancel_button_is_visible_only_during_an_operation`<br>`tests/integration/test_send_message.py::test_send_message_cancelled_mid_stream_persists_the_partial_text_as_cancelled` |
| PA-005 | Reinicio de conversación | automática | — | `tests/gui/test_conversation_ui.py::test_messages_persist_after_closing_and_reopening`<br>`tests/gui/test_conversation_ui.py::test_history_loads_in_stable_order_on_startup`<br>`tests/integration/test_get_conversation_history_sqlite.py::test_get_history_returns_persisted_messages_in_order` |
| PA-006 | Crear proyecto | automática | — | `tests/unit/test_initial_project_use_case.py::test_create_initial_project_normalizes_and_persists_name_and_objective`<br>`tests/unit/test_initial_project_use_case.py::test_create_initial_project_assigns_the_canonical_initial_state_and_next_step` |
| PA-007 | Un solo proyecto | automática | — | `tests/unit/test_initial_project_use_case.py::test_create_initial_project_rejects_a_second_configured_project`<br>`tests/integration/test_initial_project_persistence.py::test_create_initial_project_rejects_a_second_project_and_keeps_the_first_intact` |
| PA-008 | Retomar proyecto | parcial | proveedor-real | `tests/integration/test_send_message.py::test_send_message_context_reflects_a_project_continuity_update`<br>`tests/integration/test_initial_project_persistence.py::test_configured_project_is_recovered_after_reconstructing_repositories` |
| PA-009 | Qué hacemos ahora | manual | evaluación-humana | hueco |
| PA-010 | Guardar memoria manual | automática | — | `tests/integration/test_manual_memory_origin.py::test_explicit_save_creates_a_traceable_memory_and_its_origin_can_be_opened`<br>`tests/gui/test_knowledge_widget.py::test_view_memory_origin_shows_the_recorded_event` |
| PA-011 | No convertir exploración en decisión | automática | — | `tests/integration/test_decision_lifecycle.py::test_debating_alternatives_never_creates_a_decision`<br>`tests/integration/test_decision_archive_lifecycle.py::test_an_ordinary_conversation_never_archives_a_decision_or_memory_on_its_own` |
| PA-012 | Corregir y versionar | automática | — | `tests/integration/test_memory_correction_lifecycle.py::test_correcting_a_memory_creates_a_new_current_revision_and_keeps_the_previous_one`<br>`tests/gui/test_knowledge_widget.py::test_correct_memory_creates_a_new_revision` |
| PA-013 | Sustituir decisión | automática | — | `tests/integration/test_decision_lifecycle.py::test_a_proposed_decision_can_explicitly_supersede_an_approved_one`<br>`tests/gui/test_knowledge_widget.py::test_supersede_decision_replaces_the_approved_one` |
| PA-014 | Conflicto sin precedencia | automática | — | `tests/unit/test_precedence_domain.py::test_conflict_never_names_a_winner_regardless_of_creation_order`<br>`tests/unit/test_precedence_domain.py::test_more_than_one_approved_decision_for_the_same_subject_is_a_conflict_not_a_silent_pick`<br>`tests/gui/test_knowledge_widget.py::test_detect_conflicts_lists_unresolved_conflicts_without_choosing_a_winner` |
| PA-015 | Archivar | automática | — | `tests/integration/test_memory_archive_delete_lifecycle.py::test_archiving_a_memory_keeps_content_and_history_but_leaves_ordinary_queries`<br>`tests/gui/test_knowledge_widget.py::test_archive_memory_moves_it_out_of_current` |
| PA-016 | Eliminar | automática | — | `tests/integration/test_memory_archive_delete_lifecycle.py::test_deletion_keeps_only_the_approved_minimal_marker_fields`<br>`tests/integration/test_memory_archive_delete_lifecycle.py::test_deleting_with_redact_choice_removes_the_source_message_content`<br>`tests/gui/test_knowledge_widget.py::test_delete_memory_dialog_ok_button_disabled_until_explicit_choice` |
| PA-017 | Fallo del proveedor | automática | — | `tests/unit/test_error_messages.py::test_all_error_kinds_are_covered_exhaustively`<br>`tests/unit/test_error_messages.py::test_each_known_error_kind_has_a_distinct_actionable_message`<br>`tests/gui/test_conversation_ui.py::test_each_llm_error_kind_shows_its_actionable_message` |
| PA-018 | Límite mensual | automática | — | `tests/unit/test_budget_status.py::test_spend_at_the_warn_threshold_is_near_limit`<br>`tests/unit/test_budget_status.py::test_spend_above_the_warn_threshold_and_below_the_limit_is_near_limit` |
| PA-019 | Cierre forzado | automática | — | `tests/integration/test_forced_shutdown_recovery.py::test_forced_shutdown_preserves_confirmed_state_and_reopens_coherently` |
| PA-020 | Exportación | automática | — | `tests/integration/test_export_structured.py::test_export_structured_writes_exactly_the_six_approved_files`<br>`tests/integration/test_export_structured.py::test_export_structured_contains_real_conversation_project_memory_and_decision_data` |
| PA-021 | Copia y restauración | parcial | windows-real | `tests/integration/test_sqlite_backup_restore.py::test_restore_backup_replaces_the_database_atomically`<br>`tests/integration/test_sqlite_backup_restore.py::test_restore_backup_creates_a_validated_safety_copy_of_the_current_database` |
| PA-022 | Copia inválida | automática | — | `tests/integration/test_sqlite_backup_validation.py::test_validate_backup_rejects_a_tampered_ciphertext`<br>`tests/integration/test_sqlite_backup_restore.py::test_restore_backup_rejects_a_tampered_backup_without_modifying_data` |
| PA-023 | Sin telemetría | manual | windows-real | hueco |
| PA-024 | Sin acciones externas | automática | — | `tests/unit/test_identity_domain.py::test_canonical_seed_includes_the_external_actions_policy`<br>`tests/unit/test_render_instructions.py::test_render_instructions_includes_the_external_actions_policy_from_the_canonical_seed` |
| PA-025 | Rendimiento local | parcial | windows-real | `tests/integration/test_local_performance.py::test_el_conjunto_de_referencia_tiene_el_tamano_que_fija_el_plan`<br>`tests/integration/test_local_performance.py::test_el_inicio_local_cumple_el_limite_aprobado`<br>`tests/integration/test_local_performance.py::test_las_operaciones_locales_no_se_disparan`<br>`tests/integration/test_local_performance.py::test_listar_decisiones_vigentes_cumple_el_limite_aprobado` |
| PA-E2E-01 | Proyecto real durante varias sesiones | manual | evaluación-humana | hueco |

## Suite de personalidad

El propio plan lo zanja: «la evaluación humana es vinculante». Ninguna de estas
se automatiza, y la rúbrica de siete dimensiones no es un sustituto: es la
estructura de una revisión humana.

| ID | Prueba del plan | Cobertura | Motivo | Pruebas |
|---|---|---|---|---|
| PS-01 | Conversación cotidiana | manual | evaluación-humana | hueco |
| PS-02 | Decisión técnica | manual | evaluación-humana | hueco |
| PS-03 | Desacuerdo | manual | evaluación-humana | hueco |
| PS-04 | Incertidumbre | manual | evaluación-humana | hueco |
| PS-05 | Error serio | manual | evaluación-humana | hueco |
| PS-06 | Frustración | manual | evaluación-humana | hueco |
| PS-07 | Tarea larga | manual | evaluación-humana | hueco |

## Pruebas de seguridad y privacidad

| ID | Prueba del plan | Cobertura | Motivo | Pruebas |
|---|---|---|---|---|
| SP-01 | Clave en reposo | parcial | windows-real | `tests/integration/test_secret_leakage.py::test_key_never_appears_in_settings_json`<br>`tests/integration/test_secret_leakage.py::test_key_never_appears_in_sqlite_after_a_full_send`<br>`tests/integration/test_secret_leakage.py::test_key_never_appears_in_a_structured_export` |
| SP-02 | Logs minimizados | automática | — | `tests/integration/test_secret_leakage.py::test_key_never_appears_in_logs_even_when_an_exception_message_embeds_it`<br>`tests/unit/test_error_messages.py::test_failed_send_message_never_leaks_a_raw_provider_message` |
| SP-03 | Contexto enviado | automática | — | `tests/integration/test_context_builder.py::test_context_field_order_matches_the_defined_sections`<br>`tests/integration/test_context_builder.py::test_build_excludes_memories_and_decisions_unrelated_to_the_query`<br>`tests/integration/test_context_builder.py::test_build_excludes_archived_and_deleted_memories` |
| SP-04 | store=false | automática | — | `tests/unit/test_openai_responses_provider.py::test_store_is_always_false` |
| SP-05 | Copia cifrada | automática | — | `tests/integration/test_sqlite_backup_service.py::test_create_backup_can_be_decrypted_only_with_the_correct_password`<br>`tests/integration/test_sqlite_backup_service.py::test_create_backup_package_contains_only_manifest_and_database` |
| SP-06 | Borrado y copia antigua | automática | — | `tests/gui/test_knowledge_widget.py::test_delete_memory_preserving_source_message_shows_old_backup_warning`<br>`tests/gui/test_knowledge_widget.py::test_delete_memory_redacting_source_message_shows_old_backup_warning` |
| SP-07 | Renderizado Markdown | automática | — | `tests/gui/test_conversation_ui.py::test_html_and_script_content_is_shown_literal_and_never_interpreted`<br>`tests/gui/test_conversation_ui.py::test_html_and_script_inside_code_block_is_shown_literal_and_never_interpreted` |

## Huecos abiertos

Lo que esta matriz deja al descubierto, que es para lo que sirve:

| Hueco | Qué falta | Dónde se cierra |
|---|---|---|
| PA-009, PA-E2E-01, PS-01 a PS-07 | Evaluación humana, imposible de automatizar por definición | V8.4 |
| PA-023 | Monitorización de tráfico real en Windows | B14 |

Las entradas `parcial` (PA-001, PA-002, PA-008, PA-021, PA-025 y SP-01) **no**
son huecos: su parte automatizable está cubierta y lo que falta es la ejecución
formal, que pertenece a V8.3 y V8.4.

### Un riesgo abierto que la medición destapó (PA-025)

B12c midió el rendimiento sobre el conjunto de referencia del plan y encontró
que **construir el contexto consume entre el 89 % y el 100 % de sus 300 ms** en
tres pasadas del mismo código. El término dominante está localizado:
`list_current_memories()` ejecuta 501 consultas para 500 recuerdos, porque
`_load_memory()` pide la revisión vigente una por una.

No es un hueco de trazabilidad: es un riesgo de producto sobre una prueba de
aceptación que todavía no se ha ejecutado en la máquina real. Corregirlo exige
tocar código productivo y espera decisión del propietario. El detalle y las
cifras están en ADR-007.

## Lo que esta matriz no dice

- **No dice que una PA esté superada.** Dice qué la cubre por máquina.
- **No mide la calidad de la prueba.** Una prueba vacua cuenta igual que una
  buena; contra eso está la disciplina de mutación de ADR-001, no esta tabla.
- **No cubre RF ni RNF directamente.** Enlaza pruebas del plan con pruebas
  automáticas; la trazabilidad requisito–PA vive en el plan aprobado.

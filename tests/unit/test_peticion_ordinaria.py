"""M16 (SIRIUS-ARQ-0.2 §11.3/§11.5, incidencia #504): la política uniforme
con la que ``RankRelevantKnowledgeUseCase._rank_via_staged_engine`` interroga
al motor por etapas gana ámbito real (derivado del proyecto activo) y su
propósito honesto queda confirmado por una prueba explícita, en vez de serlo
solo por lectura del código (ADR-124).

Prueba de caja blanca contra ``_peticion_ordinaria`` directamente — el mismo
patrón que ya usan ``test_sqlite_backup_validation.py``
(``_derive_key``/``_decrypt_envelope``) y ``test_llm_provider_selection.py``
(``_build_llm_provider``) para funciones privadas de un solo caller real: es
la función exacta que ``_rank_via_staged_engine`` invoca para construir la
``Peticion`` que ``recuperar()`` recibe, sin repositorio ni SQLite de por
medio porque es pura.
"""

from __future__ import annotations

import inspect

from sirius.application.interpret_query_request import PROPOSITO_RECUPERACION_ORDINARIA
from sirius.application.rank_relevant_knowledge import _LIMITE_SIN_ATAR, _peticion_ordinaria
from sirius.domain.staged_engine_contracts import Ambito, Cardinalidad, Modo


def test_ambito_is_scoped_to_the_active_project_when_one_is_configured() -> None:
    peticion = _peticion_ordinaria("consulta", "op-1", active_project_id=7)
    assert peticion.ambito == Ambito(global_=False, proyectos=("7",))


def test_ambito_is_global_without_an_active_project() -> None:
    peticion = _peticion_ordinaria("consulta", "op-1", active_project_id=None)
    assert peticion.ambito == Ambito(global_=True, proyectos=())


def test_la_ampliacion_por_categoria_viene_encendida_con_proyecto_activo_y_sin_el() -> None:
    """§11.3 + ADR-177 (H4 de ADR-148): la única llamada real a ``rank()``
    ocurre desde ``ContextBuilder._rank_related_knowledge`` para ensamblar el
    contexto de un turno, y esta política es uniforme —no infiere intención—,
    así que pide la recuperación más amplia siempre, con proyecto activo o
    sin él: que la llamada ensamble contexto no depende del proyecto.

    Hasta ADR-177 esto mismo se afirmaba de rebote, comprobando que el
    literal del propósito contuviera la subcadena «contexto»
    (``pide_contexto``). Ahora se afirma sobre la señal que de verdad decide,
    y el propósito se comprueba aparte, como lo que es: un texto declarado
    que ya no activa nada."""
    con_proyecto = _peticion_ordinaria("consulta", "op-1", active_project_id=7)
    sin_proyecto = _peticion_ordinaria("consulta", "op-1", active_project_id=None)
    assert con_proyecto.amplia_por_categoria is True
    assert sin_proyecto.amplia_por_categoria is True
    assert con_proyecto.proposito == PROPOSITO_RECUPERACION_ORDINARIA


def test_mode_cardinality_and_limits_stay_fixed_regardless_of_the_active_project() -> None:
    """§11.3 prohíbe tocar modo, cardinalidad y límite en este encargo: solo
    el ámbito depende de ``active_project_id``."""
    con_proyecto = _peticion_ordinaria("consulta", "op-1", active_project_id=7)
    sin_proyecto = _peticion_ordinaria("consulta", "op-1", active_project_id=None)
    for peticion in (con_proyecto, sin_proyecto):
        assert peticion.modo is Modo.M1_ORDINARIO
        assert peticion.cardinalidad is Cardinalidad.EXHAUSTIVA
        assert peticion.limite_objetivo == _LIMITE_SIN_ATAR
        assert peticion.limite_duro == _LIMITE_SIN_ATAR


def test_no_caller_can_override_the_purpose() -> None:
    """El propósito lo fija ``_peticion_ordinaria`` misma, no quien la llama
    (§11.5-M16, criterio de aceptación): su firma no admite ``proposito``
    como argumento, así que ningún caller —incluida una petición construida
    fuera de ``ContextBuilder``, como ``peticion_desde_caso`` del arnés de
    aceptación, que nunca pasa por esta función— puede inyectar uno propio."""
    assert "proposito" not in inspect.signature(_peticion_ordinaria).parameters

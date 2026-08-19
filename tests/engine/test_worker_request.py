"""WorkerRequest: proyección determinista del encargo (arquitectura §5.1, incidencia #202).

A4-P1 (determinismo) y A4-P2 (no-divergencia con la vía GitHub existente)
viven aquí. A4-P2 no reimplementa la lógica del workflow en Python: ejecuta
el guión bash REAL del paso "Preparar instrucciones para Claude Code" de
``.github/workflows/implement-sirius-work.yml`` (leído tal cual, nunca
modificado) y compara su salida, byte a byte, contra la proyección de este
bloque -así una divergencia futura entre el prompt real y la proyección cae
aquí en rojo, en vez de depender de que alguien se acuerde de mirar.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest
import yaml

from sirius_engine.adapters.github_worker_request import (
    project_github_prompt,
    read_procedure_text,
)
from sirius_engine.capability_registry import load_capability_registry
from sirius_engine.domain.context_fragment import ContextFragment
from sirius_engine.domain.errors import EgressClassificationError
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item
from sirius_engine.profile_registry import load_agent_profile
from sirius_engine.worker_request import project_worker_request

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "implement-sirius-work.yml"
_BUILD_PROMPT_STEP_NAME = "Preparar instrucciones para Claude Code"


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _work_item(*, now: datetime) -> WorkItem:
    return create_work_item(
        work_id="canelamoraguezandyjesus-bot/sirius#202",
        peticion_original="texto literal de la petición",
        objetivo="Implementar A4",
        contexto_origen=("incidencia:202",),
        entregable="código, pruebas y ADR",
        criterio_terminado="las cinco pruebas de terminado A4-P1..P5 en verde",
        limites={"presupuesto_turnos": 300},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=now,
    )


# --- A4-P1: determinismo ----------------------------------------------------


def test_misma_entrada_produce_el_mismo_worker_request(now: datetime) -> None:
    work_item = _work_item(now=now)
    profile = load_agent_profile("implementer")
    registro = load_capability_registry()
    contexto = (ContextFragment(contenido="x", procedencia="p", clasificacion="privado"),)

    primero = project_worker_request(
        work_item=work_item, profile=profile, registro=registro, contexto=contexto
    )
    segundo = project_worker_request(
        work_item=work_item, profile=profile, registro=registro, contexto=contexto
    )

    assert primero == segundo
    assert primero is not segundo  # objetos nuevos, no el mismo, y aun así iguales


@pytest.mark.parametrize("ref", ("implementer", "reviewer", "corrector", "auditor"))
def test_determinismo_para_los_cuatro_perfiles_reales(ref: str, now: datetime) -> None:
    # WorkerRequest.limites es un Mapping (MappingProxyType), no hasheable:
    # se comparan tres proyecciones por igualdad, no por pertenencia a un
    # set -que exigiría __hash__ sobre un campo que a propósito no lo tiene.
    work_item = _work_item(now=now)
    profile = load_agent_profile(ref)
    registro = load_capability_registry()

    proyecciones = [
        project_worker_request(work_item=work_item, profile=profile, registro=registro)
        for _ in range(3)
    ]
    assert proyecciones[0] == proyecciones[1] == proyecciones[2]


def test_worker_request_no_incluye_una_capacidad_no_concedida(now: datetime) -> None:
    """El envelope calculado concede exactamente lo que el perfil declara: nada de más."""
    work_item = _work_item(now=now)
    profile = load_agent_profile("reviewer")
    registro = load_capability_registry()

    resultado = project_worker_request(work_item=work_item, profile=profile, registro=registro)

    nombres_resueltos = {c.nombre for c in resultado.capacidades_resueltas}
    assert nombres_resueltos == set(profile.capacidades)
    assert "repo.escribir" not in nombres_resueltos  # reviewer nunca escribe


def test_fragmento_sin_clasificar_impide_construir_el_worker_request(now: datetime) -> None:
    work_item = _work_item(now=now)
    profile = load_agent_profile("implementer")
    registro = load_capability_registry()
    contexto = (ContextFragment(contenido="x", procedencia="p", clasificacion=None),)

    with pytest.raises(EgressClassificationError):
        project_worker_request(
            work_item=work_item, profile=profile, registro=registro, contexto=contexto
        )


# --- A4-P2: no-divergencia con la vía GitHub existente ----------------------


def _extraer_paso_build_prompt() -> str:
    datos = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    pasos = datos["jobs"]["implement"]["steps"]
    for paso in pasos:
        if paso.get("name") == _BUILD_PROMPT_STEP_NAME:
            run_script = paso["run"]
            assert isinstance(run_script, str)
            return run_script
    raise AssertionError(f"no se encontró el paso {_BUILD_PROMPT_STEP_NAME!r} en {_WORKFLOW_PATH}")


_HEREDOC_RE = re.compile(r"prompt<<SIRIUS_PROMPT_EOF\n(.*?\n)SIRIUS_PROMPT_EOF\n", re.DOTALL)


def _prompt_real_del_workflow(*, repo: str, issue_number: int, tmp_path: Path) -> str:
    """Ejecutar el guión bash REAL del workflow (leído, no reescrito) y extraer su salida."""
    script = _extraer_paso_build_prompt()
    output_path = tmp_path / "github_output.txt"
    entorno = dict(os.environ)
    entorno.update(
        {"GH_REPO": repo, "ISSUE_NUMBER": str(issue_number), "GITHUB_OUTPUT": str(output_path)}
    )
    subprocess.run(
        ["bash", "-c", script],
        check=True,
        cwd=_REPO_ROOT,
        env=entorno,
        capture_output=True,
        text=True,
    )
    contenido = output_path.read_text(encoding="utf-8")
    match = _HEREDOC_RE.search(contenido)
    assert match is not None, f"no se pudo extraer el heredoc 'prompt' de:\n{contenido}"
    return match.group(1)


def test_la_proyeccion_del_perfil_implementer_reproduce_el_prompt_real_del_workflow(
    tmp_path: Path,
) -> None:
    """A4-P2: la proyección del perfil implementador reproduce el prompt que hoy monta
    ``implement-sirius-work.yml`` para una incidencia fixture."""
    perfil = load_agent_profile("implementer")
    procedure_text = read_procedure_text(perfil)

    repo = "canelamoraguezandyjesus-bot/sirius"
    issue_number = 202

    esperado = _prompt_real_del_workflow(repo=repo, issue_number=issue_number, tmp_path=tmp_path)
    obtenido = project_github_prompt(
        procedure_text=procedure_text, repo=repo, issue_number=issue_number, base_branch="main"
    )

    assert obtenido == esperado


def test_la_no_divergencia_vale_para_otra_incidencia_y_otro_repositorio(tmp_path: Path) -> None:
    perfil = load_agent_profile("implementer")
    procedure_text = read_procedure_text(perfil)

    repo = "otra-org/otro-repo"
    issue_number = 4242

    esperado = _prompt_real_del_workflow(repo=repo, issue_number=issue_number, tmp_path=tmp_path)
    obtenido = project_github_prompt(
        procedure_text=procedure_text, repo=repo, issue_number=issue_number, base_branch="main"
    )

    assert obtenido == esperado


def test_read_procedure_text_lee_exactamente_el_fichero_del_perfil(tmp_path: Path) -> None:
    (tmp_path / "perfiles").mkdir()
    procedimiento = tmp_path / "runbook.md"
    procedimiento.write_text("contenido de prueba\ncon dos líneas\n", encoding="utf-8")

    from sirius_engine.domain.profile import AgentProfile, ProfilePermissions

    perfil = AgentProfile(
        ref="x",
        version=1,
        mision="probar",
        procedimiento_ref="runbook.md",
        capacidades=(),
        permisos=ProfilePermissions(escritura=None, red=False),
        contrato_entrada=(),
        contrato_salida=(),
    )
    assert (
        read_procedure_text(perfil, repo_root=tmp_path) == "contenido de prueba\ncon dos líneas\n"
    )


def test_limites_del_work_item_viajan_como_mapa_inmutable(now: datetime) -> None:
    work_item = _work_item(now=now)
    profile = load_agent_profile("implementer")
    registro = load_capability_registry()

    resultado = project_worker_request(work_item=work_item, profile=profile, registro=registro)

    assert isinstance(resultado.limites, MappingProxyType)
    assert dict(resultado.limites) == dict(work_item.limites)

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

import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest
import yaml

from sirius_engine.adapters.github_worker_request import (
    plazo_del_implementador,
    project_github_prompt,
    read_procedure_text,
)
from sirius_engine.capability_registry import load_capability_registry
from sirius_engine.domain.context_fragment import ContextFragment
from sirius_engine.domain.errors import EgressClassificationError, UnknownAgentProfileError
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item
from sirius_engine.profile_registry import load_agent_profile
from sirius_engine.worker_request import project_worker_request

from .conftest import PERFILES_REALES

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


@pytest.mark.parametrize("ref", PERFILES_REALES)
def test_determinismo_para_todos_los_perfiles_reales(ref: str, now: datetime) -> None:
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

#: El instante en que el arnés «prepara el prompt»: el guión real calcula el
#: reloj del implementador con `date -u` (ADR-228), y la no-divergencia solo
#: se puede comparar byte a byte si el guión y la proyección ven la misma hora.
_AHORA_DEL_RELOJ = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
#: Lo que la preparación «consumió» en el arnés antes de preparar el prompt: el
#: guión real resta ese tiempo del tope del job (ADR-228, plazo calculado).
_CONSUMIDO_DEL_ARNES_MIN = 8


def _date_fijo(destino: Path) -> Path:
    """Un `date` de arnés: la hora base es `_AHORA_DEL_RELOJ` y el `-d "+N minutes"`
    del guión se aplica sobre ella. Todo lo demás se delega al `date` real."""
    real = shutil.which("date")
    assert real is not None, "no hay `date` en el PATH"
    binarios = destino / "bin-date-fijo"
    binarios.mkdir(exist_ok=True)
    guion = binarios / "date"
    guion.write_text(
        "#!/bin/sh\n"
        f'base="{_AHORA_DEL_RELOJ.strftime("%Y-%m-%dT%H:%M:%SZ")}"\n'
        'desplazamiento=""\n'
        'formato=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in\n'
        "    -u) ;;\n"
        '    -d) desplazamiento="$2"; shift ;;\n'
        '    +*) formato="$1" ;;\n'
        "  esac\n"
        "  shift\n"
        "done\n"
        f'exec "{real}" -u -d "${{base}} ${{desplazamiento}}" ${{formato:+"$formato"}}\n',
        encoding="utf-8",
    )
    guion.chmod(0o755)
    return binarios


def _cuerpo_con_perfil(perfil: str) -> str:
    """Un cuerpo de incidencia mínimo con su campo ``Perfil:``, como lo escribe el despachador.

    Desde C3 (ADR-088) el workflow ELIGE el prompt leyendo ese campo, así que
    ejecutar su guión sin cuerpo ya no reproduce nada: muere por variable no
    definida. Dárselo aquí no es maquillar el fallo -es darle el mismo dato que
    el `env:` del paso le da en producción. La versión se lee del PERFIL, como
    hace el despachador real: clavar aquí un @N a mano haría que esta prueba
    comparase la proyección vigente contra un prompt congelado de otra versión
    (le pasó con implementer@3, ADR-145).
    """
    try:
        version = load_agent_profile(perfil).version
    except UnknownAgentProfileError:
        # Un perfil desconocido tiene que llegar AL GUIÓN y morir allí
        # (test_un_perfil_desconocido_...): el fixture no le hace de puerta.
        version = 1
    return f"## Bloque\n\nENCARGO\n\nPerfil: {perfil}@{version}\n\n## Objetivo\n\nlo que sea\n"


def _ejecutar_paso_build_prompt(
    *,
    repo: str,
    issue_number: int,
    tmp_path: Path,
    perfil: str = "implementer",
    consumido_min: int = _CONSUMIDO_DEL_ARNES_MIN,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Ejecutar el guión bash REAL del paso del prompt (leído, no reescrito).

    `JOB_ARRANQUE_EPOCH` es lo que en producción deja el paso «Anotar el arranque
    del job»: aquí, `consumido_min` minutos antes de la hora fija del arnés.
    """
    script = _extraer_paso_build_prompt()
    # Un fichero por invocación, y no por pulcritud: el guión ANEXA a
    # `$GITHUB_OUTPUT`, así que dos llamadas sobre el mismo fichero hacen que la
    # segunda lea el heredoc de la primera. Se descubrió porque una prueba que
    # comparaba dos perfiles los vio idénticos: el fallo estaba en el arnés, no
    # en el workflow.
    output_path = tmp_path / f"github_output-{perfil}-{consumido_min}.txt"
    entorno = dict(os.environ)
    entorno.update(
        {
            "GH_REPO": repo,
            "ISSUE_NUMBER": str(issue_number),
            "GITHUB_OUTPUT": str(output_path),
            "RUNNER_TEMP": str(tmp_path),
            "ISSUE_BODY": _cuerpo_con_perfil(perfil),
            "JOB_ARRANQUE_EPOCH": str(int(_AHORA_DEL_RELOJ.timestamp()) - consumido_min * 60),
            "PATH": f"{_date_fijo(tmp_path)}{os.pathsep}{os.environ.get('PATH', '')}",
        }
    )
    proceso = subprocess.run(
        ["bash", "-c", script],
        check=False,
        cwd=_REPO_ROOT,
        env=entorno,
        capture_output=True,
        text=True,
    )
    return proceso, output_path


def _prompt_real_del_workflow(
    *, repo: str, issue_number: int, tmp_path: Path, perfil: str = "implementer"
) -> str:
    """El prompt que el guión real deja en `$GITHUB_OUTPUT`; un guión que falla, falla aquí."""
    proceso, output_path = _ejecutar_paso_build_prompt(
        repo=repo, issue_number=issue_number, tmp_path=tmp_path, perfil=perfil
    )
    if proceso.returncode != 0:
        raise subprocess.CalledProcessError(
            proceso.returncode, proceso.args, proceso.stdout, proceso.stderr
        )
    contenido = output_path.read_text(encoding="utf-8")
    match = _HEREDOC_RE.search(contenido)
    assert match is not None, f"no se pudo extraer el heredoc 'prompt' de:\n{contenido}"
    return match.group(1)


def test_un_encargo_documental_ejecuta_el_prompt_documental_y_no_el_de_codigo(
    tmp_path: Path,
) -> None:
    """C3 (ADR-088): el guión REAL elige por el campo `Perfil:`, no por costumbre.

    Es la mitad del bloque que no se podía comprobar leyendo: hasta este cambio
    el prompt estaba clavado a fuego, así que un encargo documental habría
    ejecutado la vara del código -«una vuelta completa falsa», en palabras del
    propio implementador cuando se negó a entregarlo-.
    """
    documental = _prompt_real_del_workflow(
        repo="o/r", issue_number=1, tmp_path=tmp_path, perfil="documentalista"
    )
    de_codigo = _prompt_real_del_workflow(
        repo="o/r", issue_number=1, tmp_path=tmp_path, perfil="implementer"
    )

    assert documental != de_codigo, "el perfil documental no puede recibir el prompt de código"
    esperado = (_REPO_ROOT / "scripts/automation/prompts/documentalista.md").read_text(
        encoding="utf-8"
    )
    assert esperado.strip() in documental, (
        "el guión tiene que insertar documentalista.md, no solo nombrarlo"
    )


def test_un_perfil_desconocido_hace_fallar_el_guion_en_vez_de_elegir_uno(
    tmp_path: Path,
) -> None:
    """Ni repliegue silencioso ni adivinar (ADR-088).

    Un prompt elegido por descarte produce trabajo que PARECE hecho y publica su
    veredicto como bueno. Cuesta más que un workflow en rojo.
    """
    with pytest.raises(subprocess.CalledProcessError):
        _prompt_real_del_workflow(
            repo="o/r", issue_number=1, tmp_path=tmp_path, perfil="perfil-que-no-existe"
        )


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
        procedure_text=procedure_text,
        repo=repo,
        issue_number=issue_number,
        base_branch="main",
        ahora=_AHORA_DEL_RELOJ,
        consumido_min=_CONSUMIDO_DEL_ARNES_MIN,
    )

    assert obtenido == esperado
    assert "tu paso muere a las 2026-10-01T13:11:00Z UTC (71 minutos desde ahora" in esperado, (
        "el guión real lleva el reloj del implementador (ADR-228) calculado sobre la hora fija "
        "y sobre lo que el job le deja: 85 - 6 - 8 = 71"
    )
    assert "no más tarde de las 2026-10-01T12:46:00Z UTC" in esperado


def test_el_plazo_del_prompt_se_calcula_desde_el_arranque_del_job(tmp_path: Path) -> None:
    """Ronda 1 de Codex en la PR #675: un plazo fijo de 50 era mentira cuando la
    preparación era lenta (el job moría antes que el paso). El guión resta lo
    consumido desde `JOB_ARRANQUE_EPOCH` y publica el número en `plazo_min`,
    que es el `timeout-minutes` del paso del agente."""
    proceso, salida = _ejecutar_paso_build_prompt(
        repo="o/r", issue_number=1, tmp_path=tmp_path, consumido_min=30
    )
    assert proceso.returncode == 0, proceso.stderr
    contenido = salida.read_text(encoding="utf-8")
    assert "plazo_min=49\n" in contenido, contenido
    assert "(49 minutos desde ahora" in contenido
    assert "tu paso muere a las 2026-10-01T12:49:00Z UTC" in contenido
    assert "no más tarde de las 2026-10-01T12:24:00Z UTC" in contenido


def test_una_preparacion_que_se_come_el_plazo_no_arranca_al_agente_y_deja_el_veredicto(
    tmp_path: Path,
) -> None:
    """Por debajo del mínimo no se arranca al agente con un plazo que no da ni
    para validar: el guión falla, deja un veredicto FAILED_SAFELY que dice
    cuánto comió la preparación (lo publica «Aplicar el veredicto») y una
    salida válida para el `timeout-minutes` del paso que se salta."""
    proceso, salida = _ejecutar_paso_build_prompt(
        repo="o/r", issue_number=1, tmp_path=tmp_path, consumido_min=45
    )
    assert proceso.returncode != 0
    assert "No se arranca al agente" in proceso.stdout + proceso.stderr
    veredicto = json.loads((tmp_path / "sirius_verdict.json").read_text(encoding="utf-8"))
    assert veredicto["verdict"] == "FAILED_SAFELY"
    assert "consumió 45 minutos de los 85" in veredicto["summary"]
    assert "quedaban 34" in veredicto["summary"] and "mínimo de 40" in veredicto["summary"]
    contenido = salida.read_text(encoding="utf-8")
    assert "plazo_min=1\n" in contenido and "prompt<<" not in contenido


def test_la_proyeccion_exige_el_reloj_entero_o_ninguno() -> None:
    perfil = load_agent_profile("implementer")
    procedure_text = read_procedure_text(perfil)
    with pytest.raises(ValueError, match="van juntos"):
        project_github_prompt(
            procedure_text=procedure_text, repo="o/r", issue_number=1, ahora=_AHORA_DEL_RELOJ
        )
    with pytest.raises(ValueError, match="van juntos"):
        project_github_prompt(
            procedure_text=procedure_text, repo="o/r", issue_number=1, consumido_min=8
        )


def test_la_proyeccion_hace_la_misma_resta_que_el_workflow_y_se_niega_bajo_el_minimo() -> None:
    """`plazo_del_implementador` es la resta del guión (85 - 6 - consumido) y
    devuelve `None` por debajo del mínimo (40), que es cuando el workflow no
    arranca al agente; la proyección entonces no inventa un prompt."""
    assert plazo_del_implementador(8) == 71
    assert plazo_del_implementador(39) == 40
    assert plazo_del_implementador(40) is None
    perfil = load_agent_profile("implementer")
    procedure_text = read_procedure_text(perfil)
    with pytest.raises(ValueError, match="se comió el plazo"):
        project_github_prompt(
            procedure_text=procedure_text,
            repo="o/r",
            issue_number=1,
            ahora=_AHORA_DEL_RELOJ,
            consumido_min=45,
        )


def test_la_no_divergencia_vale_para_otra_incidencia_y_otro_repositorio(tmp_path: Path) -> None:
    perfil = load_agent_profile("implementer")
    procedure_text = read_procedure_text(perfil)

    repo = "otra-org/otro-repo"
    issue_number = 4242

    esperado = _prompt_real_del_workflow(repo=repo, issue_number=issue_number, tmp_path=tmp_path)
    obtenido = project_github_prompt(
        procedure_text=procedure_text,
        repo=repo,
        issue_number=issue_number,
        base_branch="main",
        ahora=_AHORA_DEL_RELOJ,
        consumido_min=_CONSUMIDO_DEL_ARNES_MIN,
    )

    assert obtenido == esperado


def test_sin_reloj_la_proyeccion_no_lleva_la_linea_del_plazo() -> None:
    """Sin `ahora` la proyección es el prompt de antes de ADR-228, y lo declara:
    una línea de plazo con una hora inventada sería peor que ninguna."""
    perfil = load_agent_profile("implementer")
    texto = project_github_prompt(
        procedure_text=read_procedure_text(perfil), repo="o/r", issue_number=1
    )
    assert "Plazo de esta ejecución" not in texto
    assert texto.endswith("SIRIUS_VERDICT_FILE.\n")


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

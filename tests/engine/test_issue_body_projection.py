"""El cuerpo generado pasa el validador REAL del contrato (C2-P2, incidencia #240).

Se ejercita ``scripts/automation/validate_issue_body.py`` como subproceso -la
misma vía que ``tests/automation/test_validate_issue_body.py``-, nunca una
copia de sus reglas: si el validador cambia sus secciones obligatorias, esta
prueba lo nota sin que nadie tenga que sincronizar dos copias.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item
from sirius_engine.issue_body_projection import generar_cuerpo_incidencia
from sirius_engine.profile_field import ProfileRef, parse_perfil_field

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "automation" / "validate_issue_body.py"


def _work_item() -> WorkItem:
    return create_work_item(
        work_id="SIRIUS-WORK-ENGINE-C2-DEMO-001",
        peticion_original="implementa el despachador end-to-end de programación",
        objetivo=(
            "Cerrar el círculo del propietario-no-mensajero para la clase programación: "
            "generar la incidencia desde la plantilla y aplicar la etiqueta de activación."
        ),
        contexto_origen=(
            "incidencia:240",
            "docs/implementation/AUTOMATION_OPERATING_CONTRACT.md#12.1",
        ),
        entregable="Un despachador C2 que crea la incidencia y aplica sirius:implement-requested.",
        criterio_terminado=(
            "Las seis pruebas de terminado C2-P1 a C2-P6 pasan, junto con las validaciones "
            "obligatorias del proyecto."
        ),
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        plan=("preparar", "ejecutar", "comprobar"),
    )


def _run_validator(body: str, path: Path) -> subprocess.CompletedProcess[str]:
    path.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)], capture_output=True, text=True, check=False
    )


def test_cuerpo_generado_pasa_el_validador_real(tmp_path: Path) -> None:
    cuerpo = generar_cuerpo_incidencia(
        _work_item(), profile_ref=ProfileRef(ref="implementer", version=1), bloque="C2"
    )
    resultado = _run_validator(cuerpo, tmp_path / "body.md")
    assert resultado.returncode == 0, resultado.stderr


def test_cuerpo_generado_declara_el_campo_perfil_de_a4() -> None:
    perfil = ProfileRef(ref="implementer", version=1)
    cuerpo = generar_cuerpo_incidencia(_work_item(), profile_ref=perfil, bloque="C2")
    assert parse_perfil_field(cuerpo) == perfil


def test_cuerpo_generado_proyecta_el_contenido_real_no_relleno() -> None:
    work_item = _work_item()
    cuerpo = generar_cuerpo_incidencia(
        work_item, profile_ref=ProfileRef(ref="implementer", version=1), bloque="C2"
    )
    assert work_item.work_id in cuerpo
    assert work_item.objetivo in cuerpo
    assert work_item.entregable in cuerpo
    assert work_item.criterio_terminado in cuerpo


def test_cuerpo_sin_contexto_origen_ni_plan_sigue_pasando_el_validador(tmp_path: Path) -> None:
    from dataclasses import replace

    work_item = replace(_work_item(), contexto_origen=(), plan=())
    cuerpo = generar_cuerpo_incidencia(
        work_item, profile_ref=ProfileRef(ref="implementer", version=1), bloque="C2"
    )
    resultado = _run_validator(cuerpo, tmp_path / "body.md")
    assert resultado.returncode == 0, resultado.stderr

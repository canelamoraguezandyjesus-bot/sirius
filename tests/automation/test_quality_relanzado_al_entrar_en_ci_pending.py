"""ADR-149: los workflows que aplican veredictos de avance dan al paso el token
de lectura de Actions y el permiso ``actions: read``, y el guion relanza
Quality en la rama de avance con la doctrina de tokens correcta (lectura con
el ``github.token``, relanzamiento con el token de la invocación, el PAT).

Guardianes textuales sobre el YAML y el guion: el comportamiento del
relanzamiento lo prueba ``test_sirius_apply_verdict.py`` con el ``gh``
simulado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
IMPLEMENT = WORKFLOWS / "implement-sirius-work.yml"
REPAIR = WORKFLOWS / "repair-sirius-work.yml"
GUION = REPO_ROOT / "scripts" / "automation" / "sirius_apply_verdict.sh"


def _documento(ruta: Path) -> dict[str, Any]:
    doc = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), ruta.name
    return doc


def _paso_del_veredicto(ruta: Path) -> dict[str, Any]:
    for job in _documento(ruta)["jobs"].values():
        for paso in job.get("steps", []):
            if paso.get("name") == "Aplicar el veredicto":
                assert isinstance(paso, dict)
                return paso
    raise AssertionError(f"{ruta.name}: no hay paso «Aplicar el veredicto»")


def test_los_dos_workflows_dan_el_token_de_lectura_al_veredicto() -> None:
    for ruta in (IMPLEMENT, REPAIR):
        env = _paso_del_veredicto(ruta).get("env") or {}
        assert env.get("SIRIUS_READ_TOKEN") == "${{ github.token }}", ruta.name
        assert env.get("GH_TOKEN") == "${{ secrets.SIRIUS_BOT_TOKEN }}", ruta.name


def test_los_dos_workflows_tienen_permiso_de_lectura_de_actions() -> None:
    for ruta in (IMPLEMENT, REPAIR):
        permisos = _documento(ruta).get("permissions") or {}
        assert permisos.get("actions") == "read", (
            f"{ruta.name}: el GET de runs de Quality va con el github.token y necesita actions:read"
        )


def test_el_guion_relanza_en_la_rama_de_avance_con_la_doctrina_de_tokens() -> None:
    guion = GUION.read_text(encoding="utf-8")
    rama = guion[guion.index("READY_FOR_REVIEW | FIXED)") : guion.index("CHECKS_UNRELATED)")]
    assert "relanzar_quality_si_ya_termino" in rama, (
        "la rama de avance ya no relanza Quality al entrar en ci-pending"
    )
    cuerpo = guion[
        guion.index("relanzar_quality_si_ya_termino() {") : guion.index("require_reviewed_head() {")
    ]
    assert cuerpo.count('export GH_TOKEN="${SIRIUS_READ_TOKEN') == 1, (
        "solo la LECTURA de runs va con el token de lectura; el POST de rerun "
        "tiene que ir con el token de la invocación (el PAT)"
    )
    assert "-X POST" in cuerpo and "/rerun" in cuerpo
    assert cuerpo.index('export GH_TOKEN="${SIRIUS_READ_TOKEN') < cuerpo.index("-X POST")

"""Lo que la documentación dice de la CI tiene que coincidir con los workflows.

El README afirmó durante tres semanas que Ruff, mypy y pytest corrían en Windows
en cada pull request y cada merge. Dejó de ser cierto el 21 de julio de 2026,
cuando el ciclo pasó a Linux por coste, y nadie lo notó: una afirmación sobre CI
solo se desmiente mirando los workflows, y nadie los mira al leer el README.

La comprobación se ata al DISPARADOR real, no a una lista negra de frases: así
no se esquiva reescribiendo la frase, y deja de aplicar sola el día que alguien
devuelva Windows al ciclo.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

DOCUMENTOS = (REPO_ROOT / "README.md", REPO_ROOT / "REPOSITORY_STATUS.md")

AFIRMA_WINDOWS_CONTINUO = re.compile(
    r"en Windows para cada (?:pull request|cambio)|GitHub Actions funciona en Windows",
    re.IGNORECASE,
)


def _hay_windows_en_cada_cambio() -> bool:
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        definicion = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        if not isinstance(definicion, dict):
            continue
        # `on` es la palabra reservada YES/ON: PyYAML la interpreta como True.
        disparadores = definicion.get("on", definicion.get(True, {})) or {}
        if isinstance(disparadores, str):
            disparadores = [disparadores]
        if not {"pull_request", "push"} & set(disparadores):
            continue
        for job in (definicion.get("jobs") or {}).values():
            if isinstance(job, dict) and "windows" in str(job.get("runs-on", "")):
                return True
    return False


def test_la_documentacion_no_promete_una_ci_de_windows_que_no_se_dispara() -> None:
    if _hay_windows_en_cada_cambio():
        return  # la afirmación sería cierta: no hay nada que comprobar

    for documento in DOCUMENTOS:
        encontrado = AFIRMA_WINDOWS_CONTINUO.findall(documento.read_text(encoding="utf-8"))
        assert not encontrado, (
            f"{documento.relative_to(REPO_ROOT)} afirma que la CI corre en Windows en cada "
            f"cambio ({encontrado}), y ningún workflow con `pull_request` o `push` usa un "
            "runner de Windows. La validación en Windows es puntual y bajo demanda."
        )

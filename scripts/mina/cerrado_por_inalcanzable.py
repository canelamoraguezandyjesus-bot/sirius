"""Cuantos defectos cerrados citan en `cerrado_por` un commit que `main` no contiene.

Medida de la propuesta 7 de la mina de septiembre: la convencion de dos commits
de la skill `registro-de-defectos` presupone fusiones que conservan el commit, y
el repositorio aplasta desde ADR-205. Uso:

    uv run python scripts/mina/cerrado_por_inalcanzable.py [--rama origin/main]

Para cada entrada `estado: cerrado` comprueba, con `git`, si el sha existe en el
clon y si es antepasado de la rama; para las inalcanzables busca la PR que
fusiono el ADR de la entrada (el titulo del commit aplastado lleva «(#N)»).
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import yaml

# Anclado a la raiz del repositorio, no al directorio de invocacion: la misma
# orden mide lo mismo desde la raiz y desde scripts/mina/ (Codex, PR #665).
RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "audits" / "registro_defectos.yml"
_PR = re.compile(r"\(#(\d+)\)")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=False)


def _pr_del_adr(adr: int, rama: str) -> str:
    salida = _git(
        "log", rama, "--diff-filter=A", "--format=%s", "--", f"docs/decisions/ADR-{adr:03d}-*"
    )
    lineas = salida.stdout.strip().splitlines()
    if not lineas:
        return "?"
    encontrada = _PR.search(lineas[-1])
    return f"#{encontrada.group(1)}" if encontrada else "?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rama", default="origin/main")
    argumentos = parser.parse_args()
    defectos = yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))["defectos"]
    cerrados = [d for d in defectos if d.get("estado") == "cerrado"]
    inalcanzables: list[tuple[str, str, str, str]] = []
    for entrada in cerrados:
        sha = str(entrada.get("cerrado_por", ""))
        if len(sha) != 40:
            inalcanzables.append((entrada["id"], sha, "no es un sha de 40", "?"))
            continue
        if _git("cat-file", "-e", sha).returncode != 0:
            motivo = "no existe en el clon"
        elif _git("merge-base", "--is-ancestor", sha, argumentos.rama).returncode != 0:
            motivo = f"no es antepasado de {argumentos.rama}"
        else:
            continue
        adr = entrada.get("adr")
        pr = _pr_del_adr(int(adr), argumentos.rama) if isinstance(adr, int) else "?"
        inalcanzables.append((entrada["id"], sha[:8], motivo, pr))
    print(
        f"cerrados: {len(cerrados)}; con cerrado_por inalcanzable desde "
        f"{argumentos.rama}: {len(inalcanzables)}"
    )
    for identificador, sha, motivo, pr in inalcanzables:
        print(f"  {identificador}: {sha} ({motivo}); PR del ADR: {pr}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

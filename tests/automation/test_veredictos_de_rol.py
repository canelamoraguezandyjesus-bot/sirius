"""El conjunto de veredictos de cada rol vive en dos ficheros, y deben coincidir.

Un rol obligado a elegir entre veredictos que **no describen su situación** es
lo que produce las paradas mudas. Ocurrió dos veces el mismo día, con dos
pruebas inestables distintas: Quality falló por algo ajeno, el corrector
comprobó que no era suyo —correctamente— y solo tenía `FIXED`, que presupone un
push. Sin push no hay evento, sin evento no hay Quality, y `sirius:ci-pending`
no avisa a nadie. La primera vez costó 45 minutos de silencio y una persona
pulsando «Re-run failed jobs».

`CHECKS_UNRELATED` cubre ese desenlace. Pero la correspondencia entre lo que el
prompt documenta y lo que `sirius_apply_verdict.sh` acepta se mantiene **a mano
en dos ficheros**, y desincronizarla es fácil y silencioso en la dirección
peligrosa: un veredicto documentado que el guion no acepta manda al rol a una
parada segura con un diagnóstico que no entiende nadie.

Estas pruebas atan las dos listas leyéndolas de los ficheros reales.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "automation"
PROMPTS_DIR = SCRIPTS_DIR / "prompts"
APPLY_VERDICT = SCRIPTS_DIR / "sirius_apply_verdict.sh"

# Prompt de cada rol y el nombre con el que `sirius_apply_verdict.sh` lo conoce.
ROLES = {
    "implementer.md": "implementer",
    "reviewer.md": "reviewer",
    "corrector.md": "corrector",
    "revisor-documental.md": "reviewer",
}


def _veredictos_que_acepta(rol: str) -> set[str]:
    """La lista `allowed=` de ese rol, leída del guion que de verdad decide."""
    texto = APPLY_VERDICT.read_text(encoding="utf-8")
    match = re.search(rf'{rol}\)\s*allowed="([^"]+)"', texto)
    assert match, f"no se encontró la lista de veredictos de '{rol}' en {APPLY_VERDICT.name}"
    return set(match.group(1).split())


def _veredictos_que_documenta(prompt: Path) -> set[str]:
    """Los veredictos que el prompt ofrece al rol, de su lista con viñetas.

    Se leen solo las viñetas de la forma ``- `VEREDICTO`:`` — la definición— y no
    cualquier mención en el texto, para que citar un veredicto en una
    explicación no lo dé por ofrecido.
    """
    texto = prompt.read_text(encoding="utf-8")
    return set(re.findall(r"^- `([A-Z_]+)`:", texto, re.MULTILINE))


def test_hay_prompts_que_comprobar() -> None:
    """Un glob vacío dejaría toda la familia en verde sin comprobar nada."""
    for nombre in ROLES:
        assert (PROMPTS_DIR / nombre).is_file(), f"falta el prompt {nombre}"


@pytest.mark.parametrize("prompt_name,rol", sorted(ROLES.items()))
def test_lo_que_el_prompt_ofrece_es_exactamente_lo_que_el_guion_acepta(
    prompt_name: str, rol: str
) -> None:
    """Las dos listas tienen que ser la misma, y en las dos direcciones.

    Sobra en el prompt: el rol emite un veredicto que el guion rechaza por
    `veredicto-fuera-de-conjunto`, y la ronda muere con un diagnóstico que
    describe un error de configuración, no su trabajo.

    Falta en el prompt: el rol nunca usa un desenlace que el sistema sí sabe
    tratar — que es exactamente cómo nació esta prueba. `CHECKS_UNRELATED`
    existía como necesidad mucho antes de tener nombre.
    """
    documentados = _veredictos_que_documenta(PROMPTS_DIR / prompt_name)
    aceptados = _veredictos_que_acepta(rol)
    assert documentados == aceptados, (
        f"{prompt_name} y {APPLY_VERDICT.name} no coinciden para '{rol}': "
        f"solo en el prompt {sorted(documentados - aceptados)}, "
        f"solo en el guion {sorted(aceptados - documentados)}"
    )


def test_el_corrector_puede_declarar_que_el_fallo_de_ci_no_es_suyo() -> None:
    """El desenlace concreto que motivó todo esto.

    No basta con que las listas coincidan: podrían coincidir en un conjunto que
    siga sin cubrir el caso. Esta prueba nombra el desenlace.
    """
    assert "CHECKS_UNRELATED" in _veredictos_que_acepta("corrector")
    assert "CHECKS_UNRELATED" in _veredictos_que_documenta(PROMPTS_DIR / "corrector.md")


def test_la_reejecucion_por_ci_ajeno_esta_acotada_a_una_por_commit() -> None:
    """Sin cota, `CHECKS_UNRELATED` convierte una construcción rota en un bucle.

    La cota vive en el dato publicado —el marcador con el head—, no en una
    variable del proceso: el corrector es otro proceso en cada ronda y no
    recuerda nada. Si el mismo commit vuelve a fallar, deja de ser intermitencia
    y pasa a decisión humana.
    """
    texto = APPLY_VERDICT.read_text(encoding="utf-8")
    inicio = texto.index("CHECKS_UNRELATED)")
    rama = texto[inicio : texto.index("REVIEW_APPROVED)", inicio)]

    assert "sirius-verdict:corrector:CHECKS_UNRELATED:${head_sha}" in rama, (
        "la cota debe comprobarse contra el marcador del head, que es lo único que persiste"
    )
    assert "ci-ajeno-reincidente" in rama, "un segundo fallo sobre el mismo head debe parar"
    assert "sin-fallo-de-ci-que-atribuir" in rama, (
        "el veredicto solo vale si hubo un CI_FAILURE para este head"
    )
    assert "rerun-failed-jobs" in rama, "debe reejecutar los trabajos fallidos"

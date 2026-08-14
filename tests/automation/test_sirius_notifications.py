"""Una etiqueta notificable escrita con el GITHUB_TOKEN no notifica a nadie.

GitHub suprime los eventos que produce el `GITHUB_TOKEN` para evitar recursión
entre workflows. Cuando los tres roles se mudaron a Actions, las etiquetas
pasaron a escribirse con ese token y `notify-sirius-state.yml` dejó de recibir
el `issues: labeled` de `sirius:implementing` y `sirius:completed`: el contrato
§7 los declara notificables y nunca volvieron a avisar. No fue un estado
histórico, fue una regresión silenciosa.

Esta prueba DERIVA la lista de estados notificables del propio `notify` en vez
de copiarla. Copiarla dejaría dos listas que se desincronizan, que es el defecto
que la auditoría lleva corrigiendo en la documentación.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
NOTIFICADOR = WORKFLOWS / "notify-sirius-state.yml"

ETIQUETA_EN_CONDICION = re.compile(r"github\.event\.label\.name == '(sirius:[a-z-]+)'")

# Workflows que escriben una etiqueta notificable, y la marca que demuestra que
# lo hacen con la identidad real. Se comprueba el fichero entero y no un paso
# concreto: enumerar pasos por nombre se esquiva renombrando el paso.
ESCRITORES = (
    "implement-sirius-work.yml",
    "complete-sirius-after-merge.yml",
    "repair-sirius-work.yml",
    "advance-sirius-after-quality.yml",
)


def _estados_notificables() -> set[str]:
    return set(ETIQUETA_EN_CONDICION.findall(NOTIFICADOR.read_text(encoding="utf-8")))


def test_el_notificador_sigue_declarando_los_seis_estados_del_contrato() -> None:
    # Sin esto, la prueba siguiente se satisface vaciando el `if:` del notificador.
    estados = _estados_notificables()
    assert estados == {
        "sirius:implementing",
        "sirius:repair-requested",
        "sirius:ready-for-merge",
        "sirius:blocked-decision",
        "sirius:failed-safely",
        "sirius:completed",
    }, f"El contrato §7 declara seis estados notificables; el notificador escucha {estados}."


def test_quien_escribe_una_etiqueta_notificable_usa_la_identidad_real() -> None:
    """Por PASO y no por fichero.

    Comprobar que el fichero «contiene» el PAT en alguna parte se satisface con
    cualquier otra aparición —el `checkout`, la acción de Claude— y deja pasar
    justo el defecto que se quiere impedir. Se comprobó midiendo: la primera
    versión de esta prueba pasaba con la mutación puesta.
    """
    for nombre in ESCRITORES:
        ruta = WORKFLOWS / nombre
        definicion = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        pasos = [
            paso
            for job in (definicion.get("jobs") or {}).values()
            for paso in (job.get("steps") or [])
            if isinstance(paso, dict)
        ]
        escritores = [paso for paso in pasos if _escribe_etiqueta(str(paso.get("run") or ""))]
        assert escritores, f"{nombre} figura como escritor y ningún paso escribe etiquetas."

        for paso in escritores:
            entorno = paso.get("env") or {}
            guion = str(paso.get("run") or "")
            por_entorno = "SIRIUS_BOT_TOKEN" in str(entorno.get("GH_TOKEN", ""))
            por_subshell = (
                re.search(r'export GH_TOKEN="\$\{?SIRIUS_TRIGGER_TOKEN', guion) is not None
                and "SIRIUS_BOT_TOKEN" in str(entorno.get("SIRIUS_TRIGGER_TOKEN", ""))
            )
            assert por_entorno or por_subshell, (
                f"{nombre}, paso «{paso.get('name', 'sin nombre')}»: escribe una etiqueta "
                "notificable con el GITHUB_TOKEN. GitHub suprime ese `issues: labeled` "
                "y la notificación no llega nunca."
            )


# Regla ancha a propósito: TODO paso que escriba etiquetas usa la identidad
# real, se llame como se llame el estado que escribe. La regla estrecha —«solo
# los pasos que AÑADEN un estado notificable»— exigiría deducir del texto del
# comando qué argumento añade y cuál quita, que es reconstruir desde fuera la
# semántica de otro sistema (ADR-001, quince defectos). El coste de la ancha es
# algún evento que nadie consume; el de la estrecha, una notificación perdida.
ESCRITURAS_DE_ETIQUETA = ("sirius_set_issue_labels", "sirius_transition", "sirius_apply_verdict.sh")


def _escribe_etiqueta(guion: str) -> bool:
    return any(llamada in guion for llamada in ESCRITURAS_DE_ETIQUETA)

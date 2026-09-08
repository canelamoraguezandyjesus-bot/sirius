"""Arnés que EJECUTA las puertas de carril retirado con un `gh` doble (ADR-167).

No comprueba cadenas del YAML: extrae el guion real del paso, lo corre con
`bash` y devuelve lo observable —código de salida, `GITHUB_OUTPUT`, etiquetas
finales, comentarios publicados y la lista de llamadas a `gh`—. Es lo único que
distingue «llama a `sirius_comment_once`» de «lo llama y comprueba el resultado»,
que es exactamente el defecto que ADR-167 corrige.

Sin red y sin credenciales: el doble vive en `gh` (mismo directorio) y el estado
de la incidencia es un JSON local.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[4]
DOBLE_GH = Path(__file__).resolve().parent / "gh"


@dataclass(frozen=True, slots=True)
class Resultado:
    """Lo observable de una ejecución del paso: nada de esto es una cadena del YAML."""

    codigo: int
    github_output: str
    etiquetas: list[str]
    comentarios: list[str]
    estado_incidencia: str
    llamadas_gh: list[str]
    stdout: str
    stderr: str

    @property
    def valid(self) -> str | None:
        for linea in self.github_output.splitlines():
            if linea.startswith("valid="):
                return linea.split("=", 1)[1]
        return None

    @property
    def retirado(self) -> str | None:
        for linea in self.github_output.splitlines():
            if linea.startswith("retirado="):
                return linea.split("=", 1)[1]
        return None


def guion_del_paso(workflow: str, job: str, step_id: str) -> str:
    datos: dict[str, Any] = yaml.safe_load(
        (RAIZ / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    )
    for paso in datos["jobs"][job]["steps"]:
        if paso.get("id") == step_id:
            return str(paso["run"])
    raise AssertionError(f"{workflow}: no existe el paso {step_id!r} en {job!r}")


def ejecutar_paso(
    workflow: str,
    job: str,
    step_id: str,
    *,
    tmp_path: Path,
    incidencia: dict[str, Any],
    fallar: str = "",
    ambiguo: bool = False,
    basura: bool = False,
    cuerpo_del_evento: str | None = None,
    entorno: dict[str, str] | None = None,
    codigo_del_lector: int | None = None,
    registro: Path | None = None,
) -> Resultado:
    """Corre el guion real del paso contra el doble y devuelve lo observable."""
    trabajo = tmp_path
    binarios = trabajo / "bin"
    binarios.mkdir(parents=True, exist_ok=True)
    destino = binarios / "gh"
    destino.write_text(DOBLE_GH.read_text(encoding="utf-8"), encoding="utf-8")
    destino.chmod(0o755)

    if codigo_del_lector is not None:
        # Un `python3` que sale con el código pedido SOLO para el lector del
        # registro, y que para todo lo demás delega en el intérprete de verdad.
        #
        # Aislar así la variable es lo que hace concluyente la prueba: un shim
        # que rompiera TODAS las llamadas a `python3` haría fallar también al
        # validador de activación, y la puerta se detendría por ese otro motivo.
        # Parecería correcta sin serlo. Rompiendo solo el lector, lo que se
        # observa es exactamente lo que la puerta concluye del código que no
        # entiende. (Un PATH falso entero tampoco vale: se lleva por delante al
        # propio intérprete.)
        real = subprocess.run(
            ["bash", "-c", "command -v python3"], capture_output=True, text=True
        ).stdout.strip()
        interprete = binarios / "python3"
        interprete.write_text(
            "#!/bin/sh\n"
            'case "$*" in\n'
            f"  *sirius_carril_retirado.py*) exit {codigo_del_lector} ;;\n"
            f'esac\nexec "{real}" "$@"\n',
            encoding="utf-8",
        )
        interprete.chmod(0o755)

    estado = trabajo / "incidencia.json"
    estado.write_text(json.dumps(incidencia, ensure_ascii=False), encoding="utf-8")
    bitacora = trabajo / "llamadas.txt"
    bitacora.touch()
    salida = trabajo / "github_output.txt"
    salida.touch()
    guion = trabajo / "paso.sh"
    guion.write_text(guion_del_paso(workflow, job, step_id), encoding="utf-8")

    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{binarios}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_STATE": str(estado),
            "FAKE_GH_LOG": str(bitacora),
            "FAKE_GH_FAIL": fallar,
            "FAKE_GH_FAIL_AMBIGUO": "1" if ambiguo else "",
            "FAKE_GH_BASURA": "1" if basura else "",
            "GITHUB_OUTPUT": str(salida),
            "RUNNER_TEMP": str(trabajo),
            "GH_TOKEN": "token-efimero",
            "SIRIUS_TRIGGER_TOKEN": "pat-del-bot",
            "GH_REPO": "duenyo/repo",
            "ISSUE_NUMBER": "1",
            "ISSUE_BODY": (
                cuerpo_del_evento
                if cuerpo_del_evento is not None
                else str(incidencia.get("body", ""))
            ),
            # Plazos cortos: el arnés no debe tardar, y el reintento de
            # `sirius_comment_once` tiene que agotarse en la prueba, no en CI.
            "SIRIUS_COMMENT_BUDGET_SECONDS": "3",
            "SIRIUS_RETRY_BASE_DELAY": "0",
        }
    )
    if registro is not None:
        # Registro CONTROLADO: el guion del paso llama al lector sin
        # `--registro`, así que la única forma de probarlo contra otra
        # configuración -una reactivación, por ejemplo- sin tocar el registro
        # real es esta variable.
        env["SIRIUS_CARRILES_RETIRADOS"] = str(registro)
    if entorno:
        env.update(entorno)

    proceso = subprocess.run(
        ["bash", "--noprofile", "--norc", str(guion)],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=env,
    )
    final: dict[str, Any] = json.loads(estado.read_text(encoding="utf-8"))
    return Resultado(
        codigo=proceso.returncode,
        github_output=salida.read_text(encoding="utf-8"),
        etiquetas=list(final.get("labels", [])),
        comentarios=list(final.get("comments", [])),
        estado_incidencia=str(final.get("state", "open")),
        llamadas_gh=bitacora.read_text(encoding="utf-8").splitlines(),
        stdout=proceso.stdout,
        stderr=proceso.stderr,
    )


#: Las secciones que `validate_issue_body.py` exige a una orden real. Se
#: reproducen aquí para que el arnés pueda ejercitar el camino COMPLETO -incluida
#: la validación de activación de siempre- y no solo la puerta de retirada.
_SECCIONES = (
    "Work ID",
    "Bloque",
    "Objetivo",
    "Base y dependencias",
    "Alcance permitido",
    "Fuera de alcance",
    "Requisitos y pruebas de aceptación",
    "Validaciones obligatorias",
    "Rama base",
    "Condiciones de parada",
    "Salvaguardas",
)


def cuerpo_de_orden(perfil: str = "investigador") -> str:
    """El cuerpo de una orden estructuralmente completa, con el perfil pedido."""
    secciones = "\n".join(f"## {s}\n\nContenido de prueba para {s.lower()}.\n" for s in _SECCIONES)
    return f"Perfil: {perfil}@2\n\n{secciones}"


def incidencia_activa(**cambios: Any) -> dict[str, Any]:
    """Una activación sana de investigación: `planned` + `implement-requested`."""
    base: dict[str, Any] = {
        "labels": ["sirius:planned", "sirius:implement-requested"],
        "comments": [],
        "state": "open",
        "body": cuerpo_de_orden(),
    }
    base.update(cambios)
    return base

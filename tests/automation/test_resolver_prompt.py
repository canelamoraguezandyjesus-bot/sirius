"""Pruebas de ``scripts/automation/resolver_prompt.py`` (H-28, incidencia #396).

El defecto: los workflows extraían el rol de ``Perfil: rol@N`` TIRANDO la
versión y leían el prompt vigente de main — ``implementer@1`` podía significar
dos textos distintos en dos Runs. La ley nueva: el manifiesto
(``scripts/automation/prompts/manifiesto.json``) es quien dice qué texto es
cada ``rol@N``, con el sha256 de sus bytes, y el resolver falla EN ROJO ante
cualquier cosa que no pueda afirmar: versión desconocida, rol desconocido,
campo ausente, o texto que ya no coincide con la versión declarada.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "resolver_prompt.py"
MANIFIESTO = REPO_ROOT / "scripts" / "automation" / "prompts" / "manifiesto.json"

WORKFLOW_IMPLEMENT = REPO_ROOT / ".github" / "workflows" / "implement-sirius-work.yml"
WORKFLOW_REVIEW = REPO_ROOT / ".github" / "workflows" / "review-sirius-work.yml"


def _cargar_modulo() -> ModuleType:
    spec = importlib.util.spec_from_file_location("resolver_prompt", SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def resolver() -> ModuleType:
    return _cargar_modulo()


def _lineas_de_codigo(texto: str) -> list[str]:
    """Solo líneas que no son comentarios: la familia vacua mordió CUATRO veces
    en un día por contar patrones dentro de comentarios o docstrings."""
    return [linea for linea in texto.splitlines() if not linea.strip().startswith("#")]


# --- resolución contra el manifiesto real ---------------------------------------------


def test_resuelve_la_fila_exacta_del_manifiesto(resolver: ModuleType) -> None:
    ruta = resolver.resolver_prompt("Perfil: implementer@1", carril="ejecucion", raiz=REPO_ROOT)
    assert ruta == Path("scripts/automation/prompts/implementer.md")
    assert (REPO_ROOT / ruta).is_file()


def test_el_carril_de_revision_da_el_revisor_del_ejecutor(resolver: ModuleType) -> None:
    """Quien revisa depende de quién implementó: la llave es el perfil del
    EJECUTOR declarado en el cuerpo, no el perfil propio del revisor."""
    ruta = resolver.resolver_prompt("Perfil: investigador@1", carril="revision", raiz=REPO_ROOT)
    assert ruta == Path("scripts/automation/prompts/revisor-documental.md")


def test_una_version_desconocida_de_un_rol_conocido_para_en_rojo(
    resolver: ModuleType,
) -> None:
    """LA prueba de H-28: hoy la versión se tira y ``implementer@99`` ejecutaría
    el prompt vigente tan campante. Con el manifiesto, es parada visible."""
    with pytest.raises(resolver.ResolucionImposible) as exc:
        resolver.resolver_prompt("Perfil: implementer@99", carril="ejecucion", raiz=REPO_ROOT)
    assert "implementer@99" in str(exc.value)


def test_un_rol_desconocido_para_en_rojo(resolver: ModuleType) -> None:
    with pytest.raises(resolver.ResolucionImposible):
        resolver.resolver_prompt("Perfil: poeta@1", carril="ejecucion", raiz=REPO_ROOT)


def test_sin_campo_perfil_para_en_rojo(resolver: ModuleType) -> None:
    with pytest.raises(resolver.ResolucionImposible):
        resolver.resolver_prompt(
            "Un cuerpo sin el campo.\nperfil: implementer@1", carril="ejecucion", raiz=REPO_ROOT
        )


def test_el_parseo_es_el_de_profile_field(resolver: ModuleType) -> None:
    """El campo lo define ``sirius_engine.profile_field``: mismo módulo, no una
    copia del regex. Un cuerpo que ``parse_perfil_field`` no acepta (versión
    ausente) tampoco lo acepta el resolver."""
    assert resolver.parse_perfil_field is not None  # importado, no redefinido
    with pytest.raises(resolver.ResolucionImposible):
        resolver.resolver_prompt("Perfil: implementer", carril="ejecucion", raiz=REPO_ROOT)


# --- el manifiesto no puede pudrirse --------------------------------------------------


def test_cada_fila_del_manifiesto_apunta_a_un_fichero_real_con_su_sha256() -> None:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    filas = [
        (carril, clave, fila)
        for carril, filas_carril in manifiesto["carriles"].items()
        for clave, fila in filas_carril.items()
    ]
    assert filas, "un manifiesto vacío no gobierna nada"
    for carril, clave, fila in filas:
        fichero = REPO_ROOT / fila["fichero"]
        assert fichero.is_file(), f"{carril}/{clave}: {fila['fichero']} no existe"
        real = hashlib.sha256(fichero.read_bytes()).hexdigest()
        assert real == fila["sha256"], (
            f"{carril}/{clave}: el texto de {fila['fichero']} ya no es el registrado. "
            "Si el cambio es deliberado, registra una versión nueva en el manifiesto "
            "y sube la versión del perfil; no se edita una versión publicada."
        )


def test_las_llaves_despachables_estan_en_el_manifiesto() -> None:
    """Las llaves que ``TABLA_PERFILES`` puede proyectar hacia estos dos
    workflows tienen fila: si un perfil sube de versión sin fila nueva, esto
    se pone en rojo AQUÍ, no en el workflow en producción."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from sirius_engine.dispatch_cli import TABLA_PERFILES
        from sirius_engine.domain.work_item import WorkItemClass
    finally:
        sys.path.pop(0)
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    ejecucion = manifiesto["carriles"]["ejecucion"]
    revision = manifiesto["carriles"]["revision"]
    # Ejecución: las clases que atiende implement-sirius-work.yml (ADR-088).
    for clase in (WorkItemClass.PROGRAMACION, WorkItemClass.DOCUMENTACION):
        perfil = TABLA_PERFILES[clase]
        assert f"{perfil.ref}@{perfil.version}" in ejecucion
    # Revisión: también la investigación (su PR la revisa el revisor documental).
    for clase in (
        WorkItemClass.PROGRAMACION,
        WorkItemClass.DOCUMENTACION,
        WorkItemClass.INVESTIGACION,
    ):
        perfil = TABLA_PERFILES[clase]
        assert f"{perfil.ref}@{perfil.version}" in revision


def test_un_prompt_editado_sin_registrar_version_nueva_para_en_rojo(
    resolver: ModuleType, tmp_path: Path
) -> None:
    """Fail-closed: mover el texto sin registrar versión convierte «texto
    distinto en silencio» en «parada que se ve»."""
    prompt = tmp_path / "scripts" / "automation" / "prompts" / "rol.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("texto de la versión 1\n", encoding="utf-8")
    manifiesto = {
        "version": 1,
        "carriles": {
            "ejecucion": {
                "rol@1": {
                    "fichero": "scripts/automation/prompts/rol.md",
                    "sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                }
            }
        },
    }
    (prompt.parent / "manifiesto.json").write_text(json.dumps(manifiesto), encoding="utf-8")
    # Con el texto intacto resuelve.
    assert resolver.resolver_prompt("Perfil: rol@1", carril="ejecucion", raiz=tmp_path)
    # Editado sin registrar: rojo, y el mensaje nombra el remedio.
    prompt.write_text("texto RETOCADO sin subir versión\n", encoding="utf-8")
    with pytest.raises(resolver.ResolucionImposible) as exc:
        resolver.resolver_prompt("Perfil: rol@1", carril="ejecucion", raiz=tmp_path)
    assert "versión" in str(exc.value)


# --- el CLI que ejecuta el runner -----------------------------------------------------


def _cli(cuerpo: str, carril: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--carril", carril],
        env={**os.environ, "ISSUE_BODY": cuerpo},
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_el_cli_imprime_solo_la_ruta_y_sale_cero() -> None:
    proceso = _cli("Perfil: documentalista@1\nOtra línea", "ejecucion")
    assert proceso.returncode == 0, proceso.stderr
    assert proceso.stdout.strip() == "scripts/automation/prompts/documentalista.md"


def test_el_cli_para_en_rojo_con_version_desconocida() -> None:
    proceso = _cli("Perfil: documentalista@99", "ejecucion")
    assert proceso.returncode != 0
    assert "::error::" in proceso.stderr
    assert "documentalista@99" in proceso.stderr


# --- los workflows llaman al resolver de verdad ---------------------------------------


def test_los_dos_workflows_invocan_al_resolver_y_el_case_viejo_no_existe() -> None:
    for workflow, carril in ((WORKFLOW_IMPLEMENT, "ejecucion"), (WORKFLOW_REVIEW, "revision")):
        codigo = "\n".join(_lineas_de_codigo(workflow.read_text(encoding="utf-8")))
        invocaciones = codigo.count(
            f"python3 scripts/automation/resolver_prompt.py --carril {carril}"
        )
        assert invocaciones == 1, (
            f"{workflow.name}: esperaba exactamente 1 invocación del resolver "
            f"con --carril {carril}, hay {invocaciones}"
        )
        # El mecanismo viejo -case con rutas a fuego que tiraba la versión- no
        # puede seguir vivo en paralelo. (La puerta del implementador conserva
        # un sed sobre `Perfil:` para ENRUTAR -qué workflow atiende, ADR-099-;
        # eso no elige texto y queda fuera de la ley de H-28.)
        assert "PROMPT_ROL=scripts/automation/prompts/" not in codigo, workflow.name

"""Las entradas de un carril retirado quedan cerradas, y las de los vivos no (ADR-162).

Lo que estas pruebas existen para impedir es el defecto que el inventario de
ADR-162 encontró: **una entrada retirada que se queda esperando, o que acaba en
programación por otra ruta**. Investigación comparte la etiqueta de activación
con programación y se reparte por el campo ``Perfil:``; si se desactivara solo
``investigar-orden.yml`` la activación quedaría colgada, y si se quitara la
puerta del implementador se implementaría como programación.

La prueba que de verdad ata es
:func:`test_toda_entrada_de_un_carril_retirado_esta_cubierta`: **enumera los
disparadores desde el árbol**, no de una lista escrita a mano, así que un
workflow nuevo que reaccione a esas etiquetas y no consulte el registro la hace
caer. Una lista a mano se queda vieja el día que alguien añade un fichero.

Deterministas: leen ficheros, ejecutan guiones de shell sin red y usan un
registro de prueba. No lanzan ningún agente ni gastan ninguna API.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "docs" / "implementation" / "work_engine" / "carriles_retirados.json"
LECTOR = RAIZ / "scripts" / "automation" / "sirius_carril_retirado.py"
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Los carriles que ADR-161 retira, y la etiqueta por la que entra cada uno.
CARRILES = {"investigacion": "sirius:implement-requested", "auditoria": "auditoria:solicitada"}


def _registro() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(REGISTRO.read_text(encoding="utf-8"))
    return datos


def _workflow(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((WORKFLOWS / nombre).read_text(encoding="utf-8"))
    return datos


def _pasos(nombre: str, job: str) -> list[dict[str, Any]]:
    pasos: list[dict[str, Any]] = _workflow(nombre)["jobs"][job]["steps"]
    return pasos


def _guion(nombre: str, job: str, step_id: str) -> str:
    for paso in _pasos(nombre, job):
        if paso.get("id") == step_id:
            return str(paso["run"])
    raise AssertionError(f"{nombre}: no existe el paso {step_id!r} en {job!r}")


def _ejecutar(guion: str, tmp_path: Path, **entorno: str) -> tuple[int, str, str]:
    fichero = tmp_path / "paso.sh"
    fichero.write_text(guion, encoding="utf-8")
    salida = tmp_path / "github_output.txt"
    salida.touch()
    env = dict(os.environ)
    env.update(
        {
            "GITHUB_OUTPUT": str(salida),
            "RUNNER_TEMP": str(tmp_path),
            "GH_TOKEN": "",
            "SIRIUS_TRIGGER_TOKEN": "",
            "GH_REPO": "duenyo/repo",
            "ISSUE_NUMBER": "1",
        }
    )
    env.update(entorno)
    proceso = subprocess.run(
        ["bash", "--noprofile", "--norc", str(fichero)],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=env,
    )
    return proceso.returncode, salida.read_text(encoding="utf-8"), proceso.stdout


# --------------------------------------------------------------------------
# El registro
# --------------------------------------------------------------------------


def test_el_registro_declara_los_dos_carriles_retirados() -> None:
    carriles: dict[str, Any] = _registro()["carriles"]
    assert set(carriles) == set(CARRILES), (
        "el registro tiene que declarar exactamente los carriles que ADR-161 retira"
    )
    for clase, fila in carriles.items():
        datos: dict[str, Any] = fila
        for campo in ("retirado_por", "ejecutado_por", "fecha", "motivo", "a_donde_va"):
            assert str(datos.get(campo, "")).strip(), f"{clase}: falta el campo {campo!r}"


def test_la_clase_sigue_en_la_tabla_de_activacion_y_en_el_contrato() -> None:
    """Retirar no es borrar: la fila se conserva, y por eso reactivar es una línea.

    Si alguien 'limpiara' `TABLA_ACTIVACION`, el rechazo pasaría a ser
    `ClaseNoDespachableError` -«esta clase nunca tuvo despachador»- y se
    perdería la distinción que ADR-162 existe para conservar.
    """
    from sirius_engine.dispatcher import TABLA_ACTIVACION
    from sirius_engine.domain.work_item import WorkItemClass

    assert WorkItemClass.INVESTIGACION in TABLA_ACTIVACION
    assert WorkItemClass.AUDITORIA in TABLA_ACTIVACION


# --------------------------------------------------------------------------
# El despachador
# --------------------------------------------------------------------------


@pytest.mark.parametrize("clase", sorted(CARRILES))
def test_el_despachador_rechaza_un_carril_retirado_con_su_explicacion(clase: str) -> None:
    from sirius_engine.carriles_retirados import carril_retirado

    entrada = carril_retirado(clase)
    assert entrada is not None, f"{clase} debería constar como retirado"
    explicacion = entrada.explicacion()
    assert "retirado" in explicacion
    assert "A dónde va ahora" in explicacion, "quien lo pide tiene que saber a dónde ir"
    assert "carriles_retirados.json" in explicacion, "y cómo se revierte"


@pytest.mark.parametrize("clase", ["programacion", "documentacion"])
def test_las_clases_vivas_no_constan_retiradas(clase: str) -> None:
    from sirius_engine.carriles_retirados import carril_retirado

    assert carril_retirado(clase) is None


def test_el_rechazo_del_despachador_es_un_error_propio_y_no_el_generico() -> None:
    """`nunca tuvo despachador` y `lo tuvo y se retiró` no son lo mismo."""
    from sirius_engine.domain.errors import CarrilRetiradoError, ClaseNoDespachableError

    assert issubclass(CarrilRetiradoError, Exception)
    # Que mypy sepa que son tipos distintos es justo lo que se quiere: la prueba
    # fija que el despachador NO reutiliza el error genérico, y por eso compara
    # los nombres -comparar los tipos sería una identidad que el comprobador ya
    # resuelve, y no probaría nada en ejecución-.
    assert CarrilRetiradoError.__name__ != ClaseNoDespachableError.__name__
    assert not issubclass(CarrilRetiradoError, ClaseNoDespachableError)


# --------------------------------------------------------------------------
# El lector que usan los workflows
# --------------------------------------------------------------------------


@pytest.mark.parametrize("clase", sorted(CARRILES))
def test_el_lector_del_runner_dice_retirado_con_codigo_cero(clase: str) -> None:
    proceso = subprocess.run(
        [sys.executable, str(LECTOR), clase], capture_output=True, text=True, cwd=RAIZ
    )
    assert proceso.returncode == 0, proceso.stderr
    assert "retirado" in proceso.stdout


def test_el_lector_del_runner_dice_activo_con_codigo_uno() -> None:
    proceso = subprocess.run(
        [sys.executable, str(LECTOR), "programacion"], capture_output=True, text=True, cwd=RAIZ
    )
    assert proceso.returncode == 1


def test_un_registro_ilegible_no_se_lee_como_carril_activo(tmp_path: Path) -> None:
    """Fail-closed en la afirmación: no poder leer no es «está activo».

    Si un registro roto devolviera 1, el workflow concluiría que el carril sigue
    vivo y dejaría pasar el trabajo por un carril retirado.
    """
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    proceso = subprocess.run(
        [sys.executable, str(LECTOR), "auditoria", "--registro", str(roto)],
        capture_output=True,
        text=True,
        cwd=RAIZ,
    )
    assert proceso.returncode == 2, "un registro ilegible tiene que salir con 2, no con 0 ni con 1"


# --------------------------------------------------------------------------
# Las entradas reales, enumeradas desde el árbol
# --------------------------------------------------------------------------


def test_toda_entrada_de_un_carril_retirado_esta_cubierta() -> None:
    """La guarda que no envejece: enumera los disparadores, no los da por sabidos.

    Cualquier workflow que reaccione a una de las dos etiquetas de entrada tiene
    que consultar el registro, o declarar por qué no le hace falta. Añadir uno
    nuevo sin cerrarlo hace caer esta prueba.
    """
    # El implementador reacciona a la etiqueta compartida y NO consulta el
    # registro a propósito: su papel es declinar el perfil para que el carril
    # retirado lo atienda quien sabe responderlo. Se declara aquí, con su
    # motivo, en vez de dejarlo como un hueco silencioso.
    exentos = {
        # Declina el perfil `investigador` ANTES de consumir el evento: no
        # atiende el carril, lo aparta para que lo atienda quien sabe cerrarlo.
        "implement-sirius-work.yml": "declina el perfil investigador; no lo atiende",
        # Solo valida que la activación sea legítima y retira el evento si no lo
        # es. No ejecuta ningún carril, así que no tiene nada que cerrar. Lo
        # encontró esta misma prueba, que por eso enumera en vez de suponer.
        "validate-sirius-activation.yml": "valida la activación; no atiende ningún carril",
    }

    sin_cubrir: list[str] = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        texto = ruta.read_text(encoding="utf-8")
        datos = yaml.safe_load(texto)
        # `on` lo lee PyYAML como el booleano True: es la trampa de YAML 1.1.
        disparadores = datos.get("on", datos.get(True, {})) if isinstance(datos, dict) else {}
        if not isinstance(disparadores, dict) or "issues" not in disparadores:
            continue
        for clase, etiqueta in CARRILES.items():
            if etiqueta not in texto:
                continue
            if ruta.name in exentos:
                continue
            assert "sirius_carril_retirado.py" in texto, (
                f"{ruta.name} reacciona a {etiqueta!r} (carril {clase!r}, retirado) y no "
                "consulta el registro de carriles retirados: una activación por ahí se "
                "quedaría esperando"
            )
    assert sin_cubrir == []


def test_la_puerta_del_implementador_sigue_declinando_el_perfil_investigador() -> None:
    """Sin ella, una activación de investigación se implementaría como programación.

    Es la decisión que ADR-161 dejó pendiente y que ADR-162 resuelve: la puerta
    se conserva. Esta prueba impide que una limpieza futura la quite.
    """
    guion = _guion("implement-sirius-work.yml", "implement", "gate")
    assert 'if [ "$perfil" = "investigador" ]' in guion
    assert "valid=false" in guion


def test_investigar_orden_no_investiga_y_no_deja_la_incidencia_esperando(tmp_path: Path) -> None:
    """La entrada se cierra: `valid=false` apaga todos los pasos que investigan."""
    guion = _guion("investigar-orden.yml", "investigar", "gate")
    codigo, salida, _ = _ejecutar(guion, tmp_path, ISSUE_BODY="Perfil: investigador@2\n")
    assert codigo == 0, "la puerta no puede morir: eso dejaría la incidencia en curso"
    assert "valid=false" in salida

    # Y lo que apaga `valid=false` son, de verdad, todos los pasos que gastan
    # el investigador: si mañana alguien añade uno sin esa condición, esto cae.
    pasos = _pasos("investigar-orden.yml", "investigar")
    caros = [
        p
        for p in pasos
        if p.get("id") in {"atender", "abrir_pr"} or "Atender" in str(p.get("name", ""))
    ]
    assert caros, "se esperaba encontrar los pasos que ejecutan al investigador"
    for paso in caros:
        assert "valid == 'true'" in str(paso.get("if", "")), (
            f"el paso {paso.get('name')!r} correría con el carril retirado"
        )


def test_investigar_orden_deja_la_incidencia_en_un_estado_terminal() -> None:
    """`failed-safely` es terminal: ni espera, ni reentra, ni cae en programación."""
    guion = _guion("investigar-orden.yml", "investigar", "gate")
    assert "sirius:failed-safely" in guion
    assert "sirius_comment_once" in guion, "tiene que explicarlo en la incidencia"


def test_el_auditor_no_ejecuta_el_modelo_y_publica_la_explicacion(tmp_path: Path) -> None:
    guion = _guion("audit-sirius-repository.yml", "auditar", "retirada")
    codigo, salida, _ = _ejecutar(guion, tmp_path)
    assert codigo == 0
    assert "retirado=true" in salida
    informe = (tmp_path / "sirius_audit_report.md").read_text(encoding="utf-8")
    assert "retirado" in informe
    assert "No se ha ejecutado ningun modelo" in informe

    # Y el paso que gasta el modelo queda condicionado a que NO esté retirado.
    pasos = _pasos("audit-sirius-repository.yml", "auditar")
    claude = [p for p in pasos if p.get("id") == "claude"]
    assert claude, "se esperaba el paso que ejecuta Claude"
    assert "retirada.outputs.retirado != 'true'" in str(claude[0].get("if", ""))


# --------------------------------------------------------------------------
# Lo que NO se toca
# --------------------------------------------------------------------------


def test_los_revisores_el_corrector_y_quality_siguen_intactos() -> None:
    """El encargo los conserva, y ninguno menciona el registro de retirados."""
    for nombre in (
        "review-sirius-work.yml",
        "repair-sirius-work.yml",
        "quality.yml",
        "advance-sirius-after-quality.yml",
    ):
        texto = (WORKFLOWS / nombre).read_text(encoding="utf-8")
        assert "sirius_carril_retirado" not in texto, f"{nombre} no debería haberse tocado"


def test_no_se_ha_borrado_nada_de_los_carriles_retirados() -> None:
    """Desactivar es reversible; borrar no. Estas piezas se conservan enteras."""
    conservados = [
        ".github/workflows/investigar-orden.yml",
        ".github/workflows/audit-sirius-repository.yml",
        "docs/implementation/AUDITOR_AGENT_V0.md",
        "docs/implementation/work_engine/perfiles/auditor.yml",
        "scripts/investigacion/investigar_orden.py",
        "scripts/investigacion/atender_orden.py",
        "docs/investigaciones/README.md",
    ]
    faltan = [ruta for ruta in conservados if not (RAIZ / ruta).exists()]
    assert faltan == [], f"la desactivación no puede borrar: faltan {faltan}"

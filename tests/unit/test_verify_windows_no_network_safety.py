"""Regresiones estructurales del verificador de red de B14.

`scripts/verify_windows_no_network.ps1` afirma algo fuerte —que abrir Sirius no
llama a nadie— y aqui no hay PowerShell que ejecutarlo, asi que se fijan las
propiedades de las que depende que esa afirmacion valga algo. Las mismas que ya
protegen al verificador de B13: el artefacto tiene que ser el del `HEAD`, el
proceso se arranca aislado, la limpieza va en un `finally`, y lo que no se puede
demostrar se declara en vez de callarse.
"""

from __future__ import annotations

from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_windows_no_network.ps1"


def _script() -> str:
    return _SCRIPT.read_text(encoding="utf-8")


def test_the_verifier_exists() -> None:
    assert _SCRIPT.is_file()


def test_it_refuses_to_run_elevated() -> None:
    """Sirius no necesita administrador, asi que no se prueba con administrador."""
    script = _script()
    elevation_check = script.index("IsInRole")
    launch = script.index("$process.Start()")

    assert elevation_check < launch
    assert "SIN elevar" in script[elevation_check:launch]


def test_it_only_watches_the_artifact_of_the_current_head() -> None:
    """Vigilar el paquete de otro commit no dice nada del codigo del arbol.

    Es la misma regla de procedencia que B13, y nace del mismo fallo real: un ZIP
    sobrante de una ronda anterior se valido y se acredito como si fuera el del
    repositorio.
    """
    script = _script()

    assert "package_provenance.py" in script
    assert "rev-parse --short HEAD" in script
    select = script.index('$provenance "select"')
    launch = script.index("$process.Start()")
    assert select < launch


def test_the_launch_environment_carries_no_api_key() -> None:
    """Un trafico cero conseguido porque el proceso no tenia clave no vale.

    Lo que se mide es el arranque, que no debe llamar a nadie ni con clave ni sin
    ella; pero pasarle una por variable de entorno seria introducir un secreto en
    la prueba, y eso no se hace.
    """
    script = _script()
    banned = script.index("foreach ($banned in @(")
    banned_line = script[banned : script.index(")) {", banned)]

    for name in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT"):
        assert name in banned_line
    assert "OPENAI_API_KEY" in banned_line


def test_it_never_touches_credential_manager() -> None:
    """Esta tanda mide trafico. La boveda del usuario no se toca ni se consulta."""
    script = _script()

    for forbidden in ("cmdkey", "KeyringSecretStore", "ApiKeySettingsUseCase", "has_key"):
        assert forbidden not in script, f"el verificador de red toca la credencial: {forbidden}"


def test_listening_sockets_are_not_counted_as_outbound() -> None:
    """Una escucha no es una llamada.

    Un socket a la escucha aparece con destino `0.0.0.0`/`::` y puerto remoto 0.
    Contarlo como trafico saliente haria fallar la prueba por algo que no lo es,
    y una prueba que grita sin motivo se acaba ignorando.
    """
    script = _script()
    rule = script.index("function Get-OutboundConnections")
    body = script[rule : script.index("$startInfo = New-Object", rule)]

    assert "RemotePort -eq 0" in body
    assert "$LocalOnly -contains $remote" in body
    assert 'StartsWith("127.")' in body


def test_the_whole_process_tree_is_watched() -> None:
    """Un hijo tambien tiene red.

    Vigilar solo el PID raiz dejaria fuera cualquier proceso auxiliar que el
    paquete lanzara, y la afirmacion de trafico cero seria falsa sin que nada
    fallara.
    """
    script = _script()

    assert "function Get-ProcessTree" in script
    assert "ParentProcessId" in script
    watch = script.index("Get-OutboundConnections -ProcessIds $tree")
    assert watch > script.index("function Get-ProcessTree")


def test_the_package_process_is_always_stopped() -> None:
    """Ninguna excepcion de sondeo puede dejar el ejecutable del paquete vivo."""
    script = _script()
    finally_block = script.index("finally {")
    verdict = script.index('Write-Step "Resultado"')

    assert finally_block < verdict
    region = script[finally_block:verdict]
    assert "CloseMainWindow" in region
    assert "Kill()" in region


def test_the_udp_gap_is_declared_instead_of_hidden() -> None:
    """Lo que no se puede demostrar se dice.

    UDP no expone el extremo remoto sin captura de paquetes, y capturar exigiria
    administrador. Declararlo como omision es lo que impide que un veredicto en
    verde se lea como "no hubo ningun trafico de ningun tipo".
    """
    script = _script()

    assert 'Add-Skip "Destinos UDP' in script
    assert "administrador" in script[script.index('Add-Skip "Destinos UDP') :]


def test_the_verdict_separates_clean_from_reserved() -> None:
    script = _script()

    assert "B14/red: SUPERADA" in script
    assert "B14/red: SUPERADA CON RESERVAS" in script
    assert "B14/red: NO SUPERADA" in script
    assert "exit 1" in script

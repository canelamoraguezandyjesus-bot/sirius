"""La lista blanca que se escribe sola tiene que valerle a Sirius tal cual.

Una configuración generada que Sirius luego descarta es peor que no generar
nada: deja creyendo que las cámaras están puestas cuando no lo están. Por eso
casi todas estas pruebas terminan pasando el resultado por el mismo camino que
usa el arranque, ``build_scene_registry``, y comprobando que responde a lo que
se diría en voz alta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.capture_commands import CaptureCommand, interpret
from sirius.capture_setup import (
    AJUSTE,
    frases_de_voz,
    guardar_configuracion,
    leer_contrasena_guardada,
    proponer_escenas,
)
from sirius.config.secrets_config import OBS_WEBSOCKET_PASSWORD_SECRET_NAME
from sirius.config.settings import load_settings, save_settings
from sirius.domain.capture import SceneRegistry, build_scene_registry


def _registro(nombres: list[str]) -> SceneRegistry:
    return build_scene_registry(proponer_escenas(nombres))


# --- Identificadores ------------------------------------------------------


def test_every_scene_gets_a_stable_identifier() -> None:
    propuestas = proponer_escenas(["Cámara cenital", "Mesa de trabajo"])

    assert [escena["id"] for escena in propuestas] == ["camara-cenital", "mesa-de-trabajo"]


def test_the_identifier_survives_accents_and_symbols() -> None:
    propuestas = proponer_escenas(["Cámara ✦ Frontal (2)"])

    assert propuestas[0]["id"] == "camara-frontal-2"
    assert propuestas[0]["backend_name"] == "Cámara ✦ Frontal (2)", "OBS manda en su nombre"


def test_two_scenes_that_normalize_the_same_never_collide() -> None:
    """Un identificador repetido haría que el registro rechazara la lista entera."""
    propuestas = proponer_escenas(["Cámara", "cámara", "CAMARA"])

    identificadores = [escena["id"] for escena in propuestas]
    assert len(set(identificadores)) == 3
    assert len(build_scene_registry(propuestas).scenes) == 3


def test_a_scene_with_an_unusable_name_still_gets_an_identifier() -> None:
    propuestas = proponer_escenas(["✦✦✦"])

    assert propuestas[0]["id"] == "escena-1"


def test_blank_names_are_dropped() -> None:
    assert proponer_escenas(["  ", "", "Mesa"]) == proponer_escenas(["Mesa"])


# --- Alias de voz ---------------------------------------------------------


def test_the_short_alias_is_the_one_you_would_actually_say() -> None:
    """Nadie dice «cambia a la cámara cámara cenital»."""
    registro = _registro(["Cámara cenital"])

    assert registro.resolve("cenital") is not None
    assert registro.resolve("camara cenital") is not None


def test_an_alias_that_would_fit_two_scenes_is_dropped_from_both() -> None:
    """El registro no elige ante una ambigüedad, así que no se escribe ninguna.

    «Cámara mesa» y «Plano mesa» darían las dos el alias corto «mesa». Dejarlo
    escrito sería configurar a mano una orden que nunca funcionaría.
    """
    propuestas = proponer_escenas(["Cámara mesa", "Plano mesa"])

    for escena in propuestas:
        assert "mesa" not in escena["aliases"]

    registro = build_scene_registry(propuestas)
    assert registro.resolve("camara mesa") is not None
    assert registro.resolve("plano mesa") is not None


def test_the_first_scene_is_the_fallback() -> None:
    """Es a la que se vuelve si un plano se rompe grabando."""
    registro = build_scene_registry(proponer_escenas(["Cara", "Mesa"]))

    assert registro.fallback is not None
    assert registro.fallback.display_name == "Cara"


# --- Lo que de verdad importa: que la orden hablada funcione --------------


def test_the_spoken_order_reaches_the_scene() -> None:
    escenas = build_scene_registry(proponer_escenas(["Cámara cenital", "Mesa de trabajo"]))

    intencion = interpret("cambia a la camara cenital", escenas)

    assert intencion is not None
    assert intencion.command is CaptureCommand.SWITCH_SCENE
    assert intencion.scene_id == "camara-cenital"


def test_the_short_spoken_order_also_reaches_the_scene() -> None:
    escenas = build_scene_registry(proponer_escenas(["Cámara cenital", "Mesa de trabajo"]))

    intencion = interpret("ponme cenital", escenas)

    assert intencion is not None
    assert intencion.scene_id == "camara-cenital"


def test_a_scene_that_is_not_configured_is_never_activated() -> None:
    escenas = build_scene_registry(proponer_escenas(["Cámara cenital"]))

    assert interpret("cambia a la camara del vecino", escenas) is None


# --- Guardar --------------------------------------------------------------


@pytest.fixture(autouse=True)
def configuracion_aislada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def test_saving_keeps_the_rest_of_the_configuration() -> None:
    from sirius.config.settings import load_settings, save_settings

    save_settings({"llm_provider": "openai"})

    paso = guardar_configuracion(
        proponer_escenas(["Mesa"]), "127.0.0.1", 4455, "secreta", FakeSecretStore()
    )

    assert paso.correcto, paso.detalle
    guardado = load_settings()
    assert guardado["llm_provider"] == "openai", "no puede llevarse por delante lo demás"
    assert guardado[AJUSTE]["port"] == 4455
    assert len(guardado[AJUSTE]["scenes"]) == 1


def test_what_is_saved_is_what_sirius_reads_at_startup(tmp_path: Path) -> None:
    """La comprobación que evita el fallo silencioso: escribir algo inservible."""
    from sirius.composition_root import _build_studio_capture_use_case

    guardar_configuracion(
        proponer_escenas(["Cara", "Mesa"]), "127.0.0.1", 4455, "secreta", FakeSecretStore()
    )

    caso_de_uso = _build_studio_capture_use_case(tmp_path, FakeSecretStore())

    assert [escena.scene_id for escena in caso_de_uso.authorized_scenes()] == ["cara", "mesa"]


def test_the_password_is_never_part_of_what_gets_printed() -> None:
    paso = guardar_configuracion(
        proponer_escenas(["Mesa"]), "127.0.0.1", 4455, "muy-secreta", FakeSecretStore()
    )

    assert "muy-secreta" not in paso.linea()


# --- Lo que se le enseña al usuario --------------------------------------


def test_the_user_is_shown_a_phrase_that_really_works() -> None:
    """De nada sirve enseñar «di esto» si al decirlo no pasa nada."""
    propuestas = proponer_escenas(["Cámara cenital", "Mesa de trabajo"])
    escenas = build_scene_registry(propuestas)

    for frase in frases_de_voz(propuestas):
        orden = frase.split("»")[0].removeprefix("«")
        assert interpret(orden, escenas) is not None, f"la frase enseñada no funciona: {orden}"


# --- La contraseña, cuando pegarla a ciegas no funciona -------------------


def test_the_password_can_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pegar en un campo que no muestra nada no confirma que haya entrado.

    Sin esta salida, quien no consigue pegar la contraseña se queda sin poder
    conectar OBS y sin saber si el problema es la consola o él.
    """
    from sirius.capture_setup import VARIABLE_CONTRASENA, _preguntar_datos

    monkeypatch.setenv(VARIABLE_CONTRASENA, "la-de-obs")
    monkeypatch.setattr("builtins.input", lambda *_: "")

    _, _, contrasena = _preguntar_datos()

    assert contrasena == "la-de-obs"


def test_typing_the_password_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """La variable es una salida, no un sustituto: sin ella se sigue tecleando."""
    from sirius.capture_setup import VARIABLE_CONTRASENA, _preguntar_datos

    monkeypatch.delenv(VARIABLE_CONTRASENA, raising=False)
    monkeypatch.setattr("builtins.input", lambda *_: "")
    monkeypatch.setattr("sirius.capture_setup.getpass", lambda *_: "tecleada")

    _, _, contrasena = _preguntar_datos()

    assert contrasena == "tecleada"


def test_the_environment_password_is_never_echoed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from sirius.capture_setup import VARIABLE_CONTRASENA, _preguntar_datos

    monkeypatch.setenv(VARIABLE_CONTRASENA, "secretisima")
    monkeypatch.setattr("builtins.input", lambda *_: "")

    _preguntar_datos()

    assert "secretisima" not in capsys.readouterr().out


# --- La contraseña es un secreto, no configuración -----------------------


def test_la_contrasena_no_acaba_en_settings_json() -> None:
    """`settings.json` es el fichero que el resto del sistema trata como no
    confidencial, y AGENTS.md prohíbe guardar claves en archivos de texto."""
    almacen = FakeSecretStore()

    paso = guardar_configuracion(
        proponer_escenas(["Mesa"]), "127.0.0.1", 4455, "muy-secreta", almacen
    )

    assert paso.correcto, paso.detalle
    assert "muy-secreta" not in json.dumps(load_settings())
    assert almacen.get_secret(OBS_WEBSOCKET_PASSWORD_SECRET_NAME) == "muy-secreta"


class _AlmacenSinRespaldoSeguro(FakeSecretStore):
    """`FakeSecretStore` es seguro a propósito; aquí hace falta lo contrario."""

    def is_secure_backend(self) -> bool:
        return False


def test_sin_almacen_seguro_no_se_guarda_en_texto_plano() -> None:
    """Mismo criterio que la clave de API: sin almacén seguro, no se guarda.

    Escribirla igualmente «para que Captura funcione» sería exactamente lo que
    este arreglo viene a retirar.
    """
    almacen = _AlmacenSinRespaldoSeguro()

    paso = guardar_configuracion(
        proponer_escenas(["Mesa"]), "127.0.0.1", 4455, "muy-secreta", almacen
    )

    assert not paso.correcto
    assert "muy-secreta" not in json.dumps(load_settings())


def test_una_contrasena_ya_escrita_se_traslada_y_se_borra_del_fichero() -> None:
    """Sin migración, el texto plano SOBREVIVE al arreglo.

    Una instalación existente ya tiene la contraseña en `settings.json`:
    limitarse a dejar de escribirla la dejaría ahí para siempre.
    """
    save_settings({AJUSTE: {"host": "127.0.0.1", "port": 4455, "password": "vieja", "scenes": []}})
    almacen = FakeSecretStore()

    recuperada = leer_contrasena_guardada(almacen)

    assert recuperada == "vieja"
    assert almacen.get_secret(OBS_WEBSOCKET_PASSWORD_SECRET_NAME) == "vieja"
    assert "vieja" not in json.dumps(load_settings()), "el texto plano tiene que desaparecer"

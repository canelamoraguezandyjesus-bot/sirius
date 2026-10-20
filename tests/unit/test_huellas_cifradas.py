"""Las huellas, cifradas con una llave que no vive en la base (pieza E de la 0.4, ADR-263).

Con un almacén de secretos de mentira que dice si es seguro: la llave se crea la primera vez
que hay que cifrar y solo en uno seguro; sin llave no se abre nada; una huella cambiada, o
cifrada con otra llave, no se abre; y lo cifrado no lleva los números en claro.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

import pytest
from cryptography.fernet import Fernet

from sirius.adapters.recognition.sealer import (
    BAD_KEY,
    NO_KEY,
    NO_SAFE_STORE,
    UNREADABLE,
    FernetSealer,
)
from sirius.config.secrets_config import RECOGNITION_KEY_SECRET_NAME
from sirius.ports.recognition import RecognitionUnavailable
from sirius.ports.secrets import SecretStoreError

_HUELLA = (0.6, -0.8, 0.0, 1 / 3)


@dataclass
class _Secretos:
    """El almacén de secretos de mentira: en memoria, seguro o no, y que puede fallar."""

    seguro: bool = True
    guardados: dict[str, str] = field(default_factory=dict)
    falla: bool = False

    def get_secret(self, key: str) -> str | None:
        if self.falla:
            msg = "el almacén no responde"
            raise SecretStoreError(msg)
        return self.guardados.get(key)

    def set_secret(self, key: str, value: str) -> None:
        if self.falla:
            msg = "el almacén no responde"
            raise SecretStoreError(msg)
        self.guardados[key] = value

    def delete_secret(self, key: str) -> None:
        self.guardados.pop(key, None)

    def is_secure_backend(self) -> bool:
        return self.seguro


def test_cifra_y_abre_la_misma_huella_con_todos_sus_decimales() -> None:
    sellador = FernetSealer(_Secretos())

    assert sellador.open(sellador.seal(_HUELLA)) == _HUELLA


def test_lo_cifrado_no_lleva_los_numeros_en_claro_de_ninguna_forma() -> None:
    sellada = FernetSealer(_Secretos()).seal(_HUELLA)

    for forma in ("<", ">"):
        for letra in ("d", "f"):
            empaquetada = struct.pack(f"{forma}{len(_HUELLA)}{letra}", *_HUELLA)
            assert empaquetada not in sellada
            assert empaquetada[:8] not in sellada
    assert repr(_HUELLA[0]).encode() not in sellada
    assert b"0.6" not in sellada


def test_crea_la_llave_la_primera_vez_y_la_guarda_en_el_almacen_de_secretos() -> None:
    secretos = _Secretos()
    sellada = FernetSealer(secretos).seal(_HUELLA)

    llave = secretos.guardados[RECOGNITION_KEY_SECRET_NAME]
    assert Fernet(llave.encode()).decrypt(sellada), "es la llave con que cifró"
    assert FernetSealer(secretos).open(sellada) == _HUELLA, "y sirve al volver a abrir"


def test_sin_un_almacen_seguro_no_crea_la_llave_ni_cifra_nada() -> None:
    secretos = _Secretos(seguro=False)

    with pytest.raises(RecognitionUnavailable) as error:
        FernetSealer(secretos).seal(_HUELLA)

    assert error.value.reason == NO_SAFE_STORE
    assert secretos.guardados == {}


def test_sin_llave_no_abre_nada_y_abrir_no_la_crea() -> None:
    secretos = _Secretos()
    sellada = FernetSealer(_Secretos()).seal(_HUELLA)

    with pytest.raises(RecognitionUnavailable) as error:
        FernetSealer(secretos).open(sellada)

    assert error.value.reason == NO_KEY
    assert secretos.guardados == {}


def test_una_huella_cambiada_o_cifrada_con_otra_llave_no_se_abre() -> None:
    sellador = FernetSealer(_Secretos())
    sellada = sellador.seal(_HUELLA)
    cambiada = sellada[:-5] + bytes([sellada[-5] ^ 1]) + sellada[-4:]
    de_otra_llave = FernetSealer(_Secretos()).seal(_HUELLA)

    for mala in (cambiada, de_otra_llave, b"no es nada"):
        with pytest.raises(RecognitionUnavailable) as error:
            sellador.open(mala)
        assert error.value.reason == UNREADABLE


def test_lo_cifrado_con_su_llave_que_no_son_numeros_enteros_no_se_abre() -> None:
    secretos = _Secretos()
    sellador = FernetSealer(secretos)
    sellador.seal(_HUELLA)
    llave = Fernet(secretos.guardados[RECOGNITION_KEY_SECRET_NAME].encode())

    with pytest.raises(RecognitionUnavailable) as error:
        sellador.open(llave.encrypt(b"siete b"))

    assert error.value.reason == UNREADABLE


@pytest.mark.parametrize("llave", ["no-es-una-llave", "a" * 44, "ñ" * 44])
def test_una_llave_que_no_vale_lo_dice_al_cifrar_y_al_abrir(llave: str) -> None:
    secretos = _Secretos(guardados={RECOGNITION_KEY_SECRET_NAME: llave})

    for intento in (
        lambda: FernetSealer(secretos).seal(_HUELLA),
        lambda: FernetSealer(secretos).open(b"algo"),
    ):
        with pytest.raises(RecognitionUnavailable) as error:
            intento()
        assert error.value.reason == BAD_KEY
    assert secretos.guardados == {RECOGNITION_KEY_SECRET_NAME: llave}, "no la cambia"


def test_si_el_almacen_de_secretos_falla_lo_dice_sin_su_detalle() -> None:
    secretos = _Secretos(falla=True)

    with pytest.raises(RecognitionUnavailable) as error:
        FernetSealer(secretos).seal(_HUELLA)

    assert error.value.reason == NO_SAFE_STORE

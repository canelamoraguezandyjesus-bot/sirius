"""Las huellas, cifradas con una llave que no vive en la base (pieza E de la 0.4, ADR-263).

Con Fernet, de ``cryptography``, como las copias de seguridad: AES en modo CBC con su
HMAC, así que una huella cambiada no se lee. La llave se crea al azar la primera vez que
hay que cifrar y se guarda en el almacén de secretos, el mismo de las claves de Sirius: en
Windows, el administrador de credenciales, con la sesión del propietario. Sin un almacén
seguro no se crea: sin llave no hay huellas, y nunca en claro.

Cada huella se guarda como sus números en float64, enteros, y cifrados.
"""

from __future__ import annotations

import struct
import threading

from cryptography.fernet import Fernet, InvalidToken

from sirius.config.secrets_config import RECOGNITION_KEY_SECRET_NAME
from sirius.ports.recognition import Print, RecognitionUnavailable
from sirius.ports.secrets import SecretStore, SecretStoreError

#: Lo que se dice si no hay dónde guardar la llave a salvo.
NO_SAFE_STORE = "este ordenador no tiene un almacén seguro para la llave de las huellas"
#: Si falta la llave con huellas guardadas, o una no se puede leer.
NO_KEY = "falta la llave de las huellas guardadas"
UNREADABLE = "una huella guardada no se puede leer"
#: Si la llave del almacén no es una llave de Fernet.
BAD_KEY = "la llave de las huellas guardadas no vale"


class FernetSealer:
    """Cifra y descifra huellas con la llave del almacén de secretos."""

    def __init__(self, secrets: SecretStore) -> None:
        self._secrets = secrets
        self._lock = threading.Lock()
        self._fernet: Fernet | None = None

    def seal(self, numbers: Print) -> bytes:
        """``numbers``, cifrados. Crea la llave si no la hay, solo en un almacén seguro."""
        return self._key(create=True).encrypt(struct.pack(f"<{len(numbers)}d", *numbers))

    def open(self, sealed: bytes) -> Print:
        """Los números de ``sealed``; ``RecognitionUnavailable`` si falta la llave o no es
        una huella cifrada con ella."""
        try:
            plain = self._key(create=False).decrypt(sealed)
        except InvalidToken as error:
            raise RecognitionUnavailable(UNREADABLE) from error
        if len(plain) % 8:
            raise RecognitionUnavailable(UNREADABLE)
        return struct.unpack(f"<{len(plain) // 8}d", plain)

    def _key(self, *, create: bool) -> Fernet:
        with self._lock:
            if self._fernet is not None:
                return self._fernet
            try:
                value = self._secrets.get_secret(RECOGNITION_KEY_SECRET_NAME)
                if value is None:
                    if not create:
                        raise RecognitionUnavailable(NO_KEY)
                    if not self._secrets.is_secure_backend():
                        raise RecognitionUnavailable(NO_SAFE_STORE)
                    value = Fernet.generate_key().decode("ascii")
                    self._secrets.set_secret(RECOGNITION_KEY_SECRET_NAME, value)
            except SecretStoreError as error:
                raise RecognitionUnavailable(NO_SAFE_STORE) from error
            try:
                self._fernet = Fernet(value.encode("ascii"))
            except ValueError as error:
                # Base64 que no lo es, otra longitud o letras de fuera: no es una llave.
                raise RecognitionUnavailable(BAD_KEY) from error
            return self._fernet

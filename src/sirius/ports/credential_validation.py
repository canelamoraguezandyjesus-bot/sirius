"""Provider-neutral credential validation contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class CredentialValidationKind(StrEnum):
    """Safe categories produced while validating a provider credential."""

    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


_SAFE_MESSAGES: dict[CredentialValidationKind, str] = {
    CredentialValidationKind.AUTHENTICATION: "La clave no es válida.",
    CredentialValidationKind.PERMISSION: (
        "La clave no tiene permiso para usar el modelo configurado."
    ),
    CredentialValidationKind.CONNECTION: "No se pudo contactar con el proveedor.",
    CredentialValidationKind.TIMEOUT: "El proveedor tardó demasiado en responder.",
    CredentialValidationKind.RATE_LIMITED: (
        "El proveedor está limitando temporalmente las solicitudes."
    ),
    CredentialValidationKind.CONFIGURATION: ("La clave y el modelo deben estar configurados."),
    CredentialValidationKind.UNKNOWN: "No se pudo validar la clave.",
}


class CredentialValidationError(RuntimeError):
    """Safe validation failure that never contains the credential value."""

    def __init__(self, kind: CredentialValidationKind) -> None:
        self.kind = kind
        super().__init__(_SAFE_MESSAGES[kind])


class CredentialValidator(Protocol):
    """Validate that a credential can use the configured provider model."""

    def validate(self, credential: str, model: str) -> None:
        """Return normally when usable, otherwise raise a safe typed error."""
        ...

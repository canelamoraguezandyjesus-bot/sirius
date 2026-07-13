"""In-memory secret store for tests and offline development."""

from __future__ import annotations


class FakeSecretStore:
    """Small deterministic adapter; it never touches the OS credential store."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def get_secret(self, key: str) -> str | None:
        return self._secrets.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self._secrets[key] = value

    def delete_secret(self, key: str) -> None:
        self._secrets.pop(key, None)

    def is_secure_backend(self) -> bool:
        """Always True: this is an explicit, safe test double, not an
        insecure fallback being used unknowingly."""
        return True

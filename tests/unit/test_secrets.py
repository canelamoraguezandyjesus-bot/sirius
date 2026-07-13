from sirius.adapters.secrets.fake import FakeSecretStore


def test_get_secret_returns_none_when_absent() -> None:
    store = FakeSecretStore()

    assert store.get_secret("openai_api_key") is None


def test_set_secret_then_get_secret_round_trips() -> None:
    store = FakeSecretStore()

    store.set_secret("openai_api_key", "sk-fake")

    assert store.get_secret("openai_api_key") == "sk-fake"


def test_set_secret_replaces_existing_value() -> None:
    store = FakeSecretStore()
    store.set_secret("openai_api_key", "sk-first")

    store.set_secret("openai_api_key", "sk-second")

    assert store.get_secret("openai_api_key") == "sk-second"


def test_delete_secret_removes_stored_value() -> None:
    store = FakeSecretStore()
    store.set_secret("openai_api_key", "sk-fake")

    store.delete_secret("openai_api_key")

    assert store.get_secret("openai_api_key") is None


def test_delete_secret_is_a_no_op_when_absent() -> None:
    store = FakeSecretStore()

    store.delete_secret("openai_api_key")

    assert store.get_secret("openai_api_key") is None


def test_is_secure_backend_is_always_true() -> None:
    assert FakeSecretStore().is_secure_backend() is True

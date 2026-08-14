"""Centralized, stable naming for Sirius's secrets.

Pure constants, no dependency on ``keyring`` or any concrete secret store: any
layer may import this module to agree on names without coupling to how
secrets are actually stored.
"""

from __future__ import annotations

SIRIUS_KEYRING_SERVICE_NAME = "Sirius"
"""The service name under which Sirius stores all its credentials in the
OS-level credential store. Stable across releases: renaming it would orphan
any key a user already saved."""

OPENAI_API_KEY_SECRET_NAME = "openai_api_key"
"""The key name (not value) used to store the OpenAI API key."""

OBS_WEBSOCKET_PASSWORD_SECRET_NAME = "obs_websocket_password"
"""The key name (not value) used to store the OBS WebSocket server password.

It is a credential —it is what keeps the local WebSocket port from being open
to any process that finds it— so it lives in the OS credential store, next to
the API key, and never in ``settings.json``: that file is non-sensitive
configuration, and `AGENTS.md` forbids keeping keys in plain-text files."""

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

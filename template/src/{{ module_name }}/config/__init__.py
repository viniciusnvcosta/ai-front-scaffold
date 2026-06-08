"""Config loading. Holds only REFERENCES to secrets, never secret values."""

from __future__ import annotations

import os


def load_config() -> dict:
    # Resolve secret references from the environment / secret manager.
    # NEVER hardcode secrets here.
    return {
        "env": os.getenv("APP_ENV", "dev"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }

"""Tests for settings __init__.py import error handling."""

import sys
from unittest.mock import MagicMock

import pytest


def test__settings_init__pydantic_not_installed__raises_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    # Remove redis_client_kit.settings from modules if already imported
    modules_to_remove = [key for key in sys.modules if key.startswith("redis_client_kit.settings")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Mock _deps to simulate pydantic-settings not installed
    mock_deps = MagicMock()
    mock_deps.HAS_PYDANTIC_SETTINGS = False
    sys.modules["redis_client_kit.settings._deps"] = mock_deps

    # Act & Assert
    with pytest.raises(ImportError, match="pydantic-settings not installed"):
        import redis_client_kit.settings  # noqa: F401, PLC0415

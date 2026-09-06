"""Tests for providers __init__.py import error handling."""

import sys
from unittest.mock import MagicMock

import pytest


def _unload_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the providers package from sys.modules for the duration of one test.

    monkeypatch restores every entry afterwards, so the modules the rest of the
    suite already imported keep pointing at the real ones.
    """
    for module in [key for key in sys.modules if key.startswith("redis_client_kit.providers")]:
        monkeypatch.delitem(sys.modules, module)


def test__providers_init__dishka_not_installed__raises_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _unload_providers(monkeypatch)

    # Mock _deps to simulate dishka not installed
    mock_deps = MagicMock()
    mock_deps.HAS_DISHKA = False
    monkeypatch.setitem(sys.modules, "redis_client_kit.providers._deps", mock_deps)

    # Act & Assert
    with pytest.raises(ImportError, match="dishka not installed"):
        import redis_client_kit.providers  # noqa: F401, PLC0415


def test__providers_init__dishka_installed__imports_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _unload_providers(monkeypatch)

    # Mock _deps to simulate dishka installed
    mock_deps = MagicMock()
    mock_deps.HAS_DISHKA = True
    mock_deps.AsyncRedisProvider = MagicMock
    monkeypatch.setitem(sys.modules, "redis_client_kit.providers._deps", mock_deps)
    monkeypatch.setitem(sys.modules, "redis_client_kit.providers.redis", mock_deps)
    monkeypatch.setitem(sys.modules, "redis_client_kit.providers.utils", mock_deps)

    # Act
    import redis_client_kit.providers  # noqa: F401, PLC0415

    # Assert - No exception raised
    assert True

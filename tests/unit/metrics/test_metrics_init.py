"""Tests for metrics __init__.py import error handling."""

import sys
from unittest.mock import MagicMock

import pytest


def _unload_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the metrics package from sys.modules for the duration of one test.

    monkeypatch restores every entry afterwards, so the modules the rest of the
    suite already imported keep pointing at the real ones.
    """
    for module in [key for key in sys.modules if key.startswith("redis_client_kit.metrics")]:
        monkeypatch.delitem(sys.modules, module)


def test__metrics_init__prometheus_not_installed__raises_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _unload_metrics(monkeypatch)

    # Mock _deps to simulate prometheus not installed
    mock_deps = MagicMock()
    mock_deps.HAS_PROMETHEUS = False
    monkeypatch.setitem(sys.modules, "redis_client_kit.metrics._deps", mock_deps)

    # Act & Assert
    with pytest.raises(ImportError, match="prometheus-client not installed"):
        import redis_client_kit.metrics  # noqa: F401, PLC0415


def test__metrics_init__prometheus_installed__imports_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _unload_metrics(monkeypatch)

    # Mock _deps to simulate prometheus installed
    mock_deps = MagicMock()
    mock_deps.HAS_PROMETHEUS = True
    mock_deps.REDIS_COMMAND_DURATION_BUCKETS = (0.001, 0.01, 0.1, 1.0)
    mock_deps.RedisMetrics = MagicMock
    monkeypatch.setitem(sys.modules, "redis_client_kit.metrics._deps", mock_deps)
    monkeypatch.setitem(sys.modules, "redis_client_kit.metrics.redis", mock_deps)

    # Act
    import redis_client_kit.metrics  # noqa: F401, PLC0415

    # Assert - No exception raised
    assert True

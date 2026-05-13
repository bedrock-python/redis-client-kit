"""Tests for metrics __init__.py import error handling."""

import sys
from unittest.mock import MagicMock

import pytest


def test__metrics_init__prometheus_not_installed__raises_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    # Remove redis_client_kit.metrics from modules if already imported
    modules_to_remove = [key for key in sys.modules if key.startswith("redis_client_kit.metrics")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Mock _deps to simulate prometheus not installed
    mock_deps = MagicMock()
    mock_deps.HAS_PROMETHEUS = False
    sys.modules["redis_client_kit.metrics._deps"] = mock_deps

    # Act & Assert
    with pytest.raises(ImportError, match="prometheus-client not installed"):
        import redis_client_kit.metrics  # noqa: F401, PLC0415


def test__metrics_init__prometheus_installed__imports_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    # Remove redis_client_kit.metrics from modules if already imported
    modules_to_remove = [key for key in sys.modules if key.startswith("redis_client_kit.metrics")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Mock _deps to simulate prometheus installed
    mock_deps = MagicMock()
    mock_deps.HAS_PROMETHEUS = True
    mock_deps.REDIS_COMMAND_DURATION_BUCKETS = (0.001, 0.01, 0.1, 1.0)
    mock_deps.RedisMetrics = MagicMock
    sys.modules["redis_client_kit.metrics._deps"] = mock_deps
    sys.modules["redis_client_kit.metrics.redis"] = mock_deps

    # Act
    import redis_client_kit.metrics  # noqa: F401, PLC0415

    # Assert - No exception raised
    assert True

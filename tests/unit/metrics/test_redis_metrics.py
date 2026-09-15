"""Tests for the cached RedisMetrics getter."""

import pytest

from redis_client_kit.metrics import RedisMetrics, get_redis_metrics


def test__redis_metrics__same_prefix_twice__raises_duplicated_timeseries() -> None:
    """Prometheus registers a name once per registry; the second instance is refused."""
    # Arrange
    RedisMetrics(prefix="twice_test")

    # Act & Assert
    with pytest.raises(ValueError, match="Duplicated timeseries"):
        RedisMetrics(prefix="twice_test")


def test__get_redis_metrics__no_prefix_twice__returns_the_cached_instance() -> None:
    """A second container asking for the collector gets the one the first container registered."""
    # Act
    first = get_redis_metrics()
    second = get_redis_metrics(prefix=None)

    # Assert
    assert first is second
    assert isinstance(first, RedisMetrics)


def test__get_redis_metrics__different_prefixes__returns_different_instances() -> None:
    # Act
    first = get_redis_metrics(prefix="cache_a")
    second = get_redis_metrics(prefix="cache_b")

    # Assert
    assert first is not second
    assert first.pool_size._name == "cache_a_redis_pool_size"
    assert second.pool_size._name == "cache_b_redis_pool_size"


def test__get_redis_metrics__empty_prefix__is_the_unprefixed_instance() -> None:
    """RedisMetrics treats "" as no prefix, so the cache must too or the second call would re-register."""
    # Act & Assert
    assert get_redis_metrics(prefix="") is get_redis_metrics()

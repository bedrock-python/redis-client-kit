"""Optional prometheus dependencies (lazy import)."""

try:
    from prometheus_client import Counter, Gauge, Histogram

    HAS_PROMETHEUS = True
except ImportError:
    Counter = None  # type: ignore[assignment,misc]
    Gauge = None  # type: ignore[assignment,misc]
    Histogram = None  # type: ignore[assignment,misc]
    HAS_PROMETHEUS = False

__all__ = ["HAS_PROMETHEUS", "Counter", "Gauge", "Histogram"]

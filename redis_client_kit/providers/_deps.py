"""Optional dishka dependencies (lazy import)."""

try:
    from dishka import Provider, Scope, provide

    HAS_DISHKA = True
except ImportError:
    Provider = None  # type: ignore[assignment,misc]
    Scope = None  # type: ignore[assignment,misc]
    provide = None  # type: ignore[assignment,misc]
    HAS_DISHKA = False

__all__ = ["HAS_DISHKA", "Provider", "Scope", "provide"]

"""Optional pydantic-settings dependencies (lazy import)."""

try:
    from pydantic import BaseModel, Field, SecretStr, model_validator
    from pydantic_settings import BaseSettings

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    BaseModel = None  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]
    SecretStr = None  # type: ignore[assignment,misc]
    model_validator = None  # type: ignore[assignment,misc]
    BaseSettings = None  # type: ignore[assignment,misc]
    HAS_PYDANTIC_SETTINGS = False

__all__ = [
    "HAS_PYDANTIC_SETTINGS",
    "BaseModel",
    "BaseSettings",
    "Field",
    "SecretStr",
    "model_validator",
]

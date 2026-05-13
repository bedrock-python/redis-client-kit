"""Provider utility functions for connection retry and cleanup."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def retry_async_connection(
    connect_func: Callable[[], Awaitable[bool]],
    service_name: str,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
) -> None:
    """Retry async connection with exponential backoff."""
    for attempt in range(1, max_attempts + 1):
        try:
            if await connect_func():
                logger.info("%s connected successfully", service_name)
                return
        except Exception as e:
            if attempt == max_attempts:
                raise
            wait_time = backoff_base * (2 ** (attempt - 1))
            logger.warning(
                "%s connection failed (attempt %d/%d), retrying in %ss: %s",
                service_name,
                attempt,
                max_attempts,
                wait_time,
                e,
            )
            await asyncio.sleep(wait_time)


async def safe_async_cleanup(
    cleanup_func: Callable[[], Awaitable[None]],
    service_name: str,
    exception_type: type[Exception],
) -> None:
    """Safely cleanup async resource."""
    try:
        await cleanup_func()
        logger.info("%s cleaned up successfully", service_name)
    except exception_type as e:
        logger.warning("%s cleanup failed: %s", service_name, e)
    except Exception:
        logger.exception("Unexpected error during %s cleanup", service_name)


__all__ = ["retry_async_connection", "safe_async_cleanup"]

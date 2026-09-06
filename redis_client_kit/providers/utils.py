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
    """Retry async connection with exponential backoff.

    An attempt fails when connect_func raises or returns a falsy value; both are
    retried with the same backoff.

    Args:
        connect_func: Callable returning True once the service is reachable
        service_name: Name used in log messages and in the raised error
        max_attempts: Number of attempts before giving up
        backoff_base: Base of the exponential backoff in seconds

    Raises:
        ConnectionError: If no attempt reported success and none of them raised.
        Exception: The error raised by the last attempt, if it raised one.
    """
    for attempt in range(1, max_attempts + 1):
        error: Exception
        try:
            if await connect_func():
                logger.info("%s connected successfully", service_name)
                return
            error = ConnectionError(f"{service_name} did not report a healthy connection")
        except Exception as e:
            error = e

        if attempt == max_attempts:
            raise error

        wait_time = backoff_base * (2 ** (attempt - 1))
        logger.warning(
            "%s connection failed (attempt %d/%d), retrying in %ss: %s",
            service_name,
            attempt,
            max_attempts,
            wait_time,
            error,
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

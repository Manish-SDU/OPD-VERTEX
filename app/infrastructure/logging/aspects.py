"""Aspect-oriented logging decorators for cross-cutting concerns.

Provides decorators that act as logging aspects, automatically capturing
entry/exit, performance, errors, and component context without polluting
business logic.  Apply these to service methods, routes, and repository
calls so that logging remains a separate cross-cutting concern.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Component-aware logger factory
# ---------------------------------------------------------------------------


def get_component_logger(component: str, module: str | None = None) -> logging.Logger:
    """Return a logger namespaced by architectural component.

    Example:
        get_component_logger("service", "consultations")
        → logger named "opd_vertex.service.consultations"
    """
    parts = ["opd_vertex", component]
    if module:
        parts.append(module)
    return logging.getLogger(".".join(parts))


# ---------------------------------------------------------------------------
# Generic method-level logging aspect
# ---------------------------------------------------------------------------


def log_method(
    component: str,
    module: str | None = None,
    *,
    log_args: bool = False,
    log_result: bool = False,
    level: int = logging.DEBUG,
) -> Callable[[F], F]:
    """Decorator that logs method entry, exit, duration, and errors.

    Args:
        component: Architectural layer name (e.g. "service", "repository").
        module:    Sub-module name (e.g. "consultations", "patients").
        log_args:  Whether to include call arguments in the log.
        log_result: Whether to include the return value in the log.
        level:     Log level for normal entry/exit messages.
    """

    def decorator(fn: F) -> F:
        logger = get_component_logger(component, module)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            fn_name = fn.__qualname__

            extra_info = ""
            if log_args:
                # Exclude 'self' for bound methods
                display_args = (
                    args[1:] if args and hasattr(args[0], fn.__name__) else args
                )
                extra_info = f" args={display_args} kwargs={kwargs}"

            logger.log(level, "[ENTER] %s%s", fn_name, extra_info)

            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.exception("[ERROR] %s failed after %.1fms", fn_name, elapsed_ms)
                raise

            elapsed_ms = (time.perf_counter() - start) * 1000
            result_info = f" result={result}" if log_result else ""
            logger.log(
                level,
                "[EXIT]  %s completed in %.1fms%s",
                fn_name,
                elapsed_ms,
                result_info,
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Layer-specific convenience decorators
# ---------------------------------------------------------------------------


def log_service(module: str, *, log_args: bool = False) -> Callable[[F], F]:
    """Aspect for application-service methods."""
    return log_method("service", module, log_args=log_args, level=logging.INFO)


def log_route(module: str) -> Callable[[F], F]:
    """Aspect for API route handlers."""
    return log_method("route", module, level=logging.INFO)


def log_repository(module: str, *, log_args: bool = False) -> Callable[[F], F]:
    """Aspect for repository / persistence methods."""
    return log_method("repository", module, log_args=log_args, level=logging.DEBUG)


def log_infrastructure(module: str) -> Callable[[F], F]:
    """Aspect for infrastructure adapters (AI, email, PDF, etc.)."""
    return log_method("infrastructure", module, level=logging.INFO)


# ---------------------------------------------------------------------------
# Class-level aspect applicator
# ---------------------------------------------------------------------------


def apply_logging_aspect(
    component: str,
    module: str,
    *,
    log_args: bool = False,
    exclude: frozenset[str] = frozenset(),
) -> Callable[[type], type]:
    """Class decorator that applies the logging aspect to every public method.

    This is the main AOP mechanism: apply it to an entire service or
    repository class so that *all* public methods get entry/exit/error
    logging without touching individual method bodies.

    Args:
        component: Architectural layer name.
        module:    Sub-module name.
        log_args:  Whether to include call arguments.
        exclude:   Method names to skip.
    """

    def decorator(cls: type) -> type:
        aspect = log_method(component, module, log_args=log_args)
        for attr_name in list(vars(cls)):
            if attr_name.startswith("_") or attr_name in exclude:
                continue
            attr = getattr(cls, attr_name)
            if callable(attr):
                setattr(cls, attr_name, aspect(attr))
        return cls

    return decorator


# ---------------------------------------------------------------------------
# Performance-threshold aspect
# ---------------------------------------------------------------------------


def log_performance(
    threshold_ms: float = 500.0,
    component: str = "service",
    module: str | None = None,
) -> Callable[[F], F]:
    """Decorator that emits a WARNING when a call exceeds *threshold_ms*.

    Combines naturally with ``log_method``::

        @log_performance(threshold_ms=200)
        @log_method("service", "consultations")
        def generate_report(self, ...):
            ...

    Or apply via ``apply_logging_aspect`` which handles entry/exit, and
    use this separately for SLA boundary checks.
    """

    def decorator(fn: F) -> F:
        logger = get_component_logger(component, module)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > threshold_ms:
                    logger.warning(
                        "[SLOW]  %s took %.1fms (threshold=%.0fms)",
                        fn.__qualname__,
                        elapsed_ms,
                        threshold_ms,
                    )

        return wrapper  # type: ignore[return-value]

    return decorator

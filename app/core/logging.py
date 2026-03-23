"""Structured logging bootstrap.

Configures component-aware logging for the layered architecture.
All opd_vertex.* loggers (route, service, repository, infrastructure,
middleware) inherit from the root logger configuration set here.
"""

from __future__ import annotations

from logging.config import dictConfig


def configure_logging(level: str) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "loggers": {
                # Application component loggers
                "opd_vertex.route": {"level": level.upper()},
                "opd_vertex.service": {"level": level.upper()},
                "opd_vertex.repository": {"level": level.upper()},
                "opd_vertex.infrastructure": {"level": level.upper()},
                "opd_vertex.middleware": {"level": level.upper()},
                # Quieter third-party loggers
                "uvicorn": {"level": "INFO"},
                "sqlalchemy.engine": {"level": "WARNING"},
                "pymongo": {"level": "WARNING"},
            },
            "root": {"level": level.upper(), "handlers": ["console"]},
        }
    )

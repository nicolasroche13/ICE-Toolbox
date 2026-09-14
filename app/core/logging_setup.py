"""Minimal crash-safety logging for the frozen, console-less Windows build.

This is operational infrastructure only: it never receives Microsoft Graph
payloads, tokens or the Client Secret. It exists so an unhandled exception in
``EndpointToolbox.exe`` (built with ``console=False``, so nothing is printed
anywhere the user can see) leaves a trace on disk instead of failing silently.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.paths import user_log_dir

LOG_FILE_NAME = "endpoint_toolbox.log"
LOGGER_NAME = "endpoint_toolbox"

_configured = False


def configure_logging() -> logging.Logger:
    """Set up the rotating file handler and the uncaught-exception hook, once."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    log_dir = user_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    previous_hook = sys.excepthook

    def _log_uncaught(exc_type, exc_value, exc_tb) -> None:
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        previous_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _log_uncaught

    _configured = True
    return logger

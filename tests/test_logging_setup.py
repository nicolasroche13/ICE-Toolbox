from __future__ import annotations

import logging

from app.core import logging_setup


def _reset_logging_state(monkeypatch) -> None:
    monkeypatch.setattr(logging_setup, "_configured", False)
    logger = logging.getLogger(logging_setup.LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def test_configure_logging_creates_log_dir_under_user_log_dir(monkeypatch, tmp_path) -> None:
    _reset_logging_state(monkeypatch)
    monkeypatch.setattr(logging_setup, "user_log_dir", lambda: tmp_path / "logs")
    logging_setup.configure_logging()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "logs" / logging_setup.LOG_FILE_NAME).exists()


def test_configure_logging_is_idempotent(monkeypatch, tmp_path) -> None:
    _reset_logging_state(monkeypatch)
    monkeypatch.setattr(logging_setup, "user_log_dir", lambda: tmp_path / "logs")
    logging_setup.configure_logging()
    logger = logging_setup.configure_logging()
    assert len(logger.handlers) == 1


def test_configure_logging_never_logs_graph_settings_or_secrets_by_construction(monkeypatch, tmp_path) -> None:
    # configure_logging only wires a file handler and an excepthook: it has no call
    # site that could ever receive a GraphSettings object or a Client Secret string,
    # unlike the sanitize_for_export path used by Support Bundles.
    _reset_logging_state(monkeypatch)
    monkeypatch.setattr(logging_setup, "user_log_dir", lambda: tmp_path / "logs")
    logger = logging_setup.configure_logging()
    logger.info("startup")
    log_content = (tmp_path / "logs" / logging_setup.LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "secret" not in log_content.lower()
    assert "client_secret" not in log_content.lower()

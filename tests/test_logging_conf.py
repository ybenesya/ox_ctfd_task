from __future__ import annotations

import logging
from pathlib import Path

from ox_ctfd_task.logging_conf import configure_logging


def _get_single_handler(logger: logging.Logger) -> logging.Handler:
    assert len(logger.handlers) == 1
    return logger.handlers[0]


def test_configure_logging_stdout_info() -> None:
    logger = configure_logging(log_dest="stdout", debug=False)
    handler = _get_single_handler(logger)
    assert isinstance(handler, logging.StreamHandler)
    assert handler.level == logging.INFO


def test_configure_logging_stdout_debug() -> None:
    logger = configure_logging(log_dest="stdout", debug=True)
    handler = _get_single_handler(logger)
    assert handler.level == logging.DEBUG


def test_configure_logging_file(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    logger = configure_logging(
        log_dest="file", log_file_path=str(log_path), debug=False
    )
    handler = _get_single_handler(logger)
    assert isinstance(handler, logging.FileHandler)
    assert handler.level == logging.INFO

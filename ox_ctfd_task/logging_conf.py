from __future__ import annotations

import logging
import sys
from typing import Literal


LogDest = Literal["stdout", "file"]


def configure_logging(
    *,
    log_dest: LogDest = "stdout",
    log_file_path: str | None = None,
    debug: bool = False,
) -> logging.Logger:
    """
    Configure a single app logger.
    - stdout -> StreamHandler(sys.stdout)
    - file   -> FileHandler(log_file_path)
    - debug  -> DEBUG level else INFO
    """
    logger = logging.getLogger("ox_ctfd_task")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


    logger.handlers.clear()

    level = logging.DEBUG if debug else logging.INFO

    if log_dest == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        if not log_file_path:
            raise ValueError("log_file_path must be provided when log_dest='file'")
        handler = logging.FileHandler(log_file_path, encoding="utf-8")

    handler.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)

    logger.addHandler(handler)
    logger.debug("Logging configured (dest=%s, debug=%s)", log_dest, debug)
    return logger

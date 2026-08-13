import logging
import sys


class Logger:
    """Thin wrapper around Python's built in logger"""
    """At some point in the future, we'll use this to send webhooks."""

    _DEFAULT_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        name: str = "app",
        level: int = logging.INFO,
        fmt: str = _DEFAULT_FMT,
        datefmt: str = _DEFAULT_DATEFMT,
        propagate: bool = False,
    ):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.propagate = propagate

        # Avoid duplicate handlers if instantiated multiple times with same name
        if self._logger.handlers:
            self._logger.handlers.clear()

        formatter = logging.Formatter(fmt, datefmt=datefmt)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    # --- passthroughs ---
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        # Use inside an except block; auto-includes traceback
        self._logger.exception(msg, *args, **kwargs)

    def set_level(self, level: int):
        self._logger.setLevel(level)
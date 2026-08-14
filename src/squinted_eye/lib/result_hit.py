import logging

from logger import logger


class result_hit:
    """Function we call when we find a result."""

    def __init__(self, name: str = "app", level: int = logging.INFO):
        self.logger = logger(name=name, level=level)

    def hit(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
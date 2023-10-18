import logging


class ColorFormatter(logging.Formatter):
    """Форматированный logging c цветами.

    Цвета можно посмотреть: https://gist.github.com/raghav4/48716264a0f426cf95e4342c21ada8e7
    """
    gray: str = "\x1b[90;20m"
    green: str = "\x1b[32;20m"
    blue: str = "\x1b[34;20m"
    yellow: str = "\x1b[33;20m"
    red: str = "\x1b[31;20m"
    bold_red: str = "\x1b[31;1m"
    reset: str = "\x1b[0m"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.NOTSET: gray + format + reset,
        logging.DEBUG: green + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(ColorFormatter())

logger.addHandler(ch)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handling loggers
"""

import sys
import logging

HAS_IPYTHON = False
try:
    from IPython.core.interactiveshell import InteractiveShell

    HAS_IPYTHON = True
except ImportError:
    pass

# Enable color output in Jupyter Notebook
if HAS_IPYTHON:
    InteractiveShell.ast_node_interactivity = "all"

# set up default logging configureation
_default_format = "[%(name)-s | %(levelname)-8s] %(message)s"
_default_format_file = "[%(asctime)s | %(name)-s | %(levelname)-8s] %(message)s"
_default_datefmt = "%Y-%m-%d %H:%M:%S"
_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.FATAL,
    "CRITICAL": logging.CRITICAL,
}

# # needs colorlog, not enabled yet!
# _default_colors = {'DEBUG': 'cyan',
#                    'INFO': 'green',
#                    'WARNING': 'yellow',
#                    'ERROR':    'red',
#                    'CRITICAL': 'red'}
#

_log = False


# Define a custom logging formatter with color
class ConsoleColorFormatter(logging.Formatter):
    """Colored logging formatter intended for the console output"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;21m"
    reset = "\x1b[0m"
    format = _default_format

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def logging_basicConfig(level="INFO"):
    """logging basic configuration"""
    global _log
    logging.basicConfig(
        level=_levels[level], format=_default_format, datefmt=_default_datefmt
    )
    # filename='{0}.log'.format(tempfile.mktemp()),
    # filemode='w')
    _log = True


def getConsoleHandler():
    """Default console handler"""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleColorFormatter())
    return console_handler


def getFileHandler(filename, mode="a"):
    """Default console handler"""
    file_handler = logging.FileHandler(filename, mode=mode)
    file_handler.setFormatter(
        logging.Formatter(fmt=_default_format_file, datefmt=_default_datefmt)
    )
    return file_handler


def getLogger(name, level="INFO"):
    """Utility function to get the logger with customization

    .. warning:: NOT WORKING AS EXPECTED -> FIXME!!!

    Parameters
    ----------
    name : str
        name of the logger
    level : str (optional)
        logging level ['INFO']
    """
    if not _log:
        logging_basicConfig(level=level)
    logger = logging.getLogger(name)
    logger.setLevel(_levels[level])

    if logger.hasHandlers():
        logger.handlers.clear()
        logger.debug("custom logger setup > clear handlers")
    logger.addHandler(getConsoleHandler())
    """Clear existing handlers and add current one"""

    logger.propagate = False
    logger.debug("custom logger setup > finished")

    return logger


def test_logger(level="DEBUG"):
    """Test custom logger"""
    logger = getLogger("larch.test", level=level)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    import tempfile

    flog = tempfile.mktemp(prefix="test_logger_", suffix=".log")
    logger.addHandler(getFileHandler(flog))
    logger.info(f"Added a file handler -> {flog}")
    logger.info("Testing all log levels (again):")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")


if __name__ == "__main__":
    test_logger()

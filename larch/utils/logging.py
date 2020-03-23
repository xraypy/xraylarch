#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handling loggers
"""
import sys
import logging

# import tempfile

# set up default logging configureation
_default_format = '[%(name)-s] %(levelname)-s : %(message)s'
_default_format_file = '%(asctime)s [%(name)-s] %(levelname)-s : %(message)s'
_default_datefmt = '%Y-%m-%d %H:%M'
_levels = {'DEBUG': logging.DEBUG,
           'INFO': logging.INFO,
           'WARNING': logging.WARNING,
           'ERROR': logging.ERROR,
           'FATAL': logging.FATAL,
           'CRITICAL': logging.CRITICAL}

# # needs colorlog, not enabled yet!
# _default_colors = {'DEBUG': 'cyan',
#                    'INFO': 'green',
#                    'WARNING': 'yellow',
#                    'ERROR':    'red',
#                    'CRITICAL': 'red'}
#

_log = False


def logging_basicConfig(level='INFO'):
    """logging basic configuration"""
    global _log
    logging.basicConfig(level=_levels[level],
                        format=_default_format,
                        datefmt=_default_datefmt)
                        # filename='{0}.log'.format(tempfile.mktemp()),
                        # filemode='w')
    _log = True


def getConsoleHandler():
    """Default console handler"""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(fmt=_default_format))
    return console_handler


def getFileHandler(filename, mode='a'):
    """Default console handler"""
    file_handler = logging.FileHandler(filename, mode=mode)
    file_handler.setFormatter(logging.Formatter(fmt=_default_format_file,
                                                datefmt=_default_datefmt))
    return file_handler


def getLogger(name, level='INFO'):
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

    if (logger.hasHandlers()):
        logger.handlers.clear()
        logger.debug("custom logger setup > clear handlers")
    logger.addHandler(getConsoleHandler())
    """Clear existing handlers and add current one"""

    logger.propagate = False
    logger.debug("custom logger setup > finished")

    return logger


def test_logger(level='DEBUG'):
    """Test custom logger"""
    logger = getLogger('test', level=level)
    logger.debug('a debug message')
    logger.info('an info message')
    logger.warning('a warning message')
    logger.error('an error message')
    logger.critical('a critical message')
    import tempfile
    flog = tempfile.mktemp(prefix='test_logger_', suffix='.log')
    logger.addHandler(getFileHandler(flog))
    logger.info(f'added file handler -> {flog}')
    logger.info('testing again all log levels:')
    logger.debug('a debug message')
    logger.info('an info message')
    logger.warning('a warning message')
    logger.error('an error message')
    logger.critical('a critical message')



if __name__ == '__main__':
    test_logger()

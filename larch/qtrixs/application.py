#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RIXS GUI APPLICATION
====================
"""
import sys
import argparse
import signal

from larch.utils.logging import getLogger
_logger = getLogger('lach.qtrixs.application')


def createParser():
    """Application parser"""
    parser = argparse.ArgumentParser(description="Larch-RIXS GUI parser")

    return parser


def mainQtApp(options):
    """Part of the main application depending on Qt"""
    try:
        # it should be loaded before h5py
        import hdf5plugin  # noqa
    except ImportError:
        _logger.debug("Backtrace", exc_info=True)
    import h5py

    import silx
    import silx.utils.files
    from silx.gui import qt

    # Make sure matplotlib is configured
    # Needed for Debian 8: compatibility between Qt4/Qt5 and old matplotlib
    from silx.gui.plot import matplotlib

    _logger.info('Starting application')
    app = qt.QApplication([])
    qt.QLocale.setDefault(qt.QLocale.c())

    def sigintHandler(*args):
        """Handler for the SIGINT signal."""
        qt.QApplication.quit()

    signal.signal(signal.SIGINT, sigintHandler)
    sys.excepthook = qt.exceptionHandler

    timer = qt.QTimer()
    timer.start(500)
    # Application have to wake up Python interpreter, else SIGINT is not
    # catched
    timer.timeout.connect(lambda: None)

    from .window import RixsAppWindow as MainWindow

    window = MainWindow(with_ipykernel=True)
    window.setAttribute(qt.Qt.WA_DeleteOnClose, True)

    window.show()
    _logger.info('Finished initialization')

    # Very important, IPython-specific step: this gets GUI event loop
    # integration going, and it replaces calling app.exec_()
    _logger.info('Starting the IPython kernel')
    window._ipykernel.kernel.start()

    result = app.exec_()
    # remove ending warnings relative to QTimer
    app.deleteLater()
    return result


def main(argv):
    """Main function to launch sloth-daxs as an Application

    Parameters
    ----------
    argv : list
        command line arguments
    """
    parser = createParser()
    options = parser.parse_args(argv[1:])
    mainQtApp(options)


if __name__ == '__main__':
    main(sys.argv)

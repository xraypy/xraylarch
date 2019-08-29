#!/usr/bin/env python
# coding: utf-8
"""This module provides integration of an IPython kernel.

.. note:: Initial idea taken from ipykernel example `internal_ipkernel.py`.
"""
from __future__ import absolute_import, division
import sys
from ipykernel import connect_qtconsole
from ipykernel.kernelapp import IPKernelApp


class InternalIPyKernel(object):

    def init_kernel(self, backend='qt', log_level='INFO'):
        _optslist = ['python',
                     '--gui={0}'.format(backend),
                     '--log-level={0}'.format(log_level)]

        self.kernel = IPKernelApp.instance()
        self.kernel.initialize(_optslist)

        # To create and track active qt consoles
        self.consoles = []

        # This application will also act on the shell user namespace
        self.namespace = self.kernel.shell.user_ns
        self.add_to_namespace('kernel', self.kernel)

    def print_namespace(self, evt=None):
        print("\n***Variables in User namespace***")
        for k, v in self.namespace.items():
            if not k.startswith('_'):
                print('%s -> %r' % (k, v))
        sys.stdout.flush()

    def add_to_namespace(self, namestr, nameobj):
        """Extend kernel namespace."""
        self.namespace[namestr] = nameobj

    def new_qt_console(self):
        """Start a new qtconsole connected to our kernel."""
        self.consoles.append(connect_qtconsole(self.kernel.abs_connection_file, profile=self.kernel.profile))

    def cleanup_consoles(self):
        for c in self.consoles:
            c.kill()

#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import numpy as np

from functools import partial
from collections import OrderedDict

from larch.math import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, CEN, RCEN,
                         LCEN, Font)

from .taskpanel import TaskPanel


np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)


PlotOne_Choices = OrderedDict((('Raw Data', 'mu'),
                               ('Normalized', 'norm'),
                               ('Derivative', 'dmude'),
                               ('Normalized + Derivative', 'norm+deriv')))

PlotSel_Choices = OrderedDict((('Raw Data', 'mu'),
                               ('Normalized', 'norm'),
                               ('Flattened', 'flat'),
                               ('Derivative', 'dmude')))


class LASSOPanel(TaskPanel):
    """LASSO Panel"""


    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='lasso_config',
                           title='LASSO / Partial Least Squares Analysis',
                           **kws)

    def process(self, dgroup, **kws):
        """ handle LASSO processing"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

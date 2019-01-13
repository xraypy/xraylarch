#!/usr/bin/env python
"""
wx widgets for Larch
"""
import platform
import wx

from . import larchframe
from . import larchfilling
from . import readlinetextctrl


from wxutils import (set_sizer, pack, SetTip, Font, HLine, Check, MenuItem,
                     Popup, is_wxPhoenix, RIGHT, LEFT, CEN , LCEN, RCEN,
                     CCEN, LTEXT, FRAMESTYLE, hms, DateTimeCtrl, Button,
                     ToggleButton, BitmapButton, Choice, YesNo, SimpleText,
                     TextCtrl, LabeledTextCtrl, HyperText, EditableListBox,
                     get_icon, GUIColors, OkCancel, FileOpen, FileSave,
                     SelectWorkdir, fix_filename, SavedParameterDialog,
                     FileCheckList, FileDropTarget, GridPanel, RowPanel,
                     make_steps, set_float, FloatCtrl, NumericCombo)


from .floatspin import FloatSpin, FloatSpinWithPin


from .notebooks import flatnotebook

from .larchframe import LarchFrame, LarchPanel
from .columnframe import ColumnDataFileFrame, EditColumnFrame
from .athena_importer import AthenaImporter
from .reportframe import ReportFrame
from .parameter import ParameterWidgets



FONTSIZE = 8
if platform.system() in ('Windows', 'Darwin'):
    FONTSIZE = 10

#############################
## Hack System and Startfile on Windows totry to track down
## weird error of starting other applications, like Mail
if platform.system() == 'Windows':
    from os import system as os_system
    from os import startfile as os_startfile
    def my_system(command):
        print("#@ os.system: ", command)
        return os_system(command)

    def my_startfile(filepath, operation=None):
        print("#@ os.startfile: ", filepath, operation)
        try:
            if operation is None:
                return os_startfile(filepath)
            else:
                return os_startfile(filepath, operation)
        except WindowsError:
            print("#@ os.startfile failed: ", filepath, operation)

    os.system = my_system
    os.startfile = my_startfile
#############################

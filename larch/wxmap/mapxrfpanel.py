#!/usr/bin/env python
"""
XRF Analysis Panel
"""

import json
from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled

import numpy as np

from ..wxlib import (LarchPanel, LarchFrame, EditableListBox, SimpleText,
                     FloatCtrl, Font, pack, Popup, Button, MenuItem,
                     Choice, Check, GridPanel, FileSave, HLine)
from ..utils.strutils import bytes2str, version_ge

from ..xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT

TOP_MSG = "Select Spectrum and Fit to Apply to Map"
NOFITS_MSG = "No XRF fits available.  Use XRF Viewer to fit spectrum first."
HASFITS_MSG = "Select Spectrum and Fit to it to Apply to Map."


class XRFAnalysisPanel(scrolled.ScrolledPanel):
    """Panel of XRF Analysis results"""
    label  = 'XRF Analysis'
    def __init__(self, parent, owner=None, **kws):

        self.owner = owner
        self.map   = None
        self.cfile = None
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        sizer = wx.GridBagSizer(3, 3)

        self.mca_choice = Choice(self, size=(400, -1), choices=[],
                                   action=self.onSpectrum)
        self.fit_choice = Choice(self, size=(300, -1), choices=[])
        self.use_nnls = Check(self, label='force non-negative (~4x slower)',
                              default=False)

        save_btn = Button(self, 'Calculate and Save Element Mapss', size=(300, -1),
                          action=self.onSaveArrays)

        self.scale = FloatCtrl(self, value=1.0, minval=0, precision=5, size=(150, -1))
        self.name  = wx.TextCtrl(self, value='abundance', size=(300, -1))

        self.fit_status = SimpleText(self, label=NOFITS_MSG)

        ir = 0
        sizer.Add(SimpleText(self, TOP_MSG), (ir, 0), (1, 5), ALL_LEFT, 2)

        ir += 1
        sizer.Add(self.fit_status,           (ir, 0), (1, 5), ALL_LEFT, 2)


        ir += 1
        sizer.Add(SimpleText(self, 'XRF Spectrum:'), (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.mca_choice,                 (ir, 1), (1, 2), ALL_LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(self, 'Fit Label:'), (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.fit_choice,                (ir, 1), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Scaling Factor:'), (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.scale,                       (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.use_nnls,                    (ir, 2), (1, 1), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Group Name:'), (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.name,                       (ir, 1), (1,21), ALL_LEFT, 2)
        ir += 1
        sizer.Add(save_btn,                        (ir, 0), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(HLine(self, size=(400, 4)), (ir, 0), (1, 4), ALL_LEFT, 2)

#         ir += 1
#         sizer.Add(SimpleText(self, 'Work Arrays: '), (ir, 0), (1, 1), ALL_LEFT, 2)
#
#         self.workarray_choice = Choice(self, size=(200, -1),
#                                        action=self.onSelectArray)
#         btn_delete  = Button(self, 'Delete Array',  size=(90, -1),
#                               action=self.onDeleteArray)
#         self.info1   = wx.StaticText(self, -1, '',  size=(250, -1))
#         self.info2   = wx.StaticText(self, -1, '',  size=(250, -1))


        pack(self, sizer)
        self.SetupScrolling()

    def onSpectrum(self, event=None):
        print("selected spectrum ", self.spect_choice.GetStringSelection())

    def onSaveArrays(self, evt=None):
        print("on save arrays")
        print(self.owner.larch)

    def onOtherSaveArray(self, evt=None):
        name = self.name_in.GetValue()
        expr = self.expr_in.GetValue()
        xrmfile = self.owner.current_file
        info = []
        for varname in sorted(self.varfile.keys()):
            fname   = self.varfile[varname].GetStringSelection()
            roiname = self.varroi[varname].GetStringSelection()
            dname   = self.vardet[varname].GetStringSelection()
            dtcorr  = self.varcor[varname].IsChecked()
            info.append((varname, (fname, roiname, dname, dtcorr)))

        if self.map is None:
            self.onShowMap()

        if name in xrmfile.work_array_names():
            if (wx.ID_YES == Popup(self.owner, """Overwrite Array '%s' for %s?
    WARNING: This cannot be undone
    """ % (name, xrmfile.filename),
                                   'Overwrite Array?', style=wx.YES_NO)):
                xrmfile.del_work_array(h5str(name))
            else:
                return
        xrmfile.add_work_array(self.map, h5str(name),
                               expression=h5str(expr),
                               info=json.dumps(info))

        for p in self.owner.nb.pagelist:
            if hasattr(p, 'update_xrmmap'):
                p.update_xrmmap(xrmfile=xrmfile, set_detectors=True)


    def update_xrmmap(self, xrmfile=None, set_detectors=None):
        if xrmfile is None:
            xrmfile = self.owner.current_file
        self.cfile = xrmfile
        symtab = self.owner.larch.symtable
        xrfdat_group = getattr(symtab, '_xrfdata', None)
        mcas = {}
        if xrfdat_group is not None:
            for sym in dir(xrfdat_group):
                obj = getattr(xrfdat_group, sym)
                label = getattr(obj, 'label', None)
                hist = getattr(obj, 'fit_history', None)
                if label is not None and hist is not None:
                    mcas[label] = [h.label for h in hist]
        if len(mcas) > 0:
            self.fit_status.SetLabel(HASFITS_MSG)
            cur_mcalabel = self.mca_choices.GetSelection()
            self.mca_choices.Clear()
            mca_names = list(mca.keys())
            self.mca_choices.AppendItems(mca_names)
            self.mca_choices.SetSelection(cur_mcalabel)
            hist = mca[mca_names[0]]
            self.fit_choices.AppendItems(hist)
            self.fit_choices.SetSelection(0)

#         print(symtab,
#               ' model: ', getattr(symtab, '_xrfmodel', 'no xrf model'),
#               ' data : ', getattr(symtab, '_xrfdata', 'no xrf data'))




#         self.xrmmap = xrmfile.xrmmap
#         self.set_file_choices(self.owner.filelist.GetItems())
#         self.set_det_choices()
#         self.set_workarray_choices(self.xrmmap)
#
#         for vfile in self.varfile.values():
#             vfile.SetSelection(-1)
#         self.info1.SetLabel('')
#         self.info2.SetLabel('')

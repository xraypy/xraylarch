#!/usr/bin/env python
"""
XRF Analysis Panel
"""
import os
import json
from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled

import numpy as np

from ..wxlib import (LarchPanel, LarchFrame, EditableListBox, SimpleText,
                     FloatCtrl, Font, pack, Popup, Button, MenuItem,
                     Choice, Check, GridPanel, FileSave, FileOpen, HLine)
from ..utils.strutils import bytes2str, version_ge, fix_varname

from ..xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup

from ..wxlib.xrfdisplay_utils import (XRFGROUP, mcaname,
                                      XRFRESULTS_GROUP,
                                      MAKE_XRFRESULTS_GROUP)

CEN = wx.ALIGN_CENTER
LEFT = wx.ALIGN_LEFT
RIGHT = wx.ALIGN_RIGHT
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT

NOFITS_MSG  = "No XRF Fits: Use XRFViewer to fit spectrum."
HASFITS_MSG = "Select XRF Fit to build elemental maps"

from ..wxlib.xrfdisplay_utils import (XRFGROUP, MAKE_XRFGROUP_CMD, next_mcaname)

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
        self.current_fit = 0
        self.fit_choice = Choice(self, size=(375, -1), choices=[])

        self.use_nnls = Check(self, label='force non-negative (~5x slower)',
                              default=False)

        save_btn = Button(self, 'Calculate Element Maps', size=(200, -1),
                          action=self.onSaveArrays)

        load_btn = Button(self, 'Load Saved XRF Model', size=(200, -1),
                          action=self.onLoadXRFModel)

        self.scale = FloatCtrl(self, value=1.0, minval=0, precision=5, size=(100, -1))
        self.name  = wx.TextCtrl(self, value='abundance', size=(375, -1))

        self.fit_status = SimpleText(self, label=NOFITS_MSG)

        ir = 0
        sizer.Add(self.fit_status,           (ir, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(load_btn,                  (ir, 2), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Use Fit Label:'),  (ir, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.fit_choice,                     (ir, 1), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Scaling Factor:'), (ir, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.scale,                          (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.use_nnls,                       (ir, 2), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Save to Group:'), (ir, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.name,                          (ir, 1), (1, 3), ALL_LEFT, 2)
        ir += 1
        sizer.Add(save_btn,                           (ir, 0), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(HLine(self, size=(600, 5)), (ir, 0), (1, 4), ALL_LEFT, 2)

        pack(self, sizer)
        self.SetupScrolling()

    def onSaveArrays(self, evt=None):
        self.current_fit = cfit = self.fit_choice.GetSelection()
        try:
            thisfit = self.owner.larch.symtable._xrfresults[cfit]
        except:
            thisfit = None
        if thisfit is None:
            print("Unknown fit? " , cfit,
                  self.owner.larch.symtable._xrfresults)
            return

        scale = self.scale.GetValue()
        method = 'nnls' if self.use_nnls.IsChecked() else 'lstsq'
        xrmfile = self.owner.current_file
        workname = fix_varname(self.name.GetValue())

        cmd = """weights = _xrfresults[{cfit:d}].decompose_map({groupname:s}.xrmmap['mcasum/counts'],
        scale={scale:.6f}, pixel_time={ptime:.5f},method='{method:s}')
        for key, val in weights.items():
             {groupname:s}.add_work_array(val, fix_varname(key), parent='{workname:s}')
        #endfor
        """
        cmd = cmd.format(cfit=cfit, groupname=xrmfile.groupname, ptime=xrmfile.pixeltime,
                         workname=workname, scale=scale, method=method)
        self.owner.larch.eval(cmd)
        dlist = xrmfile.get_detector_list(use_cache=False)
        for p in self.owner.nb.pagelist:
            if hasattr(p, 'update_xrmmap'):
                p.detectors_set = False
                p.update_xrmmap(xrmfile=xrmfile, set_detectors=True)

    def onLoadXRFModel(self, evt=None):
        _larch = self.owner.larch
        symtab = _larch.symtable
        FILE_WILDCARDS = "XRF Model Files(*.xrfmodel)|*.xrfmodel|All files (*.*)|*.*"

        dlg = wx.FileDialog(self, message="Read XRF Model File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN)
        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if path is not None:
            _, fname = os.path.split(path)
            if not symtab.has_group(XRFRESULTS_GROUP):
                _larch.eval(MAKE_XRFRESULTS_GROUP)
            _larch.eval("tmp = xrf_fitresult('{:s}')".format(path))
            _larch.eval("tmp.filename = '{:s}'".format(fname))
            _larch.eval("_xrfresults.insert(0, tmp)")
            _larch.eval("del tmp")
            self.current_fit = 0
            self.update_xrmmap()

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
        xrfresults = getattr(symtab, '_xrfresults', [])
        fit_names = ["%s: %s" % (a.label, a.mcalabel) for a in xrfresults]

        if len(fit_names) > 0:
            self.fit_status.SetLabel(HASFITS_MSG)
            self.fit_choice.Clear()
            self.fit_choice.AppendItems(fit_names)
            self.fit_choice.SetSelection(self.current_fit)

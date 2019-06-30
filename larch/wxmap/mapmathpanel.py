#!/usr/bin/env python
"""
GUI for displaying maps from HDF5 files

"""

import os
import platform
import sys
import time
import json
import socket
import datetime
from functools import partial
from threading import Thread

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception


import h5py
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

VARNAMES = ('a', 'b', 'c', 'd', 'e', 'f')

class MapMathPanel(scrolled.ScrolledPanel):
    """Panel of Controls for doing math on arrays from Map data"""
    label  = 'Map Math'
    def __init__(self, parent, owner=None, **kws):

        self.map   = None
        self.cfile = None

        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner
        sizer = wx.GridBagSizer(3, 3)
        bpanel = wx.Panel(self)
        show_new = Button(bpanel, 'Show New Map',     size=(125, -1),
                          action=partial(self.onShowMap, new=True))
        show_old = Button(bpanel, 'Replace Last Map', size=(125, -1),
                                   action=partial(self.onShowMap, new=False))
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(show_new, 0, 3)
        bsizer.Add(show_old, 0, 3)
        pack(bpanel, bsizer)

        save_arr = Button(self, 'Save Array', size=(120, -1),
                          action=self.onSaveArray)

        self.expr_in = wx.TextCtrl(self, -1,   '', size=(180, -1))
        self.name_in = wx.TextCtrl(self, -1,   '', size=(180, -1))

        ir = 0
        txt = """Enter Math Expressions for Map: a+b, (a-b)/c, log10(a+0.1),  etc"""
        sizer.Add(SimpleText(self, txt),    (ir, 0), (1, 6), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Expression:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.expr_in,   (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(bpanel,  (ir, 2), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Array Name:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.name_in,   (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(save_arr,  (ir, 2), (1, 1), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Array'),       (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'File'),        (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Detector'),    (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'ROI'),         (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'DT Correct?'), (ir, 4), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Array Shape'), (ir, 5), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Data Range'), (ir, 6), (1, 1), ALL_CEN, 2)

        self.varfile  = {}
        self.varroi   = {}
        self.varshape = {}
        self.varrange = {}
        self.vardet   = {}
        self.varcor   = {}
        for varname in VARNAMES:
            self.varfile[varname]  = vfile  = Choice(self, size=(250, -1),
                                                     action=partial(self.onFILE, varname=varname))
            self.varroi[varname]   = vroi   = Choice(self, size=(125, -1),
                                                     action=partial(self.onROI, varname=varname))
            self.vardet[varname]   = vdet   = Choice(self, size=(100, -1),
                                                     action=partial(self.onDET, varname=varname))
            self.varcor[varname]   = vcor   = wx.CheckBox(self, -1, ' ')
            self.varshape[varname] = vshape = SimpleText(self, '(, )',
                                                          size=(125, -1))
            self.varrange[varname] = vrange = SimpleText(self, '[   :    ]',
                                                         size=(125, -1))
            vcor.SetValue(self.owner.dtcor)
            vdet.SetSelection(0)

            ir += 1
            sizer.Add(SimpleText(self, '%s = ' % varname),    (ir, 0), (1, 1), ALL_CEN, 2)
            sizer.Add(vfile,                        (ir, 1), (1, 1), ALL_CEN, 2)
            sizer.Add(vdet,                         (ir, 2), (1, 1), ALL_CEN, 2)
            sizer.Add(vroi,                         (ir, 3), (1, 1), ALL_CEN, 2)
            sizer.Add(vcor,                         (ir, 4), (1, 1), ALL_CEN, 2)
            sizer.Add(vshape,                       (ir, 5), (1, 1), ALL_LEFT, 2)
            sizer.Add(vrange,                       (ir, 6), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(HLine(self, size=(350, 4)), (ir, 0), (1, 5), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Work Arrays: '), (ir, 0), (1, 1), ALL_LEFT, 2)

        self.workarray_choice = Choice(self, size=(200, -1),
                                       action=self.onSelectArray)
        btn_delete  = Button(self, 'Delete Array',  size=(90, -1),
                              action=self.onDeleteArray)
        self.info1   = wx.StaticText(self, -1, '',  size=(250, -1))
        self.info2   = wx.StaticText(self, -1, '',  size=(250, -1))


        sizer.Add(self.workarray_choice, (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(btn_delete, (ir, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.info1, (ir+1, 0), (1, 3), ALL_LEFT, 2)
        sizer.Add(self.info2, (ir+2, 0), (3, 3), ALL_LEFT, 2)

        pack(self, sizer)
        self.SetupScrolling()

    def on_select(self):
        for v in VARNAMES:
            self.onFILE(evt=None, varname=v)


    def onSelectArray(self, evt=None):
        xrmfile = self.owner.current_file
        name = self.workarray_choice.GetStringSelection()
        dset = xrmfile.get_work_array(h5str(name))
        expr = bytes2str(dset.attrs.get('expression', '<unknonwn>'))
        self.info1.SetLabel("Expression: %s" % expr)

        info = json.loads(bytes2str(dset.attrs.get('info', [])))
        buff = []
        for var, dat in info:
            fname, aname, det, dtc = dat
            if dat[1] != '1':
                buff.append("%s= %s('%s', det=%s, dtcorr=%s)" % (var, fname, aname, det, dtc))
        self.info2.SetLabel('\n'.join(buff))

    def onDeleteArray(self, evt=None):
        name = self.workarray_choice.GetStringSelection()
        xrmfile = self.owner.current_file

        if (wx.ID_YES == Popup(self.owner, """Delete Array '%s' for %s?
    WARNING: This cannot be undone
    """ % (name, xrmfile.filename),
                               'Delete Array?', style=wx.YES_NO)):
                xrmfile.del_work_array(h5str(name))
                self.update_xrmmap(xrmfile)

    def onSaveArray(self, evt=None):
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
        # print("Add Work Array: ", name, info)
        xrmfile.add_work_array(self.map, h5str(name),
                               expression=h5str(expr),
                               info=json.dumps(info))

        for p in self.owner.nb.pagelist:
            print("update ", p, hasattr(p, 'update_xrmmap'))
            if hasattr(p, 'update_xrmmap'):
                p.update_xrmmap(xrmfile=xrmfile)

    def onFILE(self, evt=None, varname='a'):

        fname   = self.varfile[varname].GetStringSelection()
        if fname not in (None, 'None', ''):
            shape = self.owner.filemap[fname].get_shape()
            self.varshape[varname].SetLabel('%s' % repr(shape))

    def onDET(self, evt, varname='a'):
        self.set_roi_choices(varname=varname)

    def onROI(self, evt, varname='a'):
        fname   = self.varfile[varname].GetStringSelection()
        roiname = self.varroi[varname].GetStringSelection()
        dname   = self.vardet[varname].GetStringSelection()
        dtcorr  = self.varcor[varname].IsChecked()

        shape = self.owner.filemap[fname].get_shape()
        self.varshape[varname].SetLabel('%s' % repr(shape))

        map = self.owner.filemap[fname].get_roimap(roiname, det=dname, dtcorrect=dtcorr)
        self.varrange[varname].SetLabel('[%g:%g]' % (map.min(), map.max()))

    def update_xrmmap(self, xrmfile=None):

        if xrmfile is None:
            xrmfile = self.owner.current_file

        self.cfile = xrmfile
        self.xrmmap = xrmfile.xrmmap

        self.set_det_choices()
        self.set_workarray_choices(self.xrmmap)

        for vfile in self.varfile.values():
            vfile.SetSelection(-1)
        self.info1.SetLabel('')
        self.info2.SetLabel('')

    def set_det_choices(self, varname=None):

        det_list = self.cfile.get_detector_list()
        if varname is None:
            for wid in self.vardet.values():
                wid.SetChoices(det_list)
        else:
            self.vardet[varname].SetChoices(det_list)
        self.set_roi_choices(varname=varname)


    def set_roi_choices(self, varname=None):
        if varname is None:
            for varname in self.vardet.keys():
                dname = self.vardet[varname].GetStringSelection()
                rois = self.update_roi(dname)
                self.varroi[varname].SetChoices(rois)
        else:
            dname = self.vardet[varname].GetStringSelection()
            rois = self.update_roi(dname)
            self.varroi[varname].SetChoices(rois)


    def update_roi(self, detname):
        return self.cfile.get_roi_list(detname)

    def set_workarray_choices(self, xrmmap):

        c = self.workarray_choice
        c.Clear()
        if 'work' in xrmmap:
            choices = [a for a in xrmmap['work']]
            c.AppendItems(choices)
            c.SetSelection(len(choices)-1)

    def set_file_choices(self, fnames):
        for wid in self.varfile.values():
            wid.SetChoices(fnames)

        for varname in VARNAMES:
            fname = self.varfile[varname].GetStringSelection()
            if fname in (None, 'None', ''):
                self.varfile[varname].SetSelection(0)


    def onShowMap(self, event=None, new=True):
        def get_expr(wid):
            val = str(wid.Value)
            if len(val) == 0:
                val = '1'
            return val
        expr_in = get_expr(self.expr_in)

        files = []
        _larch = self.owner.larch
        filemap = self.owner.filemap

        for varname in self.varfile.keys():
            try:
                _larch.symtable.get_symbol(varname)
                _larch.symtable.del_symbol(str(varname))
            except:
                pass
            fname   = self.varfile[varname].GetStringSelection()
            if fname in filemap:
                if fname not in files:
                    files.append(fname)
                roiname = self.varroi[varname].GetStringSelection()
                dname   = self.vardet[varname].GetStringSelection()
                dtcorr  = self.varcor[varname].IsChecked()

                map = filemap[fname].get_roimap(roiname, det=dname, dtcorrect=dtcorr)
                _larch.symtable.set_symbol(str(varname), map)

        _larch.eval("_mapcalc = %s" % expr_in)
        self.map = _larch.symtable._mapcalc
        omap = self.map[:, 1:-1]
        info  = 'Intensity: [%g, %g]' %(omap.min(), omap.max())
        title = '%se: %s' % (fname, expr_in)
        subtitles = None

        main_file = filemap[files[0]]
        try:
            x = main_file.get_pos(0, mean=True)
        except:
            x = None
        try:
            y = main_file.get_pos(1, mean=True)
        except:
            y = None

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title)

        self.owner.display_map(omap, title=title, subtitles=subtitles,
                               info=info, x=x, y=y, xrmfile=main_file,
                               with_savepos=(len(files)==1))

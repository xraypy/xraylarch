import os
from collections import namedtuple
from functools import partial

import numpy as np
import wx
from wxutils import (SimpleText, Choice, Check, Button, HLine,
                     OkCancel, GridPanel, LCEN)


from larch.utils import index_of, index_nearest
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon


PI = np.pi
DEG2RAD  = PI/180.0

# Planck constant over 2 pi times c: 197.3269718 (0.0000044) MeV fm
PLANCK_HC = 1973.269718 * 2 * PI # hc in eV * Ang = 12398.4193


class DeglitchDialog(wx.Dialog):
    """dialog for deglitching or removing unsightly data points"""
    msg = """Select Points to remove"""

    def __init__(self, parent, dgroup, controller, callback=None, **kws):

        self.dgroup = dgroup
        self.controller = controller
        self.callback = callback
        xdat  = dgroup.xdat[:]
        ydat  = dgroup.ydat[:]
        self.data = [(xdat, ydat)]

        xrange = (max(xdat) - min(xdat))
        xmax = int(max(xdat) + xrange/5.0)
        xmin = int(min(xdat) - xrange/5.0)

        lastx, lasty = self.controller.get_cursor()
        if lastx is None:
            lastx = xmax

        title = "Select Points to Remove"

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 250), title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        bb_xlast = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='x'),
                                tooltip='use last point selected from plot')

        bb_range1 = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='range1'),
                                tooltip='use last point selected from plot')
        bb_range2 = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='range2'),
                                tooltip='use last point selected from plot')

        br_xlast = Button(panel, 'Remove point', size=(125, -1),
                          action=partial(self.on_remove, opt='x'))

        br_range = Button(panel, 'Remove range', size=(125, -1),
                          action=partial(self.on_remove, opt='range'))

        undo = Button(panel, 'Undo remove', size=(125, -1),
                      action=self.on_undo)

        floatopts = dict(precision=2, minval=xmin, maxval=xmax, size=(125, -1))

        self.wid_xlast = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range1 = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range2 = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range2.Disable()

        self.choice_range = Choice(panel, choices=('above', 'below', 'between'),
                                    size=(100, -1), action=self.on_choice)

        panel.Add(SimpleText(panel, 'Single Energy : '), dcol=2)
        panel.Add(bb_xlast)
        panel.Add(self.wid_xlast)
        panel.Add(br_xlast)

        panel.Add(SimpleText(panel, 'Energy Range : '), newrow=True)
        panel.Add(self.choice_range)
        panel.Add(bb_range1)
        panel.Add(self.wid_range1)
        panel.Add(br_range)

        panel.Add((10, 10), dcol=2, newrow=True)
        panel.Add(bb_range2)
        panel.Add(self.wid_range2)

        panel.Add(OkCancel(panel, onOK=self.onOK), dcol=3, newrow=True)
        panel.Add((10, 10))
        panel.Add(undo)

        panel.pack()

    def on_choice(self, event=None):
        if self.choice_range.GetStringSelection() == 'between':
            self.wid_range2.Enable()
        else:
            self.wid_range2.Disable()

    def on_select(self, event=None, opt=None):
        _x, _y = self.controller.get_cursor()
        if opt == 'x':
            self.wid_xlast.SetValue(_x)
        elif opt == 'range1':
            self.wid_range1.SetValue(_x)
        elif opt == 'range2':
            self.wid_range2.SetValue(_x)

    def on_remove(self, event=None, opt=None):
        xwork, ywork = self.data[-1]
        if opt == 'x':
            bad = index_nearest(xwork, self.wid_xlast.GetValue())
        elif opt == 'range':
            rchoice = self.choice_range.GetStringSelection().lower()
            x1 = index_nearest(xwork, self.wid_range1.GetValue())
            x2 = None
            if rchoice == 'below':
                x2, x1 = x1, x2
            elif rchoice == 'between':
                x2 = index_nearest(xwork, self.wid_range2.GetValue())
                if x1 > x2:
                    x1, x2 = x2, x1
            bad = slice(x1, x2, None)

        self.data.append((np.delete(xwork, bad), np.delete(ywork, bad)))
        self.plot_results()

    def on_undo(self, event=None):
        if len(self.data) > 1:
            self.data.pop()
            self.plot_results()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data[-1]
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='deglitching: %s' % fname,
                    label='current', xlabel=dgroup.plot_xlabel,
                    ylabel=dgroup.plot_ylabel)

        if len(self.data) > 1:
            xold, yold = self.data[-2]
            ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                         marker='o', markersize=4, linewidth=2.0,
                         label='previous', show_legend=True)
        ppanel.canvas.draw()

    def onOK(self, event=None):
        xdat, ydat = self.data[-1]
        self.callback(ok=True, dgroup=self.dgroup, xdat=xdat, ydat=ydat)
        self.Destroy()

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")

class EnergyUnitsDialog(wx.Dialog):
    """dialog for selecting, changing energy units, forcing data to eV"""
    msg = """Specify Energy Units"""
    unit_choices = ['eV', 'keV', 'deg', 'steps']

    def __init__(self, parent, unitname, energy_array, **kws):

        self.energy = energy_array[:]

        title = "Select Energy Units to convert to 'eV'"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.en_units = Choice(panel, choices=self.unit_choices, size=(125, -1),
                               action=self.onUnits)
        self.en_units.SetStringSelection(unitname)
        self.mono_dspace = FloatCtrl(panel, value=1.0, minval=0, maxval=100.0,
                                     precision=6, size=(125, -1))
        self.steps2deg  = FloatCtrl(panel, value=1.0, minval=0,
                                     precision=1, size=(125, -1))

        self.mono_dspace.Disable()
        self.steps2deg.Disable()

        panel.Add(SimpleText(panel, 'Energy Units : '), newrow=True)
        panel.Add(self.en_units)

        panel.Add(SimpleText(panel, 'Mono D spacing : '), newrow=True)
        panel.Add(self.mono_dspace)

        panel.Add(SimpleText(panel, 'Mono Steps per Degree : '), newrow=True)
        panel.Add(self.steps2deg)
        panel.Add((5, 5))

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def onUnits(self, event=None):
        units = self.en_units.GetStringSelection()

        self.steps2deg.Disable()
        self.mono_dspace.Disable()

        if units in ('deg', 'steps'):
            self.mono_dspace.Enable()
            if units == 'steps':
                self.steps2deg.Enable()

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('EnergyUnitsResponse', ('ok', 'units', 'energy'))
        ok, units, en = False, 'eV', None

        if self.ShowModal() == wx.ID_OK:
            units = self.en_units.GetStringSelection()
            if units == 'eV':
                en = self.energy
            elif units == 'keV':
                en = self.energy * 1000.0
            elif units in ('steps', 'deg'):
                dspace = float(self.mono_dspace.GetValue())
                if units == 'steps':
                    self.energy /= self.steps2deg.GetValue()
                en = (PLANCK_HC/(2*dspace))/np.sin(self.energy * DEG2RAD)
            ok = True
        return response(ok, units, en)

class MergeDialog(wx.Dialog):
    """dialog for merging groups"""
    msg = """Merge Selected Groups"""
    ychoices = ['raw mu(E)', 'normalized mu(E)']

    def __init__(self, parent, groupnames, outgroup='merge', **kws):
        title = "Merge %i Selected Groups" % (len(groupnames))
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.master_group = Choice(panel, choices=groupnames, size=(250, -1))
        self.yarray_name  = Choice(panel, choices=self.ychoices, size=(250, -1))
        self.group_name   = wx.TextCtrl(panel, -1, outgroup,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Match Energy to : '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'Array to merge  : '), newrow=True)
        panel.Add(self.yarray_name)

        panel.Add(SimpleText(panel, 'New group name  : '), newrow=True)
        panel.Add(self.group_name)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('MergeResponse', ('ok', 'master', 'ynorm', 'group'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            master= self.master_group.GetStringSelection()
            ynorm = 'norm' in self.yarray_name.GetStringSelection().lower()
            gname = self.group_name.GetValue()
            ok = True
        return response(ok, master, ynorm, gname)

class QuitDialog(wx.Dialog):
    """dialog for quitting, prompting to save project"""
    msg = '''You may want to save your project before Quitting!'''

    def __init__(self, parent, **kws):
        title = "Quit Larch XAS Viewer?"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(425, 150))
        self.needs_save = True
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.save = Check(panel, default=False, label='Save Project?')

        panel.Add(SimpleText(panel, self.msg), dcol=3, newrow=True)
        panel.Add((2, 2), newrow=True)
        panel.Add(self.save, newrow=True)
        panel.Add((2, 2), newrow=True)
        panel.Add(HLine(panel, size=(500, 3)), dcol=3, newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self):
        self.Raise()
        response = namedtuple('QuitResponse', ('ok', 'save'))
        ok = (self.ShowModal() == wx.ID_OK)
        return response(ok, self.save.IsChecked())

class RenameDialog(wx.Dialog):
    """dialog for renaming group"""
    msg = """Rename Group"""

    def __init__(self, parent, oldname,  **kws):
        title = "Rename Group %s" % (oldname)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.newname   = wx.TextCtrl(panel, -1, oldname,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Old Name : '), newrow=True)
        panel.Add(SimpleText(panel, oldname))
        panel.Add(SimpleText(panel, 'New Name : '), newrow=True)
        panel.Add(self.newname)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, newname=None):
        self.Raise()
        response = namedtuple('RenameResponse', ('ok', 'newname'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            newname = self.newname.GetValue()
            ok = True
        return response(ok, newname)

class RemoveDialog(wx.Dialog):
    """dialog for removing groups"""
    msg = """Remove Selected Group"""

    def __init__(self, parent, grouplist,  **kws):
        title = "Remove %i Selected Group" % len(grouplist)
        self.grouplist = grouplist
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        panel.Add(SimpleText(panel, 'Remove %i Selected Grous?' % (len(grouplist))),
                  newrow=True, dcol=2)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, ngroups=None):
        self.Raise()
        response = namedtuple('RemoveResponse', ('ok','ngroups'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            ngroups = len(self.grouplist)
            ok = True
        return response(ok, ngroups)

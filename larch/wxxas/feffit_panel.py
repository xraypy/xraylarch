import time
import sys
import ast
import shutil
import string
import json
import math
from copy import deepcopy
from sys import exc_info
from string import printable
from functools import partial
from pathlib import Path

import numpy as np
np.seterr(all='ignore')

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from pyshortcuts import platform
from lmfit import Parameter
from lmfit.model import (save_modelresult, load_modelresult,
                         save_model, load_model)

import lmfit.models as lm_models

from larch import Group, site_config
from larch.math import index_of
from larch.fitting import group2params, param
from larch.utils.jsonutils import encode4js, decode4js
from larch.inputText import is_complete
from larch.utils import fix_varname, fix_filename, gformat, mkdir, isValidName
from larch.io.export_modelresult import export_modelresult
from larch.xafs import feffit_report, feffpath
from larch.xafs.feffdat import FEFFDAT_VALUES
from larch.xafs.xafsutils import FT_WINDOWS

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, pack,
                         Button, HLine, Choice, Check, MenuItem, GUIColors,
                         CEN, RIGHT, LEFT, FRAMESTYLE, Font, FONTSIZE,
                         COLORS, set_color, FONTSIZE_FW, FileSave,
                         FileOpen, flatnotebook, EditableListBox, Popup,
                         ExceptionPopup)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel

from .config import (Feffit_KWChoices, Feffit_SpaceChoices,
                     Feffit_PlotChoices, make_array_choice,
                     PlotWindowChoices)

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

# PlotOne_Choices = [chik, chirmag, chirre, chirmr]

Plot1_Choices = make_array_choice(['chi','chir_mag', 'chir_re', 'chir_mag+chir_re', 'chiq'])
Plot2_Choices = make_array_choice(['noplot', 'chi','chir_mag', 'chir_re', 'chir_mag+chir_re', 'chiq'])

# Plot2_Choices = [noplot] + Plot1_Choices

ScriptWcards = "Fit Models(*.lar)|*.lar|All files (*.*)|*.*"

MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['feffit_top'] = """##### FEFFIT Commands
##
## saved {ctime}
## to use from python, uncomment these import lines:
##

#from larch.xafs import feffit, feffit_dataset, feffit_transform, feffit_report
#from larch.xafs import pre_edge, autobk, xftf, xftr, ff2chi, feffpath
#from larch.fitting import  param_group, param
#from larch.io import read_ascii, read_athena, read_xdi, read_specfile
#
####  for interactive plotting from python (but not the Larch shell!) use:
#from larch.wxlib.xafsplots import plot_chik, plot_chir
#from wxmplot.interactive import get_wxapp
#wxapp = get_wxapp()  # <- needed for plotting to work from python command-line
####
####
"""

COMMANDS['data_source'] = """### you will need to add how the data chi(k) gets built:
###
## data group = {groupname}
## from source = {filename}
## some processing steps for this group (comment out as needed):
"""

COMMANDS['xft'] =  """# ffts on group {groupname:s}
xftf({groupname:s}, kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.3f}, window='{kwindow:s}', kweight={kweight:.3f})
xftr({groupname:s}, rmin={rmin:.3f}, rmax={rmax:.3f}, dr={dr:.3f}, window='{rwindow:s}')
"""

COMMANDS['feffit_params_init'] = """# create feffit Parameter Group to hold fit parameters
_feffit_params = param_group(reff=-1.0)
"""

COMMANDS['feffit_trans'] = """# define Fourier transform and fitting space
_feffit_trans = feffit_transform(kmin={fit_kmin:.3f}, kmax={fit_kmax:.3f}, dk={fit_dk:.4f}, kw={fit_kwstring:s},
                      window='{fit_kwindow:s}', fitspace='{fit_space:s}', rmin={fit_rmin:.3f}, rmax={fit_rmax:.3f})
"""


COMMANDS['feffit_dataset_init'] = """# create empty dataset
_feffit_dataset = feffit_dataset(transform=_feffit_trans)
"""


COMMANDS['paths_init'] = """# make sure dictionary for Feff Paths exists
try:
    npaths = len(_feffpaths.keys())
except:
    _feffcache = {'paths':{}, 'runs':{}}  # group of all paths, info about Feff runs
    _feffpaths = {}    # dict of paths currently in use, copied from _feffcache.paths
#endtry
"""

COMMANDS['paths_reset'] = """# clear existing paths
npaths = 0
_feffpaths = {}
#endtry
"""

COMMANDS['cache_path'] = """
_feffcache['paths']['{title:s}'] = feffpath('{fullpath:s}',
                                             label='{title:s}',feffrun='{feffrun:s}', degen=1)
"""

COMMANDS['use_path'] = """
_feffpaths['{title:s}'] = use_feffpath(_feffcache['paths'], '{title:s}',
                                       s02='{amp:s}',  e0='{e0:s}',
                                       deltar='{delr:s}', sigma2='{sigma2:s}',
                                       third='{third:s}', ei='{ei:s}', use={use})
"""

COMMANDS['ff2chi']   = """# sum paths using a list of paths and a group of parameters
_feffit_dataset = feffit_dataset(data={groupname:s}, transform={trans:s},
                                 refine_bkg={refine_bkg},
                                 paths={paths:s})
_feffit_dataset.model = ff2chi({paths:s}, paramgroup=_feffit_params)
"""

COMMANDS['ff2chi_nodata']   = """# sum paths using a list of paths and a group of parameters
_feffit_dataset = feffit_dataset(transform={trans:s}, paths={paths:s})
_feffit_dataset.model = ff2chi({paths:s}, paramgroup=_feffit_params)
"""

COMMANDS['do_feffit'] = """# build feffit dataset, run feffit
_feffit_dataset = feffit_dataset(data={groupname:s}, transform={trans:s},
                                 refine_bkg={refine_bkg},
                                 paths={paths:s})
_feffit_result = feffit({params}, _feffit_dataset)
if not hasattr({groupname:s}, 'feffit_history'): {groupname}.feffit_history = []
{groupname:s}.feffit_history.insert(0, _feffit_result)
"""

COMMANDS['path2chi'] = """# generate chi(k) and chi(R) for each path
for label, path in {paths_name:s}.items():
     path.calc_chi_from_params({pargroup_name:s})
     xftf(path, kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.3f},
         window='{kwindow:s}', kweight={kweight:.3f})
#endfor
"""

def get_commands(textlines):
    """return list of complete larch command / python function calls
    from a list of text lines such as 'command history'
    """
    out = []
    work_lines = []
    for line in textlines:
        work_lines.append(line)
        work = ' '.join(work_lines)
        if is_complete(work):
            out.append(work)
            work_lines.clear()
    out.extend(work_lines)   # add any dangling text
    return out


class ParametersModel(dv.DataViewIndexListModel):
    def __init__(self, paramgroup, selected=None, pathkeys=None):
        dv.DataViewIndexListModel.__init__(self, 0)
        self.data = []
        if selected is None:
            selected = []
        self.selected = selected

        if pathkeys is None:
            pathkeys = []
        self.pathkeys = pathkeys

        self.paramgroup = paramgroup
        self.read_data()

    def set_data(self, paramgroup, selected=None, pathkeys=None):
        self.paramgroup = paramgroup
        if selected is not None:
            self.selected = selected
        if pathkeys is not None:
            self.pathkeys = pathkeys
        self.read_data()

    def read_data(self):
        self.data = []
        if self.paramgroup is None:
            self.data.append(['param name', False, 'vary', '0.0'])
        else:
            for pname, par in group2params(self.paramgroup).items():
                if any([pname.endswith('_%s' % phash) for phash in self.pathkeys]):
                    continue
                ptype = 'vary'
                if not par.vary:
                    pytype = 'fixed'
                if getattr(par, 'skip', None) not in (False, None):
                    ptype = 'skip'
                par.skip = ptype == 'skip'
                try:
                    value = str(par.value)
                except:
                    value = 'INVALID  '
                if par.expr is not None:
                    ptype = 'constraint'
                    value = "%s := %s" % (value, par.expr)
                sel = pname in self.selected
                self.data.append([pname, sel, ptype, value])
        self.Reset(len(self.data))

    def select_all(self, value=True):
        self.selected = []
        for irow, row in enumerate(self.data):
            self.SetValueByRow(value, irow, 1)
            if value:
                self.selected.append(row[0])

    def select_none(self):
        self.select_all(value=False)

    def GetColumnType(self, col):
        return "bool" if col == 2 else "string"

    def GetValueByRow(self, row, col):
        return self.data[row][col]

    def SetValueByRow(self, value, row, col):
        self.data[row][col] = value
        return True

    def GetColumnCount(self):
        return len(self.data[0])

    def GetCount(self):
        return len(self.data)

    def GetAttrByRow(self, row, col, attr):
        """set row/col attributes (color, etc)"""
        ptype = self.data[row][2]
        if ptype == 'vary':
            attr.SetColour('#000000')
        elif ptype == 'fixed':
            attr.SetColour('#AA2020')
        elif ptype == 'skip':
            attr.SetColour('#50AA50')
        else:
            attr.SetColour('#2010BB')
        return True

class EditParamsFrame(wx.Frame):
    """ edit parameters"""
    def __init__(self, parent=None, feffit_panel=None,
                 paramgroup=None, selected=None):
        wx.Frame.__init__(self, None, -1,
                          'Edit Feffit Parameters',
                          style=FRAMESTYLE, size=(550, 325))

        self.parent = parent
        self.feffit_panel = feffit_panel
        self.paramgroup = paramgroup

        spanel = scrolled.ScrolledPanel(self, size=(500, 275))
        spanel.SetBackgroundColour('#EEEEEE')

        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.NORMAL)

        self.dvc = dv.DataViewCtrl(spanel, style=DVSTYLE)
        self.dvc.SetFont(self.font_fixedwidth)
        self.SetMinSize((500, 250))

        self.model = ParametersModel(paramgroup, selected)
        self.dvc.AssociateModel(self.model)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.dvc, 1, LEFT|wx.ALL|wx.GROW)
        pack(spanel, sizer)

        spanel.SetupScrolling()

        toppan = GridPanel(self, ncols=4, pad=1, itemstyle=LEFT)

        bkws = dict(size=(200, -1))
        toppan.Add(Button(toppan, "Select All",    action=self.onSelAll, size=(175, -1)))
        toppan.Add(Button(toppan, "Select None",             action=self.onSelNone, size=(175, -1)))
        toppan.Add(Button(toppan, "Select Unused Variables", action=self.onSelUnused, size=(200, -1)))
        toppan.Add(Button(toppan, "Remove Selected",   action=self.onRemove, size=(175,-1)), newrow=True)
        toppan.Add(Button(toppan, "'Skip' Selected",    action=self.onSkip, size=(175, -1)))
        toppan.Add(Button(toppan, "Force Refresh",     action=self.onRefresh, size=(200, -1)))
        npan = wx.Panel(toppan)
        nsiz = wx.BoxSizer(wx.HORIZONTAL)

        self.par_name = wx.TextCtrl(npan, -1, value='par_name', size=(125, -1),
                                    style=wx.TE_PROCESS_ENTER)
        self.par_expr = wx.TextCtrl(npan, -1, value='<expression or value>', size=(250, -1),
                                    style=wx.TE_PROCESS_ENTER)
        nsiz.Add(SimpleText(npan, "Add Parameter:"), 0)
        nsiz.Add(self.par_name, 0)
        nsiz.Add(self.par_expr, 1, wx.GROW|wx.ALL)
        nsiz.Add(Button(npan, label='Add', action=self.onAddParam), 0)
        pack(npan, nsiz)

        toppan.Add(npan, dcol=4, newrow=True)
        toppan.Add(HLine(toppan, size=(500, 2)), dcol=5, newrow=True)
        toppan.pack()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(toppan, 0, wx.GROW|wx.ALL, 1)
        mainsizer.Add(spanel, 1, wx.GROW|wx.ALL, 1)
        pack(self, mainsizer)

        columns = [('Parameter',   150, 'text'),
                   ('Select',       75, 'bool'),
                   ('Type',         75, 'text'),
                   ('Value',       200, 'text')]

        for icol, dat in enumerate(columns):
             label, width, dtype = dat
             method = self.dvc.AppendTextColumn
             mode = dv.DATAVIEW_CELL_EDITABLE
             if dtype == 'bool':
                 method = self.dvc.AppendToggleColumn
                 mode = dv.DATAVIEW_CELL_ACTIVATABLE
             method(label, icol, width=width, mode=mode)
             c = self.dvc.Columns[icol]
             c.Alignment = c.Renderer.Alignment = wx.ALIGN_LEFT
             c.SetSortable(False)

        self.dvc.EnsureVisible(self.model.GetItem(0))
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Show()
        self.Raise()
        wx.CallAfter(self.onSelUnused)

    def onSelAll(self, event=None):
        self.model.select_all()
        self.model.read_data()

    def onSelNone(self, event=None):
        self.model.select_none()
        self.model.read_data()

    def onSelUnused(self, event=None):
        curr_syms = self.feffit_panel.get_used_params()
        unused = []
        for pname, par in group2params(self.paramgroup).items():
            if pname not in curr_syms: #  and par.vary:
                unused.append(pname)
        self.model.set_data(self.paramgroup, selected=unused,
                            pathkeys=self.feffit_panel.get_pathkeys())

    def onRemove(self, event=None):
        out = []
        for pname, sel, ptype, val in self.model.data:
            if sel:
                out.append(pname)
        nout = len(out)

        msg = f"Remove {nout:d} Parameters? \n This is not easy to undo!"
        dlg = wx.MessageDialog(self, msg, 'Warning', wx.YES | wx.NO )
        if (wx.ID_YES == dlg.ShowModal()):
            for pname, sel, ptype, val in self.model.data:
                if sel:
                    out.append(pname)
                    if hasattr(self.paramgroup, pname):
                        delattr(self.paramgroup, pname)

            self.model.set_data(self.paramgroup, selected=None,
                                pathkeys=self.feffit_panel.get_pathkeys())
            self.model.read_data()
            self.feffit_panel.get_pathpage('parameters').Rebuild()
        dlg.Destroy()

    def onSkip(self, event=None):
        for pname, sel, ptype, val in self.model.data:
            if sel:
                par = getattr(self.paramgroup, pname, None)
                if par is not None:
                    par.skip = True
        self.model.read_data()
        self.feffit_panel.get_pathpage('parameters').Rebuild()


    def onAddParam(self, event=None):
        par_name = self.par_name.GetValue()
        par_expr = self.par_expr.GetValue()

        try:
            val = float(par_expr)
            ptype = 'vary'
        except:
            val = par_expr
            ptype = 'expr'

        if ptype == 'vary':
            cmd = f"_feffit_params.{par_name} = param({val}, vary=True)"
        else:
            cmd = f"_feffit_params.{par_name} = param(expr='{val}')"

        self.feffit_panel.larch_eval(cmd)
        self.onRefresh()

    def onRefresh(self, event=None):
        self.paramgroup = self.feffit_panel.get_paramgroup()
        self.model.set_data(self.paramgroup,
                            pathkeys=self.feffit_panel.get_pathkeys())
        self.model.read_data()
        self.feffit_panel.get_pathpage('parameters').Rebuild()

    def onClose(self, event=None):
        self.Destroy()


class FeffitParamsPanel(wx.Panel):
    def __init__(self, parent=None, feffit_panel=None, **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 250))
        self.feffit_panel = feffit_panel
        self.parwids = {}
        self.SetFont(Font(FONTSIZE))
        spanel = scrolled.ScrolledPanel(self)
        spanel.SetSize((250, 250))
        spanel.SetMinSize((50, 50))
        panel = self.panel = GridPanel(spanel, ncols=8, nrows=30, pad=1, itemstyle=LEFT)
        panel.SetFont(Font(FONTSIZE))

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=wx.ALIGN_LEFT, **kws)

        panel.Add(SLabel("Feffit Parameters ", colour='#0000AA', size=(200, -1)), dcol=2)
        panel.Add(Button(panel, 'Edit Parameters', action=self.onEditParams),  dcol=2)
        panel.Add(Button(panel, 'Force Refresh', action=self.Rebuild),         dcol=3)

        panel.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        panel.AddMany((SLabel(" Value"), SLabel(" Type"), SLabel(' Bounds'),
                       SLabel("  Min", size=(60, -1)),
                       SLabel("  Max", size=(60, -1)),
                       SLabel(" Expression")))

        self.update()
        panel.pack()
        ssizer = wx.BoxSizer(wx.VERTICAL)
        ssizer.Add(panel, 1,  wx.GROW|wx.ALL, 2)
        pack(spanel, ssizer)

        spanel.SetupScrolling()
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(spanel, 1, wx.GROW|wx.ALL, 2)
        pack(self, mainsizer)

    def Rebuild(self, event=None):
        for pname, parwid in self.parwids.items():
            for x in parwid.widgets:
                x.Destroy()
        self.panel.irow = 1
        self.parwids = {}
        self.update()

    def set_init_values(self, params):
        for pname, par in params.items():
            if pname in self.parwids and par.vary:
                stderr = getattr(par, 'stderr', 0.001)
                try:
                    prec = max(1, min(8, round(2-math.log10(stderr))))
                except:
                    prec = 5
                self.parwids[pname].value.SetValue(("%%.%.df" % prec) % par.value)

    def update(self):
        pargroup = self.feffit_panel.get_paramgroup()
        hashkeys = self.feffit_panel.get_pathkeys()
        params = group2params(pargroup)
        for pname, par in params.items():
            if any([pname.endswith('_%s' % phash) for phash in hashkeys]):
                continue
            if pname not in self.parwids and not hasattr(par, '_is_pathparam'):
                pwids = ParameterWidgets(self.panel, par, name_size=120,
                                         expr_size=200,   float_size=85,
                                         with_skip=True,
                                         widgets=('name', 'value',
                                                  'minval', 'maxval',
                                                  'vary', 'expr'))

                self.parwids[pname] = pwids
                self.panel.Add(pwids.name, newrow=True)
                self.panel.AddMany((pwids.value, pwids.vary, pwids.bounds,
                                    pwids.minval, pwids.maxval, pwids.expr))
                self.panel.pack()

            pwids = self.parwids[pname]
            varstr = 'vary' if par.vary else 'fix'
            if par.expr is not None:
                varstr = 'constrain'
                pwids.expr.SetValue(par.expr)
            if getattr(par, 'skip', None) not in (False, None):
                varstr = 'skip'
            pwids.vary.SetStringSelection(varstr)
            if varstr != 'skip':
                pwids.value.SetValue(par.value)
                pwids.minval.SetValue(par.min)
                pwids.maxval.SetValue(par.max)
            pwids.onVaryChoice()
        self.panel.Update()

    def onEditParams(self, event=None):
        pargroup = self.feffit_panel.get_paramgroup()
        self.feffit_panel.show_subframe('edit_params', EditParamsFrame,
                                        paramgroup=pargroup,
                                        feffit_panel=self.feffit_panel)

    def RemoveParams(self, event=None, name=None):
        if name is None:
            return
        pargroup = self.feffit_panel.get_paramgroup()

        if hasattr(pargroup, name):
            delattr(pargroup, name)
        if name in self.parwids:
            pwids = self.parwids.pop(name)
            pwids.name.Destroy()
            pwids.value.Destroy()
            pwids.vary.Destroy()
            pwids.bounds.Destroy()
            pwids.minval.Destroy()
            pwids.maxval.Destroy()
            pwids.expr.Destroy()
            pwids.remover.Destroy()

    def generate_params(self, event=None):
        s = []
        s.append(COMMANDS['feffit_params_init'])
        for name, pwids in self.parwids.items():
            param = pwids.param
            args = [f'{param.value}']
            minval = pwids.minval.GetValue()
            if np.isfinite(minval):
                args.append(f'min={minval}')
            maxval = pwids.maxval.GetValue()
            if np.isfinite(maxval):
                args.append(f'max={maxval}')

            varstr = pwids.vary.GetStringSelection()
            if varstr == 'skip':
                args.append('skip=True, vary=False')
            elif param.expr is not None and varstr == 'constrain':
                args.append(f"expr='{param.expr}'")
            elif varstr == 'vary':
                args.append(f'vary=True')
            else:
                args.append(f'vary=False')
            args = ', '.join(args)
            cmd = f'_feffit_params.{name} = param({args})'
            s.append(cmd)
        return s


class FeffPathPanel(wx.Panel):
    """Feff Path """
    def __init__(self, parent, feffit_panel, filename, title, user_label,
                 geomstr, absorber, shell, reff, nleg, degen,
                 par_amp, par_e0, par_delr, par_sigma2, par_third, par_ei):

        self.parent = parent
        self.title = title
        self.user_label = fix_varname(f'{title:s}')
        self.feffit_panel = feffit_panel
        self.editing_enabled = False

        wx.Panel.__init__(self, parent, -1, size=(550, 250))
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.fullpath = filename
        pfile = Path(filename).absolute()
        feffdat_file = pfile.name
        dirname = pfile.parent.name

        self.user_label = user_label

        self.nleg = nleg
        self.reff = reff
        self.geomstr = geomstr
        # self.geometry = geometry

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=LEFT, **kws)

        self.wids = wids = {}
        for name, expr in (('label', user_label),
                           ('amp',  par_amp),
                           ('e0',  par_e0),
                           ('delr',   par_delr),
                           ('sigma2', par_sigma2),
                           ('third',  par_third),
                           ('ei',  par_ei)):
            self.wids[name] = wx.TextCtrl(panel, -1, size=(250, -1),
                                          value=expr, style=wx.TE_PROCESS_ENTER)
            wids[name+'_val'] = SimpleText(panel, '', size=(150, -1), style=LEFT)

        wids['use'] = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        wids['del'] = Button(panel, 'Remove This Path', size=(150, -1),
                             action=self.onRemovePath)
        wids['plot_feffdat'] = Button(panel, 'Plot F(k)', size=(150, -1),
                             action=self.onPlotFeffDat)

        scatt = {2: 'Single', 3: 'Double', 4: 'Triple',
                 5: 'Quadruple'}.get(nleg, f'{nleg-1:d}-atom')
        scatt = scatt + ' Scattering'


        title1 = f'{dirname:s}: {feffdat_file:s}  {absorber:s} {shell:s} edge'
        title2 = f'Reff={reff:.4f},  Degen={degen:.1f}, {scatt:s}: {geomstr:s}'

        panel.Add(SLabel(title1, size=(375, -1), colour='#0000AA'),
                  dcol=2,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['use'])
        panel.Add(wids['del'])
        panel.Add(SLabel(title2, size=(425, -1)),
                  dcol=3, style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['plot_feffdat'])

        panel.AddMany((SLabel('Label'),     wids['label'],  wids['label_val']), newrow=True)
        panel.AddMany((SLabel('Amplitude'), wids['amp'],    wids['amp_val']),   newrow=True)
        panel.AddMany((SLabel('E0 '),       wids['e0'],     wids['e0_val']),    newrow=True)
        panel.AddMany((SLabel('Delta R'),   wids['delr'],   wids['delr_val']),  newrow=True)
        panel.AddMany((SLabel('sigma2'),    wids['sigma2'], wids['sigma2_val']),newrow=True)
        panel.AddMany((SLabel('third'),     wids['third'],  wids['third_val']), newrow=True)
        panel.AddMany((SLabel('Eimag'),     wids['ei'],     wids['ei_val']),    newrow=True)
        panel.pack()
        sizer= wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(self, sizer)


    def enable_editing(self):
        for name in ('label', 'amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            self.wids[name].Bind(wx.EVT_TEXT_ENTER, partial(self.onExpression, name=name))
            self.wids[name].Bind(wx.EVT_KILL_FOCUS, partial(self.onExpression, name=name))
        self.editing_enabled = True
        self.wids['label'].SetValue(self.user_label)

    def set_userlabel(self, label):
        self.wids['label'].SetValue(label)

    def get_expressions(self):
        out = {'use': self.wids['use'].IsChecked()}
        for key in ('label', 'amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            val = self.wids[key].GetValue().strip()
            if len(val) == 0: val = '0'
            out[key] = val
        return out

    def onExpression(self, event=None, name=None):
        if name is None:
            return
        expr = self.wids[name].GetValue()
        if name == 'label':
            time.sleep(0.001)
            return

        expr = self.wids[name].GetValue().strip()
        if len(expr) < 1:
            return
        opts= dict(value=1.e-3, minval=None, maxval=None)
        if name == 'sigma2':
            opts['minval'] = 0
            opts['maxval'] = 1
            opts['value'] = np.sqrt(self.reff)/200.0
        elif name == 'delr':
            opts['minval'] = -0.75
            opts['maxval'] =  0.75
        elif name == 'amp':
            opts['value'] = 1
        result = self.feffit_panel.update_params_for_expr(expr, **opts)
        if result:
            pargroup = self.feffit_panel.get_paramgroup()
            _eval = pargroup.__params__._asteval
            try:
                value = _eval.eval(expr, show_errors=False, raise_errors=False)
                if value is not None:
                    value = gformat(value, 11)
                    self.wids[name + '_val'].SetLabel(f'= {value}')
            except:
                result = False

        if result:
            bgcol, fgcol = 'white', 'black'
        else:
            bgcol, fgcol = '#AAAA4488', '#AA0000'
        self.wids[name].SetForegroundColour(fgcol)
        self.wids[name].SetBackgroundColour(bgcol)
        self.wids[name].SetOwnBackgroundColour(bgcol)
        if event is not None:
            event.Skip()


    def onPlotFeffDat(self, event=None):
        cmd = f"plot_feffdat(_feffpaths['{self.title}'], title='Feff data for path {self.title}')"
        self.feffit_panel.larch_eval(cmd)

    def onRemovePath(self, event=None):
        msg = f"Delete Path {self.title:s}?"
        dlg = wx.MessageDialog(self, msg, 'Warning', wx.YES | wx.NO )
        if (wx.ID_YES == dlg.ShowModal()):
            self.feffit_panel.paths_data.pop(self.title)
            self.feffit_panel.model_needs_build = True
            path_nb = self.feffit_panel.paths_nb
            for i in range(path_nb.GetPageCount()):
                if self.title == path_nb.GetPageText(i).strip():
                    path_nb.DeletePage(i)
            self.feffit_panel.skip_unused_params()
        dlg.Destroy()

    def update_values(self):
        pargroup = self.feffit_panel.get_paramgroup()
        _eval = pargroup.__params__._asteval
        for par in ('amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            expr = self.wids[par].GetValue().strip()
            if len(expr) > 0:
                try:
                    value = _eval.eval(expr, show_errors=False, raise_errors=False)
                    if value is not None:
                        value = gformat(value, 10)
                        self.wids[par + '_val'].SetLabel(f'= {value}')
                except:
                    self.feffit_panel.update_params_for_expr(expr)


class FeffitPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        self.resetting = False
        self.model_needs_rebuild = False
        self.params_need_update = False
        self.rmin_warned = False
        TaskPanel.__init__(self, parent, controller, panel='feffit', **kws)
        self.paths_data = {}
        self.config_saved = self.get_defaultconfig()
        self.dgroup = None

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        dgroup = self.controller.get_group()
        try:
            pargroup = self.get_paramgroup()
            self.params_panel.update()
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            if not hasattr(dgroup, 'chi'):
                self.parent.process_exafs(dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill feffit panel from group ")
        if dgroup is not self.dgroup:
            # setting up feffit for this group
            self.dgroup = dgroup
            try:
                has_fit_hist = len(self.dgroup.feffit_history) > 0
            except:
                has_fit_hist = getattr(self.larch.symtable, '_feffit_dataset', None) is not None

            if has_fit_hist:
                self.wids['show_results'].Enable()


            feffpaths = getattr(self.larch.symtable, '_feffpaths', None)
            if feffpaths is not None:
                self.reset_paths()

            self.params_panel.update()
            self.skip_unused_params()
            self.params_need_update = False

    def build_display(self):
        self.paths_nb = flatnotebook(self, {}, on_change=self.onPathsNBChanged,
                                     with_dropdown=True)

        self.params_panel = FeffitParamsPanel(parent=self.paths_nb,
                                              feffit_panel=self)
        self.paths_nb.AddPage(self.params_panel, ' Parameters ', True)
        pan = self.panel # = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = wids = {}

        fsopts = dict(digits=2, increment=0.1, with_pin=True)

        fit_kmin = self.add_floatspin('fit_kmin',  value=2, **fsopts)
        fit_kmax = self.add_floatspin('fit_kmax',  value=17, **fsopts)
        fit_dk   = self.add_floatspin('fit_dk',    value=4, **fsopts)
        fit_rmax = self.add_floatspin('fit_rmax',  value=5, **fsopts)
        fit_rmin = self.add_floatspin('fit_rmin',  value=1, action=self.onRmin, **fsopts)

        wids['fit_kwstring'] = Choice(pan, size=(120, -1),
                                     choices=list(Feffit_KWChoices.keys()))
        wids['fit_kwstring'].SetSelection(1)

        wids['fit_kwindow'] = Choice(pan, choices=list(FT_WINDOWS), size=(150, -1))

        wids['fit_space'] = Choice(pan, choices=list(Feffit_SpaceChoices.keys()),
                                   size=(150, -1))

        wids['plot_kw'] = Choice(pan, size=(80, -1),
                                  choices=['0', '1', '2', '3', '4'], default=2)

        wids['plot1_op'] = Choice(pan, choices=list(Plot1_Choices.keys()),
                                    action=self.onPlot, size=(150, -1))
        wids['plot1_op'].SetSelection(1)

        wids['plot1_voff'] =  FloatSpin(pan, value=0, digits=2, increment=0.25,
                                          size=(100, -1), action=self.onPlot)

        wids['plot1_paths'] = Check(pan, default=False, label='Plot Each Path',
                                   action=self.onPlot)
        wids['plot1_ftwins'] = Check(pan, default=False, label='Plot FT Windows',
                                       action=self.onPlot)


        wids['plot2_win'] = Choice(pan, choices=PlotWindowChoices,
                                   action=self.onPlot, size=(55, -1))
        wids['plot2_win'].SetStringSelection('2')
        wids['plot2_win'].SetToolTip('Plot Window for Second Plot')

        wids['plot2_op'] = Choice(pan, choices=list(Plot2_Choices.keys()),
                                    action=self.onPlot, size=(150, -1))


        wids['plot2_voff'] =  FloatSpin(pan, value=0, digits=2, increment=0.25,
                                          size=(100, -1), action=self.onPlot)

        wids['plot2_paths'] = Check(pan, default=False, label='Plot Each Path',
                                   action=self.onPlot)
        wids['plot2_ftwins'] = Check(pan, default=False, label='Plot FT Windows',
                                       action=self.onPlot)
        wids['plot_current']  = Button(pan,'Plot Current Model',
                                     action=self.onPlot,  size=(175, -1))

        wids['refine_bkg'] = Check(pan, default=False,
                                   label='Refine Background during Fit?')
        wids['do_fit']        = Button(pan, 'Fit Data to Model',
                                      action=self.onFitModel,  size=(175, -1))
        wids['show_results']  = Button(pan, 'Show Fit Results',
                                      action=self.onShowResults,  size=(175, -1))
        wids['show_results'].Disable()

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, 'Feff Fitting',
                           size=(150, -1), **self.titleopts), style=LEFT, dcol=1)
        pan.Add(SimpleText(pan, 'Use Feff->Browse Feff Calculations to Add Paths',
                           size=(425, -1)), style=LEFT, dcol=4)

        add_text('Fitting Space: ')
        pan.Add(wids['fit_space'])

        add_text('k weightings: ', newrow=False)
        pan.Add(wids['fit_kwstring'], dcol=3)

        add_text('k min: ')
        pan.Add(fit_kmin)
        add_text(' k max: ', newrow=False)
        pan.Add(fit_kmax)

        add_text('k Window: ')
        pan.Add(wids['fit_kwindow'])
        add_text('dk: ', newrow=False)
        pan.Add(fit_dk)

        add_text('R min: ')
        pan.Add(fit_rmin)
        add_text('R max: ', newrow=False)
        pan.Add(fit_rmax)
        add_text('  ', newrow=True)
        pan.Add(wids['refine_bkg'], dcol=3)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        pan.Add(wids['plot_current'], dcol=1, newrow=True)
        pan.Add(wids['plot1_op'], dcol=1)
        add_text('k-weight:' , newrow=False)
        pan.Add(wids['plot_kw'], dcol=1)

        pan.Add(wids['plot1_ftwins'], newrow=True)
        pan.Add(wids['plot1_paths'])
        add_text('Vertical Offset' , newrow=False)
        pan.Add(wids['plot1_voff'])


        add_text('Add Second Plot: ')

        pan.Add(wids['plot2_op'], dcol=1)
        add_text('Plot Window:' , newrow=False)
        pan.Add(wids['plot2_win'])

        pan.Add(wids['plot2_ftwins'],  newrow=True)
        pan.Add(wids['plot2_paths'])
        add_text('Vertical Offset' , newrow=False)
        pan.Add(wids['plot2_voff'])


        pan.Add(wids['do_fit'], dcol=1, newrow=True)
        pan.Add(wids['show_results'])
        pan.Add((5, 5), newrow=True)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((3, 3), 0, LEFT, 3)
        sizer.Add(SimpleText(self, ' Parameters and Paths'), 0, LEFT, 2)
        sizer.Add((3, 3), 0, LEFT, 3)
        sizer.Add(self.paths_nb,  1, LEFT|wx.GROW, 5)
        pack(self, sizer)

    def onRmin(self, event=None, **kws):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        rbkg = getattr(dgroup, 'rbkg', None)
        callargs = getattr(dgroup, 'callargs', None)
        if rbkg is None and callargs is not None:
            autobk_args = getattr(callargs, 'autobk', {'rbkg': 1.0})
            rbkg = autobk_args.get('rbkg', None)
        if rbkg is None: rbkg = 0.0
        rmin = self.wids['fit_rmin'].GetValue()
        if rmin > (rbkg-0.025):
            self.rmin_warned = False

        if rmin < (rbkg-0.025) and not self.rmin_warned:
            self.rmin_warned = True
            Popup(self,
                  f"""Rmin={rmin:.3f} Ang is below Rbkg={rbkg:.3f} Ang.

                  This should be done with caution.""",
                  "Warning: Rmin < Rbkg",
                  style=wx.ICON_WARNING|wx.OK_DEFAULT)


    def onPathsNBChanged(self, event=None):
        updater = getattr(self.paths_nb.GetCurrentPage(), 'update_values', None)
        if self.params_need_update and not self.resetting:
            self.params_panel.update()
            self.skip_unused_params()
            self.params_need_update = False
        if callable(updater) and not self.resetting:
            updater()

    def get_config(self, dgroup=None):
        """get and set processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            conf = None
        if not hasattr(dgroup, 'chi'):
            self.parent.process_exafs(dgroup)

        dconf = self.get_defaultconfig()

        if dgroup is None:
            return dconf
        if not hasattr(dgroup, 'config'):
            dgroup.config = Group()

        conf = getattr(dgroup.config, self.configname, dconf)
        for k, v in dconf.items():
            if k not in conf:
                conf[k] = v

        econf = getattr(dgroup.config, 'exafs', {})
        for key in ('fit_kmin', 'fit_kmax', 'fit_dk',
                    'fit_rmin', 'fit_rmax', 'fit_dr',
                    'fit_kwindow', 'fit_rwindow'):
            val = conf.get(key, -1)
            if val in (None, -1, 'Auto'):
                alt = key.replace('fit', 'fft')
                if alt in econf:
                    conf[key] = econf[alt]
        setattr(dgroup.config, self.configname, conf)
        self.config_saved = conf
        return conf

    def process(self, dgroup=None, **kws):
        # print("Feffit Panel Process ", dgroup, time.ctime())
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = self.get_config(dgroup=dgroup)
        conf.update(kws)

        if self.params_need_update:
            self.params_panel.update()
            self.skip_unused_params()
            self.params_need_update = False

        opts = self.read_form(dgroup=dgroup)
        if dgroup is not None:
            self.dgroup = dgroup
            for attr in ('fit_kmin', 'fit_kmax', 'fit_dk', 'fit_rmin',
                         'fit_rmax', 'fit_kwindow', 'fit_rwindow',
                         'fit_dr', 'fit_kwstring', 'fit_space',
                         'fit_plot', 'plot1_paths'):

                conf[attr] = opts.get(attr, None)

            if not hasattr(dgroup, 'config'):
                dgroup.config = Group()
            setattr(dgroup.config, self.configname, conf)

            orig_dgroup = self.controller.get_group()
            if orig_dgroup is not None:
                setattr(orig_dgroup.config, self.configname, conf)
            # print("dgroup " , conf)

            try:
                tchi = getattr(dgroup, 'chi', np.zeros(10))
                has_data = 1.e-12 <  (tchi**2).sum()
            except:
                has_data = False
            cmds = [COMMANDS['feffit_trans'].format(**conf)]
            _feffit_dataset = getattr(self.larch.symtable, '_feffit_dataset', None)
            if _feffit_dataset is None:
                cmds.append(COMMANDS['feffit_dataset_init'])
            if has_data:
                cmds.append(f"_feffit_dataset.set_datagroup({dgroup.groupname})")
                cmds.append(f"_feffit_dataset.refine_bkg = {opts['refine_bkg']}")
            self.larch.eval('\n'.join(cmds))
        return opts

    def fill_form(self, dat):
        dgroup = self.controller.get_group()
        conf = self.get_config(dat)

        for attr in ('fit_kmin', 'fit_kmax', 'fit_rmin', 'fit_rmax', 'fit_dk'):
            self.wids[attr].SetValue(conf[attr])

        self.wids['fit_kwindow'].SetStringSelection(conf['fit_kwindow'])

        fit_space = conf.get('fit_space', 'r')

        for key, val in Feffit_SpaceChoices.items():
            if fit_space in (key, val):
                self.wids['fit_space'].SetStringSelection(key)

        for key, val in Feffit_KWChoices.items():
            if conf['fit_kwstring'] == val:
                self.wids['fit_kwstring'].SetStringSelection(key)

    def read_form(self, dgroup=None):
        "read form, returning dict of values"

        if dgroup is None:
            try:
                fname = self.controller.filelist.GetStringSelection()
                gname = self.controller.file_groups[fname]
                dgroup = self.controller.get_group()
            except:
                gname  = fname = dgroup = None
        else:

            gname = dgroup.groupname
            fname = dgroup.filename

        form_opts = {'datagroup': dgroup, 'groupname': gname, 'filename': fname}
        wids = self.wids

        for attr in ('fit_kmin', 'fit_kmax', 'fit_rmin', 'fit_rmax', 'fit_dk'):
            form_opts[attr] = wids[attr].GetValue()
        form_opts['fit_kwstring'] = Feffit_KWChoices[wids['fit_kwstring'].GetStringSelection()]
        if len(form_opts['fit_kwstring']) == 1:
            d = form_opts['fit_kwstring']
        else:
            d = form_opts['fit_kwstring'].replace('[', '').strip(',').split()[0]
        try:
            form_opts['fit_kweight'] = int(d)
        except:
            form_opts['fit_kweight'] = 2


        form_opts['refine_bkg'] = wids['refine_bkg'].IsChecked()
        fitspace_string = wids['fit_space'].GetStringSelection()
        form_opts['fit_space'] = Feffit_SpaceChoices[fitspace_string]

        form_opts['fit_kwindow'] = wids['fit_kwindow'].GetStringSelection()
        form_opts['plot_kw'] = int(wids['plot_kw'].GetStringSelection())
        form_opts['plot1_ftwins'] = wids['plot1_ftwins'].IsChecked()
        form_opts['plot1_paths'] = wids['plot1_paths'].IsChecked()
        form_opts['plot1_op'] = Plot1_Choices[wids['plot1_op'].GetStringSelection()]
        form_opts['plot1_voff'] = wids['plot1_voff'].GetValue()

        form_opts['plot2_op'] = Plot2_Choices[wids['plot2_op'].GetStringSelection()]
        form_opts['plot2_ftwins'] = wids['plot2_ftwins'].IsChecked()
        form_opts['plot2_paths'] = wids['plot2_paths'].IsChecked()
        form_opts['plot2_voff'] = wids['plot2_voff'].GetValue()
        form_opts['plot2_win'] = int(wids['plot2_win'].GetStringSelection())
        return form_opts


    def fill_model_params(self, prefix, params):
        comp = self.fit_components[prefix]
        parwids = comp.parwids
        for pname, par in params.items():
            pname = prefix + pname
            if pname in parwids:
                wids = parwids[pname]
                if wids.minval is not None:
                    wids.minval.SetValue(par.min)
                if wids.maxval is not None:
                    wids.maxval.SetValue(par.max)
                wids.value.SetValue(par.value)
                varstr = 'vary' if par.vary else 'fix'
                if par.expr is not None:
                    varstr = 'constrain'
                if wids.vary is not None:
                   wids.vary.SetStringSelection(varstr)

    def onPlot(self, evt=None, dataset_name='_feffit_dataset',
               pargroup_name='_feffit_params', title=None, build_fitmodel=True,
               topwin=None, **kws):

        dataset = getattr(self.larch.symtable, dataset_name, None)
        if dataset is None:
            dgroup = self.controller.get_group()
        else:
            if dataset.has_data:
                dgroup = dataset.data
            else:
                dgroup = self.controller.get_group()
                #   print("no data?  dgroup  ", dataset.data, dgroup)
                if dgroup is not None:
                    self.larch.eval(f"{dataset_name}.set_datagroup({dgroup.groupname})")
                    dataset = getattr(self.larch.symtable, dataset_name, None)
                    dgroup = dataset.data
        # print("now data now dgroup  ", dataset, getattr(dataset, 'data', None), dgroup)

        opts = self.process(dgroup)
        opts.update(**kws)

        if build_fitmodel:
            self.build_fitmodel(dgroup, opts=opts)

        model_name = dataset_name + '.model'
        paths_name = dataset_name + '.paths'
        paths = self.larch.eval(paths_name)

        data_name  = dataset_name + '.data'
        refine_bkg = getattr(dataset, 'refine_bkg',
                             opts.get('refine_bkg', False))

        if refine_bkg and hasattr(dataset, 'data_rebkg'):
            data_name =  dataset_name + '.data_rebkg'

        exafs_conf = self.parent.get_nbpage('exafs')[1].read_form()
        opts['plot_rmax'] = exafs_conf['plot_rmax']
        groupname = getattr(dgroup, 'groupname', 'unknown')
        cmds = ["#### plot ",
                f"#  build arrays for plotting: refine bkg? {refine_bkg}, {groupname} / {dataset_name}"]

        kweight = opts['plot_kw']

        ftargs = dict(kmin=opts['fit_kmin'], kmax=opts['fit_kmax'], dk=opts['fit_dk'],
                      kwindow=opts['fit_kwindow'], kweight=opts['plot_kw'],
                      rmin=opts['fit_rmin'], rmax=opts['fit_rmax'],
                      dr=opts.get('fit_dr', 0.1), rwindow='hanning')

        if model_name is not None:
            cmds.append(COMMANDS['xft'].format(groupname=model_name, **ftargs))
        if data_name  is not None:
            cmds.append(COMMANDS['xft'].format(groupname=data_name, **ftargs))

        if opts['plot1_paths'] or opts['plot2_paths']:
            cmds.append(COMMANDS['path2chi'].format(paths_name=paths_name,
                                                    pargroup_name=pargroup_name,
                                                    **ftargs))

        self.larch_eval('\n'.join(cmds))
        self.plot_feffit_result(dataset_name, topwin=topwin, ftargs=ftargs, **opts)

    def plot_feffit_result(self, dataset_name, topwin=None, ftargs=None, **kws):

        if isValidName(dataset_name):
            dataset = getattr(self.larch.symtable, dataset_name, None)
        else:
            dataset = self.larch.eval(dataset_name)

        if dataset is None:
            dgroup = self.controller.get_group()
        else:
            dgroup = dataset.data
        data_name  = dataset_name + '.data'
        model_name = dataset_name + '.model'
        has_data = getattr(dataset, 'has_data', True)

        #print("plot_feffit_result/ dgroup, dataset: ", dataset_name, dgroup, dataset, has_data)

        opts = self.process(dgroup)
        opts.update(**kws)
        title = fname = opts['filename']
        if title is None:
            title = 'Feff Sum'
        if "'" in title:
            title = title.replace("'", "\\'")

        needs_qspace = False
        plot1 = opts['plot1_op']
        plot2 = opts['plot2_op']
        plot_rmax = opts['plot_rmax']
        kweight = opts['plot_kw']
        if ftargs is None:
            ftargs = dict(kmin=opts['fit_kmin'], kmax=opts['fit_kmax'], dk=opts['fit_dk'],
                         kwindow=opts['fit_kwindow'], kweight=opts['plot_kw'],
                         rmin=opts['fit_rmin'], rmax=opts['fit_rmax'],
                         dr=opts.get('fit_dr', 0.1), rwindow='hanning')

        cmds = []
        for i, plot in enumerate((plot1, plot2)):
            if plot in Plot2_Choices:
                plot = Plot2_Choices[plot]
            plotwin = 1
            if i == 1:
                if plot in ('noplot', '<no plot>'):
                    continue
                else:
                    plotwin = int(opts.get('plot2_win', '2'))
            pcmd = 'plot_chir'
            pextra = f', win={plotwin:d}'
            if plot == 'chi':
                pcmd = 'plot_chik'
                pextra += f', kweight={kweight:d}'
            elif plot == 'chir_mag':
                pcmd = 'plot_chir'
                pextra +=  f', rmax={plot_rmax}'
            elif plot == 'chir_re':
                pextra += f', show_mag=False, show_real=True, rmax={plot_rmax}'
            elif plot == 'chir_mag+chir_re':
                pextra += f', show_mag=True, show_real=True, rmax={plot_rmax}'
            elif plot == 'chiq':
                pcmd = 'plot_chiq'
                pextra += f', show_chik=False'
                needs_qspace = True
            else:
                # print(" do not know how to plot ", plot)
                continue
            with_win = opts[f'plot{i+1}_ftwins']
            newplot = f', show_window={with_win}, new=True'
            overplot = f', show_window=False, new=False'
            extra = newplot
            if dgroup is not None:
                if has_data:
                    cmds.append(f"{pcmd}({data_name:s}, label='data'{pextra}, title='{title}'{extra})")
                    extra = overplot
                if dataset.model is not None:
                    cmds.append(f"{pcmd}({model_name:s}, label='model'{pextra}{extra})")
                    extra = overplot
            elif dataset.model is not None:
                cmds.append(f"{pcmd}({model_name:s}, label='Path sum'{pextra}, title='sum of paths'{extra})")
                extra = overplot
            if opts[f'plot{i+1}_paths']:
                paths_name = dataset_name + '.paths'
                try:
                    paths = self._plain_larch_eval(paths_name)
                except:
                    paths = {}
                voff = opts[f'plot{i+1}_voff']
                for i, label in enumerate(paths.keys()):
                    if paths[label].use:
                        objname = f"{paths_name}['{label:s}']"
                        if needs_qspace:
                            xpath = paths.get(label)
                            if not hasattr(xpath, 'chiq_re'):
                                cmds.append(COMMANDS['xft'].format(groupname=objname, **ftargs))

                        cmds.append(f"{pcmd}({objname}, label='{label:s}'{pextra}, offset={(i+1)*voff}{overplot})")

        self.larch_eval('\n'.join(cmds))
        if topwin is not None:
            self.controller.set_focus(topwin=topwin)


    def reset_paths(self, event=None):
        "reset paths from _feffpaths"
        self.resetting = True
        def get_pagenames():
            allpages = []
            for i in range(self.paths_nb.GetPageCount()):
                allpages.append(self.paths_nb.GetPage(i).__class__.__name__)
            return allpages

        allpages = get_pagenames()
        t0 = time.time()

        while 'FeffPathPanel' in allpages:
            for i in range(self.paths_nb.GetPageCount()):
                nbpage = self.paths_nb.GetPage(i)
                if isinstance(nbpage, FeffPathPanel):
                    key = self.paths_nb.GetPageText(i)
                    self.paths_nb.DeletePage(i)
            allpages = get_pagenames()

        time.sleep(0.02)
        feffpaths = deepcopy(getattr(self.larch.symtable, '_feffpaths', {}))
        self.paths_data = {}
        for path in feffpaths.values():
            self.add_path(path.filename, feffpath=path, resize=False)

        self.get_pathpage('parameters').Rebuild()
        self.resetting = False
        self.params_need_update = True


    def add_path(self, filename, pathinfo=None, feffpath=None, resize=True):
        """ add new path to cache  """

        if pathinfo is None and feffpath is None:
            raise ValueError("add_path needs a Feff Path or Path information")
        self.params_need_update = True
        pfile = Path(filename).absolute()
        fname = pfile.name
        feffrun = pfile.parent.name

        feffcache = getattr(self.larch.symtable, '_feffcache', None)
        if feffcache is None:
            self.larch_eval(COMMANDS['paths_init'])
            feffcache = getattr(self.larch.symtable, '_feffcache', None)
        if feffcache is None:
            raise ValueError("cannot get feff cache ")

        geomstre = None
        if pathinfo is not None:
            absorber = pathinfo.absorber
            shell = pathinfo.shell
            reff  = float(pathinfo.reff)
            nleg  = int(pathinfo.nleg)
            degen = float(pathinfo.degen)
            if hasattr(pathinfo, 'atoms'):
                geom = pathinfo.atoms
            geomstr = pathinfo.geom      # '[Fe] > O > [Fe]'
            par_amp = par_e0 = par_delr = par_sigma2 = par_third = par_ei = ''

        if feffpath is not None:
            absorber = feffpath.absorber
            shell = feffpath.shell
            reff  = feffpath.reff
            nleg  = feffpath.nleg
            degen = float(feffpath.degen)
            geomstr = []
            for gdat in feffpath.geom: #  ('Fe', 26, 0, 55.845, x, y, z)
                w = gdat[0]
                if gdat[2] == 0: # absorber
                    w = '[%s]' % w
                geomstr.append(w)
            geomstr.append(geomstr[0])
            geomstr = ' > '.join(geomstr)
            par_amp = feffpath.s02
            par_e0 = feffpath.e0
            par_delr = feffpath.deltar
            par_sigma2 = feffpath.sigma2
            par_third = feffpath.third
            par_ei = feffpath.ei

        try:
            atoms = [s.strip() for s in geomstr.split('>')]
            atoms.pop()
        except:
            title = "Cannot interpret Feff Path data"
            message = [f"Cannot interpret Feff path {filename}"]
            ExceptionPopup(self, title, message)

        title = '_'.join(atoms) + "%d" % (round(100*reff))
        for c in ',.[](){}<>+=-?/\\&%$#@!|:;"\'':
            title = title.replace(c, '')
        if title in self.paths_data:
            btitle = title
            i = -1
            while title in self.paths_data:
                i += 1
                title = btitle + '_%s' % string.ascii_lowercase[i]

        user_label = fix_varname(title)
        self.paths_data[title] = filename

        ptitle = title
        if ptitle.startswith(absorber):
            ptitle = ptitle[len(absorber):]
        if ptitle.startswith('_'):
            ptitle = ptitle[1:]

        # set default Path parameters if not supplied already
        if len(par_amp) < 1:
            par_amp = f'{degen:.1f} * s02'
        if len(par_e0) < 1:
            par_e0 = 'e0'
        if len(par_delr) < 1:
            par_delr = f'delr_{ptitle}'
        if len(par_sigma2) < 1:
            par_sigma2 = f'sigma2_{ptitle}'

        pathpanel = FeffPathPanel(self.paths_nb, self, filename, title,
                                  user_label, geomstr, absorber, shell,
                                  reff, nleg, degen, par_amp, par_e0,
                                  par_delr, par_sigma2, par_third, par_ei)

        self.paths_nb.AddPage(pathpanel, f' {title:s} ', True)

        for pname  in ('amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            pathpanel.onExpression(name=pname)

        pathpanel.enable_editing()

        pdat = {'title': title, 'fullpath': filename,
                'feffrun': feffrun, 'use':True}
        pdat.update(pathpanel.get_expressions())

        if title not in feffcache['paths']:
            if Path(filename).exists():
                self.larch_eval(COMMANDS['cache_path'].format(**pdat))
            else:
                print(f"cannot file Feff data file '{filename}'")

        self.larch_eval(COMMANDS['use_path'].format(**pdat))
        if resize:
            sx,sy = self.GetSize()
            self.SetSize((sx, sy+1))
            self.SetSize((sx, sy))
            ipage, pagepanel = self.parent.get_nbpage('feffit')
            self.parent.nb.SetSelection(ipage)
            self.parent.Raise()

    def get_pathkeys(self):
        _feffpaths = getattr(self.larch.symtable, '_feffpaths', {})
        return [p.hashkey for p in _feffpaths.values()]

    def get_paramgroup(self):
        pgroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pgroup is None:
            self.larch_eval(COMMANDS['feffit_params_init'])
            pgroup = getattr(self.larch.symtable, '_feffit_params', None)
        if not hasattr(self.larch.symtable, '_feffpaths'):
            self.larch_eval(COMMANDS['paths_init'])
        return pgroup

    def update_params_for_expr(self, expr=None, value=1.e-3,
                               minval=None, maxval=None):
        if expr is None:
            return
        pargroup = self.get_paramgroup()
        symtable = pargroup.__params__._asteval.symtable
        extras= ''
        if minval is not None:
            extras = f', min={minval}'
        if maxval is not None:
            extras = f'{extras}, max={maxval}'

        try:
            for node in ast.walk(ast.parse(expr)):
                if isinstance(node, ast.Name):
                    sym = node.id
                    if sym not in symtable and sym not in FEFFDAT_VALUES:
                        s = f"_feffit_params.{sym:s} = param({value:.4f}, name='{sym:s}', vary=True{extras:s})"
                        self.larch_eval(s)
            result = True
        except:
            result = False

        self.params_need_update = True
        return result

    def onLoadFitResult(self, event=None):
        rfile = FileOpen(self, "Load Saved Feffit Model",
                            wildcard=ModelWcards)
        if rfile is None:
            return

    def get_xranges(self, x):
        if self.dgroup is None:
            self.dgroup = self.controller.get_group()
        self.process(self.dgroup)
        opts = self.read_form(self.dgroup)
        dgroup = self.controller.get_group()
        en_eps = min(np.diff(dgroup.energy)) / 5.

        i1 = index_of(x, opts['emin'] + en_eps)
        i2 = index_of(x, opts['emax'] + en_eps) + 1
        return i1, i2

    def get_pathpage(self, name):
        "get nb page for a Path by name"
        name = name.lower().strip()
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip().lower()
            if name in text:
                return self.paths_nb.GetPage(i)

    def build_fitmodel(self, groupname=None, opts=None):
        """ use fit components to build model"""
        paths = []
        cmds = ["### set up feffit "]
        pargroup = self.get_paramgroup()
        if self.dgroup is None:
            self.dgroup = self.controller.get_group()

        # self.params_panel.update()
        cmds.extend(self.params_panel.generate_params())

        if opts is None:
            opts = self.process(self.dgroup)

        cmds.append(COMMANDS['feffit_trans'].format(**opts))

        path_pages = {}
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)

        _feffpaths = getattr(self.larch.symtable, '_feffpaths', None)
        if _feffpaths is None:
            cmds.append(COMMANDS['paths_init'])
        else:
            cmds.append(COMMANDS['paths_reset'])

        _feffit_dataset = getattr(self.larch.symtable, '_feffit_dataset', None)
        if _feffit_dataset is None:
            cmds.append(COMMANDS['feffit_dataset_init'])

        paths_list = []
        opts['paths'] = []
        for title, pathdata in self.paths_data.items():
            if title not in path_pages:
                continue
            pdat = {'title': title, 'fullpath': pathdata[0],
                    'feffrun': pathdata[1], 'use':True}
            pdat.update(path_pages[title].get_expressions())

            #if pdat['use']:
            cmds.append(COMMANDS['use_path'].format(**pdat))
            paths_list.append(f"_feffpaths['{title:s}']")
            opts['paths'].append(pdat)

        paths_string = '[%s]' % (', '.join(paths_list))

        gname = opts.get('groupname', None)
        if gname is None:
            cmds.append(COMMANDS['ff2chi_nodata'].format(paths=paths_string,
                                                        trans='_feffit_trans')
                                                        )
        else:
            cmds.append(COMMANDS['ff2chi'].format(paths=paths_string,
                                                  trans='_feffit_trans',
                                                  groupname=gname,
                                                  refine_bkg=opts['refine_bkg'])
                        )
        cmds.append('# end of build model')
        self.larch_eval("\n".join(cmds))
        return opts


    def get_used_params(self):
        used_syms = []
        path_pages = {}

        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)
        for title in self.paths_data:
            if title not in path_pages:
                continue
            exprs = path_pages[title].get_expressions()
            if exprs['use']:
                for ename, expr in exprs.items():
                    if ename in ('label', 'use'):
                        continue
                    for node in ast.walk(ast.parse(expr)):
                        if isinstance(node, ast.Name):
                            sym = node.id
                            if sym not in used_syms:
                                used_syms.append(sym)
        return used_syms


    def skip_unused_params(self):
        # find unused symbols, set to "skip"
        curr_syms = self.get_used_params()
        pargroup = self.get_paramgroup()
        parpanel = self.params_panel
        for pname, par in group2params(pargroup).items():
            if pname in parpanel.parwids:
                ppar = parpanel.parwids[pname]
                _skip = False
                _str = ppar.vary.GetStringSelection()
                if pname not in curr_syms:
                    _skip = True
                    _str = 'skip'
                elif (pname in curr_syms and getattr(ppar, 'skip', False)):
                    _str = 'vary'
                ppar.skip = ppar.param.skip = par.skip = _skip
                ppar.vary.SetStringSelection(_str)
                ppar.onVaryChoice()
            parpanel.update()

    def onFitModel(self, event=None, dgroup=None):
        session_history = self.get_session_history()
        nstart = len(session_history)

        script = [COMMANDS['feffit_top'].format(ctime=time.ctime())]

        if dgroup is None:
           dgroup = self.controller.get_group()
        opts = self.build_fitmodel(dgroup)

        # dgroup = opts['datagroup']
        fopts = dict(groupname=opts['groupname'],
                     refine_bkg=bool(opts['refine_bkg']),
                     trans='_feffit_trans',
                     paths='_feffpaths',
                     params='_feffit_params')

        groupname = opts['groupname']
        filename = opts['filename']
        if dgroup is None:
            dgroup = opts['datagroup']

        script.append("###\n### DATA \n###\n")
        script.append(COMMANDS['data_source'].format(groupname=groupname, filename=filename))
        seen_cmds = []
        cmdhist = []
        sesshist = get_commands(session_history)
        for cmd in reversed(sesshist):
            if groupname in cmd or filename in cmd or 'athena' in cmd or 'session' in cmd:
                scmd = cmd.strip()
                if (scmd.startswith('#') or scmd.startswith('plot_')
                   or 'feffit_dataset(' in scmd or 'feffit_transform(' in scmd):
                    continue
                fcn_name, args = scmd.split('(', 1) if '(' in scmd else ('', scmd)
                if fcn_name in ('autobk', 'pre_edge', 'xftf', 'xftr'):
                    if fcn_name in seen_cmds:
                        continue
                    else:
                        seen_cmds.append(fcn_name)
                cmdhist.append(f"# {cmd}")

        script.extend(list(reversed(cmdhist)))

        script.append("### end of data reading and preparation\n###\n###")
        script.append("## read Feff Paths into '_feffpaths'.  You will need to either")
        script.append("##    read feff.dat from disk files with `feffpath()` or use Paths")
        script.append("##     cached from a session file into `feffcache`")
        script.append("#_feffcache = {'runs': {}, 'paths':{}}")
        script.append("#_feffpaths = {}")
        for path in opts['paths']:
            lab, fname, run = path['title'], path['fullpath'], path['feffrun']
            amp, e0, delr, sigma2, third, ei = path['amp'], path['e0'], path['delr'], path['sigma2'], path['third'], path['ei']
            script.append(f"""## Path '{lab}' : ############
#_feffcache['paths']['{lab}'] = feffpath('{fname}', label='{lab}', feffrun='{run}', degen=1)
#_feffpaths['{lab}'] = use_feffpath(_feffcache['paths'], '{lab}',
#                               s02='{amp:s}', e0='{e0:s}', deltar='{delr:s}',
#                               sigma2='{sigma2:s}', third='{third:s}', ei='{ei:s}')""")

        script.append("###\n###\n###")
        self.larch_eval(COMMANDS['do_feffit'].format(**fopts))

        self.wids['show_results'].Enable()
        self.onPlot(dataset_name='_feffit_dataset',
                    pargroup_name='_feffit_result.paramgroup',
                    build_fitmodel=False)


        script.extend(self.get_session_history()[nstart:])
        script.extend(["print(feffit_report(_feffit_result))",
                       "#end of autosaved feffit script" , ""])

        if not hasattr(dgroup, 'feffit_history'):
            dgroup.feffit_history = []


        label = now  = time.strftime("%b-%d %H:%M")
        if len(dgroup.feffit_history) > 0:
            dgroup.feffit_history[0].commands = script
            dgroup.feffit_history[0].timestamp = time.strftime("%Y-%b-%d %H:%M")
            dgroup.feffit_history[0].label = label

        fitlabels = [fhist.label for fhist in dgroup.feffit_history[1:]]
        if label in fitlabels:
            count = 1
            while label in fitlabels:
                label = f'{now:s}_{printable[count]:s}'
                count +=1
            dgroup.feffit_history[0].label = label

        sname = self.autosave_script('\n'.join(script))
        self.write_message("wrote feffit script to '%s'" % sname)

        self.show_subframe('feffit_result', FeffitResultFrame,
                           datagroup=opts['datagroup'], feffit_panel=self)
        self.subframes['feffit_result'].add_results(dgroup, form=opts)

    def onShowResults(self, event=None):
        self.show_subframe('feffit_result', FeffitResultFrame,
                           feffit_panel=self)

    def update_start_values(self, params):
        """fill parameters with best fit values"""
        self.params_panel.set_init_values(params)
        for i in range(self.paths_nb.GetPageCount()):
            if 'parameters' in self.paths_nb.GetPageText(i).strip().lower():
                self.paths_nb.SetSelection(i)

    def autosave_script(self, text, fname='feffit_script.lar'):
        """autosave model result to user larch folder"""
        confdir = self.controller.larix_folder
        if fname is None:
            fname = 'feffit_script.lar'
        fullpath = Path(confdir, fname)
        fullname = fullpath.as_posix()
        if fullpath.exists():
            shutil.copy(fullname, Path(confdir, 'feffit_script_BAK.lar').as_posix())
        with open(fullname, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write(text)
        return fullname


###############

class FeffitResultFrame(wx.Frame):
    def __init__(self, parent=None, feffit_panel=None, datagroup=None, **kws):
        wx.Frame.__init__(self, None, -1, title='Feffit Results',
                          style=FRAMESTYLE, size=(1000, 700), **kws)

        self.outforms = {'chik': 'chi(k), no k-weight',
                         'chikw': 'chi(k), k-weighted',
                         'chir_mag': '|chi(R)|',
                         'chir_re': 'Real[chi(R)]',
                         'chiq': 'Filtered \u03c7(k)'
                         }

        self.feffit_panel = feffit_panel
        self.datagroup = datagroup
        self.feffit_history = getattr(datagroup, 'fit_history', [])
        self.parent = parent
        self.report_frame = None
        self.datasets = {}
        self.form = {}
        self.larch_eval = feffit_panel.larch_eval
        self.nfit = 0
        self.createMenus()
        self.build()

        if datagroup is None:
            symtab = self.feffit_panel.larch.symtable
            xasgroups = getattr(symtab, '_xasgroups', None)
            if xasgroups is not None:
                for dname, dgroup in xasgroups.items():
                    dgroup = getattr(symtab, dgroup, None)
                    hist = getattr(dgroup, 'feffit_history', None)
                    if hist is not None:
                        self.add_results(dgroup, show=True)


    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        m = {}
        for key, desc in self.outforms.items():
            MenuItem(self, fmenu,
                     f"Save Fit: {desc}",
                     f"Save data, model, path arrays as {desc}",
                     partial(self.onSaveFit, form=key))

        fmenu.AppendSeparator()
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def build(self):
        sizer = wx.GridBagSizer(2, 2)
        sizer.SetVGap(2)
        sizer.SetHGap(2)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(200)

        self.filelist = EditableListBox(splitter, self.ShowDataSet,
                                        size=(250, -1))
        set_color(self.filelist, 'list_fg', bg='list_bg')

        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.NORMAL)

        panel = scrolled.ScrolledPanel(splitter)

        panel.SetMinSize((725, 575))
        panel.SetSize((850, 575))

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Feffit Results', font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+2),
                                        minsize=(350, -1),
                                        colour=COLORS['title'], style=LEFT)

        wids['plot1_op'] = Choice(panel, choices=list(Plot1_Choices.keys()),
                                    action=self.onPlot, size=(125, -1))
        wids['plot1_op'].SetSelection(1)
        wids['plot2_op'] = Choice(panel, choices=list(Plot2_Choices.keys()),
                                    action=self.onPlot, size=(125, -1))

        wids['plot2_win'] = Choice(panel, choices=PlotWindowChoices,
                                  action=self.onPlot, size=(60, -1))
        wids['plot2_win'].SetStringSelection('2')

        wids['plot_kw'] = Choice(panel, size=(80, -1),
                                  choices=['0', '1', '2', '3', '4'], default=2)

        wids['plot1_paths'] = Check(panel, default=False, label='Plot Each Path',
                                    action=self.onPlot)
        wids['plot1_ftwins'] = Check(panel, default=False, label='Plot FT Windows',
                                     action=self.onPlot)

        wids['plot1_voff'] = FloatSpin(panel, value=0, digits=2, increment=0.25,
                                       action=self.onPlot, size=(100, -1))
        wids['plot2_paths'] = Check(panel, default=False, label='Plot Each Path',
                                    action=self.onPlot)
        wids['plot2_ftwins'] = Check(panel, default=False, label='Plot FT Windows',
                                     action=self.onPlot)

        wids['plot2_voff'] = FloatSpin(panel, value=0, digits=2, increment=0.25,
                                       action=self.onPlot, size=(100, -1))

        wids['plot_current']  = Button(panel,'Plot Current Model',
                                     action=self.onPlot,  size=(175, -1))

        wids['show_pathpars']  = Button(panel,'Show Path Parameters',
                                        action=self.onShowPathParams, size=(175, -1))
        wids['show_script']  = Button(panel,'Show Fit Script',
                                        action=self.onShowScript, size=(150, -1))

        lpanel = wx.Panel(panel)
        wids['fit_label'] = wx.TextCtrl(lpanel, -1, ' ', size=(175, -1))
        wids['set_label'] = Button(lpanel, 'Update Label', size=(150, -1),
                                   action=self.onUpdateLabel)
        wids['del_fit'] = Button(lpanel, 'Remove from Fit History', size=(200, -1),
                                 action=self.onRemoveFromHistory)

        lsizer = wx.BoxSizer(wx.HORIZONTAL)
        lsizer.Add(wids['fit_label'], 0, 2)
        lsizer.Add(wids['set_label'], 0, 2)
        lsizer.Add(wids['del_fit'],   0, 2)
        pack(lpanel, lsizer)

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['data_title'], (irow, 1), (1, 3), LEFT)

        irow += 1
        sizer.Add(wids['plot_current'],     (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plot1_op'],         (irow, 1), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, 'k-weight'),  (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot_kw'],               (irow, 3), (1, 1), LEFT)
        irow += 1
        sizer.Add(wids['plot1_ftwins'],     (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plot1_paths'],      (irow, 1), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, 'Vertical  Offest:'),  (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot1_voff'],         (irow, 3), (1, 1), LEFT)

        irow += 1
        sizer.Add(SimpleText(panel, 'Add Second Plot:', style=LEFT), (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plot2_op'],                                (irow, 1), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, 'Plot Window:', style=LEFT), (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot2_win'],                              (irow, 3), (1, 1), LEFT)
        irow += 1
        sizer.Add(wids['plot2_ftwins'],     (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plot2_paths'],      (irow, 1), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, 'Vertical  Offest:'),  (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot2_voff'],         (irow, 3), (1, 1), LEFT)

        irow += 1
        sizer.Add(wids['show_pathpars'], (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['show_script'],   (irow, 1), (1, 1), LEFT)
        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(SimpleText(panel, 'Fit Label:', style=LEFT), (irow, 0), (1, 1), LEFT)
        sizer.Add(lpanel, (irow, 1), (1, 4), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)
        subtitle = SimpleText(panel, ' (most recent fit is at the top)',
                              font=Font(FONTSIZE+1),  style=LEFT)

        sizer.Add(title, (irow, 0), (1, 1), LEFT)
        sizer.Add(subtitle, (irow, 1), (1, 3), LEFT)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.SetFont(self.font_fixedwidth)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)

        xw = (40, 135, 80, 80, 92, 92, 122, 100)
        if platform=='darwin':
            xw = (30, 125, 60, 60, 75, 75, 90, 90)

        sview.AppendTextColumn(' # ', width=xw[0])
        sview.AppendTextColumn('Label', width=xw[1])
        sview.AppendTextColumn('Npaths', width=xw[2])
        sview.AppendTextColumn('Nvary', width=xw[3])
        sview.AppendTextColumn('Nidp',  width=xw[4])
        sview.AppendTextColumn('\u03c7\u00B2', width=xw[5])
        sview.AppendTextColumn('reduced \u03c7\u00B2', width=xw[6])
        sview.AppendTextColumn('R Factor', width=xw[7])

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            this.Sortable = True
            this.Alignment = wx.ALIGN_RIGHT if col > 1 else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        sview.SetMinSize((750, 150))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)
        sizer.Add(title, (irow, 0), (1, 1), LEFT)

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(225, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LEFT)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        pview.SetFont(self.font_fixedwidth)
        self.wids['paramsdata'] = []
        xw = (180, 140, 150, 250)
        if platform=='darwin':
            xw = (180, 110, 110, 250)

        pview.AppendTextColumn('Parameter',  width=xw[0])
        pview.AppendTextColumn('Best Value', width=xw[1])
        pview.AppendTextColumn('1-\u03c3 Uncertainty', width=xw[2])
        pview.AppendTextColumn('Info ',     width=xw[3])

        for col in range(4):
            this = pview.Columns[col]
            this.Sortable = False
            this.Alignment = wx.ALIGN_RIGHT if col in (1, 2) else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        pview.SetMinSize((750, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)

        ppanel = wx.Panel(panel)
        ppanel.SetMinSize((450, 20))
        self.wids['all_correl'] = Button(ppanel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatSpin(ppanel, value=MIN_CORREL,
                                            min_val=0, size=(100, -1),
                                            digits=3, increment=0.1)

        psizer = wx.BoxSizer(wx.HORIZONTAL)
        psizer.Add(SimpleText(ppanel, 'minimum correlation: '), 0, 2)
        psizer.Add(self.wids['min_correl'], 0, 2)
        psizer.Add(self.wids['all_correl'], 0, 2)
        pack(ppanel, psizer)

        sizer.Add(title,  (irow, 0), (1, 1), LEFT)
        sizer.Add(ppanel, (irow, 1), (1, 4), LEFT)

        cview = self.wids['correl'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        cview.SetFont(self.font_fixedwidth)

        cview.AppendTextColumn('Parameter 1',    width=150)
        cview.AppendTextColumn('Parameter 2',    width=150)
        cview.AppendTextColumn('Correlation',    width=150)

        for col in (0, 1, 2):
            this = cview.Columns[col]
            this.Sortable = False
            align = wx.ALIGN_LEFT
            if col == 2:
                align = wx.ALIGN_RIGHT
            this.Alignment = this.Renderer.Alignment = align
        cview.SetMinSize((550, 150))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LEFT)

        pack(panel, sizer)
        panel.SetupScrolling()

        splitter.SplitVertically(self.filelist, panel, 1)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def show_report(self, text, title='Text', default_filename='out.txt',
                    wildcard=None):
        if wildcard is None:
            wildcard='Text Files (*.txt)|*.txt'
        try:
            self.report_frame.set_text(text)
            self.report_frame.SetTitle(title)
            self.report_frame.default_filename = default_filename
            self.report_frame.wildcard = wildcard
        except:
            self.report_frame = ReportFrame(parent=self.parent,
                                            text=text, title=title,
                                            default_filename=default_filename,
                                            wildcard=wildcard)

    def onShowPathParams(self, event=None):
        result = self.get_fitresult()
        if result is None:
            return
        text = f'# Feffit Report for {self.datagroup.filename} fit "{result.label}"\n'
        text = text + feffit_report(result)
        title = f'Report for {self.datagroup.filename} fit "{result.label}"'
        fname = fix_filename(f'{self.datagroup.filename}_{result.label}.txt')
        self.show_report(text, title=title, default_filename=fname)

    def onShowScript(self, event=None):
        result = self.get_fitresult()
        if result is None:
            return
        text = [f'# Feffit Script for {self.datagroup.filename} fit "{result.label}"']
        text.extend(result.commands)
        text = '\n'.join(text)
        title = f'Script for {self.datagroup.filename} fit "{result.label}"'
        fname = fix_filename(f'{self.datagroup.filename}_{result.label}.lar')
        self.show_report(text, title=title, default_filename=fname,
                         wildcard='Larch/Python Script (*.lar)|*.lar')

    def onUpdateLabel(self, event=None):
        result = self.get_fitresult()
        if result is None:
            return
        item = self.wids['stats'].GetSelectedRow()
        result.label = self.wids['fit_label'].GetValue()
        self.show_results()

    def onRemoveFromHistory(self, event=None):
        result = self.get_fitresult()
        if result is None:
            return
        if wx.ID_YES != Popup(self,
                              f"Remove fit '{result.label}' from history?\nThis cannot be undone.",
                              "Remove fit?", style=wx.YES_NO):
                return
        self.datagroup.feffit_history.pop(self.nfit)
        self.nfit = 0
        self.show_results()

    def onPlot(self, event=None):
        result = self.get_fitresult()
        if result is None:
            return
        dset   = result.datasets[0]
        dgroup = dset.data
        if not hasattr(dset.data, 'rwin'):
            dset._residual(result.params)
            dset.save_outputs()
        trans  = dset.transform
        dset.prepare_fit(result.params)
        dset._residual(result.params)

        opts = self.feffit_panel.read_form(dgroup=dgroup)
        opts = {'build_fitmodel': False}

        for key, meth in (('plot1_ftwins', 'IsChecked'),
                          ('plot2_ftwins', 'IsChecked'),
                          ('plot1_paths', 'IsChecked'),
                          ('plot2_paths', 'IsChecked'),
                          ('plot1_op', 'GetStringSelection'),
                          ('plot2_op', 'GetStringSelection'),
                          ('plot1_voff', 'GetValue'),
                          ('plot2_voff', 'GetValue'),
                          ('plot_kw', 'GetStringSelection'),
                          ('plot2_win',   'GetStringSelection'),
                          ):
            opts[key] = getattr(self.wids[key], meth)()

        opts['plot1_op'] = Plot1_Choices[opts['plot1_op']]
        opts['plot2_op'] = Plot2_Choices[opts['plot2_op']]
        opts['plot2_win'] = int(opts['plot2_win'])
        opts['plot_kw'] = int(opts['plot_kw'])


        result_name  = f'{self.datagroup.groupname}.feffit_history[{self.nfit}]'
        opts['label'] = f'{result_name}.label'
        opts['filename'] = self.datagroup.filename
        opts['pargroup_name'] = f'{result_name}.paramgroup'
        opts['title'] = f'{self.datagroup.filename}: {result.label}'

        for attr in ('kmin', 'kmax', 'dk', 'rmin', 'rmax', 'fitspace'):
            opts[attr] = getattr(trans, attr)
        opts['fit_kwstring'] = "%s" % getattr(trans, 'kweight')
        opts['kwindow']  = getattr(trans, 'window')
        opts['topwin'] = self

        exafs_conf = self.feffit_panel.parent.get_nbpage('exafs')[1].read_form()
        opts['plot_rmax'] = exafs_conf['plot_rmax']
        self.feffit_panel.plot_feffit_result(f'{result_name}.datasets[0]', **opts)


    def onSaveFitCommand(self, event=None):
        wildcard = 'Larch/Python Script (*.lar)|*.lar|All files (*.*)|*.*'
        result = self.get_fitresult()
        if result is None:
            return
        fname = fix_filename(f'{self.datagroup.filename}_{result.label:s}.lar')

        path = FileSave(self, message='Save text to file',
                        wildcard=wildcard, default_file=fname)
        if path is not None:
            text  = '\n'.join(result.commands)
            with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(text)
                fh.write('')


    def onSaveFit(self, evt=None, form='chikw'):
        "Save arrays to text file"
        result = self.get_fitresult()
        if result is None:
            return

        fname = fix_filename(f'{self.datagroup.filename}_{result.label:s}_{form}')
        fname = fname.replace('.', '_')
        fname = fname + '.txt'

        wildcard = 'Text Files (*.txt)|*.txt|All files (*.*)|*.*'
        savefile = FileSave(self, 'Save Fit Model (%s)' % form,
                            default_file=fname,
                            wildcard=wildcard)
        if savefile is None:
            return

        text = feffit_report(result)
        desc = self.outforms[form]
        buff = [f'# Results for {self.datagroup.filename} "{result.label}": {desc}']

        for line in text.split('\n'):
            buff.append('# %s' % line)
        buff.append('## ')
        buff.append('#' + '---'*25)

        ds0 = result.datasets[0]

        xname = 'k' if form.startswith('chik') else 'r'
        yname = 'chi' if form.startswith('chik') else form
        yname = 'chiq_re' if form.startswith('chiq') else form
        kw = 0
        if form == 'chikw':
            kw = ds0.transform.kweight

        xarr   = getattr(ds0.data, xname)
        nx     = len(xarr)
        ydata  = getattr(ds0.data, yname)[:nx] * xarr**kw
        ymodel = getattr(ds0.model, yname)[:nx] * xarr**kw
        out    = [xarr, ydata, ymodel]

        array_names = [xname, 'expdata', 'model']
        for pname, pgroup in ds0.paths.items():
            array_names.append(f'feffpath_{pname}')
            out.append(getattr(pgroup, yname)[:nx] * xarr**kw)

        col_labels = []
        for a in array_names:
            if len(a) < 13:
                a = (a + ' '*13)[:13]
            col_labels.append(a)

        buff.append('# ' + '  '.join(col_labels))

        for i in range(nx):
            words = [gformat(x[i], 12) for x in out]
            buff.append('   '.join(words))
        buff.append('')


        with open(savefile, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write('\n'.join(buff))

    def get_fitresult(self, nfit=None):
        if nfit is None:
            nfit = self.nfit
        self.feffit_history = getattr(self.datagroup, 'feffit_history', [])
        self.nfit = max(0, nfit)
        n_hist = len(self.feffit_history)
        if n_hist == 0:
            return None
        if self.nfit > n_hist:
            self.nfit = 0
        return self.feffit_history[self.nfit]


    def onSelectFit(self, evt=None):
        if self.wids['stats'] is None:
            return
        item = self.wids['stats'].GetSelectedRow()
        if item > -1:
            self.show_fitresult(nfit=item)

    def onSelectParameter(self, evt=None):
        if self.wids['params'] is None:
            return
        if not self.wids['params'].HasSelection():
            return
        item = self.wids['params'].GetSelectedRow()
        pname = self.wids['paramsdata'][item]

        cormin= self.wids['min_correl'].GetValue()
        self.wids['correl'].DeleteAllItems()

        result = self.get_fitresult()
        if result is None:
            return
        this = result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.wids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        result = self.get_fitresult()
        if result is None:
            return
        params = result.params
        parnames = list(params.keys())

        cormin= self.wids['min_correl'].GetValue()
        correls = {}
        for i, name in enumerate(parnames):
            par = params[name]
            if not par.vary:
                continue
            if hasattr(par, 'correl') and par.correl is not None:
                for name2 in parnames[i+1:]:
                    if (name != name2 and name2 in par.correl and
                            abs(par.correl[name2]) > cormin):
                        correls["%s$$%s" % (name, name2)] = par.correl[name2]

        sort_correl = sorted(correls.items(), key=lambda it: abs(it[1]))
        sort_correl.reverse()

        self.wids['correl'].DeleteAllItems()

        for namepair, corval in sort_correl:
            name1, name2 = namepair.split('$$')
            self.wids['correl'].AppendItem((name1, name2, "% .4f" % corval))

    def onCopyParams(self, evt=None):
        result = self.get_fitresult()
        if result is None:
            return
        self.feffit_panel.update_start_values(result.params)

    def ShowDataSet(self, evt=None):
        dataset = evt.GetString()
        group = self.datasets.get(evt.GetString(), None)
        if group is not None:
            self.show_results(datagroup=group)

    def add_results(self, dgroup, form=None, larch_eval=None, show=True):
        name = dgroup.filename
        if name not in self.filelist.GetItems():
            self.filelist.Append(name)
        self.datasets[name] = dgroup
        if show:
            self.show_results(datagroup=dgroup, form=form, larch_eval=larch_eval)

    def show_results(self, datagroup=None, form=None, larch_eval=None):
        if datagroup is not None:
            self.datagroup = datagroup
        if larch_eval is not None:
            self.larch_eval = larch_eval

        datagroup = self.datagroup
        self.feffit_history = getattr(self.datagroup, 'feffit_history', [])

        cur = self.get_fitresult()
        if cur is None:
            return
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.feffit_history):
            args = ["%d" % (i+1), res.label, "%.d" % (len(res.datasets[0].paths))]
            for attr in ('nvarys', 'n_independent', 'chi_square',
                         'chi2_reduced', 'rfactor'):
                val = getattr(res, attr)
                if isinstance(val, int):
                    val = '%d' % val
                elif attr == 'n_independent':
                    val = "%.2f" % val
                else:
                    val = "%.4f" % val
                    # val = gformat(val, 9)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))
        wids['data_title'].SetLabel(self.datagroup.filename)
        self.show_fitresult(nfit=0)


    def show_fitresult(self, nfit=0, datagroup=None):
        if datagroup is not None:
            self.datagroup = datagroup

        result = self.get_fitresult(nfit=nfit)
        if result is None:
            return

        path_hashkeys = []
        for ds in result.datasets:
            path_hashkeys.extend([p.hashkey for p in ds.paths.values()])

        wids = self.wids
        wids['fit_label'].SetValue(result.label)
        wids['data_title'].SetLabel(self.datagroup.filename)
        wids['params'].DeleteAllItems()
        wids['paramsdata'] = []
        for param in reversed(result.params.values()):
            pname = param.name
            if any([pname.endswith('_%s' % phash) for phash in path_hashkeys]):
                continue
            if getattr(param, 'skip', None) not in (False, None):
                continue

            try:
                val = gformat(param.value, 10)
            except (TypeError, ValueError):
                val = ' ??? '
            serr = ' N/A '
            if param.stderr is not None:
                serr = gformat(param.stderr, 10)
            extra = ' '
            if param.expr is not None:
                extra = '= %s ' % param.expr
            elif not param.vary:
                extra = '(fixed)'
            elif param.init_value is not None:
                extra = '(init=%s)' % gformat(param.init_value, 10)

            wids['params'].AppendItem((pname, val, serr, extra))
            wids['paramsdata'].append(pname)
        self.Refresh()

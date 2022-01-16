import time
import os
import ast
import shutil
import string
from sys import exc_info
import numpy as np
np.seterr(all='ignore')

from functools import partial
import json

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from lmfit import Parameter
from lmfit.model import (save_modelresult, load_modelresult,
                             save_model, load_model)

import lmfit.models as lm_models
from lmfit.printfuncs import gformat

from larch import Group, site_config
from larch.math import index_of
from larch.fitting import group2params, param
from larch.utils.jsonutils import encode4js, decode4js
from larch.utils.strutils import fix_varname, fix_filename
from larch.io.export_modelresult import export_modelresult
from larch.xafs import feffit_report
from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, MenuItem,
                         GUIColors, CEN, RIGHT, LEFT, FRAMESTYLE, Font,
                         FONTSIZE, FileSave, FileOpen, flatnotebook,
                         EditableListBox)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel


DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

KWeight_Choices = {'1': '1', '2': '2', '3': '3',
                   '2 and 3': '[2, 3]',
                   '1, 2, and 3':  '[2, 1, 3]'}
FitSpace_Choices = {'R space': 'r', 'k space':'k', 'wavelet': 'w'}
FitPlot_Choices = {'K and R space': 'k+r', 'R space only': 'r'}


chik    = '\u03c7(k)'
chirmag = '|\u03c7(R)|'
chirre  = 'Re[\u03c7(R)]'
chirmr  = '|\u03c7(R)| + Re[\u03c7(R)]'
# wavelet = 'EXAFS wavelet'
noplot  = '<no plot>'

PlotOne_Choices = [chik, chirmag, chirre, chirmr]
PlotAlt_Choices = [noplot] + PlotOne_Choices

FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

ScriptWcards = "Fit Models(*.lar)|*.lar|All files (*.*)|*.*"
PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['feffit_top'] = """## saved {ctime}
## commmands to reproduce Feffit
## to use from python, uncomment these lines:
#from larch.xafs import feffit, feffit_dataset, feffit_transform, feffit_report
#from larch.xafs import pre_edge, autobk, xftf, xftr, ff2chi, feffpath
#from larch.fitting import  param_group, param
#from larch.io import read_ascii, read_athena, read_xdi, read_specfile
#
####  for interactive plotting from python (but not the Larch shell!) use:
#from larch.wxlib.xafsplots import plot_chik, plot_chir
#from wxmplot.interactive import get_wxapp
#wxapp = get_wxapp()  # <- needed for plotting to work from python
####
"""

COMMANDS['data_source'] = """# you will need to add how the data chi(k) gets built:
## data group = {groupname}
## from source = {filename}
## some processing steps for this group (comment out as needed):
"""

COMMANDS['xft'] =  """# ffts on group {groupname:s}
xftf({groupname:s}, kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.3f}, window='{kwindow:s}', kweight={kweight:.3f})
xftr({groupname:s}, rmin={rmin:.3f}, rmax={rmax:.3f}, dr={dr:.3f}, window='{rwindow:s}')
"""

COMMANDS['feffit_params_init'] = """# create feffit Parameter Group to hold fit parameters
_feffit_params = param_group(s02=param(1.0, min=0, vary=True),
                             e0=param(0.1, min=-25, max=25, vary=True))
"""

COMMANDS['feffit_trans'] = """# define Fourier transform and fitting space
_feffit_trans = feffit_transform(kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.4f}, kw={kwstring:s},
                      window='{kwindow:s}', fitspace='{fitspace:s}', rmin={rmin:.3f}, rmax={rmax:.3f})
"""

COMMANDS['paths_init'] = """# make sure a dictionary for Feff Paths exists
try:
    npaths = len(_paths.keys())
except:
    _paths = {}
#endtry
"""

COMMANDS['add_path'] = """
_paths['{title:s}'] = feffpath('{fullpath:s}',
                  label='{label:s}', degen=1,
                  s02='{amp:s}',     e0='{e0:s}',
                  deltar='{delr:s}', sigma2='{sigma2:s}',
                  third='{third:s}', ei='{ei:s}')
"""

COMMANDS['ff2chi']   = """# make dict of paths, sum them using a group of parameters
_ff2chi_paths  = {paths:s}
if len(_ff2chi_paths) > 0:
    _pathsum = ff2chi(_ff2chi_paths, paramgroup={params:s})
#endif
"""

COMMANDS['do_feffit'] = """# build feffit dataset, run feffit
_feffit_dataset = feffit_dataset(data={groupname:s}, transform={trans:s}, paths={paths:s})
_feffit_result = feffit({params}, _feffit_dataset)
if not hasattr({groupname:s}, 'feffit_history'): {groupname}.feffit_history = []
_feffit_result.label = 'Fit %i' % (1+len({groupname}.feffit_history))
{groupname:s}.feffit_history.insert(0, _feffit_result)
"""

COMMANDS['path2chi'] = """# generate chi(k) and chi(R) for each path
for label, path in {paths_name:s}.items():
     path.calc_chi_from_params({pargroup_name:s})
     xftf(path, kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.3f},
         window='{kwindow:s}', kweight={kweight:.3f})
#endfor
"""



default_config = dict(fitspace='r', kwstring='2', kmin=2, kmax=None, dk=4, kwindow=FTWINDOWS[0], rmin=1, rmax=4)

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
                ptype = 'vary' if par.vary else 'fixed'
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
            attr.SetColour('#000')
        elif ptype == 'fixed':
            attr.SetColour('#A11')
        else:
            attr.SetColour('#11A')
        return True

class EditParamsFrame(wx.Frame):
    """ edit parameters"""
    def __init__(self, parent=None, feffit_panel=None,
                 paramgroup=None, selected=None):
        wx.Frame.__init__(self, None, -1,
                          'Edit Feffit Parameters',
                          style=FRAMESTYLE, size=(550, 300))

        self.parent = parent
        self.feffit_panel = feffit_panel
        self.paramgroup = paramgroup

        spanel = scrolled.ScrolledPanel(self, size=(500, 275))
        spanel.SetBackgroundColour('#EEEEEE')

        self.dvc = dv.DataViewCtrl(spanel, style=DVSTYLE)
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
        toppan.Add(Button(toppan, "'Fix' Selected",    action=self.onFix, size=(175, -1)))
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
            if pname not in curr_syms and par.vary:
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

    def onFix(self, event=None):
        for pname, sel, ptype, val in self.model.data:
            if sel and ptype == 'vary':
                par = getattr(self.paramgroup, pname, None)
                if par is not None and par.vary:
                    par.vary = False
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
        wx.Panel.__init__(self, parent, -1, size=(550, 450))
        self.feffit_panel = feffit_panel
        self.parwids = {}
        spanel = scrolled.ScrolledPanel(self)

        panel = self.panel = GridPanel(spanel, ncols=8, nrows=30, pad=1, itemstyle=LEFT)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=wx.ALIGN_LEFT, **kws)

        panel.Add(SLabel("Feffit Parameters ", colour='#0000AA', size=(200, -1)), dcol=2)
        panel.Add(Button(panel, 'Edit Parameters', action=self.onEditParams),  dcol=2)
        panel.Add(Button(panel, 'Force Refresh', action=self.Rebuild),         dcol=3)

        panel.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        panel.AddMany((SLabel(" Value"),
                       SLabel(" Type"),
                       SLabel(' Bounds'),
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
            if pname in self.parwids:
                self.parwids[pname].value.SetValue(par.value)

    def update(self):
        pargroup = self.feffit_panel.get_paramgroup()
        hashkeys = self.feffit_panel.get_pathkeys()
        params = group2params(pargroup)
        for pname, par in params.items():
            if any([pname.endswith('_%s' % phash) for phash in hashkeys]):
                continue
            if pname in self.parwids:
                pwids = self.parwids[pname]
                varstr = 'vary' if par.vary else 'fix'
                if par.expr is not None:
                    varstr = 'constrain'
                    pwids.expr.SetValue(par.expr)
                pwids.vary.SetStringSelection(varstr)
                pwids.value.SetValue(par.value)
                pwids.minval.SetValue(par.min)
                pwids.maxval.SetValue(par.max)
            else:
                if not hasattr(par, '_is_pathparam'):
                    pwids = ParameterWidgets(self.panel, par,
                                             name_size=100,
                                             expr_size=150,
                                             float_size=70,
                                             widgets=('name',
                                                      'value', 'minval', 'maxval',
                                                      'vary', 'expr'))

                    self.parwids[pname] = pwids
                    self.panel.Add(pwids.name, newrow=True)
                    self.panel.AddMany((pwids.value, pwids.vary, pwids.bounds,
                                    pwids.minval, pwids.maxval, pwids.expr))
                    self.panel.pack()
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

    def generate_script(self, event=None):
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
            if param.expr is not None:
                args.append(f"expr='{param.expr}'")
            elif param.vary:
                args.append(f'vary=True')
            else:
                args.append(f'vary=False')
            args = ', '.join(args)
            cmd = f'_feffit_params.{name} = param({args})'
            s.append(cmd)
        return s


class FeffPathPanel(wx.Panel):
    """Feff Path """
    def __init__(self, parent=None, feffdat_file=None, dirname=None,
                 fullpath=None, absorber=None, edge=None, reff=None,
                 degen=None, geom=None, npath=1, title='', user_label='',
                 _larch=None, feffit_panel=None, **kws):

        self.parent = parent
        self.title = title
        self.user_label = user_label
        self.feffit_panel = feffit_panel
        self.losefocus_active = False
        wx.Panel.__init__(self, parent, -1, size=(550, 450))
        panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.feffdat_file = feffdat_file
        self.fullpath = fullpath

        self.reff = reff = float(reff)
        degen = float(degen)
        self.geom = geom

        self.wids = wids = {}
        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=LEFT, **kws)

        for name, expr in (('label', user_label),
                           ('amp',  f'{degen:.1f} * s02'),
                           ('e0',  'e0'),
                           ('delr',  f'delr_{title}'),
                           ('sigma2',  f'sigma2_{title}'),
                           ('third',  ''),
                           ('ei',  '')):
            self.wids[name] = wx.TextCtrl(panel, -1, size=(250, -1),
                                          value=expr, style=wx.TE_PROCESS_ENTER)
            wids[name+'_val'] = SimpleText(panel, '', size=(150, -1), style=LEFT)

        wids['use'] = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        wids['del'] = Button(panel, 'Remove This Path', size=(150, -1),
                             action=self.onRemovePath)
        wids['plot_feffdat'] = Button(panel, 'Plot F(k)', size=(150, -1),
                             action=self.onPlotFeffDat)

        title1 = f'{dirname:s}: {feffdat_file:s}  {absorber:s} {edge:s} edge'
        title2 = f'Reff={reff:.4f},  Degen={degen:.1f}   {geom:s}'

        panel.Add(SLabel(title1, size=(375, -1), colour='#0000AA'),
                  dcol=2,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['use'])
        panel.Add(wids['del'])
        panel.Add(SLabel(title2, size=(375, -1)),
                  dcol=3, style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['plot_feffdat'])

        panel.AddMany((SLabel('Label'),     wids['label'], wids['label_val']),  newrow=True)
        panel.AddMany((SLabel('Amplitude'), wids['amp'],    wids['amp_val']), newrow=True)
        panel.AddMany((SLabel('E0 '),       wids['e0'],     wids['e0_val']),  newrow=True)
        panel.AddMany((SLabel('Delta R'),   wids['delr'],   wids['delr_val']), newrow=True)
        panel.AddMany((SLabel('sigma2'),    wids['sigma2'], wids['sigma2_val']), newrow=True)
        panel.AddMany((SLabel('third'),     wids['third'],  wids['third_val']),   newrow=True)
        panel.AddMany((SLabel('Eimag'),     wids['ei'],  wids['ei_val']),   newrow=True)
        panel.pack()
        sizer= wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(self, sizer)

    def enable_losefocus(self):
        # print("enable losefocus")
        for name in ('label', 'amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            self.wids[name].Bind(wx.EVT_TEXT_ENTER, partial(self.onExpression, name=name))
            self.wids[name].Bind(wx.EVT_KILL_FOCUS, partial(self.onExpression, name=name))
        self.losefocus_active = True
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
            opts['value'] = np.sqrt(self.reff)/200.0
        elif name == 'delr':
            opts['minval'] = -0.5
            opts['maxval'] =  0.5
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
        cmd = f"plot_feffdat(_paths['{self.title}'], title='Feff data for path {self.title}')"
        self.feffit_panel.larch_eval(cmd)

    def onRemovePath(self, event=None):
        msg = f"Delete Path {self.title:s}?"
        dlg = wx.MessageDialog(self, msg, 'Warning', wx.YES | wx.NO )
        if (wx.ID_YES == dlg.ShowModal()):
            self.feffit_panel.paths_data.pop(self.title)
            path_nb = self.feffit_panel.paths_nb
            for i in range(path_nb.GetPageCount()):
                if self.title == path_nb.GetPageText(i).strip():
                    path_nb.DeletePage(i)
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
        TaskPanel.__init__(self, parent, controller,
                           configname='feffit_config',
                           config=default_config,
                           title='Feff Fitting of EXAFS Paths', **kws)
        self.paths_data = {}
        self.timers = {'paths': wx.Timer(self)}
        self.Bind(wx.EVT_TIMER, self.onPathTimer, self.timers['paths'])

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
                self.xasmain.process_exafs(dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")


    def build_display(self):
        self.paths_nb = flatnotebook(self, {}, drag_tabs=False,
                                     on_change=self.onPathsNBChanged)
        self.params_panel = FeffitParamsPanel(parent=self.paths_nb,
                                              feffit_panel=self)

        self.paths_nb.AddPage(self.params_panel, ' Parameters ', True)

        pan = self.panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = wids = {}

        fsopts = dict(digits=2, increment=0.1, with_pin=True)

        ffit_kmin = self.add_floatspin('ffit_kmin',  value=2, **fsopts)
        ffit_kmax = self.add_floatspin('ffit_kmax',  value=17, **fsopts)
        ffit_dk   = self.add_floatspin('ffit_dk',    value=4, **fsopts)
        ffit_rmin = self.add_floatspin('ffit_rmin',  value=1, **fsopts)
        ffit_rmax = self.add_floatspin('ffit_rmax',  value=5, **fsopts)

        wids['ffit_kweight'] = Choice(pan, size=(125, -1),
                                     choices=list(KWeight_Choices.keys()))
        wids['ffit_kweight'].SetSelection(1)

        wids['ffit_kwindow'] = Choice(pan, choices=list(FTWINDOWS), size=(125, -1))

        wids['ffit_fitspace'] = Choice(pan, choices=list(FitSpace_Choices.keys()),
                                       size=(125, -1))

        wids['plot_paths'] = Check(pan, default=False, label='Plot Each Path'
                                   , size=(125, -1), action=self.onPlot)
        wids['plot_ftwindows'] = Check(pan, default=False, label='Plot FT Windows'
                                   , size=(125, -1), action=self.onPlot)
        wids['plotone_op'] = Choice(pan, choices=PlotOne_Choices,
                                    action=self.onPlot, size=(125, -1))
        wids['plotone_op'].SetSelection(1)
        wids['plotalt_op'] = Choice(pan, choices=PlotAlt_Choices,
                                    action=self.onPlot, size=(125, -1))

        wids['plot_voffset'] = FloatSpin(pan, value=0, digits=2, increment=0.25,
                                         action=self.onPlot)

        wids['plot_current']  = Button(pan,'Plot Current Model',
                                     action=self.onPlot,  size=(175, -1))
        wids['do_fit']       = Button(pan, 'Fit Data to Model',
                                      action=self.onFitModel,  size=(175, -1))
        # wids['do_fit'].Disable()

#         wids['do_fit_sel']= Button(pan, 'Fit Selected Groups',
#                                    action=self.onFitSelected,  size=(125, -1))
#         wids['do_fit_sel'].Disable()

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, 'Feff Fitting',
                           size=(150, -1), **self.titleopts), style=LEFT, dcol=2, newrow=True)
        pan.Add(SimpleText(pan, 'To add paths, use Feff->Browse Feff Calculations',
                           size=(350, -1)), style=LEFT, dcol=3)

        add_text('Fitting Space: ')
        pan.Add(wids['ffit_fitspace'])

        add_text('k weightings: ', newrow=False)
        pan.Add(wids['ffit_kweight'])

        add_text('k min: ')
        pan.Add(ffit_kmin)
        add_text(' k max: ', newrow=False)
        pan.Add(ffit_kmax)

        add_text('k Window: ')
        pan.Add(wids['ffit_kwindow'])
        add_text('dk: ', newrow=False)
        pan.Add(ffit_dk)

        add_text('R min: ')
        pan.Add(ffit_rmin)
        add_text('R max: ', newrow=False)
        pan.Add(ffit_rmax)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        pan.Add(wids['plot_current'], dcol=1, newrow=True)
        pan.Add(wids['plotone_op'], dcol=1)
        pan.Add(wids['plot_paths'], dcol=2)
        pan.Add(wids['plot_ftwindows'], dcol=2)
        add_text('Add Second Plot: ', newrow=True)
        pan.Add(wids['plotalt_op'], dcol=1)
        add_text('Vertical offset: ', newrow=False)
        pan.Add(wids['plot_voffset'], dcol=1)

        pan.Add(wids['do_fit'], dcol=3, newrow=True)
        #        pan.Add(wids['do_fit_sel'], dcol=2)
        pan.Add((5, 5), newrow=True)

        pan.Add(HLine(self, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(self.paths_nb,  1, LEFT|wx.GROW, 5)
        pack(self, sizer)

    def onPathsNBChanged(self, event=None):
        updater = getattr(self.paths_nb.GetCurrentPage(), 'update_values', None)
        if callable(updater):
            updater()

    def onPathTimer(self, event=None):
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip().lower()
            page = self.paths_nb.GetPage(i)
            if not text.lower().startswith('param'):
                losefocus_active = getattr(page, 'losefocus_active', True)
                losefocus_method = getattr(page, 'enable_losefocus', None)
                if not losefocus_active and callable(losefocus_method):
                    losefocus_method()
                wids = getattr(page, 'wids', {})
                if 'label' in wids:
                    wids['label'].SetValue(page.user_label)
        self.timers['paths'].Stop()


    def get_config(self, dgroup=None):
        """get and set processing configuration for a group"""
        if dgroup is None:
             dgroup = self.controller.get_group()
        if dgroup is None:
             return self.get_defaultconfig()
        if not hasattr(dgroup, 'chi'):
             self.xasmain.process_exafs(dgroup)
        conf = getattr(dgroup, self.configname, None)
        if conf is None:
            # initial reading: start with default then take Athena Project values
            conf = self.get_defaultconfig()
            if hasattr(dgroup, 'fft_params'):
                afft_pars = getattr(dgroup, 'fft_params')
                if hasattr(afft_pars, 'kw'):
                    conf['kwstring'] = str(getattr(afft_pars, 'kw'))
                if hasattr(afft_pars, 'kweight'):
                    conf['kwstring'] = str(getattr(afft_pars, 'kweight'))

            econf = getattr(dgroup, 'exafs_config', {})
            for key in ('fft_kmin', 'fft_kmax', 'fft_dk', 'fft_kwindow',
                        'fft_rmin', 'fft_rmax','fft_kweight'):
                val = econf.get(key, None)
                tkey = key.replace('fft_', '')
                if key == 'fft_kweight':
                    val = str(int(val))
                    tkey = 'kwstring'
                if val is not None and tkey in conf:
                    conf[tkey] = val

            setattr(dgroup, self.configname, conf)
        return conf


    def process(self, dgroup=None, **kws):
        if dgroup is not None:
            self.dgroup = dgroup
        if dgroup is None:
            return

        conf = self.get_config(dgroup=dgroup)
        conf.update(kws)
        conf = self.read_form()


    def fill_form(self, dat):
        conf = self.get_config(dat)
        self.wids['ffit_kmin'].SetValue(conf['kmin'])
        self.wids['ffit_kmax'].SetValue(conf['kmax'])
        self.wids['ffit_rmin'].SetValue(conf['rmin'])
        self.wids['ffit_rmax'].SetValue(conf['rmax'])
        self.wids['ffit_dk'].SetValue(conf['dk'])
        self.wids['ffit_kwindow'].SetStringSelection(conf['kwindow'])

        for key, val in FitSpace_Choices.items():
            if conf['fitspace'] == val:
                self.wids['ffit_fitspace'].SetStringSelection(key)

        for key, val in KWeight_Choices.items():
            if conf['kwstring'] == val:
                self.wids['ffit_kweight'].SetStringSelection(key)

    def read_form(self, dgroup=None):
        "read for, returning dict of values"

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
        form_opts['kmin'] = wids['ffit_kmin'].GetValue()
        form_opts['kmax'] = wids['ffit_kmax'].GetValue()
        form_opts['dk']   = wids['ffit_dk'].GetValue()
        form_opts['rmin'] = wids['ffit_rmin'].GetValue()
        form_opts['rmax'] = wids['ffit_rmax'].GetValue()
        form_opts['kwstring'] = KWeight_Choices[wids['ffit_kweight'].GetStringSelection()]
        form_opts['fitspace'] = FitSpace_Choices[wids['ffit_fitspace'].GetStringSelection()]

        form_opts['kwindow']    = wids['ffit_kwindow'].GetStringSelection()
        form_opts['plot_ftwindows'] = wids['plot_ftwindows'].IsChecked()
        form_opts['plot_paths'] = wids['plot_paths'].IsChecked()
        form_opts['plotone_op'] = wids['plotone_op'].GetStringSelection()
        form_opts['plotalt_op'] = wids['plotalt_op'].GetStringSelection()
        form_opts['plot_voffset'] = wids['plot_voffset'].GetValue()
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

    def onPlot(self, evt=None, dgroup=None, pargroup_name='_feffit_params',
               paths_name='_ff2chi_paths', pathsum_name='_pathsum',
               build_fitmodel=True, **kws):

        opts = self.read_form(dgroup)
        opts.update(**kws)
        fname = opts['filename']
        gname = opts['groupname']
        dgroup = opts['datagroup']

        if build_fitmodel:
            self.build_fitmodel(dgroup)

        try:
            pathsum = self._plain_larch_eval(pathsum_name)
        except:
            pathsum = None

        try:
            paths = self._plain_larch_eval(paths_name)
        except:
            paths = {}

        plot1 = opts['plotone_op']
        plot2 = opts['plotalt_op']
        cmds = []

        if ',' in opts['kwstring']:
            kw = int(opts['kwstring'].replace('[','').replace(']','').split(',')[0])
        else:
            kw = int(opts['kwstring'])

        ftargs = dict(kmin=opts['kmin'], kmax=opts['kmax'], dk=opts['dk'],
                      kwindow=opts['kwindow'], kweight=kw,
                      rmin=opts['rmin'], rmax=opts['rmax'],
                      dr=opts.get('dr', 0.1), rwindow='hanning')

        if pathsum is not None:
            cmds.append(COMMANDS['xft'].format(groupname=pathsum_name, **ftargs))
        if dgroup is not None:
            cmds.append(COMMANDS['xft'].format(groupname=gname, **ftargs))
        if opts['plot_paths']:
            cmds.append(COMMANDS['path2chi'].format(paths_name=paths_name,
                                                    pargroup_name=pargroup_name,
                                                    **ftargs))

        self.larch_eval('\n'.join(cmds))
        with_win = opts['plot_ftwindows']
        cmds = []
        for i, plot in enumerate((plot1, plot2)):
            pcmd = 'plot_chir'
            pextra = f', win={i+1:d}'
            if plot == chik:
                pcmd = 'plot_chik'
                pextra += f', kweight={kw:d}'
            elif plot == chirre:
                pextra += ', show_mag=False, show_real=True'
            elif plot == chirmr:
                pextra += ', show_mag=True, show_real=True'
            if plot == noplot:
                continue
            newplot = f', show_window={with_win}, new=True'
            overplot = f', show_window=False, new=False'
            if dgroup is not None:
                cmds.append(f"{pcmd}({gname}, label='data'{pextra}, title='{fname}'{newplot})")
                if pathsum is not None:
                    cmds.append(f"{pcmd}({pathsum_name:s}, label='model'{pextra}{overplot})")
            elif pathsum is not None:
                cmds.append(f"{pcmd}({pathsum_name:s}, label='Path sum'{pextra}, title='sum of paths'{newplot})")
            if opts['plot_paths']:
                voff = opts['plot_voffset']

                for i, label in enumerate(paths.keys()):
                    objname = f"{paths_name}['{label:s}']"
                    # plabel = path.replace(pathlist_name, '').replace('[', '').replace(']', '')
                    cmds.append(f"{pcmd}({objname}, label='{label:s}'{pextra}, offset={(i+1)*voff}{overplot})")

        self.larch_eval('\n'.join(cmds))

    def add_path(self, feffdat_file,  feffresult):
        pathinfo = None
        folder, fp_file = os.path.split(feffdat_file)
        folder, dirname = os.path.split(folder)
        for path in feffresult.paths:
            if path.filename == fp_file:
                pathinfo = path
                break
        atoms = [s.strip() for s in pathinfo.geom.split('>')]
        atoms.pop(0)
        atoms.pop()
        title = '_'.join(atoms) + "%d" % (round(100*pathinfo.reff))
        for c in ',.[](){}<>+=-?/\\&%$#@!|:;"\'':
            title = title.replace(c, '')
        if title in self.paths_data:
            btitle = title
            i = -1
            while title in self.paths_data:
                i += 1
                title = btitle + '_%s' % string.ascii_lowercase[i]

        self.paths_data[title] = (feffdat_file, feffresult.folder,
                                  feffresult.absorber, feffresult.edge, pathinfo)

        user_label = fix_varname(f'{title:s}')
        pathpanel = FeffPathPanel(parent=self.paths_nb, title=title,
                                  npath=len(self.paths_data),
                                  user_label=user_label,
                                  feffdat_file=fp_file, dirname=dirname,
                                  fullpath=feffdat_file,
                                  absorber=feffresult.absorber,
                                  edge=feffresult.edge, reff=pathinfo.reff,
                                  degen=pathinfo.degeneracy,
                                  geom=pathinfo.geom,
                                  feffit_panel=self)

        self.paths_nb.AddPage(pathpanel, f' {title:s} ', True)

        for pname  in ('amp', 'e0', 'delr', 'sigma2', 'third', 'ei'):
            pathpanel.onExpression(name=pname)

        pdat = {'title': title, 'fullpath': feffdat_file, 'use':True}
        pdat.update(pathpanel.get_expressions())
        self.larch_eval(COMMANDS['add_path'].format(**pdat))

        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))
        ipage, pagepanel = self.xasmain.get_nbpage('feffit')
        self.xasmain.nb.SetSelection(ipage)
        self.xasmain.Raise()
        self.timers['paths'].Start(1000)

    def get_pathkeys(self):
        _paths = getattr(self.larch.symtable, '_paths', {})
        return [p.hashkey for p in _paths.values()]

    def get_paramgroup(self):
        pgroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pgroup is None:
            self.larch_eval(COMMANDS['feffit_params_init'])
            pgroup = getattr(self.larch.symtable, '_feffit_params')
        if not hasattr(self.larch.symtable, '_paths'):
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
                    if sym not in symtable:
                        s = f'_feffit_params.{sym:s} = param({value:.4f}, vary=True{extras:s})'
                        self.larch_eval(s)
            result = True
        except:
            result = False

        self.params_panel.update()
        return result


    def onLoadFitResult(self, event=None):
        dlg = wx.FileDialog(self, message="Load Saved Pre-edge Model",
                            wildcard=ModelWcards, style=wx.FD_OPEN)
        rfile = None
        if dlg.ShowModal() == wx.ID_OK:
            rfile = dlg.GetPath()
        dlg.Destroy()

        if rfile is None:
            return

        self.larch_eval("# peakmodel = lm_load_modelresult('%s')" %rfile)

        result = load_modelresult(str(rfile))
        for prefix in list(self.fit_components.keys()):
            self.onDeleteComponent(prefix=prefix)

        for comp in result.model.components:
            isbkg = comp.prefix in result.user_options['bkg_components']
            self.addModel(model=comp.func.__name__,
                          prefix=comp.prefix, isbkg=isbkg)

        for comp in result.model.components:
            parwids = self.fit_components[comp.prefix].parwids
            for pname, par in result.params.items():
                if pname in parwids:
                    wids = parwids[pname]
                    if wids.minval is not None:
                        wids.minval.SetValue(par.min)
                    if wids.maxval is not None:
                        wids.maxval.SetValue(par.max)
                    val = result.init_values.get(pname, par.value)
                    wids.value.SetValue(val)
                    varstr = 'vary' if par.vary else 'fix'
                    if par.expr is not None:
                        varstr = 'constrain'
                    if wids.vary is not None:
                        wids.vary.SetStringSelection(varstr)

        self.fill_form(result.user_options)


    def onSelPoint(self, evt=None, opt='__', relative_e0=False, win=None):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if opt not in self.wids:
            return None

        _x, _y = last_cursor_pos(win=win, _larch=self.larch)
        if _x is not None:
            if relative_e0 and 'e0' in self.wids:
                _x -= self.wids['e0'].GetValue()
            self.wids[opt].SetValue(_x)

    def get_xranges(self, x):
        opts = self.read_form()
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

    def build_fitmodel(self, groupname=None):
        """ use fit components to build model"""
        paths = []
        cmds = ["### set up feffit "]
        pargroup = self.get_paramgroup()
        cmds.extend(self.params_panel.generate_script())

        opts = self.read_form()
        cmds.append(COMMANDS['feffit_trans'].format(**opts))

        path_pages = {}
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)

        cmds.append(COMMANDS['paths_init'])

        paths_list = []
        for title, pathdata in self.paths_data.items():
            if title not in path_pages:
                continue
            pdat = {'title': title, 'fullpath': pathdata[0], 'use':True}
            pdat.update(path_pages[title].get_expressions())
            if pdat['use']:
                cmds.append(COMMANDS['add_path'].format(**pdat))
                paths_list.append(f"'{title:s}': _paths['{title:s}']")

        paths_string = '{%s}' % (', '.join(paths_list))
        cmds.append(COMMANDS['ff2chi'].format(paths=paths_string, params='_feffit_params'))
        self.larch_eval("\n".join(cmds))
        return opts


    def get_used_params(self, action='fix'):
        used_syms = []
        path_pages = {}
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)
        for title in self.paths_data:
            if title not in path_pages:
                continue
            exprs = path_pages[title].get_expressions()
            for ename, expr in exprs.items():
                if ename in ('label', 'use'):
                    continue
                for node in ast.walk(ast.parse(expr)):
                    if isinstance(node, ast.Name):
                        sym = node.id
                        if sym not in used_syms:
                            used_syms.append(sym)

        return used_syms


    def onFitModel(self, event=None, dgroup=None):
        session_history = self.get_session_history()
        nstart = len(session_history)

        script = [COMMANDS['feffit_top'].format(ctime=time.ctime())]

        opts = self.build_fitmodel(dgroup)
        dgroup = opts['datagroup']
        fopts = dict(groupname=opts['groupname'],
                     trans='_feffit_trans',
                     paths='_ff2chi_paths',
                     params='_feffit_params')

        groupname = opts['groupname']
        filename = opts['filename']

        script.append("######################################")
        script.append(COMMANDS['data_source'].format(groupname=groupname, filename=filename))
        for cmd in session_history:
            if groupname in cmd or filename in cmd or 'athena' in cmd:
                for cline in cmd.split('\n'):
                    script.append(f"#{cline}")

        script.append("## end of data reading and preparation")
        script.append("######################################")


        self.larch_eval(COMMANDS['do_feffit'].format(**fopts))


        self.onPlot(dgroup=opts['datagroup'], build_fitmodel=False,
                    pargroup_name='_feffit_result.paramgroup',
                    paths_name='_feffit_dataset.paths',
                    pathsum_name='_feffit_dataset.model')

        script.extend(self.get_session_history()[nstart:])
        script.extend(["print(feffit_report(_feffit_result))",
                       "#end of autosaved feffit script" , ""])
        dgroup.feffit_history[0].commands = script

        sname = self.autosave_script('\n'.join(script))
        self.write_message("wrote feffit script to '%s'" % sname)

        self.show_subframe('feffit_result', FeffitResultFrame,
                           datagroup=dgroup, feffit_panel=self)
        self.subframes['feffit_result'].add_results(dgroup, form=opts)

    def update_start_values(self, params):
        """fill parameters with best fit values"""
        self.params_panel.set_init_values(params)
        for i in range(self.paths_nb.GetPageCount()):
            if 'parameters' in self.paths_nb.GetPageText(i).strip().lower():
                self.paths_nb.SetSelection(i)

    def autosave_script(self, text, fname='feffit_script.lar'):
        """autosave model result to user larch folder"""
        confdir = os.path.join(site_config.user_larchdir, 'xas_viewer')
        if not os.path.exists(confdir):
            try:
                os.makedirs(confdir)
            except OSError:
                print("Warning: cannot create XAS_Viewer user folder")
                return
        if fname is None:
            fname = 'feffit_script.lar'
        fullname = os.path.join(confdir, fname)
        if os.path.exists(fullname):
            backup = os.path.join(confdir, 'feffit_script_BAK.lar')
            shutil.copy(fullname, backup)
        with open(fullname, 'w')as fh:
            fh.write(text)
        return fullname


###############

class FeffitResultFrame(wx.Frame):
    configname='feffit_config'
    def __init__(self, parent=None, feffit_panel=None, datagroup=None,
                  **kws):
        wx.Frame.__init__(self, None, -1, title='Feffit Results',
                          style=FRAMESTYLE, size=(900, 700), **kws)

        self.outforms = {'chik': 'chi(k), no k-weight',
                         'chikw': 'chi(k), k-weighted',
                         'chir_mag': '|chi(R)|',
                         'chir_re': 'Real[chi(R)]'}

        self.feffit_panel = feffit_panel
        self.datagroup = datagroup
        self.fit_history = getattr(datagroup, 'fit_history', [])
        self.parent = parent
        self.report_frame = None
        self.datasets = {}
        self.form = {}
        self.larch_eval = feffit_panel.larch_eval
        self.nfit = 0
        self.createMenus()
        self.build()

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

        self.datalistbox = EditableListBox(splitter, self.ShowDataSet,
                                           size=(250, -1))
        panel = scrolled.ScrolledPanel(splitter)

        panel.SetMinSize((600, 575))
        panel.SetSize((850, 575))
        self.colors = GUIColors()

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Feffit Results', font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+2),
                                        minsize=(350, -1),
                                        colour=self.colors.title, style=LEFT)

        wids['plot_paths'] = Check(panel, default=False, label='Plot Each Path'
                                   , size=(125, -1), action=self.onPlot)
        wids['plot_ftwindows'] = Check(panel, default=False, label='Plot FT Windows'
                                   , size=(125, -1), action=self.onPlot)
        wids['plotone_op'] = Choice(panel, choices=PlotOne_Choices,
                                    action=self.onPlot, size=(125, -1))
        wids['plotone_op'].SetSelection(1)
        wids['plotalt_op'] = Choice(panel, choices=PlotAlt_Choices,
                                    action=self.onPlot, size=(125, -1))

        wids['plot_voffset'] = FloatSpin(panel, value=0, digits=2, increment=0.25,
                                         action=self.onPlot)

        wids['plot_current']  = Button(panel,'Plot Current Model',
                                     action=self.onPlot,  size=(175, -1))

        wids['show_pathpars']  = Button(panel,'Show Path Parameters',
                                        action=self.onShowPathParams, size=(175, -1))
        wids['show_script']  = Button(panel,'Show Feffit Script',
                                        action=self.onShowScript, size=(175, -1))

        wids['fit_label'] = wx.TextCtrl(panel, -1, ' ', size=(225, -1))
        wids['set_label'] = Button(panel, 'Update Label', size=(175, -1),
                                   action=self.onUpdateLabel)


        irow = 0
        sizer.Add(title,              (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['data_title'], (irow, 1), (1, 3), LEFT)

        irow += 1
        sizer.Add(wids['plot_current'],     (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plotone_op'],       (irow, 1), (1, 1), LEFT)
        sizer.Add(wids['plot_paths'],       (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot_ftwindows'],   (irow, 3), (1, 1), LEFT)

        irow += 1
        sizer.Add(SimpleText(panel, 'Add Second Plot:', style=LEFT), (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plotalt_op'],                                (irow, 1), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, 'Vertical offset:', style=LEFT), (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['plot_voffset'],                              (irow, 3), (1, 1), LEFT)

        irow += 1
        sizer.Add(wids['show_pathpars'], (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['show_script'],   (irow, 1), (1, 1), LEFT)
        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(SimpleText(panel, 'Fit Label:', style=LEFT), (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['fit_label'], (irow, 1), (1, 2), LEFT)
        sizer.Add(wids['set_label'], (irow, 3), (1, 1), LEFT)


        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)
        subtitle = SimpleText(panel, ' (most recent fit is at the top)',
                              font=Font(FONTSIZE+1),  style=LEFT)

        sizer.Add(title, (irow, 0), (1, 1), LEFT)
        sizer.Add(subtitle, (irow, 1), (1, 1), LEFT)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn(' Label', width=120)
        sview.AppendTextColumn('N_paths', width=75)
        sview.AppendTextColumn('N_vary', width=70)
        sview.AppendTextColumn('N_idp',  width=70)
        sview.AppendTextColumn('\u03c7\u00B2', width=80)
        sview.AppendTextColumn('reduced \u03c7\u00B2', width=90)
        sview.AppendTextColumn('R Factor', width=90)
        sview.AppendTextColumn('Akaike Info', width=95)


        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            this.Sortable = True
            this.Alignment = wx.ALIGN_RIGHT if col > 0 else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        sview.SetMinSize((700, 125))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)
        sizer.Add(title, (irow, 0), (1, 1), LEFT)

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(225, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LEFT)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        self.wids['paramsdata'] = []
        pview.AppendTextColumn('Parameter',         width=150)
        pview.AppendTextColumn('Best-Fit Value',    width=125)
        pview.AppendTextColumn('Standard Error',    width=125)
        pview.AppendTextColumn('Info ',             width=300)

        for col in range(4):
            this = pview.Columns[col]
            this.Sortable = False
            this.Alignment = wx.ALIGN_RIGHT if col in (1, 2) else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        pview.SetMinSize((700, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)

        self.wids['all_correl'] = Button(panel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatSpin(panel, value=MIN_CORREL,
                                            min_val=0, size=(100, -1),
                                            digits=3, increment=0.1)

        ctitle = SimpleText(panel, 'minimum correlation: ')
        sizer.Add(title,  (irow, 0), (1, 1), LEFT)
        sizer.Add(ctitle, (irow, 1), (1, 1), LEFT)
        sizer.Add(self.wids['min_correl'], (irow, 2), (1, 1), LEFT)
        sizer.Add(self.wids['all_correl'], (irow, 3), (1, 1), LEFT)

        cview = self.wids['correl'] = dv.DataViewListCtrl(panel, style=DVSTYLE)

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
        cview.SetMinSize((475, 200))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LEFT)

        pack(panel, sizer)
        panel.SetupScrolling()

        splitter.SplitVertically(self.datalistbox, panel, 1)

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
        text = f'# Feffit Report for {self.datagroup.filename} fit "{result.label}"\n'
        text = text + feffit_report(result)
        title = f'Report for {self.datagroup.filename} fit "{result.label}"'
        fname = fix_filename(f'{self.datagroup.filename}_{result.label}.txt')
        self.show_report(text, title=title, default_filename=fname)

    def onShowScript(self, event=None):
        result = self.get_fitresult()
        text = [f'# Feffit Script for {self.datagroup.filename} fit "{result.label}"']
        text.extend(result.commands)
        text = '\n'.join(text)
        title = f'Script for {self.datagroup.filename} fit "{result.label}"'
        fname = fix_filename(f'{self.datagroup.filename}_{result.label}.lar')
        self.show_report(text, title=title, default_filename=fname,
                         wildcard='Larch/Python Script (*.lar)|*.lar')

    def onUpdateLabel(self, event=None):
        result = self.get_fitresult()
        item = self.wids['stats'].GetSelectedRow()
        result.label = self.wids['fit_label'].GetValue()
        self.show_results()

    def onPlot(self, event=None):
        opts = {'build_fitmodel': False}
        for key, meth in (('plot_ftwindows', 'IsChecked'),
                          ('plot_paths', 'IsChecked'),
                          ('plotone_op', 'GetStringSelection'),
                          ('plotalt_op', 'GetStringSelection'),
                          ('plot_voffset', 'GetValue')):
            opts[key] = getattr(self.wids[key], meth)()

        result = self.get_fitresult()
        dgroup = result.datasets[0].data
        trans  = result.datasets[0].transform

        result_name  = f'{self.datagroup.groupname}.feffit_history[{self.nfit}]'
        opts['label'] = f'{result_name}.label'
        opts['pargroup_name'] = f'{result_name}.paramgroup'
        opts['paths_name']    = f'{result_name}.datasets[0].paths'
        opts['pathsum_name']  = f'{result_name}.datasets[0].model'
        opts['dgroup']  = dgroup
        opts['title'] = f'{self.datagroup.filename} "{result.label}"'

        for attr in ('kmin', 'kmax', 'dk', 'rmin', 'rmax', 'fitspace'):
            opts[attr] = getattr(trans, attr)
        opts['kwstring'] = "%s" % getattr(trans, 'kweight')
        opts['kwindow']  = getattr(trans, 'window')

        self.feffit_panel.onPlot(**opts)


    def onSaveFitCommand(self, event=None):
        wildcard = 'Larch/Python Script (*.lar)|*.lar|All files (*.*)|*.*'
        result = self.get_fitresult()
        fname = fix_filename(f'{self.datagroup.filename}_{result.label:s}.lar')

        path = FileSave(self, message='Save text to file',
                        wildcard=wildcard, default_file=fname)
        if path is not None:
            text  = '\n'.join(result.commands)
            with open(path, 'w') as fh:
                fh.write(text)
                fh.write('')


    def onSaveFit(self, evt=None, form='chikw'):
        "Save arrays to text file"
        result = self.get_fitresult()

        fname = fix_filename(f'{self.datagroup.filename}_{result.label:s}_{form}')
        fname = fname.replace('.', '_')
        fname = fname + '.txt'

        wildcard = 'Text Files (*.txt)|*.txt|All files (*.*)|*.*'
        savefile = FileSave(self, 'Save Fit Model (%s)' % form,
                            default_file=fname,
                            wildcard=wildcard)
        if savefile is None:
            return

        result = self.get_fitresult()
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
        kw = 0
        if form == 'chikw':
            kw = ds0.transform.kweight

        xarr   = getattr(ds0.data, xname)
        nx     = len(xarr)
        ydata  = getattr(ds0.data, yname) * xarr**kw
        ymodel = getattr(ds0.model, yname) * xarr**kw
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


        with open(savefile, 'w') as fh:
            fh.write('\n'.join(buff))


    def get_fitresult(self, nfit=None):
        if nfit is None:
            nfit = self.nfit
        self.fit_history = getattr(self.datagroup, 'feffit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.fit_history):
            self.nfit = 0
        return self.fit_history[self.nfit]


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
        this = result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.wids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        result = self.get_fitresult()
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
        self.feffit_panel.update_start_values(result.params)

    def ShowDataSet(self, evt=None):
        dataset = evt.GetString()
        group = self.datasets.get(evt.GetString(), None)
        if group is not None:
            self.show_results(datagroup=group)

    def add_results(self, dgroup, form=None, larch_eval=None, show=True):
        name = dgroup.filename
        if name not in self.datalistbox.GetItems():
            self.datalistbox.Append(name)
        self.datasets[name] = dgroup
        if show:
            self.show_results(datagroup=dgroup, form=form, larch_eval=larch_eval)

    def show_results(self, datagroup=None, form=None, larch_eval=None):
        if datagroup is not None:
            self.datagroup = datagroup
        if larch_eval is not None:
            self.larch_eval = larch_eval

        datagroup = self.datagroup
        self.fit_history = getattr(self.datagroup, 'feffit_history', [])

        cur = self.get_fitresult()
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.fit_history):
            args = [res.label, "%.d" % (len(res.datasets[0].paths))]
            for attr in ('nvarys', 'n_independent', 'chi_square',
                         'chi2_reduced', 'rfactor', 'aic'):
                val = getattr(res, attr)
                if isinstance(val, int):
                    val = '%d' % val
                else:
                    val = gformat(val, 9)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))
        wids['data_title'].SetLabel(self.datagroup.filename)
        self.show_fitresult(nfit=0)


    def show_fitresult(self, nfit=0, datagroup=None):
        if datagroup is not None:
            self.datagroup = datagroup

        result = self.get_fitresult(nfit=nfit)

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

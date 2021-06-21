import time
import os
import ast
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
from lmfit.printfuncs import gformat, CORREL_HEAD

from larch import Group, site_config
from larch.math import index_of
from larch.fitting import group2params, param
from larch.utils.jsonutils import encode4js, decode4js
from larch.io.export_modelresult import export_modelresult

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, TextCtrl,
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
FitSpace_Choices = {'R space': 'R', 'k space': 'k', 'wavelet': 'w'}
FitPlot_Choices = {'K and R space': 'k+r', 'R space only': 'r'}


chik    = '\u03c7(k)'
chirmag = '|\u03c7(R)|'
chirre  = 'Re[\u03c7(R)]'
chirmr  = '|\u03c7(R)| + Re[\u03c7(R)]'
# wavelet = 'EXAFS wavelet'
noplot  = '<no plot>'

PlotOne_Choices = [chirmag, chik, chirre, chirmr]
PlotAlt_Choices = [noplot] + PlotOne_Choices


FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

ScriptWcards = "Fit Models(*.lar)|*.lar|All files (*.*)|*.*"
PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['feffit_params_init'] = """# create feffit parameters
_feffit_params = param_group(s02=param(1.0, min=0, vary=True),
                             e0=param(0, min=-25, max=25, vary=True))
_paths = {}

"""
COMMANDS['feffit_trans'] = """
_feffit_trans = feffit_transform(kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.4f}, kw={kwstring:s},
                      window='{kwindow:s}', fitspace='{fitspace:s}', rmin={rmin:.3f}, rmax={rmax:.3f})
"""
COMMANDS['add_path'] = """
_paths['{title:s}'] = feffpath('{fullpath:s}',
                     label='{label:s}',   degen=1,
                     s02='{amp:s}',       e0='{e0:s}',
                     deltar='{delr:s}',   sigma2='{sigma2:s}',   c3='{c3:s}')
"""


COMMANDS['pathlist'] = "_pathlist  = {pathlist:s}"
COMMANDS['ff2chi']   = "_pathsum = ff2chi(_pathlist, paramgroup=_feffit_params)"

COMMANDS['do_feffit'] = """# build feffit dataset, run feffit
_feffit_dataset  = feffit_dataset(data={groupname:s}, transform=_feffit_trans,
                                  pathlist=_feffit_trans)
_feffit_result = feffit(_feffit_params, _feffit_dataset)

"""

defaults = dict(e=None, elo=-10, ehi=-5, emin=-40, emax=0, yarray='norm')

def get_xlims(x, xmin, xmax):
    xeps = min(np.diff(x))/ 5.
    i1 = index_of(x, xmin + xeps)
    i2 = index_of(x, xmax + xeps) + 1
    return i1, i2



class FeffitParamsPanel(wx.Panel):
    def __init__(self, parent=None, _larch=None, feffit_panel=None, **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 450))
        self.larch = _larch
        self.feffit_panel = feffit_panel
        self.parwids = {}
        spanel = scrolled.ScrolledPanel(self)

        panel = self.panel = GridPanel(spanel, ncols=8, nrows=30, pad=1, itemstyle=LEFT)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=wx.ALIGN_LEFT, **kws)

        panel.Add(SLabel("Feffit Parameters ", colour='#0000AA', size=(200, -1)), dcol=2)
        panel.Add(Button(panel, 'Edit Parameters', action=self.onEditParams),
                  dcol=2)
        self.fix_unused = Check(panel, default=True,
                                 label="'Fix' unused variables for fit", size=(200, -1))
        panel.Add(self.fix_unused, dcol=4)

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

    def update(self):
        pargroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pargroup is None:
            self.feffit_panel.larch_eval(COMMANDS['feffit_params_init'])
            pargroup = getattr(self.larch.symtable, '_feffit_params')

        params = group2params(pargroup)
        for pname, par in params.items():
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
        pargroup = getattr(self.larch.symtable, '_feffit_params', None)
        print('edit params ' , pargroup)


    def RemoveParams(self, event=None, name=None):
        if name is None:
            return
        pargroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pargroup is None:
            return

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



class FeffPathPanel(wx.Panel):
    """Feff Path """
    def __init__(self, parent=None, feffdat_file=None, dirname=None,
                 fullpath=None, absorber=None, edge=None, reff=None,
                 degen=None, geom=None, npath=1, title='', user_label='',
                 _larch=None, feffit_panel=None, **kws):

        self.parent = parent
        self.title = title
        self.feffit_panel = feffit_panel
        wx.Panel.__init__(self, parent, -1, size=(550, 450))
        panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.feffdat_file = feffdat_file
        self.fullpath = fullpath

        self.reff = reff = float(reff)
        degen = float(degen)
        self.geom = geom
        self._larch = _larch

        self.wids = wids = {}
        delr = 'delr' if npath == 1 else f'delr_{npath:d}'
        sigma2  = 'sigma2' if npath == 1 else f'sigma2_{npath:d}'

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=wx.ALIGN_LEFT, **kws)

        def make_parwid(name, expr):
            wids[name] = TextCtrl(panel, expr, size=(250, -1),
                                  action=partial(self.onExpression, name=name))
            wids[name+'_val'] = SimpleText(panel, '', size=(150, -1))

        make_parwid('label', user_label)
        make_parwid('amp',  f'{degen:.1f} * s02')
        make_parwid('e0',  'e0')
        make_parwid('delr',  delr)
        make_parwid('sigma2',  sigma2)
        make_parwid('c3',  '')
        wids['use'] = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        wids['del'] = Button(panel, 'Remove This Path', size=(150, -1),
                             action=self.onRemovePath)

        title1 = f'{dirname:s}: {feffdat_file:s}  {absorber:s} {edge:s} edge'
        title2 = f'Reff={reff:.4f},  Degen={degen:.1f}   {geom:s}'

        panel.Add(SLabel(title1, size=(375, -1), colour='#0000AA'),
                  dcol=2,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['use'])
        panel.Add(wids['del'])
        panel.Add(SLabel(title2, size=(375, -1)),
                  dcol=3, style=wx.ALIGN_LEFT, newrow=True)

        panel.AddMany((SLabel('Label'),     wids['label']),                  newrow=True)
        panel.AddMany((SLabel('Amplitude'), wids['amp'],    wids['amp_val']), newrow=True)
        panel.AddMany((SLabel('E0 '),       wids['e0'],     wids['e0_val']),  newrow=True)
        panel.AddMany((SLabel('Delta R'),   wids['delr'],   wids['delr_val']), newrow=True)
        panel.AddMany((SLabel('sigma2'),    wids['sigma2'], wids['sigma2_val']), newrow=True)
        panel.AddMany((SLabel('C3'),        wids['c3'],     wids['c3_val']),   newrow=True)
        panel.pack()
        sizer= wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(self, sizer)

    def get_expressions(self):
        out = {'use': self.wids['use'].IsChecked()}
        for key in ('label', 'amp', 'e0', 'delr', 'sigma2', 'c3'):
            val = self.wids[key].GetValue().strip()
            if len(val) == 0: val = '0'
            out[key] = val
        return out

    def onExpression(self, event=None, name=None):
        if name in (None, 'label'):
            return
        expr = self.wids[name].GetValue().strip()
        if len(expr) < 1:
            return
        opts= dict(value=1.e-3, minval=None, maxval=None)
        if name == 'sigma2':
            opts['minval'] = 0
            opts['value'] = np.sqrt(self.reff)/200.0
        elif name == 'amp':
            opts['value'] = 1
        self.feffit_panel.update_params_for_expr(expr, **opts)

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



class FeffitResultFrame(wx.Frame):
    config_sect = 'feffit'
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):
        wx.Frame.__init__(self, None, -1, title='Feffit Results',
                          style=FRAMESTYLE, size=(900, 700), **kws)
        self.peakframe = peakframe
        self.datagroup = datagroup
        feffit = getattr(datagroup, 'feffit', None)
        self.fit_history = getattr(feffit, 'fit_history', [])


class FeffitPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='fefft_config',
                           title='Feff Fitting of EXAFS Paths',
                           config=defaults, **kws)
        self.paths_data = {}

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        try:
            pargroup = getattr(self.larch.symtable, '_feffit_params', None)
            if pargroup is None:
                self.larch_eval(COMMANDS['feffit_params_init'])
                pargroup = getattr(self.larch.symtable, '_feffit_params')

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
        self.paths_nb = flatnotebook(self, {})

        self.params_panel = FeffitParamsPanel(parent=self.paths_nb,
                                              _larch=self.larch,
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

        wids['plot_paths'] = Check(pan, default=True, label='Plot Each Path'
                                   , size=(125, -1), action=self.onPlot)
        wids['plot_ftwindows'] = Check(pan, default=False, label='Plot FT Windows'
                                   , size=(125, -1), action=self.onPlot)
        wids['plotone_op'] = Choice(pan, choices=PlotOne_Choices,
                                    action=self.onPlot, size=(125, -1))

        wids['plotalt_op'] = Choice(pan, choices=PlotAlt_Choices,
                                    action=self.onPlot, size=(125, -1))

        wids['plot_voffset'] = FloatSpin(pan, value=0, digits=2, increment=0.25,
                                         action=self.onPlot)

        wids['plot_current']  = Button(pan,'Plot Current Model',
                                     action=self.onPlot,  size=(125, -1))
        wids['do_fit']       = Button(pan, 'Fit Current Group',
                                      action=self.onFitModel,  size=(125, -1))
        wids['do_fit'].Disable()

        wids['do_fit_sel']= Button(pan, 'Fit Selected Groups',
                                   action=self.onFitSelected,  size=(125, -1))
        wids['do_fit_sel'].Disable()

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

        pan.Add(wids['do_fit'], dcol=2, newrow=True)
        pan.Add(wids['do_fit_sel'], dcol=2)
        pan.Add((5, 5), newrow=True)

        pan.Add(HLine(self, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(self.paths_nb,  1, LEFT|wx.GROW, 5)

        pack(self, sizer)

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, 'feffit_config', {})
        if 'kmin' not in conf:
            conf = defaults

        dgroup.feffit_config = conf
        if not hasattr(dgroup, 'feffit'):
            dgroup.feffit = Group()

        return conf

    def fill_form(self, dat):
        if isinstance(dat, Group):
            if not hasattr(dat, 'chi'):
                self.xasmain.process_exafs(dat)
            if hasattr(dat, 'feffit'):
                self.wids['ffit_kmin'].SetValue(dat.feffit.kmin)
                self.wids['ffit_kmax'].SetValue(dat.feffit.kmax)
                self.wids['ffit_rmin'].SetValue(dat.feffit.rmin)
                self.wids['ffit_rmax'].SetValue(dat.feffit.rmax)
                self.wids['ffit_dk'].SetValue(dat.feffit.dk)
        elif isinstance(dat, dict):
            # self.wids['ppeak_e0'].SetValue(dat['e0'])
            self.wids['ppeak_emin'].SetValue(dat['emin'])
            self.wids['ppeak_emax'].SetValue(dat['emax'])
            self.wids['ppeak_elo'].SetValue(dat['elo'])
            self.wids['ppeak_ehi'].SetValue(dat['ehi'])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        form_opts = {'datagroup': dgroup}
        wids = self.wids
        form_opts['kmin'] = wids['ffit_kmin'].GetValue()
        form_opts['kmax'] = wids['ffit_kmax'].GetValue()
        form_opts['dk']   = wids['ffit_dk'].GetValue()
        form_opts['rmin'] = wids['ffit_rmin'].GetValue()
        form_opts['rmax'] = wids['ffit_rmax'].GetValue()
        form_opts['kwstring'] = KWeight_Choices[wids['ffit_kweight'].GetStringSelection()]
        form_opts['fitspace'] = FitSpace_Choices[wids['ffit_fitspace'].GetStringSelection()]

        form_opts['kwindow']    = wids['ffit_kwindow'].GetStringSelection()
        form_opts['plot_ftwindow'] = wids['plot_ftwindows'].IsChecked()
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


    def onPlot(self, evt=None):
        opts = self.read_form()
        try:
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group()
        except:
            gname  = dgroup = None

        self.build_fitmodel(dgroup)

        plot1 = opts['plotone_op']
        plot2 = opts['plotalt_op']
        cmds = []

        ftargs = dict(kmin=opts['kmin'], kmax=opts['kmax'], dk=opts['dk'],
                      window=opts['kwindow'], rmin=opts['rmin'],
                      rmax=opts['rmax'], dr=opts.get('dr', 0.1))

        if ',' in opts['kwstring']:
            kw = int(opts['kwstring'].replace('[','').replace(']','').split(',')[0])
        else:
            kw = int(opts['kwstring'])

        ftargs['kweight'] = kw
        xftfcmd = "xftf({pathgroup:s}, kmin={kmin:.3f}, kmax={kmax:.3f}, dk={dk:.3f}, kweight={kweight:.3f}, window='{window:s}')"

        xftrcmd = "xftr({pathgroup:s}, rmin={rmin:.3f}, rmax={rmax:.3f}, dr={dr:.3f}, window='hanning')"
        cmds.append(xftfcmd.format(pathgroup='_pathsum', **ftargs))
        cmds.append(xftrcmd.format(pathgroup='_pathsum', **ftargs))

        if opts['plot_paths']:
            for path in self.pathlist:
                cmds.append(f"path2chi({path:s}, paramgroup=_feffit_params)")
                cmds.append(xftfcmd.format(pathgroup=path, **ftargs))

        self.larch_eval('\n'.join(cmds))
        with_win = opts['plot_ftwindow']

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
            if dgroup is not None:
                cmds.append(f"{pcmd}({gname}, label='data'{pextra}, title='sum of path', new=True)")
                cmds.append(f"{pcmd}(_pathsum, label='Path sum'{pextra}, show_win={with_win}, new=True)")
            else:
                cmds.append(f"{pcmd}(_pathsum, label='Path sum'{pextra}, title='sum of paths', show_window={with_win}, new=True)")
            if opts['plot_paths']:
                voff = opts['plot_voffset']
                for i, path in enumerate(self.pathlist):
                    plabel = path.replace('_paths', '').replace('[', '').replace(']', '')
                    cmds.append(f"{pcmd}({path}, label={plabel:s}{pextra}, offset={i*voff}, show_window=False, new=False)")

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
        title = '>'.join(atoms) + "%.2f" % (0.01*round(100*pathinfo.reff))
        if title in self.paths_data:
            btitle = title
            i = -1
            while title in self.paths_data:
                i += 1
                title = btitle + '_%s' % string.ascii_lowercase[i]

        self.paths_data[title] = (feffdat_file, feffresult.folder,
                                  feffresult.absorber, feffresult.edge,
                                  pathinfo)
        user_label = f'{title:s}, Reff={pathinfo.reff:.4f}'
        pathpanel = FeffPathPanel(parent=self.paths_nb, title=title,
                                  npath=len(self.paths_data),
                                  user_label=user_label,
                                  feffdat_file=fp_file, dirname=dirname,
                                  fullpath=feffdat_file,
                                  absorber=feffresult.absorber,
                                  edge=feffresult.edge, reff=pathinfo.reff,
                                  degen=pathinfo.degeneracy,
                                  geom=pathinfo.geom, _larch=self.larch,
                                  feffit_panel=self)

        self.paths_nb.AddPage(pathpanel, f' {title:s} ', True)

        for pname  in ('amp', 'e0', 'delr', 'sigma2', 'c3'):
            pathpanel.onExpression(name=pname)

        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

    def update_params_for_expr(self, expr=None, value=1.e-3,
                               minval=None, maxval=None):
        if expr is None:
            return

        pargroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pargroup is None:
            self.larch_eval(COMMANDS['feffit_params_init'])
            pargroup = getattr(self.larch.symtable, '_feffit_params')

        symtable =  pargroup.__params__._asteval.symtable
        extras= ''
        if minval is not None:
            extras = f', min={minval}'
        if maxval is not None:
            extras = f'{extras}, max={maxval}'

        for node in ast.walk(ast.parse(expr)):
            if isinstance(node, ast.Name):
                sym = node.id
                if sym not in symtable:
                    #setattr(pargroup, sym, param(value, min=minval,
                    #                             max=maxval, vary=True))
                    s = f'_feffit_params.{sym:s} = param({value:.4f}, vary=True{extras:s})'
                    self.larch_eval(s)

        pargroup = getattr(self.larch.symtable, '_feffit_params', None)

        # should walk through all parameters and expressions
        # and make sure to set par.vary=False for unused symbols
        self.params_panel.update()



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
        for page in self.paths_nb.pagelist:
            if name in page.__class__.__name__.lower().strip():
                return page

    def build_fitmodel(self, groupname=None):
        """ use fit components to build model"""
        paths = []
        cmds = ["## set up feffit "]
        pargroup = getattr(self.larch.symtable, '_feffit_params', None)
        if pargroup is None:
            self.larch_eval(COMMANDS['feffit_params_init'])
            pargroup = getattr(self.larch.symtable, '_feffit_params')


        opts = self.read_form()
        cmds.append(COMMANDS['feffit_trans'].format(**opts))

        path_pages = {}
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)

        pathlist = []
        for title, pathdata in self.paths_data.items():
            if title not in path_pages:
                continue

            pdat = {'title': title, 'fullpath': pathdata[0], 'use':True}
            pdat.update(path_pages[title].get_expressions())
            if pdat['use']:
                cmds.append(COMMANDS['add_path'].format(**pdat))
                pathlist.append(f"_paths['{title:s}']")
        self.pathlist = pathlist

        paths_string = '[%s]' % (', '.join(pathlist))
        cmds.append(COMMANDS['pathlist'].format(pathlist=paths_string))
        cmds.append(COMMANDS['ff2chi'])
        self.larch_eval("\n".join(cmds))


    def find_unused_params(self, action='fix'):
        used_syms = []
        path_pages = {}
        for i in range(self.paths_nb.GetPageCount()):
            text = self.paths_nb.GetPageText(i).strip()
            path_pages[text] = self.paths_nb.GetPage(i)

        for title in self.paths_data:
            if title not in path_pages:
                continue
            exprs = path_pages[title].get_expressions()
            exprs.pop('use')
            exprs.pop('label')

            for expr in exprs:
                for node in ast.walk(ast.parse(expr)):
                    if isinstance(node, ast.Name):
                        sym = node.id
                        if sym not in used_syms:
                            used_syms.append(sym)

        print("current symbols: ",  used_syms)


#
#         if len(peaks) > 0:
#             denom = '+'.join([p[0] for p in peaks])
#             numer = '+'.join(["%s*%s "% p for p in peaks])
#             cmds.append("peakpars.add('fit_centroid', expr='(%s)/(%s)')" % (numer, denom))
#
#         cmds.extend(modcmds)
#         cmds.append(COMMANDS['prepfit'].format(group=dgroup.groupname,
#                                                user_opts=repr(opts)))
#

    def onFitSelected(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return

        opts = self.read_form()

        self.show_subframe('prepeak_result', PrePeakFitResultFrame,
                           datagroup=dgroup, peakframe=self)

        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        ngroups = len(groups)
        for igroup, gname in enumerate(groups):
            dgroup = self.controller.get_group(gname)
            if not hasattr(dgroup, 'norm'):
                self.xasmain.process_normalization(dgroup)
            self.build_fitmodel(gname)
            opts['group'] = opts['gname']
            self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))
            ppeaks = dgroup.prepeaks

            # add bkg_component to saved user options
            bkg_comps = []
            for label, comp in self.fit_components.items():
                if comp.bkgbox.IsChecked():
                    bkg_comps.append(label)
            opts['bkg_components'] = bkg_comps
            imin, imax = self.get_xranges(dgroup.xdat)
            cmds = ["## do peak fit for group %s / %s " % (gname, dgroup.filename) ]

            yerr_type = 'set_yerr_const'
            yerr = getattr(dgroup, 'yerr', None)
            if yerr is None:
                if hasattr(dgroup, 'norm_std'):
                    cmds.append("{group}.yerr = {group}.norm_std")
                    yerr_type = 'set_yerr_array'
                elif hasattr(dgroup, 'mu_std'):
                    cmds.append("{group}.yerr = {group}.mu_std/(1.e-15+{group}.edge_step)")
                    yerr_type = 'set_yerr_array'
                else:
                    cmds.append("{group}.yerr = 1")
            elif isinstance(dgroup.yerr, np.ndarray):
                    yerr_type = 'set_yerr_array'

            cmds.extend([COMMANDS[yerr_type], COMMANDS['dofit']])
            cmd = '\n'.join(cmds)
            self.larch_eval(cmd.format(group=dgroup.groupname,
                                       imin=imin, imax=imax,
                                       user_opts=repr(opts)))

            self.autosave_modelresult(self.larch_get("peakresult"))
            self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                         larch_eval=self.larch_eval,
                                                         show=igroup==ngroups-1)


    def onFitModel(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        opts = self.read_form()
        self.build_fitmodel(dgroup.groupname)

        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        ppeaks = dgroup.prepeaks

        # add bkg_component to saved user options
        bkg_comps = []
        for label, comp in self.fit_components.items():
            if comp.bkgbox.IsChecked():
                bkg_comps.append(label)
        opts['bkg_components'] = bkg_comps

        imin, imax = self.get_xranges(dgroup.xdat)

        cmds = ["## do peak fit: "]

        yerr_type = 'set_yerr_const'
        yerr = getattr(dgroup, 'yerr', None)
        if yerr is None:
            if hasattr(dgroup, 'norm_std'):
                cmds.append("{group}.yerr = {group}.norm_std")
                yerr_type = 'set_yerr_array'
            elif hasattr(dgroup, 'mu_std'):
                cmds.append("{group}.yerr = {group}.mu_std/(1.e-15+{group}.edge_step)")
                yerr_type = 'set_yerr_array'
            else:
                cmds.append("{group}.yerr = 1")
        elif isinstance(dgroup.yerr, np.ndarray):
                yerr_type = 'set_yerr_array'


        cmds.extend([COMMANDS[yerr_type], COMMANDS['dofit']])

        cmd = '\n'.join(cmds)
        self.larch_eval(cmd.format(group=dgroup.groupname,
                                   imin=imin, imax=imax,
                                   user_opts=repr(opts)))

        self.autosave_modelresult(self.larch_get("peakresult"))

        self.onPlot()
        self.show_subframe('prepeak_result', PrePeakFitResultFrame,
                                  datagroup=dgroup, peakframe=self)
        self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                     larch_eval=self.larch_eval)

    def update_start_values(self, params):
        """fill parameters with best fit values"""
        allparwids = {}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for name, parwids in comp.parwids.items():
                    allparwids[name] = parwids

        for pname, par in params.items():
            if pname in allparwids:
                allparwids[pname].value.SetValue(par.value)

    def autosave_modelresult(self, result, fname=None):
        """autosave model result to user larch folder"""
        confdir = os.path.join(site_config.user_larchdir, 'xas_viewer')
        if not os.path.exists(confdir):
            try:
                os.makedirs(confdir)
            except OSError:
                print("Warning: cannot create XAS_Viewer user folder")
                return
        if fname is None:
            fname = 'autosave.fitmodel'
        save_modelresult(result, os.path.join(confdir, fname))

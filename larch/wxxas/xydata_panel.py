#!/usr/bin/env python
"""
 uncategorized XY data Panel
"""
import time
import wx
import numpy as np

from functools import partial
from xraydb import guess_edge, atomic_number

from larch.utils import gformat, path_split
from larch.math import index_of
from larch.xafs.xafsutils import guess_energy_units

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         GridPanel, CEN, RIGHT, LEFT, plotlabels,
                         get_zoomlimits, set_zoomlimits)

from larch.utils.strutils import fix_varname, fix_filename, file2groupname

from larch.utils.physical_constants import ATOM_NAMES
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel, autoset_fs_increment, update_confval
from .config import (make_array_choice, EDGES, ATSYMS,
                     NNORM_CHOICES, NNORM_STRINGS, NORM_METHODS)

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', marker='None')
PLOTOPTS_2 = dict(style='short dashed', zorder=3, marker='None')
PLOTOPTS_D = dict(style='solid', zorder=2, side='right', marker='None')

# Plot_EnergyRanges = {'full X range': None }

PlotOne_Choices = {'XY Data': 'y',
                   'Scaled Data': 'ynorm',
                   'Derivative ': 'dydx',
                   'XY Data + Derivative': 'y+dydx',
                   'Scaled Data + Derivative': 'ynorm+dydx',
                   }

PlotSel_Choices = {'XY Data': 'y',
                   'Scaled Data': 'ynorm',
                   'Derivative': 'dydx'}

FSIZE = 120
FSIZEBIG = 175


class XYDataPanel(TaskPanel):
    """XY Data Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller, panel='xydata', **kws)

    def build_display(self):
        panel = self.panel
        self.wids = {}
        self.last_plot_type = 'one'

        trow = wx.Panel(panel)
        plot_sel = Button(trow, 'Plot Selected Groups', size=(175, -1),
                          action=self.onPlotSel)
        plot_one = Button(trow, 'Plot Current Group', size=(175, -1),
                          action=self.onPlotOne)

        self.plotsel_op = Choice(trow, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(300, -1))
        self.plotone_op = Choice(trow, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(300, -1))

        opts = {'digits': 2, 'increment': 0.05, 'value': 0, 'size': (FSIZE, -1)}
        plot_voff = self.add_floatspin('plot_voff', with_pin=False,
                                       parent=trow,
                                       action=self.onVoffset,
                                       max_val=10000, min_val=-10000,
                                       **opts)

        vysize, vxsize = plot_sel.GetBestSize()
        voff_lab = wx.StaticText(parent=trow, label='  Y Offset:', size=(80, vxsize),
                                 style=wx.RIGHT|wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)

        self.plotone_op.SetSelection(0)
        self.plotsel_op.SetSelection(1)

        tsizer = wx.GridBagSizer(3, 3)
        tsizer.Add(plot_sel,        (0, 0), (1, 1), LEFT, 2)
        tsizer.Add(self.plotsel_op, (0, 1), (1, 1), LEFT, 2)
        tsizer.Add(voff_lab,        (0, 2), (1, 1), RIGHT, 2)
        tsizer.Add(plot_voff,       (0, 3), (1, 1), RIGHT, 2)
        tsizer.Add(plot_one,       (1, 0), (1, 1), LEFT, 2)
        tsizer.Add(self.plotone_op, (1, 1), (1, 1), LEFT, 2)

        pack(trow, tsizer)

        scale = self.add_floatspin('scale', action=self.onSet_Scale,
                                                digits=6, increment=0.05, value=1.0,
                                                size=(FSIZEBIG, -1))

        xshift = self.add_floatspin('xshift', action=self.onSet_XShift,
                                                digits=6, increment=0.05, value=0.0,
                                                size=(FSIZEBIG, -1))

        self.wids['is_frozen'] = Check(panel, default=False, label='Freeze Group',
                                       action=self.onFreezeGroup)

        use_auto = Button(panel, 'Use Default Settings', size=(200, -1),
                          action=self.onUseDefaults)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))

        copy_all = Button(panel, 'Copy All Parameters', size=(200, -1),
                          action=partial(self.onCopyParam, 'all'))

        add_text = self.add_text
        HLINEWID = 700

        panel.Add(SimpleText(panel, 'XY Data, General',
                             size=(650, -1), **self.titleopts), style=LEFT, dcol=4)
        panel.Add(trow, dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)

        add_text('XY Data:')
        panel.Add(use_auto, dcol=1)
        panel.Add(SimpleText(panel, 'Copy to Selected Groups:'), style=RIGHT, dcol=2)

        add_text('Scale Factor:')
        panel.Add(scale)
        panel.Add(SimpleText(panel, 'Scaled Data = Y /(Scale Factor)'))
        panel.Add(CopyBtn('scale'), dcol=1, style=RIGHT)

        add_text('Shift X scale:' )
        panel.Add(xshift)
        panel.Add(CopyBtn('xshift'), dcol=2, style=RIGHT)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)
        panel.Add(self.wids['is_frozen'], newrow=True)
        panel.Add(copy_all, dcol=3, style=RIGHT)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(panel, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        pack(self, sizer)

    def get_config(self, dgroup=None):
        """custom get_config"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return self.get_defaultconfig()
        self.read_form()

        defconf = self.get_defaultconfig()
        conf = getattr(dgroup.config, self.configname, defconf)

        for k, v in defconf.items():
            if k not in conf:
                conf[k] = v

        fname = getattr(dgroup, 'filename', None)
        if fname is None:
            fname = getattr(dgroup, 'groupname', None)
            if fname is None:
                fname =file2groupname('unknown_group',
                                      symtable=self._larch.symtable)

        for attr in ('scale', 'xshift'):
            conf[attr] = getattr(dgroup, attr, conf[attr])

        setattr(dgroup.config, self.configname, conf)
        return conf

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True

        self.plotone_op.SetChoices(list(PlotOne_Choices.keys()))
        self.plotsel_op.SetChoices(list(PlotSel_Choices.keys()))

        self.wids['scale'].SetValue(opts['scale'])
        self.wids['xshift'].SetValue(opts['xshift'])

        frozen = opts.get('is_frozen', False)
        frozen = getattr(dgroup, 'is_frozen', frozen)

        self.wids['is_frozen'].SetValue(frozen)
        self._set_frozen(frozen)
        wx.CallAfter(self.unset_skip_process)

    def unset_skip_process(self):
        self.skip_process = False

    def read_form(self):
        "read form, return dict of values"
        form_opts = {}
        form_opts['scale'] = self.wids['scale'].GetValue()
        form_opts['xshift'] = self.wids['xshift'].GetValue()
        return form_opts


    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass

        for wattr in ('scale',):
            self.wids[wattr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())

    def onPlotEither(self, evt=None):
        if self.last_plot_type == 'multi':
            self.onPlotSel(evt=evt)
        else:
            self.onPlotOne(evt=evt)

    def onPlotOne(self, evt=None):
        self.last_plot_type = 'one'
        self.plot(self.controller.get_group())
        wx.CallAfter(self.controller.set_focus)

    def onVoffset(self, evt=None):
        time.sleep(0.002)
        wx.CallAfter(self.onPlotSel)

    def onPlotSel(self, evt=None):
        newplot = True
        self.last_plot_type = 'multi'
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        groupname = self.controller.file_groups[str(last_id)]
        dgroup = self.controller.get_group(groupname)

        plot_choices = PlotSel_Choices

        ytitle = self.plotsel_op.GetStringSelection()
        yarray_name = plot_choices.get(ytitle, 'ynorm')
        ylabel = getattr(plotlabels, yarray_name, ytitle)
        xlabel = getattr(dgroup, 'plot_xlabel', getattr(plotlabels, 'xplot'))

        voff = self.wids['plot_voff'].GetValue()
        plot_traces = []
        newplot = True
        plotopts = self.controller.get_plot_conf()
        popts = {'style': 'solid', 'marker': None}
        popts['linewidth'] = plotopts.pop('linewidth')
        popts['marksize'] = plotopts.pop('markersize')
        popts['grid'] = plotopts.pop('show_grid')
        popts['fullbox'] = plotopts.pop('show_fullbox')

        for ix, checked in enumerate(group_ids):
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if dgroup is None:
                continue
            trace = {'xdata': dgroup.xplot,
                     'ydata': getattr(dgroup, yarray_name) + ix*voff,
                     'label': dgroup.filename, 'new': newplot}
            trace.update(popts)
            plot_traces.append(trace)
            newplot = False

        ppanel = self.controller.get_display(stacked=False).panel
        zoom_limits = get_zoomlimits(ppanel, dgroup)

        nplot_traces = len(ppanel.conf.traces)
        nplot_request = len(plot_traces)
        if nplot_request > nplot_traces:
            linecolors = ppanel.conf.linecolors
            ncols = len(linecolors)
            for i in range(nplot_traces, nplot_request+5):
                ppanel.conf.init_trace(i,  linecolors[i%ncols], 'dashed')


        ppanel.plot_many(plot_traces, xlabel=plotlabels.xplot, ylabel=ylabel,
                         zoom_limits=zoom_limits, show_legend=True)
        set_zoomlimits(ppanel, zoom_limits) or ppanel.unzoom_all()
        ppanel.canvas.draw()
        wx.CallAfter(self.controller.set_focus)

    def onUseDefaults(self, evt=None):
        self.wids['scale'].SetValue(1.0)
        self.wids['xshift'].SetValue(0.0)


    def onCopyAuto(self, evt=None):
        opts = dict(scale=1)
        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not getattr(grp, 'is_frozen', False):
                self.update_config(opts, dgroup=grp)
                self.fill_form(grp)
                self.process(grp, force=True)


    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())


    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        form = self.read_form()
        conf.update(form)
        dgroup = self.controller.get_group()
        self.update_config(conf)
        self.fill_form(dgroup)
        opts = {}
        name = str(name)
        def copy_attrs(*args):
            for a in args:
                opts[a] = conf[a]
        if name == 'all':
            copy_attrs('scale')
        elif name == 'scale':
            copy_attrs('scale')

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not getattr(grp, 'is_frozen', False):
                self.update_config(opts, dgroup=grp)
                for key, val in opts.items():
                    if hasattr(grp, key):
                        setattr(grp, key, val)
                self.fill_form(grp)
                self.process(grp, force=True)

    def onSet_Scale(self, evt=None, value=None):
        "handle setting scale"
        scale = self.wids['scale'].GetValue()
        if scale < 0:
            self.wids['scale'].SetValue(abs(scale))
        self.update_config({'scale': self.wids['scale'].GetValue()})
        autoset_fs_increment(self.wids['scale'], abs(scale))
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onSet_XShift(self, evt=None, value=None):
        "handle x shift"
        xshift = self.wids['xshift'].GetValue()
        self.update_config({'xshift': self.wids['xshift'].GetValue()})
        autoset_fs_increment(self.wids['xshift'], abs(xshift))
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def pin_callback(self, opt='__', xsel=None, relative_e0=True, **kws):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if xsel is None or opt not in self.wids:
            return
        if opt == 'scale':
            self.wids['scale'].SetValue(kws['ysel'])
        elif opt == 'xshift':
            self.wids['xshift'].SetValue(kws['xsel'])
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onReprocess(self, evt=None, value=None, **kws):
        "handle request reprocess"
        if self.skip_process:
            return
        try:
            dgroup = self.controller.get_group()
        except TypeError:
            return
        if not hasattr(dgroup.config, self.configname):
            return
        form = self.read_form()
        self.process(dgroup=dgroup)
        if self.stale_groups is not None:
            for g in self.stale_groups:
                self.process(dgroup=g, force=True)
            self.stale_groups = None
        self.onPlotEither()


    def process(self, dgroup=None, force_mback=False, force=False, use_form=True, **kws):
        """ handle process (pre-edge/normalize) of XAS data from XAS form
        """
        if self.skip_process and not force:
            return
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return

        self.skip_process = True
        conf = self.get_config(dgroup)
        form = self.read_form()
        if not use_form:
            form.update(self.get_defaultconfig())

        form['group'] = dgroup.groupname

        self.skip_process = False
        scale = form.get('scale', conf.get('scale', 1.0))
        xshift = form.get('xshift', conf.get('xshift', 0.0))
        gname = dgroup.groupname
        cmds = [f"{gname:s}.scale = {scale}",
                f"{gname:s}.xshift = {xshift}",
                f"{gname:s}.xplot = {gname:s}.x+{xshift}",
                f"{gname:s}.ynorm = {gname:s}.y/{scale}",
                f"{gname:s}.dydx  = gradient({gname:s}.ynorm)/gradient({gname:s}.xplot)",
                f"{gname:s}.d2ydx = gradient({gname:s}.dydx)/gradient({gname:s}.xplot)"]

        self.larch_eval('\n'.join(cmds))


        self.unset_skip_process()
        return


    def get_plot_arrays(self, dgroup):
        lab = plotlabels.ynorm
        if dgroup is None:
            return

        dgroup.plot_y2label = None
        dgroup.plot_xlabel = plotlabels.xplot
        dgroup.plot_yarrays = [('y', PLOTOPTS_1, lab)]

        req_attrs = ['y', 'i0', 'ynorm', 'dydx', 'd2ydx']
        pchoice = PlotOne_Choices.get(self.plotone_op.GetStringSelection(), 'ynorm')

        if pchoice in ('y', 'i0', 'ynorm', 'dydx', 'd2ydx'):
            lab = getattr(plotlabels, pchoice)
            dgroup.plot_yarrays = [(pchoice, PLOTOPTS_1, lab)]

        elif pchoice == 'y+dydx':
            lab = plotlabels.y
            dgroup.plot_y2label = lab2 = plotlabels.dydx
            dgroup.plot_yarrays = [('y', PLOTOPTS_1, lab),
                                   ('dydx', PLOTOPTS_D, lab2)]
        elif pchoice == 'ynorm+dydx':
            lab = plotlabels.ynorm
            dgroup.plot_y2label = lab2 = plotlabels.dydx
            dgroup.plot_yarrays = [('ynorm', PLOTOPTS_1, lab),
                                   ('dydx', PLOTOPTS_D, lab2)]

        elif pchoice == 'ynorm+i0':
            lab = plotlabels.ynorm
            dgroup.plot_y2label = lab2 = plotlabels.i0
            dgroup.plot_yarrays = [('ynorm', PLOTOPTS_1, lab),
                                   ('i0', PLOTOPTS_D, lab2)]

        dgroup.plot_ylabel = lab
        needs_proc = False
        for attr in req_attrs:
            needs_proc = needs_proc or (not hasattr(dgroup, attr))

        if needs_proc:
            self.process(dgroup=dgroup, force=True)

        y4e0 = dgroup.yplot = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.y)
        dgroup.plot_extras = []

        popts = {'marker': 'o', 'markersize': 5,
                 'label': '_nolegend_',
                 'markerfacecolor': '#888',
                 'markeredgecolor': '#A00'}


    def plot(self, dgroup, title=None, plot_yarrays=None, yoff=0,
             delay_draw=True, multi=False, new=True, with_extras=True, **kws):

        if self.skip_plotting:
            return
        ppanel = self.controller.get_display(stacked=False).panel

        plotcmd = ppanel.oplot
        if new:
            plotcmd = ppanel.plot

        groupname = getattr(dgroup, 'groupname', None)
        if groupname is None:
            return

        if not hasattr(dgroup, 'xplot'):
            print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'dydx', None) is None or
             getattr(dgroup, 'd2ydx', None) is None or
             getattr(dgroup, 'ynorm', None) is None)):
            self.process(dgroup=dgroup)
        self.get_plot_arrays(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = self.controller.get_plot_conf()
        popts.update(kws)
        popts['grid'] = popts.pop('show_grid')
        popts['fullbox'] = popts.pop('show_fullbox')

        path, fname = path_split(dgroup.filename)
        if 'label' not in popts:
            popts['label'] = dgroup.plot_ylabel

        zoom_limits = get_zoomlimits(ppanel, dgroup)

        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label

        plot_choices = PlotSel_Choices

        if multi:
            ylabel = self.plotsel_op.GetStringSelection()
            yarray_name = plot_choices.get(ylabel, 'ynorm')

            if self.is_xasgroup(dgroup):
                ylabel = getattr(plotlabels, yarray_name, ylabel)
            popts['ylabel'] = ylabel

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        popts['show_legend'] = len(plot_yarrays) > 1
        narr = len(plot_yarrays) - 1

        _linewidth = popts['linewidth']
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel
            linewidht = _linewidth
            if 'linewidth' in popts:
                linewidth = popts.pop('linewidth')
            popts['delay_draw'] = delay_draw

            if yaname == 'i0' and not hasattr(dgroup, yaname):
                dgroup.i0 = np.ones(len(dgroup.xplot))
            plotcmd(dgroup.xplot, getattr(dgroup, yaname)+yoff, linewidth=linewidth, **popts)
            plotcmd = ppanel.oplot

        if with_extras and plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    xpopts = {'marker': 'o', 'markersize': 5,
                              'label': '_nolegend_',
                              'markerfacecolor': 'red',
                              'markeredgecolor': '#884444'}
                    xpopts.update(opts)
                    axes.plot([x], [y], **xpopts)
                elif etype == 'vline':
                    xpopts = {'ymin': 0, 'ymax': 1.0,
                              'label': '_nolegend_',
                              'color': '#888888'}
                    xpopts.update(opts)
                    axes.axvline(x, **xpopts)

        # set_zoomlimits(ppanel, zoom_limits)
        ppanel.reset_formats()
        set_zoomlimits(ppanel, zoom_limits)
        ppanel.conf.unzoom(full=True, delay_draw=False)

import os
import copy
import numpy as np

import larch
from larch.larchlib import read_config, save_config
from larch.utils import group2dict, unique_name, fix_varname
from larch.wxlib.plotter import last_cursor_pos
from larch.io import fix_varname
PLOTWIN_SIZE = (550, 550)

class XASController():
    """
    class holding the Larch session and doing the processing work for XAS GUI
    """
    config_file = 'xas_viewer.conf'
    def __init__(self, wxparent=None, _larch=None):
        self.wxparent = wxparent
        self.larch = _larch
        if self.larch is None:
            self.larch = larch.Interpreter()
        self.filelist = None
        self.file_groups = {}
        self.fit_opts = {}
        self.group = None
        self.plot_erange = None
        self.groupname = None
        self.report_frame = None
        self.symtable = self.larch.symtable

    def init_larch(self):
        _larch = self.larch
        old_config = read_config(self.config_file)

        config = self.make_default_config()
        for sname in config:
            if old_config is not None and sname in old_config:
                val = old_config[sname]
                if isinstance(val, dict):
                    config[sname].update(val)
                else:
                    config[sname] = val

        for key, value in config.items():
            setattr(self.larch.symtable._sys.xas_viewer, key, value)
        try:
            os.chdir(config['workdir'])
        except:
            pass

    def make_default_config(self):
        """ default config, probably called on first run of program"""
        config = {'chdir_on_fileopen': True,
                  'workdir': os.getcwd()}
        return config

    def get_config(self, key, default=None):
        "get configuration setting"
        confgroup = self.larch.symtable._sys.xas_viewer
        return getattr(confgroup, key, default)

    def save_config(self):
        """save configuration"""
        conf = group2dict(self.larch.symtable._sys.xas_viewer)
        conf.pop('__name__')
        save_config(self.config_file, conf)

    def set_workdir(self):
        self.larch.symtable._sys.xas_viewer.workdir = os.getcwd()

    def write_message(self, msg, panel=0):
        """write a message to the Status Bar"""
        self.wxparent.statusbar.SetStatusText(msg, panel)

    def close_all_displays(self):
        "close all displays, as at exit"
        self.symtable._plotter.close_all_displays()

    def get_display(self, win=1, stacked=False):
        wintitle='Larch XAS Plot Window %i' % win
        # if stacked:
        #     win = 2
        #    wintitle='Larch XAS Plot Window'
        opts = dict(wintitle=wintitle, stacked=stacked, win=win,
                    size=PLOTWIN_SIZE)
        out = self.symtable._plotter.get_display(**opts)
        if win > 1:
            p1 = getattr(self.symtable._plotter, 'plot1', None)
            if p1 is not None:
                try:
                    siz = p1.GetSize()
                    pos = p1.GetPosition()
                    pos[0] += int(siz[0]/4)
                    pos[1] += int(siz[1]/4)
                    out.SetSize(pos)
                    if not stacked:
                        out.SetSize(siz)
                except Exception:
                    pass
        return out

    def get_group(self, groupname=None):
        if groupname is None:
            groupname = self.groupname
            if groupname is None:
                return None
        dgroup = getattr(self.symtable, groupname, None)
        if dgroup is None and groupname in self.file_groups:
            groupname = self.file_groups[groupname]
            dgroup = getattr(self.symtable, groupname, None)
        return dgroup

    def filename2group(self, filename):
        "convert filename (as displayed) to larch group"
        return self.get_group(self.file_groups[str(filename)])

    def merge_groups(self, grouplist, master=None, yarray='mu', outgroup=None):
        """merge groups"""
        cmd = """%s = merge_groups(%s, master=%s,
        xarray='energy', yarray='%s', kind='cubic', trim=True)
        """
        glist = "[%s]" % (', '.join(grouplist))
        outgroup = fix_varname(outgroup.lower())
        if outgroup is None:
            outgroup = 'merged'

        outgroup = unique_name(outgroup, self.file_groups, max=1000)

        cmd = cmd % (outgroup, glist, master, yarray)
        self.larch.eval(cmd)

        if master is None:
            master = grouplist[0]
        this = self.get_group(outgroup)
        master = self.get_group(master)
        if not hasattr(this, 'xasnorm_config'):
            this.xasnorm_config = {}
        this.xasnorm_config.update(master.xasnorm_config)
        this.datatype = master.datatype
        this.xdat = 1.0*this.energy
        this.ydat = 1.0*getattr(this, yarray)
        this.yerr =  getattr(this, 'd' + yarray, 1.0)
        if yarray != 'mu':
            this.mu = this.ydat
        this.plot_xlabel = 'energy'
        this.plot_ylabel = yarray
        return outgroup

    def set_plot_erange(self, erange):
        self.plot_erange = erange

    def copy_group(self, filename, new_filename=None):
        """copy XAS group (by filename) to new group"""
        groupname = self.file_groups[filename]
        if not hasattr(self.larch.symtable, groupname):
            return

        ogroup = self.get_group(groupname)
        ngroup = larch.Group(datatype=ogroup.datatype, copied_from=groupname)
        for attr in dir(ogroup):
            do_copy = True
            if attr in ('xdat', 'ydat', 'i0', 'data' 'yerr',
                        'energy', 'mu'):
                val = getattr(ogroup, attr)*1.0
            elif attr in ('norm', 'flat', 'deriv', 'deconv',
                          'post_edge', 'pre_edge', 'norm_mback',
                          'norm_vict', 'norm_poly'):
                do_copy = False
            else:
                try:
                    val = copy.deepcopy(getattr(ogroup, attr))
                except ValueError:
                    do_copy = False
            if do_copy:
                setattr(ngroup, attr, val)

        if new_filename is None:
            new_filename = filename + '_1'
        ngroup.filename = unique_name(new_filename, self.file_groups.keys())
        ngroup.groupname = unique_name(groupname, self.file_groups.values())
        setattr(self.larch.symtable, ngroup.groupname, ngroup)
        return ngroup

    def get_cursor(self, win=None):
        """get last cursor from selected window"""
        return last_cursor_pos(win=win, _larch=self.larch)

    def plot_group(self, groupname=None, title=None, plot_yarrays=None,
                   new=True, zoom_out=True, **kws):
        ppanel = self.get_display(stacked=False).panel
        newplot = ppanel.plot
        oplot   = ppanel.oplot
        plotcmd = oplot
        viewlims = ppanel.get_viewlimits()
        if new:
            plotcmd = newplot

        dgroup = self.get_group(groupname)
        if not hasattr(dgroup, 'xdat'):
            print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None)):
            self.process(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = kws
        path, fname = os.path.split(dgroup.filename)
        if not 'label' in popts:
            popts['label'] = dgroup.plot_ylabel
        zoom_out = (zoom_out or
                  min(dgroup.xdat) >= viewlims[1] or
                  max(dgroup.xdat) <= viewlims[0] or
                  min(dgroup.ydat) >= viewlims[3] or
                  max(dgroup.ydat) <= viewlims[2])

        if not zoom_out:
            popts['xmin'] = viewlims[0]
            popts['xmax'] = viewlims[1]
            popts['ymin'] = viewlims[2]
            popts['ymax'] = viewlims[3]
           

        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        if hasattr(dgroup, 'custom_plotopts'):
            popts.update(dgroup.custom_plotopts)

        narr = len(plot_yarrays) - 1
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel
            popts['delay_draw'] = (i != narr)

            plotcmd(dgroup.xdat, getattr(dgroup, yaname), **popts)
            plotcmd = oplot

        if plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    popts = {'marker': 'o', 'markersize': 4,
                             'label': '_nolegend_',
                             'markerfacecolor': 'red',
                             'markeredgecolor': '#884444'}
                    popts.update(opts)
                    axes.plot([x], [y], **popts)
                elif etype == 'vline':
                    popts = {'ymin': 0, 'ymax': 1.0,
                             'color': '#888888'}
                    popts.update(opts)
                    axes.axvline(x, **popts)
        ppanel.canvas.draw()


import os
import copy
import time
import numpy as np
from copy import deepcopy

import larch
from larch.larchlib import read_config, save_config
from larch.utils import group2dict, unique_name, fix_varname, get_cwd, asfloat
from larch.wxlib.plotter import last_cursor_pos
from larch.io import fix_varname
from larch.site_config import home_dir, user_larchdir

from .config import XASCONF, CONF_FILE

class XASController():
    """
    class holding the Larch session and doing the processing work for XAS GUI
    """
    def __init__(self, wxparent=None, _larch=None):
        self.wxparent = wxparent
        self.larch = _larch
        if self.larch is None:
            self.larch = larch.Interpreter()
        self.symtable = self.larch.symtable
        self.file_groups = self.symtable._xasgroups = {}

        self.filelist = None
        self.group = None
        self.groupname = None
        self.plot_erange = None
        self.report_frame = None

        config = {}
        config.update(XASCONF)
        xasv_folder = os.path.join(user_larchdir, 'xas_viewer')
        if not os.path.exists(xasv_folder):
            try:
                os.mkdir(xasv_folder)
            except:
                print("cannot create directory ", xasv_folder)

        self.config_file = CONF_FILE
        if os.path.exists(xasv_folder):
            self.config_file = os.path.join(xasv_folder, CONF_FILE)

        if os.path.exists(self.config_file):
            user_config = read_config(self.config_file)
            if user_config is not None:
                for sname in config:
                    if sname in user_config:
                        val = user_config[sname]
                        if isinstance(val, dict):
                            for k, v in val.items():
                                config[sname][k] = v
                        else:
                            config[sname] = val

        self.config = self.larch.symtable._sys.xasviewer_config = config
        self.larch.symtable._sys.wx.plotopts = config['plot']

        self.init_workdir()

    def sync_xasgroups(self):
        "make sure `_xasgroups` is identical to file_groups"
        if self.file_groups != self.symtable._xasgroups:
            self.symtable._xasgroups = self.file_groups

    def get_config(self, key, default=None):
        "get top-level, program-wide configuration setting"
        if key not in self.config:
            return default
        return deepcopy(self.config[key])

    def init_group_config(self, dgroup):
        """set up 'config' group with values from self.config"""
        if not hasattr(dgroup, 'config'):
            dgroup.config = larch.Group(__name__='xas_viewer config')

        for sect in ('exafs', 'feffit', 'lincombo', 'pca', 'prepeaks',
                     'regression', 'xasnorm'):
            setattr(dgroup.config, sect, deepcopy(self.config[sect]))

    def get_plot_conf(self):
        """get basic plot options to pass to plot() ** not window sizes **"""
        dx = {'linewidth': 3, 'markersize': 4,
              'show_grid': True, 'show_fullbox': True, 'theme': 'light'}
        pconf = self.config['plot']
        out = {}
        for attr, val in dx.items():
            out[attr] = pconf.get(attr, val)
        return out

    def save_config(self):
        """save configuration"""
        save_config(self.config_file, self.config)

    def chdir_on_fileopen(self):
        return self.config['main']['chdir_on_fileopen']

    def set_workdir(self):
        self.config['main']['workdir'] = get_cwd()

    def save_workdir(self):
        """save last workdir"""
        xasv_folder = os.path.join(user_larchdir, 'xas_viewer')
        if os.path.exists(xasv_folder):
            try:
                with open(os.path.join(xasv_folder, 'workdir.txt'), 'w') as fh:
                    fh.write("%s\n" % get_cwd())
            except:
                pass

    def init_workdir(self):
        """set initial working folder"""
        if self.config['main'].get('use_last_workdir', False):
            wfile = os.path.join(user_larchdir, 'xas_viewer', 'workdir.txt')
            if os.path.exists(wfile):
                try:
                    with open(wfile, 'r') as fh:
                        workdir = fh.readlines()[0][:-1]
                        self.config['main']['workdir'] = workdir
                except:
                    pass
        try:
            os.chdir(self.config['main']['workdir'])
        except:
            pass


    def write_message(self, msg, panel=0):
        """write a message to the Status Bar"""
        self.wxparent.statusbar.SetStatusText(msg, panel)

    def close_all_displays(self):
        "close all displays, as at exit"
        self.symtable._plotter.close_all_displays()

    def get_display(self, win=1, stacked=False):
        wintitle='Larch XAS Plot Window %i' % win

        conf = self.get_config('plot')
        opts = dict(wintitle=wintitle, stacked=stacked, win=win)
        opts.update(conf)
        return self.symtable._plotter.get_display(**opts)


    def get_group(self, groupname=None):
        if groupname is None:
            groupname = self.groupname
            if groupname is None:
                return None
        dgroup = getattr(self.symtable, groupname, None)
        if dgroup is None and groupname in self.file_groups:
            groupname = self.file_groups[groupname]
            dgroup = getattr(self.symtable, groupname, None)

        if dgroup is None and len(self.file_groups) > 0:
            gname = list(self.file_groups.keys())[0]
            dgroup = getattr(self.symtable, gname, None)
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
        if not hasattr(master, 'config'):
            self.init_group_config(master)
        if not hasattr(this, 'config'):
            self.init_group_config(this)
        this.config.xasnorm.update(master.config.xasnorm)
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

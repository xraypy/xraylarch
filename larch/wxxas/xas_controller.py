import os
import time
import shutil
from glob import glob
from pathlib import Path
from copy import deepcopy
from threading import Thread

import numpy as np
import wx
import darkdetect

from pyshortcuts import fix_varname, get_cwd, uname
import larch
from larch import Group, Journal, Entry
from larch.larchlib import read_config, save_config
from larch.utils import (group2dict, unique_name,
                         get_sessionid, get_session_info,
                         asfloat, mkdir, unixpath)
from larch.wxlib.plotter import (last_cursor_pos,
                                 get_panel_plot_config, get_markercolors)
from larch.wxlib import ExceptionPopup
from larch.io import save_session
from larch.site_config import home_dir, user_larchdir

from .config import XASCONF, CONF_FILE,  OLDCONF_FILE, SESSION_LOCK


class XASController():
    """
    class holding the Larch session and doing the processing work for Larix
    """
    def __init__(self, wxparent=None, _larch=None):
        self.wxparent = wxparent
        self.filelist = None
        self.group = None
        self.groupname = None
        self.plot_erange = None
        self.report_frame = None
        self.saver_thread = None
        self.recentfiles = []
        self.panels = {}
        self.datagroup_callbacks = {}
        self.session_filename = None
        self.session_warn_overwrite = True
        self.session_name = None

        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()
        self.init_larch_session()
        self.init_workdir()

    def init_larch_session(self):
        self.symtable = self.larch.symtable
        self.file_groups = self.symtable._xasgroups = {}

        config = {}
        config.update(XASCONF)

        self.larix_folder = Path(user_larchdir, 'larix').absolute()

        # may migrate old 'xas_viewer' folder to 'larix' folder
        xasv_folder = Path(user_larchdir, 'xas_viewer').absolute()

        if xasv_folder.exists() and not self.larix_folder.exists():
            print("Migrating xas_viewer to larix folder")
            shutil.move(xasv_folder.as_posix(), self.larix_folder.as_posix())

        if not self.larix_folder.exists():
            try:
                mkdir(self.larix_folder)
            except Exception:
                title = "Cannot create Larix folder"
                message = [f"Cannot create directory {self.larix_folder}"]
                ExceptionPopup(self, title, message)

        # may migrate old 'xas_viewer.conf' file to 'larix.conf'
        old_config_file = Path(self.larix_folder, OLDCONF_FILE)
        if old_config_file.exists() and not self.config_file.exists():
            shutil.move(old_config_file.as_posix(), self.config_file.as_posix())

        self.config_file = Path(self.larix_folder, CONF_FILE)

        if self.config_file.exists():
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

        self.config = self.larch.symtable._sys.larix_config = config

        self.session_id = get_sessionid(extra=id(self))
        self.session_lockfile = f"{SESSION_LOCK}_{self.session_id}.dat"
        self.set_session_name()
        self.set_datatask_name()

        with open(Path(self.larix_folder, self.session_lockfile), 'w') as fh:
            fh.write(f"{get_session_info()}\n")
        self.clean_autosave_sessions()

    def set_session_name(self, name=None, warn_overwrite=True):
        if name not in ('', None):
            name = fix_varname(Path(name).stem)
            self.session_filename = f"{name}.larix"
            self.session_warn_overwrite = warn_overwrite
            self.session_name = name
            self.larch.symtable._sys.session_name = name
            self.wxparent.SetTitle(f"Larix [{name}]")
            menulab = f"&Save Larch Session [{name}.larix]\tCtrl+S"
            self.wxparent.save_session_menu.SetItemLabel(menulab)


    def set_datatask_name(self, name='task'):
        self.larch.symtable._sys.datatask_name = name

    def delete_lockfile(self):
        spath = Path(self.larix_folder, self.session_lockfile)
        if spath.exists():
            os.unlink(spath)

    def get_otherlockfiles(self):
        """return lock files not matching the current session"""
        this_session_info = get_session_info()
        lock_files = {}

        conf = self.get_config('autosave', {})
        autosave_fileroot = conf.get('fileroot', 'autosave')

        for fname in os.listdir(self.larix_folder):
            if fname.startswith(SESSION_LOCK) and self.session_id not in fname:
                sid = fname.replace(SESSION_LOCK, '').replace('_', '').replace('.dat','')
                asave = f"{autosave_fileroot:s}_{sid}.larix"
                asave = Path(self.larix_folder, asave)
                if asave.exists():
                    with open(Path(self.larix_folder, fname), 'r') as fh:
                        textlines = fh.readlines()
                    macid, pid = textlines[0].split()
                    lock_files[fname] = (asave, macid, pid)
        return lock_files

    def install_group(self, groupname, filename, source=None, journal=None):
        """add groupname / filename to list of available data groups"""

        try:
            thisgroup = getattr(self.symtable, groupname)
        except AttributeError:
            thisgroup = self.symtable.new_group(groupname)

        # file /group may already exist in list
        if filename in self.file_groups:
            fbase, i = filename, 0
            while i < 50000 and filename in self.file_groups:
                filename = f"{fbase}_{i}"
                i += 1
                if i >= 50000:
                    raise ValueError(f"Too many repeated filenames: {fbase}")

        filename = filename.strip()
        if source is None:
            source = filename

        jopts = f"source='{source}'"
        if isinstance(journal, dict):
            jnl =  {'source': f"{source}"}
            jnl.update(journal)
            jopts = ', '.join([f"{k}='{v}'" for k, v in jnl.items()])
        elif isinstance(journal, (list, Journal)):
            jopts = repr(journal)

        cmds = [f"{groupname:s}.groupname = {groupname:s}.__name__ = '{groupname:s}'",
                f"{groupname:s}.filename = '{filename:s}'"]
        needs_config = not hasattr(thisgroup, 'config')
        if needs_config:
            cmds.append(f"{groupname:s}.config = group(__name__='larix config')")

        cmds.append(f"{groupname:s}.journal = journal({jopts:s})")

        if not hasattr(thisgroup, 'xdat'):
            for xattr in ('x', 'xplot', 'energy', 'xdata'):
                if hasattr(thisgroup, xattr):
                    thisgroup.xdat = deepcopy(getattr(thisgroup, xattr))
                    break

        if not hasattr(thisgroup, 'ydat'):
            for yattr in ('y', 'yplot', 'mu', 'norm', 'ydata',
                          'munorm', 'mutrans', 'signal'):
                if hasattr(thisgroup, yattr):
                    thisgroup.ydat = deepcopy(getattr(thisgroup, yattr))
                    break

        if hasattr(thisgroup, 'xdat') and not hasattr(thisgroup, 'xplot'):
            thisgroup.xplot = deepcopy(thisgroup.xdat)
        if hasattr(thisgroup, 'ydat') and not hasattr(thisgroup, 'yplot'):
            thisgroup.yplot = deepcopy(thisgroup.ydat)

        datatype = getattr(thisgroup, 'datatype', 'xydata')
        if datatype == 'xas':
            cmds.append(f"{groupname:s}.energy_orig = {groupname:s}.energy[:]")
            array_labels = getattr(thisgroup, 'array_labels', [])
            if len(array_labels) > 2  and getattr(thisgroup, 'data', None) is not None:
                for i0name in ('i0', 'i_0', 'monitor'):
                    if i0name in array_labels:
                        i0x = array_labels.index(i0name)
                        cmds.append(f"{groupname:s}.i0 = {groupname:s}.data[{i0x}, :]")

        self.larch.eval('\n'.join(cmds))

        if needs_config:
            self.init_group_config(thisgroup)

        self.file_groups[filename] = groupname
        self.filelist.Append(filename)
        self.filelist.SetStringSelection(filename)
        self.sync_xasgroups()
        return filename

    def sync_xasgroups(self):
        """
        make sure the symbol `_xasgroups` is identical to file_groups and
        that these are correctly ordered using the list of the FileList
        """
        xgroup = {}
        curr = self.symtable._xasgroups
        for key in self.filelist.GetItems():
            xgroup[key] = self.file_groups.get(key, curr.get(key, None))
        self.symtable._xasgroups = self.file_groups = xgroup

    def get_config(self, key, default=None):
        "get top-level, program-wide configuration setting"
        if key not in self.config:
            return default
        return deepcopy(self.config[key])

    def init_group_config(self, dgroup):
        """set up 'config' group with values from self.config"""
        if not hasattr(dgroup, 'config'):
            dgroup.config = larch.Group(__name__='larix config')

        for sect in ('exafs', 'feffit', 'lincombo', 'pca', 'prepeaks',
                     'regression', 'xasnorm'):
            setattr(dgroup.config, sect, deepcopy(self.config[sect]))

    def save_config(self):
        """save configuration"""
        save_config(self.config_file, self.config, form='yaml')

    def chdir_on_fileopen(self):
        return self.config['main']['chdir_on_fileopen']

    def set_workdir(self):
        self.config['main']['workdir'] = get_cwd()

    def save_workdir(self):
        """save last workdir and recent session files"""
        try:
            with open(Path(self.larix_folder, 'workdir.txt'), 'w') as fh:
                fh.write(f"{get_cwd()}\n")
        except Exception:
            pass

        buffer = []
        rfiles = []
        for tstamp, fname in sorted(self.recentfiles, key=lambda x: x[0], reverse=True)[:10]:
            if fname not in rfiles:
                buffer.append(f"{tstamp:.1f} {fname}")
                rfiles.append(fname)
        buffer.append('')
        buffer = '\n'.join(buffer)

        try:
            with open(Path(self.larix_folder, 'recent_sessions.txt'), 'w') as fh:
                fh.write(buffer)
        except Exception:
            pass

    def init_workdir(self):
        """set initial working folder, read recent session files"""
        if self.config['main'].get('use_last_workdir', False):
            wfile = Path(self.larix_folder, 'workdir.txt')
            if wfile.exists():
                try:
                    with open(wfile, 'r') as fh:
                        workdir = fh.readlines()[0][:-1]
                        self.config['main']['workdir'] = workdir
                except Exception:
                    pass
            try:
                os.chdir(self.config['main']['workdir'])
            except Exception:
                pass

        rfile = Path(self.larix_folder, 'recent_sessions.txt')
        if rfile.exists():
            with open(rfile, 'r') as fh:
                for line in fh.readlines():
                    if len(line) < 2 or line.startswith('#'):
                        continue
                    try:
                        w = line[:-1].split(None, maxsplit=1)
                        self.recentfiles.insert(0, (float(w[0]), w[1]))
                    except Exception:
                        pass

    def register_group_callback(self, label, obj, callback):
        self.datagroup_callbacks[label] = (obj, callback)

    def unregister_group_callback(self, label):
        if label in self.datagroup_callbacks:
            self.datagroup_callbacks.pop(label)

    def run_group_callbacks(self):
        "run callbacks for group changes, checking that objects are still alive"
        missing = []
        for key, val in self.datagroup_callbacks.items():
            try:
                obj, cb = val
                obj.Raise()
                cb()
            except Exception:
                missing.append(key)
        for key in missing:
            self.unregister_group_callback(key)

    def autosave_session(self, use_thread=True):
        conf = self.get_config('autosave', {})
        fileroot = conf.get('fileroot', 'autosave')
        nhistory = max(12, int(conf.get('nhistory', 2)))
        if self.saver_thread is not None:
            i = 0
            while self.saver_thread.is_alive():
                i += 1
                time.sleep(0.1)
                self.saver_thread.join()
                if i > 150:
                    break

        fname =  f"{fileroot:s}_{self.session_id}.larix"
        savefile = Path(self.larix_folder, fname).as_posix()
        for i in reversed(range(1, nhistory)):
            curf = savefile.replace('.larix', f'_{i:d}.larix' )
            if Path(curf).exists():
                newf = savefile.replace('.larix', f'_{i+1:d}.larix' )
                shutil.move(curf, newf)
        if Path(savefile).exists():
            curf = savefile.replace('.larix', '_1.larix' )
            shutil.move(savefile, curf)
        self.sync_xasgroups()
        if use_thread:
            self.saver_thread = Thread(target=save_session, args=(savefile,),
                                       kwargs={'_larch': self.larch})
            self.saver_thread.start()
        else:
            save_session(savefile, _larch=self.larch)
        time.sleep(0.25)

        return savefile

    def clean_autosave_sessions(self):
        conf = self.get_config('autosave', {})
        fileroot = conf.get('fileroot', 'autosave')
        max_hist = int(conf.get('maxfiles', 10))

        def get_autosavefiles():
            dat = []
            for afile in os.listdir(self.larix_folder):
                ffile = Path(self.larix_folder, afile)
                if afile.endswith('.larix'):
                    mtime = os.stat(ffile).st_mtime
                    words = afile.replace('.larix', '').split('_')
                    try:
                        version = int(words[-1])
                        words.pop()
                    except Exception:
                        version = 0
                    dat.append((ffile.as_posix(), version, mtime))
            return sorted(dat, key=lambda x: x[2])

        dat = get_autosavefiles()
        nremove = max(0, len(dat) - max_hist)
        # first remove oldest "version > 0" files
        while nremove > 0 and len(dat) > 0:
            dfile, version, mtime = dat.pop(0)
            if version > 0:
                os.unlink(dfile)
                nremove -= 1

        dat = get_autosavefiles()
        nremove = max(0, len(dat) - max_hist)
        # then remove the oldest "version 0" files

        while nremove > 0 and len(dat) > 0:
            dfile, vers, mtime = dat.pop(0)
            if vers == 0 and abs(mtime - time.time()) > 86400:
                os.unlink(dfile)
            nremove -= 1

        # remove lockfiles without an autosave session file
        this_session_info = get_session_info()
        stale_lock_files = []
        for fname in os.listdir(self.larix_folder):
            if fname.startswith(SESSION_LOCK) and self.session_id not in fname:
                sid = fname.replace(SESSION_LOCK, '').replace('_', '').replace('.dat','')
                asave = f"{fileroot:s}_{sid}.larix"
                if not Path(self.larix_folder, asave).exists():
                    stale_lock_files.append(Path(self.larix_folder, fname))
        # print("clean stale lock files ", stale_lock_files)
        for fname in stale_lock_files:
            os.unlink(fname)



    def get_recentfiles(self, max=10):
        return sorted(self.recentfiles, key=lambda x: x[0], reverse=True)[:max]

    def recent_autosave_sessions(self):
        "return list of (timestamp, name) for most recent autosave session files"
        conf = self.get_config('autosave', {})
        fileroot = conf.get('fileroot', 'autosave')
        max_hist = int(conf.get('maxfiles', 10))
        flist = []
        for afile in os.listdir(self.larix_folder):
            ffile = Path(self.larix_folder, afile).as_posix()
            if ffile.endswith('.larix'):
                flist.append((os.stat(ffile).st_mtime, ffile))

        return sorted(flist, key=lambda x: x[0], reverse=True)[:max_hist]

    def clear_session(self):
        self.larch.eval("clear_session()")
        self.filelist.Clear()
        self.init_larch_session()

    def save_exafsplot_config(self, options):
        exconf_path = Path(user_larchdir, 'larix', 'larix_exafsplots.conf')
        save_config(exconf_path, options, form='yaml')

    def load_exafsplot_config(self):
        plot_conf = Path(user_larchdir, 'larix', 'larix_exafsplots.conf')
        conf = {}
        if plot_conf.exists():
            conf = read_config(plot_conf)
        return conf

    def write_message(self, msg, panel=0):
        """write a message to the Status Bar"""
        self.wxparent.statusbar.SetStatusText(msg, panel)

    def close_all_displays(self):
        "close all displays, as at exit"
        self.symtable._plotter.close_all_displays()

    def get_display(self, win=1, stacked=False,
                    size=None, position=None):
        wintitle='Larch XAS Plot Window %i' % win
        return self.symtable._plotter.get_display(
                     wintitle=wintitle, stacked=stacked,
                     size=size, position=position, win=win)

    def set_focus(self, topwin=None):
        """
        set wx focus to main window or selected Window,
        even after plot
        """
        if topwin is None:
            topwin = wx.GetApp().GetTopWindow()
        topwin.Raise()
        self.filelist.SetFocus()

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
        if master is None:
            master = grouplist[0]
        gmaster = self.get_group(master)
        xarray = 'xplot' if gmaster.datatype=='xydata' else 'energy'
        outgroup = fix_varname(outgroup.lower())
        if outgroup is None:
            outgroup = 'merged'
        outgroup = unique_name(outgroup, self.file_groups, max=1000)

        glist = "[%s]" % (', '.join(grouplist))

        cmd = f"""{outgroup} = merge_groups({glist}, master={master},
        xarray='{xarray}', yarray='{yarray}', kind='cubic', trim=True)"""
        self.larch.eval(cmd)

        this = self.get_group(outgroup)
        if not hasattr(gmaster, 'config'):
            self.init_group_config(gmaster)
        if not hasattr(this, 'config'):
            self.init_group_config(this)
        this.config.xasnorm.update(gmaster.config.xasnorm)
        this.datatype = gmaster.datatype
        if xarray == 'energy':
            this.xplot = 1.0*this.energy
        this.yplot = 1.0*getattr(this, yarray)
        this.yerr =  getattr(this, 'd' + yarray, 1.0)
        if yarray != 'mu':
            this.mu = this.yplot
        this.plot_xlabel = xarray
        this.plot_ylabel = yarray
        return this

    def set_plot_erange(self, erange):
        self.plot_erange = erange

    def copy_group(self, filename, new_groupname=None, new_filename=None):
        """copy XAS group (by filename) to new group"""
        groupname = self.file_groups[filename]
        if not hasattr(self.larch.symtable, groupname):
            return

        ogroup = self.get_group(groupname)
        ngroup = larch.Group(datatype=ogroup.datatype, copied_from=groupname)

        for attr in dir(ogroup):
            val = getattr(ogroup, attr, None)
            if isinstance(val, np.ndarray):
                setattr(ngroup, attr, 1.0*val[:])
            elif val is not None:
                setattr(ngroup, attr, deepcopy(val))

        if new_filename is None:
            new_filename = filename + '_1'
        if new_groupname is None:
            new_groupname = ogroup.groupname + '_1'
        ngroup.filename = unique_name(new_filename, self.file_groups.keys())
        ngroup.groupname = unique_name(new_groupname, self.file_groups.values())
        ngroup.journal.add('source_desc', f"copied from '{filename:s}'")
        setattr(self.larch.symtable, ngroup.groupname, ngroup)
        return ngroup

    def get_cursor(self, win=None):
        """get last cursor from selected window"""
        return last_cursor_pos(win=win, _larch=self.larch)

    def plot_group(self, groupname=None, title=None, plot_yarrays=None,
                   new=True, **kws):
        ppanel = self.get_display(stacked=False).panel
        newplot = ppanel.plot
        oplot   = ppanel.oplot
        plotcmd = oplot
        viewlims = ppanel.get_viewlimits()
        if new:
            plotcmd = newplot

        dgroup = self.get_group(groupname)
        if not hasattr(dgroup, 'xplot'):
            if hasattr(dgroup, 'xdat'):
                dgroup.xplot = deepcopy(dgroup.xdat)
            else:
                print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None)):
            self.process(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = get_panel_plot_confing(ppanel)
        popts = popts.update(kws)
        fname = Path(dgroup.filename).name
        if not 'label' in popts:
            popts['label'] = dgroup.plot_ylabel

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

            plotcmd(dgroup.xplot, getattr(dgroup, yaname), **popts)
            plotcmd = oplot

        if plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    col_edge, col_face = get_markercolors(trace=len(plot_yarrays),
                                                linecolors=popts['linecolors'],
                                                facecolor=popts['facecolor'])
                    popts = {'marker': 'o',
                             'markersize': popts['markersize'],
                             'label': '_nolegend_',
                             'markerfacecolor': col_face,
                             'markeredgecolor': col_edge}
                    popts.update(opts)
                    axes.plot([x], [y], **popts)
                elif etype == 'vline':
                    popts = {'ymin': 0, 'ymax': 1.0,
                             'color': '#888888'}
                    popts.update(opts)

                    axes.axvline(x, **popts)
        ppanel.canvas.draw()
        self.set_focus()

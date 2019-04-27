#!/usr/bin/env python
#
from __future__ import print_function
import sys
import os
from functools import partial
import wx
import numpy
import scipy

import larch

from wxutils import (MenuItem, Font, Button, Choice)

from .readlinetextctrl import ReadlineTextCtrl
from .larchfilling import Filling
from .columnframe import ColumnDataFileFrame
from .athena_importer import AthenaImporter
from . import inputhook

from larch.io import (read_ascii, read_xdi, read_gsexdi,
                      gsescan_group, fix_varname,
                      is_athena_project, AthenaProject)
from larch.version import make_banner

FILE_WILDCARDS = "Data Files(*.0*,*.dat,*.xdi)|*.0*;*.dat;*.xdi|All files (*.*)|*.*"

ICON_FILE = 'larch.ico'

def makeColorPanel(parent, color):
    p = wx.Panel(parent, -1)
    p.SetBackgroundColour(color)
    return p

class LarchWxShell(object):
    ps1 = 'Larch>'
    ps2 = ' ... >'
    def __init__(self, wxparent=None,   writer=None, _larch=None,
                 prompt=None, historyfile=None, output=None, input=None):
        self._larch = _larch
        self.textstyle = None

        self.prompt = prompt
        self.input  = input
        self.output = output

        if _larch is None:
            self._larch  = larch.Interpreter(historyfile=historyfile,
                                             writer=self)
            self._larch.run_init_scripts()
        self.writer  = self._larch.writer
        self.symtable = self._larch.symtable
        # if self.output is not None:
        #    self.encoding = sys.stdout.encoding
        #    sys.stdout = self

        self.objtree = wxparent.objtree

        self.set_textstyle(mode='text')
        self._larch("_sys.display.colors['text2'] = {'color': 'blue'}",
                    add_history=False)

        self.symtable.set_symbol('_builtin.force_wxupdate', False)
        self.symtable.set_symbol('_sys.wx.inputhook',   inputhook)
        self.symtable.set_symbol('_sys.wx.ping',   inputhook.ping)
        self.symtable.set_symbol('_sys.wx.force_wxupdate', False)
        self.symtable.set_symbol('_sys.wx.wxapp', output)
        self.symtable.set_symbol('_sys.wx.parent', wx.GetApp().GetTopWindow())

        if self.output is not None:
            style = self.output.GetDefaultStyle()
            bgcol = style.GetBackgroundColour()
            sfont = style.GetFont()

            self.textstyle = wx.TextAttr('black', bgcol, sfont)

        self.SetPrompt(True)
        self.flush_timer = wx.Timer(wxparent)
        self.needs_flush = True
        wxparent.Bind(wx.EVT_TIMER, self.onFlushTimer, self.flush_timer)
        self.flush_timer.Start(500)

    def onUpdate(self, event=None):
        symtable = self.symtable
        if symtable.get_symbol('_builtin.force_wxupdate', create=True):
            app = wx.GetApp()
            evtloop = wx.EventLoop()
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
        symtable.set_symbol('_builtin.force_wxupdate', False)


    def SetPrompt(self, complete):
        if self.prompt is None:
            return
        sprompt, scolor = self.ps1, '#000075'
        if not complete:
            sprompt, scolor = self.ps2, '#E00075'
        self.prompt.SetLabel(sprompt)
        self.prompt.SetForegroundColour(scolor)
        self.prompt.Refresh()

    def set_textstyle(self, mode='text'):
        if self.output is None:
            return

        display_colors = self._larch.symtable._sys.display.colors
        textattrs = display_colors.get(mode, {'color':'black'})
        color = textattrs['color']
        style = self.output.GetDefaultStyle()
        bgcol = style.GetBackgroundColour()
        sfont = style.GetFont()
        self.textstyle = wx.TextAttr(color, bgcol, sfont)

    def write_sys(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def write(self, text, **kws):
        if text is None:
            return
        if self.textstyle is None:
            self.set_textstyle()

        if self.output is None or self.textstyle is None:
            self.write_sys(text)
        else:
            self.output.SetInsertionPointEnd()
            pos0 = self.output.GetLastPosition()
            self.output.WriteText(text)
            pos1 = self.output.GetLastPosition()
            self.output.SetStyle(pos0, pos1, self.textstyle)
            self.output.EmulateKeyPress(wx.KeyEvent())
            self.input.SetFocus()

    def flush(self, *args):
        self.output.Refresh()
        self.needs_flush = False

    def clear_input(self):
        self._larch.input.clear()
        self.SetPrompt(True)

    def onFlushTimer(self, event=None):
        if self.needs_flush:
            self.flush()

    def eval(self, text, add_history=True, **kws):
        if text is None:
            return
        if text.startswith('!'):
            return os.system(text[1:])

        elif text.startswith('help(') and text.endswith(')'):
            topic = text[5:-1]
            parent = self.symtable.get_parentpath(topic)
            self.objtree.ShowNode("%s.%s" % (parent, topic))
            return
        else:
            if add_history:
                self.input.AddToHistory(text)
                self.write("%s\n" % text)
            ret = self._larch.eval(text, add_history=add_history)
            if self._larch.error:
                self._larch.input.clear()
                self._larch.writer.set_textstyle('error')
                self._larch.show_errors()
                self._larch.writer.set_textstyle('text')
            elif ret is not None:
                self._larch.writer.write("%s\n" % repr(ret))
            try:
                self.objtree.onRefresh()
            except ValueError:
                pass
            self.SetPrompt(self._larch.input.complete)

class LarchPanel(wx.Panel):
    """Larch Input/Output Panel + Data Viewer as a wx.Panel,
    suitable for embedding into apps
    """
    def __init__(self,  parent=None, _larch=None,
                 historyfile='history_larchgui.lar', **kwds):
        self.parent = parent
        if not historyfile.startswith(larch.site_config.usr_larchdir):
            historyfile = os.path.join(larch.site_config.usr_larchdir,
                                       historyfile)

        wx.Panel.__init__(self, parent, -1, size=(750, 725))

        self.splitter = splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(150)
        self.SetBackgroundColour('#E9EEE0')

        self.objtree = Filling(splitter,  rootLabel='_main')

        self.output = wx.TextCtrl(splitter, -1,  '',
                                  style=wx.TE_MULTILINE|wx.TE_RICH|wx.TE_READONLY)

        self.output.CanCopy()
        self.output.SetInsertionPointEnd()
        # self.output.SetDefaultStyle(wx.TextAttr('black', 'white', sfont))

        splitter.SplitHorizontally(self.objtree, self.output, 0.5)

        ipanel = wx.Panel(self, -1)

        self.prompt = wx.StaticText(ipanel, -1, 'Larch>', size=(65,-1),
                                    style=wx.ALIGN_CENTER|wx.ALIGN_RIGHT)

        self.input = ReadlineTextCtrl(ipanel, -1,  '', size=(525,-1),
                                      historyfile=historyfile,
                                      style=wx.ALIGN_LEFT|wx.TE_PROCESS_ENTER)

        self.input.Bind(wx.EVT_TEXT_ENTER, self.onText)
        isizer = wx.BoxSizer(wx.HORIZONTAL)
        isizer.Add(self.prompt,  0, wx.BOTTOM|wx.CENTER)
        isizer.Add(self.input,   1, wx.ALIGN_LEFT|wx.ALIGN_CENTER|wx.EXPAND)

        ipanel.SetSizer(isizer)
        isizer.Fit(ipanel)

        opts = dict(flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, border=2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter,  1, **opts)
        sizer.Add(ipanel, 0, **opts)

        self.SetSizer(sizer)
        self.larchshell = LarchWxShell(wxparent=self,
                                       _larch = _larch,
                                       historyfile=historyfile,
                                       prompt = self.prompt,
                                       output = self.output,
                                       input  = self.input)

        self.objtree.SetRootObject(self.larchshell.symtable)
        self.larchshell.set_textstyle('text2')
        self.larchshell.write(make_banner([wx]))
        self.larchshell.write("\n  \n")
        self.larchshell.set_textstyle('text')
        root = self.objtree.tree.GetRootItem()
        self.objtree.tree.Expand(root)

    def update(self):
        self.objtree.onRefresh()

    def onText(self, event=None):
        text =  event.GetString()
        self.input.Clear()
        if text.lower() in ('quit', 'exit', 'quit()', 'exit()'):
            self.parent.onExit()
        else:
            wx.CallAfter(self.larchshell.eval, text)

class LarchFrame(wx.Frame):
    def __init__(self, parent=None, _larch=None, is_standalone=True,
                 historyfile='history_larchgui.lar', with_inspection=False,
                 exit_on_close=False, **kwds):

        self.is_standalone = is_standalone
        self.with_inspection = with_inspection
        self.parent = parent
        self.historyfile = historyfile
        self.subframes = {}
        self.last_array_sel = {}

        wx.Frame.__init__(self, parent, -1, size=(750, 725),
                          style= wx.DEFAULT_FRAME_STYLE)
        self.SetTitle('LarchGUI')

        self.font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.SetFont(self.font)
        sbar = self.CreateStatusBar(2, wx.CAPTION)

        self.SetStatusWidths([-2,-1])
        self.SetStatusText("Larch initializing...", 0)

        self.mainpanel = LarchPanel(parent=self, _larch=_larch,
                                    historyfile=historyfile)

        self.larchshell = self.mainpanel.larchshell
        self._larch = self.larchshell._larch

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.mainpanel, 1,
                  wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND)

        self.SetSizer(sizer)

        if parent is None and exit_on_close:
            self.Bind(wx.EVT_CLOSE,  self.onExit)
        else:
             self.Bind(wx.EVT_CLOSE,  self.onClose)
        self.Bind(wx.EVT_SHOW, self.onShow)
        self.BuildMenus()

        # larchdir = larch.site_config.larchdir

        fico = os.path.join(larch.site_config.icondir, ICON_FILE)
        if os.path.exists(fico):
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))

        self.Refresh()
        self.SetStatusText("Ready", 0)
        self.Raise()

    def BuildMenus(self):
        menuBar = wx.MenuBar()

        fmenu = wx.Menu()
        if self.is_standalone:
            MenuItem(self, fmenu, "&Read Data File\tCtrl+O",
                     "Read Data File", self.onReadData)
        MenuItem(self, fmenu, "&Read and Run Larch Script\tCtrl+R",
                 "Read and Execute a Larch Script", self.onRunScript)
        MenuItem(self, fmenu, "&Save Session History\tCtrl+S",
                 "Save Session History to File", self.onSaveHistory)
        MenuItem(self, fmenu, 'Change Working Directory\tCtrl+W',
                 'Change Directory', self.onChangeDir)
        MenuItem(self, fmenu, 'Clear Input\tCtrl+D',
                 'Clear Input', self.onClearInput)
        MenuItem(self, fmenu, 'Select Font\tCtrl+F',
                 'Select Font', self.onSelectFont)

        if self.with_inspection:
            MenuItem(self, fmenu, 'Show wxPython Inspector\tCtrl+I',
                     'Debug wxPython App', self.onWxInspect)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Close Display', 'Close display', self.onClose)
        if self.parent is None:
            MenuItem(self, fmenu, 'E&xit', 'End program', self.onExit)

        menuBar.Append(fmenu, '&File')

        _sys = self.larchshell.symtable._sys
        if self.is_standalone and hasattr(_sys, 'gui_apps'):
            appmenu = wx.Menu()
            x_apps = _sys.gui_apps.keys()
            for appname in sorted(x_apps):
                label, creator = _sys.gui_apps[appname]

                MenuItem(self, appmenu, label, label,
                         partial(self.show_subframe,
                                 name=appname, creator=creator))
            menuBar.Append(appmenu, 'Applications')

        hmenu = wx.Menu()
        MenuItem(self, hmenu, '&About',
                 'Information about this program',  self.onAbout)
        menuBar.Append(hmenu, '&Help')
        self.SetMenuBar(menuBar)

    def onSelectFont(self, event=None):
        fdata = wx.FontData()
        fdata.SetInitialFont(self.font)
        dlg = wx.FontDialog(self, fdata)
        if dlg.ShowModal() == wx.ID_OK:
            self.font = dlg.GetFontData().GetChosenFont()
            self.SetFont(self.font)
            self.mainpanel.output.SetFont(self.font)
            self.mainpanel.objtree.SetFont(self.font)
            self.mainpanel.objtree.text.SetFont(self.font)
        dlg.Destroy()

    def onWxInspect(self, event=None):
        wx.GetApp().ShowInspectionTool()

    def onXRFviewer(self, event=None):
        self.larchshell.eval("xrf_plot()")

    def onClearInput(self, event=None):
        self.larchshell.clear_input()

    def onClearInput(self, event=None):
        self.larchshell.clear_input()

    def show_subframe(self, event=None, name=None, creator=None, **opts):
        if name is None or creator is None:
            return
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = creator(parent=self,
                                           _larch=self.larchshell._larch,
                                           **opts)
            self.subframes[name].Show()

    def onReadData(self, event=None):
        wildcard = 'Data file (*.dat)|*.dat|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Open Data File',
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.abspath(dlg.GetPath()).replace('\\', '/')
        dlg.Destroy()

        if path is None:
            return

        if is_athena_project(path):
            self.show_subframe(name='athena_import', filename=path,
                               creator=AthenaImporter,
                               read_ok_cb=self.onReadAthenaProject_OK)
        else:
            filedir, filename = os.path.split(path)
            pref = fix_varname((filename + '_'*8)[:8]).replace('.', '_').lower()

            count, maxcount = 1, 9999
            groupname = "%s%3.3i" % (pref, count)
            while hasattr(self.larchshell.symtable, groupname) and count < maxcount:
                count += 1
                groupname = '%s%3.3i' % (pref, count)

            fh = open(path, 'r')
            line1 = fh.readline().lower()
            fh.close()
            reader = read_ascii
            if 'epics stepscan file' in line1:
                reader = read_gsexdi
            elif 'epics scan' in line1:
                reader = gsescan_group
            elif 'xdi' in line1:
                reader = read_xdi

            dgroup = reader(str(path), _larch=self.larchshell._larch)
            dgroup._path = path
            dgroup._filename = filename
            dgroup._groupname = groupname
            self.show_subframe(name='coledit', event=None,
                               creator=ColumnDataFileFrame,
                               filename=path,
                               last_array_sel=self.last_array_sel,
                               read_ok_cb=self.onReadScan_Success)


    def onReadScan_Success(self, script, path, groupname=None, array_sel=None,
                           overwrite=False):
        """ called when column data has been selected and is ready to be used"""
        self.larchshell.eval(script.format(group=groupname, path=path))
        if array_sel is not None:
            self.last_array_sel = array_sel
        self.larchshell.flush()

    def onReadAthenaProject_OK(self, path, namelist):
        """read groups from a list of groups from an athena project file"""
        read_cmd = "_prj = read_athena('{path:s}', do_fft=False, do_bkg=False)"
        self.larchshell.eval(read_cmd.format(path=path))
        dgroup = None
        script = "{group:s} = extract_athenagroup(_prj.{prjgroup:s})"
        for gname in namelist:
            this = getattr(self.larchshell.symtable._prj, gname)
            gid = str(getattr(this, 'athena_id', gname))
            self.larchshell.eval(script.format(group=gid, prjgroup=gname))
        self.larchshell.eval("del _prj")

    def onRunScript(self, event=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Open and Run Larch Script',
                            wildcard=wildcard,
                            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            path, fname = os.path.split(fout)
            os.chdir(path)
            text = "run('%s')" % fname
            self.larchshell.write("%s\n" % text)
            wx.CallAfter(self.larchshell.eval, text)
        dlg.Destroy()

    def onSaveHistory(self, event=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        deffile = 'history.lar'
        dlg = wx.FileDialog(self, message='Save Session History File',
                            wildcard=wildcard,
                            defaultFile=deffile,
                            style=wx.FD_SAVE|wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            self._larch.input.history.save(fout, session_only=True)
            self.SetStatusText("Wrote %s" % fout, 0)
        dlg.Destroy()

    def onText(self, event=None):
        text =  event.GetString()
        self.larchshell.write("%s\n" % text)
        self.input.Clear()
        if text.lower() in ('quit', 'exit'):
            self.onExit()
        else:
            self.input.AddToHistory(text)
            wx.CallAfter(self.larchshell.eval, text)


    def onChangeDir(self, event=None):
        dlg = wx.DirDialog(None, 'Choose a Working Directory',
                           defaultPath = os.getcwd(),
                           style = wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            os.chdir(dlg.GetPath())
        dlg.Destroy()
        return os.getcwd()

    def onAbout(self, event=None):
        about_msg =  """LarchGui:
        %s""" % (make_banner([wx]))

        dlg = wx.MessageDialog(self, about_msg,
                               "About LarchGui", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onShow(self, event=None):
        if event.Show:
            self.mainpanel.update()

    def onClose(self, event=None):
        try:
            self.Hide()
        except:
            pass

    def onExit(self, event=None, force=False):
        if force:
            ret = wx.ID_YES
        else:
            dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            ret = dlg.ShowModal()

        if ret == wx.ID_YES:
            try:
                self._larch.input.history.save()
            except:
                pass
            try:
                self.Destroy()
            except:
                pass
            sys.exit()
        else:
            try:
                event.Veto()
            except:
                pass


class LarchApp(wx.App):
    "simple app to wrap LarchFrame"
    def __init__(self, **kws):
        wx.App.__init__(self, **kws)

    def OnInit(self):
        frame = LarchFrame(exit_on_close=True, with_inspection=False)
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == '__main__':
    LarchApp().MainLoop()

#!/usr/bin/env python
#
from __future__ import print_function
import sys
import os

if not hasattr(sys, 'frozen'):
    try:
        import wxversion
        wxversion.ensureMinimal('2.8')
    except:
        pass

import wx
import numpy
import larch

from .readlinetextctrl import ReadlineTextCtrl
from .larchfilling import Filling
from . import inputhook

header = ('=' * 60)
BANNER = """%s
  Larch %s (%s) M. Newville, T. Trainor
  using python %s, numpy %s, wx version %s
%s
"""  %  (header, larch.__version__, larch.__date__,
         '%i.%i.%i' % sys.version_info[:3],
         numpy.__version__, wx.__version__, header)

ICON_FILE = 'larch.ico'

def makeColorPanel(parent, color):
    p = wx.Panel(parent, -1)
    p.SetBackgroundColour(color)
    return p

class LarchWxShell(object):
    ps1 = 'Larch>'
    ps2 = ' ... >'
    def __init__(self, wxparent=None,   writer=None, _larch=None,
                 prompt=None, output=None, input=None):
        self.larch = _larch
        if _larch is None:
            self.larch  = larch.Interpreter()
        self.inptext  = larch.InputText(prompt=self.ps1,
                                        interactive=False)
        self.symtable = self.larch.symtable
        self.prompt = prompt
        self.output = output
        self.input  = input
        self.larch.writer = self
        self.larch.add_plugin('wx', wxparent=wxparent)
        self.symtable.set_symbol('_builtin.force_wxupdate', False)
        self.symtable.set_symbol('_sys.wx.inputhook',   inputhook)
        self.symtable.set_symbol('_sys.wx.ping',   inputhook.ping)
        self.symtable.set_symbol('_sys.wx.force_wxupdate', False)
        self.symtable.set_symbol('_sys.wx.wxapp', output)
        # self.symtable.set_symbol('_sys.wx.parent', wx.GetApp().GetTopWindow())

        self.SetPrompt()

        for fname in larch.site_config.init_files:
            self.execute("run('%s')" % fname)


    def onUpdate(self, event=None):
        symtable = self.symtable
        if symtable.get_symbol('_builtin.force_wxupdate', create=True):
            app = wx.GetApp()
            evtloop = wx.EventLoop()
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
        symtable.set_symbol('_builtin.force_wxupdate', False)

    def SetPrompt(self, partial=False):
        if self.prompt is not None:
            if partial:
                self.prompt.SetLabel(self.ps2)
                self.prompt.SetForegroundColour('#E00075')
            else:
                self.prompt.SetLabel(self.ps1)
                self.prompt.SetForegroundColour('#000075')
            self.prompt.Refresh()

    def write(self, text, color=None):
        if self.output is None:
            sys.stdout.write(text)
            sys.stdout.flush()
            return

        pos0 = self.output.GetLastPosition()
        self.output.WriteText(text)
        if color is not None:
            style = self.output.GetDefaultStyle()
            bgcol = style.GetBackgroundColour()
            sfont = style.GetFont()
            pos1  = self.output.GetLastPosition()
            self.output.SetStyle(pos0, pos1, wx.TextAttr(color, bgcol, sfont))

        self.output.SetInsertionPoint(self.output.GetLastPosition())
        self.output.Refresh()
        self.output.Update()

    def execute(self, text=None):
        if text is not None:
            if  text.startswith('help'):
                arg = text[4:]
                if arg.startswith('(') and arg.endswith(')'): arg = arg[1:-1]
                if arg.startswith("'") and arg.endswith("'"): arg = arg[1:-1]
                if arg.startswith('"') and arg.endswith('"'): arg = arg[1:-1]
                text  = "help(%s)"% (repr(arg))
            if text.startswith('!'):
                return os.system(text[1:])
            else:
                self.inptext.put(text,lineno=0)

        if not self.inptext.input_complete:
            self.SetPrompt(partial = True)
            return None

        ret = None
        self.SetPrompt(partial = False)

        while len(self.inptext) > 0:
            block, fname, lineno = self.inptext.get()
            ret = self.larch.eval(block, fname=fname, lineno=lineno)
            self.input.SetFocus()
            self.symtable.set_symbol('_sys.wx.force_wxupdate', True)
            if hasattr(ret, '__call__') and not isinstance(ret,type):
                try:
                    if 1 == len(block.split()):
                        ret = ret()
                except:
                    pass
            if self.larch.error:
                err = self.larch.error.pop(0)
                fname, lineno = err.fname, err.lineno
                self.write("%s\n" % err.get_error()[1], color='#BB0000')
                for err in self.larch.error:
                    if ((err.fname != fname or err.lineno != lineno)
                        and err.lineno > 0 and lineno > 0):
                        self.write("%s\n" % (err.get_error()[1]), color='#BB0000')
            elif ret is not None:
                try:
                    self.write("%s\n" % repr(ret))
                except:
                    pass

class LarchFrame(wx.Frame):
    def __init__(self,  parent=None, _larch=None,
                 histfile='history_larchgui.lar',
                 exit_on_close=False, **kwds):

        self.histfile = histfile
        self.BuildFrame(parent=parent, **kwds)
        self.larchshell = LarchWxShell(wxparent=self,
                                       _larch = _larch,
                                       prompt = self.prompt,
                                       output = self.output,
                                       input  = self.input)
        self.datapanel.SetRootObject(self.larchshell.symtable)
        if exit_on_close:
            self.Bind(wx.EVT_CLOSE,  self.onExit)
        else:
            self.Bind(wx.EVT_CLOSE,  self.onClose)
        #self.timer.Start(200)
        larchdir = larch.site_config.larchdir
        fico = os.path.join(larchdir, 'icons', ICON_FILE)
        if os.path.exists(fico):
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))


    def InputPanel(self, parent):
        panel = wx.Panel(parent, -1)
        pstyle = wx.ALIGN_CENTER|wx.ALIGN_RIGHT
        self.prompt = wx.StaticText(panel, -1, 'Larch>',
                                    size = (65,-1),
                                    style = pstyle)
        histFile= os.path.join(larch.site_config.larchdir, self.histfile)
        self.input = ReadlineTextCtrl(panel, -1,  '', size=(525,-1),
                                 historyfile=histFile, mode='emacs',
                                 style=wx.ALIGN_LEFT|wx.TE_PROCESS_ENTER)

        self.input.Bind(wx.EVT_TEXT_ENTER, self.onText)
        self.input.notebooks = self.nbook

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.prompt,  0, wx.BOTTOM|wx.CENTER)
        sizer.Add(self.input,   1, wx.ALIGN_LEFT|wx.ALIGN_CENTER|wx.EXPAND)
        panel.SetSizer(sizer)
        sizer.Fit(panel)
        return panel

    def BuildFrame(self, parent=None, **kwds):
        wx.Frame.__init__(self, parent, -1, size=(725, 525),
                          style= wx.DEFAULT_FRAME_STYLE)
        self.SetTitle('LarchGUI')
        ofont = self.GetFont()

        sfont = wx.Font(11,  wx.SWISS, wx.NORMAL, wx.BOLD, False)
        self.SetFont(sfont)
        sbar = self.CreateStatusBar(2, wx.CAPTION|wx.THICK_FRAME)

        self.SetStatusWidths([-2,-1])
        self.SetStatusText("Larch initializing...", 0)

        self.BuildMenus()

        self.nbook = nbook = wx.Notebook(self, -1, style=wx.BK_DEFAULT)
        nbook.SetBackgroundColour('#E9E9EA')
        self.SetBackgroundColour('#E9EEE0')

        self.output = wx.TextCtrl(nbook, -1,  BANNER,
                             style=wx.TE_MULTILINE|wx.TE_RICH|wx.TE_READONLY)

        self.output.CanCopy()
        self.output.SetInsertionPointEnd()
        self.output.SetDefaultStyle(wx.TextAttr('black', 'white', sfont))

        self.datapanel = Filling(nbook,  rootLabel='_main')
        nbook.AddPage(self.output,      'Output Buffer', select=1)
        nbook.AddPage(self.datapanel,   'Browser')

        sizer = wx.BoxSizer(wx.VERTICAL)
        opts = dict(flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, border=2)
        sizer.Add(nbook,  1, **opts)
        sizer.Add(self.InputPanel(self),  0, **opts)

        self.SetSizer(sizer)
        self.Refresh()
        self.SetStatusText("Ready", 0)
        self.Raise()

    def onTimer(self, event=None):
        symtable = self.larchshell.symtable
        # print 'On Timer ', symtable, symtable.get_symbol('_builtin.force_wxupdate')
        #if symtable.get_symbol('_builtin.force_wxupdate', create=True):
        #    print 'Update from Timer!!'
        #    app = wx.GetApp()
        #    app.ProcessIdle()

    def BuildMenus(self):
        ID_ABOUT = wx.NewId()
        ID_CLOSE = wx.NewId()
        ID_EXIT  = wx.NewId()
        ID_FREAD = wx.NewId()
        ID_PREAD = wx.NewId()
        ID_FSAVE = wx.NewId()
        ID_CHDIR = wx.NewId()

        ID_PSETUP  = wx.NewId()
        ID_PREVIEW = wx.NewId()
        ID_PRINT = wx.NewId()

        fmenu = wx.Menu()
        fmenu.Append(ID_FREAD, "&Read ASCII Data File\tCtrl+O",
                     "Read Data File")
        fmenu.Append(ID_PREAD, "&Read and Run Larch Script\tCtrl+R",
                     "Read and Execute a Larch Script")
        fmenu.Append(ID_FSAVE, "&Save Session History\tCtrl+S",
                     "Save Session History to File")
        fmenu.Append(ID_CHDIR, 'Change Working Directory\tCtrl+W',
                     'Change Directory')
        #fmenu.Append(ID_PSETUP, 'Page Setup...', 'Printer Setup')
        #fmenu.Append(ID_PREVIEW, 'Print Preview...', 'Print Preview')
        # fmenu.Append(ID_PRINT, "&Print\tCtrl+P", "Print Plot")

        fmenu.AppendSeparator()
        fmenu.Append(ID_CLOSE, "Close Display", "Close display")
        fmenu.Append(ID_EXIT,  "E&xit", "Terminate the program")

        hmenu = wx.Menu()
        hmenu.Append(ID_ABOUT, "&About",
                     "More information about this program")
        menuBar = wx.MenuBar()
        menuBar.Append(fmenu, "&File");
        # menuBar.Append(vmenu, "&Viewers");
        menuBar.Append(hmenu, "&Help");
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU,  self.onReadData,   id=ID_FREAD)
        self.Bind(wx.EVT_MENU,  self.onRunScript,   id=ID_PREAD)
        self.Bind(wx.EVT_MENU,  self.onSaveHistory, id=ID_FSAVE)
        self.Bind(wx.EVT_MENU,  self.onAbout, id=ID_ABOUT)
        self.Bind(wx.EVT_MENU,  self.onClose, id=ID_CLOSE)
        self.Bind(wx.EVT_MENU,  self.onExit, id=ID_EXIT)
        self.Bind(wx.EVT_MENU,  self.onChangeDir, id=ID_CHDIR)

    def onReadData(self, event=None):
        wildcard = 'Data file (*.dat)|*.dat|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Open Data File',
                            wildcard=wildcard,
                            style=wx.OPEN|wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            path, fname = os.path.split(fout)
            os.chdir(path)
            print( 'Open ASCII data file? ', fname)

        dlg.Destroy()

    def onRunScript(self, event=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Open and Run Larch Script',
                            wildcard=wildcard,
                            style=wx.OPEN|wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            path, fname = os.path.split(fout)
            os.chdir(path)
            text = "run('%s')" % fname
            self.larchshell.write(">%s\n" % text)
            self.input.AddToHistory(text)
            wx.CallAfter(self.larchshell.execute, text)
        dlg.Destroy()

    def onSaveHistory(self, event=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        deffile = 'history.lar'
        dlg = wx.FileDialog(self, message='Save Session History File',
                            wildcard=wildcard,
                            defaultFile=deffile,
                            style=wx.SAVE|wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            self.input.SaveHistory(filename=fout, session_only=True)
            self.SetStatusText("Wrote %s" % fout, 0)
        dlg.Destroy()

    def onText(self, event=None):
        text =  event.GetString()
        self.larchshell.write(">%s\n" % text)
        self.input.Clear()
        if text.lower() in ('quit', 'exit'):
            self.onExit()
        else:
            self.input.AddToHistory(text)
            wx.CallAfter(self.larchshell.execute, text)
            wx.CallAfter(self.datapanel.tree.display)

    def onResize(self, event=None):
        size = event.GetSize()
        nsize = self.notebooks.GetSize()
        self.notebooks.SetSize(size)
        self.notebooks.Refresh()
        nsize = self.notebooks.GetSize()

        # self.notebooks.SetBestFittingSize()
        self.notebooks.Refresh()
        nsize = self.notebooks.GetSize()

        for k in range(self.notebooks.GetPageCount()):
            p = self.notebooks.GetPage(k)
            try:
                p.SetSize(size)
            except:
                print( 'cannot set size')
            p.Refresh()
        event.Skip()

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
        %s""" % (BANNER)

        dlg = wx.MessageDialog(self, about_msg,
                               "About LarchGui", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,event=None):
        try:
            self.Hide()
            self.input.SaveHistory()
            self.larchshell.symtable.get_symbol('_plotter.close_all_displays')()
        except:
            pass

    def onExit(self,event=None):
        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        ret = dlg.ShowModal()
        if ret == wx.ID_YES:
            try:
                self.input.SaveHistory()
                self.larchshell.symtable.get_symbol('_plotter.close_all_displays')()
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

if __name__ == '__main__':
    app = wx.PySimpleApp()
    f = LarchFrame(None)
    f.Show()
    app.MainLoop()

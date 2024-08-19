import time
import sys
import locale
from  threading import Thread
from pathlib import Path
import wx
import wx.adv, wx.richtext
from  wx.lib.mixins.inspection import InspectionMixin

from larch.site_config import icondir

LARIX_TITLE = "Larix: XAS Visualization and Analysis"
ICON_FILE = 'onecone.ico'
SPLASH_STYLE = wx.adv.SPLASH_CENTRE_ON_SCREEN|wx.adv.SPLASH_TIMEOUT

class LarixApp(wx.App, InspectionMixin):
    def __init__(self, _larch=None, filename=None, check_version=True,
                 mode='xas', with_c_locale=True, with_wx_inspect=False, **kws):
        self._larch = _larch
        self.filename = filename
        self.mode = mode
        self.with_c_locale = with_c_locale
        self.with_wx_inspect = with_wx_inspect
        self.check_version = check_version
        wx.App.__init__(self,**kws)

    def OnInit(self):
        wx.SystemOptions.SetOption("mac.window-plain-transition", 1)
        LarixSplashScreen(filename=self.filename,
                          check_version=self.check_version,
                          mode=self.mode,
                          with_wx_inspect=self.with_wx_inspect)
        return True

    def createApp(self):
        return True

    def InitLocale(self):
        """over-ride wxPython default initial locale"""
        if self.with_c_locale:
            self._initial_locale = None
            locale.setlocale(locale.LC_ALL, 'C')
        else:
            lang, enc = locale.getdefaultlocale()
            self._initial_locale = wx.Locale(lang, lang[:2], lang)
            locale.setlocale(locale.LC_ALL, lang)

class LarixSplashScreen(wx.adv.SplashScreen):
    def __init__(self, **kws):
        self.kws = kws
        bmp = wx.Image(Path(icondir, ICON_FILE).as_posix()).ConvertToBitmap()
        wx.adv.SplashScreen.__init__(self, bmp, SPLASH_STYLE, 9000, None, -1)
        self.import_thread = Thread(target=self.importer)
        self.import_thread.start()
        wx.CallAfter(self.ShowMain)

    def importer(self, evt=None):
        from larch.wxxas.xasgui import LarixFrame

    def ShowMain(self):
        self.import_thread.join()
        from larch.wxxas.xasgui import LarixFrame
        self.frame = LarixFrame(**self.kws)
        wx.GetApp().SetTopWindow(self.frame)
        return True

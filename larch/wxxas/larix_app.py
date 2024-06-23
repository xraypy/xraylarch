import time
import sys
import os
import locale
import wx
from wx.adv import AboutBox, AboutDialogInfo, SplashScreen
import wx.adv
import wx.lib

from larch.site_config import icondir

LARIX_TITLE = "Larix: XAS Visualization and Analysis"
ICON_FILE = 'onecone.ico'

class LarixApp(wx.App):
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

class LarixSplashScreen(SplashScreen):
    def __init__(self, **kws):
        self.kws = kws
        bmp = wx.Image(os.path.join(icondir, ICON_FILE)).ConvertToBitmap()
        SplashScreen.__init__(self, bmp,
                              wx.adv.SPLASH_CENTRE_ON_SCREEN|wx.adv.SPLASH_TIMEOUT,
                              8000, None, -1)
        self.Raise()
        wx.CallAfter(self.ShowMain)

    def ShowMain(self):
        self.Show()
        wx.Yield()
        from larch.wxxas.xasgui import LarixFrame

        self.frame = LarixFrame(**self.kws)
        wx.GetApp().SetTopWindow(self.frame)
        if self.kws.get('wx_debug', False):
           wx.GetApp().ShowInspectionTool()
        return True

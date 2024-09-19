#!/usr/bin/env pythonw
'''
GUI for displaying 1D XRD images

'''
import os
import sys
import time

from functools import partial

import numpy as np
from numpy.polynomial.chebyshev import chebfit, chebval

from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
import pyFAI.units
pyFAI.use_opencl = False

import wx
import wx.lib.scrolledpanel as scrolled
from wxmplot import PlotPanel

from lmfit.lineshapes import gaussian

import larch
from larch.larchlib import read_workdir, save_workdir
from larch.utils import get_cwd, gformat, fix_filename
from larch.utils.physical_constants import PLANCK_HC
from larch.xray import XrayBackground
from larch.wxxas.xas_dialogs import RemoveDialog
from larch.io import tifffile

from larch.xrd import (d_from_q,twth_from_q,q_from_twth,
                       d_from_twth,twth_from_d,q_from_d,
                       lambda_from_E, E_from_lambda, calc_broadening,
                       instrumental_fit_uvw,peaklocater,peakfitter,
                       xrd1d, save1D, read_poni)

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, pack,
                         Button, HLine, Choice, Check, MenuItem, COLORS,
                         set_color, CEN, RIGHT, LEFT, FRAMESTYLE, Font,
                         FONTSIZE, FONTSIZE_FW, FileSave, FileOpen,
                         flatnotebook, Popup, FileCheckList, OkCancel,
                         EditableListBox, ExceptionPopup, CIFFrame,
                         LarchFrame, LarchWxApp)

MAXVAL = 2**32 - 2**15
MAXVAL_INT16 = 2**16 - 8

XYWcards = "XY Data File(*.xy)|*.xy|All files (*.*)|*.*"
TIFFWcards = "TIFF Files|*.tif;*.tiff|All files (*.*)|*.*"
PlotWindowChoices = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

X_SCALES = [u'q (\u212B\u207B\u00B9)', u'2\u03B8 (\u00B0)', u'd (\u212B)']
Y_SCALES = ['linear', 'log']

PLOT_TYPES = {'Raw Data': 'raw',
              'Raw Data + Background' : 'raw+bkg',
              'Background-subtracted Data': 'sub'}

PLOT_CHOICES = list(PLOT_TYPES.keys())
PLOT_CHOICES_MULTI = [PLOT_CHOICES[0], PLOT_CHOICES[2]]

SCALE_METHODS = {'Max Raw Intensity': 'raw_max',
                 'Max Background-Subtracted Intensity': 'sub_max',
                 'Max Background Intensity': 'bkg_max',
                 'Mean Raw Intensity': 'raw_mean',
                 'Mean Background-Subtracted Intensity': 'sub_mean',
                 'Mean Background Intensity': 'bkg_mean'}

def keyof(dictlike, value, default):
    "dict reverse lookup"
    if value not in dictlike.values():
        value = default
    defout = None
    for key, val in dictlike.items():
        if defout is None:
            defout = key
        if val == value:
            return key
    return defout


def smooth_bruckner(y, smooth_points, iterations):
    y_original = y
    N_data = y.size
    N = smooth_points
    N_float = float(N)
    y = np.empty(N_data + N + N)

    y[0:N].fill(y_original[0])
    y[N:N + N_data] = y_original[0:N_data]
    y[N + N_data:N_data + N + N].fill(y_original[-1])

    y_avg = np.average(y)
    y_min = np.min(y)

    y_c = y_avg + 2. * (y_avg - y_min)
    y[y > y_c] = y_c

    window_size = N_float*2+1

    for j in range(0, iterations):
        window_avg = np.average(y[0: 2*N + 1])
        for i in range(N, N_data - 1 - N - 1):
            if y[i]>window_avg:
                y_new = window_avg
                #updating central value in average (first bracket)
                #and shifting average by one index (second bracket)
                window_avg += ((window_avg-y[i]) + (y[i+N+1]-y[i - N]))/window_size
                y[i] = y_new
            else:
                #shifting average by one index
                window_avg += (y[i+N+1]-y[i - N])/window_size
    return y[N:N + N_data]

def extract_background(x, y, smooth_width=0.1, iterations=40, cheb_order=40):
    """DIOPTAS
    Performs a background subtraction using bruckner smoothing and a chebyshev polynomial.
    Standard parameters are found to be optimal for synchrotron XRD.
    :param x: x-data of pattern
    :param y: y-data of pattern
    :param smooth_width: width of the window in x-units used for bruckner smoothing
    :param iterations: number of iterations for the bruckner smoothing

    :param cheb_order: order of the fitted chebyshev polynomial
    :return: vector of extracted y background
    """
    smooth_points = int((float(smooth_width) / (x[1] - x[0])))
    y_smooth = smooth_bruckner(y, abs(smooth_points), iterations)
    # get cheb input parameters
    x_cheb = 2. * (x - x[0]) / (x[-1] - x[0]) - 1.
    cheb_params = chebfit(x_cheb, y_smooth, cheb_order)
    return chebval(x_cheb, cheb_params)

def calc_bgr(dset, qwid=0.1, nsmooth=40, cheb_order=40):
    try:
        bgr = extract_background(dset.q, dset.I,
                                 smooth_width=qwid,
                                 iterations=nsmooth,
                                 cheb_order=cheb_order)
    except:
        bgr = 0.0*dset.I
    return bgr


class WavelengthDialog(wx.Dialog):
    """dialog for wavelength/energy"""
    def __init__(self, parent, wavelength, callback=None):

        self.parent = parent
        self.callback = callback

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Set Wavelength / Energy")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}

        opts  = dict(size=(90, -1), act_on_losefocus=True)
        wids['wavelength'] = FloatCtrl(panel, value=wavelength, precision=7,
                                       minval=1.0e-4, maxval=100, **opts)

        en_ev = PLANCK_HC/wavelength
        wids['energy'] = FloatCtrl(panel, value=en_ev, precision=2,
                                   minval=50, maxval=5.e5, **opts)


        wids['wavelength'].SetAction(self.set_wavelength)
        wids['energy'].SetAction(self.set_energy)

        panel.Add(SimpleText(panel, 'Wavelength(\u212B): '),
                  dcol=1, newrow=False)
        panel.Add(wids['wavelength'], dcol=1)
        panel.Add(SimpleText(panel, 'Energy (eV): '),
                  dcol=1, newrow=True)
        panel.Add(wids['energy'], dcol=1)

        panel.Add((10, 10), newrow=True)

        panel.Add(Button(panel, 'Done', size=(150, -1),
                         action=self.onDone),  newrow=True)
        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT, 5)
        pack(self, sizer)
        self.Fit()

        w0, h0 = self.GetSize()
        w1, h1 = self.GetBestSize()
        self.SetSize((max(w0, w1)+25, max(h0, h1)+25))

    def onDone(self, event=None):
        if callable(self.callback):
            self.callback(self.wids['wavelength'].GetValue())
        self.Destroy()

    def set_wavelength(self, value=1, event=None):
        w = self.wids['wavelength'].GetValue()

        self.wids['energy'].SetValue(PLANCK_HC/w, act=False)

    def set_energy(self, value=10000, event=None):
        w = self.wids['energy'].GetValue()
        self.wids['wavelength'].SetValue(PLANCK_HC/w, act=False)

class RenameDialog(wx.Dialog):
    """dialog for renaming a pattern"""
    def __init__(self, parent, name, callback=None):

        self.parent = parent
        self.callback = callback

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Rename dataset")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}
        wids['newname'] = wx.TextCtrl(panel, value=name, size=(150, -1))

        panel.Add(SimpleText(panel, 'New Name: '),  dcol=1, newrow=False)
        panel.Add(wids['newname'], dcol=1)
        panel.Add((10, 10), newrow=True)

        panel.Add(Button(panel, 'Done', size=(150, -1),
                         action=self.onDone),  newrow=True)
        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT, 5)
        pack(self, sizer)
        self.Fit()

        w0, h0 = self.GetSize()
        w1, h1 = self.GetBestSize()
        self.SetSize((max(w0, w1)+25, max(h0, h1)+25))

    def onDone(self, event=None):
        if callable(self.callback):
            self.callback(self.wids['newname'].GetValue())
        self.Destroy()

class ResetMaskDialog(wx.Dialog):
    """dialog for wavelength/energy"""
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(350, 300),
                           title="Unset Mask?")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}

        warn_msg = 'This will remove the current mask!'

        panel.Add(SimpleText(panel, warn_msg), dcol=2)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT, 5)
        pack(self, sizer)
        self.Fit()
        w0, h0 = self.GetSize()
        w1, h1 = self.GetBestSize()
        self.SetSize((max(w0, w1)+25, max(h0, h1)+25))

    def GetResponse(self):
        self.Raise()
        return (self.ShowModal() == wx.ID_OK)

class XRD1DFrame(wx.Frame):
    """browse 1D XRD patterns"""

    def __init__(self, parent=None, wavelength=1.0, ponifile=None,
                 _larch=None, **kws):

        wx.Frame.__init__(self, None, -1, title='1D XRD Browser',
                          style=FRAMESTYLE, size=(600, 600), **kws)
        self.parent = parent
        self.wavelength = wavelength
        self.poni = {'wavelength': 1.e-10*self.wavelength} # ! meters!
        self.pyfai_integrator = None

        self.larch = _larch
        if self.larch is None:
            self.larch_buffer = LarchFrame(_larch=None, parent=self,
                                           is_standalone=False,
                                           with_raise=False,
                                           exit_on_close=False)

            self.larch = self.larch_buffer.larchshell

        self.current_label = None
        self.cif_browser = None
        self.img_display = None
        self.plot_display = None
        self.mask = None
        self.datasets = {}
        self.form = {}
        self.createMenus()
        self.build()
        self.set_wavelength(self.wavelength)
        if ponifile is not None:
            self.set_ponifile(ponifile)

    def createMenus(self):
        fmenu = wx.Menu()
        cmenu = wx.Menu()
        smenu = wx.Menu()
        MenuItem(self, fmenu, "Read XY File",
                 "Read XRD 1D data from XY FIle",
                 self.onReadXY)

        MenuItem(self, fmenu, "Save XY File",
                 "Save XRD 1D data to XY FIle",
                 self.onSaveXY)
        self.tiff_reader = MenuItem(self, fmenu, "Read TIFF XRD Image",
                                    "Read XRD 2D image to be integrated",
                                    self.onReadTIFF)
        self.tiff_reader.Enable(self.poni.get('dist', -1) > 0)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Change Label for Current Pattern",
                 "Rename Current Pattern",
                 self.onRenameDataset)

        MenuItem(self, fmenu, "Remove Selected Patterns",
                 "Remove Selected Patterns",
                 self.remove_selected_datasets)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        MenuItem(self, smenu, "Browse AmMin Crystal Structures",
                 "Browse Structures from American Mineralogical Database",
                 self.onCIFBrowse)

        MenuItem(self, cmenu, "Read PONI Calibration File",
                 "Read PONI Calibration (pyFAI) File",
                 self.onReadPONI)

        MenuItem(self, cmenu, "Set Energy/Wavelength",
                 "Set Energy and Wavelength",
                 self.onSetWavelength)

        MenuItem(self, cmenu, "Set Mask for imported Images",
                 "Read Mask for Imported TIFF XRD Images", self.onReadMask)

        m = MenuItem(self, cmenu, "Unset Mask",
                     "Reset to use no mask for Imported TIFF XRD Images",
                     self.onUnsetMask)
        self.unset_mask_menu = m
        m.Enable(False)

        m = MenuItem(self, cmenu, "Show Mask Image",
                     "Show image of mask", self.onShowMask)
        self.show_mask_menu = m
        m.Enable(False)

        menubar = wx.MenuBar()
        menubar.Append(fmenu, "&File")
        menubar.Append(cmenu, "&Calibration and Mask")
        menubar.Append(smenu, "&Search CIF Structures")
        self.SetMenuBar(menubar)


    def onClose(self, event=None):
        try:
            if self.panel is not None:
                self.panel.win_config.Close(True)
            if self.panel is not None:
                self.panel.win_config.Destroy()
        except:
            pass

        for attr in ('cif_browser', 'img_display', 'plot_display'):
            winx = getattr(self, attr, None)
            if winx is not None:
                try:
                    winx.Destroy()
                except:
                    pass

        if hasattr(self.larch.symtable, '_plotter'):
            wx.CallAfter(self.larch.symtable._plotter.close_all_displays)

        self.Destroy()

    def onSetWavelength(self, event=None):
        WavelengthDialog(self, self.wavelength, self.set_wavelength).Show()

    def onReadPONI(self, event=None):
        sfile = FileOpen(self, 'Read PONI (pyFAI) calibration file',
                         default_file='XRD.poni',
                         default_dir=get_cwd(),
                         wildcard="PONI Files(*.poni)|*.poni|All files (*.*)|*.*")

        if sfile is not None:
            try:
                self.set_poni(read_poni(sfile), with_pyfai=True)
            except:
                title = "Could not read PONI File"
                message = [f"Could not read PONI file {sfile}"]
                ExceptionPopup(self, title, message)

            top, xfile = os.path.split(sfile)
            os.chdir(top)

            if self.pyfai_integrator is None:
                try:
                    self.pyfai_integrator = AzimuthalIntegrator(**self.poni)
                except:
                    self.pyfai_integrator = None

            self.tiff_reader.Enable(self.pyfai_integrator is not None)

        self.set_wavelength(self.poni['wavelength']*1.e10)

    def onReadXY(self, event=None):
        sfile = FileOpen(self, 'Read XY Data',
                         default_file='XRD.xy',
                         default_dir=get_cwd(),
                         wildcard=XYWcards)
        if sfile is not None:
            top, xfile = os.path.split(sfile)
            os.chdir(top)
            dxrd = xrd1d(file=sfile, wavelength=self.wavelength)
            self.add_data(dxrd, label=xfile)

    def onUnsetMask(self, event=None):
        if self.mask is not None:
            dlg = ResetMaskDialog(self)
            if dlg.GetResponse():
                self.mask = None
                self.unset_mask_menu.Enable(False)
                self.show_mask_menu.Enable(False)

    def onReadMask(self, event=None):
        sfile = FileOpen(self, 'Read Mask Image File',
                         default_file='XRD.mask',
                         default_dir=get_cwd(),
                         wildcard="Mask Files(*.mask)|*.mask|All files (*.*)|*.*")

        if sfile is not None:
            valid_mask = False
            try:
                img =  tifffile.imread(sfile)
                valid_mask = len(img.shape)==2 and img.max() == 1 and img.min() == 0
            except:
                valid_mask = False
            if valid_mask:
                self.mask = (1 - img[::-1, :]).astype(img.dtype)
                self.unset_mask_menu.Enable(True)
                self.show_mask_menu.Enable(True)
            else:
                title = "Could not use mask file"
                message = [f"Could not use {sfile:s} as a mask file"]
                o = ExceptionPopup(self, title, message)

    def onShowMask(self, event=None):
        if self.mask is not None:
            imd = self.get_imdisplay()
            imd.display(self.mask, colomap='gray', auto_contrast=True)

    def onReadTIFF(self, event=None):
        sfile = FileOpen(self, 'Read TIFF XRD Image',
                         default_file='XRD.tiff',
                         default_dir=get_cwd(),
                         wildcard=TIFFWcards)
        if sfile is not None:
            top, fname = os.path.split(sfile)            
            
            if self.pyfai_integrator is None:
                try:
                    self.pyfai_integrator = AzimuthalIntegrator(**self.poni)
                except:
                    title = "Could not create pyFAI integrator: bad PONI data?"
                    message = [f"Could not create pyFAI integrator"]
                    ExceptionPopup(self, title, message)
            if self.pyfai_integrator is None:
                return

            img =  tifffile.imread(sfile)
            self.display_xrd_image(img, label=fname)

    def display_xrd_image(self, img, label='Image'):
        if self.mask is not None:
            if (self.mask.shape == img.shape):
                img = img*self.mask
            else:
                title = "Could not apply current mask"
                message = [f"Could not apply current mask [shape={self.mask.shape}]",
                           f"to this XRD image [shape={img.shape}]"]
                o = ExceptionPopup(self, title, message)

        if (img.max() > MAXVAL_INT16) and (img.max() < MAXVAL_INT16 + 64):
            #probably really 16bit data
            img[np.where(img>MAXVAL_INT16)] = 0
        else:
            img[np.where(img>MAXVAL)] = 0
        img[np.where(img<-1)] = -1
        img = img[::-1, :]

        imd = self.get_imdisplay()
        imd.display(img, colomap='gray', auto_contrast=True)
            
        integrate = self.pyfai_integrator.integrate1d
        q, ix = integrate(img, 2048, method='csr', unit='q_A^-1',
                          correctSolidAngle=True,
                          polarization_factor=0.999)

        dxrd = xrd1d(label=label, x=q, I=ix, xtype='q',
                     wavelength=self.wavelength)
        self.add_data(dxrd, label=label)


    def onCIFBrowse(self, event=None):
        shown = False
        if self.cif_browser is not None:
            try:
                self.cif_browser.Raise()
                shown = True
            except:
                del self.cif_browser
                shown = False
        if not shown:
            self.cif_browser = CIFFrame(usecif_callback=self.onLoadCIF,
                                        _larch=self.larch)
            self.cif_browser.Raise()

    def onLoadCIF(self, cif=None):
        if cif is None:
            return
        t0 = time.time()

        energy = E_from_lambda(self.wavelength)

        sfact = cif.get_structure_factors(wavelength=self.wavelength)
        try:
            self.cif_browser.cifdb.set_hkls(self.current_cif.ams_id, sfact.hkls)
        except:
            pass

        mineral = getattr(cif, 'mineral', None)
        label = getattr(mineral, 'name', '')
        if len(label) < 0:
            label = getattr(cif, 'formula', '')
        cifid = getattr(cif, 'ams_id', '')
        if len(label) < 1 and len(cifid) > 0:
            label = 'CIF:{cifid}'
        else:
            label = f'{label}, CIF:{cifid}'

        try:
            q = self.datasets[self.current_label].q
        except:
            q = np.linspace(0, 10, 2048)

        sigma = 2.5*(q[1] - q[0])

        intensity = q*0.0
        for cen, amp in zip(sfact.q, sfact.intensity):
            intensity += gaussian(q, amplitude=amp, center=cen, sigma=sigma)

        xdat = xrd1d(label=label, energy=energy, wavelength=self.wavelength)
        xdat.set_xy_data(np.array([q, intensity/max(intensity)]), 'q')
        self.add_data(xdat, label=label)


    def onSaveXY(self, event=None):
        fname = fix_filename(self.current_label.replace('.', '_') + '.xy')
        sfile = FileSave(self, 'Save XY Data', default_file=fname)
        if sfile is None:
            return

        label = self.current_label
        dset = self.datasets[label]

        xscale = self.wids['xscale'].GetSelection()
        xlabel = self.wids['xscale'].GetStringSelection()
        xdat = dset.twth
        xlabel = pyFAI.units.TTH_DEG
        if xscale == 0:
            xdat = dset.q
            xlabel = pyFAI.units.Q_A

        ydat = 1.0*dset.I/dset.scale
        wavelength = PLANCK_HC/(dset.energy*1000.0)
        buff = [f"# XY data from {label}",
                f"# wavelength (Ang) = {gformat(wavelength)}",
                "# Calibration data from pyFAI:"]
        for key, value in self.poni.items():
            buff.append(f"#    {key}: {value}")
        buff.append("#-------------------------------------")
        buff.append(f"# {xlabel}    Intensity")

        for x, y in zip(xdat, ydat):
            buff.append(f"  {gformat(x, 13)}  {gformat(y, 13)}")
        buff.append('')
        with open(sfile, 'w') as fh:
            fh.write('\n'.join(buff))


    def build(self):
        sizer = wx.GridBagSizer(3, 3)
        sizer.SetVGap(3)
        sizer.SetHGap(3)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(220)

        # left side: list of XRD 1D patterns
        lpanel = wx.Panel(splitter)
        lpanel.SetMinSize((275, 350))
        # rpanel = scrolled.ScrolledPanel(splitter)
        rpanel = wx.Panel(splitter)
        rpanel.SetMinSize((400, 350))
        rpanel.SetSize((750, 550))

        ltop = wx.Panel(lpanel)

        def Btn(msg, x, act):
            b = Button(ltop, msg, size=(x, 30),  action=act)
            b.SetFont(Font(FONTSIZE))
            return b

        sel_none = Btn('Select None', 130, self.onSelNone)
        sel_all  = Btn('Select All', 130, self.onSelAll)

        self.filelist = FileCheckList(lpanel, main=self,
                                      select_action=self.show_dataset,
                                      remove_action=self.remove_dataset)
        set_color(self.filelist, 'list_fg', bg='list_bg')

        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LEFT|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LEFT|wx.GROW, 1)
        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.filelist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(lpanel, sizer)

        # right side: parameters controlling display
        panel = GridPanel(rpanel, ncols=6, nrows=10, pad=3, itemstyle=LEFT)
        panel.sizer.SetVGap(3)
        panel.sizer.SetHGap(3)

        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.BOLD)

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, '1D XRD Data Display', font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)

        self.last_plot_type = 'one'
        self.plotone = Button(panel, 'Plot Current ', size=(125, -1),
                              action=self.onPlotOne)
        self.plotsel = Button(panel, 'Plot Selected ', size=(125, -1),
                              action=self.onPlotSel)
        wids['plotone'] = Choice(panel, choices=PLOT_CHOICES, default=0,
                                 action=self.onPlotOne, size=(200, -1))
        wids['plotsel'] = Choice(panel, choices=PLOT_CHOICES_MULTI, default=0,
                                 action=self.onPlotSel, size=(200, -1))
        wids['xscale'] = Choice(panel, choices=X_SCALES, default=0,
                                 action=self.onPlotEither, size=(100, -1))

        opts = dict(default=False, size=(200, -1), action=self.onPlotEither)
        wids['plot_win']  = Choice(panel, size=(100, -1), choices=PlotWindowChoices,
                                   action=self.onPlotEither)
        wids['plot_win'].SetStringSelection('1')

        wids['auto_scale'] = Check(panel, default=True, label='auto?',
                                   action=self.auto_scale)
        wids['scale_method'] = Choice(panel, choices=list(SCALE_METHODS.keys()),
                                      size=(250, -1), action=self.auto_scale, default=0)

        wids['scale'] = FloatCtrl(panel, value=1.0, size=(90, -1), precision=2,
                                  action=self.set_scale)
        wids['wavelength'] = SimpleText(panel, label="%.6f" % (self.wavelength), size=(100, -1))
        wids['energy_ev'] = SimpleText(panel, label="%.1f" % (PLANCK_HC/self.wavelength), size=(100, -1))

        wids['bkg_qwid'] = FloatSpin(panel, value=0.1, size=(90, -1), digits=2,
                                     increment=0.01,
                                     min_val=0.001, max_val=5, action=self.on_bkg)
        wids['bkg_nsmooth'] = FloatSpin(panel, value=30, size=(90, -1),
                                        digits=0, min_val=2, max_val=100, action=self.on_bkg)
        wids['bkg_porder'] = FloatSpin(panel, value=40, size=(90, -1),
                                        digits=0, min_val=2, max_val=100, action=self.on_bkg)

        def CopyBtn(name):
            return Button(panel, 'Copy to Seleceted', size=(150, -1),
                          action=partial(self.onCopyAttr, name))

        wids['bkg_copy'] = CopyBtn('bkg')
        wids['scale_copy'] = CopyBtn('scale_method')

        def slabel(txt):
            return wx.StaticText(panel, label=txt)

        panel.Add(title, style=LEFT, dcol=5)
        panel.Add(self.plotsel, newrow=True)
        panel.Add(wids['plotsel'], dcol=2)
        panel.Add(slabel(' X scale: '), dcol=2, style=LEFT)
        panel.Add(wids['xscale'], style=RIGHT)

        panel.Add(self.plotone, newrow=True)
        panel.Add(wids['plotone'], dcol=2)
        panel.Add(slabel(' Plot Window: '), dcol=2)
        panel.Add(wids['plot_win'], style=RIGHT)

        panel.Add((5, 5))
        panel.Add(HLine(panel, size=(550, 3)), dcol=6, newrow=True)
        panel.Add((5, 5))


        panel.Add(slabel(' Scaling Factor: '), style=LEFT, newrow=True)
        panel.Add(wids['scale'])
        panel.Add(wids['auto_scale'])
        panel.Add(slabel(' Scaling Method: '), style=LEFT, newrow=True)
        panel.Add(wids['scale_method'], dcol=3)
        panel.Add(wids['scale_copy'], dcol=2, style=RIGHT)

        panel.Add((5, 5))
        panel.Add(HLine(panel, size=(550, 3)), dcol=6, newrow=True)
        panel.Add((5, 5))

        panel.Add(slabel(' Background Subtraction Parameters: '), dcol=3, style=LEFT, newrow=True)
        panel.Add(wids['bkg_copy'], dcol=3, style=RIGHT)

        panel.Add(slabel(' Q width (\u212B\u207B\u00B9): '), style=LEFT, newrow=True)
        panel.Add(wids['bkg_qwid'])
        panel.Add(slabel(' Smoothing Steps: '), style=LEFT, newrow=True)
        panel.Add(wids['bkg_nsmooth'], dcol=2)
        panel.Add(slabel(' Polynomial Order: '), style=LEFT, newrow=True)
        panel.Add(wids['bkg_porder'])

        panel.Add((5, 5))
        panel.Add(HLine(panel, size=(550, 3)), dcol=6, newrow=True)
        panel.Add((5, 5))

        panel.Add(slabel(' Calibration, Calculated XRD Patterns: '), dcol=6, style=LEFT, newrow=True)
        panel.Add(slabel(' X-ray Energy (eV): '), style=LEFT, newrow=True)
        panel.Add(wids['energy_ev'], dcol=1)
        panel.Add(slabel(' Wavelength (\u212B): '), style=LEFT, newrow=False)
        panel.Add(wids['wavelength'], dcol=2)


        panel.Add((5, 5))

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(panel, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        pack(rpanel, sizer)

        # rpanel.SetupScrolling()

        splitter.SplitVertically(lpanel, rpanel, 1)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        pack(self, mainsizer)
        self.SetSize((875, 450))

        self.Show()
        self.Raise()

    def set_ponifile(self, ponifile, with_pyfai=True):
        "set poni from datafile"
        try:
            self.set_poni(read_poni(ponifile), with_pyfai=with_pyfai)
        except:
            pass

    def set_poni(self, poni, with_pyfai=True):
        "set poni from dict"
        try:
            self.poni.update(poni)
            self.set_wavelength(self.poni['wavelength']*1.e10)
            self.tiff_reader.Enable(self.poni.get('dist', -1) > 0)
        except:
            pass

        if with_pyfai:
            try:
                self.pyfai_integrator = AzimuthalIntegrator(**self.poni)
            except:
                self.pyfai_integrator = None
                

    def set_wavelength(self, value):
        self.wavelength = value
        self.wids['wavelength'].SetLabel("%.6f" % value)
        self.wids['energy_ev'].SetLabel("%.1f" % (PLANCK_HC/value))
        for key, dset in self.datasets.items():
            dset.set_wavelength(value)

    def onCopyAttr(self, name=None, event=None):
        # print("Copy ", name, event)
        if name == 'bkg':
            qwid = self.wids['bkg_qwid'].GetValue()
            nsmooth = int(self.wids['bkg_nsmooth'].GetValue())
            cheb_order = int(self.wids['bkg_porder'].GetValue())

            for label in self.filelist.GetCheckedStrings():
                dset = self.datasets.get(label, None)
                if dset is not None:
                    dset.bkg_qwid = qwid
                    dset.bkg_nsmooth = nsmooth
                    dset.bkg_porder = cheb_order
                    # print("redo bkg for ", label)
                    dset.bkgd = calc_bgr(dset, qwid=qwid, nsmooth=nsmooth,
                                         cheb_order=cheb_order)

        elif name == 'scale_method':
            for label in self.filelist.GetCheckedStrings():
                dset = self.datasets.get(label, None)
                if dset is not None:
                    # print("redo scale for ", label)
                    self.scale_data(dset, with_plot=False)


    def onSelNone(self, event=None):
        self.filelist.select_none()

    def onSelAll(self, event=None):
        self.filelist.select_all()

    def on_bkg(self, event=None, value=None):
        try:
            qwid = self.wids['bkg_qwid'].GetValue()
            nsmooth = int(self.wids['bkg_nsmooth'].GetValue())
            cheb_order = int(self.wids['bkg_porder'].GetValue())
        except:
            return
        label = self.current_label
        if label not in self.datasets:
            return
        dset = self.datasets[label]
        dset.bkgd = calc_bgr(dset, qwid=qwid, nsmooth=nsmooth,
                             cheb_order=cheb_order)
        if 'back' not in self.wids['plotone'].GetStringSelection().lower():
            self.wids['plotone'].SetSelection(1)
        else:
            self.onPlotOne()

    def show_dataset(self, event=None, label=None):
        # print('show xd1d ', event, label)
        if label is None and event is not None:
            label = str(event.GetString())
        if label not in self.datasets:
            return

        self.current_label = label
        dset = self.datasets[label]

        if not hasattr(dset, 'scale'):
            dset.scale = dset.I.max()
            dset.scale_method = 'raw_max'
            dset.auto_scale = True
            dset.bkg_qwid = 0.1
            dset.bkg_nsmooth = 30
            dset.bkg_porder = 40

        bkgd = getattr(dset, 'bkgd', None)
        if (bkgd is None
            or (isinstance(bkgd, np.ndarray)
                and (bkgd.sum() < 0.5/len(bkgd)))):
            dset.bkgd = calc_bgr(dset)

        meth_desc = keyof(SCALE_METHODS, dset.scale_method, 'raw_max')

        self.wids['scale_method'].SetStringSelection(meth_desc)
        self.wids['auto_scale'].SetValue(dset.auto_scale)
        self.wids['scale'].SetValue(dset.scale)
        self.wids['energy_ev'].SetLabel("%.1f" % (dset.energy*1000.0))
        self.wids['wavelength'].SetLabel("%.6f" % (PLANCK_HC/(dset.energy*1000.0)))

        self.wids['bkg_qwid'].SetValue(dset.bkg_qwid)
        self.wids['bkg_nsmooth'].SetValue(dset.bkg_nsmooth)
        self.wids['bkg_porder'].SetValue(dset.bkg_porder)

        self.onPlotOne(label=label)

    def set_scale(self, event=None, value=-1.0):
        label = self.current_label
        if label not in self.datasets:
            return
        if value < 0:
            value = self.wids['scale'].GetValue()
        self.datasets[label].scale = value # self.wids['scale'].GetValue()

    def auto_scale(self, event=None):
        label = self.current_label
        if label not in self.datasets:
            return
        dset = self.datasets[label]
        dset.auto_scale = self.wids['auto_scale'].IsChecked()
        self.wids['scale_method'].Enable(dset.auto_scale)

        if dset.auto_scale:
            self.scale_data(dset, with_plot=True)

    def scale_data(self, dset, with_plot=True):
        meth_name = self.wids['scale_method'].GetStringSelection()

        meth = dset.scale_method = SCALE_METHODS[meth_name]

        # if not meth.startswith('raw'):
        qwid = self.wids['bkg_qwid'].GetValue()
        nsmooth = int(self.wids['bkg_nsmooth'].GetValue())
        cheb_order = int(self.wids['bkg_porder'].GetValue())
        dset.bkgd = calc_bgr(dset, qwid=qwid, nsmooth=nsmooth,
                            cheb_order=cheb_order)
        dset.bkg_qwid = qwid
        dset.bkg_nmsooth = nsmooth
        dset.bkg_porder = cheb_order

        scale =  -1
        if meth == 'raw_max':
            scale = dset.I.max()
        elif meth == 'raw_mean':
            scale = dset.I.mean()
        elif meth == 'sub_max':
            scale = (dset.I - dset.bkgd).max()
        elif meth == 'sub_mean':
            scale = (dset.I - dset.bkgd).mean()
        elif meth == 'bkg_max':
            scale = (dset.bkgd).max()
        elif meth == 'bkg_mean':
            scale = (dset.bkgd).mean()

        if scale > 0:
            self.wids['scale'].SetValue(scale)
            if with_plot:
                self.onPlotOne()

    def rename_dataset(self, newlabel):
        dset = self.datasets.pop(self.current_label)
        dset.label = newlabel
        self.datasets[newlabel] = dset
        self.current_label = newlabel

        self.filelist.Clear()
        for name in self.datasets:
            self.filelist.Append(name)


    def onRenameDataset(self, event=None):
        RenameDialog(self, self.current_label, self.rename_dataset).Show()


    def remove_dataset(self, dname=None, event=None):
        if dname in self.datasets:
            self.datasets.pop(dname)

        self.filelist.Clear()
        for name in self.datasets:
            self.filelist.Append(name)


    def remove_selected_datasets(self, event=None):
        sel = []
        for checked in self.filelist.GetCheckedStrings():
            sel.append(str(checked))
        if len(sel) < 1:
            return

        dlg = RemoveDialog(self, sel)
        res = dlg.GetResponse()
        dlg.Destroy()

        if res.ok:
            all = self.filelist.GetItems()
            for dname in sel:
                self.datasets.pop(dname)
                all.remove(dname)

            self.filelist.Clear()
            for name in all:
                self.filelist.Append(name)

    def get_imdisplay(self, win=1):
        wintitle='XRD Image Window %i' % win
        opts = dict(wintitle=wintitle, win=win, image=True)
        self.img_display = self.larch.symtable._plotter.get_display(**opts)
        return self.img_display

    def get_display(self, win=1, stacked=False):
        wintitle='XRD Plot Window %i' % win
        opts = dict(wintitle=wintitle, stacked=stacked, win=win, linewidth=3)
        self.plot_display = self.larch.symtable._plotter.get_display(**opts)
        return self.plot_display

    def plot_dset(self, dset, plottype, newplot=True):
        win    = int(self.wids['plot_win'].GetStringSelection())
        xscale = self.wids['xscale'].GetSelection()
        opts = {'show_legend': True, 'xmax': None,
                'xlabel':  self.wids['xscale'].GetStringSelection(),
                'ylabel':'Scaled Intensity',
                'label': dset.label}

        xdat = dset.q
        if xscale == 2:
           xdat = dset.d
           opts['xmax'] = min(12.0, max(xdat))
        elif xscale == 1:
            xdat = dset.twth

        ydat = 1.0*dset.I/dset.scale
        if plottype == 'sub':
            ydat = 1.0*(dset.I-dset.bkgd)/dset.scale
            opts['ylabel'] = 'Scaled (Intensity - Background)'

        pframe = self.get_display(win=win)
        plot = pframe.plot if newplot else pframe.oplot
        plot(xdat, ydat, **opts)
        if plottype == 'raw+bkg':
            y2dat = 1.0*dset.bkgd/dset.scale
            opts['ylabel'] = 'Scaled Intensity with Background'
            opts['label'] = 'background'
            pframe.oplot(xdat, y2dat, **opts)

    def onPlotOne(self, event=None, label=None):
        if label is None:
            label = self.current_label
        if label not in self.datasets:
            return
        dset = self.datasets[label]
        self.last_plot_type = 'one'
        plottype = PLOT_TYPES.get(self.wids['plotone'].GetStringSelection(), 'raw')
        self.plot_dset(dset, plottype, newplot=True)
        wx.CallAfter(self.SetFocus)

    def onPlotSel(self, event=None):
        labels = self.filelist.GetCheckedStrings()
        if len(labels) < 1:
            return
        self.last_plot_type = 'multi'
        plottype = PLOT_TYPES.get(self.wids['plotsel'].GetStringSelection(), 'raw')
        newplot = True
        for label in labels:
            dset = self.datasets.get(label, None)
            if dset is not None:
                self.plot_dset(dset, plottype, newplot=newplot)
                newplot = False
        wx.CallAfter(self.SetFocus)

    def onPlotEither(self, event=None):
        if self.last_plot_type == 'multi':
            self.onPlotSel(event=event)
        else:
            self.onPlotOne(event=event)

    def add_data(self, dataset, label=None,  **kws):
        if label is None:
            label = 'XRD pattern'
        if label in self.datasets:
            print('label already in datasets: ', label )
        else:
            self.filelist.Append(label)
            self.datasets[label] = dataset
            self.show_dataset(label=label)

class XRD1DApp(LarchWxApp):
    def __init__(self, **kws):
        LarchWxApp.__init__(self)

    def createApp(self):
        frame = XRD1DFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True

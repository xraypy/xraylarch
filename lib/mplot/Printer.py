#!/usr/bin/python
##
## wxPython Printer class for Matplotlib WX backend.
##
import wx

class PrintoutWx(wx.Printout):
    """Simple wrapper around wx Printout class -- all the real work
    here is scaling the matplotlib canvas bitmap to the current
    printer's definition.
    """
    def __init__(self, canvas, width=6.0,margin=0.25, title='MPlot Figure'):
        wx.Printout.__init__(self,title=title)
        self.canvas = canvas
        self.width  = width
        self.margin = margin

    def HasPage(self, page):
        return page <= 1

    def GetPageInfo(self):
        return (1, 1, 1, 1)

    def OnPrintPage(self, page):
        self.canvas.draw()

        ppw,pph = self.GetPPIPrinter()      # printer's pixels per in
        pgw,pgh = self.GetPageSizePixels()  # page size in pixels
        grw,grh = self.canvas.GetSizeTuple()
        dc      = self.GetDC()
        dcw,dch = dc.GetSize()

        # save current figure dpi resolution and bg color,
        # so that we can temporarily set them to the dpi of
        # the printer, and the bg color to white
        bgcolor   = self.canvas.figure.get_facecolor()
        fig_dpi   = self.canvas.figure.dpi

        # draw the bitmap, scaled appropriately
        vscale    = float(ppw) / fig_dpi

        # set figure resolution,bg color for printer
        self.canvas.figure.dpi = ppw
        self.canvas.figure.set_facecolor('#FFFFFF')
        self.canvas.bitmap.SetWidth(  int(self.canvas.bitmap.GetWidth() * vscale))
        self.canvas.bitmap.SetHeight( int(self.canvas.bitmap.GetHeight()* vscale))
        self.canvas.draw()
        # page may need additional scaling on preview
        page_scale = 1.0
        if self.IsPreview():   page_scale = float(dcw)/pgw

        # get margin in pixels = (margin in in) * (pixels/in)
        top_margin  = int(self.margin * pph * page_scale)
        left_margin = int(self.margin * ppw * page_scale)

        # set scale so that width of output is self.width inches
        # (assuming grw is size of graph in inches....)
        user_scale = (self.width * fig_dpi * page_scale)/float(grw)

        dc.SetDeviceOrigin(left_margin,top_margin)
        dc.SetUserScale(user_scale,user_scale)

        # this cute little number avoid API inconsistencies in wx
        try:
            dc.DrawBitmap(self.canvas.bitmap, 0, 0)
        except:
            pass
        # restore original figure  resolution
        self.canvas.figure.set_facecolor(bgcolor)
        self.canvas.figure.dpi = fig_dpi
        self.canvas.draw()
        return True

class Printer:
    def __init__(self, parent, canvas=None, width=6.0, margin=0.5):
        """initialize printer settings using wx methods"""

        self.parent = parent
        self.canvas = canvas
        self.pwidth = width
        self.pmargin= margin

        self.printerData = wx.PrintData()
        self.printerData.SetPaperId(wx.PAPER_LETTER)
        self.printerData.SetPrintMode(wx.PRINT_MODE_PRINTER)
        self.printerPageData= wx.PageSetupDialogData()
        self.printerPageData.SetMarginBottomRight((25,25))
        self.printerPageData.SetMarginTopLeft((25,25))
        self.printerPageData.SetPrintData(self.printerData)

    def Setup(self, event=None):
        """set up figure for printing.  Using the standard wx Printer
        Setup Dialog. """

        if hasattr(self, 'printerData'):
            data = wx.PageSetupDialogData()
            data.SetPrintData(self.printerData)
        else:
            data = wx.PageSetupDialogData()
        data.SetMarginTopLeft( (15, 15) )
        data.SetMarginBottomRight( (15, 15) )

        dlg = wx.PageSetupDialog(None, data)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetPageSetupData()
            tl = data.GetMarginTopLeft()
            br = data.GetMarginBottomRight()
        self.printerData = wx.PrintData(data.GetPrintData())
        dlg.Destroy()

    def Preview(self, event=None):
        """ generate Print Preview with wx Print mechanism"""
        po1  = PrintoutWx(self.canvas,
                          width=self.pwidth,   margin=self.pmargin)
        po2  = PrintoutWx(self.canvas,
                          width=self.pwidth,   margin=self.pmargin)
        self.preview = wx.PrintPreview(po1,po2,self.printerData)

        if self.preview.Ok():
            self.preview.SetZoom(65)
            frameInst= self.parent
            while not isinstance(frameInst, wx.Frame):
                frameInst= frameInst.GetParent()
            frame = wx.PreviewFrame(self.preview, frameInst, "Preview")
            frame.Initialize()
            frame.SetSize((850,650))
            frame.Centre(wx.BOTH)
            frame.Show(True)

    def Print(self, event=None):
        """ Print figure using wx Print mechanism"""
        pdd = wx.PrintDialogData()
        pdd.SetPrintData(self.printerData)
        pdd.SetToPage(1)
        printer  = wx.Printer(pdd)
        printout = PrintoutWx(self.canvas, width=self.pwidth,   margin=self.pmargin)
        print_ok = printer.Print(self.parent, printout, True)

        if not print_ok and not printer.GetLastError() == wx.PRINTER_CANCELLED:
            wx.MessageBox("""There was a problem printing.
            Perhaps your current printer is not set correctly?""",
                          "Printing", wx.OK)
        printout.Destroy()


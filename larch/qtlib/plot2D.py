#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom version of SILX Plot2D
=============================
"""
import time
import numpy as np
from silx.gui.plot import Plot2D as silxPlot2D
from larch.utils.logging import getLogger


class Plot2D(silxPlot2D):
    """Custom Plot2D instance targeted to 2D images"""

    def __init__(self, parent=None, backend=None, logger=None, title="Plot2D"):

        super(Plot2D, self).__init__(parent=parent, backend=backend)

        self._logger = logger or getLogger("Plot2D")
        self._index = None
        self._title = title
        self.setWindowTitle(self._title)
        self._image = None
        self._mask = None
        self._origin = (0, 0)
        self._scale = (1, 1)
        self._xlabel = 'X'
        self._ylabel = 'Y'
        self.setKeepDataAspectRatio(True)
        self.getDefaultColormap().setName('viridis')

    def _drawContours(self, values, color='gray',
                      plot_timeout=100, plot_method='curve'):
        """Draw iso contours for given values

        Parameters
        ----------
        values : list or array
            intensities at which to find contours
        color : string (optional)
            color of contours (among common color names) ['gray']
        plot_timeout : int (optional)
            time in seconds befor the plot is interrupted
        plot_method : str (optional)
            method to use for the contour plot
            'curve' -> self.addCurve, polygons as from find_contours
            'curve_max' -> self.addCurve, one polygon (max length)
            'curve_merge' -> self.addCurve, one polygon (concatenate)
            'scatter' -> self.addScatter (only points)
        """
        if self._ms is None:
            return
        ipolygon = 0
        totTime = 0
        for ivalue, value in enumerate(values):
            startTime = time.time()
            polygons = self._ms.find_contours(value)
            polTime = time.time()
            self._logger.debug(f"Found {len(polygons)} polygon at level {value}")
            totTime += polTime - startTime
            # prepare polygons list for plot_method
            if len(polygons) == 0:
                continue
            if len(polygons) > 1:
                if (plot_method == 'curve_max'):
                    from sloth.utils.arrays import imax
                    lengths = [len(x) for x in polygons]
                    polygons = [polygons[imax(lengths)]]
                elif (plot_method == 'curve_merge') or (plot_method == 'scatter'):
                    polygons = [np.concatenate(polygons, axis=0)]
                else:
                    pass
            # define default contour style
            contourStyle = {"linestyle": "-",
                            "linewidth": 0.5,
                            "color": color}
            for polygon in polygons:
                legend = "polygon-%d" % ipolygon
                xpoly = polygon[:, 1]
                ypoly = polygon[:, 0]
                xscale = np.ones_like(xpoly) * self._scale[0]
                yscale = np.ones_like(ypoly) * self._scale[1]
                xorigin = np.ones_like(xpoly) * self._origin[0]
                yorigin = np.ones_like(ypoly) * self._origin[1]
                x = xpoly * xscale + xorigin
                y = ypoly * yscale + yorigin
                # plot timeout
                if totTime >= plot_timeout:
                    self._logger.warning("Plot contours time out reached!")
                    break
                # plot methods
                if plot_method == 'scatter':
                    from silx.gui.colors import (Colormap, rgba)
                    cm = Colormap()
                    cm.setColormapLUT([rgba(color)])
                    arrval = np.ones_like(x)*value
                    self.addScatter(x, y, arrval, symbol='.', colormap=cm)
                else:
                    self.addCurve(x=x, y=y, legend=legend, resetzoom=False,
                                  **contourStyle)
                pltTime = time.time()
                totTime += pltTime - polTime
                ipolygon += 1

    def addContours(self, nlevels, algo='merge', **draw_kwars):
        """Add contour lines to plot

        Parameters
        ----------
        nlevels : int
            number of contour levels to plot

        algo : str (optional)
            marching squares algorithm implementation
            'merge' -> silx
            'skimage' -> scikit-image
        color : str, optional
            color of contour lines ['gray']
        linestyle : str, optional
            line style of contour lines ['-']
        linewidth : int, optional
            line width of contour lines [1]

        Returns
        -------
        None
        """
        image = self._image
        mask = self._mask
        if image is None:
            self._logger.error('add image first!')
        if algo == 'merge':
            from silx.image.marchingsquares._mergeimpl import MarchingSquaresMergeImpl
            self._ms = MarchingSquaresMergeImpl(image, mask=mask)
        elif algo == 'skimage':
            try:
                import skimage
                from silx.image.marchingsquares._skimage import MarchingSquaresSciKitImage
                self._ms = MarchingSquaresSciKitImage(image,
                                                      mask=mask)
            except ImportError:
                self._logger.error('skimage not found')
                self._ms = None
        else:
            self._ms = None
        imgmin, imgmax = image.min(), image.max()
        delta = (imgmax - imgmin) / nlevels
        values = np.arange(imgmin, imgmax, delta)
        self._drawContours(values, **draw_kwars)

    def index(self):
        if self._index is None:
            self._index = 0
        return self._index

    def setIndex(self, value):
        self._index = value
        if self._index is not None:
            self.setWindowTitle('{0}: {1}'.format(self._index, self._title))

    def reset(self):
        self.clear()
        self.setGraphTitle()
        self.setGraphXLabel('X')
        # self.setGraphXLimits(0, 100)
        self.setGraphYLabel('Y')
        # self.setGraphYLimits(0, 100)

    def addImage(self, data, x=None, y=None,
                 title=None, xlabel=None, ylabel=None,
                 vmin=None, vmax=None, **kwargs):
        """Custom addImage

        Parameters
        ----------
        data : array
        x, y : None or array (optional)
            x, y to set origin and scale (both should be given!)
        title : str
            set self.setGraphTitle(str) / self.setWindowTitle(str)
        xlabel, ylabel : None or str (optional)
            set self.setGraphXLabel / self.setGraphYLabel
        vmin, vmax : float (optional)
            intensity values of the colormap min/max
        """
        self._image = data
        self._x = x
        self._y = y
        if (x is not None) and (y is not None):
            self._origin = (np.min(x), np.min(y))
            self._scale = (x[1]-x[0], y[1]-y[0])
        if title is not None:
            self._title = title
            self.setGraphTitle(title)
            if self._index is not None:
                self.setWindowTitle('{0}: {1}'.format(self._index, self._title))
            else:
                self.setWindowTitle(self._title)
        if xlabel is not None:
            self._xlabel = xlabel
            self.setGraphXLabel(xlabel)
        if ylabel is not None:
            self._ylabel = ylabel
            self.setGraphYLabel(ylabel)
        if (vmin is None):
            vmin = self._image.min()
        if (vmax is None):
            vmax = self._image.max()
        self.getDefaultColormap().setVRange(vmin, vmax)
        return super(Plot2D, self).addImage(data, origin=self._origin,
                                            scale=self._scale,
                                            **kwargs)


def dummy_gauss_image(x=None, y=None,
                      xhalfrng=1.5, yhalfrng=None, xcen=0.5, ycen=0.9,
                      xnpts=1024, ynpts=None, xsigma=0.55, ysigma=0.25,
                      noise=0.3):
    """Create a dummy 2D Gaussian image with noise

    Parameters
    ----------
    x, y : 1D arrays (optional)
        arrays where to generate the image [None -> generated]
    xhalfrng : float (optional)
        half range of the X axis [1.5]
    yhalfrng : float or None (optional)
        half range of the Y axis [None -> xhalfrng]
    xcen : float (optional)
        X center [0.5]
    ycen : float (optional)
        Y center [0.9]
    xnpts : int (optional)
        number of points X [1024]
    ynpts : int or None (optional)
        number of points Y [None -> xnpts]
    xsigma : float (optional)
        sigma X [0.55]
    ysigma : float (optional)
        sigma Y [0.25]
    noise : float (optional)
        random noise level between 0 and 1 [0.3]

    Returns
    -------
    x, y : 1D arrays
    signal : 2D array
    """
    if yhalfrng is None:
        yhalfrng = xhalfrng
    if ycen is None:
        ycen = xcen
    if ynpts is None:
        ynpts = xnpts
    if x is None:
        x = np.linspace(xcen-xhalfrng, xcen+xhalfrng, xnpts)
    if y is None:
        y = np.linspace(ycen-yhalfrng, ycen+yhalfrng, ynpts)
    xx, yy = np.meshgrid(x, y)
    signal = np.exp(-((xx-xcen)**2 / (2*xsigma**2) +
                      ((yy-ycen)**2 / (2*ysigma**2))))
    # add noise
    signal += noise * np.random.random(size=signal.shape)
    return x, y, signal


def main(contour_levels=5, noise=0.1, compare_with_matplolib=False,
         plot_method='curve'):
    """Run a Qt app with the widget"""
    from silx import sx
    sx.enable_gui()
    xhalfrng = 10.5
    yhalfrng = 5.5
    npts = 1024
    xcen = 0
    ycen = 0
    x = np.linspace(xcen-0.7*xhalfrng, xcen+1.3*xhalfrng, npts)
    y = np.linspace(ycen-0.7*yhalfrng, ycen+1.3*yhalfrng, npts)
    x1, y1, signal1 = dummy_gauss_image(x=x, y=y, xcen=xcen, ycen=ycen,
                                        xsigma=3, ysigma=1.1,
                                        noise=noise)
    x2, y2, signal2 = dummy_gauss_image(x=x, y=y,
                                        xcen=4.2, ycen=2.2,
                                        xsigma=3, ysigma=2.1,
                                        noise=noise)
    signal = signal1 + 0.8*signal2
    p = Plot2D(backend='matplotlib')
    p.addImage(signal, x=x, y=y, xlabel='X', ylabel='Y')
    p.addContours(contour_levels, plot_method=plot_method)
    p.show()

    if compare_with_matplolib:
        import matplotlib.pyplot as plt
        from matplotlib import cm
        plt.ion()
        plt.close('all')
        fig, ax = plt.subplots()
        imgMin, imgMax = np.min(signal), np.max(signal)
        values = np.linspace(imgMin, imgMax, contour_levels)
        extent = (x.min(), x.max(), y.min(), y.max())
        ax.imshow(signal, origin='lower', extent=extent,
                  cmap=cm.viridis)
        ax.contour(x, y, signal, values, origin='lower', extent=extent,
                   colors='gray', linewidths=1)
        ax.set_title("pure matplotlib")
        plt.show()

    input("Press enter to close window")


if __name__ == '__main__':
    main()

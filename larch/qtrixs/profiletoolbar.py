#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RIXS profile toolbar
====================

A modified version of the SILX profile toolbar.
"""
from itertools import cycle
from silx.gui.plot.Profile import (ProfileToolBar, createProfile)


_DEFAULT_OVERLAY_COLORS = cycle(['#1F77B4', '#AEC7E8', '#FF7F0E', '#FFBB78',
                                 '#2CA02C', '#98DF8A', '#D62728', '#FF9896',
                                 '#9467BD', '#C5B0D5', '#8C564B', '#C49C94',
                                 '#E377C2', '#F7B6D2', '#7F7F7F', '#C7C7C7',
                                 '#BCBD22', '#DBDB8D', '#17BECF', '#9EDAE5'])


class RixsProfileToolBar(ProfileToolBar):
    """RIXS-adapted Profile (=Cuts) toolbar"""

    def __init__(self, parent=None, plot=None, profileWindow=None,
                 overlayColors=None, title='RIXS profile'):
        """Constructor"""
        super(RixsProfileToolBar, self).__init__(parent=parent, plot=plot,
                                                 profileWindow=profileWindow,
                                                 title=title)

        self._overlayColors = overlayColors or _DEFAULT_OVERLAY_COLORS

    def _getNewColor(self):
        return next(self._overlayColors)

    def updateProfile(self):
        """Update the displayed profile and profile ROI.
        This uses the current active image of the plot and the current ROI.
        """
        image = self.plot.getActiveImage()
        if image is None:
            return

        self._overlayColor = self._getNewColor()

        self._createProfile(currentData=image.getData(copy=False),
                            origin=image.getOrigin(), scale=image.getScale(),
                            colormap=None, z=image.getZValue(),
                            method=self.getProfileMethod())


    def _createProfile(self, currentData, origin, scale, colormap, z, method):
        """Create the profile line for the the given image.
        :param numpy.ndarray currentData: the image or the stack of images
            on which we compute the profile
        :param origin: (ox, oy) the offset from origin
        :type origin: 2-tuple of float
        :param scale: (sx, sy) the scale to use
        :type scale: 2-tuple of float
        :param dict colormap: The colormap to use
        :param int z: The z layer of the image
        """
        if self._roiInfo is None:
            return

        coords, profile, area, profileName, xLabel = createProfile(
            roiInfo=self._roiInfo,
            currentData=currentData,
            origin=origin,
            scale=scale,
            lineWidth=self.lineWidthSpinBox.value(),
            method=method)

        profilePlot = self.getProfilePlot()
        plotTitle = self.plot.getGraphTitle()

        profilePlot.setGraphTitle("Profiles")
        profilePlot.getXAxis().setLabel(xLabel)

        profileName = "{0}: {1}".format(plotTitle, profileName)

        dataIs3D = len(currentData.shape) > 2
        if dataIs3D:
            profileScale = (coords[-1] - coords[0]) / profile.shape[1], 1
            profilePlot.addImage(profile,
                                 legend=profileName,
                                 colormap=colormap,
                                 origin=(coords[0], 0),
                                 scale=profileScale)
            profilePlot.getYAxis().setLabel("Frame index (depth)")
        else:
            profilePlot.addCurve(coords,
                                 profile[0],
                                 legend=profileName,
                                 color=self.overlayColor)

        self.plot.addItem(area[0], area[1],
                          legend=self._POLYGON_LEGEND,
                          color=self.overlayColor,
                          shape='polygon', fill=True,
                          replace=False, z=z + 1)

        self._showProfileMainWindow()




if __name__ == '__main__':
    pass

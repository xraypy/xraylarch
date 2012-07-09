#!/usr/bin/env python

########################################################################
# MCA class
# From Mca written by Mark Rivers
# Modified for tdl
########################################################################

"""
This module defines a device-independent MultiChannel Analyzer (MCA) class,
and a number of support classes.

Author:
    Mark Rivers

Created:
    Sept. 16, 2002.  Based on my earlier IDL code.

Modifications:
    Sept. 24, 2002 MLR
        - Fixed bug in saving ROIs in Meds
        - Fixed bug reading environment variables
    Sept. 25, 2002
        - Changed McaPeak.get_calibration to McaPeak.update, make more fields
          consistent.
        - Added McaPeak.ignore field to fix problem with other fields getting
          clobbered in fitPeaks.
        - Fixed serious bug in .d_to_channel()
    Mar  18, 2003 MN
        - changes to include ICR in Mca, epicsMca, and Med classes:
        - added icr data member to McaElapsed
        - added printing of icr in write_ascii_file
"""

import numpy as np
import copy
import math
import deadtime

HC = 12.3984193 # hc in keV*Ang
########################################################################
class McaEnvironment:
    """
    The "environment" or related parameters for an Mca.  These might include
    things like motor positions, temperature, anything that describes the
    experiment.

    An Mca object has an associated list of McaEnvironment objects, since there
    are typically many such parameters required to describe an experiment.

    Fields:
        .name         # A string name of this parameter, e.g. "13IDD:m1"
        .value        # A string value of this parameter,  e.g. "14.223"
        .description  # A string description of this parameter, e.g. "X stage"
    """
    def __init__(self, name='', value='', description=''):
        self.name = name
        self.value = value
        self.description = description


########################################################################
class McaCalibration:
    """
    Class defining an Mca calibration.  The calibration equation is
        energy = .offset + .slope*channel + .quad*channel**2
    where the first channel is channel 0, and thus the energy of the first
    channel is .offset.

    Fields:
        .offset    # Offset
        .slope     # Slope
        .quad      # Quadratic
        .units     # Calibration units, a string
        .two_theta # 2-theta of this Mca for energy-dispersive diffraction
    """
    def __init__(self, offset=0., slope=1.0, quad=0., units='keV', two_theta=10.):
        """
        There is a keyword with the same name as each field, so the object can
        be initialized when it is created.
        """
        self.offset    = offset
        self.slope     = slope
        self.quad      = quad
        self.units     = units
        self.two_theta = two_theta

    ########################################################################
    def channel_to_energy(self, channels):
        """
        Converts channels to energy using the current calibration values for the
        Mca.  This routine can convert a single channel number or an array of
        channel numbers.  Users are strongly encouraged to use this function
        rather than implement the conversion calculation themselves, since it
        will be updated if additional calibration parameters (cubic, etc.) are
        added.

        Inputs:
            channels: The channel numbers to be converted to energy.  This can be
                      a single number or a sequence of channel numbers.

        Outputs:
            This function returns the equivalent energy for the input channels.

        Example:
            channels = [100, 200, 300]
            energy = mca.channel_to_energy(channels)
        """
        c  = np.asarray(channels)
        return self.offset +  c * (self.slope + c * self.quad)

    ########################################################################
    def energy_to_channel(self, energy, clip=0):
        """
        Converts energy to channels using the current calibration values for the
        Mca.  This routine can convert a single energy or an array of energy
        values.  Users are strongly encouraged to use this function rather than
        implement the conversion calculation themselves, since it will be updated
        if additional calibration parameters are added.

        Inputs:
            energy: The energy values to be converted to channels. This can be a
                    single number or a sequence energy values.

        Keywords:
            clip: Set this flag to >0 to clip the returned values to be between
                  0 and clip-1.  The default is not to clip.

        Outputs:
            This function returns the closest equivalent channel for the input
            energy.  Note that it does not generate an error if the channel number
            is outside the range 0 to (nchans-1), which will happen if the energy
            is outside the range for the calibration values of the Mca.

        Example:
            channel = mca.energy_to_channel(5.985)
        """
        if (self.quad == 0.0):
            channel = ((energy - self.offset) / self.slope)
        else:
            # Use the quadratic formula, use some shorthand
            a = self.quad
            b = self.slope
            c = self.offset - energy
            # There are 2 roots.  I think we always want the "+" root?
            channel = (-b + np.sqrt(b**2 - 4.*a*c))/(2.*a)
        channel = np.around(channel)
        if (clip > 0):
            #nchans = len(self.data)
            nchans  = clip
            channel = np.clip(channel, 0, nchans-1)

        return int(channel)

    ########################################################################
    def channel_to_d(self, channels):
        """
        Converts channels to "d-spacing" using the current calibration values for
        the Mca.  This routine can convert a single channel number or an array of
        channel numbers.  Users are strongly encouraged to use this function
        rather than implement the conversion calculation themselves, since it
        will be updated if additional calibration parameters are added.  This
        routine is useful for energy dispersive diffraction experiments.  It uses
        both the energy calibration parameters and the "two-theta" calibration
        parameter.

        Inputs:
            channels: The channel numbers to be converted to "d-spacing".
                      This can be a single number or a list of channel numbers.

        Outputs:
            This function returns the equivalent "d-spacing" for the input channels.
            The output units are in Angstroms.

        Restrictions:
            This function assumes that the units of the energy calibration are keV
            and that the units of "two-theta" are degrees.

        Example:
            channels = [100,200,300]
            d = mca.channel_to_d(channels)
        """
        e = self.channel_to_energy(channels)
        return 12.398 / (2. * e * math.sin(self.two_theta*math.pi/180.))


    ########################################################################
    def d_to_channel(self, d, clip=0):
        """
        Converts "d-spacing" to channels using the current calibration values
        for the Mca.  This routine can convert a single "d-spacing" or an array
        of "d-spacings".  Users are strongly encouraged to use this function
        rather than implement the conversion calculation themselves, since it
        will be updated if additional calibration parameters are added.
        This routine is useful for energy dispersive diffraction experiments.
        It uses both the energy calibration parameters and the "two-theta"
        calibration parameter.

        Inputs:
            d:  The "d-spacing" values to be converted to channels.
                This can be a single number or an array of values.

        Keywords:
            clip: Set this flag to 1 to clip the returned values to be between
                  0 and nchans-1.  The default is not to clip.

        Outputs:
            This function returns the closest equivalent channel for the input
            "d-spacing". Note that it does not generate an error if the channel
            number is outside the range 0 to (nchans-1), which will happen if the
            "d-spacing" is outside the range for the calibration values of the Mca.

        Example:
            channel = mca.d_to_chan(1.598)
        """
        e = 12.398 / (2. * d * math.sin(self.two_theta*math.pi/180./2.))
        return self.energy_to_channel(e, clip=clip)


########################################################################
class McaElapsed:
    """
    The elapsed time and counts for an Mca.

    Fields:
        .start_time   # Start time and date, a string
        .live_time    # Elapsed live time in seconds
        .real_time    # Elapsed real time in seconds
        .read_time    # Time that the Mca was last read in seconds
        .total_counts # Total counts between the preset start and stop channels
        .input_counts # Actual total input counts (eg given by detector software)
                      # Note total_counts and input counts ARE NOT time normalized
                      #
        .tau          # Factor for deadtime/detector saturation calculations, ie
                      #  ocr = icr * exp(-icr*tau)
        .icr_calc     # Calculated input count rate from above expression
        .cor_factor   # Calculated correction factor based on icr,ocr,lt,rt
                      # data_corrected = data * cor_factor

    Note if input_counts are read from the data file then there is no need for tau
    values (and hence icr_calc is not used) - ie we assume the detector
    provides the icr value.

    The application of corrections uses the following logic:
    if tau > 0 this will be used in the correction factor calculation
    if tau = 0 then we assume ocr = icr in the correction factor calculation
    if tau < 0 (or None):
       if input_counts > 0 this will be used for icr in the factor calculation
       if input_counts <= 0 we assume ocr = icr in the correction factor calculation

    """
    def __init__(self, start_time='', live_time=0., real_time=0.,
                 read_time=0., total_counts=0., input_counts=0., tau=-1.0):
        self.start_time   = start_time
        self.live_time    = live_time
        self.real_time    = real_time
        self.read_time    = read_time
        self.total_counts = total_counts
        self.input_counts = input_counts
        self.tau          = tau
        self.icr_calc     = None
        self.cor_factor   = 1.0
        self.calc_correction()

    def __repr__(self):
        lout = "    Real Time= %f, Live Time= %f, OCR= %6.0f, ICR= %6.0f" % \
                        (self.real_time, self.live_time,
                         self.total_counts / self.live_time,
                         self.input_counts / self.live_time)
        if self.icr_calc != None:
            lout = lout + ",Tau = %6.0f, ICR_Calc= %6.0f, Correction= %5.2f\n" % \
                             (self.tau, self.icr_calc, self.cor_factor)
        else:
            lout = lout + ", ICR_Calc= None, Correction= %5.2f\n" % \
                             (self.cor_factor)
        return lout

    def calc_correction(self):
        """
        if tau > 0 this will be used in the correction factor calculation
        if tau = 0 then we assume ocr = icr in the correction factor calculation, ie only lt correction
                   (note deadtime.calc_icr handles above two conditions)
        if tau < 0 (or None):
           if input_counts > 0 this will be used for icr in the factor calculation
           if input_counts <= 0 we assume ocr = icr in the correction factor calculation, ie only lt correction
        """
        if (self.live_time <=0) or (self.real_time <=0):
            self.cor_factor  = 1.0
            return

        if self.total_counts > 0:
            ocr = self.total_counts / self.live_time
        else:
            ocr = None

        if self.tau >= 0:
            self.icr_calc = deadtime.calc_icr(ocr,self.tau)
            icr = self.icr_calc
        elif self.input_counts > 0:
            icr = self.input_counts / self.live_time
        else:
            icr = ocr = None
        self.cor_factor  = deadtime.correction_factor(self.real_time,
                                                      self.live_time,
                                                      icr = icr,
                                                      ocr = ocr)
        if self.cor_factor <= 0:
            print "Error computing data correction factor, setting to 1"
            self.cor_factor = 1.0


########################################################################
class McaROI:
    """
    Class that defines a Region-Of-Interest (ROI)
    Fields
        .units     # Can be "channel", "keV", "eV"
        .left      # Left channel
        .right     # Right channel
        .centroid  # Centroid channel
        .fwhm      # Width
        .bgd_width # Number of channels to use for background subtraction
        .use       # Flag: should the ROI should be used for energy calibration
        .preset    # Flag: is this ROI controlling preset acquisition
        .label     # Name of the ROI
        .d_spacing # Lattice spacing if a diffraction peak
        .energy    # Energy of the centroid for energy calibration
    """
    def __init__(self, units="channel", left=0., right=0., centroid=0., fwhm=0.,
                 bgd_width=0, use=1, preset=0, label='', d_spacing=0., energy=0.):
        """
        Keywords:
            There is a keyword with the same name as each attribute that can be
            used to initialize the ROI when it is created.
        """
        self.units     = units
        self.left      = left
        self.right     = right
        self.centroid  = centroid
        self.fwhm      = fwhm
        self.bgd_width = bgd_width
        self.use       = use
        self.preset    = preset
        self.label     = label
        self.d_spacing = d_spacing
        self.energy    = energy
        self.total     = 0
        self.net       = 0

    def __cmp__(self, other):
        """
        Comparison operator.  The .left field is used to define ROI ordering
        """
        return (self.left - other.left)

    def __repr__(self):
        lout = "    ROI= %s: , units = %s," % (self.label, self.units)
        lout = lout + " left =%f, right = %f, nbgr =%d" % (self.left,self.right,self.bgd_width)
        lout = lout + " total =%g, net = %g\n" % (self.total,self.net)
        #lout = lout + "centroid = %f, fwhm = %f\n" % (self.centroid,self.fwhm)
        return lout

    def update_counts(self, data, background_width=1):
        """
        Update the total and net.
        Note this sets roi units should be set to channel

        Arguments:
            data: Array or list of data.

        Keywords:
            background_width: Set this keyword to set the width of the
                              background region on either side of the peaks
                              when computing net counts.  The default is 1.
        """
        nchans = len(data)
        def_background_width = background_width

        if self.bgd_width > 0 and def_background_width==1:
            background_width = int(self.bgd_width)
        else:
            background_width = int(def_background_width)
            self.bgd_width    = def_background_width

        left = self.left
        ll = max((left-background_width+1), 0)
        if (background_width > 0):
             bgd_left = sum(data[ll:(left+1)]) / (left-ll+1)
        else:
            bgd_left = 0.

        right = self.right
        rr = min((right+background_width-1), nchans-1)
        if (background_width > 0):
            bgd_right = sum(data[right:rr+1]) / (rr-right+1)
        else:
            bgd_right = 0.

        #total cts array
        total_counts = data[left:right+1]

        #net cts array
        n_sel        = right - left + 1
        bgd_counts   = bgd_left + np.arange(n_sel)/(n_sel-1.0) * (bgd_right - bgd_left)
        net_counts   = total_counts - bgd_counts

        # do sums
        self.total =  sum(total_counts)
        self.net   =  sum(net_counts)

        return

########################################################################
class Mca:
    """ Device-independent MultiChannel Analyzer (MCA) class """
    def __init__(self, name='mca'):
        """
        Creates new Mca object.  The data are initially all zeros, and the number
        of channels is 2048.

        Keywords:
            name: Name of the mca object, eg a file name or detector name
        """
        self.name        = name
        nchans           = 2048
        self.data        = np.zeros(nchans)
        self.rois        = []
        self.calibration = McaCalibration()
        self.elapsed     = McaElapsed()
        self.environment = []

    def __repr__(self):
        lout = "  Detector %s\n" % self.name
        lout = lout + self.elapsed.__repr__()
        rois = self.get_rois(units='keV')
        for roi in rois:
            lout = lout + roi.__repr__()
        return lout

    ########################################################################
    def __copy__(self):
        """
        Makes a "shallow" copy of an Mca instance, using copy.copy() on all of
        the attributes of the Mca instance.  The .rois and .environment attributes
        will still point to the same values, because they are lists.
        """
        new = Mca()
        new.name = copy.copy(self.name)
        new.data = copy.copy(self.data)
        new.rois = copy.copy(self.rois)
        new.elapsed = copy.copy(self.elapsed)
        new.calibration = copy.copy(self.calibration)
        new.environment = copy.copy(self.environment)
        return(new)

    ########################################################################
    def __deepcopy__(self, visit):
        """
        Makes a "deep" copy of an Mca instance, using copy.deepcopy() on all of
        the attributes of the Mca instance. All of the attribute will point to
        new objects.
        """
        new = Mca()
        new.name = copy.copy(self.name)
        new.data = copy.copy(self.data)
        new.rois = copy.deepcopy(self.rois, visit)
        new.elapsed = copy.copy(self.elapsed)
        new.calibration = copy.copy(self.calibration)
        new.environment = copy.deepcopy(self.environment, visit)
        return(new)

    ########################################################################
    def get_name(self):
        """ Returns the Mca name as a string """
        return self.name

    ########################################################################
    def set_name(self, name):
        """
        Sets the Mca name.

        Inputs:
            name: A string
        """
        self.name = name

    ########################################################################
    def get_calibration(self):
        """ Returns the Mca calibration, as an McaCalibration object """
        return self.calibration

    ########################################################################
    def set_calibration(self, calibration):
        """
        Sets the Mca calibration.

        Inputs:
            calibration: An McaCalibration object
        """
        self.calibration = calibration

    ########################################################################
    def get_elapsed(self):
        """ Returns the Mca elapsed parameters, as an McaElapsed object """
        return self.elapsed

    ########################################################################
    def set_elapsed(self, elapsed):
        """
        Sets the Mca elapsed parameters.

        Inputs:
            elapsed: An McaElapsed object
        """
        self.elapsed = elapsed

    ########################################################################
    def get_environment(self):
        """
        Returns a list of McaEnvironment objects that contain the environment
        parameters of the Mca.
        """
        return self.environment

    ########################################################################
    def set_environment(self, environment):
        """
        Copies a list of McaEnvironment objects to the Mca object.

        Inputs:
            environment:
                A list of McaEnvironment objects.
        """
        self.environment = environment

    ########################################################################
    def add_roi(self, roi):
        """
        This procedure adds a new region-of-interest to the MCA.

        Inputs:
            roi: An object of type mcaROI.

        Example:
            mca = Mca('mca.001')
            roi = McaROI(units="channel")
            roi.left = 500
            roi.right = 600
            roi.label = 'Fe Ka'
            mca.add_roi(roi)
        """
        r = copy.copy(roi)
        self.rois.append(r)

        # update counts.  this also
        # makes sure ROI is in channel units and sorts them
        self.update_rois()

    ########################################################################
    def set_rois(self, rois):
        """
        Sets/resets the region-of-interest parameters for the MCA.

        Inputs:
            rois: A list of objects of type McaROI

        Example:
          mca = Mca('mca.001')
          r1 = McaROI(units="keV")
          r1.left = 5.4
          r1.right = 5.6
          r2 = McaROI(units="keV")
          r2.left = 6.1
          r2.right = 6.2
          mca.set_rois([r1,r2])
        """
        self.rois = []
        for roi in rois:
            self.rois.append(roi)

        # update counts.  this also
        # makes sure ROI is in channel units
        self.update_rois()

    ########################################################################
    def find_roi(self, left, right, energy=False):
        """
        This procedure finds the index number of the ROI with a specified
        left and right channel number.

        Inputs:
            left: Left channel number (or energy) of this ROI

            right: Right channel number (or energy) of this ROI

        Keywords:
            energy: Set this flag to True to indicate that Left and Right are
                    in units of energy rather than channel number.

        Output:
            Returns the index of the specified ROI, -1 if the ROI was not found.

        Example:
            index = mca.find_roi(100, 200)
        """
        l = left
        r = right
        if (energy == True):
            l = self.calibration.energy_to_channel( l, clip=len(self.data))
            r = self.calibration.energy_to_channel( r, clip=len(self.data))
        index = 0
        for roi in self.rois:
            if (l == roi.left) and (r == roi.right): return index
            index = index + 1
        return -1

    ########################################################################
    def find_roi_label(self, label=None):
        """
        This procedure finds the index number of the ROI with a specified
        label.

        Inputs:
            label: String label of ROI

        Output:
            Returns the index of the specified ROI, -1 if the ROI was not found.

        Example:
            index = mca.find_roi(label="Fe ka")
        """
        if label == None: return -1
        index = 0
        for roi in self.rois:
            if roi.label == label: return index
            index = index + 1
        return -1

    ########################################################################
    def delete_roi(self, index):
        """
        This procedure deletes the specified region-of-interest from the MCA.

        Inputs:
            index:  The index of the ROI to be deleted, range 0 to len(mca.rois)

        Example:
          mca.delete_roi(2)
        """
        del self.rois[index]

    ########################################################################
    def get_rois(self, units="channel"):
        """ Returns the Mca ROIS, as a list of McaROI objects.
            Note: default is to return in channel units
            Valid units are "channel","keV", and "eV"
        """
        # make sure counts are updated
        # this also sets ROI units to channel
        self.update_rois()
        rois = copy.copy(self.rois)
        # this should convert rois to passed units
        self.set_roi_units(rois=rois,units=units)

        return rois

    ########################################################################
    def set_roi_units(self, rois=[], units="channel"):
        """
        Sets the units on rois or on self.rois (if rois=[]) to keyword units
        Note we assume rois are a list, therefore pass by reference,
        so modifications made here should stick.  ie this method does
        not return any value
        Valid units are "channel","keV","eV"
        """
        if rois == []:
            rois = self.rois

        for roi in rois:
            if roi.units != units:
                if units == "channel":
                    if roi.units == "keV":
                        roi.left  = self.calibration.energy_to_channel(roi.left)
                        roi.right = self.calibration.energy_to_channel(roi.right)
                        roi.units = units
                    elif roi.units == "eV":
                        roi.left  = self.calibration.energy_to_channel(roi.left/1000.)
                        roi.right = self.calibration.energy_to_channel(roi.right/1000.)
                        roi.units = units
                    else:
                        print "Warning: Roi units %s uknown" % str(roi.units)
                elif units == "keV":
                    if roi.units == "channel":
                        roi.left  = self.calibration.channel_to_energy(roi.left)
                        roi.right = self.calibration.channel_to_energy(roi.right)
                        roi.units = units
                    elif roi.units == "eV":
                        roi.left  = roi.left/1000.
                        roi.right = roi.right/1000.
                        roi.units = units
                    else:
                        print "Warning: Roi units %s uknown" % str(roi.units)
                elif units == "eV":
                    if roi.units == "channel":
                        roi.left  = 1000.*self.calibration.channel_to_energy(roi.left)
                        roi.right = 1000.*self.calibration.channel_to_energy(roi.right)
                        roi.units = units
                    elif roi.units == "keV":
                        roi.left  = 1000.*roi.left
                        roi.right = 1000.*roi.right
                        roi.units = units
                    else:
                        print "Warning: Roi units %s uknown" % str(roi.units)
                else:
                    print "Warning: units %s uknown" % str(units)

    ########################################################################
    def get_roi_counts(self, background_width=1,correct=True):
        """
        Returns a tuple (total, net) containing the total and net counts of
        each region-of-interest in the MCA.

        Keywords:
            background_width:
                Set this keyword to set the width of the background region on either
                side of the peaks when computing net counts.  The default is 1.

        Outputs:
             total:  The total counts in each ROI.
             net:    The net counts in each ROI.

             The dimension of each list is NROIS, where NROIS
             is the number of currently defined ROIs for this MCA.  It returns
             and empty list for both if NROIS is zero.

        Example:
            total, net = mca.get_roi_counts(background_width=3)
            print 'Net counts = ', net
        """
        total = []
        net = []
        self.update_rois(background_width=background_width,correct=correct)
        for roi in self.rois:
            total.update(roi.total)
            net.update(roi.net)
        return (total,net)

    ########################################################################
    def get_roi_counts_lbl(self, background_width=1,correct=True):
        """
        Returns a dict of {'lbl:(total, net),...} containing the total and net counts of
        each region-of-interest in the MCA.

        Keywords:
            background_width:
                Set this keyword to set the width of the background region on either
                side of the peaks when computing net counts.  The default is 1.

        Outputs:
             lbl:    ROI label
             total:  The total counts in each ROI.
             net:    The net counts in each ROI.

        Example:
            rois = mca.get_roi_counts_lbl(background_width=3)
        """
        rois = {}
        self.update_rois(background_width=background_width,correct=correct)
        for roi in self.rois:
            rois[roi.label] = (roi.total, roi.net)
        return rois

    ########################################################################
    def update_rois(self, background_width=1,correct=True):
        """
        Update the total and net counts for each roi.
        Note this sets roi units to channel and
        sorts them according to left channel

        Keywords:
            background_width: Set this keyword to set the width of the
                              background region on either side of the peaks
                              when computing net counts.  The default is 1.
        """

        # make sure current units for rois are channel units
        self.set_roi_units(units="channel")

        # Sort ROIs.  This sorts by left channel.
        self.rois.sort()

        for roi in self.rois:
            if correct == True:
                data = self.get_data(correct=correct)
                roi.update_counts(data, background_width=background_width)
            else:
                roi.update_counts(self.data, background_width=background_width)
        return

    ########################################################################
    def update_correction(self,tau=None):
        """
        Update the deadtime correction
        if tau == None just recompute,
        otherwise assign a new tau and recompute
        """
        if tau != None:
            self.elapsed.tau = tau
        self.elapsed.calc_correction()

    ########################################################################
    def get_data(self,correct=True):
        """
        Returns the data (counts) from the Mca
        Note if correct == True the corrected data is returned. However,
        this does not (re)compute the correction factor, therefore, make
        sure the correction factor is up to date before requesting corrected data...
        """
        if correct == True:
            d = self.elapsed.cor_factor * self.data
            return map(int,d)
        else:
            return self.data

    ########################################################################
    def set_data(self, data):
        """
        Copies an array of data (counts) to the Mca.

        Inputs:
            data:
                A numpy array of data (counts).
        """
        self.data = data
        return

    ########################################################################
    def get_energy(self):
        """
        Returns a list containing the energy of each channel in the MCA spectrum.

        Procedure:
            Simply returns mca.channel_to_energy() for each channel

        Example:
             from Mca import *
             mca = Mca('mca.001')
             energy = mca.get_energy()
        """
        channels = np.arange(len(self.data))
        energy   = self.calibration.channel_to_energy(channels)
        return energy

    ########################################################################
    def initial_calibration(self, energy):
        """
        Performs an initial coarse energy calibration of the Mca, setting only
        the slope, and setting the offset parameter to 0.

        Inputs:
            energy: The energy of the biggest peak in the MCA spectrum.

        Procedure:
            This routine does the following:
                1) Sets the offset coefficient to 0.0
                2) Sets the quadratic coefficient to 0.0
                3) Determines which channel contains the most counts, PEAK_CHAN
                4) Sets the slope equal to the input energy divided by PEAK_CHAN

        Example:
            from Mca import *
            mca = Mca('mca.001')
            mca.initial_calibration(20.1)
        """
        peak_chan = np.argmax(self.data)
        peak_chan = max(peak_chan,1)
        self.calibration.offset = 0.
        self.calibration.slope = float(energy)/peak_chan
        self.calibration.quad = 0.

    ########################################################################
    #def final_calibration():
    #    pass

#####################################################################################################

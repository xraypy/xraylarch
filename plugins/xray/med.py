########################################################################
# Methods for Multi-element detectors
# From Med written by Mark Rivers
# Modified for tdl
########################################################################


"""
Support for Multi-Element Detectors (Med).

Author:        Mark Rivers
Created:       Sept. 18, 2002.  Based on earlier IDL code.
Modifications:
"""

import mca
import numpy as np
import copy

from scipy.signal import cspline1d, cspline1d_eval

def spline_interpolate(oldx, oldy, newx):
    """
      1-d cubic spline interpolation, for cases where
      both oldx and newx are on a uniform grid.
      newy = spline_interpolate(oldx, oldy, newx)
    """
    return cspline1d_eval(cspline1d(oldy), newx, dx=oldx[1]-oldx[0], x0=oldx[0])

#########################################################################
#class Med(Mca.Mca):
class Med:
    """
    The MED class is basically a collection of Mca objects.

    This class is device-independent.

    Its methods generally simply apply the Mca class methods to each Mca object
    in the collection. The Med class itself is most commonly used for reading
    data from disk files. More importantly, this class is the superclass of the
    epicsMed class.
    """

    def __init__(self, n_detectors=16, name='med'):
        """
        Initialization code for creating a new Med object.

        Keywords:
            n_detectors: The number of detectors (Mca objects) in the Med.

            name: Name of the mca object, eg a file name or detector name
        """
        self.n_detectors = n_detectors
        self.name        = name
        self.mcas        = []
        for i in range(n_detectors):
            mca_name = 'mca:%s' % str(i + 1)
            self.mcas.append(Mca.Mca(name=mca_name))
        self.environment = []

    def __repr__(self):
        lout = "Name = %s\n" % self.name
        lout = lout + "Number of detectors = %i\n" % self.n_detectors
        for mca in self.mcas:
            lout = lout + mca.__repr__()
        return lout

    def __copy__(self):
        new = Med()
        new.n_detectors = copy.copy(self.n_detectors)
        new.name        = copy.copy(self.name)
        new.mcas        = []
        for i in range(self.n_detectors):
            new.mcas.append(self.mcas[i].__copy__())
        return new

    def __deepcopy__(self,visit):
        new = Med()
        new.n_detectors = copy.copy(self.n_detectors)
        new.name        = copy.copy(self.name)
        new.mcas        = []
        for i in range(self.n_detectors):
            new.mcas.append(self.mcas[i].__deepcopy__(visit))
        return new

    ########################################################################
    def set_environment(self, environment):
        """
        Copies a list of McaEnvironment objects to the Med object.

        Inputs:
            environment:
                A list of McaEnvironment objects.
        """
        self.environment = environment

    #########################################################################
    def get_mcas(self):
        """
        Returns a list of Mca objects from the Med.
        """
        return self.mcas

    #########################################################################
    def initial_calibration(self, energy):
        """
        Performs an initial energy calibration for each Mca in the Med.

        Inputs:
            energy: The energy of the largest peak in the spectrum.

        See the documentation for Mca.initial_calibration() for more information.
        """
        for mca in self.mcas:
            mca.initial_calibration(energy)

    #########################################################################
    #def final_calibration(self, peaks):
    #    """
    #    Performs a final energy calibration for each Mca in the Med.
    #
    #    Inputs:
    #        peaks: A list of McaPeak objects. This list is typically read from a
    #               disk file with function Mca.read_peaks().
    #
    #    See the documentation for Mca.final_calibration() for more information.
    #    """
    #    print "Not yet implemented"
    #    #for mca in self.mcas:
    #    #    mca.final_calibration(peaks)
    #
    #########################################################################
    def get_calibration(self):
        """
        Returns a list of McaCalibration objects, one for each Mca in the Med.
        """
        calibration = []
        for mca in self.mcas:
            calibration.append(mca.get_calibration())
        #self.calibration = calibration
        return calibration

    #########################################################################
    def set_calibration(self, calibration):
        """
        This procedure sets the calibration parameters for the Med.
        The calibration information is contained in an object or list of
        objects of type McaCalibration.

        Inputs:
            calibration: A single object or a list of objects of type McaCalibration
                         containing the calibration parameters for each Mca.
                         If a single object is passed then this is written to each Mca.
                         If a list of objects is passed then calibration[i] is written to
                         Mca[i].
        """
        if (isinstance(calibration, Mca.McaCalibration)):
            for mca in self.mcas:
                mca.set_calibration(calibration)
        else:  # Assume it is a list or tuple
            for i in range(self.n_detectors):
                self.mcas[i].set_calibration(calibration[i])


    #########################################################################
    def get_elapsed(self):
        """
        Returns the elapsed parameters for the Med.
        The elapsed information is contained in a list of structures of type
        McaElapsed.

        Outputs:
            Returns a list of structures of type McaElapsed.

        Procedure:
            This function simply invokes Mca.get_elapsed for each Mca in the Med
            and stores the results in the returned list.
        """
        elapsed = []
        for mca in self.mcas:
            elapsed.append(mca.get_elapsed())
        return elapsed

    #########################################################################
    def set_elapsed(self, elapsed):
        """
        Sets the elapsed parameters for the Med.
        The elapsed information is contained in an object or list of
        objects of type McaElapsed.

        Inputs:
            elapsed: A single structure or a list of structures of type McaElapsed
                     containing the elapsed parameters for each Mca.
                     If a single object is passed then this is written to each Mca.
                     If a list of objects is passed then elapsed[i] is written to Mca[i].
        """
        if (isinstance(elapsed, Mca.McaElapsed)):
            for mca in self.mcas:
                mca.set_elapsed(elapsed)
        else:  # Assume it is a list or tuple
            for i in range(self.n_detectors):
                self.mcas[i].set_elapsed(elapsed[i])

    #########################################################################
    def get_rois(self,units="channel"):
        """
        Returns the region-of-interest information for each Mca in the Med.

        Keywords:
            units:  the returned ROI objects will be converted to the given units
                    valid values are "channel", "kev", "ev".  Default is "channel"

        Outputs:
            Returns a list of list of lists of McaRoi objects.
            The length of the outer list is self.n_detectors, the length of the
            list for each Mca is the number of ROIs defined for that Mca.
        """
        rois = []
        for mca in self.mcas:
            rois.append(mca.get_rois(units=units))
        return rois

    #########################################################################
    def update_rois(self,background_width=1,correct=True):
        for mca in self.mcas:
            mca.update_rois(background_width=background_width,correct=correct)
        return

    #########################################################################
    def get_roi_counts(self, background_width=1,correct=True):
        """
        Returns the net and total counts for each Roi in each Mca in the Med.

        Outputs:
            Returns a tuple (total, net).  total and net are lists of lists
            containing the total and net counts in each ROI.  The length of the
            outer list is self.n_detectors, the length of the total and net lists
            list for each Mca is the number of ROIs defined for that Mca.
        """
        total = []
        net = []
        for mca in self.mcas:
            t, n = mca.get_roi_counts(background_width=background_width,correct=correct)
            total.append(t)
            net.append(n)
        return (total, net)

   #########################################################################
    def get_roi_counts_lbl(self, background_width=1,correct=True):
        """
        Returns the net and total counts for each Roi in each Mca in the Med.

        Outputs:
            Returns a list of dictionaries.  The list is of length num detectors
            each entry in the list holds a dictionary of {'lbl:(total, net),...}
        """
        rois = []
        for mca in self.mcas:
            r = mca.get_roi_counts_lbl(background_width=background_width,correct=correct)
            rois.append(r)
        return rois

    #########################################################################
    def set_rois(self, rois):
        """
        This procedure sets the ROIs for the Med (blowing away old ones)
        The elapsed information is contained in a list of McaRoi objects,
        or list of such lists.

        Inputs:
            rois: A single list or a nested list of objects McaROI objects.
                  If a single list is passed then this is written to each Mca.
                  If a list of lists is passed then rois[i][*] is written to Mca[i].
        """
        if (len(rois) <= 1):
            for mca in self.mcas:
                mca.set_rois(rois)
        else:
            for i in range(self.n_detectors):
                self.mcas[i].set_rois(rois[i])

    #########################################################################
    def add_roi(self, roi):
        """
        This procedure adds an ROI to each Mca in the Med.

        Inputs:
            roi: A single McaROI to be added.
        """
        for mca in self.mcas:
            mca.add_roi(roi)

    #########################################################################
    def delete_roi(self, index):
        """
        This procedure deletes the ROI at position "index" from each Mca in the
        Med.

        Inputs:
            index:  The index number of the ROI to be deleted.
        """
        for mca in self.mcas:
            mca.delete_roi(index)

    #########################################################################
    def copy_rois(self, source_mca=0, energy=False):
        """
        This procedure copies the ROIs defined for one Mca in the Med to all of
        the other Mcas.

        Inputs:
            source_mca: The index number of the Mca from which the ROIs are to
                        be copied.  This number ranges from 0 to self.n_detectors-1.
                        The default is the first Mca (index=0).

        Keywords:
            energy: Set this keyword if the ROIs should be copied by their position
                    in energy rather than in channels. This is very useful when
                    copying ROIs when the calibration parameters for each Mca in
                    the Med are not identical.
        """
        if energy:
            units = "keV"
        else:
            units = "channel"
        rois = self.mcas[source_mca].get_rois(units=units)
        self.set_rois(rois)

    #########################################################################
    def update_correction(self, tau=None):
        """ Update mca deadtime correction """
        if tau is None:
            for j in range(self.n_detectors):
                self.mcas[j].update_correction(tau=None)
        else:
            self._set_taus(tau=tau)
        return

    ########################################################################
    def _set_taus(self, tau=None):
        """
        Update the deadtime correction factors
        """
        # empty list or None, turn off taus...
        if tau is None:
            for j in range(self.n_detectors):
                self.mcas[j].update_correction(tau = -1.0)
            return
        # if one value assign to all dets
        if isinstance(tau, (float, int)):
            for j in range(self.n_detectors):
                self.mcas[j].update_correction(tau = tau)
            return
        # if list
        if isinstance(tau, (list, tuple)):
            # single val assign to all
            if len(tau) == 1:
                for j in range(self.n_detectors):
                    self.mcas[j].update_correction(tau = tau[0])
                return
            # otherwise assign to each
            elif len(tau) == self.n_detectors:
                for j in range(self.n_detectors):
                    self.mcas[j].update_correction(tau = tau[j])
                return
            else:
                print "Error: tau array must be of length %d" % self.n_detectors
                return

        print "Failure assigning tau values - Type error"
        return

    #########################################################################
    def get_data(self, bad_mca_idx=[], total=False, align=False, correct=True):
        """
        Returns the data from each Mca in the Med as a 2-D Numeric array

        Keywords:
            total: Set this keyword to return the sum of the spectra from all
                   of the Mcas as a 1-D Numeric array.

            align: Set this keyword to return spectra which have been shifted and
                   and stretched to match the energy calibration parameters of the
                   first detector.  This permits doing arithmetic on a
                   "channel-by-channel" basis. This keyword can be used alone
                   or together with the TOTAL keyword, in which case the data
                   are aligned before summing.

            bad_mca_idx: A list of bad mca's, data will be zeros.  An empty
                       list (default) means all the detectors are ok.
                       Note detector indexing starts at zero!

            correct:
                True means to apply deadtime correction, false ignores it

        Outputs:
            By default this function returns a long 2-D array of counts dimensioned
            [self.n_detectors,nchans]

            If the "total" keyword is set then the array dimensions are [1,nchans]
        """

        temp = self.mcas[0].get_data()
        nchans = len(temp)

        # init all data to zeros
        data = np.zeros((self.n_detectors, nchans))

        # get (corrected) data from MCA
        for d in range(self.n_detectors):
            if d not in bad_mca_idx:
                data[d,:] = self.mcas[d].get_data(correct=correct)

        # align if requested.
        if align and self.n_detectors > 1:
            #ref_energy = self.mcas[0].get_energy()
            first_good = self.get_align_idx(bad_mca_idx)
            ref_energy = self.mcas[first_good].get_energy()
            for d in range(self.n_detectors):
                if d not in bad_mca_idx:
                    energy = self.mcas[d].get_energy()
                    temp = spline_interpolate(energy, data[d,:], ref_energy)
                    #data[d,:] = int(temp+.5)
                    data[d,:] = (temp+.5).astype(np.dtype('i'))

        # make a total if requested.
        if total and self.n_detectors > 1:
            # note probably a bad idea to total and not align
            if not align:
                print "Warning, totaling data without aligning"
            data = data.sum(axis=0)
            return [data]
        else:
            return data

    #########################################################################
    def get_align_idx(self,bad_mca_idx):
        " find first good detector for alignment"
        for d in range(self.n_detectors):
            if d not in bad_mca_idx:
                return d
        return 0

    #########################################################################
    def get_energy(self,detectors = []):
        """
        Returns a list of energy arrays, one array for each Mca in the Med.
        See the documentation for Mca.get_energy() for more information.
        """
        if len(detectors) > 0 and len(detectors) < self.n_detectors:
            det_idx = detectors
        else:
            det_idx = range(self.n_detectors)

        energy = []
        #for mca in self.mcas:
        for i in range(len(det_idx)):
            energy.append(self.mcas[int(det_idx[i])].get_energy())
        return energy

    #########################################################################
    def energy_idx(self,det_idx, emin, emax):
        """
        get the channel numbers for emin and emax
        for given detector index
        """
        calib    = self.mcas[det_idx].calibration
        nchans   = len(self.mcas[det_idx].data)
        if emin >= 0.0:
            mi = calib.energy_to_channel(emin)
        else:
            mi = 0
        if emax >= 0.0 and emax > emin:
            ma = calib.energy_to_channel(emax)
        else:
            ma = 0
        if mi < 0: mi = 0
        if ma < 0: ma = 0
        if mi >= nchans-1:
            mi = nchans-2
        if ma > nchans-1:
            ma = nchans-1
        if ma < mi:
            mi = ma
        return (mi,ma)

"""
Methods for Multipl element MCA detectors

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* Modified for Tdl, tpt
* modified and simplified for Larch, M Newville

Notes:
------
Conventions for MultiMCA.get_data and MultiMCA.get_energy:
 * If MultiMCA.total == True the returned array will be dim: [1, nchans]
 * If MultiMCA.total == False the returned array will be dim: [n_detectors, nchans]
                   bad det's are zeros
 * If MultiMCA.align == True the first good detector will be used as the energy reference
 * If MultiMCA.correct == True deadtime corrections will be applied on MultiMCA.get_data()

"""
###########################################################################

import numpy as np
import exceptions
from mca import MCA

"""
cubic splines for energy alignment using
scipy.signal and/or scipy.interpolate
"""
from scipy.signal import cspline1d, cspline1d_eval
from scipy.interpolate import UnivariateSpline

def spline_interpolate(oldx, oldy, newx):
    """
    newy = spline_interpolate(oldx, oldy, newx)
    1-dimensional cubic spline, for cases where oldx and newx are on a uniform grid.
    """
    return UnivariateSpline(oldx, oldy, s=0)(newx)
    # return cspline1d_eval(cspline1d(oldy), newx, dx=oldx[1]-oldx[0], x0=oldx[0])

#########################################################################
class MultiMCA:
    """
    The MED class --> collection of MCA objects.

    Attributes:
    -----------
    * total: Set this keyword to return the sum of the spectra from all
      of the MCAs as a 1-D numeric array.

    * align: Set this keyword to return spectra which have been shifted and
      and stretched to match the energy calibration parameters of the
      first (good) detector.  This permits doing arithmetic on a
      "channel-by-channel" basis. This keyword can be used alone
      or together with the TOTAL keyword, in which case the data
      are aligned before summing.

    * correct: True means to apply deadtime correction, false ignores it

    * tau:  mca deadtime tau values
        None --> recompute correction factor
        []   --> Turn off correction, ie set taus to -1
        single value (or single valued list) --> assign to all mcas
        list (or array) --> assign to individual mcas

    """
    ########################################################################
    def __repr__(self):
        return "<MultiMCA %s, n_mca=%d>" % (self.name, len(self.mcas))

    ########################################################################
    def __init__(self, mcas=None, name='med',
                 total=True, align=True, correct=True):
        """
        initialize by passing in list of mcas

        The kw arguments correspond to object attributes
        """
        self.det_type    = "MED"
        self.name        = name
        if mcas  is None:
            mcas = []
        self.mcas        = mcas
        self.n_detectors = len(self.mcas)
        self.total    = total
        self.align    = align
        self.correct  = correct
        self.update_correction(tau=None)

    ################################################################
    def get_tau(self):
        """
        return tau values
        """
        return [m.tau for m in self.mcas]

    #########################################################################
    def update_correction(self, tau=None):
        """
        Update mca deadtime correction
        pass in tau =
           None      --> recompute correction factor
           < 0       --> Turn off correction, ie set taus to -1
           single value (or single valued list) --> assign to all mcas
           list (or array) --> assign to individual mcas
        """
        if tau < 0:
            tau = -1.0
        if (isinstance(tau, (list, tuple, np.ndarray)) and len(tau) == 1):
            tau = tau[0]

        if isinstance(tau, (None, float, int)):
            for mca in self.mcas:
                mca.update_correction(tau = tau)
        elif (isinstance(tau, (list, tuple, np.ndarray)) and
              len(tau) == self.n_detectors):
            for mca, t in zip(self.mcas, tau):
                mca.update_correction(tau = t)
        else:
            print "Error: tau array must be of length %d" % self.n_detectors
        return

    #########################################################################
    def get_data(self):
        """
        Returns the data as a 2-D numeric array

        Outputs:
        --------
        * This function returns a long 2-D array of counts dimensioned
          [n_detectors, nchans]

          If the "total" keyword is set then the array dimensions are [1,nchans]
        """
        # see how many channels, all mcas must be same length!!
        temp = self.mcas[0].get_data()
        nchans = len(temp)

        # init data to zeros
        data = np.zeros((self.n_detectors, nchans), dtype=np.int)

        # get (corrected) data from MCA
        for d, mca in enumerate(self.mcas):
            data[d,:] = mca.get_data(correct=self.correct)

        # align if requested.
        if self.align and self.n_detectors > 1:
            first_good = self.get_firstgood_mca()
            energy = first_good.get_energy()
            for d, mca in enumerate(self.mcas):
                en  = mca.get_energy()
                dat = spline_interpolate(en, data[d,:], energy)
                # note adding .5 rounds the data
                data[d,:] = (dat+.5).astype(np.int)

        # make a total if requested.
        if self.total and self.n_detectors > 1:
            return data.sum(axis=0)
        else:
            return data

    def get_firstgood_mca(self,):
        """ find first good detector for alignment """
        for mca in self.mcas:
            if mca.total_counts >= 1:
                return mca
        raise exceptions.IndexError("No good detector index found")


"""
Methods for Multipl element Mca detectors

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* See http://cars9.uchicago.edu/software/python/index.html
* Modified for Tdl, tpt

Notes:
------
Conventions for Med.get_data and Med.get_energy:
 * If Med.total == True the returned array will be dim: [1, nchans]
 * If Med.total == False the returned array will be dim: [n_detectors, nchans]
                   bad det's are zeros
 * If Med.align == True the first good detector will be used as the energy reference
 * If Med.correct == True deadtime corrections will be applied on Med.get_data()

"""
###########################################################################

import numpy as num
import exceptions

from mca import Mca
from tdl.modules.spectra import calibration as calib

"""
cubic splines for energy alignment using
scipy.signal and/or scipy.interpolate
"""
from scipy.signal import cspline1d, cspline1d_eval

def spline_interpolate(oldx, oldy, newx):
    """
    newy = spline_interpolate(oldx, oldy, newx)
    1-dimensional cubic spline, for cases where oldx and newx are on a uniform grid.
    """
    return cspline1d_eval(cspline1d(oldy), newx, dx=oldx[1]-oldx[0], x0=oldx[0])

#########################################################################
class Med:
    """
    The MED class --> collection of Mca objects.

    Attributes:
    -----------
    * bad_mca_idx: A list of bad mca's, data will be zeros.  An empty
      list (default) means all the detectors are ok.
      Note detector indexing starts at zero!

    * total: Set this keyword to return the sum of the spectra from all
      of the Mcas as a 1-D numeric array.

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
        return "<MED %s, n_mca=%d>" % (self.name, len(self.mca))

    ########################################################################
    def __init__(self,name='med',mca=[],**kws):
        """
        initialize by passing in list of mcas

        The kw arguments correspond to object attributes
        """
        self.det_type    = "MED"
        self.name        = name
        self.mca         = mca
        self.n_detectors = len(self.mca)

        # med parameters
        self.bad_mca_idx = []
        self.total       = True
        self.align       = True
        self.correct     = True

        # update params
        self.init_params(params=kws)
        self.update_correction(tau=None)

    ########################################################################
    def re_init(self,n_detectors=1,nchans=2048,**kws):
        """
        use to create new instance with given number of empty
        detectors/mcas
        """
        self.n_detectors = n_detectors
        self.mca = []
        for i in range(n_detectors):
            mca_name = 'mca:%s' % str(i)
            self.mca.append(Mca(name=mca_name, nchans=nchans))
        # update params
        self.init_parameters(params=kws)

    ########################################################################
    def init_params(self,params={}):
        """
        set/reset parameters based on key word arguments
        """
        for key in params.keys():
            if key == 'tau':
                self.update_correction(tau=params['tau'])
            else:
                setattr(self,key,params[key])

    ########################################################################
    def get_params(self,):
        """
        return the parameters we care about
        """
        params = {'bad_mca_idx':self.bad_mca_idx,
                  'total':self.total,
                  'align':self.align,
                  'correct':self.correct,
                  'tau':self.get_tau()}
        return params

    ################################################################
    def get_tau(self):
        """
        return tau values
        """
        tau = []
        for j in range(self.n_detectors):
            tau.append(self.mca[j].tau)
        return tau

    ########################################################################
    def init_mca_params(self, det_idx=0, mca_params={}):
        """
        set/reset individual mca parameters based on key word arguments
        """
        self.mca[det_idx].init_params(mca_params=mca_params)

    def init_mca_data(self, det_idx=0, data=None, channels=None):
        """
        set/reset individual mca data/channels
        """
        self.mca[det_idx].init_data(data=data, channels=channels)

    #########################################################################
    def update_correction(self, tau=None):
        """
        Update mca deadtime correction
        pass in tau =
           None --> recompute correction factor
           []   --> Turn off correction, ie set taus to -1
           single value (or single valued list) --> assign to all mcas
           list (or array) --> assign to individual mcas
        """
        if tau is None:
            for j in range(self.n_detectors):
                self.mca[j].update_correction(tau=None)
        else:
            self._set_taus(tau=tau)
        return

    ########################################################################
    def _set_taus(self, tau=None):
        """
        Update the deadtime correction factors
        tau:
           empty list -> turn off taus...
           if one value assign to all dets
           if list assign to each
        """
        if tau is None: return

        # empty list turn off taus...
        if tau == []:
            for j in range(self.n_detectors):
                self.mca[j].update_correction(tau = -1.0)
            return
        # if one value assign to all dets
        if isinstance(tau, (float, int):
            for j in range(self.n_detectors):
                self.mca[j].update_correction(tau = tau)
            return
        # if list
        if isinstance(tau, (list, tuple)):
            # single val assign to all
            if len(tau) == 1:
                for j in range(self.n_detectors):
                    self.mca[j].update_correction(tau = tau[0])
                return
            # otherwise assign to each
            elif len(tau) == self.n_detectors:
                for j in range(self.n_detectors):
                    self.mca[j].update_correction(tau = tau[j])
                return
            else:
                print "Error: tau array must be of length %d" % self.n_detectors
                return

        print "Failure assigning tau values - Type error"
        return

    #########################################################################
    def get_data(self,):
        """
        Returns the data as a 2-D numeric array

        Outputs:
        --------
        * This function returns a long 2-D array of counts dimensioned
          [n_detectors, nchans]

          If the "total" keyword is set then the array dimensions are [1,nchans]
        """
        # see how many channels, all mcas must be same length!!
        temp = self.mca[0].get_data()
        nchans = len(temp)

        # init data to zeros
        data = num.zeros((self.n_detectors, nchans), dtype=num.int)

        # get (corrected) data from MCA
        for d in range(self.n_detectors):
            if d not in self.bad_mca_idx:
                data[d,:] = self.mca[d].get_data(correct=self.correct)

        # align if requested.
        if self.align and self.n_detectors > 1:
            first_good = self._get_align_idx()
            ref_energy = self.mca[first_good].get_energy()
            for d in range(self.n_detectors):
                if d not in self.bad_mca_idx:
                    energy = self.mca[d].get_energy()
                    temp   = spline_interpolate(energy, data[d,:], ref_energy)
                    # note adding .5 rounds the data
                    data[d,:] = (temp+.5).astype(num.int)

        # make a total if requested.
        if self.total and self.n_detectors > 1:
            if not self.align:
                # note probably a bad idea to total and not align?
                # ie we wont know what the correct energy array is!
                print "Warning, totaling data without aligning"
            data = data.sum(axis=0)
            return num.asarray([data])
        else:
            return data

    #########################################################################
    def get_energy(self,):
        """
        Returns a 2-D numpy array of energy values.
        """
        # One detector easy
        if self.n_detectors == 1:
            return  num.asarray([self.mca[0].get_energy()])

        # if align or total all energies are same.
        # use first good as energy/reference energy
        if self.align or self.total:
            first_good = self._get_align_idx()
            ref_energy = self.mca[first_good].get_energy()

            if self.total:
                return num.asarray([ref_energy])
            #elif self.align:
            else:
                energy = [ref_energy]*self.n_detectors
                return num.asarray(energy)

        # otherwise all unique
        else:
            energy = []
            for mca in self.mca:
                energy.append(mca.get_energy())
            return num.asarray(energy)

    #########################################################################
    def get_calib_params(self,):
        """
        return a list of mca calibration parameters
        """
        if self.n_detectors == 1:
            return [self.mca[0].get_calib_params()]
        if self.align or self.total:
            first_good = self._get_align_idx()
            params = self.mca[first_good].get_calib_params()

            if self.total:
                return [params]
            else:
                return [params]*self.n_detectors
        else:
            ret = []
            for mca in self.mca:
                ret.append(mca.get_calib_params())
            return ret

    #########################################################################
    def _get_align_idx(self,):
        """ find first good detector for alignment """
        for d in range(self.n_detectors):
            if d not in self.bad_mca_idx:
                if self.mca[d].total_counts >= 1:
                    return d
        #return 0
        raise exceptions.IndexError("No good detector index found")

    #########################################################################
    def get_data_range(self,emin=0.,emax=0.):
        """
        return (energy, data) truncated to be in range emin and emax
        if emin of emax < 0 they are ignored.
        """
        energy = self.get_energy()
        data   = self.get_data()
        en = []
        da = []
        for j in range(len(energy)):
            idx    = calib.energy_idx()
            en.append(energy[j][idx])
            da.append(data[j][idx])
        try:
            en = num.array(en)
            da = num.array(da)
        except:
            print "Error in get data range"

        return (en,da)


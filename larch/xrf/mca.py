"""
This module defines a device-independent MultiChannel Analyzer (MCA) class.

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* Modified for Tdl, tpt
* modified and simplified for Larch, M Newville
"""
import numpy as np
from larch import Group, isgroup

from xraydb import xray_line, xray_edge, material_mu
from ..math import interp
from .deadtime import calc_icr, correction_factor
from .roi import ROI


def isLarchMCAGroup(grp):
    """tests whether variable holds a valid Larch MCAGroup"""
    return isgroup(grp, 'energy',  'counts', 'rois')

class Environment:
    """
    The "environment" or related parameters for a detector.  These might include
    things like motor positions, temperature, anything that describes the
    experiment.

    Attributes:
    -----------
    * name         # A string name of this parameter, e.g. "13IDD:m1"
    * description  # A string description of this parameter, e.g. "X stage"
    * value        # A string value of this parameter,  e.g. "14.223"
    """
    def __init__(self, desc='', addr='', val=''):
        self.addr  = str(addr).strip()
        self.val   = str(val).strip()
        self.desc  = str(desc).strip()
        if self.desc.startswith('(') and self.desc.endswith(')'):
            self.desc = self.desc[1:-1]

    def __repr__(self):
        return "Environment(desc='%s', val='%s', addr='%s')" % (self.desc,
                                                                self.val,
                                                                self.addr)


class MCA(Group):
    """
    MultiChannel Analyzer (MCA) class

    Attributes:
    -----------
    * self.name        = 'mca'  # Name of the mca object
    * self.nchans      = 2048   # number of mca channels
    * self.counts      = None   # MCA data
    * self.pileup      = None   # predicted pileup

    # Counting parameters
    * self.start_time   = ''    # Start time and date, a string
    * self.live_time    = 0.    # Elapsed live time in seconds
    * self.real_time    = 0.    # Elapsed real time in seconds
    * self.read_time    = 0.    # Time that the MCA was last read in seconds
    * self.total_counts = 0.    # Total counts between the preset start and stop channels
    * self.input_counts = 0.    # Actual total input counts (eg given by detector software)
                                # Note total_counts and input counts ARE NOT time normalized
                                #
    * self.tau          = -1.0  # Factor for deadtime/detector saturation calculations, ie
                                #     ocr = icr * exp(-icr*tau)
    * self.icr_calc     = -1.0  # Calculated input count rate from above expression
    * self.dt_factor   = 1.0    # deadtime correction factor based on icr,ocr,lt,rt
                                # data_corrected = data * dt_factor
                                #
    # Calibration parameters
    * self.offset       = 0.    # Offset
    * self.slope        = 1.0   # Slope
    * self.quad         = 0.    # Quadratic

    Notes:
    ------
    If input_counts are read from the data file then there is no need for tau
    values (and hence icr_calc is not used) - ie we assume the detector
    provides the icr value.

    The application of corrections uses the following logic:
       if tau > 0 this will be used in the correction factor calculation
       if tau = 0 then we assume ocr = icr in the correction factor calculation
       if tau < 0 (or None):
       if input_counts > 0 this will be used for icr in the factor calculation
          if input_counts <= 0 we assume ocr = icr in the correction factor calculation

    Energy calibration is based on the following:
        energy = offset + slope*channel + quad*channel**2

    """
    ###############################################################################
    def __init__(self, counts=None, nchans=2048, start_time='',
                 offset=0, slope=0, quad=0, name='mca', dt_factor=1,
                 real_time=0, live_time=0, input_counts=0, tau=0, **kws):

        self.name    = name
        self.nchans  = nchans
        self.environ = []
        self.rois    = []
        self.counts  = counts

        # Calibration parameters
        self.offset       = offset # Offset
        self.slope        = slope  # Slope
        self.quad         = quad   # Quadratic

        # Counting parameters
        self.start_time   = start_time
        self.real_time    = real_time  # Elapsed real time in seconds (requested counting time)
        self.live_time    = live_time  # Elapsed live time in seconds (time detector is live)
        self.input_counts = input_counts # Actual total input counts (eg given by detector software)
                                  # Note total_counts and input counts ARE NOT time normalized
                                  #
        self.total_counts = 0.    # Total counts between the preset start and stop channels
        self.tau          = tau   # Factor for deadtime/detector saturation calculations, ie
                                  #     ocr = icr * exp(-icr*tau)
        # Calculated correction values
        self.icr_calc    = -1.0  # Calculated input count rate from above expression
        # corrected_counts = counts * dt_factor
        self.bgr = None
        self.dt_factor   = float(dt_factor)
        if counts is not None:
            self.nchans      = len(counts)
            self.total_counts =  counts.sum()
        self.incident_energy = None
        self.get_energy()
        self._calc_correction()
        Group.__init__(self)

    def __repr__(self):
        form = "<MCA %s, nchans=%d, counts=%d, realtime=%.1f>"
        return form % (self.name, self.nchans, self.total_counts, self.real_time)

    def add_roi(self, name='', left=0, right=0, bgr_width=3,
                counts=None, sort=True):
        """add an ROI"""
        name = name.strip()
        roi = ROI(name=name, left=left, right=right,
                  bgr_width=bgr_width, counts=counts)

        rnames = [r.name.lower() for r in self.rois]
        if name.lower() in rnames:
            iroi = rnames.index(name.lower())
            self.rois[iroi] = roi
        else:
            self.rois.append(roi)
        if sort:
            self.rois.sort()

    def get_roi_counts(self, roi, net=False):
        """get counts for an roi"""
        thisroi = None
        if isinstance(roi, ROI):
            thisroi = roi
        elif isinstance(roi, int) and roi < len(self.rois):
            thisroi = self.rois[roi]
        elif isinstance(roi, str):
            rnames = [r.name.lower() for r in self.rois]
            for iroi, nam in enumerate(rnames):
                if nam.startswith(roi.lower()):
                    thisroi = self.rois[iroi]
                    break
        if thisroi is None:
            return None
        return thisroi.get_counts(self.counts, net=net)

    def add_environ(self, desc='', val='', addr=''):
        """add an Environment setting"""
        if len(desc) > 0 and len(val) > 0:
            self.environ.append(Environment(desc=desc, val=val, addr=addr))

    def predict_pileup(self, scale=None):
        """
        predict pileup for a spectrum, save to 'pileup' attribute
        """
        en = self.energy
        npts = len(en)
        counts = self.counts.astype(int)*1.0
        pileup = 1.e-8*np.convolve(counts, counts, 'full')[:npts]
        ex = en[0] + np.arange(len(pileup))*(en[1] - en[0])
        if scale is None:
            npts = len(en)
            nhalf = int(npts/2) + 1
            nmost = int(7*npts/8.0) - 1
            scale = self.counts[nhalf:].sum()/ pileup[nhalf:nmost].sum()
        self.pileup = interp(ex, scale*pileup, self.energy, kind='cubic')
        self.pileup_scale = scale

    def predict_escape(self, det='Si', scale=1.0):
        """
        predict detector escape for a spectrum, save to 'escape' attribute

        X-rays penetrate a depth 1/mu(material, energy) and the
        detector fluorescence escapes from that depth as
            exp(-mu(material, KaEnergy)*thickness)
        with a fluorecence yield of the material

        """
        fluor_en = xray_line(det, 'Ka').energy/1000.0
        edge = xray_edge(det, 'K')

        # here we use the 1/e depth for the emission
        # and the 1/e depth of the incident beam:
        # the detector fluorescence can escape on either side
        mu_emit  = material_mu(det, fluor_en*1000)
        mu_input = material_mu(det, self.energy*1000)
        escape   = 0.5*scale*edge.fyield * np.exp(-mu_emit / (2*mu_input))
        escape[np.where(self.energy*1000 < edge.energy)] = 0.0
        escape *= interp(self.energy - fluor_en, self.counts*1.0,
                         self.energy, kind='cubic')
        self.escape = escape

    def update_correction(self, tau=None):
        """
        Update the deadtime correction

        if tau == None just recompute,
        otherwise assign a new tau and recompute
        """
        if tau is not None:
            self.tau = tau
        self._calc_correction()

    def _calc_correction(self):
        """
        if self.tau > 0 this will be used in the correction factor calculation
        if self.tau = 0 then we assume ocr = icr in the correction factor calculation,
                      ie only lt correction
                     (note deadtime.calc_icr handles above two conditions)
        if self.tau < 0 (or None):
           if input_counts > 0  this will be used for icr in the factor calculation
           if input_counts <= 0 we assume ocr = icr in the correction factor calculation,
                                ie only lt correction
        """
        if self.live_time <= 0 or self.real_time <= 0:
            self.dt_factor  = 1.0
            return

        if self.total_counts > 0:
            ocr = self.total_counts / self.live_time
        else:
            ocr = None

        if self.tau >= 0:
            icr = calc_icr(ocr,self.tau)
            if icr is None:
                icr = 0
            self.icr_calc = icr
        elif self.input_counts > 0:
            icr = self.input_counts / self.live_time
        else:
            icr = ocr = None
        self.dt_factor  = correction_factor(self.real_time, self.live_time,
                                             icr=icr,  ocr=ocr)
        if self.dt_factor <= 0:
            print( "Error computing counts correction factor --> setting to 1")
            self.dt_factor = 1.0

    ########################################################################
    def get_counts(self, correct=True):
        """
        Returns the counts array from the MCA

        Note if correct == True the corrected counts is returned. However,
        this does not (re)compute the correction factor, therefore, make
        sure the correction factor is up to date before requesting
        corrected counts...
        """
        if correct:
            return  (self.dt_factor * self.counts).astype(np.int)
        else:
            return self.counts

    def get_energy(self):
        """
        Returns array of energy for each channel in the MCA spectra.
        """
        chans = np.arange(self.nchans, dtype=np.float)
        self.energy = self.offset +  chans * (self.slope + chans * self.quad)
        return self.energy

    def save_columnfile(self, filename, headerlines=None):
        "write summed counts to simple ASCII column file for mca counts"
        f = open(filename, "w+")
        f.write("#XRF counts for %s\n" % self.name)
        if headerlines is not None:
            for i in headerlines:
                f.write("#%s\n" % i)
        f.write("#\n")
        f.write("#EnergyCalib.offset = %.9g \n" % self.offset)
        f.write("#EnergyCalib.slope = %.9g \n" % self.slope)
        f.write("#EnergyCalib.quad  = %.9g \n" % self.quad)
        f.write("#Acquire.RealTime  = %.9g \n" % self.real_time)
        f.write("#Acquire.LiveTime  = %.9g \n" % self.live_time)
        roiform = "#ROI_%i '%s': [%i, %i]\n"
        for i, r in enumerate(self.rois):
            f.write(roiform % (i+1, r.name, r.left, r.right))

        f.write("#-----------------------------------------\n")
        f.write("#    energy       counts     log_counts\n")

        for e, d in zip(self.energy, self.counts):
            dlog = 0.
            if  d > 0: dlog = np.log10(max(d, 1))
            f.write(" %10.4f  %12i  %12.6g\n" % (e, d, dlog))
        f.write("\n")
        f.close()

    def dump_mcafile(self):
        """return text of mca file, not writing to disk, as for dump/load"""
        b = ['VERSION:    3.1', 'ELEMENTS:   1',
             'DATE:       %s' % self.start_time,
             'CHANNELS:   %d' % len(self.counts),
             'REAL_TIME:  %f' % self.real_time,
             'LIVE_TIME:  %f' % self.live_time,
             'CAL_OFFSET: %e' % self.offset,
             'CAL_SLOPE:  %e' % self.slope,
             'CAL_QUAD:   %e' % self.quad,
             'ROIS:       %d' % len(self.rois)]

        # ROIS
        for i, roi in enumerate(self.rois):
            b.extend(['ROI_%i_LEFT:  %d' % (i, roi.left),
                      'ROI_%i_RIGHT: %d' % (i, roi.right),
                      'ROI_%i_LABEL: %s &' % (i, roi.name)])

        # environment
        for e in self.environ:
            b.append('ENVIRONMENT: %s="%s" (%s)' % (e.addr, e.val, e.desc))

        # data
        b.append('DATA: ')
        for d in self.counts:
            b.append(" %d" % d)
        b.append('')
        return '\n'.join(b)

    def save_mcafile(self, filename):
        """write MCA file

        Parameters:
        -----------
        * filename: output file name
        """
        with open(filename, 'w') as fh:
            fh.write(self.dump_mcafile())

def create_mca(counts=None, nchans=2048, offset=0, slope=0, quad=0,
               name='mca', start_time='', real_time=0, live_time=0,
               dt_factor=1, input_counts=0, tau=0, **kws):

    """create an MCA object, containing an XRF (or similar) spectrum

     Parameters:
     ------------
      counts:   counts array
      nchans:   # channels

     Returns:
     ----------
      an MCA object

    """
    return MCA(counts=counts, nchans=nchans, name=name,
               start_time=start_time, offset=offset, slope=slope,
               quad=quad, dt_factor=dt_factor, real_time=real_time,
               live_time=live_time, input_counts=input_counts,
               tau=tau, **kws)

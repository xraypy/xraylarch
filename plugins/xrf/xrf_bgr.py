"""
Methods for fitting background in energy dispersive xray spectra

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* modified for Larch, M Newville

Notes:
------
This function fits a background to an MCA spectrum. The background is
fitted using an enhanced version of the algorithm published by
Kajfosz, J. and Kwiatek, W .M. (1987)  'Non-polynomial approximation of
background in x-ray spectra.' Nucl. Instrum. Methods B22, 78-81.


Procedure:

1) At each channel "i" in a spectrum (y[i]) an n'th degree polynomial which
is concave up is fitted. Its equation is


                    (e(i) - e(j))**n
    f(j,i) = y(i) + --------------
                     top_width**n

where f(j,i) is the fitted counts in channel j for the polynomial
centered in channel i. y(i) is the input counts in channel "i", e(i) is
the energy of channel i, e(j) is the energy of channel j, and
"top_width" and "n" are user-specified parameters. The background count
in channel "j", b(j) is defined as

    b(j) = min ((f(j,i), y(j))
            i

b(j) is thus the smallest fitted polynomial in channel j, or the raw
data, whichever is smaller.

2) After the concave up polynomials have been fitted, a series of
concave down polynomials are constructed. At each channel "i" an n'th
degree polynomial which is concave up is fitted. The polynomial is slid
up from below until it "just touches" some channel of the spectrum. Call
this channel "i". The maximum height of the polynomial is thus


                            (e(i) - e(j))**n
    height(j) = max ( b(j) +  --------------  )
                 i            bottom_width**n


where bottom_width is a user_specified parameter.

3) Once the value of height(i) is known the polynomial is fitted. The
background counts in each channel are then determined from:


                               (e(i) - e(j))**n
    bgr(j) = max ( height(i) + --------------  )
              i                 bottom_width**n


bgr(j) is thus the maximum counts for any of the concave down
polynomials passing though channel j.

Before the concave-down polynomials are fitted the spectrum at each
channel it is possible to subtract out a straight line which is
tangent to the spectrum at that channel. Use the TANGENT qualifier to
do this. This is equivalent to fitting a "tilted" polynomial whose
apex is tangent to the spectrum at that channel. By fitting
polynomials which are tangent rather than vertical the background fit
is much improved on spectra with steep slopes.

Input Parameter Fields:

    bottom_width (double, variable):
        Specifies the width of the polynomials which are concave downward.
        The bottom_width is the full width in energy units at which the
        magnitude of the polynomial is 100 counts. The default is 4.

    top_width (double, variable):
        Specifies the width of the polynomials which are concave upward.
        The top_width is the full width in energy units at which the
        magnitude of the polynomial is 100 counts. The default is 0, which
        means that concave upward polynomials are not used.

    tangent (True/False):
        Specifies that the polynomials are to be tangent to the slope of the
        spectrum. The default is vertical polynomials. This option works
        best on steeply sloping spectra. It has trouble in spectra with
        big peaks because the polynomials are very tilted up inside the
        peaks. Default is False

    exponent (int):
        Specifies the power of polynomial which is used. The power must be
        an integer. The default is 2, i.e. parabolas. Higher exponents,
        for example EXPONENT=4, results in polynomials with flatter tops
        and steeper sides, which can better fit spectra with steeply
        sloping backgrounds.

    compress (int):
        Compression factor to apply before fitting the background.
        Default=4, which means, for example, that a 2048 channel spectrum
        will be rebinned to 512 channels before fitting.
        The compression is done on a temporary copy of the input spectrum,
        so the input spectrum itself is unchanged.
        The algorithm works best if the spectrum is compressed before it
        is fitted. There are two reasons for this. First, the background
        is constrained to never be larger than the data itself. If the
        spectrum has negative noise spikes they will cause the fit to be
        too low. Compression will smooth out such noise spikes.
        Second, the algorithm requires about 3*N**2 operations, so the time
        required grows rapidly with the size of the input spectrum. On a
        200 MHz Pentium it takes about 3 seconds to fit a 2048 channel
        spectrum with COMPRESS=1 (no compression), but only 0.2 seconds
        with COMPRESS=4 (the default).

        Note - compress needs a data array that integer divisible.

Inputs to calc
    data:
       The raw data to fit the background

    slope:
        Slope for the conversion from channel number to energy.
        Ie the slope from calibration

Todo:
-----
* fix compress so works for arbitrary factor
  (see ana.background)
* get rid of bottom width and top width flags
  no reason to optimize these...
"""

import numpy as np

class XRFBackground:
    """
    Class defining a spectrum background

    Attributes:
    -----------
    These may be set by kw argument upon initialization.
    * bottom_width      = 4.0   # Bottom width
    * fix_bottom_width  = True
    * top_width         = 0.0   # Top width
    * fix_width_flag    = True
    * exponent          = 2     # Exponent
    * tangent           = False # Tangent flag
    * compress          = 4     # Compress
    """

    def __init__(self, bottom_width=4, fix_bottom_width=True,
                 top_width=0, fix_top_width=True,
                 exponent=2, compress=4, tangent=False):
        self.bgr               = []      # Background
        self.bottom_width      = bottom_width
        self.fix_bottom_width  = fix_bottom_width

        self.top_width         = top_width
        self.fix_top_width     = fix_top_width
        self.compress          = compress
        self.exponent          = exponent
        self.tangent           = tangent

        self.parinfo = [{'parname':'bottom_width',
                         'value':self.bottom_width,
                         'fixed':self.fix_bottom_width,
                         'limited':[0,0], 'limits':[0., 0.], 'step':0.},
                        {'parname':'top_width',
                         'value':self.top_width,
                         'fixed':self.fix_top_width,
                         'limited':[0,0], 'limits':[0., 0.], 'step':0.}]

    def get_params(self,):
        """
        Return a dictionary of parameters
        """
        return {'bottom_width':self.bottom_width,
                'fix_bottom_width':self.fix_bottom_width,
                'top_width':self.top_width,
                'fix_top_width':self.fix_top_width,
                'exponent':self.exponent,
                'tangent':self.tangent,
                'compress':self.compress}

    def calc(self, data, slope=1.0):
        """compute background

        Parameters:
        -----------
        * data is the spectrum
        * slope is the slope of conversion channels to energy
        """
        REFERENCE_AMPL=100.
        TINY = 1.E-20
        HUGE = 1.E20
        MAX_TANGENT=2

        bottom_width = self.bottom_width
        top_width    = self.top_width
        exponent     = self.exponent
        tangent      = self.tangent
        compress     = self.compress

        nchans      = len(data)
        self.bgr    = np.zeros(nchans, dtype=np.int)
        scratch     = data[:]

        # Compress scratch spectrum
        if compress > 1:
            tmp = compress_array(scratch, compress)
            if tmp is None:
                compress = 1
            else:
                scratch = tmp
                slope = slope * compress
                nchans = nchans / compress

        # Copy scratch spectrum to background spectrum
        bckgnd = scratch[:]

        # Find maximum counts in input spectrum. This information is used to
        # limit the size of the function lookup table
        max_counts = max(scratch)

        ####################################################
        #  Fit functions which come down from top
        if top_width > 0:
            #   First make a lookup table of this function
            chan_width  = top_width / (2. * slope)
            denom       = chan_width**exponent
            indices     = np.arange(nchans*2+1, dtype=np.float) - nchans
            power_funct = indices**exponent * (REFERENCE_AMPL / denom)
            power_funct = np.compress((power_funct <= max_counts), power_funct)
            max_index   = len(power_funct)/2 - 1

            for chan in range(nchans):
                chan0  = max((chan - max_index), 0)
                chan1   = min((chan + max_index), (nchans-1))
                f       = chan0 - chan + max_index
                l       = chan1 - chan + max_index
                test    = scratch[chan] + power_funct[f:l+1]
                sub     = bckgnd[chan0:chan1+1]
                bckgnd[chan0:chan1+1] = np.maximum(sub, test)

        # Copy this approximation of background to scratch
        scratch = bckgnd[:]

        # Find maximum counts in scratch spectrum. This information is used to
        #   limit the size of the function lookup table
        max_counts = max(scratch)

        ####################################################
        # Fit functions which come up from below
        bckgnd = np.arange(nchans, dtype=np.float) - HUGE

        # First make a lookup table of this function
        chan_width = bottom_width / (2. * slope)
        if chan_width == 0:
            denom = TINY
        else:
            denom = chan_width**exponent

        indices     = np.arange(nchans*2+1, dtype=np.float) - nchans
        power_funct = indices**exponent  * (REFERENCE_AMPL / denom)
        power_funct = np.compress((power_funct <= max_counts), power_funct)
        max_index   = len(power_funct)/2 - 1

        for chan in range(nchans-1):
            tan_slope = 0.
            if tangent:
                # Find slope of tangent to spectrum at this channel
                chan0  = max((chan - MAX_TANGENT), 0)
                chan1  = min((chan + MAX_TANGENT), (nchans-1))
                denom  = chan - np.arange(chan1 - chan0 + 1, dtype=np.float)
                # is this correct?
                denom   = max(max(denom), 1)
                tan_slope = (scratch[chan] - scratch[chan0:chan1+1]) / denom
                tan_slope = np.sum(tan_slope) / (chan1 - chan0)

            chan0 = max((chan - max_index), 0)
            chan1 = min((chan + max_index), (nchans-1))
            chan1 = max(chan1, chan0)
            nc    = chan1 - chan0 + 1
            lin_offset = scratch[chan] + (np.arange(float(nc)) - nc/2) * tan_slope

            # Find the maximum height of a function centered on this channel
            # such that it is never higher than the counts in any channel

            f      = chan0 - chan + max_index
            l      = chan1 - chan + max_index
            test   = scratch[chan0:chan1+1] - lin_offset + power_funct[f:l+1]
            height = min(test)

            # We now have the function height. Set the background to the
            # height of the maximum function amplitude at each channel

            test = height + lin_offset - power_funct[f:l+1]
            sub  = bckgnd[chan0:chan1+1]
            bckgnd[chan0:chan1+1] = np.maximum(sub, test)

        ####################################################
        # Expand spectrum
        if compress > 1:
            bckgnd = expand_array(bckgnd, compress)

        # Bgr should be positive integers??
        bgr = bckgnd.astype(int)
        idx = np.where(bgr <= 0)
        bgr[idx] = 0
        self.bgr = bgr

    ##################################################################################
    def _update(self,parameters):
        """
        update for fitting
        """
        if len(parameters) != 2:
            raise "Wrong number of parameters in background"
        self.bottom_width = parameters[0]
        self.top_width    = parameters[1]

############################################################
def compress_array(array, compress):
   """
   Compresses an 1-D array by the integer factor "compress".

   near equivalent of IDL's 'rebin'....
   """
   if len(array) % compress != 0:
      print 'Warning compress must be integer divisor of array length'
      return None

   temp = np.resize(array, (len(array)/compress, compress))
   return np.sum(temp, 1)/compress

############################################################
def expand_array(array, expand, sample=0):
   """
   Expands an 1-D array by the integer factor "expand".

   if 'sample' is 1 the new array is created with sampling,
   if 0 then the new array is created via interpolation (default)
   Temporary fix until the equivalent of IDL's 'rebin' is found.
   """

   if expand == 1:
       return array
   if sample == 1:
       return np.repeat(array, expand)

   kernel = np.ones(expand)/expand
   # The following mimic the behavior of IDL's rebin when expanding
   temp = np.convolve(np.repeat(array, expand), kernel, mode=2)
   # Discard the first "expand-1" entries
   temp = temp[expand-1:]
   # Replace the last "expand" entries with the last entry of original
   for i in range(1,expand):
       temp[-i]=array[-1]
   return temp

########################################################################
########################################################################
########################################################################
def test():
    from matplotlib import pyplot
    # make some dat
    import _test_dat as test_dat
    chans = np.arange(2048)
    offset = 1.0
    slope = .01
    en = offset + slope*chans
    data = test_dat.data1(en)
    pyplot.plot(en,data,'ko')
    #
    bgr = XRFBackground(bottom_width=4.,compress=4)
    bgr.calc(data,slope=slope)
    pyplot.plot(en,bgr.bgr,'r')
    #
    pyplot.show()

########################################################################
if __name__ == "__main__":
    test()


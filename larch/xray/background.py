"""
Methods for fitting background in xray spectra (energy dispersive or diffraction)

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* modified for Larch, M Newville
* modified to work for XRD data, M. Koker

Notes:
------
This function fits a background to MCA spectrum or XRD data. The background is
fitted using an enhanced version of the algorithm published by
Kajfosz, J. and Kwiatek, W .M. (1987)  'Non-polynomial approximation of
background in x-ray spectra.' Nucl. Instrum. Methods B22, 78-81.


Procedure:

1) A series of concave down polynomials are constructed. At each
channel "i" an n'th degree polynomial which is concave up is
fitted. The polynomial is slid up from below until it "just touches"
some channel of the spectrum. Call this channel "i". The maximum
height of the polynomial is thus


                            (e(i) - e(j))**n
    height(j) = max ( b(j) +  --------------  )
                 i               width**n


where width is a user_specified parameter.

3) Once the value of height(i) is known the polynomial is fitted. The
background counts in each channel are then determined from:


                               (e(i) - e(j))**n
    bgr(j) = max ( height(i) + --------------  )
              i                     width**n


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

    width (double, variable):
        Specifies the width of the polynomials which are concave downward.
        The bottom_width is the full width in energy units at which the
        magnitude of the polynomial is 100 counts. The default is 4.

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

    tangent (True/False):
        Specifies that the polynomials are to be tangent to the slope of the
        spectrum. The default is vertical polynomials. This option works
        best on steeply sloping spectra. It has trouble in spectra with
        big peaks because the polynomials are very tilted up inside the
        peaks. Default is False

Inputs to calc()
    data:
       The raw data to fit the background

    slope:
        Slope for the conversion from channel number to energy.
        i.e. the slope from calibration

"""


import numpy as np

REFERENCE_AMPL=100.
TINY = 1.E-20
HUGE = 1.E20
MAX_TANGENT=2

def compress_array(array, compress):
    """
    Compresses an 1-D array by the integer factor compress.
    near equivalent of IDL's 'rebin'....
    """

    if len(array) % compress != 0:
        ## Trims array to be divisible by compress factor
        rng_min = int( (len(array) % compress ) / 2)
        rng_max = int( len(array) / compress ) * compress + 1
        array = array[rng_min:rng_max]

    nsize = int(len(array)/compress)
    temp = np.resize(array, (nsize, compress))
    return np.sum(temp, 1)/compress


def expand_array(array, expand, sample=0):
    """
    Expands an 1-D array by the integer factor expand.

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

class XrayBackground:
    '''
    Class defining a spectrum background

    Attributes:
    -----------
    These may be set by kw argument upon initialization.


    * width      = 4.0   # Width
    * exponent   = 2     # Exponent
    * compress   = 2     # Compress
    * tangent    = False # Tangent flag
    '''

    def __init__(self, data=None, width=4, slope=1.0, exponent=2, compress=2,
                 tangent=False, type_int=False, data_type='xrf'):

        if data_type == 'xrf': type_int = True

        self.bgr          = []
        self.width = width
        self.compress     = compress
        self.exponent     = exponent
        self.tangent      = tangent

        self.info = {'width': width, 'compress': compress,
                     'exponent': exponent, 'tangent': tangent}

        self.data = data
        if data is not None:
            self.calc(data, slope=slope, type_int=type_int)

    def calc(self, data=None, slope=1.0, type_int=False):
        '''compute background

        Parameters:
        -----------
        * data is the spectrum
        * slope is the slope of conversion channels to energy
        '''

        if data is None:
            data = self.data

        width    = self.width
        exponent = self.exponent
        tangent  = self.tangent
        compress = self.compress

        nchans   = len(data)
        self.bgr = np.zeros(nchans, dtype=np.int)
        scratch  = data[:]

        # Compress scratch spectrum
        if compress > 1:
            tmp = compress_array(scratch, compress)
            if tmp is None:
                compress = 1
            else:
                scratch = tmp
                slope = slope * compress
                nchans = len(scratch) #nchans / compress

        # Copy scratch spectrum to background spectrum
        bckgnd = scratch[:]

        # Find maximum counts in input spectrum. This information is used to
        # limit the size of the function lookup table
        max_counts = max(scratch)

        # Fit functions which come up from below
        bckgnd = np.arange(nchans, dtype=np.float) - HUGE

        denom = max(TINY, (width / (2. * slope)**exponent))

        indices     = np.arange(nchans*2+1, dtype=np.float) - nchans
        power_funct = indices**exponent  * (REFERENCE_AMPL / denom)
        power_funct = np.compress((power_funct <= max_counts), power_funct)
        max_index   = int(len(power_funct)/2 - 1)
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

            chan0 = int(max((chan - max_index), 0))
            chan1 = int(min((chan + max_index), (nchans-1)))
            chan1 = max(chan1, chan0)
            nc    = chan1 - chan0 + 1
            lin_offset = scratch[chan] + (np.arange(float(nc)) - nc/2) * tan_slope

            # Find the maximum height of a function centered on this channel
            # such that it is never higher than the counts in any channel
            f      = int(chan0 - chan + max_index)
            l      = int(chan1 - chan + max_index)
            test   = scratch[chan0:chan1+1] - lin_offset + power_funct[f:l+1]
            height = min(test)

            # We now have the function height. Set the background to the
            # height of the maximum function amplitude at each channel

            test = height + lin_offset - power_funct[f:l+1]
            sub  = bckgnd[chan0:chan1+1]
            bckgnd[chan0:chan1+1] = np.maximum(sub, test)

        # Expand spectrum
        if compress > 1:
            bckgnd = expand_array(bckgnd, compress)

        ## Set background to be of type integer
        if type_int:
            bckgnd = bckgnd.astype(int)

        ## No negative values in background
        bckgnd[np.where(bckgnd <= 0)] = 0

        self.bgr = bckgnd

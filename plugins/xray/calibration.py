"""
MultiChannel Analyzer (MCA) Energy calibration.

Authors/Modifications:
----------------------
* Mark Rivers, GSECARS
* See http://cars9.uchicago.edu/software/python/index.html
* Modified for Tdl, tpt

Notes:
------
Compute channel to energy conversions and visa-versa
for multi-channel analyzer.

We use the following convention:

    energy = offset + channels * slope (+ quad*channels^2)

where channels is an integer array (energy is a double array).
Note that it is assumed that the offset is ALWAYS defined to be
relative to channel number zero

Therefore, the index of the channel array does not
need to equal its value.  E.g.

  channels = np.arange(nchan,dtype=int)        ==> [0,1,2................2048]
  channels = np.arange(mi_ch,ma_ch,dtype=int)  ==> [33,34,..............657]

are both valid.
"""
########################################################################

import numpy as np
HC = 12.3984193  # hc in keV*Ang
########################################################################
def channel_to_energy(channels, offset=0.0, slope=1.0, quad=0.0):
    """
    Converts channels to energy using the current calibration values
    for the Mca.

    Parameters:
    -----------
    * channels: The channel numbers to be converted to energy.  This can be
      a single number or a sequence of channel numbers.

    Outputs:
    --------
    * This function returns the equivalent energy for the input channels.
    """
    c  = np.asarray(channels,dtype=np.double)
    return offset +  c * (slope + c * quad)

#########################################################################
def energy_idx(energy, emin=-1., emax=-1.):
    """
    Get the indicies of the energy array for emin and emax:

    Example:
    --------
    >>idx = energy_idx(energy,3.2,7.1)
    >>en  = energy[idx]
    >>dat = data[idx]
    """
    # find emin
    idx_min = 0
    idx_max = len(energy) - 1
    if emin >= 0.0:
        delta    = np.abs(energy - emin)
        idx_min  = np.where( delta == min(delta))[0][0]
    # find emax
    if emax >= 0.0 and emax >= emin:
        delta    = np.abs(energy - emax)
        idx_max  = np.where( delta == min(delta))[0][0]

    #return (idx_mi,idx_ma)
    index = np.arange(idx_min, idx_max+1, dtype=np.int)
    return index

########################################################################
def energy_to_channel(energy, offset=0.0, slope=1.0, quad=0.0, clip=0):
    """
    Converts energy to channel numbers for an Mca.

    Parameters:
    -----------
    * energy: The energy values to be converted to channels. This can be a
      single number or a sequence energy values.

    * clip: Set this flag to >0 to clip the returned values to be between
      0 and clip (inclusive).  The default is not to clip.

    Outputs:
    --------
    * This function returns the closest equivalent channel for the
      input energy.

    """
    if (quad == 0.0):
        channel = ((energy - offset) / slope)
    else:
        # Use the quadratic formula
        a = quad
        b = slope
        c = offset - energy
        # There are 2 roots.  I think we always want the "+" root?
        channel = (-b + np.sqrt(b**2 - 4.*a*c))/(2.*a)
    channel = np.around(channel)

    if (clip > 0):
        channel = np.clip(channel, 0, clip)
        # Note if energy is an array, below may
        # result in a return array of different length
        #condition = (channel >= 0) and (channel <=clip)
        #channel = channel.compress(condition)

    channel = channel.astype(np.int)

    return channel

########################################################################
def channel_to_d(channels,two_theta=0.0, offset=0.0, slope=1.0, quad=0.0):
    """
    Converts channels to "d-spacing"

    Parameters:
    -----------
    * channels: The channel numbers to be converted to "d-spacing".
      This can be a single number or a list of channel numbers.

    Outputs:
    --------
    * This function returns the equivalent "d-spacing" for the input channels.
      The output units are in Angstroms.

    Notes:
    ------
    This function assumes that the units of the energy calibration are keV
    and that the units of "two-theta" are degrees.

    Example:
    --------
    >>channels = [100,200,300]
    >>d = mca.channel_to_d(channels)
    """
    e = channel_to_energy(channels,offset=offset, slope=slope, quad=quad)
    return HC / (2. * e * np.sin(two_theta*np.pi/360.))


########################################################################
def d_to_channel(d, two_theta=0.0, offset=0.0, slope=1.0, quad=0.0, clip=0):
    """
    Converts "d-spacing" to channels

    Parameters:
    -----------
    * d:  The "d-spacing" values to be converted to channels.
      This can be a single number or an array of values.

    * clip: Set this flag to 1 to clip the returned values to be between
      0 and nchans-1.  The default is not to clip.

    Outputs:
    --------
    * This function returns the closest equivalent channel for the input
      "d-spacing".

    Example:
    --------
    >>channel = d_to_channel(1.598)
    """
    e = HC / (2. * d * np.sin(two_theta*np.pi/360.))
    return energy_to_channel(e,offset=offset, slope=slope, quad=quad, clip=clip)

########################################################################
########################################################################
if __name__ == "__main__":
    e = np.arange(1,15.,.1)
    idx = energy_idx(e,1.66,1.66)
    print e[idx]


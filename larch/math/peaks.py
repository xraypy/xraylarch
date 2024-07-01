"""Peak detection algorithm borrowed from PeakUtils

original author: Lucas Hermann Negri <lucashnegri@gmail.com>

"""
import numpy as np

def peak_indices(y, threshold=0.1, min_dist=1):
    """Peak detection routine.

    Finds the indices of peaks in `y` data by taking its first order
    derivative.  and using the `thres` and `min_dist` parameters, to
    control the number of peaks detected.

    Parameters
    ----------
    y : 1D ndarray
        1D amplitude data to search for peaks.
    threshold : float [0.1]
        Normalized peak threshold, as fraction of peak-to-peak of `y`.
        Peaks with amplitude higher than the threshold will be detected.
    min_dist: int [1]
        Minimum index distance between detected peaks. When multiple
        peaks are within this distance, the peak with highest amplitude
        is preferred.

    Returns
    -------
    ndarray
        Array with numeric indexes of the peaks that were detected.
    """
    thres = threshold * np.ptp(y) + y.min()
    min_dist = int(min_dist)

    # compute first order difference
    dy = np.diff(y)

    # propagate left and right values successively to fill all
    # plateau pixels (0-value)
    zeros, = np.where(dy == 0)

    # check if the signal is totally flat
    if len(zeros) == len(y) - 1:
        return np.array([])

    if len(zeros):
        # compute first order difference of zero indexes
        zeros_diff = np.diff(zeros)
        # check when zeros are not chained together
        zeros_diff_not_one, = np.add(np.where(zeros_diff != 1), 1)
        # make an array of the chained zero indexes
        zero_plateaus = np.split(zeros, zeros_diff_not_one)

        # fix if leftmost value in dy is zero
        if zero_plateaus[0][0] == 0:
            dy[zero_plateaus[0]] = dy[zero_plateaus[0][-1] + 1]
            zero_plateaus.pop(0)

        # fix if rightmost value of dy is zero
        if len(zero_plateaus) and zero_plateaus[-1][-1] == len(dy) - 1:
            dy[zero_plateaus[-1]] = dy[zero_plateaus[-1][0] - 1]
            zero_plateaus.pop(-1)

        # for each chain of zero indexes
        for plateau in zero_plateaus:
            median = np.median(plateau)
            # set leftmost values to leftmost non zero values
            dy[plateau[plateau < median]] = dy[plateau[0] - 1]
            # set rightmost and middle values to rightmost non zero values
            dy[plateau[plateau >= median]] = dy[plateau[-1] + 1]

    # find the peaks by using the first order difference
    peaks = np.where((np.hstack([dy, 0.0]) < 0.0) &
                     (np.hstack([0.0, dy]) > 0.0) &
                     (np.greater(y, thres)) )[0]

    # handle multiple peaks, respecting the minimum distance
    if peaks.size > 1 and min_dist > 1:
        highest = peaks[np.argsort(y[peaks])][::-1]
        rem = np.ones(y.size, dtype=bool)
        rem[peaks] = False

        for peak in highest:
            if not rem[peak]:
                sl = slice(max(0, peak - min_dist), peak + min_dist + 1)
                rem[sl] = True
                rem[peak] = False

        peaks = np.arange(y.size)[~rem]
    return peaks

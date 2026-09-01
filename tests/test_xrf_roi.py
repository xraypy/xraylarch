import numpy
import numpy.testing

from larch.xrf import ROI

# an ROI covers the inclusive channel range [left, right], so it holds
# (right-left+1) channels.  These tests use synthetic spectra with a
# background that the ROI background estimator reproduces exactly, so that
# the expected net counts are known analytically.

def test_roi_total_counts():
    """total counts must be the sum over the inclusive range [left, right]"""
    data = numpy.zeros(200)
    data[50:60] = 1.0
    roi = ROI(left=50, right=59, name='total', bgr_width=3)
    numpy.testing.assert_allclose(roi.get_counts(data), 10.0)

    roi = ROI(left=80, right=80, name='one channel', bgr_width=3)
    data = numpy.zeros(200)
    data[80] = 7.0
    numpy.testing.assert_allclose(roi.get_counts(data), 7.0)


def test_roi_net_counts_flat_background():
    """a flat spectrum has no peak, so net counts must be zero"""
    data = numpy.full(200, 100.0)
    for left, right in ((50, 59), (50, 69), (80, 80), (100, 149)):
        roi = ROI(left=left, right=right, name='flat', bgr_width=3)
        nchans = right - left + 1
        numpy.testing.assert_allclose(roi.get_counts(data, net=False),
                                      100.0*nchans)
        numpy.testing.assert_allclose(roi.get_counts(data, net=True), 0.0,
                                      atol=1.e-8)


def test_roi_net_counts_sloping_background():
    """the background windows are symmetric about the ROI, so their mean
    equals the mean of a linear background over the ROI: net is still zero"""
    chans = numpy.arange(200.0)
    data = 500.0 - 1.75*chans
    for left, right in ((50, 59), (50, 69), (80, 80), (100, 149)):
        roi = ROI(left=left, right=right, name='sloped', bgr_width=3)
        numpy.testing.assert_allclose(roi.get_counts(data, net=True), 0.0,
                                      atol=1.e-8)


def test_roi_net_counts_with_peak():
    """net counts must recover the area of a peak on top of a background"""
    data = numpy.full(200, 100.0)
    data[52:56] += numpy.array([50.0, 200.0, 200.0, 50.0])  # area = 500

    roi = ROI(left=50, right=59, name='peak', bgr_width=3)
    numpy.testing.assert_allclose(roi.get_counts(data, net=False), 1500.0)
    numpy.testing.assert_allclose(roi.get_counts(data, net=True), 500.0)

    # a wider ROI around the same peak must give the same net counts
    roi = ROI(left=40, right=70, name='wide peak', bgr_width=3)
    numpy.testing.assert_allclose(roi.get_counts(data, net=False), 3600.0)
    numpy.testing.assert_allclose(roi.get_counts(data, net=True), 500.0)


def test_roi_counts_attributes():
    """total and net are also stored on the ROI"""
    data = numpy.full(200, 100.0)
    data[52:56] += numpy.array([50.0, 200.0, 200.0, 50.0])  # area = 500
    roi = ROI(left=50, right=59, name='peak', bgr_width=3, counts=data)
    numpy.testing.assert_allclose(roi.total, 1500.0)
    numpy.testing.assert_allclose(roi.net, 500.0)

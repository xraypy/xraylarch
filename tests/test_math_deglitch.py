import numpy as np
from larch.math.deglitch import remove_spikes_numpy, remove_spikes_pandas, remove_spikes_scipy


def test_remove_spikes_numpy():
    # Input array with spikes
    y = np.random.random(100)
    y[24] = 10
    y[56] = 11

    # Run the function
    result = remove_spikes_numpy(y, window=3, threshold=3)

    # Check if all elements in result are smaller than 5
    assert np.all(result < 5), "Test failed: spikes not detected"


def test_remove_spikes_scipy():
    # Input array with spikes
    y = np.random.random(100)
    y[24] = 10
    y[56] = 11

    # Run the function
    result = remove_spikes_scipy(y, window=3, threshold=3)

    # Check if all elements in result are smaller than 5
    assert np.all(result < 5), "Test failed: spikes not detected"


def test_remove_spikes_pandas():
    # Input array with spikes
    y = np.random.random(100)
    y[24] = 10
    y[56] = 11

    # Run the function
    result = remove_spikes_pandas(y, window=3, threshold=3)

    # Check if all elements in result are smaller than 5
    assert np.all(result < 5), "Test failed: spikes not detected"

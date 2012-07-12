"""
This module defines a region of interest class
and utility functions.  Needs some more work.

Authors/Modifications:
-----------------------
* Mark Rivers, GSECARS
* See http://cars9.uchicago.edu/software/python/index.html
* Modified for Tdl, tpt

"""
########################################################################
import sys

from larch.larchlib import plugin_path
sys.path.insert(0, plugin_path('xray'))

from calibration import channel_to_energy, energy_to_channel

########################################################################
class Roi:
    """
    Class that defines a Region-Of-Interest (ROI)

    Attributes:
    -----------
    * left      # Left channel
    * right     # Right channel
    * label     # Name of the ROI
    * bgr_width # Number of channels to use for background subtraction

    # Computed
    * total     # Total counts
    * net       # Net (bgr subtr) counts
    * center    # Centroid
    * width     # Width
    """
    def __init__(self, left=0, right=0, label='', bgr_width=3):
        """
        Parameters:
        -----------
        * left      Left limit in index/channels numbers
        * right     Right limit in index/channels numbers
        * label     Name of the ROI
        * bgr_width Number of channels to use for background subtraction
        """
        self.left      = int(left)
        self.right     = int(right)
        self.label     = label
        self.bgr_width = int(bgr_width)

        # Computed values....
        self.total  = 0
        self.net    = 0
        self.center = int((self.right + self.left)/2.)
        self.width  = abs((self.right - self.left)/2.)

    ######################################################################################
    def __repr__(self):
        form = "<ROI %s: total=%g, net=%g, range=[%d, %d], center=%d, width=%d, nbgr=%d>"
        return form % (self.label, self.total, self.net, self.left, self.right,
                       self.center, self.width, self.bgr_width)

    ######################################################################################
    def __cmp__(self, other):
        """
        Comparison operator.

        The .left field is used to define ROI ordering
        """
        return (self.left - other.left)

    ########################################################################
    def update_counts(self, data):
        """
        Calc the total and net.

        Parameters:
        -----------
        * data: num array or list of data.
        """
        # Computed values....
        self.center = int((self.right + self.left)/2.)
        self.width  = abs((self.right - self.left)/2.)

        bgr_width = int(self.bgr_width)
        ilmin = max((self.left - bgr_width), 0 )
        irmax = min((self.right + bgr_width), len(data)-1) + 1
        bgr_left = bgr_right = 0
        if bgr_width > 0:
            bgr_left  = data[ilmin:self.left].sum() / float(bgr_width)
            bgr_right = data[self.right+1:irmax].sum() / float(bgr_width)

        #total and net cts
        self.total  = data[self.left:self.right+1].sum()
        bgr_counts  = int((1.0+self.right-self.left)*(bgr_left + bgr_right)/2.0)
        self.net    = self.total - bgr_counts

        return

########################################################################
# Utility Functions
########################################################################

def find_roi(mca, left, right, energy=False):
    """
    This procedure finds the index number of the ROI with a specified
    left and right channel number.

    Parameters:
    -----------
    * mca: mca object
    * left: Left channel number (or energy) of this ROI
    * right: Right channel number (or energy) of this ROI
    * energy: Set this flag to True to indicate that Left and Right are
      in units of energy rather than channel number.

    Output:
    -------
    * Returns the index of the specified ROI,
      -1 if the ROI was not found.

    Example:
    --------
    >>index = find_roi(mca, 100, 200)
    """
    if energy:
        kws   = dict(offset=mca.offset, slope=mca.slope,
                     quad=mca.quad, clip=len(mca.data))
        left  = energy_to_channel(left, **kws)
        right = energy_to_channel(right, **kws)
    index = 0
    for roi in self.rois:
        if left == roi.left and right == roi.right:
            return index
        index = index + 1
    return -1

########################################################################
def find_roi_label(mca, label=None):
    """
    This procedure finds the index number of the ROI with a specified
    label.

    Parameters:
    -----------
    * mca: mca object
    * label: String label of ROI

    Output:
    -------
    * Returns the index of the specified ROI,
      -1 if the ROI was not found.

    Example:
    --------
    >>index = find_roi(mca,label="Fe ka")
    """
    if label is not None:
        index = 0
        for roi in mca.rois:
            if roi.label == label:
                return index
            index = index + 1
    return -1

########################################################################
def delete_roi(mca, index):
    """
    This procedure deletes the specified region-of-interest from the MCA.

    Parameters:
    -----------
    * mca: mca object
    * index:  The index of the ROI to be deleted, range 0 to len(mca.rois)

    Example:
    --------
    >>delete_roi(mca,2)
    """
    del mca.rois[index]

########################################################################
def update_rois(mca, bgr_width=3,correct=True):
    """
    Update the rois.

    Parameters:
    -----------
    * bgr_width: Set this keyword to set the width of the background region on either
      side of the peaks when computing net counts.  The default is 3.

    * correct: Set to True to deadtime correct the data
    """
    # Sort ROIs.  This sorts by left channel.
    mca.rois.sort()
    data = mca.get_data(correct=correct)
    for j in range(len(mca.rois)):
        mca.rois[j].update_counts(data)

########################################################################
def get_rois(mca, bgr_width=3,correct=True):
    """
    Returns a tuple ([total], [net]).

    Parameters:
    -----------
    * bgr_width: Set this keyword to set the width of the background region on either
      side of the peaks when computing net counts.  The default is 3.

    * correct: Set to True to deadtime correct the data

    Outputs:
    --------
    * total:  List of the total counts in each ROI.

    * net:    List of the net counts in each ROI.

    The dimension of each list is NROIS, where NROIS
    is the number of currently defined ROIs for this MCA.  It returns
    and empty list for both if NROIS is zero.

    Example:
    --------
    >>total, net = mca.get_roi_counts(bgr_width=3)
    >>print 'Net counts = ', net
    """
    total = []
    net = []
    update_rois(mca, bgr_width=bgr_width,correct=correct)
    for j in range(len(mca.rois)):
        total.append(mca.rois[j].total)
        net.append(mca.rois[j].net)
    return (total,net)

########################################################################
def get_rois_dict(mca, bgr_width=3,correct=True):
    """
    Returns a tuple of dictionary: (total,net) where total and net are
    {'lbl',cts...}

    Parameters:
    -----------
    * bgr_width: Set this keyword to set the width of the background region on either
      side of the peaks when computing net counts.  The default is 1.

    * correct: Set to True to deadtime correct the data

    Outputs:
    --------
    * total:  Dictionary of total counts in each ROI.

    * net:    Dictionary of net counts in each ROI.

    Example:
    --------
    >>(total,net) = get_rois_dict(mca, bgr_width=3)
    """
    total = {}
    net  = {}
    update_rois(mca, bgr_width=bgr_width,correct=correct)
    for roi in self.rois:
        total[roi.label] = roi.total
        net[roi.label]   = roi.net
    return (total,net)

##########################################################################
##########################################################################
def med_get_rois(med, bgr_width=3,correct=True):
    """
    Returns the net and total counts for each Roi in each Mca in the Med.

    Outputs:
    --------
    * Returns a tuple (total, net).  total and net are lists of lists
      containing the total and net counts in each ROI.  The length of the
      outer list is self.n_detectors, the length of the total and net lists
      list for each Mca is the number of ROIs defined for that Mca.
    """
    total = []
    net = []
    for mca in med.mca:
        (t, n) = get_rois(mca,bgr_width=bgr_width,correct=correct)
        total.append(t)
        net.append(n)
    return (total, net)

#########################################################################
def med_get_rois_dict(med, bgr_width=3,correct=True):
    """
    Returns the net and total counts for each Roi in each Mca in the Med.

    Outputs:
    --------
    * Returns a list of dictionaries.  The list is of length num detectors
      each entry in the list holds a dictionary of {'lbl:(total, net),...}
    """
    total = []
    net = []
    for mca in med.mca:
        t,n = get_roiS_dict(bgr_width=bgr_width,correct=correct)
        total.append(t)
        net.append(n)
    return (total,net)

#########################################################################
def med_add_roi(med, roi):
    """
    This procedure adds an ROI to each Mca in the Med.

    Parameters:
    -----------
    * med: an med object
    * roi: A single Mca ROI to be added.
    """
    for mca in med.mca:
        if not hasattr(mca,'rois'):
            mca.rois = []
        mca.rois.append(roi)

#########################################################################
def med_delete_roi(med, index):
    """
    This procedure deletes the ROI at position "index" from each Mca in the
    Med.

    Parameters:
    -----------
    * index:  The index number of the ROI to be deleted.
    """
    for mca in med.mca:
        mca.rois.pop(index)

#########################################################################
def med_copy_rois(med, source_mca=0):
    """
    This procedure copies the ROIs defined for one Mca in the Med to all of
    the other Mcas.

    Parameters:
    -----------
    * source_mca: The index number of the Mca from which the ROIs are to
      be copied.  This number ranges from 0 to self.n_detectors-1.
      The default is the first Mca (index=0).

    Notes:
    ------
    The ROIs are copied by their position
    in energy rather than in channels. This is very useful when
    copying ROIs when the calibration parameters for each Mca in
    the Med are not identical.
    """
    units = "channel"
    if energy:
        units = "keV"

    kws = dict(offset = med.mca[source_mca].offset,
               slope =  med.mca[source_mca].slope,
               quad = med.mca[source_mca].quad,
               clip = med.mca[source_mca].clip)

    left, right, label, bgr_width  = [], [], [], []

    for roi in med.mca[source_mca].rois:
        left.append(channel_to_energy(roi.left,   **kws))
        right.append(channel_to_energy(roi.right, **kws))
        label.append(roi.label)
        bgr_width.append(roi.bgr)

    for j in range(med.n_detectors):
        off   = med.mca[j].offset
        slope = med.mca[j].slope
        quad  = med.mca[j].quad
        clip  = len(med.mca[j].data)
        med.mca[j].rois = []
        for k in range(len(left)):
            l = energy_to_channel(left[k],offset=off,slope=slope,quad=quad,clip=clip)
            r = energy_to_channel(right[k],offset=off,slope=slope,quad=quad,clip=clip)
            roi = ROI(left=int(l),right=int(r), label=label[k], bgr_width=bgr_width[k])

###

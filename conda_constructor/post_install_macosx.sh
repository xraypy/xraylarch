#/bin/bash

echo "### Larch > installing Larch-specific packages"
$PREFIX/bin/conda install -c gsecars pycifrw peakutils pyshortcuts pyepics lmfit asteval wxutils wxmplot dioptas tomopy xraylarch

$PREFIX/bin/pip install --upgrade fabio pyFAI tifffile silx hdf5plugin

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/python $PREFIX/bin/larch -m

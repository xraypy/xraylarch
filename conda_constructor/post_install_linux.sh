#/bin/bash

echo "### Larch > installing Larch-specific packages"
$PREFIX/bin/conda install -yc gsecars dioptas tomopy xraylarch=0.9.41

$PREFIX/bin/pip install --upgrade fabio pyFAI tifffile silx hdf5plugin

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/python $PREFIX/bin/larch -m

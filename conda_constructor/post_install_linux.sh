#/bin/bash

echo "### Larch > installing OS dependent packages"
$PREFIX/bin/conda install fontconfig pango patchelf

echo "### Larch > installing more scientific python packages"
$PREFIX/bin/conda install cython h5py pillow sqlalchemy psycopg2 scikit-image scikit-learn pandas wxpython=4.0.4

echo "### Larch > installing Larch-specific packages"
$PREFIX/bin/conda install -c gsecars pycifrw peakutils pyshortcuts pyepics lmfit asteval wxutils wxmplot xraylarch dioptas tomopy

$PREFIX/bin/pip install --upgrade fabio pyFAI tifffile silx hdf5plugin

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/python $PREFIX/bin/larch -m

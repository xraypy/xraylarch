#/bin/bash

echo "### Larch > installing OS dependent packages"
$PREFIX/bin/conda install fontconfig pango patchelf

echo "### Larch > installing more scientific python packages"
$PREFIX/bin/conda install cython h5py pillow sqlalchemy psycopg2 scikit-image scikit-learn pandas wxpython=4.0.4

echo "### Larch > installing Larch-specific packages"
$PREFIX/bin/conda install -c gsecars pycifrw peakutils pyshortcuts pyepics=3.3.3 lmfit=0.9.12 asteval wxutils=0.2.3 wxmplot=0.9.34 xraylarch dioptas tomopy

$PREFIX/bin/pip install --upgrade fabio pyFAI tifffile silx hdf5plugin

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/python $PREFIX/bin/larch -m

#/bin/bash

# note that "pkg" does not set PREFIX, but this is
# is found from argument $2 and __NAME_LOWER__
if [ xxx$PREFIX == 'xxx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi


echo "PREFIX :  "  $PREFIX

echo "### Larch > installing Larch-specific packages"
$PREFIX/bin/conda install -yc gsecars dioptas tomopy xraylarch=0.9.41

$PREFIX/bin/pip install --upgrade fabio pyFAI tifffile silx hdf5plugin

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/python $PREFIX/bin/larch -m

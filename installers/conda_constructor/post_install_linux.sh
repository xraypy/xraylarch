#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

echo " THIS IS POST INSTALL LINUX  PREFIX " $PREFIX
# force install of packages from conda-forge
echo "### $PREFIX/bin/conda install -yc conda-forge wxpython tomopy "

$PREFIX/bin/conda install --force-reinstall -yc conda-forge  wxpython tomopy pymatgen

# use pip to install some known-safe-for-pip packages
$PREFIX/bin/pip install xraylarch pyepics epicsapps psycopg2-binary PyCIFRW pyFAI numdifftools

# make desktop icons
$PREFIX/bin/python $PREFIX/bin/larch -m

echo '# Larch post install done!'
sleep 1

#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

echo "### Larch > creating desktop shortcuts in Desktop/Larch folder"
$PREFIX/bin/conda install --force-reinstall qtpy
$PREFIX/bin/python $PREFIX/bin/larch -m

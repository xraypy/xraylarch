#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

unset CONDA_EXE CONDA_PYTHON_EXE CONDA_PREFIX PROJ_LIB

# use pip to install some known-safe-for-pip packages
$PREFIX/bin/pip install xraylarch[larix]

# make desktop icons
$PREFIX/bin/python $PREFIX/bin/larch -m

chown -R $USER  $HOME/.larch
printenv > $HOME/.larch/xraylarch_pkginstall.log
echo '# Larch post install done!'
sleep 1

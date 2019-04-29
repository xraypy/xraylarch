#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

echo '## XrayLarch post install log ' > $HOME/xraylarch_install.log

# move noarch packages to site-packages
PYVERS=`$PREFIX/bin/python --version | sed 's/ //g' | sed 's/Python/python/g' | colrm 10`
echo '## moving noarch packacges to site-packages ' > $HOME/xraylarch_install.log
mv $PREFIX/site-packages/*  $PREFIX/lib/$PYVERS/site-packages/.

echo '## HOME ' $HOME >> $HOME/xraylarch_install.log
echo '## PREFIX ' $PREFIX >> $HOME/xraylarch_install.log
$PREFIX/bin/python -VV >> $HOME/xraylarch_install.log

echo '## Environmental Variables ' >> $HOME/xraylarch_install.log
printenv >> $HOME/xraylarch_install.log

echo "## Force conda re-installs " >> $HOME/xraylarch_install.log
$PREFIX/bin/conda install --force-reinstall qtpy

echo "## Creating desktop shortcuts in Desktop/Larch folder" >> $HOME/xraylarch_install.log
$PREFIX/bin/python $PREFIX/bin/larch -m

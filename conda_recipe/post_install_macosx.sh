#/bin/bash

echo "post_install script for Mac OSX, installing to $PREFIX"

$PREFIX/bin/pip install --upgrade --use-wheel fabio pyFAI

#  fix what seems to be a broken python.app install
mv $PREFIX/python.app  $PREFIX/orig_python_app
$PREFIX/bin/conda install python.app

# fix scripts to use pythonw instead of python
scripts="diFFit1D
diFFit2D
feff8l
gse_dtcorrect
gse_mapviewer
gse_scanviewer
larch
larch_client
larch_gui
larch_makeicons
larch_server
xrfdisplay
xrfdisplay_epics
xyfit"

for f in $scripts; do
    fname="$PREFIX/bin/$f"
    sed "s|$PREFIX/bin/python\$|$PREFIX/bin/pythonw|" $fname > Tmp
    mv Tmp $fname
done

# make folder of simple Apps / Icons
$PREFIX/bin/python $PREFIX/bin/larch_makeicons

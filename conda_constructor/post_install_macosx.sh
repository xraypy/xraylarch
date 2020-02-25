#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

# force install of packages that are noarch or have install problems
# $PREFIX/bin/conda install --force-reinstall qtpy dask pytz pyparsing networkx bokeh


# fix pythonw on MacOSX
wxapps='gse_dtcorrect gse_mapviewer larch xas_viewer xrd1d_viewer xrd2d_viewer xrfdisplay xrfdisplay_epics'

for wapp in $wxapps; do
    sed 's|bin/python|python.app/Contents/MacOS/python|g' $PREFIX/bin/$wapp > TMP
    mv TMP $PREFIX/bin/$wapp
    chmod +x $PREFIX/bin/$wapp
done


# make desktop icons
$PREFIX/bin/python $PREFIX/bin/larch -m
echo '# Larch post install done!'
chown -R $USER  $HOME/.larch
printenv > $HOME/.larch/xraylarch_pkginstall.log
sleep 3

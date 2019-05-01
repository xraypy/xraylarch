#!/bin/bash

# $2 is the install location, ($HOME by default)
if [ xx$PREFIX == 'xx' ]; then
    PREFIX=$(echo "$2/__NAME_LOWER__" | sed -e 's,//,/,g')
fi

# force install of packages that are noarch or have install problems
$PREFIX/bin/conda install --force-reinstall qtpy dask pytz pyparsing networkx bokeh

# make desktop icons
$PREFIX/bin/python $PREFIX/bin/larch -m

echo '# Larch post install done!'
sleep 1

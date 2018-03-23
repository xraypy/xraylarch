#/bin/bash

echo "post_install script for Mac OSX, installing to $PREFIX"

# fix scripts to use pythonw instead of python
# make folder of simple Apps / Icons

$PREFIX/bin/python $PREFIX/bin/larch_makeicons

# $PREFIX/bin/pip install --upgrade --use-wheel fabio pyFAI tifffile

### fix what seems to be a broken python.app install
# mv $PREFIX/python.app  $PREFIX/orig_python_app
# $PREFIX/bin/conda install -y python.app

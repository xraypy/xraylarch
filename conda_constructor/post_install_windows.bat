;;  post install for windows

$PREFIX/bin/conda install -yc gsecars dioptas tomopy xraylarch=0.9.41

%PREFIX%\Scripts\pip.exe install --upgrade fabio pyFAI silx hdf5plugin

%PREFIX%\Scripts\larch-script.py -m

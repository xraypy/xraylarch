;;  post install for windows

%PREFIX%\Scripts\conda.exe install -yc gsecars pycifrw dioptas tomopy xraylarch=0.9.41

%PREFIX%\Scripts\pip.exe install --upgrade fabio pyFAI silx hdf5plugin

%PREFIX%\python.exe %PREFIX%\Scripts\larch-script.py -m

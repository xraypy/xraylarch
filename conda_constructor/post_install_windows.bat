;;  post install for windows

%PREFIX%\Scripts\pip.exe install --upgrade fabio pyFAI silx hdf5plugin

%PREFIX%\Scripts\larch -m

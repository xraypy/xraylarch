;;  post install for windows

%PREFIX%\Scripts\conda.exe install -c gsecars pycifrw peakutils pyshortcuts pyepics lmfit asteval wxutils wxmplot dioptas tomopy xraylarch

%PREFIX%\Scripts\pip.exe install --upgrade fabio pyFAI silx hdf5plugin

%PREFIX%\Scripts\larch -m

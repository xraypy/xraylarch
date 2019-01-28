;;  post install for windows

;; echo "### Larch > installing OS dependent packages"
%PREFIX\Scripts\conda.exe install pywin32 console_shortcut

;; echo "### Larch > installing more scientific python packages"
%PREFIX%\Scripts\conda.exe install cython h5py pillow sqlalchemy psycopg2 scikit-image scikit-learn pandas wxpython=4.0.4

%PREFIX%\Scripts\conda.exe install -c gsecars pycifrw peakutils pyshortcuts pyepics lmfit asteval wxutils wxmplot dioptas tomopy xraylarch

%PREFIX%\Scripts\pip.exe install --upgrade fabio pyFAI silx hdf5plugin

%PREFIX%\Scripts\larch -m

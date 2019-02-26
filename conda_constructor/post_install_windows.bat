REM  post install for windows

%PREFIX%\Scripts\conda.exe install -yc gsecars tomopy
%PREFIX%\Scripts\conda.exe install --force-reinstall qtpy

%PREFIX%\python.exe %PREFIX%\Scripts\larch-script.py -m

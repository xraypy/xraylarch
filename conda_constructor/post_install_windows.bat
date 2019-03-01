REM  post install for windows

%PREFIX%\Scripts\conda.exe install -y --force-reinstall qtpy
%PREFIX%\Scripts\conda.exe install -yc gsecars tomopy

%PREFIX%\python.exe %PREFIX%\Scripts\larch-script.py -m

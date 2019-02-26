REM  post install for windows

%PREFIX%\Scripts\conda.exe install -yc gsecars --force-reinstall tomopy qtpy

%PREFIX%\python.exe %PREFIX%\Scripts\larch-script.py -m

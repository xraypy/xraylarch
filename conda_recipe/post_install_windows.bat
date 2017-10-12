;;  post install for windows

%PREFIX%\Scripts\pip.exe install --upgrade --use-wheel fabio pyFAI

%PREFIX%\bin\larch_makeicons.exe

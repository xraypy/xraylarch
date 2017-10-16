;;  post install for windows

%PREFIX%\Scripts\pip.exe install --upgrade --use-wheel fabio pyFAI

%PREFIX%\Scripts\larch_makeicons.exe

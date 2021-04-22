
REM # install wxpython and tomopy from conda-forge
call %PREFIX%\condabin\conda install --force-reinstall -yc conda-forge wxpython tomopy

REM # use pip to install some known-safe-for-pip packages
%PREFIX%\Scripts\pip.exe install xraylarch pyepics epicsapps psycopg2-binary PyCIFRW pyFAI numdifftools

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

echo '# Larch post install done!'
timeout /t 10

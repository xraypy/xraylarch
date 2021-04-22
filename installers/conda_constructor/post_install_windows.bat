
REM # install wxpython and tomopy from conda-forge
call %PREFIX%\condabin\conda install -yc conda-forge wxpython tomopy

REM # use pip to install some known-safe-for-pip packages
%PREFIX%\Scripts\pip.exe install xraylarch pyepics epicsapps psycopg2-binary PyCIFRW pyFAI numdifftools

sleep 1

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

echo '# Larch post install done!'
sleep 5

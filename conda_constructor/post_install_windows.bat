REM  post install for windows


REM # force install of packages that are noarch or have install problems
%PREFIX%\Scripts\conda.exe install -y --force-reinstall qtpy dask pytz pyparsing networkx bokeh

REM # make desktop icons
%PREFIX%\python.exe %PREFIX%\Scripts\larch-script.py -m


echo '# Larch post install done!'
sleep 1

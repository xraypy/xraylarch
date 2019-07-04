

REM # force install of packages that are noarch or have install problems
%PREFIX%\Scripts\conda.exe install -y --force qtpy dask pytz pyparsing networkx bokeh conda==4.5.13

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

echo '# Larch post install done!'
sleep 15


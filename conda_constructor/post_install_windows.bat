

REM # force install of packages that are noarch or have install problems
REM %PREFIX%\Scripts\conda.exe install -y --force qtpy dask pytz

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

echo '# Larch post install done!'
sleep 10

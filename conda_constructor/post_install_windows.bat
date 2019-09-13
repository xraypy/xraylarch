
REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

REM # force install of packages that are noarch or have install problems
%PREFIX%\Scripts\conda.exe install -y -c conda-forge tomopy

echo '# Larch post install done!'
sleep 10




REM # use pip to install some known-safe-for-pip packages
echo "Windows Post Install"

call "%PREFIX%\Scripts\activate.bat"

%PREFIX%\python -m pip install "xraylarch[larix]"

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m

echo '# Larch post install done!'
timeout /t 10




echo "Larch Installation for Windows" 

set PATH=%PATH%;%PREFIX%;%PREFIX%\bin;%PREFIX%\mingw-w64\bin;%PREFIX%\condabin;%PREFIX%\Scripts;
set PATH=%PATH%;%PREFIX%\Library\bin;%PREFIX%\Library\usr\bin

call "%PREFIX%\Scripts\activate.bat"

%PREFIX%\python -m pip install "xraylarch[larix]"

echo "Making Desktop Icons"
%PREFIX%\Scripts\larch.exe -m

echo 'Larch post installation done'
timeout /t 10


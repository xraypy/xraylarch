@echo off

set prefix=%USERPROFILE%\xraylarch

set condaurl=https://github.com/conda-forge/miniforge/releases/latest/download
set condafile=Miniforge3-Windows-x86_64.exe

if not exist %~dp0%condafile% (
    echo ## Downloading Miniconda from https://repo.anaconda.com/miniconda/, please wait...
    bitsadmin /transfer getmamba /download /priority normal %condaurl%/%condafile% %~dp0%condafile%
)

echo ## Installing miniconda environment to %prefix%, please wait...

%~dp0%condafile% /InstallationType=JustMe /RegisterPython=0 /S /D=%prefix%

echo ## basic mamba installed, running updates

set PATH=%prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts;%PATH%

echo ## Installing basic python scipy packages
call %prefix%\Scripts\mamba install -yc conda-forge python==3.11.5 numpy scipy matplotlib h5py scikit-image scikit-learn pycifrw pandas jupyter plotly wxpython fabio pyfai pymatgen mkl_fft tomopy

echo ## Installing xraylarch and dependencies from PyPI
call %prefix%\Scripts\pip install xraylarch[larix]

echo ## Creating desktop shortcuts
call %prefix%\Scripts\larch -m

echo ## Installation to %prefix% done!
echo ## Applications can be run from the Larch folder on your Desktop.
echo ##
echo ## To use from a terminal or command-line, you may want to add
echo ##     %prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts
echo ## to your PATH environment, such as
echo ##     set PATH=%prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts;%PATH%

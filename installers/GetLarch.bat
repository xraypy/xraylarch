@echo off


set prefix=%USERPROFILE%\xraylarch

set condaurl=https://github.com/conda-forge/miniforge/releases/download/4.10.2-0/
set condafile=Miniforge3-Windows-x86_64.exe

if not exist %~dp0%condafile% (
    echo ## Downloading Miniconda from https://repo.anaconda.com/miniconda/, please wait...
    bitsadmin /transfer getminiconda /download /priority normal %condaurl%/%condafile% %~dp0%condafile%
)

echo ## Installing miniconda environment to %prefix%, please wait...

set CONDA_EXE=
set CONDA_PYTHON_EXE=
set CONDA_PREFIX=
set PROJ_LIB=

%~dp0%condafile% /InstallationType=JustMe /RegisterPython=0 /S /D=%prefix%

echo ## basic miniconda installed, running updates

set PATH=%prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts;%PATH%

call %prefix%\condabin\conda update -n base -yc defaults --all
call %prefix%\condabin\conda activate base
call %prefix%\condabin\conda config --set auto_activate_base true

echo ## Installing wxpython and tomopy from conda-forge
call %prefix%\condabin\conda install -yc conda-forge wxpython tomopy scipy matplotlib scikit-image scikit-learn pymatgen pycifrw

echo ## Installing xraylarch and dependencies from PyPI
call %prefix%\Scripts\pip install wxmplot wxutils lmfit asteval pyshortcuts pyfai xraylarch

echo ## Creating desktop shortcuts
call %prefix%\Scripts\larch -m


echo ## Installation to %prefix% done!
echo ## Applications can be run from the Larch folder on your Desktop.
echo ##
echo ## To use from a terminal or command-line, you may want to add
echo ##     %prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts
echo ## to your PATH environment, such as
echo ##     set PATH=%prefix%;%prefix%\bin;%prefix%\condabin;%prefix%\Scripts;%PATH%

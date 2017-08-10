@echo off

REM conda config --add channels conda-forge
REM conda config --add channels newville
REM conda config --set always_yes yes --set changeps1 no

conda update conda

conda install numpy scipy h5py matplotlib cython

conda install h5py pandas nose sphinx sqlalchemy
conda install pillow scikit-learn scikit-image
conda install yaml pango pcre wxpython 
conda install lmfit termcolor pyepics 
conda install wxmplot wxutils 
conda install fabio pyfai

REM conda update numpy scipy h5py matplotlib cython
REM conda update h5py pandas nose sphinx sqlalchemy
REM conda update pillow scikit-learn scikit-image
REM conda update yaml pango pcre wxpython 
REM conda update lmfit termcolor pyepics 


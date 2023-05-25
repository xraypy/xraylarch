#!/bin/sh
##
## script to install Larch on Linux or MacOS
## using a Mambaforge environment and installing
## all required packages with mamba or pip

prefix=$HOME/xraylarch

uname=`uname`
if [ $uname == Darwin ]; then
    uname=MacOSX
fi

condaurl="https://github.com/conda-forge/miniforge/releases/latest/download"
condafile="Mambaforge-$uname-x86_64.sh"

logfile=GetLarch.log

## set list of conda packages to install from conda-forge
cforge_pkgs="numpy=>1.22 scipy=>1.8 matplotlib=>3.6 scikit-image scikit-learn pycifrw pandas jupyter plotly wxpython fabio pyfai pymatgen mkl_fft tomopy"

## set list of pip packages to install from pypi
pip_pkgs="wxmplot wxutils lmfit asteval pyshortcuts pyepics epicsapps psycopg2-binary"

unset CONDA_EXE CONDA_PYTHON_EXE CONDA_PREFIX PROJ_LIB

use_devel=0

## get command line options
for opt ; do
  option=''
  case "$opt" in
    -*=*)
        optarg=`echo "$opt" | sed 's/[-_a-zA-Z0-9]*=//'`
        option=`echo "$opt" | sed 's/=.*//' | sed 's/-*//'`
        ;;
    *)
        option=`echo "$opt" | sed 's/^-*//'`
        optarg=
        ;;
  esac
  case "$option" in
    prefix)        prefix=$optarg ;;
    devel)         use_devel=1 ;;
    -h | h | -help | --help | help) cat<<EOF
Usage: GetLarch.sh [options]
Options:
  --prefix=PREFIX             base directory for installation [$prefix]
  --devel                     install development branch of xraylarch instead of latest release [no]
EOF
    exit 0
    ;;

   *)
       echo " unknown option "  $opt
       exit 1
       ;;
  esac
done

## test for prefix already existing
if [ -d $prefix ] ; then
   echo "##Error: $prefix exists."
   exit 0
fi


larchurl='xraylarch'
if [ $use_devel == 1 ]; then
    larchurl='git+https://github.com/xraypy/xraylarch.git'
fi

echo "##############  " | tee $logfile
echo "##  This script will install Larch for $uname to $prefix" | tee -a $logfile
echo "##  " | tee -a $logfile
echo "##  The following packages will be taken from conda-forge:" | tee -a $logfile
echo "##        $cforge_pkgs " | tee -a $logfile
echo "##  " | tee -a $logfile
echo "##  See GetLarch.log for complete log and error messages" | tee -a $logfile
echo "##############  " | tee -a $logfile


## download miniconda installer if needed
if [ ! -f $condafile ] ; then
    echo "## Downloading Miniconda installer for $uname" | tee -a $logfile
    echo "#>  /usr/bin/curl -L $condaurl/miniconda/$condafile -O " | tee -a $logfile
    /usr/bin/curl -L $condaurl/$condafile -O | tee -a $logfile
fi

# install and update miniconda
echo "##  Installing Miniconda for $uname to $prefix" | tee -a $logfile
echo "#>  sh ./$condafile -b -p $prefix " | tee -a $logfile
sh ./$condafile -b -p $prefix | tee -a $logfile

export PATH=$prefix/bin:$PATH

echo "##  Installing packages from conda-forge"  | tee -a $logfile
echo "#> $prefix/bin/mamba install -yc conda-forge $cforge_pkgs " | tee -a $logfile
$prefix/bin/mamba install -y -c conda-forge $cforge_pkgs

## pip install of dependencies and Larch
echo "##Installing dependencies from PyPI"  | tee -a $logfile
echo "#> $prefix/bin/pip install $pip_pkgs"| tee -a $logfile
$prefix/bin/pip install $pip_pkgs | tee -a $logfile

echo "##Installing xraylarch as 'pip install $larchurl'"  | tee -a $logfile
echo "#> $prefix/bin/pip install $larchurl"| tee -a $logfile
$prefix/bin/pip install $larchurl | tee -a $logfile

## create desktop shortcuts
echo "## Creating desktop shortcuts"
$prefix/bin/larch -m

echo "##############  " | tee -a $logfile
echo "##  Larch Installation to $prefix done." | tee -a $logfile
echo "##  Applications can be run from the Larch folder on your Desktop." | tee -a $logfile
echo "##  "| tee -a $logfile
echo "##  To use from a terminal, you may want to add:"  | tee -a $logfile
echo "        export PATH=$prefix/bin:\$PATH"  | tee -a $logfile
echo "##  to your $SHELL startup script."  | tee -a $logfile
echo "##  "| tee -a $logfile
echo "##  See GetLarch.log for complete log and error messages" | tee -a $logfile
echo "##############  " | tee -a $logfile

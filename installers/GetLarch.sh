#!/bin/sh
##
## script to install Larch on Linux or MacOS
## using a Mambaforge environment and installing
## all required packages with mamba or pip

prefix=$HOME/xraylarch
larchurl='xraylarch[larix]'

uname=`uname`
if [ $uname == Darwin ]; then
    uname=MacOSX
fi

condaurl="https://github.com/conda-forge/miniforge/releases/latest/download"

condafile="Miniforge3-$uname-x86_64.sh"
condafile="Mambaforge-$uname-x86_64.sh"

logfile=GetLarch.log

## set list of conda packages to install from conda-forge
cforge_pkgs="python=>3.12.3 numpy scipy matplotlib h5py scikit-image scikit-learn pycifrw pandas jupyter plotly wxpython fabio pyfai pymatgen mkl_fft tomopy"

unset CONDA_EXE CONDA_PYTHON_EXE CONDA_PREFIX PROJ_LIB


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
    -h | h | -help | --help | help) cat<<EOF
Usage: GetLarch.sh [options]
Options:
  --prefix=PREFIX             base directory for installation [$prefix]
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
$prefix/bin/mamba list

echo "##Installing xraylarch as 'pip install \"$larchurl\"'"  | tee -a $logfile
echo "#> $prefix/bin/pip install \"$larchurl\""| tee -a $logfile
$prefix/bin/pip install "$larchurl" | tee -a $logfile

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

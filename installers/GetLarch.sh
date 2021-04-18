#!/bin/sh
##
## script to install Larch on Linux or MacOS
## using a Miniconda environment and all required packages


prefix=$HOME/xraylarch

uname=`uname`
if test $uname = Darwin; then
    uname=MacOSX
fi

condafile=Miniconda3-latest-$uname-x86_64.sh
logfile=GetLarch.log

with_wx=1
with_tomopy=1
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
    with-tomopy)   with_tomopy=1 ;;
    no-tomopy)     with_tomopy=0 ;;
    with-wx)       with_wx=1 ;;
    no-wx)         with_wx=0 ;;
    -h | h | -help | --help | help) cat<<EOF
Usage: GetLarch.sh [options]
Options:
  --prefix=PREFIX             base directory for installation [$prefix]
  --with-wx  / --no-wx        include / omit wxPython from Anaconda Python [with]
  --with-tomopy / --no-tompy  include / omit tomopy from Anaconda Python   [with]
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

## set list of conda packages to install from conda-forge
cforge_pkgs="numpy scipy matplotlib scikit-image scikit-learn"

if test $uname==MacOSX ; then
    cforge_pkgs="$cforge_pkgs python.app"
fi

if test $with_wx = 1; then
    cforge_pkgs="$cforge_pkgs wxpython"
fi

if test $with_tomopy = 1; then
    cforge_pkgs="$cforge_pkgs tomopy"
fi

echo "##############  " | tee $logfile
echo "##  This script will install Larch for $uname to $prefix" | tee -a $logfile
echo "##  " | tee -a $logfile
echo "##  See GetLarch.log for complete log and error messages" | tee -a $logfile
echo "##############  " | tee -a $logfile

## download miniconda installer if needed
if [ ! -f $condafile ] ; then
    echo "## Downloading Miniconda installer for $uname" | tee -a $logfile
    /usr/bin/curl https://repo.anaconda.com/miniconda/$condafile -O | tee -a $logfile
fi

# install and update miniconda
echo "##  Installing Miniconda for $uname to $prefix" | tee -a $logfile
sh ./$condafile -b -p $prefix | tee -a $logfile

echo "##  Running conda updates"  | tee -a $logfile
$prefix/bin/conda update -n base -yc defaults --all | tee -a $logfile

export PATH=$prefix/bin:$PATH

echo "##  Installing packages from conda-forge"  | tee -a $logfile
$prefix/bin/conda install -yc conda-forge $cforge_pkgs | tee -a $logfile

## pip install of dependencies and Larch
echo "##  Installing xraylarch dependencies from PyPI" | tee -a $logfile
$prefix/bin/pip install packaging pyepics epicsapps psycopg2-binary wxmplot wxutils PyCIFRW pyFAI lmfit numdifftools peakutils scikit-image scikit-learn | tee -a $logfile
echo "##Installing xraylarch from PyPI"  | tee -a $logfile
$prefix/bin/pip install xraylarch | tee -a $logfile

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

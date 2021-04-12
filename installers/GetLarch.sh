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

##
##
## test for prefix already existing
if [ -d $prefix ] ; then
   echo "##Error: $prefix exists."
   exit 0
fi

## download miniconda installer if needed
if [ ! -f $condafile ] ; then
    echo "##Downloading Miniconda installer for $uname"
    /usr/bin/curl https://repo.anaconda.com/miniconda/$condafile -O
fi

# install and update miniconda
echo "##Installing Miniconda for $uname to $prefix"
sh ./$condafile -b -p $prefix

echo "#Running conda updates"
$prefix/bin/conda update -n base -yc defaults --all

export PATH=$prefix/bin:$PATH

## optional conda installs of wxPython and TomoPy
if test $with_wx = 1; then
    echo "##Installing wxPython"
    $prefix/bin/conda install -yc conda-forge wxpython
fi

if test $with_tomopy = 1; then
    echo "##Installing tomopy"
    $prefix/bin/conda install -yc conda-forge tomopy
fi

## pip install of dependencies and Larch
echo "##Installing xraylarch dependencies from PyPI"
$prefix/bin/pip install packaging pyepics epicsapps psycopg2-binary wxmplot wxutils PyCIFRW pyFAI lmfit numdifftools peakutils scikit-image scikit-learn
echo "##Installing xraylarch from PyPI"
$prefix/bin/pip install xraylarch


## create desktop shortcuts
echo "##Creating desktop shortcuts"
$prefix/bin/larch -m

msg="######\n
Installation done!  You may want to add:\n\n
     export PATH=$prefix/bin:\$PATH\n
\nto your $SHELL startup script.\n
######\n
"

echo -e $msg

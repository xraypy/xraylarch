installdir='/www/apache/htdocs/software/python/lmfit'
docbuild='doc/_build'
name='larch'
cd doc
echo '# Making docs'
make all
cd _build/html
tar czf ../../../docs.tgz *

cd ../../../
#
echo "# Switching to gh-pages branch"
git checkout gh-pages

if  [ $? -ne 0 ]  ; then
  echo ' failed.'
  exit
fi

tar xzf docs.tgz 

echo "# commit changes to gh-pages branch"
git add *.html */*.html  *.js objects.inv searchindex.js larch.pdf _sources/ _static/ _images/ _images/math
git commit -am "updated docs"

if  [ $? -ne 0 ]  ; then
  echo ' failed.'
  exit
fi

echo "# Pushing docs to github"
git push

echo "# switch back to master branch"
git checkout master

if  [ $? -ne 0 ]  ; then
  echo ' failed.'
  exit
fi

# # install locally
# echo "# Installing docs to CARS web pages"
# cp ../_docs.tar.gz $installdir/..
#
# cd $installdir
# if  [ $? -ne 0 ]  ; then
#   echo ' failed.'
#   exit
# fi
#
# tar xvzf ../_docs.tar.gz

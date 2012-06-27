installdir='/www/apache/htdocs/software/python/lmfit'
docbuild='doc/_build'
name='larch'
cd doc
echo '# Making docs'
make all
cd _build/html
tar cvzf ../../docs.tgz *
cd ../../
#
echo "# Switching to gh-pages branch"
git checkout gh-pages

if  [ $? -ne 0 ]  ; then
  echo ' failed.'
  exit
fi

tar xzf docs.tar.gz .

echo "# commit changes to gh-pages branch"
git add *.html _source/  _static/*
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

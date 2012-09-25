docdir='doc'
name='larch'

finish() {
   echo "# git checkout master"
   git checkout master
   if  [ $? -ne 0 ]  ; then
      echo '# git checkout master failed.'
      exit
   fi
}

cd $docdir
echo '# Making docs'
make clean 
make html pdf
cd _build/html
tar czf ../../../_docs.tgz *
cd ../../../
#
echo "# Switching to gh-pages branch"
git checkout gh-pages
git pull

if  [ $? -ne 0 ]  ; then
  echo '# git pull on gh-pages branch failed.'
  finish
fi

tar xzf _docs.tgz 
echo "# commit changes to gh-pages branch"
git add *.html */*.html larch.pdf
git add *.js objects.inv searchindex.js 
git add  _sources/ _static/ _images/ _images/math
git commit -am "updated docs"

if  [ $? -ne 0 ]  ; then
  echo '# git commit of all doc changes failed.'
  finish
fi

echo "# Pushing docs to github"
git push
if  [ $? -ne 0 ]  ; then
  echo '# git push failed.'
  finish
fi

echo "# switch back to master branch"
git checkout master
if  [ $? -ne 0 ]  ; then
  echo '# checkout master failed.'
  finish
fi

# -*- coding: utf-8 -*-
#
# larch documentation build configuration file, created by

from pathlib import Path
import sys, os

# sys.path.insert(0, Path('sphinx', 'ext'))
sys.path.insert(0, '.')

extensions = ['sphinx.ext.mathjax', 'sphinx.ext.autodoc',
              'sphinx.ext.napoleon', 'sphinx.ext.extlinks',
              'sphinx.ext.intersphinx', 'sphinx.ext.ifconfig',
              'sphinxcontrib.bibtex', 'sphinx_subfigure',
              'sphinx_copybutton', 'numpydoc' ]

import authorlist_format

intersphinx_mapping = {'py':    ('https://docs.python.org/3', None),
                       'numpy': ('https://numpy.org/doc/stable/', None),
                       'scipy': ('https://docs.scipy.org/doc/scipy/', None),
                       }

extlinks = {
    'scipydoc' : ('https://docs.scipy.org/doc/scipy/reference/generated/scipy.%s.html', 'scipy.'),
    'numpydoc' : ('https://docs.scipy.org/doc/numpy/reference/generated/numpy.%s.html', 'numpy.'),
    'lmfitdoc' : ('https://lmfit.github.io/lmfit-py/%s.html', 'lmfit.'),
    'lmfitx' : ('https://lmfit.github.io/lmfit-py/%s', ' '),
    }

# List of patterns, relative to source directory, that match files and
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = {'.rst': 'restructuredtext'}

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'xraylarch'
author = 'Matthew Newville'
copyright = 'Matthew Newville, The University of Chicago, 2022'

numfig = True
numfig_secnum_depth = 3
numfig_format = {'figure': 'Figure %s',
                 'table': 'Table %s',
                 'code-block': 'Listing %s',
                 'section': 'Section %s'}

bibtex_bibfiles = ['larch.bib']

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
try:
    import larch
    release = larch.__release_version__
except ImportError:
    release = 'unknown'

exclude_trees = ['_build']
exclude_patterns = ['_build', 'sphinx', '_junk', 'epilog.rst']

# rst_epilog = open(Path('epilog.rst'),'r').read()# .decode('utf-8')

add_function_parentheses = True
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# -- Options for HTML output ---------------------------------------------------

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = ['sphinx/theme']
# html_theme = 'nature'
# html_theme = 'larchdoc'

html_theme = 'bizstyle'
html_static_path = ['_static']
html_css_files = ['xraylarch_style.css']
html_sidebars = {'index': ['indexsidebar.html','searchbox.html']}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

# htmlhelp_basename = 'larchdoc'
# html_domain_indices = False

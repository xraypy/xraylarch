# -*- coding: utf-8 -*-
#
# larch documentation build configuration file, created by

import sys, os


CURDIR = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, os.path.abspath(os.path.join('sphinx', 'ext')))
sys.path.insert(0, CURDIR)
sys.path.append(os.path.abspath(os.path.join('.')))

from extensions import extensions

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
source_suffix = '.rst'

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
# The full version, including alpha/beta/rc tags.
except ImportError:
    release = 'unknown (larch import failed??)'

exclude_trees = ['_build']
exclude_patterns = ['_build', 'sphinx', '_junk', 'epilog.rst']

#sphinxtr
# Ideally, we wouldn't have to do this, but sphinx seems to have trouble with
# directives inside only directives
if tags.has('latex'):
    master_doc = 'index_tex'
    exclude_patterns.append('index.rst')
else:
    master_doc = 'index'
    exclude_patterns.append('index_tex.rst')

#sphinxtr
# A string of reStructuredText that will be included at the end of
# every source file that is read.
rst_epilog = open(os.path.join(CURDIR, 'epilog.rst'),'r').read()# .decode('utf-8')

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
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
html_theme_path = ['sphinx/theme']
# html_theme = 'nature'
html_theme = 'larchdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

# html_theme_options = {'collapsiblesidebar': False}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title =

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typograpbhically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'index': ['indexsidebar.html','searchbox.html']}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

htmlhelp_basename = 'larchdoc'
html_domain_indices = False

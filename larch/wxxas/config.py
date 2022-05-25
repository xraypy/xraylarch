import wxmplot

from larch.site_config import get_homedir
from larch.xafs.xafsutils import FT_WINDOWS
from larch.xray import atomic_symbols

ATSYMS = ['?'] + atomic_symbols
EDGES  = ['K', 'L3', 'L2', 'L1', 'M5', 'M4', 'M3', 'N7']
CONF_FILE = 'xas_viewer.conf'

wxmplot.config.Themes['fivethirtyeight'].update({'legend.fontsize': 10,
                                                 'xtick.labelsize': 9,
                                                 'ytick.labelsize': 9,
                                                 'axes.labelsize': 9,
                                                 'axes.titlesize': 13})

ARRAYS = {'mu':      'Raw \u03BC(E)',
          'norm':    'Normalized \u03BC(E)',
          'flat':    'Flattened \u03BC(E)',
          'prelines':   '\u03BC(E) + Pre-/Post-edge',
          'mback_norm': '\u03BC(E) + MBACK  \u03BC(E)',
          'mback_poly': 'MBACK + Poly Normalized',
          'dmude':     'd\u03BC(E)/dE ',
          'norm+dmude': 'Normalized \u03BC(E) + d\u03BC(E)/dE',
          'd2mude':     'd^2\u03BC(E)/dE^2',
          'norm+d2mude': 'Normalized \u03BC(E) + d^2\u03BC(E)/dE^2',
          'deconv': 'Deconvolved \u03BC(E)',
          'chi':  '\u03c7(k)',
          'chi0': '\u03c7(k)',
          'chi1': 'k \u03c7(k)',
          'chi2': 'k^2 \u03c7(k)',
          'chi3': 'k^3 \u03c7(k)',
          'chir_mag':  '|\u03c7(R)|',
          'chir_re':  'Re[\u03c7(R)]',
          'chir_mag+chir_re': '|\u03c7(R)| + Re[\u03c7(R)]',
          'chir_re_chir_im':  'Re[\u03c7(R)] + Im[\u03c7(R)]',
          'noplot': '<no plot>',
          }

# wavelet = 'EXAFS wavelet'


def make_array_choice(opts):
    """make (ordered) dict of {Array Description: varname}"""
    out = {}
    for n in opts:
        if n in ARRAYS:
            out[ARRAYS[n]] = n
    return out


Linear_ArrayChoices = make_array_choice(['norm', 'flat', 'dmude', 'chi0', 'chi1', 'chi2'])
PrePeak_ArrayChoices = make_array_choice(['norm', 'flat', 'deconv'])
Regress_Choices = ['Partial Least Squares', 'LassoLars']

PlotWindowChoices = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

NNORM_CHOICES = {'auto':None,  'constant':0, 'linear':1, 'quadratic':2, 'cubic':3}
NORM_METHODS = ('polynomial', 'mback')

ATHENA_CLAMPNAMES = {'none': 0, 'slight': 1, 'weak': 5, 'medium': 20,
                     'strong': 100, 'rigid': 500}


Feffit_KWChoices = {'1': '1', '2': '2', '3': '3',
                    '2 and 3': '[2, 3]',
                    '1, 2, and 3': '[2, 1, 3]'}

Feffit_SpaceChoices = {'R space':'r', 'k space':'k', 'wavelet': 'w'}
Feffit_PlotChoices = {'K and R space': 'k+r', 'R space only': 'r'}


Valid_DataTypes = ('string', 'float', 'int', 'bool', 'choice', 'path')

PANELS = {'exafs': 'EXAFS Background Subtraction and Fourier Transforms',
          'feffit': 'Feff Fitting of EXAFS Paths',
          'lincombo': 'Linear Combination Analysis',
          'pca': 'Principal Component Analysis',
          'prepeaks': 'Pre-edge Peak Analysis',
          'regression': 'Regression and Feature Selection',
          'xasnorm': 'XAS Normalization',
          }

class CVar:
    """configuration variable"""
    def __init__(self, name, value, dtype, choices=None, desc='a variable',
                 min=None, max=None, step=1):
        self.name = name
        self.value = value
        self.dtype = dtype
        self.choices = choices
        self.desc = desc
        self.min = min
        self.max = max
        self.step = step

        if dtype not in Valid_DataTypes:
            raise ValueError(f"unknown configuration type '{dtype}' for '{name}'")

        if dtype == 'choice' and self.choices is None:
            raise ValueError(f"choice configuration type must have choices for '{name}'")

    def __repr__(self):
        return f"CVar('{self.name}', {self.value!r}, '{self.dtype}')"

##
## sections
##
CONF_SECTIONS = {k:v for k, v in PANELS.items()}
CONF_SECTIONS.update({'main': 'Main program configuration',
                      'pin': 'Pin icon to select points from plots',
                      'plot': 'General Plotting',
                      'autosave': 'Automatic saving of Project files',
                      })

main = [CVar('chdir_on_fileopen', True, 'bool', desc='whether to change working directory when opening a file'),
        CVar('workdir', get_homedir(), 'path', desc='starting working directory'),
        CVar('use_last_workdir', True, 'bool',  desc='whehter to use the working directory of the last session\nor always start in workdir'),
        ]

autosave = [CVar('savetime', 900, 'int', min=1, step=30, desc='time (in sec) between auto-saving Project files'),
            CVar('nhistory', 3, 'int', min=0, desc='number of auto-saved Project files to keep'),
            CVar('fileroot', 'session_autosave', 'string', desc='filename prefix for auto-saved Project files')]

pin = [CVar('style', 'pin first', 'choice', choices=['pin first', 'plot first'],
           desc='whether to click on pin first, then plot or plot first, then pin'),
       CVar('min_time', 2.0, 'float', min=0, max=60,
           desc='minimum time (seconds) between clicking on the pin and reporting a value,\nallowing multiple clicks on the plot in that time'),
       CVar('max_time', 15.0, 'float', min=1, max=300,
           desc='maximum time (seconds) after clicking on the pin to click on plot.\nWill report last saved value')]

plot = [CVar('theme', 'light', 'choice', choices=list(wxmplot.config.Themes.keys()),
            desc='plotting theme for colors and "look and feel"'),
        CVar('height', 550, 'int', min=100, desc='height of main plot window (in pixels)'),
        CVar('width', 600, 'int', min=100, desc='width of main plot window (in pixels)'),
        CVar('linewidth', 3.0, 'float', min=0, step=0.5, desc='line width for each trace (in pixels)'),
        CVar('markersize', 4.0, 'float', min=0, step=0.5, desc='size of plot markers (in pixels)'),
        CVar('show_grid', True, 'bool', desc='whether to show grid lines'),
        CVar('show_fullbox', True, 'bool', desc='whether to show a full box around plot,\nor only left and bottom axes'),
        ]


exafs = [CVar('rbkg', 1.0, 'float', min=0, step=0.1, max=10, desc='R value separating background from EXAFS signal'),
         CVar('bkg_kmin', 0.0, 'float', min=0, step=0.1, max=10, desc='k min for background subtraction'),
         CVar('bkg_kmax', -1, 'float', min=-1, step=0.1, desc='k max for background subtraction (use -1 for "auto")'),
         CVar('bkg_kweight', 1, 'float', min=0, step=1, max=10, desc='k weight for background subtraction'),
         CVar('bkg_clamplo', 1, 'float', min=0, step=5, desc='low-k clamp for background subtraction'),
         CVar('bkg_clamphi', 20, 'float', min=0, step=5, desc='high-k clamp for background subtraction'),
         CVar('fft_kmin',  2.0, 'float', min=0, step=0.1, max=50, desc='k min for EXAFS Fourier transform'),
         CVar('fft_kmax',  -1, 'float', min=-1, step=0.1, desc='k max for EXAFS Fourier transform (use -1 for "auto")'),
         CVar('fft_kweight', 2, 'float', min=0, step=1, max=10, desc='k weight for EXAFS Fourier transform'),
         CVar('fft_dk',      4, 'float', min=0, step=0.1, desc='window parameter for k->R EXAFS Fourier transform'),
         CVar('fft_kwindow', 'Kaiser-Bessel', 'choice', choices=FT_WINDOWS, desc='window type for k->R EXAFS Fourier transform'),
         CVar('fft_rmin',  -1, 'float', min=-1, step=0.1, max=50, desc='R min for EXAFS Back Fourier transform\n(use -1 for "auto")'),
         CVar('fft_rmax',  5.0, 'float', min=0, step=0.1, desc='k max for EXAFS Back Fourier transform'),
         CVar('fft_dr',    0.25, 'float', min=0, step=0.05, desc='window parameter for EXAFS Back Fourier transform'),
         CVar('fft_rwindow', 'Hanning', 'choice', choices=FT_WINDOWS, desc='window type for EXAFS Back Fourier transform'),
         CVar('fft_rmaxout',  12.0, 'float', min=0, step=0.5, desc='maximum output R value for EXAFS Fourier transform'),
         CVar('plot_rmax',     8.0, 'float', min=0, step=0.5, desc='maximum R value for EXAFS chi(R) plots')]


feffit  = [CVar('kwstring', '2', 'choice', choices=list(Feffit_KWChoices.keys()),
                desc='k weight to use for Feff fitting'),
           CVar('fitspace', 'R', 'choice', choices=list(Feffit_SpaceChoices.keys()),
                desc='Fourier space to use for Feff fitting'),
           CVar('fit_plot', 'R space only', 'choice', choices=list(Feffit_PlotChoices.keys()),
                desc='How to plot results for Feff fitting'),
           CVar('plot_paths', True, 'bool',   desc='Whether to plot individual paths in results for Feff fitting')]


lincombo = [CVar('all_combos', True, 'bool', desc='whether to fit all combinations'),
            CVar('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
            CVar('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
            CVar('sum_to_one', False, 'bool',  desc='whether components high-energy fit range, relative to E0'),
            CVar('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
                 desc='Array to use for Linear Combinations'),
            CVar('vary_e0',  False, 'bool', desc='whether to vary E0 in the fit'),
            CVar('show_e0',  False, 'bool', desc='whether to show E0 after fit'),
            CVar('show_fitrange',  True, 'bool', desc='whether to show energy range after fit')]

pca = [CVar('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
       CVar('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
       CVar('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
            desc='Array to use for Linear Combinations'),
       CVar('weight_min',  -1, 'float', min=-1, step=0.0001, desc='minimum component weight to use \n(use -1 for "auto")'),
       CVar('max_components',  20, 'int', min=0, desc='maximum number of components use')
       ]


prepeaks = [CVar('elo_rel', -20, 'float',  step=0.5, desc='low-energy fit range, relative to E0'),
           CVar('ehi_rel',   0, 'float',  step=0.5, desc='high-energy fit range, relative to E0'),
           CVar('eblo_rel', -8, 'float',  step=0.5, desc='low-energy of "baseline skip" range, relative to E0'),
           CVar('ebhi_rel', -3, 'float',  step=0.5, desc='high-energy of "baseline skip" range, relative to E0'),
           CVar('fitspace', 'Normalized μ(E)', 'choice', choices=list(PrePeak_ArrayChoices.keys()),
                desc='Array to use for Pre-edge peak fitting')]

regression = [CVar('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
              CVar('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
              CVar('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
                   desc='Array to use for Linear Regression'),
              CVar('variable',  'valence', 'string',  desc='name of variable to use for regression'),
              CVar('method',  'LassoLars', 'choice', choices=Regress_Choices,
                   desc='which Regression method to use'),
              CVar('alpha',  -1, 'float', min=0, step=0.01,
                   desc='alpha regularization parameter for LassoLars (use -1 for "auto")'),
              CVar('cv_folds',  -1, 'int', min=-1,
                   desc='number of Cross-Validation folds to use (set to -1 for "auto")'),
              CVar('cv_repeats',  -1, 'int', min=-1,
                   desc='number of Cross-Validation repeats to do (set to -1 for "auto")'),
              CVar('fit_intercept',  True, 'bool', desc='whether to fit the intercept with LassoLars'),
              CVar('auto_scale_pls',  True, 'bool', desc='whether to scale data with Partial-Least-Squares')
       ]

xasnorm = [CVar('auto_e0',  True, 'bool', desc='whether to automatically set E0'),
           CVar('auto_step',  True, 'bool', desc='whether to automatically set edge step'),
           CVar('show_e0',  True, 'bool', desc='whether to show E0'),
           CVar('energy_shift',  0., 'float', desc='value of Energy shift from original data'),
           CVar('auto_energy_shift',  True, 'bool', desc='when changing energy_shift for a Group, also shift \nall other Groups sharing that reference'),
           CVar('edge',      'K', 'choice',  choices=EDGES, desc='symbol of absorption edge'),
           CVar('nnorm',     'auto', 'choice', choices=list(NNORM_CHOICES.keys()),
                desc='type of polynomial for normalization'),
           CVar('norm_method',  'polynomial', 'choice', choices=NORM_METHODS,  desc='normalization method'),
           CVar('pre1', -200, 'float',  step=5, desc='low-energy fit range for pre-edge line,\nrelative to E0'),
           CVar('pre2',  -30, 'float',  step=5, desc='high-energy fit range for pre-edge line,\nrelative to E0'),
           CVar('norm1', 200, 'float',  step=5, desc='low-energy fit range for normalization curve,\nrelative to E0'),
           CVar('norm2',  -1, 'float',  step=5, desc='high-energy fit range for normalization curve,\nelative to E0 (set to -1 for "auto")'),
           CVar('nvict',   0, 'int',     min=0, max=3,  desc='Victoreen order for pre-edge fitting\n(Energy^(-nvict))'),
           CVar('scale',  1.0, 'float', step=0.1, desc='scale to use to "normalize" non-XAS data'),
           ]


XASCONF = {}
FULLCONF= {}

_locals = locals()

for section in ('main', 'autosave', 'pin', 'plot', 'xasnorm', 'exafs',
                'feffit', 'prepeaks', 'lincombo', 'pca', 'regression'):
    sname = section
    XASCONF[sname] = {}
    FULLCONF[sname] = {}
    for v in _locals[section]:
        XASCONF[sname][v.name] = v.value
        FULLCONF[sname][v.name] = v

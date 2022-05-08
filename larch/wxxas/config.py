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
Regress_Choices = ['Partial Least Squares', 'Lasso', 'LassoLars']


NNORM_CHOICES = {'auto':None,  'constant':0, 'linear':1, 'quadratic':2, 'cubic':3}
NORM_METHODS = ('polynomial', 'mback')

Feffit_KWChoices = {'1': '1', '2': '2', '3': '3',
                    '2 and 3': '[2, 3]',
                    '1, 2, and 3': '[2, 1, 3]'}

Feffit_SpaceChoices = {'R space':'r', 'k space':'k', 'wavelet': 'w'}
Feffit_PlotChoices = {'K and R space': 'k+r', 'R space only': 'r'}


Valid_DataTypes = ('string', 'float', 'int', 'bool', 'choice', 'path')

class Var:
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

###
### sections

_main = [Var('chdir_on_fileopen', True, 'bool', desc='whether to change directory when opening a file'),
         Var('workdir', get_homedir(), 'path', desc='staring working directory')]

autosave = [Var('savetime', 900, 'int', min=1, step=30, desc='time (in sec) between auto-saving Project files'),
            Var('nhistory', 3, 'int', min=0, desc='number of auto-saved Project files to keep'),
            Var('fileroot', 'session_autosave', 'string', desc='filename prefix for auto-saved Project files')]

pin = [Var('style', 'pin first', 'choice', choices=['pin first', 'plot first'],
           desc='whether to click on pin first, then plot or plot first, then pin'),
       Var('min_time', 2.0, 'float', min=0, max=60,
           desc='minimum time (seconds) between clicking on the pin and reporting a value, allowing multiple clicks on the plot in that time'),
       Var('max_time', 15.0, 'float', min=1, max=300,
           desc='maximum time (seconds) after clicking on the pin to click on plot - will report last saved value')]

plot = [Var('theme', 'light', 'choice', choices=list(wxmplot.config.Themes.keys()),
            desc='plotting theme for colors and "look and feel"'),
        Var('height', 550, 'int', min=100, desc='height of main plot window (in pixels)'),
        Var('width', 600, 'int', min=100, desc='width of main plot window (in pixels)'),
        Var('linewidth', 2.5, 'float', min=0, step=0.5, desc='width of main plot window (in pixels)'),
        Var('show_grid', True, 'bool', desc='whether to show grid lines'),
        Var('show_fullbox', True, 'bool', desc='whether to show a full box around plot, or only left and bottom axes'),
        ]


exafs = [Var('rbkg', 1.0, 'float', min=0, step=0.1, max=10, desc='R value separating background from EXAFS signal'),
         Var('bkg_kmin', 0.0, 'float', min=0, step=0.1, max=10, desc='k min for background subtraction'),
         Var('bkg_kmax', -1, 'float', min=-1, step=0.1, desc='k max for background subtraction (use -1 for "auto")'),
         Var('bkg_kweight', 1, 'float', min=0, step=1, max=10, desc='k weight for background subtraction'),
         Var('bkg_clamplo', 1, 'float', min=0, step=5, desc='low-k clamp for background subtraction'),
         Var('bkg_clamphi', 1, 'float', min=0, step=5, desc='high-k clamp for background subtraction'),
         Var('fft_kmin',  2.0, 'float', min=0, step=0.1, max=50, desc='k min for EXAFS Fourier transform'),
         Var('fft_kmax',  -1, 'float', min=-1, step=0.1, desc='k max for EXAFS Fourier transform (use -1 for "auto")'),
         Var('fft_kweight', 2, 'float', min=0, step=1, max=10, desc='k weight for EXAFS Fourier transform'),
         Var('fft_dk',      4, 'float', min=0, step=0.1, desc='window parameter for k->R EXAFS Fourier transform'),
         Var('fft_kwindow', 'Kaiser-Bessel', 'choice', choices=FT_WINDOWS, desc='window type for k->R EXAFS Fourier transform'),
         Var('fft_rmin',  -1, 'float', min=-1, step=0.1, max=50, desc='R min for EXAFS Back Fourier transform (use -1 for "auto")'),
         Var('fft_rmax',  5.0, 'float', min=0, step=0.1, desc='k max for EXAFS Back Fourier transform'),
         Var('fft_dr',    0.25, 'float', min=0, step=0.05, desc='window parameter for EXAFS Back Fourier transform'),
         Var('fft_rwindow', 'Hanning', 'choice', choices=FT_WINDOWS, desc='window type for EXAFS Back Fourier transform'),
         Var('fft_rmaxout',  12.0, 'float', min=0, step=0.1, desc='maximum output R value for EXAFS Fourier transform'),
         Var('plot_rmax',     7.0, 'float', min=0, step=0.1, desc='maximum R value for EXAFS chi(R) plots')]


feffit  = [Var('kwstring', '2', 'choice', choices=list(Feffit_KWChoices.keys()),
               desc='k weight to use for Feff fitting'),
           Var('fitspace', 'R', 'choice', choices=list(Feffit_SpaceChoices.keys()),
               desc='Fourier space to use for Feff fitting'),
           Var('fit_plot', 'R space only', 'choice', choices=list(Feffit_PlotChoices.keys()),
               desc='How to plot results for Feff fitting'),
           Var('plot_paths', True, 'bool',   desc='Whether to plot individual paths in results for Feff fitting')]


lincombo = [Var('all_combos', True, 'bool', desc='whether to fit all combinations'),
            Var('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
            Var('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
            Var('sum_to_one', False, 'bool',  desc='whether components high-energy fit range, relative to E0'),
            Var('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
                desc='Array to use for Linear Combinations'),
            Var('vary_e0',  False, 'bool', desc='whether to vary E0 in the fit'),
            Var('show_e0',  False, 'bool', desc='whether to show E0 after fit'),
            Var('show_fitrange',  True, 'bool', desc='whether to show energy range after fit')]

pca = [Var('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
       Var('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
       Var('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
           desc='Array to use for Linear Combinations'),
       Var('weight_min',  -1, 'float', min=-1, step=0.0001, desc='minimum component weight to use (use -1 for "auto")'),
       Var('max_components',  20, 'int', min=0, desc='maximum number of components use')
       ]


prepeaks = [Var('elo_rel', -20, 'float',  step=0.5, desc='low-energy fit range, relative to E0'),
           Var('ehi_rel',   0, 'float',  step=0.5, desc='high-energy fit range, relative to E0'),
           Var('eblo_rel', -8, 'float',  step=0.5, desc='low-energy of "baseline skip" range, relative to E0'),
           Var('ebhi_rel', -3, 'float',  step=0.5, desc='high-energy of "baseline skip" range, relative to E0'),
           Var('fitspace', 'Normalized μ(E)', 'choice', choices=list(PrePeak_ArrayChoices.keys()),
               desc='Array to use for Pre-edge peak fitting')]

regression = [Var('elo_rel', -40, 'float',  desc='low-energy fit range, relative to E0'),
              Var('ehi_rel', 100, 'float',  desc='high-energy fit range, relative to E0'),
              Var('fitspace', 'Normalized μ(E)', 'choice', choices=list(Linear_ArrayChoices.keys()),
                  desc='Array to use for Linear Regression'),
              Var('variable',  'valence', 'string',  desc='name of variable to use for regression'),
              Var('method',  'LassoLars', 'choice', choices=Regress_Choices,
                  desc='which Regression method to use'),
              Var('alpha',  -1, 'float', min=0, step=0.01,
                  desc='alpha regularization parameter for LassoLars (use -1 for "auto")'),
              Var('cv_folds',  -1, 'int', min=-1,
                  desc='number of Cross-Validation folds to use (set to -1 for "auto")'),
              Var('cv_repeats',  -1, 'int', min=-1,
                  desc='number of Cross-Validation repeats to do (set to -1 for "auto")'),
              Var('fit_intercept',  True, 'bool', desc='whether to fit the intercept with LassoLars'),
              Var('scale',  True, 'bool', desc='whether to scale data with Partial-Least-Squares')
       ]

xasnorm = [Var('auto_e0',  True, 'bool', desc='whether to automatically set E0'),
           Var('auto_step',  True, 'bool', desc='whether to automatically set edge step'),
           Var('e0',         0., 'float', desc='value of E0 (energy origin)'),
           Var('show_e0',  True, 'bool', desc='whether to show E0'),
           Var('energy_shift',  0., 'float', desc='value of Energy shift from original data'),
           Var('edge_step',  0., 'float', desc='value of edge step'),
           Var('edge',      'K', 'choice',  choices=EDGES, desc='symbol of absorption edge'),
           Var('nnorm',     'auto', 'choice', choices=list(NNORM_CHOICES.keys()),
               desc='type of polynomial for normalization'),
           Var('norm_method',  'polynomial', 'choice', choices=NORM_METHODS,  desc='normalization method'),
           Var('pre1', -200, 'float',  step=5, desc='low-energy fit range for pre-edge line, relative to E0'),
           Var('pre2',  -30, 'float',  step=5, desc='high-energy fit range for pre-edge line, relative to E0'),
           Var('norm1', 200, 'float',  step=5, desc='low-energy fit range for normalization curve, relative to E0'),
           Var('norm2',  -1, 'float',  step=5, desc='high-energy fit range for normalization curve, relative to E0 (set to -1 for "auto")'),
           Var('nvict',   0, 'int',     min=0, max=3,  desc='Victoreen order for pre-edge fitting (Energy^(-nvict))'),
           Var('scale',  1.0, 'float', step=0.1, desc='scale to use to "normalize" non-XAS data'),
           ]


XASCONF = {}
FULLCONF= {}

for v in _main:
    XASCONF[v.name] = v.value
    FULLCONF[v.name] = v

_locals = locals()

for section in ('autosave', 'pin', 'plot', 'xasnorm', 'exafs', 'feffit',
                'prepeaks', 'lincombo', 'pca', 'regression'):
    sname = section + '_config'
    XASCONF[sname] = {}
    FULLCONF[sname] = {}
    for v in _locals[section]:
        XASCONF[sname][v.name] = v.value
        FULLCONF[sname][v.name] = v

##
##         XASCONF[section][v.name] = v.value

OLDXASCONF = { # default configurations
    'autosave_config': {'savetime': 900, 'nhistory': 3,
                        'fileroot': 'session_autosave'},

    'chdir_on_fileopen': True,

    'exafs_config': {'bkg_clamphi': 1, 'bkg_clamplo': 0, 'bkg_kmax': None,
                     'bkg_kmin': 0, 'bkg_kweight': 2, 'e0': -1.0,
                     'fft_dk': 4, 'fft_dr': 0.25, 'fft_kmax': None,
                     'fft_kmin': 2.5, 'fft_kweight': 2,
                     'fft_kwindow': 'Kaiser-Bessel',
                     'fft_rmax': 6, 'fft_rmin': 1, 'fft_rwindow':
                     'Hanning', 'rbkg': 1},

    'feffit_config': {'dk': 4, 'fitspace': 'r', 'kmax': None, 'kmin': 2,
                      'kwindow': 'Kaiser-Bessel', 'kwstring': '2',
                      'rmax': 4, 'rmin': 1},

    'lincombo_config': {'all_combos': True, 'ehi': 99999, 'ehi_rel': 110,
                        'elo': -99999, 'elo_rel': -40,
                        'fitspace': 'Normalized μ(E)', 'show_e0': False,
                        'show_fitrange': True, 'sum_to_one': False,
                        'vary_e0': False},

    'pca_config': {'fitspace': 'Normalized μ(E)',
                   'max_components': 20, 'weight_auto': True,
                   'weight_min': 0.001, 'xmax': 99999, 'xmin': -99999},

    'pin_config': {'min_time': 2.0, 'style': 'pin_first', 'timeout': 15.0},

    'plot_config': {'height': 550, 'theme': 'light', 'width': 600},

    'prepeaks_config': {'e': None, 'ehi': -5, 'elo': -10, 'emax': 0,
                        'emin': -40, 'yarray': 'norm'},

    'regression_config': {'alpha': 0.01, 'cv_folds': None,
                          'cv_repeats': 3, 'fit_intercept': True,
                          'fitspace': 'Normalized μ(E)', 'scale': True,
                          'use_lars': True, 'varname': 'valence',
                          'xmax': 99999, 'xmin': -99999},

    'workdir': '/Users/Newville/Codes/xraylarch',

    'xasnorm_config': {'auto_e0': True, 'auto_step': True,
                       'e0': 0, 'edge': 'K', 'edge_step': None,
                       'energy_ref': None, 'energy_shift': 0,
                       'nnorm': None, 'norm1': None, 'norm2': None,
                       'norm_method': 'polynomial', 'nvict': 0,
                       'pre1': None, 'pre2': None, 'scale': 1, 'show_e0': True},
    }

__DOC__ = """Mathematical functions for Larch"""

from .utils import (linregress, polyfit, realimag, as_ndarray,
                    complex_phase, deriv, interp, interp1d,
                    remove_dups, remove_nans2, index_of,
                    index_nearest, savitzky_golay, smooth, boxcar)

from .lineshapes import (gaussian, lorentzian, voigt, pvoigt, hypermet,
                         pearson7, lognormal, gammaln,
                         breit_wigner, damped_oscillator,
                         expgaussian, donaich, skewed_voigt,
                         students_t, logistic, erf, erfc, wofz)


from .fitpeak import fit_peak
from .convolution1D import glinbroad
from .lincombo_fitting import lincombo_fit, lincombo_fitall, groups2matrix
from .pca import pca_train, pca_fit, nmf_train
from .learn_regress import pls_train, pls_predict, lasso_train, lasso_predict
from .gridxyz import gridxyz
from .spline import spline_rep, spline_eval
from . import transformations as trans

from .tomography import (tomo_reconstruction, reshape_sinogram,
                         trim_sinogram, TOMOPY_ALG, TOMOPY_FILT)

_larch_builtins = {'_math': dict(linregress=linregress, polyfit=polyfit,
                                 realimag=realimag, as_ndarray=as_ndarray,
                                 complex_phase=complex_phase, deriv=deriv,
                                 interp=interp, interp1d=interp1d,
                                 remove_dups=remove_dups,
                                 remove_nans2=remove_nans2,
                                 index_of=index_of,
                                 index_nearest=index_nearest,
                                 savitzky_golay=savitzky_golay,
                                 smooth=smooth, boxcar=boxcar,
                                 glinbroad=glinbroad, gridxyz=gridxyz,
                                 pca_train=pca_train, pca_fit=pca_fit,
                                 nmf_train=nmf_train,
                                 pls_train=pls_train,
                                 pls_predict=pls_predict,
                                 lasso_train=lasso_train,
                                 lasso_predict=lasso_predict,
                                 groups2matrix=groups2matrix,
                                 fit_peak=fit_peak,
                                 lincombo_fit=lincombo_fit,
                                 lincombo_fitall=lincombo_fitall,
                                 spline_rep=spline_rep,
                                 spline_eval=spline_eval,
                                 gaussian=gaussian,
                                 lorentzian=lorentzian, voigt=voigt,
                                 pvoigt=pvoigt, hypermet=hypermet,
                                 pearson7=pearson7, lognormal=lognormal,
                                 gammaln=gammaln,
                                 breit_wigner=breit_wigner,
                                 damped_oscillator=damped_oscillator,
                                 expgaussian=expgaussian, donaich=donaich,
                                 skewed_voigt=skewed_voigt,
                                 students_t=students_t, logistic=logistic,
                                 erf=erf, erfc=erfc, wofz=wofz),
                   '_math.transforms': {# 'doc': trans.__doc__,
                                        'identity_matrix': trans.identity_matrix,
                                        'translation_matrix': trans.translation_matrix,
                                        'translation_from_matrix': trans.translation_from_matrix,
                                        'reflection_matrix': trans.reflection_matrix,
                                        'reflection_from_matrix': trans.reflection_from_matrix,
                                        'rotation_matrix': trans.rotation_matrix,
                                        'rotation_from_matrix': trans.rotation_from_matrix,
                                        'scale_matrix': trans.scale_matrix,
                                        'scale_from_matrix': trans.scale_from_matrix,
                                        'projection_matrix': trans.projection_matrix,
                                        'projection_from_matrix': trans.projection_from_matrix,
                                        'clip_matrix': trans.clip_matrix,
                                        'shear_matrix': trans.shear_matrix,
                                        'shear_from_matrix': trans.shear_from_matrix,
                                        'decompose_matrix': trans.decompose_matrix,
                                        'compose_matrix': trans.compose_matrix,
                                        'orthogonalization_matrix': trans.orthogonalization_matrix,
                                        'affine_matrix_from_points': trans.affine_matrix_from_points,
                                        'superimposition_matrix': trans.superimposition_matrix,
                                        'euler_matrix': trans.euler_matrix,
                                        'euler_from_matrix': trans.euler_from_matrix,
                                        'euler_from_quaternion': trans.euler_from_quaternion,
                                        'quaternion_from_euler': trans.quaternion_from_euler,
                                        'quaternion_about_axis': trans.quaternion_about_axis,
                                        'quaternion_matrix': trans.quaternion_matrix,
                                        'quaternion_from_matrix': trans.quaternion_from_matrix,
                                        'quaternion_multiply': trans.quaternion_multiply,
                                        'quaternion_conjugate': trans.quaternion_conjugate,
                                        'quaternion_inverse': trans.quaternion_inverse,
                                        'quaternion_real': trans.quaternion_real,
                                        'quaternion_imag': trans.quaternion_imag,
                                        'quaternion_slerp': trans.quaternion_slerp,
                                        'vector_norm': trans.vector_norm,
                                        'unit_vector': trans.unit_vector,
                                        'vector_product': trans.vector_product,
                                        'angle_between_vectors': trans.angle_between_vectors,
                                        'inverse_matrix': trans.inverse_matrix}}

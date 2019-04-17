"""
ini doc
"""
__DOC__ = '''
Functions for Input/Output, especially reading specific types
of scientific data files.
'''
from .fileutils import (increment_filename, new_filename, new_dirname,
                        fix_filename, fix_varname, pathOf, unixpath,
                        winpath, nativepath, strip_quotes, get_timestamp,
                        asciikeys)

from .columnfile import (read_ascii, write_ascii, write_group, set_array_labels,
                         guess_filereader)
from .xdi import read_xdi, XDIFile, XDIFileException
from .mda import read_mda
from .hdf5group import h5file, h5group, netcdf_file, netcdf_group

from .xsp3_hdf5 import read_xsp3_hdf5
from .xrf_netcdf import read_xrf_netcdf
from .xrd_netcdf import read_xrd_netcdf
from .xrd_hdf5 import read_xrd_hdf5

from .xdi import read_xdi

from .gse_escan import gsescan_group, gsescan_deadtime_correct
from .gse_xdiscan import read_gsexdi, gsexdi_deadtime_correct, is_GSEXDI
from .gse_mcafile import gsemca_group, GSEMCA_File
from .save_restore import save, restore
from .tifffile import TIFFfile
from .athena_project import (is_athena_project, read_athena, AthenaProject, create_athena,
                             extract_athenagroup, make_hashkey)
from .csvfiles import groups2csv, read_csv
from .export_modelresult import export_modelresult
from .mergegroups import merge_groups
from .specfile_reader import (HAS_SPECFILE, spec_getscan2group,
                              spec_getmap2group, spec_getmrg2group,
                              str2rng_larch)
from .stepscan_file import read_stepscan
from . import tifffile
def read_tiff(fname, _larch=None, *args, **kws):
    """read image data from a TIFF file as an array"""
    return tifffile.imread(fname, *args, **kws)


__exports__ = dict(increment_filename=increment_filename,
                   new_filename=new_filename,
                   new_dirname=new_dirname,
                   fix_filename=fix_filename,
                   fix_varname=fix_varname,
                   pathOf=pathOf,
                   unixpath=unixpath,
                   winpath=winpath,
                   nativepath=nativepath,
                   strip_quotes=strip_quotes,
                   get_timestamp=get_timestamp,
                   asciikeys=asciikeys,
                   read_ascii=read_ascii,
                   set_array_labels=set_array_labels,
                   guess_filereader=guess_filereader,
                   write_ascii=write_ascii,
                   write_group=write_group,
                   groups2csv=groups2csv,
                   read_csv=read_csv,
                   read_xdi=read_xdi,
                   read_athena=read_athena,
                   create_athena=create_athena,
                   extract_athenagroup=extract_athenagroup,
                   export_modelresult=export_modelresult,
                   read_gsescan=gsescan_group,
                   gsescan_dtcorrect=gsescan_deadtime_correct,
                   read_gsemca=gsemca_group,
                   read_gsexdi=read_gsexdi,
                   gsexdi_deadtime_correct=gsexdi_deadtime_correct,
                   read_mda=read_mda,
                   read_stepscan=read_stepscan,
                   read_tiff=read_tiff,
                   merge_groups=merge_groups,
                   save=save,
                   restore=restore,
                   read_xrd_hdf5=read_xrd_hdf5,
                   read_xrd_netcdf=read_xrd_netcdf,
                   read_xrf_netcdf=read_xrf_netcdf,
                   read_xsp3_hdf5=read_xsp3_hdf5,
                   h5group=h5group,
                   h5file=h5file,
                   netcdf_file=netcdf_file,
                   netcdf_group=netcdf_group,
                   )




if HAS_SPECFILE:
    __exports__.update(dict(read_specfile_scan=spec_getscan2group,
                            read_specfile_map=spec_getmap2group,
                            read_specfile_mrg=spec_getmrg2group,
                            str2rng=str2rng_larch))

_larch_builtins = {'_io':__exports__}

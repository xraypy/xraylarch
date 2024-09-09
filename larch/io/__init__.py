"""
ini doc
"""
__DOC__ = '''
Functions for Input/Output, especially reading specific types
of scientific data files.
'''

from .fileutils import (increment_filename, new_filename, new_dirname)


from .columnfile import (read_ascii, write_ascii, write_group, set_array_labels,
                         guess_filereader, look_for_nans, read_fdmnes, sum_fluor_channels)
from .xdi import read_xdi, XDIFile, XDIFileException
from .hdf5group import h5file, h5group, netcdf_file, netcdf_group
from .xsp3_hdf5 import read_xsp3_hdf5
from .xrf_netcdf import read_xrf_netcdf
from .xrd_netcdf import read_xrd_netcdf
from .xrd_hdf5 import read_xrd_hdf5
from .xdi import read_xdi
from .gse_escan import gsescan_group, gsescan_deadtime_correct
from .gse_xdiscan import read_gsexdi, gsexdi_deadtime_correct, is_GSEXDI
from .gse_mcafile import gsemca_group, GSEMCA_File

from .save_restore import (save_session, load_session, read_session,
                           clear_session, is_larch_session_file,
                           save_groups, read_groups)

from . import tifffile
from .tifffile import TIFFfile
from .athena_project import (is_athena_project, read_athena, AthenaProject,
                             create_athena, extract_athenagroup,
                             make_hashkey)

from .xafs_beamlines import guess_beamline
from .csvfiles import groups2csv, read_csv
from .export_modelresult import export_modelresult
from .mergegroups import merge_groups

from .specfile_reader import (str2rng_larch, read_specfile, open_specfile,
                              is_specfile)
from .stepscan_file import read_stepscan

from .nexus_xas import NXxasFile
from .xas_data_source import open_xas_source, read_xas_source

def read_tiff(fname, *args, **kws):
    """read image data from a TIFF file as an array"""
    return tifffile.imread(fname, *args, **kws)


__exports__ = dict(increment_filename=increment_filename,
                   new_filename=new_filename,
                   new_dirname=new_dirname,
                   read_ascii=read_ascii,
                   look_for_nans=look_for_nans,
                   set_array_labels=set_array_labels,
                   guess_filereader=guess_filereader,
                   write_ascii=write_ascii,
                   write_group=write_group,
                   groups2csv=groups2csv,
                   read_csv=read_csv,
                   read_xdi=read_xdi,
                   sum_fluor_channels=sum_fluor_channels,
                   read_athena=read_athena,
                   create_athena=create_athena,
                   extract_athenagroup=extract_athenagroup,
                   export_modelresult=export_modelresult,
                   read_gsescan=gsescan_group,
                   gsescan_dtcorrect=gsescan_deadtime_correct,
                   read_gsemca=gsemca_group,
                   read_gsexdi=read_gsexdi,
                   gsexdi_deadtime_correct=gsexdi_deadtime_correct,
                   read_stepscan=read_stepscan,
                   read_tiff=read_tiff,
                   merge_groups=merge_groups,
                   save_session=save_session,
                   clear_session=clear_session,
                   load_session=load_session,
                   read_session=read_session,
                   save_groups=save_groups,
                   read_groups=read_groups,
                   read_xrd_hdf5=read_xrd_hdf5,
                   read_xrd_netcdf=read_xrd_netcdf,
                   read_xrf_netcdf=read_xrf_netcdf,
                   read_xsp3_hdf5=read_xsp3_hdf5,
                   h5group=h5group,
                   h5file=h5file,
                   netcdf_file=netcdf_file,
                   netcdf_group=netcdf_group,
                   str2rng=str2rng_larch,
                   read_specfile=read_specfile,
                   specfile=open_specfile,
                   read_fdmnes=read_fdmnes,
                   open_xas_source=open_xas_source,
                   read_xas_source=read_xas_source
                   )

_larch_builtins = {'_io':__exports__}

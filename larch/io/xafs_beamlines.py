#!/usr/bin/env python
"""
classes for handling XAFS data in plaintext column files for various beamlines.


Basically, a class for XAFS Beamline data. This defines
  a) how to name the arrays for columns in the data file
  b) which column is most likely to hold the energy (or energy-definig) array
  c) what the energy units are most likely to be.

Specific beamline data should define a class that derives from GenericBeamlineData
and has the following attributes/methods:


  energy_column : int index for default energy column

  energy_units : str ('eV', 'keV', 'deg') for default expected energy units

  beamline_matches(): method to decide whether data may be from the beamline
     should give more false positives than false negatives.

  get_array_labels(): method to guess array labels.

The XXX__BeamlineData class will be given *only* the headerlines (a list of lines)
from the text file.

By default, that header will defined all the text before the data table.

"""

import numpy as np
from .fileutils import fix_varname

def guess_beamline(header=None):
    """
    guess beamline data class used to parse headers from header lines
    """
    if header is not None and len(header) > 1:
        line1 = header[0].lower()
        full = '\n'.join(header).lower()

        if line1.startswith('#'):
            line1 = line1.replace('#', '')

        if 'xdi/1' in line1 and 'epics stepscan' in line1:
            return APSGSE_BeamlineData
        elif line1.startswith('; epics scan 1 dim'):
            return APSGSE_BeamlineData
        elif 'labview control panel' in line1:
            return APSXSD_BeamlineData
        elif 'mrcat_xafs' in line1:
            return APSMRCAT_BeamlineData
        elif line1.startswith('xdac'):
            return NSLSXDAC_BeamlineData
        elif 'ssrl' in line1 and 'exafs data collector' in line1:
            return SSRL_BeamlineData
        elif 'cls data acquisition' in line1:
            return CLSHXMA_BeamlineData
        elif 'kek-pf' in line1:
            return KEKPF_BeamlineData
        elif 'exafsscan' in full and 'exafs_region' in full:
            return APS12BM_BeamlineData
    return GenericBeamlineData


class GenericBeamlineData:
    """
    Generic beamline data file - use as last resort

    This parses the last header line for labels:
    First, it remove any leading '#', '#C', '#L', and 'C' as if
    collected by Spec or many other collection systems.

    Next, it removes bad characters ',#@%&' and quotes.
    Then, it splits on whitespace and fixes names to make
    sure they are valid variable names
    """
    energy_column = 1
    energy_units = 'eV'
    mono_dspace = -1
    name = 'generic'

    def __init__(self, headerlines=None):
        if headerlines is None:
            headerlines = []
        self.headerlines = list(headerlines)

    def beamline_matches(self):
        return len(self.headerlines) > 1

    def get_array_labels(self, ncolumns=None):
        if len(self.headerlines) < 2:
            return None

        lastline = self.headerlines[-1].strip()
        for cchars in ('#L', '#C', '#', 'C'):
            if lastline.startswith(cchars):
                lastline = lastline[len(cchars):]
        for badchar in ',#@%&"\'':
            lastline = lastline.replace(badchar, ' ')
        return self._set_labels(lastline.split(), ncolumns=ncolumns)

    def _set_labels(self, labels, ncolumns=None):
        """
        final parsing, cleaning, ensuring number of columns is satisfied
        """
        labels = [fix_varname(word.strip().lower()) for word in labels]
        for i, lab in enumerate(labels):
            if lab in labels[:i]:
                labels[i] = lab + '_col%d' % i

        if ncolumns is not None and len(labels) < ncolumns:
            for i in range(len(labels), ncolumns):
                labels.append('col%d' % (i+1))
        self.labels = labels
        return labels


class APSGSE_BeamlineData(GenericBeamlineData):
    """
    GSECARS EpicsScan data, APS 13ID, some NSLS-II XFM 4BM data
    """
    name = 'GSE EpicsScan'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0].lower()
        return (('xdi/1' in line1 and 'epics stepscan' in line1) or
                line1.startswith('; epics scan 1 dim'))


    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        line1 = self.headerlines[0].lower()
        oldstyle = line1.startswith('; epics scan 1 dim')

        labels = []
        if oldstyle:
            mode = 'search'
            for line in self.headerlines:
                line = line[1:].strip()
                if mode == 'found legend':
                    if len(line) < 2 or '-->' not in line:
                        mode = 'legend done'
                    else:
                        pref, suff = line.split('-->', 1)
                        pid, arg = pref.split('=')
                        arg = arg.replace('{', '').replace('}','')
                        labels.append(arg.strip())
                elif mode == 'search' and 'column labels:' in line:
                    mode = 'found legend'


        else:
            for line in self.headerlines:
                if line.startswith('#'):
                    line = line[1:].strip()
                else:
                    break
                if line.lower().startswith('column.') and '||' in line:
                    label, pvname = line.split('||', 1)
                    label, entry = label.split(':')
                    entry = entry.strip()
                    if ' ' in entry:
                        entry, units = entry.split(' ')
                        if 'energy' in entry.lower() and len(units) > 1:
                            self.energy_units = units
                    labels.append(entry)
        return self._set_labels(labels, ncolumns=ncolumns)


class APS12BM_BeamlineData(GenericBeamlineData):
    """
    APS sector 12BM data
    """
    name = 'APS 12BM'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        """ must see 'exafs_region' """
        match = False
        if len(self.headerlines) > 0:
            for line in self.headerlines:
                if not line.startswith('#'):
                    match = False
                    break
                if 'exafs_region' in line:
                    match = True
        return match

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        labelline = self.headerlines[-1].replace('#C', ' ').strip()
        words = labelline.split()

        labels = []
        for word in words:
            if '_' in word:
                pref, suff = word.split('_')
                isint = False
                try:
                    ipref = int(pref)
                    isint = True
                except ValueError:
                    pass
                if isint: labels.append(suff)
            elif len(labels) == 1:
                word = word.replace('(', '').replace(')', '')
                self.energy_units = word
        return self._set_labels(labels, ncolumns=ncolumns)


class APSMRCAT_BeamlineData(GenericBeamlineData):
    """
    APS sector 10ID or 10BM data
    """
    name = 'APS MRCAT'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0]
        return ('MRCAT_XAFS' in line1)

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        labels = []
        mode = 'search'
        for line in self.headerlines:
            if mode == 'found':
                labels = line.strip().split()
                break
            if mode == 'search' and '-------' in line:
                mode = 'found'

        return self._set_labels(labels, ncolumns=ncolumns)


class APSXSD_BeamlineData(GenericBeamlineData):
    """
    APS sector 20ID, 20BM, 9BM
    """
    name = 'APS XSD'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0]
        return ('LabVIEW Control Panel' in line1)

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        # here we try two different ways for "older" and "newer" 20BM/9BM fles
        labels = []
        mode = 'search'
        _tmplabels = {}
        lablines = []
        for line in self.headerlines:
            line = line[1:].strip()
            if mode == 'search' and 'is a readable list of column' in line:
                mode = 'found legend'
            elif mode == 'found legend':
                if len(line) < 2:
                    break
                # print("Label Line : ", line)
                if ')' in line:
                    if line.startswith('#'):
                        line = line[1:].strip()
                    if '*' in line:
                        lablines.extend(line.split('*'))
                    elif line.count(')') > 1:
                        words = line.split()
                        lablines.append('%s %s' % (words[0], words[1]))
                        if len(words) == 4:
                            lablines.append('%s %s' % (words[2], words[3]))
                    else:
                        lablines.append(line)

        if len(lablines) > 1:
            labels = ['']*len(lablines)
            for line in lablines:
                words = line.strip().split(' ', 1)
                if ')' in words[0]:
                    key = int(words[0].replace(')', ''))
                    labels[key-1] = words[1]

        # older version: no explicit legend, parse last header line, uses '*'
        if len(labels) == 0:
            labelline = self.headerlines[-1].replace('#', '')
            words = labelline.split('*')
            if len(words) > 1:
                lastword = words.pop()
                words.extend(lastword.split())
            labels = words

        return self._set_labels(labels, ncolumns=ncolumns)


class NSLSXDAC_BeamlineData(GenericBeamlineData):
    """
    NSLS (I) XDAC collected data
    """
    name = 'NSLS XDAC'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0].replace('#', '').strip()
        return line1.startswith('XDAC')

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        labels = []
        mode = 'search'
        for line in self.headerlines:
            if mode == 'found':
                labels = line.strip().split()
                break
            if mode == 'search' and '-------' in line:
                mode = 'found'

        return self._set_labels(labels, ncolumns=ncolumns)


class SSRL_BeamlineData(GenericBeamlineData):
    """
    SSRL EXAFS Data Collect beamline data
    """
    name = 'SSRL'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0]
        return ('ssrl' in line1.lower() and 'exafs data collector' in line1.lower())

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        labels = []
        mode = 'search'
        for line in self.headerlines:
            line = line.strip()
            if mode == 'found legend':
                if len(line) < 2:
                    mode = 'legend done'
                    break
                else:
                    labels.append(line)
                    if 'energy' in line.lower():
                        self.energy_column = len(labels)
            elif mode == 'search' and line == 'Data:':
                mode = 'found legend'

        return self._set_labels(labels, ncolumns=ncolumns)


class CLSHXMA_BeamlineData(GenericBeamlineData):
    """
    CLS HXMA beamline data
    """
    name = 'CLS HXMA'
    energy_column = 1

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0]
        return ('cls data acquisition' in line1.lower())

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        labels = []
        for line in self.headerlines:
            line = line.strip()
            if line.startswith('#(1)')  and '$(' in line:
                line = line.replace('#(1)', '')
                for bchar in '"#$()\t':
                    line = line.replace(bchar, ' ')
                labels = line.split()

        labels = [fix_varname(word.strip().lower()) for word in labels]
        for i, label in enumerate(labels):
            if 'energy' in label:
                self.energy_column = i+1
        return self._set_labels(labels, ncolumns=ncolumns)


class KEKPF_BeamlineData(GenericBeamlineData):
    """
    KEK-PF (Photon Factory Data), as from BL12C
    """
    name = 'KEK PF'
    energy_column = 2
    energy_units = 'deg'

    def __init__(self, headerlines=None):
        GenericBeamlineData.__init__(self, headerlines=headerlines)

    def beamline_matches(self):
        line1  = ''
        if len(self.headerlines) > 0:
            line1 = self.headerlines[0].replace('#', '').strip()
        return 'KEK-PF' in line1

    def get_array_labels(self, ncolumns=None):
        if not self.beamline_matches():
            raise ValueError('header is not from beamline %s' % self.name)

        for line in self.headerlines:
            line = line.lower().replace('#', ' ').strip()
            if 'mono :' in line:
                words = ['_'] + line.replace('=', ' ').split()
                for i, w in enumerate(words):
                    if i == 0: continue
                    if words[i-1] == 'd':
                        try:
                            self.mono_dspace = float(w)
                        except ValueError:
                            pass
        lastline = self.headerlines[-1]
        ncols = len(lastline.strip().split())
        if ncolumns is not None:
            ncols = max(ncols, ncolumns)

        labels= ['angle_drive', 'angle_read', 'time']
        return self._set_labels(labels, ncolumns=ncols)

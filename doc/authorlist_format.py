import re
import unicodedata
from collections import Counter

from pybtex.style.formatting.unsrt import Style as UnsrtStyle
from pybtex.style.labels import BaseLabelStyle
from pybtex.plugin import register_plugin

_alphanum_ = re.compile('[^A-Za-z0-9-]+', re.UNICODE)

def strip_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s)
                    if not unicodedata.combining(c)))

def lastname(p):
    s = strip_accents(''.join(p.prelast_names + p.last_names))
    return _alphanum_.sub('', s)

class AuthorsLabelStyle(BaseLabelStyle):
    def format_labels(self, sorted_entries):
        labels = [self.format_label(entry) for entry in sorted_entries]
        count = Counter(labels)
        counted = Counter()
        for label in labels:
            if count[label] == 1:
                yield label
            else:
                yield label + chr(ord('a') + counted[label])
                counted.update([label])

    def format_label(self, entry):
        # see alpha.bst calc.label
        org    = entry.type in ("proceedings", "manual")
        editor = entry.type in ("book", "inbook", "proceedings",
                                "inproceedings")
        author = entry.type not in ("proceedings")
        label = self.generate_label(entry, author=author,
                                    editor=editor, org=org)
        if "year" in entry.fields:
            label = "{:s} ({:s})".format(label, entry.fields["year"])
        return label

    def generate_label(self, entry, author=True, editor=True, org=True):
        result = entry.fields["key"] if "key" in entry.fields else entry.key
        if author and "author" in entry.persons:
            result = self.names2label(entry.persons["author"])
        elif editor and "editor" in entry.persons:
            result = self.names2label(entry.persons["editor"])
        elif org and "organization" in entry.fields:
            result = entry.fields["organization"]
            if result.startswith("The "):
                result = result[4:]
        return result

    def names2label(self, persons):
        numnames = len(persons)
        if numnames == 1:
            result = lastname(persons[0])
        elif numnames == 2:
            result = '{:s} and {:s}'.format(lastname(persons[0]),
                                            lastname(persons[1]))
        elif numnames == 3:
            result = '{:s}, {:s}, and {:s}'.format(lastname(persons[0]),
                                                   lastname(persons[1]),
                                                   lastname(persons[2]))
        else:
            result = '{:s} et al.'.format(lastname(persons[0]))
        return result

class AuthorListStyle(UnsrtStyle):
    default_label_style = AuthorsLabelStyle

register_plugin('pybtex.style.formatting', 'authorlist', AuthorListStyle)

"""
parses multilayer film structure as input, like Si/Cr/Pt for Cr/Pt on Si-substrate
sends lists for reflectivity calculation

# 9/24/2010 Yong Choi

adapted for Larch, M. Newville
"""

def letters_between(text, strl, strr):
    """finds letters in text between strl and strr
    returns list of tuples (string, pos of strl, and pos of strr)
    """
    mid = ''
    out = []
    left = None
    for ii, letter in enumerate(text):
        if letter == strl:
            left = ii
            # second to last letter
            if (left == len(text)-2) or (left == len(text)-3):
                mid = text[left+1:]
                out.append((mid, left, len(text)-1))
                left = None
        if left is not None and letter == strr:
            mid = text[left+1: ii]
            out.append((mid, left, ii))
            left = None
    return out

class FilmLayer:
    """single layer -- composition, density, thickness, roughness"""
    def __init__(self, composition='Si', density=1, thickness=1,
                 roughness=1, tag='film'):
        self.tag = tag
        self.composition = composition
        self.density = density         # g/cc
        self.relden = thickness        # relative density
        self.thickness = thickness     # layer thickness
        self.roughness = roughness     # layer roughness

class Film:
    """Multilayer Film"""
    def __init__(self, film_structure='Si/Cr(50)/Pt(200)'):
         self.film_structure = film_structure
         self.layer_sequence = film_structure
         self.layers = []

    def get_structure(self):
        # expand layer structure
        self.layer_sequence = self.expand_sequence(self.film_structure)
        for layer in self.layer_sequence.split('/'):
            tag='film'
            words = layer.split('(')
            material = words[0]
            if len(words)==1:
                tag, thickness = 'substrate', '100000.'
            else:
                tag, thickness = 'film', words[1][:-1]   # remove ')'
            self.layers.append(FilmLayer(composition=material,
                                            thickness=thickness, tag=tag))
        # add a vacuum layer on top
        self.layers.append(FilmLayer(composition='He', density=1e-10,
                                        thickness=0, tag='vacuum'))

    def reverse_structure(self):
        self.layers.reverse()

    def expand_sequence(self, sequence):
        fullname = sequence[:]
        repeats  = letters_between(fullname, '[', ']')
        factors  = letters_between(fullname, 'x', '/')
        for nn in range(len(repeats)):
            repeats = letters_between(fullname, '[', ']')
            factors = letters_between(fullname, 'x', '/')
            (text1, posL1, posR1) = repeats[0]
            (num2,  posL2, posR2) = factors[0]
            pre=fullname[:posL1]
            center=''
            for ix in range(0, int(num2)):
                center=center+text1+'/'
            post = fullname[posR2+1:]
            if post == '':
                center = center[:-1]
            fullname = pre+center+post
        return fullname

def test(structure):
    film=Film(structure)
    film.get_structure()
    print( '--> ', film.film_structure)
    for item in film.layers:
        print( item.composition, item.thickness, item.density,\
              item.roughness, item.tag)

def testall():
    test('Si/Ta(10)/[Pt(20)/Cr(30)]x3/Au(40)')
    test('Si/Nd(10)/[Pd(20)/Co(30)]x3/Ag(40)/[Pt(22)/Fe(33)]x2/Al(10)')
    test('Si/Nd(10)/[Pd(20)/Co(30)]x3/Ag(40)/[Pt(22)/Fe(33)]x10')
    test('Si/Cr(50)/[Pt(40)/Fe(20)]x10')

if __name__ == '__main__':
    testall()

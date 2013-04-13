# 9/24/2010
# takes film structure as input, like Si/Cr/Pt for Cr/Pt on Si-substrate
# sends lists for reflectivity calculation

def test_ChemName(chemical):
    Elem=[]; Ind=[]; Frac=[]; Pos=[]
    for (ii, letter) in enumerate(chemical):
        if letter.isalpha():
            if ii==(len(chemical)-1) and letter.upper():  # last capital letter
                Elem.append(letter)
                Pos.append(ii)
                break
            if letter.isupper(): # number of element = number of capital letter
                next=chemical[ii+1]  # next letter
                if next.isalpha() and next.islower():
                    Elem.append(chemical[ii:ii+2])
                    Pos.append(ii)
                if not next.isalpha() or (next.isalpha() and next.isupper()):
                    Elem.append(chemical[ii:ii+1])
                    Pos.append(ii)
    if chemical[ii].isalpha(): # if the last letter is alpha, last index is 1
        chemical+='1'
    num=len(chemical)
    net=0
    for (ii, before) in enumerate(Pos):
        if (before-1)<0:  # first one
            continue
        if chemical[before-1].isalpha():  # check if the letter before capital is letter
            Ind.append(1)
            net+=1
        else:
            Ind.append(int(chemical[before-1]))
            net+=int(chemical[before-1])
    Ind.append(int(chemical[num-1])) # last index is the last letter of chemical
    net+=int(chemical[num-1])
    for item in Ind:
        Frac.append(float(item)/net)
    print Elem
    print Ind
    print Frac

#def reflectivity(eV0=14000.0, th_deg=[], mat=[], thick=[], den=[], rough=[], tag=[],  depths=[]):
# need to make inputs for the relfecitivity.
# make film as an object

class Film:
    def __init__(self, FilmStructure='Si/Cr(50)/Pt(200)'):
         self.FilmStructure=FilmStructure
         self.LayerSequence=FilmStructure
         self.LayerList=[]
         
    def get_structure(self):
        self.get_sequence()  # expand layer structure
        fullname=self.LayerSequence
        layers=fullname.split('/')
        for layer in layers:
            tag='film'
            words=layer.split('(')
            if len(words)==1:
                thickness='100000.'
                material=words[0]
                tag='substrate'
            else:
                material=words[0]
                thickness=words[1]
                thickness=thickness[:-1]    # remove ')'
            onelayer=FilmLayer(composition=material, thickness=thickness)
            onelayer.tag=tag
            self.LayerList.append(onelayer)
        # add a vacuum layer on top
        onelayer=FilmLayer(composition='He', density=1e-10, thickness=0)
        onelayer.tag='vacuum'
        self.LayerList.append(onelayer)


    def reverse_structure(self):
        self.LayerList.reverse()

    
    def get_sequence(self):
        fullname=self.FilmStructure
        repeater_list=letters_between(fullname, '[', ']')
        multiplier_list=letters_between(fullname, 'x', '/')
        num0=len(repeater_list)
        for nn in range(0, num0):
            #print ' * ',  fullname
            repeater_list=letters_between(fullname, '[', ']')
            multiplier_list=letters_between(fullname, 'x', '/')
        
            (text1, posL1, posR1)=repeater_list[0]
            (num2, posL2, posR2)=multiplier_list[0]
            pre=fullname[:posL1]
            center=''
            for ix in range(0, int(num2)):
                center=center+text1+'/'
            post=fullname[posR2+1:]
            if post=='':    center=center[:-1]
            fullname=pre+center+post
            #print ' ** ',  fullname
        self.LayerSequence=fullname
        print fullname

class FilmLayer:
    def __init__(self, composition='Si', density=1, thickness=1):
        self.tag='film'
        self.composition=composition
        self.density=density        # g/cc
        self.relden=thickness         # relative density
        self.thickness=thickness     # layer thickness
        self.rms=1.0            # layer roughness  


def letters_between(text0, strL, strR):  # finds letters in text0 between strL and strR
    middle=''; list0=[]; iL=-777; iR=-777
    for (ii, letter) in enumerate(text0):
        if letter==strL:
            iL=ii
            if (iL==(len(text0)-2)) or (iL==(len(text0)-3)): # second to last letter
                middle=text0[iL+1:]
                list0.append((middle, iL, len(text0)-1))
                iL=-777; iR=-777
        if iL!=-777 and letter==strR:
            iR=ii
            middle=text0[iL+1: iR]
            list0.append((middle, iL, iR) )
            iL=-777; iR=-777
    return list0
    # returns list of tuples (string, pos of strL, and pos of strR)
                 

#-----------------------------------------------------------------------------------    
if __name__ == '__main__':
    sample1=Film()
    sample1.get_structure()
    print sample1.FilmStructure
    for item in sample1.LayerList:
        print item.composition, item.thickness, item.density,item.rms, item.tag
    print '-----------------'
    aa='Si/Ta(10)/[Pt(20)/Cr(30)]x3/Au(40)'
    sample2=Film(aa)
    sample2.get_structure()
    print sample2.FilmStructure
    for item in sample2.LayerList:
        print item.composition, item.thickness, item.density,item.rms, item.tag
    print '-----------------'
    aa='Si/Nd(10)/[Pd(20)/Co(30)]x3/Ag(40)/[Pt(22)/Fe(33)]x2/Al(10)'
    sample3=Film(aa)
    sample3.get_structure()
    print sample3.FilmStructure
    for item in sample3.LayerList:
        print item.composition, item.thickness, item.density, item.rms,item.tag
    print '-----------------'
    aa='Si/Nd(10)/[Pd(20)/Co(30)]x3/Ag(40)/[Pt(22)/Fe(33)]x10'
    sample4=Film(aa)
    sample4.get_structure()
    sample4.reverse_structure()
    print sample4.FilmStructure
    for item in sample4.LayerList:
        print item.composition, item.thickness, item.density, item.rms,item.tag
    print '-----------------'
#    print    letters_between(aa, '[', ']')
#    print letters_between(aa, 'x', '/')
    # first two work but not the last one.
    
# Si/Cr(50)/[Pt(40)/Fe(20)]x10  this structure will fail the program

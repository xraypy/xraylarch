from larch.xray.xraydb import XrayDB
db = XrayDB()

def extract(dat, key):
    val = dat.get(key, [' '])[0]
    if isinstance(val, float) and val > 1:
        val = int(round(val))
    return str(val)

elnames = ('', 'hydrogen' , 'helium', 'lithium' , 'beryllium', 'boron' ,
           'carbon' ,'nitrogen' , 'oxygen', 'fluorine' , 'neon' ,'sodium',
           'magnesium', 'aluminum' , 'silicon', 'phosphorus' , 'sulfur',
           'chlorine' , 'argon', 'potassium' , 'calcium', 'scandium' ,
           'titanium','vanadium' , 'chromium','manganese' , 'iron',
           'cobalt' , 'nickel','copper' , 'zinc','gallium' ,
           'germanium','arsenic' , 'selenium','bromine' , 'krypton',
           'rubidium' , 'strontium','yttrium' , 'zirconium','niobium' ,
           'molybdenum','technetium' , 'ruthenium','rhodium' ,
           'palladium','silver' , 'cadmium','indium' , 'tin', 'antimony' ,
           'tellurium','iodine' , 'xenon','cesium' , 'barium','lanthanum' ,
           'cerium','praseodymium', 'neodymium', 'promethium' ,
           'samarium','europium' , 'gadolinium', 'terbium' ,
           'dysprosium','holmium' , 'erbium','thulium' ,
           'ytterbium','lutetium' , 'hafnium','tantalum' , 'tungsten',
           'rhenium' , 'osmium','iridium' , 'platinum','gold' ,
           'mercury','thallium' , 'lead','bismuth' , 'polonium', 'astatine',
           'radon','francium' , 'radium','actinium' ,
           'thorium','protactinium', 'uranium','neptunium' , 'plutonium',
           'americium', 'curium', 'berkelium', 'californium')

chemstates = {'':'',
              'hydrogen':'+1',
              'helium':'',
              'lithium' :'+1',
              'beryllium':'+2',
              'boron' :'+3',
              'carbon' :'-4, -3, \ldots, +2, +3, +4',
              'nitrogen' :'-3, +3, +5',
              'oxygen':'-2',
              'fluorine' :'-1',
              'neon' :'',
              'sodium':'+1',
              'magnesium':'+2',
              'aluminum' :'+3',
              'silicon':'-4, +4',
              'phosphorus' :'-3, +3, +5',
              'sulfur':'-2, +2, +4, +6',
              'chlorine' :'-1, +1, +3, +5, +7',
              'argon':'',
              'potassium' :'+1',
              'calcium':'+2',
              'scandium' :'+3',
              'titanium':'+3, +4',
              'vanadium' :'+2, +3, +4, +5',
              'chromium':'+2, +3, +6',
              'manganese' :'+2, +3, +4, +7',
              'iron':'+2, +3',
              'cobalt' :'+2, +3',
              'nickel':'+2',
              'copper' :'+1, +2',
              'zinc':'+2',
              'gallium' :'+3',
              'germanium':'-4, +2, +4',
              'arsenic' :'-3, +3, +5',
              'selenium':'-2, +2, +4, +6',
              'bromine' :'-1, +1, +3, +5',
              'krypton':'',
              'rubidium' :'+1',
              'strontium':'+2',
              'yttrium' :'+3',
              'zirconium':'+4',
              'niobium' :'+4, +5',
              'molybdenum':'+3, +4, +6',
              'technetium' :'+4, +7',
              'ruthenium':'+3, +4, +6',
              'rhodium' :'+2, +3, +4',
              'palladium':'+2, +4',
              'silver' :'+1',
              'cadmium':'+2',
              'indium' :'+3',
              'tin':'-4, +2, +4',
              'antimony' :'-3, +3, +5',
              'tellurium':'-2, +2, +4, +6',
              'iodine' :'-1, +1, +3, +5, +7',
              'xenon':'',
              'cesium' :'+1',
              'barium':'+2',
              'lanthanum' :'+3',
              'cerium':'+3, +4',
              'praseodymium':'+3, +4',
              'neodymium':'+3',
              'promethium' :'+3',
              'samarium':'+3',
              'europium' :'+2, +3',
              'gadolinium':'+3',
              'terbium' :'+3, +4',
              'dysprosium':'+3',
              'holmium' :'+3',
              'erbium':'+3',
              'thulium' :'+3',
              'ytterbium':'+3',
              'lutetium' :'+3',
              'hafnium':'+4',
              'tantalum' :'+5',
              'tungsten':'+4, +6',
              'rhenium' :'+4',
              'osmium':'+4',
              'iridium' :'+3, +4',
              'platinum':'+2, +4',
              'gold' :'+1, +3',
              'mercury':'+1, +2',
              'thallium' :'+1, +3',
              'lead':'+2, +4',
              'bismuth' :'+3, +5',
              'polonium':'-2, +2, +4',
              'astatine':'-1, +1',
              'radon':'',
              'francium' :'+1',
              'radium':'+2',
              'actinium' :'+3',
              'thorium':'+4',
              'protactinium':'+5',
              'uranium':'+4, +6',
              'neptunium' :'+3, +4, +5',
              'plutonium':'+3, +4, +5',
              'americium':'+3, +4, +5',
              'curium':'+3',
              'berkelium':'+3, +4',
              'californium':'+3'}


table=r"""\newcommand{\%(texsym)s}{{%%
\begin{minipage}{67mm}

\vspace{1mm}

{\Huge{\hspace{1mm} {\textbf{%(sym)s}} \hfill \hfil{\textbf{%(iz)s}} \hspace{1mm}}} %%

\vspace{4mm}

{\Huge{\hfill {\Name{%(name)s}} \hfill}}

\vspace{5mm}

{\Large{
\begin{tabular*}{67mm}%%
{@{\hspace{5pt}}{r}@{\extracolsep{\fill}}r@{\extracolsep{\fill}}r}%%
{\BRed{%(k)s}}  & {\textbf{%(ka1)s}} &  {\textbf{%(kb1)s}} \\%%
{\BBlue{%(l1)s}} & %(lb3)s & %(lb4)s \\%%
{\BBlue{%(l2)s}} & %(lb1)s & %(lg1)s \\%%
{\BRed{%(l3)s}} & {\textbf{%(la1)s}} & {\textbf{%(lb2)s}} \\%%
{\BBlue{%(m5)s}} & %(ma)s & %(mb)s \\%%
\noalign{\medskip} %%  \multicolumn{3}{@{\hspace{1pt}}c}{ }\\%%
{\textbf{%(mass)s}} & \multicolumn{2}{r}{\large{%(states)s}}\\%%
\end{tabular*}
}}
\end{minipage}}}
"""

for iz in range(1, 99):
    sym = db.symbol(iz)

    dat = {'iz': iz, 'sym': sym, 'name': elnames[iz],
           'texsym': "Elem%s" % sym}

    edges = db.xray_edges(iz)
    lines = db.xray_lines(iz)
    dat['mass']  = str(db.molar_mass(iz))
    dat['states']  = chemstates.get(elnames[iz], '')


    dat['k']   = extract(edges, 'K')
    dat['ka1'] = extract(lines, 'Ka1')
    dat['kb1'] = extract(lines, 'Kb1')

    dat['l1']  = extract(edges, 'L1')
    dat['lb3'] = extract(lines, 'Lb3')
    dat['lb4'] = extract(lines, 'Lb4')

    dat['l2']  = extract(edges, 'L2')
    dat['lb1'] = extract(lines, 'Lb1')
    dat['lg1'] = extract(lines, 'Lg1')

    dat['l3']  = extract(edges, 'L3')
    dat['la1'] = extract(lines, 'La1')
    dat['lb2'] = extract(lines, 'Lb2,15')

    dat['m5'] = extract(edges, 'M5')
    dat['ma'] = extract(lines, 'Ma')
    dat['mb'] = extract(lines, 'Mb')

    # print dat.keys()
    print('%% ', dat['name'])
    print(table % dat)

highz  = ((99, 'Es', 'einsteinium'),
         (100, 'Fm', 'fermium'),
         (101, 'Md', 'mendelevium'),
         (102, 'No', 'nobelium'),
         (103, 'Lr', 'lawrencium'))

for iz, sym, name in highz:
    dat = {'iz': iz, 'sym': sym, 'name': name,
           'texsym': "Elem%s" % sym,
           'k': '', 'ka1': '', 'kb1': '', 'l1' : '', 'lb3': '', 'lb4': '',
           'l2' : '', 'lb1': '', 'lg1': '', 'l3' : '', 'la1': '', 'lb2':
           '', 'm5': '', 'ma': '', 'mb': '', 'mass':'', 'states':''}

    print( '%% ', dat['name'])
    print(table % dat)

print('%% Key')
print(table % {'iz': 'Z', 'sym': 'Symbol', 'name': 'name',
               'mass': 'Mass',  'states': 'oxidation states',
               'texsym': "ElemKey",
               'k':   r'$\mathbf{K}$ edge',
               'ka1': r'$\mathbf{K_{\alpha_1}}$',
               'kb1': r'$\mathbf{K_{\beta_1}}$',
               'l1':  r'$\mathrm{L_{\rm 1}}$ edge',
               'lb3': r'$\mathrm{L_{\beta_3}}$',
               'lb4': r'$\mathrm{L_{\beta_4}}$',
               'l2':  r'$\mathrm{L_{\rm 2}}$ edge',
               'lb1': r'$\mathrm{L_{\beta_1}}$',
               'lg1': r'$\mathrm{L_{\gamma_1}}$',
               'l3':  r'$\mathbf{L_{\rm 3}}$ edge',
               'la1': r'$\mathbf{L_{\alpha_1}}$',
               'lb2': r'$\mathbf{L_{\beta_2}}$',
               'm5':  r'$\mathrm{M_{\rm 5}}$ edge',
               'ma':  r'$\mathrm{M_{\alpha}}$',
               'mb':  r'$\mathrm{M_{\beta}}$'})

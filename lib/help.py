main = """This is Larch main help"""

import helpTopics
Help_topics = helpTopics.generate()

class Helper(object):
    """Helper looks up an displays help topics
    and/or pydoc help on larch/python objects"""
    
    TypeNames = {'<numpy.ndarray>': '<array>',
                 '<interpreter.Procedure>': '<procedure>'}
    
                 
    def __init__(self,*args,**kws):
        self.larch = None
        self.buff = []

    def help(self,*args):
        "return help text for a series of arguments"

        for arg in args:
            if arg is None: continue
            if isinstance(arg,(str,unicode)) and arg in Help_topics:
                self.addtext(Help_topics[arg])
            else:
                self.show_symbol(arg)

    def show_symbol(self,arg):
        "show help for a symbol in the symbol table"
        if isinstance(arg, str):
            sym = self.larch.symtable.getSymbol(arg,create=False)
            out = None
        else:
            out = sym = arg
            
        if sym is None:
            self.addtext(" '%s' not found"  % (arg))
        atype = str(type(sym))
        atype = atype.replace('type ','').replace('class ','').replace("'",'')
        atype = self.TypeNames.get(atype,atype)

        if out is None:
            if callable(sym) and len(sym.__doc__) > 1:
                hout = sym.__doc__
            else:
                hout = repr(sym)
            out = "%s = %s" % (arg,hout)

        if atype in ('<tuple>','<list>','<dict>','<array>'):
            out = "%s %s" % (out,atype)
        self.addtext("  %s" % out)
                        
                
    def addtext(self,text):
        self.buff.append(text)

    def getbuffer(self,delim='\n'):
        out = delim.join(self.buff)
        self.buff = []
        return out
        

#     "show help on topic or object"
#     outbuff = []
#     has_larch = larch is not None
# 
#     for a in args:
#         
#             outbuff.append(pydoc.help(a))
#     else:
#         
#     try:
#         f = open(name)
#         l = f.readlines()
# 
#     except IOError:
#         print "cannot open file: %s." % name
#         return
#     finally:
#         f.close()
#     show_more(l,filename=name,pagelength=pagelength)

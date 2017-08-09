
from termcolor import colored
import colorama
colorama.init(convert=True)
import sys

para =  '''hello
line 2 
line 3
line 4
line 5
'''


out = []
i = 0
for x in para.split('\n'):
    i = i + 1
    s = x
    if i % 2:
        s = colored(x, 'cyan')

    out.append(s)

sys.stdout.write('\n'.join(out))


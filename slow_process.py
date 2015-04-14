import time
import sys

n = 0
while n < 2000:
    sys.stdout.write(" LINE %i\n" % n)
    sys.stdout.flush()
    time.sleep(0.25)
    n  = n + 1
    

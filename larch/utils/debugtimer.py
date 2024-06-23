#!/usr/bin/env python

import time
import sys
from tabulate import tabulate

class DebugTimer():
    '''
    Measure run times for lines of code and summarize results
    '''
    def __init__(self, initial_message=None, verbose=False,
                 with_mod_count=False, precision=3):
        self.verbose = verbose
        self.precision = precision
        self.with_mod_count = with_mod_count
        self.clear(initial_message=initial_message)

    def clear(self, initial_message=None):
        self.data = []
        if initial_message is None:
            initial_message = 'DebugTimer'
        self.add(f'initial_message {time.ctime()}')

    def add(self, msg=None):
        if msg is None:
            msg = time.ctime()
        self.data.append((msg, len(sys.modules), time.perf_counter()))
        if self.verbose:
            print(msg)

    def get_table(self, precision=None, with_mod_count=True,
                 tablefmt='simple_outline'):
        prec = self.precision
        if precision is not None:
            prec = precision
        with_nmod= self.with_mod_count
        if with_mod_count is not None:
            with_nmod = with_mod_count
        m0, n0, t0 = self.data[0]
        tprev= t0
        header = ['Message','Delta Time', 'Total Time']
        row  = [m0, 0, 0]
        if with_nmod:
            header.append('# Modules')
            row.append(n0)
        table = [row[:]]
        for m, n, t in self.data[1:]:
            tt, dt = t-t0, t-tprev
            row = [m, dt, tt, n] if with_nmod else [m, dt, tt]
            table.append(row[:])
            tprev = t
        ffmt = f'.{prec}f'
        return tabulate(table, header, floatfmt=ffmt, tablefmt=tablefmt)

    def show(self, precision=None, with_mod_count=True,
             tablefmt='outline'):
        print(self.get_table(precision=precision,
                             with_mod_count=with_mod_count,
                             tablefmt=tablefmt))


def debugtimer(initial_message=None, with_mod_count=False,
               verbose=False, precision=3):
    '''debugtimer returns a DebugTimer object to measure the runtime of
    portions of code, and then write a simple report of the results.

    Arguments
    ------------
    iniitial message: str, optional initial message ['DebugTimer']
    precision:      int, precision for timing results [3]
    with_mod_count: bool, whether to include number of imported modules [True]
    verbose:        bool, whether to print() each message when entered [False]

    Returns
    --------
    DebugTimer object, with methods:

      clear(initial_message=None)      -- reset Timer
      add(message)                     -- record time, with message
      show(tablefmt='simple_outline')  -- print timer report
          where tableftmt can be any tablefmt for the tabulate module.

    Example:
    -------
      timer = debugtimer('started timer', precision=4)
      result = foo(x=100)
      timer.add('ran foo')
      bar(result)
      timer.add('ran bar')
      timer.show(tablefmt='outline')
    '''
    return DebugTimer(initial_message=initial_message,
                      with_mod_count=with_mod_count,
                      verbose=verbose, precision=precision)


if __name__ == '__main__':
    dt = debugtimer('test timer')
    time.sleep(1.102)
    dt.add('slept for 1.102 seconds')
    import numpy as np
    n = 10_000_000
    x = np.arange(n, dtype='float64')/3.0
    dt.add(f'created numpy array len={n}')
    s = np.sqrt(x)
    dt.add('took sqrt')
    dt.show(tablefmt='outline')

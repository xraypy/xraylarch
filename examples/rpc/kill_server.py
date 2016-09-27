#!/usr/bin/env python

import xmlrpclib
s = xmlrpclib.ServerProxy('http://127.0.0.1:4966')
s.shutdown()



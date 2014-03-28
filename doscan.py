from lib import scandb
from lib.station_config import StationConfig
from lib.server import run_scan
from lib.detectors import get_detector
import json

sdb = scandb.ScanDB('epics_scan', # 'test_escan001',
                    server='postgresql',
                    host='mini.cars.aps.anl.gov',
                    user='epics', 
                    password = 'epics',
                    create=True)
 
# def read_conf(fname='epicsscan.ini'):
#     conf = StationConfig(fname)
#     sdb.read_station_config(conf)

print sdb

# sx = run_scan(conf)
# for detpars in conf['detectors']:
#     print type(detpars)
#     det = get_detector(**detpars)
#     print det



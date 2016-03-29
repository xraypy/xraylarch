from epicsscan import scandb
# from lib.larch_interface import LarchScanDBServer

import epics
import json

from scan_credentials import conn
sdb = scandb.ScanDB(**conn)

conf = dict(energy_pv='13IDE:En:Energy',
            dspace_pv='13IDE:En:dspace',
            height_pv='13IDE:En:height',
            id_offset_pv='13IDE:En:id_off',
            id_track_pv='13IDE:En:id_track',
            id_wait_pv='13IDE:En:id_wait',
            y2_track_pv='13IDE:En:y2_track',
            width_motor='13IDA:m66', 
            theta_motor='13IDA:m65',
            id_drive_pv='ID13us:ScanEnergy',
            id_read_pv='ID13us:Energy',
            qxafs_record='13XRM:QXAFS',
            traj_name='qxafs.traj',
            use_id=True, 
            mcs_pv='13IDE:SIS1:',
            type='NewportXPS', 
            mode='PVTGroup',
            host='164.54.160.41', user='Administrator',
            passwd='Administrator', 
            group='MONO',
            positioners='THETA, HEIGHT', 
            outputs ='CurrentPosition, SetpointPosition')


text = json.dumps(conf)

sdb.set_config('QXAFS', text)





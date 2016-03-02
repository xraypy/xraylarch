import time
import sys
import ftplib
import logging
from six import StringIO
from XPS_C8_drivers import  XPS

##
## used methods for collector.py
##    abortScan, clearabort
##    done ftp_connect
##    done ftp_disconnect
##
## mapscan:   Build (twice!)
## linescan:  Build , clearabort
## ExecTraj;  Execute(),   building<attribute>, executing<attribute>
## WriteTrajData:  Read_FTP(), SaveGatheringData()
##
## need to have env and ROI written during traj scan:
##   use a separate thread for ROI and ENV, allow
##   XY trajectory to block.

DEFAULT_ACCEL = {'X': 10.0, 'Y': 10.0, 'THETA': 10.0}

class config:
    port    = 5001
    timeout = 10
    user    = 'Administrator'
    passwd  = 'Administrator'
    # group_name    = 'FINE'
    # positioners   = 'X Y THETA'
    gather_titles = "# XPS Gathering Data\n#--------------"
    # gather_outputs =  ('CurrentPosition', 'FollowingError',
    #                    'SetpointPosition', 'CurrentVelocity')
    gather_outputs =  ('CurrentPosition', 'SetpointPosition')

class XPSTrajectory(object):
    """XPS trajectory....
    """
    gather_header = "# XPS Gathering Data\n#--------------"
    traj_folder   = 'Public/Trajectories'
    def __init__(self, host, user='Administrator', passwd='Administrator',
                 port=5001, timeout=10, group=None, positioners=None,
                 outputs=None, **kws):

        self.host   = host
        self.user   = user
        self.passwd = passwd
        self.group  = group
        self.port  = port
        self.timeout = timeout
        self.traj_file = None
        positioners = positioners.replace(',', ' ').split()
        self.positioners = [a.strip() for a in positioners]
        if outputs is None:
            outputs = 'CurrentPosition, SetpointPosition'
        outputs = [a.strip() for a in outputs.replace(',', ' ').split()]

        self.make_template()

        gout, gtit = [], []
        for pname in self.positioners:
            for out in outputs:
                gout.append('%s.%s.%s' % (self.group, pname, out))
                gtit.append('%s.%s' % (pname, out))
        self.gather_outputs = gout
        self.gather_titles  = "%s\n#%s\n" % (self.gather_header,
                                          "  ".join(gtit))

        self.xps = XPS()
        self.ssid = self.xps.TCP_ConnectToServer(self.host,
                                                 self.port,
                                                 self.timeout)
        ret = self.xps.Login(self.ssid, self.user, self.passwd)
        self.trajectories = {}
        self.ftpconn = ftplib.FTP()

        self.nlines_out = 0

        self.xps.GroupMotionDisable(self.ssid, self.group)
        time.sleep(0.1)
        self.xps.GroupMotionEnable(self.ssid, self.group)

        for i in range(64):
            self.xps.EventExtendedRemove(self.ssid,i)

    def SetupTrajectory(self, npulses, dtime, traj_file=None):
        """set up a trajectory run with npulses and dtime per pulse,
        the nsmae of a trajectory file should be provided, or have been
        been uploaded (by this instance of XPS_Trajectory)
        """
        if traj_file is not None:
            self.traj_file = traj_file
        if self.traj_file is None:
            print("no trajectory file given... may need to upload")

        r1 = self.xps.GatheringReset(self.ssid)
        r2 = self.xps.GatheringConfigurationSet(self.ssid, self.gather_outputs)
        r3 = self.xps.MultipleAxesPVTPulseOutputSet(self.ssid, self.group,
                                                     1, npulses+1, dtime)
        r4 = self.xps.MultipleAxesPVTVerification(self.ssid,
                                                   self.group,
                                                   self.traj_file)
        # print("SetupTrajectory ", r1, r2, r3, r4)

    def RunTrajectory(self, traj_file=None):
        """run trajectory just after it has been set up with SetupTrajectory()"""
        if traj_file is not None:
            self.traj_file = traj_file
        if self.traj_file is None:
            print("no trajectory file given... may need to upload")

        buffer = ('Always', '%s.PVT.TrajectoryPulse' % self.group,)
        r1 = self.xps.EventExtendedConfigurationTriggerSet(self.ssid,
                                                          buffer,
                                                          ('0','0'), ('0','0'),
                                                          ('0','0'), ('0','0'))

        r2 = self.xps.EventExtendedConfigurationActionSet(self.ssid,
                                                         ('GatheringOneData',),
                                                         ('',), ('',),
                                                         ('',), ('',))

        self.event_id, m = self.xps.EventExtendedStart(self.ssid)
        # print(" EXECUTE TRAJECTORY ", self.ssid, self.group, self.traj_file, self.event_id)
        return  self.xps.MultipleAxesPVTExecution(self.ssid,
                                                  self.group,
                                                  self.traj_file, 1)


    def EndTrajectory(self):
        """clear trajectory setup"""
        r1 = self.xps.EventExtendedRemove(self.ssid, self.event_id)
        r2 = self.xps.GatheringStop(self.ssid)

    def ftp_connect(self):
        self.ftpconn.connect(self.host)
        self.ftpconn.login(self.user, self.passwd)
        self.FTP_connected = True

    def ftp_disconnect(self):
        "close ftp connnection"
        self.ftpconn.close()
        self.FTP_connected=False

    def upload_trajectoryFile(self, fname,  data):
        self.ftp_connect()
        self.ftpconn.cwd(self.traj_folder)
        self.ftpconn.storbinary('STOR %s' %fname, StringIO(data))
        self.ftp_disconnect()
        self.traj_file = fname

    def make_template(self):
        # line1
        b1 = ['%(ramptime)f']
        b2 = ['%(scantime)f']
        b3 = ['%(ramptime)f']
        for p in self.positioners:
            b1.append('%%(%sramp)f' % p)
            b1.append('%%(%svelo)f' % p)
            b2.append('%%(%sdist)f' % p)
            b2.append('%%(%svelo)f' % p)
            b3.append('%%(%sramp)f' % p)
            b3.append('%(zero)f')
        b1 = ', '.join(b1)
        b2 = ', '.join(b2)
        b3 = ', '.join(b3)
        self.template = '\n'.join(['', b1, b2, b3])

    def DefineLineTrajectories(self, axis='X', start=0, stop=1, accel=None,
                               step=0.001, scantime=10.0, **kws):
        """defines 'forward' and 'backward' trajectories for a simple 1 element
        line scan in PVT Mode"""
        axis =  axis.upper()
        if accel is None:
            accel = DEFAULT_ACCEL[axis]

        dist     = (stop - start)*1.0
        sign     = dist/abs(dist)
        scantime = abs(scantime)
        pixeltime = scantime * step / abs(dist)
        velo      = dist / scantime
        ramptime = abs(velo / accel)
        ramp     = 0.5 * velo * ramptime
        fore_traj = {'scantime':scantime, 'axis':axis, 'accel': accel,
                     'ramptime': ramptime, 'pixeltime': pixeltime,
                     'zero': 0.}
        # print( 'Scan Times: ', scantime, pixeltime, (dist)/(step), accel)
        this = {'start': start, 'stop': stop, 'step': step,
                'velo': velo, 'ramp': ramp, 'dist': dist}

        for attr in this.keys():
            for ax in self.positioners:
                if ax == axis:
                    fore_traj["%s%s" % (ax, attr)] = this[attr]
                else:
                    fore_traj["%s%s" % (ax, attr)] = 0.0

        back_traj = fore_traj.copy()
        for ax in self.positioners:
            for attr in ('velo', 'ramp', 'dist'):
                back_traj["%s%s" % (ax, attr)] *= -1.0
            back_traj["%sstart" % ax] = this['stop']
            back_traj["%sstp" % ax]   = this['start']

        self.trajectories['backward'] = back_traj
        self.trajectories['foreward'] = fore_traj

        ret = False
        try:
            self.upload_trajectoryFile('foreward.trj', self.template % fore_traj)
            self.upload_trajectoryFile('backward.trj', self.template % back_traj)
            ret = True
        except:
            logging.exception("error uploading trajectory")
        return ret

    def RunLineTrajectory(self, name='foreward', verbose=False, save=True,
                          outfile='Gather.dat',  debug=False):
        """run trajectory in PVT mode"""
        traj = self.trajectories.get(name, None)
        if traj is None:
            print('Cannot find trajectory named %s' %  name)
            return

        traj_file = '%s.trj'  % name
        axis = traj['axis']
        dtime = traj['pixeltime']

        ramps = [-traj['%sramp' % p] for p in self.positioners]

        self.xps.GroupMoveRelative(self.ssid, 'FINE', ramps)

        # print '=====Run Trajectory =  ', traj, axis, ramps, traj_file

        self.gather_outputs = []
        gather_titles = []
        for out in gather_outputs:
            self.gather_outputs.append('%s.%s.%s' % (self.group, axis, out))
            gather_titles.append('%s.%s' % (axis, out))

        self.gather_titles  = "%s\n#%s\n" % (gather_titles,
                                             "  ".join(gather_titles))

        # print '==Gather Titles== ',  self.gather_titles
        # print '==Gather Outputs==',  self.gather_outputs

        ret = self.xps.GatheringReset(self.ssid)
        self.xps.GatheringConfigurationSet(self.ssid, self.gather_outputs)
        # print " Group Name ", self.group

        ret = self.xps.MultipleAxesPVTPulseOutputSet(self.ssid, self.group,
                                                     1, 3, dtime)
        ret = self.xps.MultipleAxesPVTVerification(self.ssid, self.group, traj_file)

        buffer = ('Always', '%s.PVT.TrajectoryPulse' % self.group,)
        ret = self.xps.EventExtendedConfigurationTriggerSet(self.ssid, buffer,
                                                          ('0','0'), ('0','0'),
                                                          ('0','0'), ('0','0'))

        ret = self.xps.EventExtendedConfigurationActionSet(self.ssid,  ('GatheringOneData',),
                                                         ('',), ('',),('',),('',))

        eventID, m = self.xps.EventExtendedStart(self.ssid)

        ret = self.xps.MultipleAxesPVTExecution(self.ssid, self.group, traj_file, 1)
        ret = self.xps.EventExtendedRemove(self.ssid, eventID)
        ret = self.xps.GatheringStop(self.ssid)

        npulses = 0
        if save:
            npulses = self.SaveResults(outfile, verbose=verbose)
        return npulses

    def abortScan(self):
        pass

    def Move(self, xpos=None, ypos=None, tpos=None):
        "move XY positioner to supplied position"
        ret = self.xps.GroupPositionCurrentGet(self.ssid, 'FINE', 3)
        if xpos is None:  xpos = ret[1]
        if ypos is None:  ypos = ret[2]
        if tpos is None:  tpos = ret[3]
        self.xps.GroupMoveAbsolute(self.ssid, 'FINE', (xpos, ypos, tpos))

    def ReadGathering(self):
        """
        read gathering data from XPS, return as buffer
        returns npulses and text buffer of results
        """
        ret, npulses, nx = self.xps.GatheringCurrentNumberGet(self.ssid)
        counter = 0
        while npulses < 1 and counter < 5:
            counter += 1
            time.sleep(1.50)
            ret, npulses, nx = self.xps.GatheringCurrentNumberGet(self.ssid)
            print('Had to do repeat XPS Gathering: ', ret, npulses, nx)

        ret, buff = self.xps.GatheringDataMultipleLinesGet(self.ssid, 0, npulses)
        if ret < 0:  # gathering too long: need to read in chunks
            # how many chunks are needed??
            Nchunks = 3
            nx    = int( (npulses-2) / Nchunks)
            ret = 1
            while True:
                time.sleep(0.1)
                ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, 0, nx)
                if ret == 0:
                    break
                Nchunks = Nchunks + 2
                nx      = int( (npulses-2) / Nchunks)
                if Nchunks > 10:
                    print( 'looks like something is wrong with the XPS!')
                    break
            buff = [xbuff]
            for i in range(1, Nchunks):
                ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, i*nx, nx)
                buff.append(xbuff)
            ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, Nchunks*nx,
                                                                npulses-Nchunks*nx)
            buff.append(xbuff)
            buff = ''.join(buff)

        obuff = buff[:]
        for x in ';\r\t':
            obuff = obuff.replace(x,' ')
        return npulses, obuff
    
    def SaveResults(self,  fname, verbose=False):
        """read gathering data from XPS and save to file
        """
        npulses, obuff = self.ReadGathering()
        f = open(fname, 'w')
        f.write(self.gather_titles)
        f.write(obuff)
        f.close()
        nlines = len(obuff.split('\n')) - 1
        if verbose:
            print('Wrote %i lines, %i bytes to %s' % (nlines, len(buff), fname))
        self.nlines_out = nlines
        return npulses

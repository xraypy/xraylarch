# panel_refl.py : mirror reflectivity simulation
import wx
import wx.lib.plot as plot
import os.path
import math
import numpy
#import fluo
import readf1f2a
import SimpleParratt

#import input_file

class Plot(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, 'SimRefl: mirror reflectivity simulation', size=(450, 420))
        self.plot_on = 0
        LogList=['Yes', 'No']
        xUnitList=['m rad', 'Deg', 'qz']
        xcol2=180
        btnSim = wx.Button(self,  1, 'Simulate!', (30,20))
        wx.StaticText(self, -1, 'y-axis in log?', (xcol2, 5))
        self.cb0 = wx.ComboBox(self, 0, 'No', (xcol2, 25), (95, 25), LogList, wx.CB_DROPDOWN)
        wx.StaticText(self, -1, 'x-axis unit?', (xcol2, 50))
        self.cb1 = wx.ComboBox(self, 0, 'm rad', (xcol2, 70), (95, 25), xUnitList, wx.CB_DROPDOWN)
        wx.StaticText(self, -1, "incident x-ray energy (eV)", (5, 50))
        self.Text1 = wx.TextCtrl(self, 2, '7000.0', (10, 70))
        wx.StaticText(self, -1, "film material", (5, 100))
        self.Text2 = wx.TextCtrl(self, 3, 'Pt', (10, 120))
        wx.StaticText(self, -1, "film thickness (Angstrom)", (5, 150))
        self.Text3 = wx.TextCtrl(self, 4, '400.0', (10, 170))
        wx.StaticText(self, -1, "film density (g/cm^3)", (5, 200))
        self.Text4 = wx.TextCtrl(self, 5, '21.45', (10, 220))
        wx.StaticText(self, -1, "rms roughness for all interfaces (Angstrom)", (5, 250))
        self.Text5 = wx.TextCtrl(self, 6, '1.0', (10, 270))
        wx.StaticText(self, -1, "substrate material", (xcol2-5, 100))
        self.Text6 = wx.TextCtrl(self, 7, 'Si', (xcol2, 120))
        wx.StaticText(self, -1, "substrate density (g/cm^3)", (xcol2-5, 150))
        self.Text7 = wx.TextCtrl(self, 8, '2.33', (xcol2, 170))
        wx.StaticText(self, -1, "Include 50 Angstrom Cr underlayer?", (xcol2-5, 200))
        CrList=['Yes', 'No']
        self.cb2 = wx.ComboBox(self, 10, 'Yes', (xcol2, 220), (95, 25), CrList, wx.CB_DROPDOWN)
        wx.StaticText(self, -1, "define arbitrary layer structure", (5, 310))
        self.Text8 = wx.TextCtrl(self, 12, 'GaAs/GaAs(250)/Fe(40)/Au(20)', (10, 330), (300, 25))
        btnSim = wx.Button(self,  11, 'Simulate arbitrary structure.', (10,360))

        wx.EVT_BUTTON(self, 1, self.OnSimulate)
        wx.EVT_TEXT(self, 3, self.OnText2)
        wx.EVT_TEXT(self, 7, self.OnText6)
        wx.EVT_CLOSE(self, self.OnQuit)
        wx.EVT_BUTTON(self, 11, self.OnSimulate1)

    def OnText2(self, event):
        text=self.Text2.GetValue()
        #out=fluo.nominal_density(text)	 # will be 1.0 if not in dictionary
        inputfile='NominalDensity.txt'
        f=open(inputfile)
        lines=f.readlines()
        out=1.0
        for line in lines:
            if not line.startswith('#'):
                words=line.split(',')
                if text==words[0]:
                    temp=words[1].split()
                    out=temp[0]
        f.close()
        self.Text4.SetValue(str(out))

    def OnText6(self, event):
        text=self.Text6.GetValue()
        #out=fluo.nominal_density(text)	 # will be 1.0 if not in dictionary
        inputfile='NominalDensity.txt'
        f=open(inputfile)
        lines=f.readlines()
        out=1.0
        for line in lines:
            if not line.startswith('#'):
                words=line.split(',')
                if text==words[0]:
                    temp=words[1].split()
                    out=temp[0]
        f.close()
        self.Text7.SetValue(str(out))


    def OnSimulate(self, event):
        reload(SimpleParratt)
    # --- Retrive values from panel --------------
        # self.Text1
        text=self.Text1.GetValue()
        eV0=float(text)
        eV0_min=500
        if eV0<=eV0_min:    eV0=eV0_min+10.
        # self.Text2
        film_mat=self.Text2.GetValue()
        # self.Text3
        text=self.Text3.GetValue()
        film_thick=float(text)
        # self.Text4
        text=self.Text4.GetValue()
        film_den=float(text)
        # self.Text5
        text=self.Text5.GetValue()
        film_roughness=float(text)
        # self.Text6
        subs_mat=self.Text6.GetValue()
        # self.Text7
        text=self.Text7.GetValue()
        subs_den=float(text)
        # self.cb2
        text=self.cb2.GetValue()
        use_Cr=0
        if text=='Yes': use_Cr=1
        # self.cb1
        text=self.cb1.GetValue()
        xUnit='m rad'
        xUnit=text
        # self.cb0
        text=self.cb0.GetValue()
        use_Log=False
        if text=='Yes': use_Log=True
        if use_Cr==1:
            NumLayers=2
        else:
            NumLayers=1
    # --- make lists as reflectivity calculation input ----------
        out=readf1f2a.get_delta(film_mat, film_den, eV0)  # used to be fluo.
        delta_film=out[0]
        la_film=out[2]*10000.	      # absorption length in cm, convert to microns
        thc_film=(2.*delta_film)**(0.5)*180./math.pi
        print('%s %3.4f Degrees (%3.4f m radians)' % ('critical angle for film:', thc_film, thc_film*math.pi/180.*1000.))
        th_step=0.001
        th_range=numpy.arange(0.000, thc_film*3.0, th_step)  # angular range
        depths=[0.0]  # calculate efield intensity at air/film interface
        layer_mat=[];	layer_thick=[];	 layer_den=[];	 layer_rough=[]; layer_tag=[]
        # air
        layer_mat.append('He')
        layer_thick.append(0.0)			# in Angstroms
        #layer_den.append(0.0013)		# in g/cm^2, this will make
        layer_den.append(1e-10)			 # force this to be zero for vacuum
        layer_rough.append(film_roughness)	# in Angstroms
        layer_tag.append('air')			# layer name
        # film
        layer_mat.append(film_mat)
        layer_thick.append(film_thick)		# in Angstroms
        layer_den.append(film_den)		# in g/cm^2
        layer_rough.append(film_roughness)	# in Angstroms
        layer_tag.append(film_mat+'_layer')
        # Cr underlayer if use_Cr=1
        if (NumLayers==2):
            layer_mat.append('Cr')
            layer_thick.append(50.0)
            layer_den.append(7.19)
            layer_rough.append(film_roughness)
            layer_tag.append('Cr_layer')
        # Substrate
        layer_mat.append(subs_mat)
        layer_thick.append(100000.)	    # not necessary
        layer_den.append(subs_den)
        layer_rough.append(film_roughness)  # not necessary
        layer_tag.append(subs_mat+'_substrate')
        # print(critical angle and absorption length for film and substrate)
        print('energy(eV) \t layer \t critical_angle(Deg.) \t absorption_length(micron) \n')
        print('%4.1f \t %s \t %4.4f \t %4.4f\n' % (eV0, film_mat, thc_film, la_film))
        out=readf1f2a.get_delta(subs_mat, subs_den, eV0)
        delta_subs=out[0]
        la_subs=out[2]*10000.	      # absorption length in cm, convert it to microns
        thc_subs=(2.*delta_subs)**(0.5)*180./math.pi
        print('%4.1f \t %s \t %4.4f \t %4.4f\n' % (eV0, subs_mat, thc_subs, la_subs))
    # --- call reflectivity in SimpleParratt.py	 ------------------
        SimpleParratt.reflectivity(eV0, th_range, layer_mat, layer_thick, layer_den,\
            layer_rough, layer_tag, depths)
    # --- Plot ----------------------------------------------------
        if self.plot_on==1:
            print(self.plot_on)
            self.plot.Destroy()
            #self.frm.Destroy()
        frm = wx.Frame(self, 1, 'SimpleParratt.txt', size=(600,450))
        self.data=[]; self.data0=[]
        th0=0;	refl_half=1e6
        inputfile='SimpleParratt.txt'
        f=open(inputfile)
        lines=f.readlines()
        self.xMin=1e6; self.xMax=-1e6; self.yMin=1e6; self.yMax=-1e6
        for line in lines:
            if line.startswith('#'):	continue
            words=line.split()
            if xUnit=='m rad':
                xx=float(words[0])*math.pi/180.0*1000.	# convert deg to m rad
            if xUnit=='Deg':
                xx=float(words[0])
            if xUnit=='qz':
                ang=float(words[0])
                qz=4*math.pi*(eV0/1000.0/12.39842)*math.sin(ang*math.pi/180.0)
                xx=qz
            if self.xMin>xx: self.xMin=xx
            if self.xMax<=xx: self.xMax=xx
            yy=float(words[1])
            if self.yMin>yy: self.yMin=yy
            if self.yMax<=yy: self.yMax=yy
            self.data.append((xx, yy))
            self.data0.append((xx, 0.5))
            temp=abs(yy-0.5)
            if temp<=refl_half:
                refl_half=temp
                th0=xx
        self.yMax=1.0
        f.close()
        sample=''
        for (ii,item) in enumerate(layer_mat):
            if ii==0:
                sample='vacuum'
            else:
                sample=sample+'/'+item
        #title=str(eV0)+'eV, '+sample+', Refl.=0.5 at '+str(th0)+' m rad.'
        text0=' m rad.'
        text1='Incident angle (m rad)'
        if xUnit=='Deg':
            text0=' Deg'
            text1='Incident angle (Deg)'
        if xUnit=='qz':
            text0=' qz (1/Angstrom)'
            text1='qz (1/Agnstrom)'
        title='%4.1f, %s, %s %s %3.3f %s' % (eV0, 'eV', sample, 'Refl.=0.5 at', th0, text0)
        #------------------------------------------------
        client = plot.PlotCanvas(frm)
        # 9/1/2010: enable zooming function, double click for default size
        client.SetEnableZoom(True)
        line = plot.PolyLine(self.data, legend='', colour='red', width=1)
        line0 = plot.PolyLine(self.data0, legend='', colour='black', width=0.5)
        gc = plot.PlotGraphics([line, line0], title, text1, 'Reflectivity')
        client.setLogScale((False,False))
        if use_Log==True: client.setLogScale((False,True))
        client.Draw(gc,	 xAxis= (self.xMin,self.xMax), yAxis= (self.yMin,self.yMax))
        frm.Show(True)
        self.plot_on = 1
        self.plot=frm
        #------------------------------------------------

    def OnSimulate1(self, event):  # for arbitrary structure
        reload(SimpleParratt)
    # --- Retrive values from panel --------------
        # self.Text1
        text=self.Text1.GetValue()
        eV0=float(text)
        eV0_min=500
        if eV0<=eV0_min:    eV0=eV0_min+10.
        # self.Text2
        film_mat=self.Text2.GetValue()
        # self.Text3
        text=self.Text3.GetValue()
        film_thick=float(text)
        # self.Text4
        text=self.Text4.GetValue()
        film_den=float(text)
        # self.Text5
        text=self.Text5.GetValue()
        film_roughness=float(text)
        # self.Text6
        subs_mat=self.Text6.GetValue()
        # self.Text7
        text=self.Text7.GetValue()
        subs_den=float(text)
        # self.cb2
        text=self.cb2.GetValue()
        use_Cr=0
        if text=='Yes': use_Cr=1
        # self.cb1
        text=self.cb1.GetValue()
        xUnit='m rad'
        xUnit=text
        # self.cb0
        text=self.cb0.GetValue()
        use_Log=False
        if text=='Yes': use_Log=True
        if use_Cr==1:
            NumLayers=2
        else:
            NumLayers=1
        LayerStructure0=self.Text8.GetValue()
        import read_FilmName
        film1=read_FilmName.Film(LayerStructure0)
        film1.get_structure()
        film1.reverse_structure()  # reverse the layer order so that the top is vaccum
        layer_mat=[];	layer_thick=[];	 layer_den=[];	 layer_rough=[]; layer_tag=[]
        layer_thc=[]; layer_la=[]
        print('energy(eV) \t layer \t th_c(Deg.) \t th_c(m rad) \t absorption_length(micron) \t density (g/cc)\n')
        for (ii, layer1) in enumerate(film1.LayerList):
            layer_mat.append(str(layer1.composition))
            inputfile='NominalDensity.txt'
            f=open(inputfile)
            lines=f.readlines()
            out=1.0
            for line in lines:
                if not line.startswith('#'):
                    words=line.split(',')
                    if layer1.composition==words[0]:
                        temp=words[1].split()
                        out=temp[0]
            layer1.density=float(out)
            f.close()
            layer_den.append(float(layer1.density))
            layer_thick.append(float(layer1.thickness))
            layer_rough.append(float(layer1.rms))
            layer_tag.append(str(layer1.tag))
            out=readf1f2a.get_delta(layer1.composition, layer1.density, eV0)
            la_layer=out[2]*10000.0  # absorption length in cm, convert to microns
            delta_layer=out[0]
            thc_layer=(2.*delta_layer)**(0.5)*180./math.pi  # critical angle in deg
            if ii==1:
                thc_toplayer=thc_layer
            print('%4.1f \t %s \t %4.4f \t %4.4f \t %4.1f \t %s\n' % \)
                (eV0, layer1.composition+'-'+layer1.tag, thc_layer, thc_layer*math.pi/180.*1000., la_layer, layer1.density)
        th_step=0.001
        th_range=numpy.arange(0.000, thc_toplayer*12.0, th_step)  # angular range
        depths=[0.0]  # calculate efield intensity at air/film interface
        #print(layer_mat)
        #print(layer_thick)
        #print(layer_den)
        #print(layer_rough)
        #layer_mat=['He', 'Cr', 'Si']; layer_thick=[0, 10., 10000]; layer_den=[1,1,1]; layer_rough=[1,1,1]
    # --- call reflectivity in SimpleParratt.py	 ------------------
        SimpleParratt.reflectivity(eV0, th_range, layer_mat, layer_thick, layer_den,\
            layer_rough, layer_tag, depths)
    # --- Plot ----------------------------------------------------
        if self.plot_on==1:
            print(self.plot_on)
            self.plot.Destroy()
            #self.frm.Destroy()
        frm = wx.Frame(self, 1, 'SimpleParratt.txt', size=(600,450))
        self.data=[]; self.data0=[]
        th0=0;	refl_half=1e6
        inputfile='SimpleParratt.txt'
        f=open(inputfile)
        lines=f.readlines()
        self.xMin=1e6; self.xMax=-1e6; self.yMin=1e6; self.yMax=-1e6
        for line in lines:
            if line.startswith('#'):	continue
            words=line.split()
            if xUnit=='m rad':
                xx=float(words[0])*math.pi/180.0*1000.	# convert deg to m rad
            if xUnit=='Deg':
                xx=float(words[0])
            if xUnit=='qz':
                ang=float(words[0])
                qz=4*math.pi*(eV0/1000.0/12.39842)*math.sin(ang*math.pi/180.0)
                xx=qz
            if self.xMin>xx: self.xMin=xx
            if self.xMax<=xx: self.xMax=xx
            yy=float(words[1])
            if self.yMin>yy: self.yMin=yy
            if self.yMax<=yy: self.yMax=yy
            self.data.append((xx, yy))
            self.data0.append((xx, 0.5))
            temp=abs(yy-0.5)
            if temp<=refl_half:
                refl_half=temp
                th0=xx
        self.yMax=1.0
        f.close()
        sample=''
        for (ii,item) in enumerate(layer_mat):
            if ii==0:
                sample='vacuum'
            else:
                sample=sample+'/'+item
        #title=str(eV0)+'eV, '+sample+', Refl.=0.5 at '+str(th0)+' m rad.'
        text0=' m rad.'
        text1='Incident angle (m rad)'
        if xUnit=='Deg':
            text0=' Deg'
            text1='Incident angle (Deg)'
        if xUnit=='qz':
            text0=' qz (1/Angstrom)'
            text1='qz (1/Agnstrom)'
        title='%4.1f, %s, %s %s %3.3f %s' % (eV0, 'eV', sample, 'Refl.=0.5 at', th0, text0)
        #------------------------------------------------
        client = plot.PlotCanvas(frm)
        # 9/1/2010: enable zooming function, double click for default size
        client.SetEnableZoom(True)
        line = plot.PolyLine(self.data, legend='', colour='red', width=1)
        line0 = plot.PolyLine(self.data0, legend='', colour='black', width=0.5)
        gc = plot.PlotGraphics([line, line0], title, text1, 'Reflectivity')
        client.setLogScale((False,False))
        if use_Log==True: client.setLogScale((False,True))
        client.Draw(gc,	 xAxis= (self.xMin,self.xMax), yAxis= (self.yMin,self.yMax))
        frm.Show(True)
        self.plot_on = 1
        self.plot=frm
        #------------------------------------------------


    def OnQuit(self, event):
        self.plot_on=0
        self.Destroy()

class MyApp(wx.App):
    def OnInit(self):
        dlg = Plot(None, -1, 'panel.py')
        dlg.Show(True)
        dlg.Centre()
        return True
app = MyApp(0)
app.MainLoop()



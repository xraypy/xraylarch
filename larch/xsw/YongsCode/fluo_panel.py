# 2010:      panel for fluo.py
# 1/13/2011: use readf1f2.py instead of fluo.py, remove fluo-related parts.
# 4/18/2011: updated to use fluo_det, fluo_elem, readf1f2a instead of fluo
import wx
import wx.lib.plot as plot
import fluo_elem, fluo_det, readf1f2a
import os.path
import os
import time


class Plot(wx.Dialog):
        def __init__(self, parent, id, title):
                wx.Dialog.__init__(self, parent, id, 'SimFluo: fluorescence spectrum simulation', size=(350, 480))
#-------------  read simulated spectrum and set plot limits  --------------------------
                self.data=[]; self.data2=[]
                self.plot_on=0
                self.path=os.getcwd()   # remembers current directory
                inputfile='simSpectrum_plot.txt'
                if os.path.exists(inputfile)==0:
                        fo=open(inputfile, 'w')
                        out1=str(1e3)+' '+str(1e6)+'\n'
                        fo.write(out1)
                        out1=str(10e3)+' '+str(10e6)+'\n'
                        fo.write(out1)
                        fo.close()
                f=open(inputfile)
                lines=f.readlines()
                self.xMin=1e6; self.xMax=-1e6; self.yMin=1e6; self.yMax=-1e6
                for line in lines:
                    if line.startswith('#'):    continue
                    words=line.split()
                    xx=float(words[0])
                    if self.xMin>xx: self.xMin=xx
                    if self.xMax<=xx: self.xMax=xx
                    yy=float(words[1])
                    if self.yMin>yy: self.yMin=yy
                    if self.yMax<=yy: self.yMax=yy
                    self.data.append((xx, yy))
                f.close()
                HeList=['Yes', 'No']
                xswList=['WD60mm(XRM)', 'WD30mm(XSW)', 'none']
                self.fyList=[]
                self.locationList=['all', 'top', 'bottom', 'surface']
                self.ppmList=['atomic fraction', 'weight fraction']
                self.TextOutputList=[]
                self.input=fluo_det.input_param()
#--------------------------------------------------------------------------
                btnSim = wx.Button(self,  1, 'Simulate!', (30,10))
                btnPlot = wx.Button(self,  2, 'Plot!', (30,35))
                self.cbLINES = wx.ComboBox(self, 3, 'emission lines', (120, 30), (165, 10), self.fyList, wx.CB_DROPDOWN)
                #
                wx.StaticText(self, -1, "incident x-ray energy (eV)", (5, 60))
                self.textENERGY = wx.TextCtrl(self, 10, '7500', (10, 75))
                wx.StaticText(self, -1, "incident x-ray angle (Deg.)", (165, 60))
                self.textANGLE = wx.TextCtrl(self, 11, '45.', (170, 75))
                #
                wx.StaticText(self, -1, "elements and concentrations (ppm of top substrate material)", (5, 100))
                wx.StaticText(self, -1, "in atomic fraction or weight fraction", (5, 115))
                self.cbPPM = wx.ComboBox(self, 12, 'atomic fraction', (200, 113), (140, 10), self.ppmList, wx.CB_DROPDOWN)
                self.textELEMENT = wx.TextCtrl(self,  13, 'La 10 Ce 10 Nd 10', (10,135), size=(280, 20))
                #
                wx.StaticText(self, -1, "top substrate material", (5, 155))
                self.textSUBSTRATE = wx.TextCtrl(self, 14, 'CaCO3', (10, 170), (80, 20))
                wx.StaticText(self, -1, "density (g/cc)", (135, 155))
                self.textDENSITY = wx.TextCtrl(self, 15, '2.71', (140, 170), (80, 20))
                wx.StaticText(self, -1, "thickness (cm)", (235, 155))
                self.textTOP = wx.TextCtrl(self, 16, '0.001', (240, 170), (80, 20))
                #
                wx.StaticText(self, -1, "bottom substrate material", (5, 195))
                self.textSUBSTRATE2 = wx.TextCtrl(self, 17, 'Al2O3', (10, 210), (80, 20))
                wx.StaticText(self, -1, "density (g/cc)", (135, 195))
                self.textDENSITY2 = wx.TextCtrl(self, 18, '3.97', (140, 210), (80, 20))
                wx.StaticText(self, -1, "thickness (cm)", (235, 195))
                self.textBOT = wx.TextCtrl(self, 19, '0.001', (240, 210), (80, 20))
                #
                wx.StaticText(self, -1, 'location of fluorescence elements', (5, 235))
                self.cbLOCATION = wx.ComboBox(self, 20, 'all', (10, 250), (165, 10), \
                                       self.locationList, wx.CB_DROPDOWN)              
                #
                wx.StaticText(self, -1, "He-path used?", (5, 275))
                self.cbHE = wx.ComboBox(self, 21, 'No', (10, 290), (95, 10), HeList, wx.CB_DROPDOWN)
                wx.StaticText(self, -1, '# of Al film (1.5mil)', (5, 315))
                self.textAL = wx.TextCtrl(self, 22, '0', (10, 330))
                wx.StaticText(self, -1, "# of Kapton film (0.3mil)", (165, 315))
                self.textKAPTON = wx.TextCtrl(self, 23, '0', (170, 330))
                wx.StaticText(self, -1, "Vortex detector distance (cm)", (5, 355))
                self.textWD = wx.TextCtrl(self, 24, '6.0', (10, 370))
                wx.StaticText(self, -1, "detector collimator", (165, 355))
                self.cbXSW = wx.ComboBox(self, 25, 'WD60mm(XRM)', (170, 370), (120, 10), xswList, wx.CB_DROPDOWN)
                self.TextOutput = wx.ComboBox(self, 26, 'output message', (10, 410), (250, 20), self.TextOutputList, wx.CB_DROPDOWN)
                #
                wx.EVT_BUTTON(self, 1, self.OnSimulate)
                wx.EVT_BUTTON(self, 2, self.OnPlot)
                wx.EVT_TEXT(self, 14, self.OntextSUBSTRATE)
                wx.EVT_TEXT(self, 17, self.OntextSUBSTRATE2)
                wx.EVT_TEXT(self, 25, self.OnCBXSW)
                wx.EVT_CLOSE(self, self.OnQuit)

								
        def OnSimulate(self, event):
                #----------  Retrive values from panel --------------
                AtomList=[]; ConcList=[]; Atoms=[]
                text=self.textENERGY.GetValue()
                eV0=float(text)                 # incident energy
                text=self.textANGLE.GetValue()
                angle0=float(text)              # incident angle
                if eV0<=1000:   eV0=1010
                text=self.textELEMENT.GetValue()        # list of elements and concentrations
                words=text.split()
                junk=["'", ",", ":", ";", "/", "\\"]
                for (ix,word) in enumerate(words):
                        concentration=1.0;      skip=0
                        for test in junk:
                                if word==test: skip=1
                                if word.startswith(test): word=word[1:]
                                if word.endswith(test): word=word[:-1]                               
                        if skip==1: continue
                        if (word.isalpha()):            # element name
                                word=word[0].upper()+word[1:]
                                AtomList.append(str(word))
                        else:                           # concentration
                                concentration=float(word)
                                ConcList.append(concentration)
                # appending to Atoms is done later.
                #
                text=self.textSUBSTRATE.GetValue()
                substrate1=str(text)                    # substrate1 material
                text=self.textDENSITY.GetValue()
                density1=float(text)                    # substrate1 density in g/cc
                text=self.textTOP.GetValue()
                thickness1=float(text)                  # substrate1 thickness in cm
                #
                text=self.textSUBSTRATE2.GetValue()
                substrate2=str(text)                    # substrate2 material
                text=self.textDENSITY2.GetValue()
                density2=float(text)                    # substrate2 density
                text=self.textBOT.GetValue()
                thickness2=float(text)                  # substrate2 thickness
                text=self.cbLOCATION.GetValue()
                loc=text                                # location of elements 
                #
                unit_PPM=self.cbPPM.GetValue()          # unit for concentration atomic fraction or  weight fraction
                # 
                if unit_PPM=='weight fraction':                   # concentrations are in weight fraction
                        substrate1_material = fluo_det.Material(substrate1, density1)
                        AtomicWeight_substrate1 = substrate1_material.AtWt      # g/mol of substrate1
                        for (ii, item) in enumerate(AtomList):
                                AtomicSymbol = item                               # dilute elements
                                AtomicWeight = fluo_elem.AtSym2AtWt(AtomicSymbol)      # g/mol
                                concentration_AtWtFract = ConcList[ii]            # concentration in weight fraction
                                Conversion = AtomicWeight_substrate1/AtomicWeight # weight fraction to atomic fraction
                                ConcList[ii] = Conversion * concentration_AtWtFract
                                #print(AtomicSymbol, concentration_AtWtFract, Conversion, Conversion * concentration_AtWtFract)
                # concentrations are in atomic percent now
                # 
                for (ii, item) in enumerate(AtomList):
                        AtSym=item                      # name of element
                        con=ConcList[ii]/1.0e6          # concentration, from ppm(1e-6) to fraction 
                        atom1=fluo_det.ElemFY(AtSym, con)   # atom1.AtomicSybol, atom1.Concentration
                        Atoms.append(atom1)             # Atoms is a list of objects with attributes
                #
                text=self.cbHE.GetValue()
                if text=='Yes':
                        xHe=1
                else:
                        xHe=0
                text=self.textAL.GetValue()
                xAl=float(text)
                text=self.textKAPTON.GetValue()
                xKap=float(text)
                text=self.textWD.GetValue()
                WD=float(text)
                text=self.cbXSW.GetValue()              # collimator
                if text=='WD60mm(XRM)': xsw=0
                if text=='WD30mm(XSW)': xsw=1
                if text=='none':        xsw=-1
                # --------------  run functions in fluo.py -----------------------------
                reload(fluo_det)
                self.input=fluo_det.input_param(eV0, Atoms, xHe, xAl, xKap, WD, xsw)
                matrix=fluo_det.SampleMatrix2(substrate1, density1, thickness1,substrate2, density2, thickness2, angle0, loc)
                #print('####', substrate1, density1, thickness1,substrate2, density2, thickness2)
                # --- change directory for pc executable: py2exe makes exe-file in dist folder.  put outputfiles one folder up.
                exeExists=0
                if os.path.exists('fluo_panel.exe'):    # run from exe file put outputs in different folder
                        exeExists=1
                path0=os.getcwd()
                if self.path==path0 and exeExists==1:   # current directory is the original location
                        num=len(path0)
                        range0=range(num-1, -1, -1)
                        for ix in range0:
                                if path0[ix]=='\\' :    # find position for right-most '\'
                                        pos0=ix
                                        break
                        path0=path0[:pos0]              
                        os.chdir(path0)                 # go up one level in directory
                # ------------------------------------------------------------------------
                textOut=fluo_det.sim_spectra(eV0, Atoms, xHe, xAl, xKap, WD, xsw, sample=matrix)
                printout='output: simSpectrum_table.txt, simSpectrum_plot.txt, Elemental_Sensitivity.txt'
                printout+=' saved in '+path0
                print(printout)
                #self.cbLINES.Destroy()
                #self.fyList=[]
                #self.cbLINES = wx.ComboBox(self, 3, 'Press [Plot!] to update', (120, 30), (165, 10), self.fyList, wx.CB_DROPDOWN)
                self.cbLINES.Clear()  # use these three lines instead of above 3, 8/27/2010
                self.cbLINES.SetValue(str('Press [Plot!] to update'))
                self.cbLINES.AppendItems(self.fyList)
                # -------------  display output message from fluo.sim_spectra -------------
                textList=textOut.split()
                self.TextOutputList=[]
                #self.TextOutput.Destroy()  # 8/27/2010
                for ii in range(0, len(textList), 2):
                        temp=textList[ii]+' '+textList[ii+1]
                        self.TextOutputList.append(temp)
                #self.TextOutput = wx.ComboBox(self, 26, 'concentration list', (10, 410), (280, 20), self.TextOutputList, wx.CB_DROPDOWN)
                self.TextOutput.Clear()
                self.TextOutput.AppendItems(self.TextOutputList)
                # displays number densities and absorption lengths                

        
        def OnPlot(self, event):
                if self.plot_on==1:
                        self.plot.Destroy()   # destroy old plot
                frm = wx.Frame(self, -1, 'simSpectrum_plot.txt', size=(600,450))
                #--------  read simSpectrum_table.txt and fill cb0  ----------------             
                self.data2=[]
                self.fyList=[]                  # Empty ComboBox textfield and refill below 
                inputfile='simSpectrum_table.txt'
                f=open(inputfile)
                lines=f.readlines()
                yMin=1e6; yMax=-1e6
                for line in lines:
                    if line.startswith('#'):    continue
                    words=line.split()
                    name=words[0]
                    energy = int(round(float(words[1])))        # round up to int
                    inten=words[2]; inten=inten[:7]
                    tag=words[0]+'('+str(energy)+'eV)= '+inten
                    self.fyList.append(tag)                     # add to ComboBox textfield
                    self.data2.append((energy, float(inten)))   # data2 for secondary plot
                    if (float(inten)>yMax): yMax=float(inten)
                f.close()
                #self.cbLINES.Destroy()          # Destroy ComboBox
                #self.cbLINES = wx.ComboBox(self, 3, 'emission lines', (120, 30), (165, 10), self.fyList, wx.CB_DROPDOWN)
                self.cbLINES.Clear()  # use these two lines instead of above 2, 8/27/2010
                self.cbLINES.AppendItems(self.fyList)
                #Recreate ComboBox with updated list
                #--------  Reload simSpectrum_plot.txt'  ----------------
                self.data=[]
                inputfile='simSpectrum_plot.txt'
                f=open(inputfile)
                lines=f.readlines()
                self.xMin=1e6; self.xMax=-1e6; self.yMin=1e6; self.yMax=-1e6
                for line in lines:
                    if line.startswith('#'):    continue
                    words=line.split()
                    xx=float(words[0])
                    if self.xMin>xx: self.xMin=xx
                    if self.xMax<=xx: self.xMax=xx
                    yy=float(words[1])
                    if self.yMin>yy: self.yMin=yy
                    if self.yMax<=yy: self.yMax=yy
                    self.data.append((xx, yy))
                f.close()
                factor=(self.yMax/yMax)
                for (ix, ii) in enumerate(self.data2):
                        self.data2[ix]=(ii[0], ii[1]*factor)              
                eV0=self.input.eV0; Atoms=self.input.Atoms;  xsw=self.input.xsw
                temp=''
                for nn in Atoms:
                        temp=temp+'/'+nn
                temp=temp[1:]
                title=str(eV0)+'eV, '+temp
                if xsw==1: title+=', xsw'
		#------------------------------------------------
                client = plot.PlotCanvas(frm)
                line = plot.PolyLine(self.data, legend='', colour='red', width=1)
                line2 = plot.PolyMarker(self.data2, legend='', colour='blue', marker='circle', size=0.8)
                gc = plot.PlotGraphics([line, line2], title, 'energy (eV)', 'intensity (total count=100k)')
                client.setLogScale((False,True))
                client.Draw(gc,  xAxis= (self.xMin,self.xMax), yAxis= (self.yMin,self.yMax))
                frm.Show(True)
                self.plot_on=1  # to delete the old plot.
                self.plot=frm
                # after upgrading to python 2.6 saving jpg crashes
                #client.SaveFile(fileName='plot.jpg')
                #print('plot saved to plot.jpg')



        def OntextSUBSTRATE(self, event):
                text=self.textSUBSTRATE.GetValue()      # look up to see if nominal density is available.
                out=readf1f2a.nominal_density(text)          # will be 1.0 if not in dictionary
                self.textDENSITY.SetValue(str(out))

        def OntextSUBSTRATE2(self, event):
                text=self.textSUBSTRATE2.GetValue()     # look up to see if nominal density is available.
                out=readf1f2a.nominal_density(text)          # will be 1.0 if not in dictionary
                self.textDENSITY2.SetValue(str(out))                

        def OnCBXSW(self, event):
                text=self.cbXSW.GetValue()
                if text=='WD30mm(XSW)':
                        self.textWD.SetValue('3.0')
                        self.cbHE.SetValue('Yes')
                if text=='WD60mm(XSW)': self.textWD.SetValue('6.0')

        def OnQuit(self, event):
                self.Destroy()
# -------------------------------------------------------------------------------------------------------


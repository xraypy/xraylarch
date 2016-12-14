##############################################
#### DATA CALCULATIONS FUNCTIONS

    def replot(self,event=None):
        
        if self.trim:
            self.plot1D.plot(*self.raw_data, title=self.name,
                             color='gray', label='Raw data',
                             show_legend=True)
            self.plot1D.oplot(*self.plt_data, title=self.name,
                              color='blue', label='Trimmed data',
                              show_legend=True)
        else:
            self.plot1D.plot(*self.raw_data, title=self.name,
                             color='blue', label='Raw data',
                             show_legend=True)

        if self.bgr is not None:
            self.plot1D.oplot(*self.bgr_data, title=self.name,
                              color='red', label='Background',
                              show_legend=True)
            

        if self.ipeaks is not None:
            self.calc_peaks()
            self.plot_peaks()

##############################################
#### RANGE FUNCTIONS

    def set_range(self,event=None):
        
        if float(self.val_qmin.GetValue()) - np.min(self.raw_data[0]) > 0.005:
            self.xmin = float(self.val_qmin.GetValue())
        else:
            self.xmin = np.min(self.raw_data[0])
        self.val_qmin.SetValue('%0.3f' % self.xmin)            

        if np.max(self.raw_data[0]) - float(self.val_qmax.GetValue()) > 0.005:
            self.xmax = float(self.val_qmax.GetValue())
        else:
            self.xmax = np.max(self.raw_data[0])
        self.val_qmax.SetValue('%0.3f' % self.xmax)
            
        if np.max(self.raw_data[0])-self.xmax > 0.005 or self.xmin-np.min(self.raw_data[0]) > 0.005:
            self.trim = True
        else:
            self.trim = False

        self.trim_data()
        if self.bgr is not None:
            self.fit_background()
        else:
            self.replot()
            
    def reset_range(self,event=None):

        self.xmin = np.min(self.raw_data[0])
        self.xmax = np.max(self.raw_data[0])
        
        self.val_qmin.SetValue('%0.3f' % self.xmin)
        self.val_qmax.SetValue('%0.3f' % self.xmax)
        
        self.trim = False

        self.trim_data()
        if self.bgr is not None:
            self.fit_background()
        else:
            self.replot()
    

    def trim_data(self):

#         print 'trim data'
#         print 'before:'
#         print np.max(self.plt_data)
#         print np.shape(self.plt_data)
        if self.trim:
            indicies = [i for i,value in enumerate(self.raw_data[0]) if value>=self.xmin and value<=self.xmax]
            if len(indicies) > 0:
                x = [self.raw_data[0,i] for i in indicies]
                y = [self.raw_data[1,i] for i in indicies]
                self.plt_data = np.array([x,y])
        else:
            self.plt_data = self.raw_data[:]

#         print 'after:'
#         print np.max(self.plt_data)
#         print np.shape(self.plt_data)
#         print
#         print

#         self.replot()        

##############################################
#### BACKGROUND FUNCTIONS

    def fit_background(self,event=None):
        
        if self.bgr is not None:
            print 'removing background from fit function'
            self.remove_background(None,buttons=False)

        try:
            ## this creates self.bgr and self.bgr_info
            xrd_background(*self.plt_data, group=self, exponent=self.exponent, 
                           compress=self.compress, width=self.width)
        except:
            print 'did not work to fit background'
            return

        self.ck_bkgd.Enable()
        self.btn_rbkgd.Enable()

        self.bgr_data    = self.plt_data[:,:np.shape(self.bgr)[0]]
        self.bgr_data[1] = self.bgr
        
        self.plot1D.oplot(*self.bgr_data,color='red',
                          label='Fit background',show_legend=True)

  
    def remove_background(self,event=None,buttons=True):

        ## sets background to none
        self.bgr_data = None
        self.bgr = None
        self.bgr_info = None

        self.ck_bkgd.SetValue(False)
        if buttons:
            self.ck_bkgd.Disable()
            self.btn_rbkgd.Disable()
            ## resets to trimmed data state
            self.trim_data()

        self.replot()

    
    def background_options(self,event=None):
    
        myDlg = BackgroundOptions(self)#parent=self)
        
        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
            self.exponent = int(myDlg.val_exp.GetValue())
            self.compress = int(myDlg.val_comp.GetValue())
            self.width    = int(myDlg.val_wid.GetValue())
            fit = True
        myDlg.Destroy()

        if fit:
            self.fit_background()

    def subtract_background(self,event=None):

        if self.ck_bkgd.GetValue() == True:
            
            if (np.shape(self.plt_data)[1]-np.shape(self.bgr_data)[1]) > 2:
                print '**** refitting background from subtract button'
                print np.shape(self.plt_data)[1],np.shape(self.bgr_data)[1]
                print np.shape(self.plt_data),np.shape(self.bgr_data)
                self.fit_background()
            
            self.plt_data = self.plt_data[:,:np.shape(self.bgr)[0]]
            self.plt_data[1] = self.plt_data[1] - self.bgr_data[1]

            
            self.plot1D.plot(*self.plt_data, title=self.name,
                             color='blue', label='Background subtracted',
                             show_legend=True)

            self.btn_rbkgd.Disable()
            self.btn_fbkgd.Disable()
            self.btn_obkgd.Disable()
        
        else:
            
            self.plt_data = self.raw_data[:]
            self.replot()
            
            self.btn_rbkgd.Enable()
            self.btn_fbkgd.Enable()
            self.btn_obkgd.Enable()
            

##############################################
#### PEAK FUNCTIONS

    def find_peaks(self,event=None):
    
        ## clears previous searches
        self.remove_peaks()
        
        ttlpnts = len(self.plt_data[0])
        widths = np.arange(1,int(ttlpnts/self.iregions))
        
        self.ipeaks = signal.find_peaks_cwt(self.plt_data[1], widths,
                                           gap_thresh=self.gapthrsh)
# # #   scipy.signal.find_peaks_cwt(vector, widths, wavelet=None, max_distances=None, 
# # #                     gap_thresh=None, min_length=None, min_snr=1, noise_perc=10)

        self.calc_peaks()
        self.plot_peaks()
        
        self.btn_rpks.Enable()        
        self.btn_spks.Enable()

    def calc_peaks(self):

        self.plt_peaks = np.zeros((2,len(self.ipeaks)))
        for i,j in enumerate(self.ipeaks):
            self.plt_peaks[0,i] = self.plt_data[0][j]
            self.plt_peaks[1,i] = self.plt_data[1][j]
            
    def plot_peaks(self):

        self.plot1D.scatterplot(*self.plt_peaks,
                          color='red',edge_color='yellow', selectcolor='green',size=12,
                          show_legend=True)
        self.plot1D.cursor_mode = 'zoom'
 
# # #      def scatterplot(self, xdata, ydata, label=None, size=10,
# # #                     color=None, edgecolor=None,
# # #                     selectcolor=None, selectedge=None,
# # #                     xlabel=None, ylabel=None, y2label=None,
# # #                     xmin=None, xmax=None, ymin=None, ymax=None,
# # #                     title=None, grid=None, callback=None, **kw):

    def remove_peaks(self,event=None):
    
        self.peaks = None
        self.ipeaks = None
        self.replot()

        self.btn_rpks.Disable()        
        self.btn_spks.Disable()

    def edit_peaks(self,event=None):
    
        print 'this will pop up a list of peaks for removing (and adding?)'

    def peak_options(self,event=None):
    
        myDlg = PeakOptions(self)

        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
            self.iregions = int(myDlg.val_regions.GetValue())
            self.gapthrsh = int(myDlg.val_gapthr.GetValue())
            fit = True
        myDlg.Destroy()
        
        if fit:
            self.find_peaks()
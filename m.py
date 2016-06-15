add_plugin('gse_escan')

x = read_gsescan('bmd_dat.001', bad=[10, 12])

for i in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
    plot(x.x, x.det_corr[i, :]/x.det[0,:], label='%i ' % i, new=(i==2))
#endfor


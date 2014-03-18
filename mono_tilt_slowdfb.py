import epics
import time

def pv_in_range(pv, xmin, xmax):
    val = pv.get()
    return val > xmin and val < xmax

class MonoTilt(object):
    msg = 'Mono height=% .2f move DAC from %.3f to %.3f' 
    factor = 3.e-4
    def __init__(self):

        self.energy = epics.PV('13IDE:En:Energy')
        self.pitch_dac =  epics.PV('13IDA:DAC1_7')
        self.beam_height = epics.PV('13IDA:QE2:Pos12:MeanValue_RBV')
        
    def check_mono_tilt(self):
        if not pv_in_range(self.energy, 2460, 3200):
            return
        
        t0 = time.time()
        sumh, nh = 0., 0.0
        while time.time()-t0 < 1.0:
            sumh += self.beam_height.get()
            nh += 1
            time.sleep(0.1)

        old_val = self.pitch_dac.get()
        height  = sumh/(nh+0.001)
        if abs(height) > 3: 
            sign  = -abs(height)/(height)
            diff  = sign * min(500, abs(height)) 
            new_val = old_val + diff * self.factor
            if (new_val > 0.2 and new_val < 9.9  and
                abs(diff) > 0.001):
                
                print self.msg % (height, old_val, new_val)
                self.pitch_dac.put(new_val)

if __name__ == '__main__':
    m = MonoTilt()
    while True:
        try:
            time.sleep(2.0)
            m.check_mono_tilt()
        except KeyboardInterrupt:
            break
    



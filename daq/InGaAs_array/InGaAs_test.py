import os

#import------------------------------------------------------------------------

import numpy as np
import serial
import struct

import pyqtgraph as pg

#initialize--------------------------------------------------------------------

ser = serial.Serial()
ser.baudrate = 9600
ser.port = 'COM16'

#read--------------------------------------------------------------------------

ser.open()
ser.write('S')
raw_string = ser.readline()
ser.close()

#process-----------------------------------------------------------------------

out = np.zeros(256)

#remove 'ready' from end
string = raw_string[:512]
#encode to hex
vals = np.array([elem.encode("hex") for elem in string])
#reshape
vals = vals.reshape(256, -1)
vals = np.flipud(vals)
for i in range(len(vals)):
    raw_pixel = int('0x' + vals[i, 0] + vals[i, 1], 16)
    pixel = 0.00195*(raw_pixel - (2060. + -0.0142*i)) 
    out[i] = pixel

plt = pg.plot(out, title="Simplest possible plotting example")

'''
vals = np.fromstring(raw_vals, dtype = float, sep = ',')
return vals
'''
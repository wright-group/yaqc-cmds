# import------------------------------------------------------------------------

import numpy as np
import serial

# initialize--------------------------------------------------------------------

ser = serial.Serial()
ser.baudrate = 9600
ser.port = "COM5"
ser.timeout = 0.1

# read--------------------------------------------------------------------------

ser.open()
ser.write("S".encode())


eol = r"ready\n".encode()
leneol = len(eol)
line = "".encode()
while True:
    c = ser.read(1)
    if c:
        line += c
        if line.endswith(eol):
            break
    else:
        break
ser.close()


# process-----------------------------------------------------------------------

out = np.zeros(256)

# remove 'ready' from end
string = line[:512]

out = np.frombuffer(string, dtype=">i2")
# out = [string[511-(2*i):510-(2*i):-1] for i in range(256)]
# out = out[::-1]
# out = [codecs.encode(o, 'hex') for o in out]
# out = [int(o, 16) for o in out]
# out = np.array(out, dtype=np.float64)
out = out - (2060 + -0.0142 * np.arange(256))
out *= 0.0195


import matplotlib.pyplot as plt

plt.plot(out)

# import pyqtgraph as pg
# plt = pg.plot(out, title="Simplest possible plotting example")

"""
vals = np.fromstring(raw_vals, dtype = float, sep = ',')
return vals
"""

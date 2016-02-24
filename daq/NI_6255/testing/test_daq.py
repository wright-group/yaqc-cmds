'''
Is the DAQ working at all?
'''

from PyDAQmx import *
import numpy
import time

import numpy as np
import os

#os.chdir(r'C:\Users\John\Desktop\PyCMDS')

#user inputs-------------------------------------------------------------------

daq_analog_physical_channels = [3, 1, 2, 3, 4]
daq_analog_min = -1.0
daq_analog_max = 6.0

daq_digital_physical_channels = [3]
daq_digital_min = -1.0
daq_digital_max = 10.0
daq_digital_cutoff = 2.25

shots = 20
digitize = False

#initialize DAQ----------------------------------------------------------------

task_handle = TaskHandle()
read = int32()

num_analog_channels = len(daq_analog_physical_channels)
num_digital_channels = len(daq_digital_physical_channels)
num_channels = num_analog_channels + num_digital_channels

conversions_per_second = 1e6 #a property of the DAQ card
shots_per_second = 1100. #from laser
virtual_samples = int(conversions_per_second/(shots_per_second*num_channels))
us_per_virtual_sample = (1./conversions_per_second)*1e6
print us_per_virtual_sample

shots = long(shots)

try:
    #task
    DAQmxCreateTask('', byref(task_handle))

    #create global channels
    total_virtual_channels = 0
    for _ in range(virtual_samples):
        for channel in daq_analog_physical_channels:
            channel_name = 'channel_' + str(total_virtual_channels).zfill(2)
            DAQmxCreateAIVoltageChan(task_handle,                   #task handle
                                     'Dev1/ai%i'%channel,           #physical chanel
                                     channel_name,                  #name to assign to channel
                                     DAQmx_Val_Diff,                #the input terminal configuration
                                     daq_analog_min,daq_analog_max, #minVal, maxVal
                                     DAQmx_Val_Volts,               #units
                                     None)                          #custom scale
            total_virtual_channels += 1

        for channel in daq_digital_physical_channels:
            channel_name = 'channel_' + str(total_virtual_channels).zfill(2)
            DAQmxCreateAIVoltageChan(task_handle,                     #task handle
                                     'Dev1/ai%i'%channel,             #physical chanel
                                     channel_name,                    #name to assign to channel
                                     DAQmx_Val_Diff,                  #the input terminal configuration
                                     daq_digital_min,daq_digital_max, #minVal, maxVal
                                     DAQmx_Val_Volts,                 #units
                                     None)                            #custom scale
            total_virtual_channels += 1

    #timing
    DAQmxCfgSampClkTiming(task_handle,           #task handle
                          '/Dev1/PFI0',          #sorce terminal
                          1000.0,                #sampling rate (samples per second per channel) (float 64)
                          DAQmx_Val_Rising,      #acquire samples on the rising edges of the sample clock
                          DAQmx_Val_FiniteSamps, #acquire a finite number of samples
                          shots)                 #number of samples per global channel (unsigned integer 64)

except DAQError as err:
    print "DAQmx Error: %s"%err
    DAQmxStopTask(task_handle)
    DAQmxClearTask(task_handle)


#get data----------------------------------------------------------------------

samples = numpy.zeros(shots*virtual_samples*num_channels, dtype=numpy.float64)
samples_len = len(samples) #do not want to call for every acquisition

for _ in range(1):

    try:
        start_time = time.time()

        DAQmxStartTask(task_handle)

        DAQmxReadAnalogF64(task_handle,                 #task handle
                           shots,                       #number of samples per global channel (unsigned integer 64)
                           10.0,                        #timeout (seconds) for each read operation
                           DAQmx_Val_GroupByScanNumber, #fill mode (specifies whether or not the samples are interleaved)
                           samples,                     #read array
                           samples_len,                 #size of the array, in samples, into which samples are read
                           byref(read),                 #reference of thread
                           None)                        #reserved by NI, pass NULL (?)

        DAQmxStopTask(task_handle)

        #create 2D data array
        out = np.copy(samples)
        out.shape = (shots, virtual_samples, num_channels)

        #'digitize' digital channels
        if digitize:
            for i in range(num_analog_channels, num_analog_channels+num_digital_channels):
                low_value_indicies = out[:, :, i] < daq_digital_cutoff
                high_value_indicies = out[:, :, i] >= daq_digital_cutoff
                out[low_value_indicies, i] = 0
                out[high_value_indicies, i] = 1

        print 'Acquired %d shots in %f seconds'%(read.value, time.time() - start_time)

    except DAQError as err:
        print "DAQmx Error: %s"%err
        DAQmxStopTask(task_handle)
        DAQmxClearTask(task_handle)

    print out.shape
    #print out[:, :, 5].flatten()

def get_plot_arrays(channel):
    y = out[:, :, channel].flatten()
    #print len(y)
    x = numpy.zeros(len(y))
    for i in range(shots*virtual_samples):
        offset = us_per_virtual_sample*channel
        shot_count, sample_count = divmod(i, virtual_samples)
        #print shot_count, sample_count
        x[i] = offset + shot_count*1000 + sample_count*(us_per_virtual_sample*num_channels)
    return x, y



import matplotlib.pyplot as plt
plt.close()

x, y = get_plot_arrays(0)
plt.scatter(x, y, c='r')
x, y = get_plot_arrays(4)
#plt.scatter(x, y, c='g')
if digitize: plt.ylim(-0.5, 1.5)
plt.grid()
plt.xlabel('us')
plt.ylabel('V')

'''
import packages.pyqtgraph.pyqtgraph as pg
plt = pg.PlotDataItem(out[:, 0, 5].flatten(), title="Simplest possible plotting example")
plt.show()
'''

#close DAQ---------------------------------------------------------------------

if task_handle:
    DAQmxStopTask(task_handle)
    DAQmxClearTask(task_handle)
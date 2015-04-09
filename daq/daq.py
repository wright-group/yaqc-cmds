#to do##########################################################################

#[ ] daq tab
#  [ ] setting settings settings
#[ ] single channel tab
#  [ ] decide on what the display type will look like (skinned progress bar?)
#  [ ] display all channels
#[ ] current slice tab
#  [ ] two modes - last x pixels and last x slices
#  [ ] support to display at least two channels (including array channels)
#  [ ] must have 'new slice' call handable to modules or maybe some other implementation
#[ ] daq settings widget for scan modules
#  [ ] programatically construct widget so that changes can be made easily in future
#  [ ] accept parameters from array
#  [ ] object can be initialized by a scan gui and handed right back to daq control cleanly
#[ ] timing and communication
#  [ ] can do array, daq, or both
#    [ ] daq address method also communicates to array
#[ ] how to decide which array to load in
#  [ ] have a pulldown menu that allows you to choose between hardcoded options
#      simply point to files

### import #####################################################################

import sys
import time

import collections

import numpy as np

from PyQt4 import QtCore, QtGui

import project.project_globals as g
app = g.app.read()
import project.custom_widgets as custom_widgets
import project.ini_handler as ini

if not g.offline.read(): from PyDAQmx import *

### special globals ############################################################

class analog_channels():
    physical_asignments = None
    limits = None
    sample_indicies = None
analog_channels = analog_channels()

class array_detector_reference:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
array_detector_reference = array_detector_reference()

class busy(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=5000):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
busy = busy()

class data_busy(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=5000):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
data_busy = data_busy()

class digital_channels():
    physical_asignments = None
    limits = None
    sample_indicies = None
digital_channels = digital_channels()

class enqueued_actions(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.value = []
    def read(self):
        return self.value
    def push(self, value):  
        self.lock()
        self.value.append(value)
        self.unlock()
    def pop(self):
        self.lock()
        self.value = self.value[1:]
        self.unlock()
enqueued_actions = enqueued_actions()

class enqueued_data(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.value = []
    def read(self):
        return self.value
    def push(self, value):  
        self.lock()
        self.value.append(value)
        self.unlock()
    def pop(self):
        self.lock()
        self.value = self.value[1:]
        self.unlock()
enqueued_data = enqueued_data()

class last_samples(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=5000):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
last_samples = last_samples()

class last_analog_data(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=5000):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
last_analog_data = last_analog_data()

class us_per_sample:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):  
        self.value = value
us_per_sample = us_per_sample()

### gui globals ################################################################

import project.global_classes as gc

#daq
shots = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'Shots'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0)

#graph and big #
freerun = gc.boolean(initial_value = True)
tab_channel = gc.combo(['vai0', 'vai1', 'vai2', 'vai3', 'vai4'], ini = ['daq', 'DAQ', 'Tab channel'], import_from_ini = True, save_to_ini_at_shutdown = True)
tab_timescale = gc.combo(['Shots', 'Samples'], ini = ['daq', 'DAQ', 'Tab timescale'], import_from_ini = True, save_to_ini_at_shutdown = True)
tab_property = gc.combo(['Mean', 'Variance', 'Differential'], ini = ['daq', 'DAQ', 'Tab property'], import_from_ini = True, save_to_ini_at_shutdown = True)
tab_trigger = gc.combo(['TDG', 'Chopper (High)'], ini = ['daq', 'DAQ', 'Tab trigger'], import_from_ini = True, save_to_ini_at_shutdown = True)
tab_shots = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'Tab shots'], import_from_ini = True, save_to_ini_at_shutdown = True, min_value = 0, max_value = 1000, decimals = 0)

#channel timing
num_samples = gc.number(initial_value = np.nan, display = True, decimals = 0)
vai0_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai0 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai0_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai0 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai1_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai1 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai1_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai1 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai2_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai2 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai2_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai2 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai3_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai3 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai3_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai3 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai4_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai4 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vai4_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai4 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vdi0_first_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vdi0 first sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
vdi0_last_sample = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vdi0 last sample'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, min_value = 0, max_value = 160)
analog_channels.sample_indicies = [[vai0_first_sample.read(), vai0_last_sample.read()], [vai1_first_sample.read(), vai1_last_sample.read()], [vai2_first_sample.read(), vai2_last_sample.read()], [vai3_first_sample.read(), vai3_last_sample.read()], [vai4_first_sample.read(), vai4_last_sample.read()]]
digital_channels.sample_indicies = [[vdi0_first_sample.read(), vdi0_last_sample.read()]]

#analog channels
vai0_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai0 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
vai1_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai1 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
vai2_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai2 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
vai3_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai3 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
vai4_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vai4 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
analog_min = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'analog min'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, min_value = -10, max_value = 10)
analog_max = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'analog max'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, min_value = -10, max_value = 10)
analog_channels.physical_asignments = [vai0_channel.read(), vai1_channel.read(), vai2_channel.read(), vai3_channel.read(), vai4_channel.read()]
analog_channels.limits = [analog_min.read(), analog_max.read()]

#digital channels
vdi0_channel = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'vdi0 channel'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, max_value = 8)
digital_min = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'digital min'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, min_value = -10, max_value = 10)
digital_max = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'digital max'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, min_value = -10, max_value = 10)
digital_cutoff = gc.number(initial_value = np.nan, ini = ['daq', 'DAQ', 'digital cutoff'], import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, min_value = -10, max_value = 10)
digital_channels.physical_asignments = [vdi0_channel.read()]
analog_channels.limits = [digital_min.read(), digital_max.read(), digital_cutoff.read()]

#additional
seconds_since_last_task = gc.number(initial_value = np.nan, display = True, decimals = 3)
seconds_for_acquisition = gc.number(initial_value = np.nan, display = True, decimals = 3)


### dictionaries################################################################

channels = collections.OrderedDict()
channels['vai0'] = [0, [analog_channels, 'sample_indicies', 0], [analog_channels, 'limits']]
channels['vai1'] = [1, [analog_channels, 'sample_indicies', 1], [analog_channels, 'limits']]
channels['vai2'] = [2, [analog_channels, 'sample_indicies', 2], [analog_channels, 'limits']]
channels['vai3'] = [3, [analog_channels, 'sample_indicies', 3], [analog_channels, 'limits']]
channels['vai4'] = [4, [analog_channels, 'sample_indicies', 4], [analog_channels, 'limits']]
channels['vdi0'] = [5, [digital_channels, 'sample_indicies', 0], [digital_channels, 'limits']]

properties = collections.OrderedDict()
properties['Mean'] =         [0]
properties['Variance'] =     [1]
properties['Differential'] = [2]

### DAQ address#################################################################

class address(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        busy.write(True)
        if g.debug.read(): print 'daq dequeue:', method, inputs
        enqueued_actions.pop()
        getattr(self, str(method))(inputs) #method passed as qstring
        if not enqueued_actions.read(): 
            self.queue_emptied.emit()
            self.check_busy([])
            
    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        '''
        #simply check if additional actions are enqueued
        if enqueued_actions.read():
            time.sleep(0.1)
            busy.write(True)
        else:
            busy.write(False)
            
    def loop(self, inputs):
        while freerun.read():
            self.run_task([])
            
    def initialize(self, inputs):
        self.task_created = False
        self.previous_time = time.time()
        if g.debug.read(): print 'DAQ initializing'
        g.logger.log('info', 'DAQ initializing')
        if g.offline.read(): return
        self.create_task([])
    
    def create_task(self, inputs):
        if g.offline.read(): return
            
        #ensure previous task closed--------------------------------------------
        
        if self.task_created:
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            
        self.task_created = False
            
        #import variables locally (ensures they do not change during operation)-

        daq_analog_physical_channels =  [int(vai0_channel.read()), int(vai1_channel.read()), int(vai2_channel.read()), int(vai3_channel.read()), int(vai4_channel.read())]
        self.analog_min = analog_min.read()
        self.analog_max = analog_max.read()
        
        daq_digital_physical_channels = [int(vdi0_channel.read())]
        self.digital_min = digital_min.read()
        self.digital_max = digital_max.read()
        self.digital_cutoff = digital_cutoff.read()
        
        self.shots = long(shots.read())
        
        self.num_analog_channels = len(daq_analog_physical_channels)
        self.num_digital_channels = len(daq_digital_physical_channels)
        self.num_channels = self.num_analog_channels + self.num_digital_channels
        
        #calculate the number of 'virtual samples' to take----------------------
        
        conversions_per_second = 1000000. #a property of the DAQ card
        shots_per_second = 1100. #from laser (max value - if there are more shots than this we are in big trouble!!!)
        self.virtual_samples = int(conversions_per_second/(shots_per_second*self.num_channels))
        num_samples.write(self.virtual_samples)
        us_per_sample.write((1/conversions_per_second)*10**6)
        
        #create task------------------------------------------------------------
        
        try:
            self.task_handle = TaskHandle()
            self.read = int32()
            DAQmxCreateTask('',byref(self.task_handle))
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in task creation', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            return

        #initialize channels----------------------------------------------------

        #The daq is addressed in a somewhat non-standard way. A total of ~1000 
        #virtual channels are initialized (depends on DAQ speed and laser rep 
        #rate). These virtual channels are evenly distributed over the physical
        #channels addressed by the software. When the task is run, it round
        #robins over all the virtual channels, essentially oversampling the
        #analog physical channels.

        #self.virtual_samples contains the oversampling factor.

        #Each virtual channel must have a unique name.

        #The sample clock is supplied by the laser output trigger.

        try:
            
            total_virtual_channels = 0
            
            for _ in range(self.virtual_samples):
                for channel in daq_analog_physical_channels:
                    channel_name = 'channel_' + str(total_virtual_channels).zfill(3)
                    DAQmxCreateAIVoltageChan(self.task_handle,                #task handle
                                             'Dev1/ai%i'%channel,             #physical chanel
                                             channel_name,                    #name to assign to channel
                                             DAQmx_Val_Diff,                  #the input terminal configuration
                                             self.analog_min,self.analog_max, #minVal, maxVal
                                             DAQmx_Val_Volts,                 #units 
                                             None)                            #custom scale
                    total_virtual_channels += 1
                                             
                for channel in daq_digital_physical_channels:
                    channel_name = 'channel_' + str(total_virtual_channels).zfill(3)
                    DAQmxCreateAIVoltageChan(self.task_handle,                  #task handle
                                             'Dev1/ai%i'%channel,               #physical chanel
                                             channel_name,                      #name to assign to channel
                                             DAQmx_Val_Diff,                    #the input terminal configuration
                                             self.digital_min,self.digital_max, #minVal, maxVal
                                             DAQmx_Val_Volts,                   #units 
                                             None)                              #custom scale
                    total_virtual_channels += 1
                    
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in virtual channel creation', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            return
        
        #define timing----------------------------------------------------------
      
        try:
            DAQmxCfgSampClkTiming(self.task_handle,      #task handle
                                  '/Dev1/PFI0',          #sorce terminal
                                  1000.0,                #sampling rate (samples per second per channel) (float 64) (in externally clocked mode, only used to initialize buffer)
                                  DAQmx_Val_Rising,      #acquire samples on the rising edges of the sample clock
                                  DAQmx_Val_FiniteSamps, #acquire a finite number of samples
                                  self.shots)            #samples per channel to acquire (unsigned integer 64)         
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in timing definition', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            return
            
        #create arrays for task to fill-----------------------------------------

        self.samples = np.zeros(self.shots*self.virtual_samples*self.num_channels, dtype=numpy.float64)
        self.samples_len = len(self.samples) #do not want to call for every acquisition
        
        self.analog_data = np.zeros([self.num_analog_channels, 3])
            
        #finish-----------------------------------------------------------------
            
        self.task_created = True
            
    def run_task(self, inputs):
        if g.offline.read():            
            #fake readings
            out = np.random.rand(self.shots, self.virtual_samples, self.num_channels)
            self.analog_data[i, 0] = np.mean(out[:, 0, i]) #average
            self.analog_data[i, 1] = np.var(out[:, 0, i]) #variance
            self.analog_data[i, 2] = np.mean(out[:, 0, i]*diff_weights) #differential
            last_samples.write(out)
            last_analog_data.write(self.analog_data)
            self.update_ui.emit()
            time.sleep(self.shots / 1000)
            seconds_since_last_task.write(time.time() - self.previous_time)
            self.previous_time = time.time()            
        
        if not self.task_created: return
        start_time = time.time()
        
        array_detector = array_detector_reference.read()
        
        #tell array detector to begin-------------------------------------------
        
        array_detector.control.read()   
        
        #collect samples array--------------------------------------------------
        
        try:
            DAQmxStartTask(self.task_handle)
        
            DAQmxReadAnalogF64(self.task_handle,            #task handle
                               self.shots,                  #number of samples per channel
                               10.0,                        #timeout (seconds) for each read operation
                               DAQmx_Val_GroupByScanNumber, #fill mode (specifies whether or not the samples are interleaved)
                               self.samples,                #read array
                               self.samples_len,            #size of the array, in samples, into which samples are read
                               byref(self.read),            #reference of thread
                               None)                        #reserved by NI, pass NULL (?)
    
            DAQmxStopTask(self.task_handle)
        
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in timing definition', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            
        #wait for array detector to finish--------------------------------------
            
        array_detector.control.wait_until_done()
            
        seconds_for_acquisition.write(time.time() - start_time)
            
        #do math----------------------------------------------------------------
        
        out = np.copy(self.samples)
        out.shape = (self.shots, self.virtual_samples, self.num_channels)
        
        #'digitize' digital channels
        for i in range(self.num_analog_channels, self.num_analog_channels+self.num_digital_channels):
            low_value_indicies = out[:, :, i] < self.digital_cutoff
            high_value_indicies = out[:, :, i] >= self.digital_cutoff
            out[low_value_indicies, i] = 0
            out[high_value_indicies, i] = 1
        
        #create differential multiplication array
        chopper_index = 5
        diff_weights = out[:, 0, chopper_index]
        diff_weights[out[:, 0, chopper_index] == 0] = -1
        diff_weights[out[:, 0, chopper_index] == 1] = 1
        
        #get statistics
        for i in range(self.num_analog_channels):
            self.analog_data[i, 0] = np.mean(out[:, 0, i]) #average
            self.analog_data[i, 1] = np.var(out[:, 0, i]) #variance
            self.analog_data[i, 2] = np.mean(out[:, 0, i]*diff_weights) #differential
        
        #export data------------------------------------------------------------        
        
        last_samples.write(out)
        last_analog_data.write(self.analog_data)
        self.update_ui.emit()
        
        #update timer-----------------------------------------------------------
        
        seconds_since_last_task.write(time.time() - self.previous_time)
        self.previous_time = time.time()
            
    def shutdown(self, inputs):
         '''
         cleanly shutdown
         '''
         if g.offline.read(): return
         
         if self.task_created:
             DAQmxStopTask(self.task_handle)
             DAQmxClearTask(self.task_handle)

#begin address object in seperate thread
address_thread = QtCore.QThread()
address_obj = address()
address_obj.moveToThread(address_thread)
address_thread.start()

#create queue to communiate with address thread
queue = QtCore.QMetaObject()
def q(method, inputs = []):
    #add to friendly queue list 
    enqueued_actions.push([method, time.time()])
    #busy
    if not busy.read(): busy.write(True)
    #send Qt SIGNAL to address thread
    queue.invokeMethod(address_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))
    
### DATA address################################################################
    
class data(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        if g.debug.read(): print 'data dequeue:', method, inputs
        getattr(self, str(method))(inputs) #method passed as qstring
        enqueued_data.pop()
        if not enqueued_data.read(): 
            self.queue_emptied.emit()
            self.check_busy([])
            
    def check_busy(self, inputs):
        '''
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        '''
        if enqueued_data.read():
            time.sleep(0.1)
            busy.write(True)
        else:
            busy.write(False)
            
    def create_dat(self, inputs):
        '''
        dat headers
        name
        daq parameters
        dimensions
        
        '''
        #generate header
        mydict = {"foo":[1,2], "bar":[3,4], "asdf":[5,6]}
        header_items = ['file created ' + time.strftime('%Y.%m.%d %H:%M:%S'), 'columns [a, b, c, d]', str(mydict)]
        header_str = ''
        for item in header_items: header_str += item + '\n' 
        header_str[-2]
        np.savetxt(output_file, [], header=header_str[:-1])
            
    def write_dat(self, inputs):
        '''
        dat columns:                                  \n
        00) index                                     \n
        01) time (seconds since epoch)                \n
        02) OPA1 shutter state (0 = closed, 1 = open) \n
        03) OPA1 color (nm)                           \n
        04) OPA2 shutter state (0 = closed, 1 = open) \n
        05) OPA2 color (nm)                           \n
        06) ND1 position (%T)                         \n
        07) ND1 position (steps)                      \n
        08) ND2 position (%T)                         \n
        09) ND2 position (steps)                      \n
        10) ND3 position (%T)                         \n
        11) ND3 position (steps)                      \n
        12) D1 position (fs)                          \n
        13) D1 position (mm)                          \n
        14) D2 position (fs)                          \n
        15) D2 position (mm)                          \n
        16) D3 position (fs)                          \n
        17) D3 position (mm)                          \n
        18) mono color (nm)                           \n
        19) array dimension 0 map value               \n
        20) array dimension 1 map value               \n
        21) AI0                                       \n
        22) AI1                                       \n
        23) AI2                                       \n
        24) AI3                                       \n
        25) AI4                                       \n
        26) array value                               \n
        '''
        import os
        import time
        import numpy as np

        dat_file = open(output_file, 'a')
        my_row = np.full(26, np.nan)
        my_row[0] = i+1
        my_row[1] = time.time()
        my_row[2] = 1
        my_row[3] = 1300
        my_row[4] = 1
        my_row[5] = 1300
        np.savetxt(dat_file, my_row, fmt='%8.4f', delimiter='\t', newline = '\t')
        dat_file.write('\n')
        dat_file.close()

    def create_fit(self, inputs):
        pass
        
    def write_fit(self, inputs):
        '''
        fit columns:                                  \n
        00) index                                     \n
        01) time (seconds since epoch)                \n
        '''
        pass
           
    def initialize(self, inputs):
        pass
                      
    def shutdown(self, inputs):
         #cleanly shut down
         #all hardware classes must have this
         pass

#begin address object in seperate thread
data_thread = QtCore.QThread()
data_obj = data()
data_obj.moveToThread(data_thread)
data_thread.start()

#create queue to communiate with address thread
data_queue = QtCore.QMetaObject()
def data_q(method, inputs = []):
    #add to friendly queue list 
    enqueued_actions.push([method, time.time()])
    #busy
    if not busy.read(): busy.write(True)
    #send Qt SIGNAL to address thread
    data_queue.invokeMethod(data_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))

### control#####################################################################

class control():
    
    def __init__(self):
        self.ready = False
        print 'control.__init__'
        g.shutdown.add_method(self.shutdown)
        self.initialize_hardware()
        #setup freerun
        freerun.updated.connect(lambda: q('loop'))
        if freerun.read(): q('loop')
        #other controls
        shots.updated.connect(self.update_task)
        
    def initialize_hardware(self):
        q('initialize')
        #tell the array to begin initialization
        import InGaAs_array_detector.InGaAs as array_detector
        array_detector_reference.write(array_detector)
        
        
    def update_task(self):
        if freerun:
            return_to_freerun = True
            freerun.write(False)
            self.wait_until_done()
        else: return_to_freerun = False
        q('create_task')
        if return_to_freerun: freerun.write(True)
    
    def wait_until_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        '''
        start_time = time.time()
        while busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_actions.read(): q('check_busy')
                busy.wait_for_update()
            else: 
                g.logger.log('warning', 'DAQ dait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
            
    def wait_until_data_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when data_busy.wait_for_update fires
        '''
        start_time = time.time()
        while data_busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_data.read(): data_q('check_busy')
                data_busy.wait_for_update()
            else: 
                g.logger.log('warning', 'Data wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
                
    def shutdown(self):   
        #log
        if g.debug.read(): print 'daq shutting down'
        g.logger.log('info', 'DAQ shutdown')
        #shutdown other threads
        q('shutdown')
        data_q('shutdown')
        self.wait_until_done()
        self.wait_until_data_done()
        address_thread.quit()
        data_thread.quit()
        #close gui
        gui.stop()
    
control = control()

### gui#########################################################################

class widget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = custom_widgets.input_table()
        input_table.add('DAQ', None)
        self.shots = gc.number(initial_value = 200, decimals = 0)
        input_table.add('Shots', self.shots)
        layout.addWidget(input_table)
        
class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__
        #control.wait_until_done()
        address_obj.update_ui.connect(self.update)
        data_obj.update_ui.connect(self.update)
        tab_channel.updated.connect(self.update)
        tab_timescale.updated.connect(self.update)
        tab_property.updated.connect(self.update)
        tab_trigger.updated.connect(self.update)
        tab_shots.updated.connect(self.update)
        self.create_daq_frame()
        self.create_current_frame()
        
    def create_daq_frame(self):
        
        #get parent widget------------------------------------------------------
        
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        #parent_widget.layout().setContentsMargins(0, 5, 0, 0)
        layout = parent_widget.layout()
        
        #display area-----------------------------------------------------------

        #container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        #big number
        self.big_display = custom_widgets.spinbox_as_display(font_size = 100)        
        display_layout.addWidget(self.big_display)
        
        #plot
        self.plot_widget = custom_widgets.plot_1D()
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_widget.set_labels(ylabel = 'volts')
        self.plot_green_line = self.plot_widget.add_line(color = 'g')   
        self.plot_red_line = self.plot_widget.add_line(color = 'r')   
        display_layout.addWidget(self.plot_widget)
        
        #value display frame
        frame_frame_widget = QtGui.QWidget()
        frame_frame_widget.setLayout(QtGui.QVBoxLayout())
        frame_frame_widget.layout().addStretch(1)
        frame_widget = QtGui.QWidget()
        frame_widget.setLayout(QtGui.QGridLayout())
        frame_widget.layout().setMargin(0)
        value_frame_layout = frame_widget.layout()
        rlabels = ['vai0', 'vai1', 'vai2', 'vai3', 'vai4']
        clabels = ['Mean', 'Variance', 'Differential']
        label_StyleSheet = 'QLabel{color: custom_color; font: bold 14px;}'.replace('custom_color', g.colors_dict.read()['text_light'])
        self.grid_displays = []        
        for i in range(5):
            label = QtGui.QLabel(rlabels[i])
            label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
            label.setStyleSheet(label_StyleSheet)
            value_frame_layout.addWidget(label, i+1, 0)
            grid_displays_row = []
            for j in range(3):
                #display
                display = custom_widgets.spinbox_as_display()
                value_frame_layout.addWidget(display, i+1, j+1)
                grid_displays_row.append(display)
            self.grid_displays.append(grid_displays_row)
        for j in range(3):
            #label
            label = QtGui.QLabel(clabels[j])
            label.setAlignment(QtCore.Qt.AlignRight)
            label.setStyleSheet(label_StyleSheet)
            value_frame_layout.addWidget(label, 0, j+1)
        value_frame_layout
        frame_frame_widget.layout().addWidget(frame_widget)
        display_layout.addWidget(frame_frame_widget)
        
        #streach
        spacer = custom_widgets.vertical_spacer()
        spacer.add_to_layout(display_layout)
        
        #vertical line----------------------------------------------------------

        line = custom_widgets.line('V')      
        layout.addWidget(line)
        
        #settings area----------------------------------------------------------
        
        #container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = custom_widgets.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
                
        #input table one
        input_table = custom_widgets.input_table()
        input_table.add('Display', None)
        input_table.add('Shots', shots)
        input_table.add('Free run', freerun)
        input_table.add('Channel', tab_channel)
        input_table.add('Property', tab_property)
        input_table.add('Timescale', tab_timescale)        
        input_table.add('Trigger', tab_trigger)
        input_table.add('Shots', tab_shots)        
        settings_layout.addWidget(input_table)
        g.module_control.disable_when_true(input_table)
        
        #horizontal line
        line = custom_widgets.line('H')      
        settings_layout.addWidget(line)
        
        #input table two
        input_table = custom_widgets.input_table()
        input_table.add('Channel Timing', None)
        input_table.add('Samples', num_samples)
        input_table.add('vai0 first sample', vai0_first_sample)
        input_table.add('vai0 last sample', vai0_last_sample)
        input_table.add('vai1 first sample', vai1_first_sample)
        input_table.add('vai1 last sample', vai1_last_sample)
        input_table.add('vai2 first sample', vai2_first_sample)
        input_table.add('vai2 last sample', vai2_last_sample)
        input_table.add('vai3 first sample', vai3_first_sample)
        input_table.add('vai3 last sample', vai3_last_sample)
        input_table.add('vai4 first sample', vai4_first_sample)
        input_table.add('vai4 last sample', vai4_last_sample)
        input_table.add('vdi0 first sample', vdi0_first_sample)
        input_table.add('vdi0 last sample', vdi0_last_sample)
        input_table.add('Analog Channels', None)
        input_table.add('vai0', vai0_channel)
        input_table.add('vai1', vai1_channel)
        input_table.add('vai2', vai2_channel)
        input_table.add('vai3', vai3_channel)
        input_table.add('vai4', vai4_channel)
        input_table.add('Minimum', analog_min)
        input_table.add('Maximum', analog_max)
        input_table.add('Digital Channels', None)
        input_table.add('vdi0', vdi0_channel)
        input_table.add('Minimum', digital_min)
        input_table.add('Maximum', digital_max)
        input_table.add('Cutoff', digital_cutoff)
        settings_layout.addWidget(input_table)
        g.module_control.disable_when_true(input_table)        
        
        #set button
        apply_channels_button = custom_widgets.set_button('APPLY CHANNEL SETTINGS')        
        settings_layout.addWidget(apply_channels_button)
        apply_channels_button.clicked.connect(self.on_apply_channels)
        g.module_control.disable_when_true(apply_channels_button)
        
        #horizontal line
        line = custom_widgets.line('H')      
        settings_layout.addWidget(line)
        
        #debug tools
        input_table = custom_widgets.input_table()
        input_table.add('Debug', None)
        input_table.add('Loop time', seconds_since_last_task)
        input_table.add('Acquisiton time', seconds_for_acquisition)
        settings_layout.addWidget(input_table)
        g.module_control.disable_when_true(input_table)
        
        #streach
        settings_layout.addStretch(1)
        
    def create_current_frame(self):
        
        #get parent widget------------------------------------------------------
        
        parent_widget = g.current_slice_widget.read()
        parent_widget.setLayout(QtGui.QVBoxLayout())
        parent_widget.layout().setMargin(5)
        
        layout = parent_widget.layout()
        
        #fill in----------------------------------------------------------------
        
        line_edit = QtGui.QLineEdit()
        line_edit.setText('current')
        
        layout.addWidget(line_edit)
        
    def on_apply_channels(self):
        analog_channels.sample_indicies = [[vai0_first_sample.read(), vai0_last_sample.read()], [vai1_first_sample.read(), vai1_last_sample.read()], [vai2_first_sample.read(), vai2_last_sample.read()], [vai3_first_sample.read(), vai3_last_sample.read()], [vai4_first_sample.read(), vai4_last_sample.read()]]
        digital_channels.sample_indicies = [[vdi0_first_sample.read(), vdi0_last_sample.read()]]
        analog_channels.physical_asignments = [vai0_channel.read(), vai1_channel.read(), vai2_channel.read(), vai3_channel.read(), vai4_channel.read()]
        analog_channels.limits = [analog_min.read(), analog_max.read()]
        digital_channels.physical_asignments = [vdi0_channel.read()]
        analog_channels.limits = [digital_min.read(), digital_max.read(), digital_cutoff.read()]
        q('create_task')        
        
    def update(self):
        
        #import globals locally-------------------------------------------------
        
        channel_index = channels[tab_channel.read()][0]
        
        property_index = properties[tab_property.read()][0]

        channel_sample_indicies_list = channels[tab_channel.read()][1]
        channel_sample_indicies = getattr(channel_sample_indicies_list[0], channel_sample_indicies_list[1])[channel_sample_indicies_list[2]]
        
        channel_limits_list =  channels[tab_channel.read()][2]
        channel_limits = getattr(channel_limits_list[0], channel_limits_list[1])
        
        #plot-------------------------------------------------------------------
            
        #line.hide()
        if not last_samples.read() == None:
            if tab_timescale.read() == 'Shots':
                #gui update
                tab_trigger.set_disabled(True)
                tab_shots.set_disabled(True)
                self.plot_widget.set_labels(xlabel = 'shot index')
                self.plot_green_line.hide()
                self.plot_red_line.hide()
                #plot
                data = last_samples.read()[:, 0, channel_index]
                x = np.linspace(0, len(data), len(data))                
                data = np.array([x, data])
                self.plot_curve.clear()
                self.plot_curve.setData(data[0], data[1])
            elif tab_timescale.read() == 'Samples':
                #gui update
                tab_trigger.set_disabled(False)
                tab_shots.set_disabled(False)
                self.plot_widget.set_labels(xlabel = 'microseconds since first trigger')
                self.plot_green_line.show()
                self.plot_red_line.show()
                #get data
                num_shots = int(tab_shots.read())
                index = 0
                if tab_trigger.read() == 'Chopper (High)':
                    for i in range(num_shots):
                        if last_samples.read()[i, 0, 5] == 1: break
                        index += 1
                data = last_samples.read()[index:index+num_shots, :, channel_index].flatten()
                x = numpy.zeros(len(data))
                for i in range(num_shots*int(num_samples.read())):
                    offset = us_per_sample.read()*channel_index
                    shot_count, sample_count = divmod(i, num_samples.read())
                    #print shot_count, sample_count
                    x[i] = offset + shot_count*1000 + sample_count*(us_per_sample.read()*6)
                #plot
                self.plot_green_line.setValue(offset + channel_sample_indicies[0]*us_per_sample.read())
                self.plot_red_line.setValue(offset + channel_sample_indicies[1]*us_per_sample.read()*6)
                data = np.array([x, data])
                self.plot_curve.clear()
                self.plot_curve.setData(data[0], data[1])
                
        #data readout-----------------------------------------------------------
            
        if not last_analog_data.read() == None:
            analog_reading = last_analog_data.read()
            for i in range(5):
                for j in range(3):
                    display = self.grid_displays[i][j]
                    display.setValue(analog_reading[i, j])
            self.big_display.setValue(analog_reading[channel_index, property_index])
            
    def stop(self):
        pass
        
gui = gui()


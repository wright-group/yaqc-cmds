### import ####################################################################

import os
import sys
import time

import collections

import numpy as np

import scipy

from PyQt4 import QtCore, QtGui

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as custom_widgets
import project.ini_handler as ini
import opas.opas as opas
import spectrometers.spectrometers as spectrometers
import delays.delays as delays
hardware_modules = [opas, spectrometers, delays]
app = g.app.read()
main_dir = g.main_dir.read()
daq_ini = ini.daq

if not g.offline.read(): 
    from PyDAQmx import *


### special objects ###########################################################


class analog_channels():
    physical_asignments = None
    limits = None
    sample_indicies = None
analog_channels = analog_channels()

axes = pc.Mutex()

array_detector_reference = pc.Mutex()

busy = pc.Busy()

class CurrentSlice(QtCore.QMutex):
    
    def __init__(self):
        '''
        a list of numpy arrays
        '''
        QtCore.QMutex.__init__(self)
        self.value = []
        self.col = 'index'
        
    def col(self, col):
        '''
        give the slice a col, corresponding to key in data_cols
        '''
        self.col = col
        
    def read(self):
        return self.value
        
    def append(self, row):
        self.lock()
        self.value.append(row)
        self.unlock()
        
    def clear(self):
        self.lock()
        self.value = []
        self.unlock()        
        
current_slice = CurrentSlice()  # a list of numpy arrays

data_busy = pc.Busy()

data_path = pc.Mutex()

class digital_channels():
    physical_asignments = None
    limits = None
    sample_indicies = None
digital_channels = digital_channels()

enqueued_actions = pc.Enqueued()

enqueued_data = pc.Enqueued()

fit_path = pc.Mutex()

ignore = pc.Mutex()

last_samples = pc.Mutex()

last_analog_data = pc.Mutex()

origin = pc.Mutex()

us_per_sample = pc.Mutex()





### gui objects ###############################################################


#daq
shots = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='Shots', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0)
index = pc.Number(initial_value=0)

#graph and big #
freerun = pc.Bool(initial_value=True)
tab_channel = pc.Combo(['vai0', 'vai1', 'vai2', 'vai3', 'vai4'], ini=daq_ini, section='DAQ', option='Tab channel', import_from_ini = True, save_to_ini_at_shutdown = True)
tab_timescale = pc.Combo(['Shots', 'Samples'], ini=daq_ini, section='DAQ', option='Tab timescale', import_from_ini = True, save_to_ini_at_shutdown = True)
tab_property = pc.Combo(['Mean', 'Variance', 'Differential'], ini=daq_ini, section='DAQ', option='Tab property', import_from_ini = True, save_to_ini_at_shutdown = True)
tab_trigger = pc.Combo(['TDG', 'Chopper (High)'], ini=daq_ini, section='DAQ', option='Tab trigger', import_from_ini = True, save_to_ini_at_shutdown = True)
tab_shots = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='Tab shots', import_from_ini = True, save_to_ini_at_shutdown = True, limits=pc.NumberLimits(0, 1000, None), decimals = 0)

#channel timing
num_samples = pc.Number(initial_value=np.nan, display=True, decimals=0)
vai0_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai0 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai0_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai0 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai1_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai1 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai1_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai1 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai2_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai2 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai2_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai2 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai3_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai3 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai3_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai3 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai4_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai4 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vai4_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vai4 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vdi0_first_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vdi0 first sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
vdi0_last_sample = pc.Number(initial_value=np.nan, ini=daq_ini, section='DAQ', option='vdi0 last sample', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 160, None))
analog_channels.sample_indicies = [[vai0_first_sample.read(), vai0_last_sample.read()], [vai1_first_sample.read(), vai1_last_sample.read()], [vai2_first_sample.read(), vai2_last_sample.read()], [vai3_first_sample.read(), vai3_last_sample.read()], [vai4_first_sample.read(), vai4_last_sample.read()]]
digital_channels.sample_indicies = [[vdi0_first_sample.read(), vdi0_last_sample.read()]]

#analog channels
vai0_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vai0 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
vai1_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vai1 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
vai2_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vai2 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
vai3_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vai3 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
vai4_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vai4 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
analog_min = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='analog min', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, limits=pc.NumberLimits(-10, 10, None))
analog_max = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='analog max', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, limits=pc.NumberLimits(-10, 10, None))
analog_channels.physical_asignments = [vai0_channel.read(), vai1_channel.read(), vai2_channel.read(), vai3_channel.read(), vai4_channel.read()]
analog_channels.limits = [analog_min.read(), analog_max.read()]

#digital channels
vdi0_channel = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='vdi0 channel', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0, limits=pc.NumberLimits(0, 8, None))
digital_min = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='digital min', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, limits=pc.NumberLimits(-10, 10, None))
digital_max = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='digital max', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, limits=pc.NumberLimits(-10, 10, None))
digital_cutoff = pc.Number(initial_value = np.nan, ini=daq_ini, section='DAQ', option='digital cutoff', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 3, limits=pc.NumberLimits(-10, 10, None))
digital_channels.physical_asignments = [vdi0_channel.read()]
analog_channels.limits = [digital_min.read(), digital_max.read(), digital_cutoff.read()]

#additional
seconds_since_last_task = pc.Number(initial_value = np.nan, display = True, decimals = 3)
seconds_for_acquisition = pc.Number(initial_value = np.nan, display = True, decimals = 3)


### dictionaries ##############################################################


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

# column dictionaries
data_cols = pc.Mutex()
fit_cols = pc.Mutex()


### DATA address ##############################################################


class Data(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        if g.debug.read(): print 'data dequeue:', method
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
            time.sleep(0.01)
            data_busy.write(True)
        else:
            time.sleep(0.01)
            data_busy.write(False)
            
    def create_data(self, inputs):
        self.file_timestamp = wt.kit.get_timestamp()
        data_path.write(os.path.join(main_dir, 'data', self.file_timestamp + '.data'))
        header_str = self.make_header(data_cols.read())
        np.savetxt(data_path.read(), [], header=header_str)
        
    def create_fit(self, inputs):
        # create fit must always be called after create data
        fit_path.write(os.path.join(main_dir, 'data', self.file_timestamp + ' fitted.data'))
        header_str = self.make_header(fit_cols.read())
        np.savetxt(fit_path.read(), [], header=header_str)    
        
    def fit(self, inputs):
        # functions
        def gaussian(p, x):
            '''
            p = [amplitude, center, FWHM, offset]
            '''
            print p
            a, b, c, d = p
            return a*np.exp(-(x-b)**2/(2*np.abs(c/(2*np.sqrt(2*np.log(2))))**2))+d
        def residuals(p, y, x):
            return y - gaussian(p, x)
        # inputs
        xkey = inputs[0]
        zkey = inputs[1]
        data = np.array(inputs[2])
        xcol = data_cols.read()[xkey]['index']
        zcol = data_cols.read()[zkey]['index']
        xi = data[:, xcol]
        zi = data[:, zcol]
        # guess
        amplitude_guess = zi.max() - zi.min()
        center_guess = xi[np.where(zi == zi.max())]
        FWHM_guess = abs(xi[5] - xi[0])
        offset_guess = zi.min()
        p0 = [amplitude_guess, center_guess, FWHM_guess, offset_guess]
        # fit
        from scipy import optimize
        out = optimize.leastsq(residuals, p0, args=(zi, xi))[0]
        # assemble array
        arr = np.full(len(fit_cols.read()), np.nan)
        for col in fit_cols.read():
            index = fit_cols.read()[col]['index']
            if col == 'amplitude':
                arr[index] = out[0]
            elif col == 'center':
                arr[index] = out[1]
            elif col == 'FWHM':
                arr[index] = out[2]
            elif col == 'offset':
                arr[index] = out[3]
            elif col == xcol:
                arr[index] = np.nan
            else:
                # it's a hardware column
                arr[index] = data[0, index]
        # write
        self.write_fit(arr)
        
    def make_header(self, cols):
        # generate header
        units_list = [col['units'] for col in cols.values()]
        tolerance_list = [col['tolerance'] for col in cols.values()]
        label_list = [col['label'] for col in cols.values()]
        name_list = cols.keys()
        # strings need extra apostrophes and everything needs to be string
        for lis in [units_list, tolerance_list, label_list, name_list]:
            for i in range(len(lis)):
                if type(lis[i]) == str:       
                    lis[i] = '\'' + lis[i] + '\''
                else:
                    lis[i] = str(lis[i])
        header_items = ['file created:' + '\t' + '\'' + self.file_timestamp + '\'']
        header_items += ['origin:' + '\t' + '\'' + origin.read() + '\'']
        header_items += ['axes:' + '\t' + str(axes.read())]
        header_items += ['ignore:' + '\t' + str(ignore.read())]
        header_items += ['units: ' + '\t'.join(units_list)]
        header_items += ['tolerance: ' + '\t'.join(tolerance_list)]
        header_items += ['label: ' + '\t'.join(label_list)]
        header_items += ['name: ' + '\t'.join(name_list)]    
        # add header string
        header_str = ''
        for item in header_items:
            header_str += item + '\n'
        header_str = header_str[:-1]  # remove final newline charachter
        return header_str
            
    def write_data(self, inputs):
        data_file = open(data_path.read(), 'a')
        np.savetxt(data_file, inputs, fmt='%8.6f', delimiter='\t', newline = '\t')
        data_file.write('\n')
        data_file.close()
        
    def write_fit(self, inputs):
        data_file = open(fit_path.read(), 'a')
        np.savetxt(data_file, inputs, fmt='%8.6f', delimiter='\t', newline = '\t')
        data_file.write('\n')
        data_file.close()

    def initialize(self, inputs):
        pass
                      
    def shutdown(self, inputs):
        #cleanly shut down
        #all hardware classes must have this
        pass

#begin address object in seperate thread
data_thread = QtCore.QThread()
data_obj = Data()
data_obj.moveToThread(data_thread)
data_thread.start()

#create queue to communiate with address thread
data_queue = QtCore.QMetaObject()
def data_q(method, inputs = []):
    #add to friendly queue list 
    enqueued_data.push([method, time.time()])
    #busy
    data_busy.write(True)
    #send Qt SIGNAL to address thread
    data_queue.invokeMethod(data_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))


### DAQ address ###############################################################


class DAQ(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    running = False
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        #busy.write(True)
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
            time.sleep(0.01)
            busy.write(True)
        elif self.running:
            time.sleep(0.01)
            busy.write(True)
        else:
            busy.write(False)
            
    def loop(self, inputs):
        while freerun.read():
            self.run_task([False])
            
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
        
        # calculate the number of 'virtual samples' to take -------------------
        
        conversions_per_second = 1000000. # a property of the DAQ card
        shots_per_second = 1100. # from laser (max value - if there are more shots than this we are in big trouble!!!)
        self.virtual_samples = int(conversions_per_second/(shots_per_second*self.num_channels))
        num_samples.write(self.virtual_samples)
        us_per_sample.write((1/conversions_per_second)*10**6)
        
        # create task ---------------------------------------------------------
        
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

        # initialize channels -------------------------------------------------

        # The daq is addressed in a somewhat non-standard way. A total of ~1000 
        # virtual channels are initialized (depends on DAQ speed and laser rep 
        # rate). These virtual channels are evenly distributed over the physical
        # channels addressed by the software. When the task is run, it round
        # robins over all the virtual channels, essentially oversampling the
        # analog physical channels.

        # self.virtual_samples contains the oversampling factor.

        # Each virtual channel must have a unique name.

        # The sample clock is supplied by the laser output trigger.

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
        '''
        inputs[0] bool save
        '''

        self.running = True  
        self.check_busy([])
        self.update_ui.emit()

        self.save = inputs[0]
        
        if g.offline.read():            
            # fake readings
            pass          
        
        if not self.task_created: return
        start_time = time.time()
        
        #array_detector = array_detector_reference.read()
        
        # tell array detector to begin ----------------------------------------
        
        #array_detector.control.read()   
        
        # collect samples array -----------------------------------------------
        
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
            
        # wait for array detector to finish -----------------------------------
            
        #array_detector.control.wait_until_done()
            
        seconds_for_acquisition.write(time.time() - start_time)
            
        # do math -------------------------------------------------------------
        
        out = np.copy(self.samples)
        out.shape = (self.shots, self.virtual_samples, self.num_channels)
        
        # 'digitize' digital channels
        for i in range(self.num_analog_channels, self.num_analog_channels+self.num_digital_channels):
            low_value_indicies = out[:, :, i] < self.digital_cutoff
            high_value_indicies = out[:, :, i] >= self.digital_cutoff
            out[low_value_indicies, i] = 0
            out[high_value_indicies, i] = 1
        
        # create differential multiplication array
        chopper_index = 5
        diff_weights = out[:, 0, chopper_index]
        diff_weights[out[:, 0, chopper_index] == 0] = -1
        diff_weights[out[:, 0, chopper_index] == 1] = 1
        
        # get statistics
        for i in range(self.num_analog_channels):
            self.analog_data[i, 0] = np.mean(out[:, 0, i])  # average
            self.analog_data[i, 1] = np.var(out[:, 0, i])  # variance
            self.analog_data[i, 2] = np.mean(out[:, 0, i]*diff_weights)  # differential
        
        # export data ---------------------------------------------------------        
        
        last_samples.write(out)
        last_analog_data.write(self.analog_data)
        self.update_ui.emit()
        
        if self.save:
            row = np.full(len(data_cols.read()), np.nan)
            row[0] = index.read()
            row[1] = time.time()
            i = 2
            # hardware
            for module in hardware_modules:
                for hardware in module.hardwares:
                    for key in hardware.recorded:
                        out_units = hardware.recorded[key][1]
                        if out_units is None:
                            row[i] = hardware.recorded[key][0].read()
                        else:                     
                            row[i] = hardware.recorded[key][0].read(out_units)
                        i += 1
            # values
            for channel_idx in range(5):
                for property_idx in range(3):
                    row[i] = self.analog_data[channel_idx, property_idx]
                    i += 1
            # output
            data_q('write_data', [row])
            current_slice.append(row)
            
            # index
            index.write(index.read()+1)
        
        # update timer --------------------------------------------------------
        
        seconds_since_last_task.write(time.time() - self.previous_time)
        self.previous_time = time.time()
        
        self.running = False
            
    def shutdown(self, inputs):
         '''
         cleanly shutdown
         '''
         if g.offline.read(): return
         
         if self.task_created:
             DAQmxStopTask(self.task_handle)
             DAQmxClearTask(self.task_handle)

# begin address object in seperate thread
address_thread = QtCore.QThread()
address_obj = DAQ()
address_obj.moveToThread(address_thread)
address_thread.start()

# create queue to communiate with address thread
queue = QtCore.QMetaObject()
def q(method, inputs = []):
    # add to friendly queue list 
    enqueued_actions.push([method, time.time()])
    # busy
    #busy.unlock()
    busy.write(True)
    # send Qt SIGNAL to address thread    
    queue.invokeMethod(address_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))


### control####################################################################


class Control():
    
    def __init__(self):
        self.ready = False
        print 'control.__init__'
        g.shutdown.add_method(self.shutdown)
        self.initialize_hardware()
        # setup freerun
        freerun.updated.connect(self.freerun)
        self.freerun()
        # other controls
        shots.updated.connect(self.update_task)
        g.main_window.read().module_control.connect(self.module_control_update)
        
    def acquire(self):
        q('run_task', inputs=[True])
        
    def fit(self, xkey, zkey):
        data_q('fit', [xkey, zkey, current_slice.read()])
    
    def freerun(self):
        if freerun.read():
            print 'Control freerun'
            q('loop')
            
    def index_slice(self, col='index'):
        '''
        tell DAQ to start a new slice \n
        '''
        current_slice.clear()
        current_slice.col = col
        
    def initialize_hardware(self):
        q('initialize')

    def initialize_scan(self, widget, scan_origin=None, scan_axes=[], dont_ignore=[], fit=False):
        '''
        prepare environment for scanning
        '''
        origin.write(scan_origin)
        # set index back to zero
        index.write(0)
        # get params from widget
        shots.write(widget.shots.read())
        # create data file(s)
        axes.write(scan_axes)
        self.update_cols(dont_ignore=dont_ignore)
        data_q('create_data')
        if fit:
            data_q('create_fit')
        # wait until daq is done before letting module continue        
        self.wait_until_daq_done()
        self.wait_until_data_done()
        
    def module_control_update(self):
        if g.module_control.read():
            freerun.write(False)
            self.wait_until_daq_done()
            print 'module control update done'
        else:
            freerun.write(True)
            
    def update_cols(self, dont_ignore=[]):
        '''
        define the format of .data and .fit files
        '''
        new_ignore = ['index', 'time']
        new_data_cols = collections.OrderedDict()
        new_fit_cols = collections.OrderedDict()
        # exposed hardware positions get written to both filetypes
        for cols in [new_data_cols, new_fit_cols]:
            # index
            dictionary = collections.OrderedDict()
            dictionary['index'] = len(cols)
            dictionary['units'] = None
            dictionary['tolerance'] = 0.5
            dictionary['label'] = ''
            dictionary['object'] = None
            cols['index'] = dictionary
            # time
            dictionary = collections.OrderedDict()
            dictionary['index'] = len(cols)
            dictionary['units'] = 's'
            dictionary['tolerance'] = 0.001
            dictionary['label'] = 'lab'
            dictionary['object'] = None
            cols['time'] = dictionary
            for module in hardware_modules:
                for hardware in module.hardwares:
                    for key in hardware.recorded:
                        dictionary = collections.OrderedDict()
                        dictionary['index'] = len(cols)
                        dictionary['object'] = hardware.recorded[key][0]
                        dictionary['units'] = hardware.recorded[key][1]
                        dictionary['tolerance'] = hardware.recorded[key][2]
                        dictionary['label'] = hardware.recorded[key][3]
                        cols[key] = dictionary
                        if cols == new_data_cols:  # only do this once
                            if hardware.recorded[key][4] and key not in new_ignore:
                                new_ignore.append(key)
        # data
        for channel in channels:
            for prop in properties:
                dictionary = collections.OrderedDict()
                name = channel + '_' + prop
                dictionary['index'] = len(new_data_cols)
                dictionary['units'] = 'V'
                dictionary['tolerance'] = None
                dictionary['label'] = ''
                dictionary['object'] = None
                new_data_cols[name] = dictionary
        # fit
        for prop in ['amplitude', 'center', 'FWHM', 'offset']:
            dictionary = collections.OrderedDict()
            name = prop
            dictionary['index'] = len(new_fit_cols)
            dictionary['units'] = 'V'
            dictionary['tolerance'] = None
            dictionary['label'] = ''
            dictionary['object'] = None
            new_fit_cols[name] = dictionary
        data_cols.write(new_data_cols)
        fit_cols.write(new_fit_cols)
        for item in new_ignore:
            if item in dont_ignore:
                new_ignore.pop[item]
        ignore.write(new_ignore)
        
    def update_task(self):
        if freerun.read():
            return_to_freerun = True
            freerun.write(False)
            self.wait_until_daq_done()
        else: 
            return_to_freerun = False
        q('create_task')
        if return_to_freerun: 
            freerun.write(True)
    
    def wait_until_daq_done(self, timeout=10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        '''
        start_time = time.time()
        q('check_busy')
        while busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_actions.read(): 
                    q('check_busy')
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
                if not enqueued_data.read(): 
                    data_q('check_busy')
                data_busy.wait_for_update()
            else: 
                g.logger.log('warning', 'Data wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
                
    def shutdown(self):   
        # stop looping
        freerun.write(False)
        # log
        if g.debug.read(): print 'daq shutting down'
        g.logger.log('info', 'DAQ shutdown')
        # shutdown other threads
        q('shutdown')
        data_q('shutdown')
        self.wait_until_daq_done()
        self.wait_until_data_done()
        address_thread.quit()
        data_thread.quit()
        #close gui
        gui.stop()
    
control = Control()


### gui########################################################################


class Widget(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = custom_widgets.InputTable()
        input_table.add('DAQ', None)
        self.shots = pc.Number(initial_value = 200, decimals = 0)
        input_table.add('Shots', self.shots)
        layout.addWidget(input_table)
        
class Gui(QtCore.QObject):

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
        self.create_frame()
        
    def create_frame(self):
        
        # get parent widget ---------------------------------------------------
        
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        #parent_widget.layout().setContentsMargins(0, 5, 0, 0)
        layout = parent_widget.layout()
        
        # display area --------------------------------------------------------

        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        # big number
        self.big_display = custom_widgets.spinbox_as_display(font_size = 100)        
        display_layout.addWidget(self.big_display)
        
        # plot
        self.plot_widget = custom_widgets.Plot1D()
        self.plot_curve = self.plot_widget.add_scatter()
        self.plot_widget.set_labels(ylabel = 'volts')
        self.plot_green_line = self.plot_widget.add_infinite_line(color = 'g')   
        self.plot_red_line = self.plot_widget.add_infinite_line(color = 'r')   
        display_layout.addWidget(self.plot_widget)
        
        # value display frame
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
                # display
                display = custom_widgets.spinbox_as_display()
                value_frame_layout.addWidget(display, i+1, j+1)
                grid_displays_row.append(display)
            self.grid_displays.append(grid_displays_row)
        for j in range(3):
            # label
            label = QtGui.QLabel(clabels[j])
            label.setAlignment(QtCore.Qt.AlignRight)
            label.setStyleSheet(label_StyleSheet)
            value_frame_layout.addWidget(label, 0, j+1)
        value_frame_layout
        frame_frame_widget.layout().addWidget(frame_widget)
        display_layout.addWidget(frame_frame_widget)
        
        # streach
        spacer = custom_widgets.vertical_spacer()
        spacer.add_to_layout(display_layout)
        
        # vertical line -------------------------------------------------------

        line = custom_widgets.line('V')      
        layout.addWidget(line)
        
        # settings area -------------------------------------------------------
        
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = custom_widgets.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
                
        # input table one
        input_table = custom_widgets.InputTable()
        input_table.add('Display', None)
        input_table.add('Shots', shots)
        input_table.add('Free run', freerun)
        input_table.add('Channel', tab_channel)
        input_table.add('Property', tab_property)
        input_table.add('Timescale', tab_timescale)        
        input_table.add('Trigger', tab_trigger)
        input_table.add('Shots', tab_shots)        
        settings_layout.addWidget(input_table)
        
        # horizontal line
        line = custom_widgets.line('H')      
        settings_layout.addWidget(line)
        
        # input table two
        input_table = custom_widgets.InputTable()
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
        
        # set button
        apply_channels_button = custom_widgets.SetButton('APPLY CHANNEL SETTINGS')        
        settings_layout.addWidget(apply_channels_button)
        apply_channels_button.clicked.connect(self.on_apply_channels)
        g.module_control.disable_when_true(apply_channels_button)
        
        # horizontal line
        line = custom_widgets.line('H')      
        settings_layout.addWidget(line)
        
        # debug tools
        input_table = custom_widgets.InputTable()
        input_table.add('Debug', None)
        busy.update_signal = address_obj.update_ui
        input_table.add('DAQ', busy)
        data_busy.update_signal = data_obj.update_ui
        input_table.add('Data', data_busy)
        input_table.add('Loop time', seconds_since_last_task)
        input_table.add('Acquisiton time', seconds_for_acquisition)
        settings_layout.addWidget(input_table)
        g.module_control.disable_when_true(input_table)
        
        # streach
        settings_layout.addStretch(1)

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
        
gui = Gui()


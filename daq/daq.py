### import ####################################################################


import os
import sys
import imp
import time
import copy

import collections

import numpy as np

import scipy

from PyQt4 import QtCore, QtGui

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import project.ini_handler as ini
import opas.opas as opas
import spectrometers.spectrometers as spectrometers
import delays.delays as delays
hardware_modules = [opas, spectrometers, delays]
app = g.app.read()
main_dir = g.main_dir.read()
ini = ini.daq

if not g.offline.read(): 
    from PyDAQmx import *


### channels ##################################################################


rest_channel = pc.Number(decimals=0, ini=ini, section='DAQ', 
                         option='rest channel', 
                         limits=pc.NumberLimits(0, 7, None),
                         import_from_ini=True, save_to_ini_at_shutdown=True)


class Channel():
    
    def __init__(self, index):
        self.index = index
        ini_section = ' '.join(['Channel', str(self.index)])
        self.section = ini_section
        self.active = pc.Bool(ini=ini, section=ini_section, option='active')
        self.name = pc.String(inital_value='Name', ini=ini, section=ini_section, option='name')
        self.physical_correspondance = pc.Number(decimals=0, limits=pc.NumberLimits(0, 7, None), ini=ini, section=ini_section, option='physical correspondance')
        self.min = pc.Number(decimals=1, limits=pc.NumberLimits(-10, 10, None), ini=ini, section=ini_section, option='min')
        self.max = pc.Number(decimals=1, limits=pc.NumberLimits(-10, 10, None), ini=ini, section=ini_section, option='max')
        self.invert = pc.Bool(ini=ini, section=ini_section, option='invert')
        sample_limits=pc.NumberLimits(0, 900, None)
        self.signal_start_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='signal start')
        self.signal_stop_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='signal stop')
        self.signal_pre_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='signal presample')
        processing_methods = ['Average', 'Integral', 'Min', 'Max']
        self.signal_method = pc.Combo(allowed_values=processing_methods, ini=ini, section=ini_section, option='signal method')
        self.use_baseline = pc.Bool(ini=ini, section=ini_section, option='use baseline')
        self.baseline_start_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='baseline start')
        self.baseline_stop_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='baseline stop')
        self.baseline_pre_index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='baseline presample')
        self.baseline_method = pc.Combo(allowed_values=processing_methods, ini=ini, section=ini_section, option='baseline method')
        # a list of all properties
        self.properties = [self.active, self.name,
                           self.physical_correspondance, self.min, self.max,
                           self.invert, self.signal_start_index,
                           self.signal_stop_index, self.signal_method,
                           self.signal_pre_index, self.use_baseline,
                           self.baseline_method, self.baseline_pre_index,
                           self.baseline_start_index, self.baseline_stop_index]
        # call get saved on self
        self.get_saved()
        # signals
        self.use_baseline.updated.connect(lambda: self.on_use_baseline())
        self.on_use_baseline()
 
    def get_saved(self):
        for obj in self.properties:
            obj.get_saved()

    def get_widget(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Name', self.name)
        self.input_table.add('Physical Channel', self.physical_correspondance)
        self.input_table.add('Min. Voltage', self.min)
        self.input_table.add('Max. Voltage', self.max)
        self.input_table.add('Invert', self.invert)
        self.input_table.add('Signal Start', self.signal_start_index)
        self.input_table.add('Signal Stop', self.signal_stop_index)
        self.input_table.add('Signal Presample', self.signal_pre_index)
        self.input_table.add('Signal Method', self.signal_method)
        self.input_table.add('Use Baseline', self.use_baseline)
        self.input_table.add('Baseline Start', self.baseline_start_index)
        self.input_table.add('Baseline Stop', self.baseline_stop_index)
        self.input_table.add('Baseline Presample', self.baseline_pre_index)
        self.input_table.add('Baseline Method', self.baseline_method)
        return self.input_table
        
    def on_use_baseline(self):
        self.baseline_method.set_disabled(not self.use_baseline.read()) 
        self.baseline_start_index.set_disabled(not self.use_baseline.read()) 
        self.baseline_stop_index.set_disabled(not self.use_baseline.read()) 
        self.baseline_pre_index.set_disabled(not self.use_baseline.read())
        
    def save(self):
        for obj in self.properties:
            obj.save()
        

channels = pc.Mutex([Channel(i) for i in range(8)])
destination_channels = pc.Mutex([Channel(i) for i in range(8)])


class Chopper():
    
    def __init__(self, index):
        self.index = index
        ini_section = ' '.join(['Chopper', str(self.index)])
        self.section = ini_section
        self.active = pc.Bool(ini=ini, section=ini_section, option='active')
        self.name = pc.String(inital_value='Name', ini=ini, section=ini_section, option='name')
        self.physical_correspondance = pc.Number(decimals=0, limits=pc.NumberLimits(0, 7, None), ini=ini, section=ini_section, option='physical correspondance')
        self.invert = pc.Bool(ini=ini, section=ini_section, option='invert')
        sample_limits=pc.NumberLimits(0, 900, None)
        self.index = pc.Number(decimals=0, limits=sample_limits, ini=ini, section=ini_section, option='index')
        # a list of all properties
        self.properties = [self.active, self.name,
                           self.physical_correspondance, self.invert,
                           self.index]
        # call get saved on self
        self.get_saved()

 
    def get_saved(self):
        for obj in self.properties:
            obj.get_saved()

    def get_widget(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Name', self.name)
        self.input_table.add('Physical Channel', self.physical_correspondance)
        self.input_table.add('Invert', self.invert)
        self.input_table.add('Index', self.index)
        print 'CHOPPER INPUT TABLE!!!!!!!!!!!'
        return self.input_table
        
    def save(self):
        for obj in self.properties:
            obj.save()


choppers = pc.Mutex([Chopper(i) for i in range(7)])
destination_choppers = pc.Mutex([Chopper(i) for i in range(7)])

# sample correspondances holds an array of integers
# zero : rest sample
# positive : channel
# negative : chopper
sample_correspondances = pc.Mutex(initial_value=np.zeros(900))


### current data objects ######################################################


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

last_data = pc.Mutex()  # array of all daq col

last_samples = pc.Mutex()

last_shots = pc.Mutex()


### misc objects ##############################################################

# shots
shot_channel_combo = pc.Combo()
shots_processing_module_path = pc.Filepath(ini=ini, section='DAQ',
                                           option='shots processing module path',
                                           import_from_ini=True,
                                           save_to_ini_at_shutdown=True,
                                           options=['*.py'])
seconds_for_shots_processing = pc.Number(initial_value=np.nan, display=True, decimals=3)
                                           
# values
value_channel_combo = pc.Combo()
                                    
                                           

axes = pc.Mutex()

array_detector_reference = pc.Mutex()

ignore = pc.Mutex()

origin = pc.Mutex()

# daq
shots = pc.Number(initial_value = np.nan, ini=ini, section='DAQ', option='Shots', import_from_ini = True, save_to_ini_at_shutdown = True, decimals = 0)
index = pc.Number(initial_value=0)

# graph and big #
freerun = pc.Bool(initial_value=True)

# additional
seconds_since_last_task = pc.Number(initial_value=np.nan, display=True, decimals=3)
seconds_for_acquisition = pc.Number(initial_value=np.nan, display=True, decimals=3)



# column dictionaries
data_cols = pc.Mutex()
fit_cols = pc.Mutex()


### DATA address ##############################################################


data_busy = pc.Busy()

data_path = pc.Mutex()

enqueued_data = pc.Enqueued()

fit_path = pc.Mutex()

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
        scan_origin, widget = inputs
        self.file_timestamp = wt.kit.get_timestamp()
        self.filename = ' '.join([scan_origin, str(axes.read()), self.file_timestamp, widget.description.read()]).rstrip()
        data_path.write(os.path.join(main_dir, 'data', self.filename + '.data'))
        header_str = self.make_header(data_cols.read(), inputs)
        np.savetxt(data_path.read(), [], header=header_str)
        
    def create_fit(self, inputs):
        # create fit must always be called after create data
        fit_path.write(os.path.join(main_dir, 'data', self.filename + ' FITTED.data'))
        header_str = self.make_header(fit_cols.read(), inputs)
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
        
    def make_header(self, cols, inputs):
        scan_origin, widget = inputs
        # generate header
        units_list = [col['units'] for col in cols.values()]
        tolerance_list = [col['tolerance'] for col in cols.values()]
        label_list = [col['label'] for col in cols.values()]
        name_list = cols.keys()
        # name
        if widget.name.read() == '':
            name = ' '.join([origin.read(), widget.description.read()])
        else:
            name = widget.name.read()
        # strings need extra apostrophes and everything needs to be string
        for lis in [units_list, tolerance_list, label_list, name_list]:
            for i in range(len(lis)):
                if type(lis[i]) == str:       
                    lis[i] = '\'' + lis[i] + '\''
                else:
                    lis[i] = str(lis[i])
        header_items = ['file created:' + '\t' + '\'' + self.file_timestamp + '\'']
        header_items += ['name:'  + '\t' + '\'' + name + '\'']
        header_items += ['info:'  + '\t' + '\'' + widget.info.read() + '\'']
        header_items += ['origin:' + '\t' + '\'' + origin.read() + '\'']
        header_items += ['shots:' + '\t' + str(widget.shots.read())]
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


busy = pc.Busy()

enqueued_actions = pc.Enqueued()

class DAQ(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    running = False
    processing_timer = wt.kit.Timer(verbose=False)
    
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
        '''
        Define a new DAQ task. This needs to be run once every time the
        parameters of the aquisition (channel correspondance, shots, etc.)
        change.
        '''
        if g.offline.read(): return
            
        # ensure previous task closed -----------------------------------------
        
        if self.task_created:
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            
        self.task_created = False
        
        # import --------------------------------------------------------------
        
        self.shots = shots.read()
        
        # calculate the number of 'virtual samples' to take -------------------
        
        self.virtual_samples = 900  # GET RID OF THIS!!!!
        
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

        name_index = 0  # something to keep channel names unique
        try:
            # sample correspondances holds an array of integers
            # zero : rest sample
            # positive : channel
            # negative : chopper
            for correspondance in sample_correspondances.read():
                if correspondance == 0:
                    physical_channel = rest_channel.read()
                    min_voltage = -10.
                    max_voltage = 10.
                elif correspondance > 0:
                    channel = channels.read()[correspondance-1]
                    physical_channel = channel.physical_correspondance.read()
                    min_voltage = channel.min.read()
                    max_voltage = channel.max.read()
                elif correspondance < 0:
                    physical_channel = channels.read()[-correspondance-1].physical_correspondance.read()
                    min_voltage = -1.
                    max_voltage = 6.
                channel_name = 'sample_' + str(name_index).zfill(3)
                DAQmxCreateAIVoltageChan(self.task_handle,              # task handle
                                         'Dev1/ai%i'%physical_channel,  # physical chanel
                                         channel_name,                  # name to assign to channel
                                         DAQmx_Val_Diff,                # the input terminal configuration
                                         min_voltage, max_voltage,      # minVal, maxVal
                                         DAQmx_Val_Volts,               # units 
                                         None)                          # custom scale
                name_index += 1
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in virtual channel creation', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            return
        
        # define timing -------------------------------------------------------
      
        try:
            DAQmxCfgSampClkTiming(self.task_handle,       # task handle
                                  '/Dev1/PFI0',           # sorce terminal
                                  1000.0,                 # sampling rate (samples per second per channel) (float 64) (in externally clocked mode, only used to initialize buffer)
                                  DAQmx_Val_Rising,       # acquire samples on the rising edges of the sample clock
                                  DAQmx_Val_FiniteSamps,  # acquire a finite number of samples
                                  long(self.shots))       # samples per channel to acquire (unsigned integer 64)         
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in timing definition', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            return
            
        # create arrays for task to fill --------------------------------------

        self.samples = np.zeros(self.shots*900, dtype=numpy.float64)
        self.samples_len = len(self.samples)  # do not want to call for every acquisition

        # finish --------------------------------------------------------------
            
        self.task_created = True
            
    def run_task(self, inputs):
        '''
        Acquire once using the created task.        
        
        Parameters
        ----------
        inputs[0] : bool
            Toggle save behavior.
        '''
        
        ### measure ###########################################################
        
        # unpack inputs -------------------------------------------------------

        self.running = True  
        self.check_busy([])
        self.update_ui.emit()

        self.save = inputs[0]

        if not self.task_created: 
            return

        start_time = time.time()
        
        #array_detector = array_detector_reference.read()
        
        # tell array detector to begin ----------------------------------------
        
        #array_detector.control.read()   
        
        # collect samples array -----------------------------------------------
        
        try:
            DAQmxStartTask(self.task_handle)
            DAQmxReadAnalogF64(self.task_handle,             # task handle
                               long(self.shots),             # number of samples per channel
                               10.0,                         # timeout (seconds) for each read operation
                               DAQmx_Val_GroupByScanNumber,  # fill mode (specifies whether or not the samples are interleaved)
                               self.samples,                 # read array
                               self.samples_len,             # size of the array, in samples, into which samples are read
                               byref(self.read),             # reference of thread
                               None)                         # reserved by NI, pass NULL (?)
            DAQmxStopTask(self.task_handle)
        except DAQError as err:
            print "DAQmx Error: %s"%err
            g.logger.log('error', 'Error in timing definition', err)
            DAQmxStopTask(self.task_handle)
            DAQmxClearTask(self.task_handle)
            
        # export samples
        last_samples.write(self.samples)
            
        # wait for array detector to finish -----------------------------------
            
        #array_detector.control.wait_until_done()
            
        seconds_for_acquisition.write(time.time() - start_time)
        
        ### process ###########################################################
        
        # calculate shot values for each channel, chopper ---------------------
        
        active_channels = [channel for channel in channels.read() if channel.active.read()]
        active_choppers = [chopper for chopper in choppers.read() if chopper.active.read()]
        shots_array = np.full((len(active_channels)+len(active_choppers), self.shots), np.nan)
        folded_samples = self.samples.copy().reshape((900, -1), order='F')
        index = 0
        
        # channels
        for channel_index, channel in enumerate(active_channels):
            # get signal points
            signal_index_possibilities = range(int(channel.signal_start_index.read()), int(channel.signal_stop_index.read()) + 1)
            signal_indicies = [i for i in signal_index_possibilities if sample_correspondances.read()[i] == channel_index + 1]
            signal_indicies = signal_indicies[channel.signal_pre_index.read():]  # remove pre points
            signal_samples = folded_samples[signal_indicies]
            # process signal
            if channel.signal_method.read() == 'Average':
                signal = np.mean(signal_samples, axis=0)
            elif channel.signal_method.read() == 'Sum':
                signal = np.sum(signal_samples, axis=0)
            elif channel.signal_method.read() == 'Min':
                signal = np.min(signal_samples, axis=0)
            elif channel.signal_method.read() == 'Max':
                signal = np.max(signal_samples, axis=0)
            # baseline
            baseline = 0
            out = signal - baseline
            # invert
            if channel.invert.read():
                out *= -1
            # finish
            shots_array[index] = out
            index += 1
            
        # choppers
        for chopper in active_choppers:
            shots_array[index] = 0
            index += 1
            # DIGITIZE CHOPPER
            
        # export shots
        last_shots.write(shots_array)
            
        # do math -------------------------------------------------------------
        
        # pass through shots processing module
        with self.processing_timer:
            path = shots_processing_module_path.read()
            name = str(os.path.basename(path))
            processing_module = imp.load_source(name, path)
            channel_names = [channel.name.read() for channel in active_channels]
            chopper_names = [chopper.name.read() for chopper in active_choppers]
            kinds = ['channel' for _ in channel_names] + ['chopper' for _ in chopper_names]
            names = channel_names + chopper_names
            out, out_names = processing_module.process(shots_array, names, kinds)
        seconds_for_shots_processing.write(self.processing_timer.interval)
        
        # export last data
        value_channel_combo.set_allowed_values(out_names)
        last_data.write(out)
        self.update_ui.emit()
        
        # export data ---------------------------------------------------------
        
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
                    row[i] = np.nan
                    i += 1
            # output
            data_q('write_data', [row])
            current_slice.append(row)
            
            # index
            index.write(index.read()+1)
        
        # update timer, finish ------------------------------------------------
        
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
        # startup sample correspondances
        self.update_sample_correspondances(channels.read(), choppers.read())
        # setup freerun
        freerun.updated.connect(self.freerun)
        self.freerun()
        # other controls
        shots.updated.connect(self.update_task)
        rest_channel.updated.connect(self.update_task)
        g.main_window.read().module_control.connect(self.module_control_update)
        
    def acquire(self):
        q('run_task', inputs=[True])
        
    def update_sample_correspondances(self, proposed_channels, proposed_choppers):
        '''
        Parameters
        ----------
        channels : list of Channel objects
            The proposed channel settings.
        choppers : list of Chopper objects
            The proposed chopper settings.
        '''
        # sections is a list of lists: [correspondance, start index, stop index]
        sections = []
        for i in range(len(proposed_channels)):
            channel = proposed_channels[i]
            if channel.active.read():                
                correspondance = i + 1  # channels go from 1 --> infinity
                start = channel.signal_start_index.read()
                stop = channel.signal_stop_index.read()
                sections.append([correspondance, start, stop])
                if channel.use_baseline.read():
                    start = channel.baseline_start_index.read()
                    stop = channel.baseline_stop_index.read()
                    sections.append([correspondance, start, stop])
        print sections
        # desired is a list of lists containing all of the channels 
        # that desire to be read at a given sample
        desired = [[] for _ in range(900)]
        for section in sections:
            correspondance = section[0]
            start = int(section[1])
            stop = int(section[2])
            for i in range(start, stop+1):
                desired[i].append(correspondance)
                desired[i] = [val for val in set(desired[i])]  # remove non-unique
                desired[i].sort()
        # samples is the proposed sample correspondances
        samples = np.full(900, 0, dtype=int)
        for i in range(len(samples)):
            lis = desired[i]
            if not len(lis) == 0:
                samples[i] = lis[i%len(lis)]
        # choppers
        # TO DO!!!!!!!!!!!!!!!
        # check if proposed is valid
        # TO DO!!!!!!!!!!!!!!!
        # apply to channels
        channels.write(proposed_channels)
        for channel in channels.read():
            channel.save()
        choppers.write(proposed_choppers)
        for chopper in choppers.read():
            chopper.save()
        # update channel names
        channel_names = [channel.name.read() for channel in channels.read() if channel.active.read()]
        chopper_names = [chopper.name.read() for chopper in choppers.read() if chopper.active.read()]
        allowed_values = channel_names + chopper_names
        shot_channel_combo.set_allowed_values(allowed_values)
        # finish
        sample_correspondances.write(samples)
        self.update_task()       
        
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
        data_q('create_data', [scan_origin, widget])
        if fit:
            data_q('create_fit', [scan_origin, widget])
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
        for channel in old_channels:
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
        input_table = pw.InputTable()
        input_table.add('DAQ', None)
        self.shots = pc.Number(initial_value = 200, decimals = 0)
        input_table.add('Shots', self.shots)
        self.description = pc.String()
        input_table.add('Description', self.description)
        self.name = pc.String()
        input_table.add('Name', self.name)
        self.info = pc.String()
        input_table.add('Info', self.info)
        layout.addWidget(input_table)
        
class Gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        control.wait_until_daq_done()
        address_obj.update_ui.connect(self.update)
        data_obj.update_ui.connect(self.update)
        shot_channel_combo.updated.connect(self.update)
        self.create_frame()
        
    def create_frame(self):
        
        # get parent widget ---------------------------------------------------
        
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        layout = parent_widget.layout()
        
        # create tab structure ------------------------------------------------
        
        self.tabs = QtGui.QTabWidget()

        # samples tab
        samples_widget = QtGui.QWidget()
        samples_box = QtGui.QHBoxLayout()
        samples_box.setContentsMargins(0, 10, 0, 0)
        samples_widget.setLayout(samples_box)
        self.tabs.addTab(samples_widget, 'Samples')
        self.create_samples_tab(samples_box)        

        # shots tab
        shots_widget = QtGui.QWidget()
        shots_box = QtGui.QHBoxLayout()
        shots_box.setContentsMargins(0, 10, 0, 0)
        shots_widget.setLayout(shots_box)
        self.tabs.addTab(shots_widget, 'Shots')
        self.create_shots_tab(shots_box)

        # values tab
        values_widget = QtGui.QWidget()
        values_box = QtGui.QHBoxLayout()
        values_box.setContentsMargins(0, 10, 0, 0)
        values_widget.setLayout(values_box)
        self.tabs.addTab(values_widget, 'Values')
        self.create_values_tab(values_box)
        
        layout.addWidget(self.tabs)
        
    def create_samples_tab(self, layout):
        
        # display area --------------------------------------------------------

        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        # plot
        self.samples_plot_widget = pw.Plot1D()
        self.samples_plot_scatter = self.samples_plot_widget.add_scatter()
        self.samples_plot_widget.set_labels(xlabel='sample', ylabel='volts')
        self.samples_plot_max_voltage_line = self.samples_plot_widget.add_infinite_line(color='y', angle=0)
        self.samples_plot_min_voltage_line = self.samples_plot_widget.add_infinite_line(color='y', angle=0)
        self.samples_plot_signal_start_line = self.samples_plot_widget.add_infinite_line(color='g')
        self.samples_plot_signal_stop_line = self.samples_plot_widget.add_infinite_line(color='r')
        self.samples_plot_baseline_start_line = self.samples_plot_widget.add_infinite_line(color='g', style='dashed')
        self.samples_plot_baseline_stop_line = self.samples_plot_widget.add_infinite_line(color='r', style='dashed')
        self.samples_plot_chopper_line = self.samples_plot_widget.add_infinite_line(color='y')
        display_layout.addWidget(self.samples_plot_widget)
        
        # vertical line -------------------------------------------------------

        line = pw.line('V')
        layout.addWidget(line)
        
        # settings area -------------------------------------------------------
        
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area(130)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)

        input_table = pw.InputTable()
        input_table.add('Rest Channel', rest_channel)
        settings_layout.addWidget(input_table)

        # channels ------------------------------------------------------------
        
        line = pw.line('H')
        settings_layout.addWidget(line)
        
        # channel_combobox
        allowed_values = [channel.section for channel in channels.read() if channel.active.read()]
        self.samples_channel_combo = pc.Combo(allowed_values=allowed_values)
        self.samples_channel_combo.updated.connect(self.update_samples_tab)
        input_table = pw.InputTable()
        input_table.add('Channel', self.samples_channel_combo)
        settings_layout.addWidget(input_table)
        
        # add button
        self.add_channel_button = pw.SetButton('ADD CHANNEL')  
        settings_layout.addWidget(self.add_channel_button)
        self.add_channel_button.clicked.connect(self.on_add_channel)       
        
        # remove button
        self.remove_channel_button = pw.SetButton('REMOVE TRAILING CHANNEL', 'stop')     
        settings_layout.addWidget(self.remove_channel_button)
        self.remove_channel_button.clicked.connect(self.on_remove_channel) 
        
        self.channel_widgets = []
        for channel in destination_channels.read():
            widget = channel.get_widget()
            settings_layout.addWidget(widget)
            widget.hide()
            self.channel_widgets.append(widget)
            
        # apply button
        self.apply_channel_button = pw.SetButton('APPLY CHANGES')
        self.apply_channel_button.clicked.connect(self.on_apply_channel)
        settings_layout.addWidget(self.apply_channel_button)
        
        # revert button
        self.revert_channel_button = pw.SetButton('REVERT CHANGES', 'stop')
        self.revert_channel_button.clicked.connect(self.on_revert_channel)
        settings_layout.addWidget(self.revert_channel_button)

        # choppers ------------------------------------------------------------

        line = pw.line('H')
        settings_layout.addWidget(line)
        
        # chopper_combobox
        allowed_values = [chopper.section for chopper in destination_choppers.read() if chopper.active.read()]
        self.advanced_chopper_combo = pc.Combo(allowed_values=allowed_values)
        self.advanced_chopper_combo.updated.connect(self.update_samples_tab)
        input_table = pw.InputTable()
        input_table.add('Chopper', self.advanced_chopper_combo)
        settings_layout.addWidget(input_table)
        
        # add button
        self.add_chopper_button = pw.SetButton('ADD CHOPPER')  
        settings_layout.addWidget(self.add_chopper_button)
        self.add_chopper_button.clicked.connect(self.on_add_chopper)       
        
        # remove button
        self.remove_chopper_button = pw.SetButton('REMOVE TRAILING CHOPPER', 'stop')     
        settings_layout.addWidget(self.remove_chopper_button)
        self.remove_chopper_button.clicked.connect(self.on_remove_chopper) 
        
        self.chopper_widgets = []
        for chopper in destination_choppers.read():
            widget = chopper.get_widget()
            settings_layout.addWidget(widget)
            widget.hide()
            self.chopper_widgets.append(widget)
            
        # apply button
        self.apply_chopper_button = pw.SetButton('APPLY CHANGES')
        self.apply_chopper_button.clicked.connect(self.on_apply_chopper)
        settings_layout.addWidget(self.apply_chopper_button)
        
        # revert button
        self.revert_chopper_button = pw.SetButton('REVERT CHANGES', 'stop')
        self.revert_chopper_button.clicked.connect(self.on_revert_chopper)
        settings_layout.addWidget(self.revert_chopper_button)
        
        settings_layout.addStretch(1)
        
        # call self
        self.update_samples_tab()
        
    def create_shots_tab(self, layout):

        # display area --------------------------------------------------------

        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        # plot
        self.shots_plot_widget = pw.Plot1D()
        self.shots_plot_scatter = self.shots_plot_widget.add_scatter()
        self.shots_plot_widget.set_labels(xlabel='shot', ylabel='volts')
        display_layout.addWidget(self.shots_plot_widget)
        
        # vertical line
        line = pw.line('V')      
        layout.addWidget(line)
        
        # settings area -------------------------------------------------------
        
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
                
        # input table
        input_table = pw.InputTable()
        input_table.add('Display', None)
        input_table.add('Channel', shot_channel_combo)   
        input_table.add('Settings', None)
        input_table.add('Shots', shots)
        input_table.add('Shot Processing', shots_processing_module_path)
        input_table.add('Processing Time', seconds_for_shots_processing)
        settings_layout.addWidget(input_table)

        # streach
        settings_layout.addStretch(1)
        
    def create_values_tab(self, layout):
        
        # display area --------------------------------------------------------

        # container widget
        display_container_widget = pw.ExpandingWidget()#QtGui.QWidget()

        #display_rect = display_container_widget.rect()
        #display_rectf = QtCore.QRectF(display_rect)
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        # big number
        self.big_display = pw.spinbox_as_display(font_size = 100)        
        display_layout.addWidget(self.big_display)
 
        # streach
        if False:
            spacer = pw.VerticalSpacer()
            spacer.add_to_layout(display_layout)
       
        # plot
        self.values_plot_widget = pw.Plot1D()
        #self.values_plot_widget.fitInView(display_rectf)
        self.values_plot_scatter = self.values_plot_widget.add_scatter()
        display_layout.addWidget(self.values_plot_widget)
        
        # vertical line
        line = pw.line('V')      
        layout.addWidget(line)
        
        # settings area -------------------------------------------------------
        
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
                
        # input table one
        input_table = pw.InputTable()
        input_table.add('Display', None)
        input_table.add('Channel', value_channel_combo)   
        input_table.add('Settings', None)
        input_table.add('Free run', freerun)
        busy.update_signal = address_obj.update_ui
        input_table.add('DAQ status', busy)
        data_busy.update_signal = data_obj.update_ui
        input_table.add('Data status', data_busy)
        input_table.add('Loop time', seconds_since_last_task)
        input_table.add('Acquisiton time', seconds_for_acquisition)
        settings_layout.addWidget(input_table)
        
        # streach
        settings_layout.addStretch(1)
    
    def on_add_channel(self):
        allowed_values = [channel.section for channel in destination_channels.read() if channel.active.read()]
        new_channel_section = 'Channel %i'%len(allowed_values)
        allowed_values.append(new_channel_section)
        self.samples_channel_combo.set_allowed_values(allowed_values)
        print self.samples_channel_combo.allowed_values
        self.samples_channel_combo.write(new_channel_section)
        # do not activate channel until changes are applied
        self.update_samples_tab()
        
    def on_add_chopper(self):
        pass

    def on_apply_channel(self):        
        new_channel_index = int(self.samples_channel_combo.read()[-1])
        new_channel = destination_channels.read()[new_channel_index]
        new_channel.active.write(True)
        new_channels = copy.copy(channels.read())
        new_channels[new_channel_index] = new_channel
        control.update_sample_correspondances(new_channels, choppers.read())
        self.update_samples_tab()
    
    def on_apply_chopper(self):
        pass
        
    def on_remove_channel(self):
        # loop through channels backwards
        for channel in channels.read()[::-1]:
            if channel.active.read():
                channel.get_saved()  # revert to saved
                channel.active.write(False)
                channel.save()
                print channel.section
                break
        allowed_values = [channel.section for channel in destination_channels.read() if channel.active.read()]
        self.samples_channel_combo.set_allowed_values(allowed_values)
        self.samples_channel_combo.write(allowed_values[-1])
        self.update_samples_tab()
        
    def on_remove_chopper(self):
        pass
        
    def on_revert_channel(self):
        channel_index = int(self.samples_channel_combo.read()[-1])
        destination_channels.read()[channel_index].get_saved()
        
    def on_revert_chopper(self):
        pass
        
    def update(self):
        '''
        Runs each time an update_ui signal fires (basically every run_task)
        '''

        # samples
        yi = last_samples.read()[:900]
        xi = np.arange(len(yi))
        self.samples_plot_scatter.clear()
        self.samples_plot_scatter.setData(xi, yi)
        
        # shots
        yi = last_shots.read()[shot_channel_combo.read_index()]
        xi = np.arange(len(yi))
        self.shots_plot_scatter.clear()
        self.shots_plot_scatter.setData(xi, yi)

        # values
        self.big_display.setValue(last_data.read()[value_channel_combo.read_index()])
                
    def update_samples_tab(self):
        # buttons
        num_channels = len(self.samples_channel_combo.allowed_values)
        self.add_channel_button.setDisabled(False)
        self.remove_channel_button.setDisabled(False)
        if num_channels == 8:
            self.add_channel_button.setDisabled(True)
        elif num_channels == 1:
            self.remove_channel_button.setDisabled(True)
        # channel ui
        channel_index = int(self.samples_channel_combo.read()[-1])
        for widget in self.channel_widgets:
            widget.hide()
        self.channel_widgets[channel_index].show()
        # chopper ui
        chopper_index = int(self.samples_channel_combo.read()[-1])
        for widget in self.chopper_widgets:
            widget.hide()
        self.chopper_widgets[chopper_index].show()
        # lines on plot
        self.samples_plot_max_voltage_line.hide()
        self.samples_plot_min_voltage_line.hide()
        self.samples_plot_signal_start_line.hide()
        self.samples_plot_signal_stop_line.hide()
        self.samples_plot_baseline_start_line.hide()
        self.samples_plot_baseline_stop_line.hide()
        self.samples_plot_chopper_line.hide()
        current_channel_index = int(self.samples_channel_combo.read()[-1])
        current_channel_object = channels.read()[current_channel_index]
        if current_channel_object.active.read():
            self.samples_plot_max_voltage_line.show()
            self.samples_plot_max_voltage_line.setValue(current_channel_object.max.read())
            self.samples_plot_min_voltage_line.show()
            self.samples_plot_min_voltage_line.setValue(current_channel_object.min.read())
            self.samples_plot_signal_start_line.show()       
            self.samples_plot_signal_start_line.setValue(current_channel_object.signal_start_index.read())
            self.samples_plot_signal_stop_line.show()
            self.samples_plot_signal_stop_line.setValue(current_channel_object.signal_stop_index.read())
            if current_channel_object.use_baseline.read():
                self.samples_plot_baseline_start_line.show()
                self.samples_plot_baseline_start_line.setValue(current_channel_object.baseline_start_index.read())
                self.samples_plot_baseline_stop_line.show()
                self.samples_plot_baseline_stop_line.setValue(current_channel_object.baseline_stop_index.read())
        #current_chopper_index = int(self.c.read()[-1])
        #self.samples_plot_chopper_line = self.samples_plot_widget.add_infinite_line(color='y')

    def stop(self):
        pass
        
gui = Gui()


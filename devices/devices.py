### import ####################################################################


import os
import sys
import imp
import time
import copy
from distutils import util

import collections

import numpy as np

import scipy

import h5py

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import WrightTools as wt

import project.project_globals as g
main_dir = g.main_dir.read()
import project.classes as pc
import project.widgets as pw
import project.ini_handler as ini_handler
ini = ini_handler.daq
autocopy_ini = ini_handler.Ini(os.path.join(main_dir, 'devices', 'autocopy.ini'))
autocopy_ini.return_raw = True


### define ####################################################################


# dictionary of how to access all PyCMDS-compatible DAQ devices
# [module path, class name, initialization arguments, friendly name]
device_dict = collections.OrderedDict()
device_dict['NI 6251'] = [os.path.join(main_dir, 'devices', 'NI_6251', 'NI_6251.py'), 'Device', [None], 'ni6251']
device_dict['InGaAs array'] = [os.path.join(main_dir, 'devices', 'InGaAs_array', 'InGaAs.py'), 'Device', [None], 'InGaAs']

axes = pc.Mutex()

array_detector_reference = pc.Mutex()

origin = pc.Mutex()

# additional
loop_time = pc.Number(initial_value=np.nan, display=True, decimals=3)

idx = pc.Mutex()  # holds tuple

save_shots = pc.Bool(display=True)

ms_wait_limits = pc.NumberLimits(0, 10000)
ms_wait = pc.Number(ini=ini, section='settings', option='ms wait', decimals=0,
                    limits=ms_wait_limits, display=True)
                
# autocopy
enable = bool(util.strtobool(autocopy_ini.read('main', 'enable')))
path = autocopy_ini.read('main', 'path')
autocopy_enable = pc.Bool(initial_value=enable)
autocopy_path = pc.Filepath(initial_value=path, kind='directory')

                    
### classes ###################################################################
                    

class CurrentSlice(QtCore.QObject):
    indexed = QtCore.pyqtSignal()
    appended = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        
    def begin(self, shape):
        '''
        Tell current slice that a new scan is beginning. Mostly works to 
        reset y limits.
        
        Parameters
        ----------
        shape : list of ints
            Number of channels for all devices.
        '''
        self.xi = []
        self.data = []
        self.ymins = []
        self.ymaxs = []
        self.use_actual = False
        for n_channels in shape:
            self.ymins.append([-1e-6]*n_channels)
            self.ymaxs.append([1e-6]*n_channels)
        
    def index(self, d):
        '''
        Clear the old data from memory, and define new parameters for the next
        slice.
        
        Parameters
        ----------
        d : dictionary
            The new slice dictionary, passed all the way from the acquisition
            orderer module.
        '''
        self.name = str(d['name'])  # somehow a qstring is getting here? - Blaise 2016.07.27
        self.units = d['units']
        self.points = d['points']
        self.use_actual = d['use actual']
        self.xi = []
        self.data = []
        self.indexed.emit()
        
    def append(self, position, data):
        '''
        Add new values into the slice.
        
        Parameters
        ----------
        position : float
            The axis position (in the slices' own axis / units)
        data : list of lists of arrays
            List of 1) devices, 2) channels, containing arrays
        '''
        if self.use_actual:
            self.xi.append(position)
        else:
            self.xi.append(self.points[len(self.xi)])
        self.data.append(data)
        for device_index, device in enumerate(data):
            for channel_index, channel in enumerate(data[device_index]):
                minimum = np.min(data[device_index][channel_index])
                maximum = np.max(data[device_index][channel_index])
                if self.ymins[device_index][channel_index] > minimum:
                    self.ymins[device_index][channel_index] = minimum
                if self.ymaxs[device_index][channel_index] < maximum:
                    self.ymaxs[device_index][channel_index] = maximum
        self.appended.emit()

current_slice = CurrentSlice()


class Headers:

    def __init__(self):
        '''
        Contains all the seperate dictionaries that go into assembling file
        headers.
        '''
        self.clear()
        
    def clear(self):
        '''
        All dictionaries are now empty OrderedDicts.
        '''
        self.pycmds_info = collections.OrderedDict()
        self.scan_info = collections.OrderedDict()
        self.data_info = collections.OrderedDict()
        self.axis_info = collections.OrderedDict()
        self.constant_info = collections.OrderedDict()
        self.channel_info = collections.OrderedDict()
        self.daq_info = collections.OrderedDict()
        self.data_cols = collections.OrderedDict()
        self.shots_cols = collections.OrderedDict()
        
    def read(self, kind='data'):
        '''
        Assemble contained dictionaries into a single dictionary.
        
        Parameters
        ----------
        kind : {'data', 'shots'}  (optional)
            Which kind of dictionary to return. Default is data.
        '''
        # get correct cols dictionary
        if kind == 'data':
            cols = self.data_cols
            channel_info = self.channel_info
        elif kind == 'shots':
            cols = self.shots_cols
            channel_info = {}
        else:
            raise Exception('kind {} not recognized in daq.Headers.get'.format(kind))
        # assemble
        dicts = [self.pycmds_info, self.data_info, self.scan_info, 
                 self.axis_info, self.constant_info, channel_info,
                 self.daq_info, cols]
        out = collections.OrderedDict()
        for d in dicts:
            for key, value in d.items():
                out[key] = value
        return out

headers = Headers()


### file writing class ########################################################


data_busy = pc.Busy()

data_path = pc.Mutex()

enqueued_data = pc.Enqueued()

fit_path = pc.Mutex()

shot_path = pc.Mutex()


class FileAddress(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        if g.debug.read(): 
            print('data dequeue:', method)
        getattr(self, str(method))(inputs)  # method passed as qstring
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
        # unpack inputs        
        aqn, scan_folder = inputs
        file_index = 0
        # pixels --------------------------------------------------------------
        # file name
        file_index_str = str(file_index).zfill(3)
        self.filename = ' '.join([file_index_str]).rstrip()
        # create folder
        data_path.write(os.path.join(scan_folder, self.filename + '.data'))
        # generate file
        dictionary = headers.read(kind='data')
        wt.kit.write_headers(data_path.read(), dictionary)
        # shots ---------------------------------------------------------------
        # TODO: this is hack
        if aqn.has_section('NI 6251'):
            if aqn.read('NI 6251', 'save shots'):
                p = os.path.join(os.path.dirname(data_path.read()), 'NI 6251 shots.hdf5') 
                f = h5py.File(p)
                dictionary = headers.read(kind='shots')
                for key, value in dictionary.items():
                    # remove None
                    if type(value) is list:
                        for i, val in enumerate(value):
                            if val is None:
                                value[i] = 'None'
                            if isinstance(val, basestring):
                                value[i] = str(val)  # cannot handle unicode in lists...
                    # write to hdf5
                    f.attrs[key] = value
                col_count = len(dictionary['name'])
                f.create_dataset('array', (col_count, 0), maxshape=(col_count, None), compression='gzip')
                f['array'].set_fill_value = np.nan        
                f.close()

    def write_data(self, inputs):
        data_arr, shots_arr = inputs
        # pixels --------------------------------------------------------------
        data_file = open(data_path.read(), 'ab')
        if len(data_arr.shape) == 2:  # case of multidimensional devices
            for row in data_arr.T:
                np.savetxt(data_file, row, fmt=str('%8.6f'), delimiter='\t', newline='\t')
                data_file.write(b'\n')
        else:
            np.savetxt(data_file, data_arr, fmt=str('%8.6f'), delimiter='\t', newline='\t')
            data_file.write(b'\n')
        data_file.close()
        # shots ---------------------------------------------------------------
        p = os.path.join(os.path.dirname(data_path.read()), 'NI 6251 shots.hdf5')  # TODO: this is hack
        if os.path.isfile(p):
            f = h5py.File(p)
            current_row_count = f['array'].shape[1]
            new_row_count = shots_arr.shape[1]
            f['array'].resize(current_row_count+new_row_count, axis=1)
            f['array'][:, current_row_count:current_row_count+new_row_count] = shots_arr
            f.close()

    def initialize(self, inputs):
        pass
                      
    def shutdown(self, inputs):
        # TODO: ?
        pass

#begin address object in seperate thread
data_thread = QtCore.QThread()
data_obj = FileAddress()
data_obj.moveToThread(data_thread)
data_thread.start()

#create queue to communiate with address thread
data_queue = QtCore.QMetaObject()
def q(method, inputs = []):
    #add to friendly queue list 
    enqueued_data.push([method, time.time()])
    #busy
    data_busy.write(True)
    #send Qt SIGNAL to address thread
    data_queue.invokeMethod(data_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))


### device ####################################################################


class Device(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    settings_updated = QtCore.pyqtSignal()
    
    def __init__(self, inputs=[]):
        QtCore.QObject.__init__(self)
        # attributes
        self.active = False
        self.shape = (1,)
        self.has_map = False
        self.name = 'virtual'
        self.model = 'virtual'
        self.serial = None
        self.shots_compatible = False
        # mutex attributes
        self.busy = pc.Busy()
        self.busy.update_signal = self.update_ui
        self.data = pc.Data()
        self.nshots = pc.Number(initial_value=100)
        self.measure_time = pc.Number(initial_value=np.nan, display=True, decimals=3)
        self.Widget = Widget
        self.initialized = False
        self.freerun = pc.Bool(initial_value=False)
        self.settings_updated.emit()

    def close(self):
        self.thread.quit()

    def get_headers(self):
        out = collections.OrderedDict()
        out['shots'] = self.nshots.read()
        return out
        
    def initialize(self, parent_widget):
        print('DEVICE INITIALIZE BEGIN')
        self.enqueued = pc.Enqueued()
        self.driver = Driver(self)
        self.q = pc.Q(self.enqueued, self.busy, self.driver)
        self.thread = QtCore.QThread()
        self.driver.moveToThread(self.thread)
        self.thread.start()
        self.thread.setPriority(QtCore.QThread.HighestPriority)
        #self.q.push('initialize')
        self.q.push('measure')
        self.wait_until_done()
        self.freerun.updated.connect(lambda: self.q.push('loop'))
        self.update_ui.emit()
        self.driver.update_ui.connect(self.on_driver_update_ui)
        
    def load_settings(self, aqn):
        pass

    def measure(self):
        self.q.push('measure')
        
    def on_driver_update_ui(self):
        self.update_ui.emit()

    def set_freerun(self, state):
        self.freerun.write(state)
    
    def wait_until_done(self, timeout=10):
        """
        timeout in seconds (will only refer to timeout when
        busy.wait_for_update fires)
        """
        if True:
            start_time = time.time()
            while self.busy.read():
                print('DEVICE WAIT UNTIL DONE')
                QtCore.QThread.yieldCurrentThread()
                if time.time()-start_time < timeout:
                    self.busy.wait_for_update()
                else:
                    print('DEVICE WAIT UNTIL DONE TIMEOUT')
                    g.logger.log('warning', '%s wait until done timed out'%self.name, 'timeout set to {} seconds'.format(timeout))
                    break
        else:
            while self.busy.read():
                self.busy.wait_for_update()


### driver ####################################################################


class Driver(pc.Driver):
    task_changed = QtCore.pyqtSignal()
    running = False
    processing_timer = wt.kit.Timer(verbose=False)
    
    def __init__(self, device):
        QtCore.QObject.__init__(self)
        # attributes
        self.name = 'Virtual'
        self.enqueued = device.enqueued
        self.busy = device.busy
        self.freerun = device.freerun
        self.data = device.data
        self.shape = device.shape
        self.measure_time = device.measure_time
        self.measure()  # TODO: REMOVE THIS!!!
    
    def close(self):
        pass

    def initialize(self, *args, **kwargs):
        self.measure()

    def loop(self):
        while self.freerun.read() and not self.enqueued.read():
            self.measure([])
            self.busy.write(False)
        else:
            print(' '.join([self.name, 'exiting loop!']))

    def measure(self, *args, **kwargs):
        timer = wt.kit.Timer(verbose=False)
        with timer:
            time.sleep(0.1)
            out_names = ['channel %i'%i for i in range(5)]
            out = np.random.standard_normal(len(out_names))
            self.data.write_properties(self.shape, out_names, out)
        self.measure_time.write(timer.interval)
        self.update_ui.emit()


### gui #######################################################################


class Widget(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = pw.InputTable()
        input_table.add('Virtual', None)
        self.use = pc.Bool(initial_value=True)
        input_table.add('Use', self.use)
        layout.addWidget(input_table)
        
    def load(self, aqn_path):
        pass
   
    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section('virtual')
        ini.write('virtual', 'use', self.use.read())

        
class GUI(QtCore.QObject):

    def __init__(self, control):
        QtCore.QObject.__init__(self)
        self.control = control
        self.samples_tab_initialized = False

    def close(self):
        pass

    def create_frame(self, parent_widget):
        # get layout
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        self.layout = parent_widget.layout()


### control ###################################################################


class Control(QtCore.QObject):
    """
    Only one instance in the entire program.
    """
    settings_updated = QtCore.pyqtSignal()    
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.devices = []
        g.main_window.read().queue_control.connect(self.queue_control_update)
        self.channel_names = []
        # import devices
        if False:
            for key in device_dict.keys():
                if ini.read('device', key):
                    lis = device_dict[key]
                    module_path = lis[0]
                    name = os.path.basename(module_path).split('.')[0]
                    if False:
                        directory = os.path.dirname(module_path)
                        f, p, d = imp.find_module(name, [directory])
                        device_module = imp.load_module(name, f, p, d)
                    else:
                        device_module = imp.load_source(name, module_path)
                    device_class = getattr(device_module, lis[1])
                    device_obj = device_class(inputs=lis[2])
                    self.devices.append(device_obj)
        else:
            self.devices.append(Device())
        # signals and slots
        for device in self.devices:
            device.settings_updated.connect(self.on_device_settings_updated)
    
    def acquire(self, save=False, index=None):
        # loop time
        now = time.time()
        loop_time.write(now - self.t_last)
        self.t_last = now
        # ms wait
        time.sleep(ms_wait.read()/1000.)
        # acquire
        for device in self.devices:
            if device.active:
                device.measure()
        self.wait_until_done()
        # save
        if save:
            # 1D things -------------------------------------------------------
            data_rows = np.prod([d.data.size for d in self.devices if d.active])
            data_shape = (len(headers.data_cols['name']), data_rows)
            data_arr = np.full(data_shape, np.nan)
            shots_rows = int(np.prod([d.nshots.read() if d.active and d.shots_compatible else 1 for d in self.devices]))
            shots_shape = (len(headers.shots_cols['name']), shots_rows)
            shots_arr = np.full(shots_shape, np.nan)
            data_i = 0
            shots_i = 0
            # scan indicies
            for i in idx.read():  # scan device
                data_arr[data_i] = i
                shots_arr[shots_i] = i
                data_i += 1
                shots_i += 1
            for device in self.devices:  # daq
                if device.active and device.has_map:
                    map_indicies = [i for i in np.ndindex(device.data.shape)]
                    for i in range(len(device.data.shape)):
                        data_arr[data_i] = [mi[i] for mi in map_indicies]
                        data_i += 1
                        if device.shots_compatible:
                            shots_arr[shots_i] = [mi[i] for mi in map_indicies]
                            shots_i += 1
            shots_arr[shots_i] = range(shots_rows)
            shots_i += 1
            # time
            now = time.time()  # seconds since epoch
            data_arr[data_i] = now
            data_i += 1
            shots_arr[shots_i] = now
            shots_i += 1
            # hardware positions
            for scan_hardware_module in scan_hardware_modules:
                for scan_hardware in scan_hardware_module.hardwares:
                    for key in scan_hardware.recorded:
                        out_units = scan_hardware.recorded[key][1]
                        if out_units is None:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read()
                            shots_arr[shots_i] = scan_hardware.recorded[key][0].read()
                        else:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read(out_units)
                            shots_arr[shots_i] = scan_hardware.recorded[key][0].read(out_units)
                        data_i += 1
                        shots_i += 1
            # potentially multidimensional things -----------------------------
            # TODO: shots_arr should be a DICTIONARY of arrays for each device
            # acquisition maps
            for device in self.devices:
                if device.active and device.has_map:
                    data_arr[data_i] = device.get_map()
                    data_i += 1
                    if device.shots_compatible:
                        shots_arr[shots_i] = device.get_map()
                        shots_i += 1
            # acquisitions
            for device in self.devices:
                if device.active:
                    # data
                    channels = device.data.read()  # list of arrays
                    for arr in channels:
                        data_arr[data_i] = arr
                        data_i += 1
                    # shots
                    if device.shots_compatible:
                        channels = device.shots.read()  # list of arrays
                        for arr in channels:
                            shots_arr[shots_i] = arr
                            shots_i += 1
            # send to file_address --------------------------------------------
            q('write_data', [data_arr, shots_arr])
            # fill slice ------------------------------------------------------
            slice_axis_index = headers.data_cols['name'].index(current_slice.name)
            slice_position = np.mean(data_arr[slice_axis_index])
            native_units = headers.data_cols['units'][slice_axis_index]
            slice_position = wt.units.converter(slice_position, native_units, current_slice.units)
            data_arrs = []
            for device in self.devices:
                data_arrs.append(device.data.read())
            current_slice.append(slice_position, data_arrs)
        
    def initialize(self):
        print('DEVICE CONTROL INITIALIZE BEGIN')
        # initialize own gui
        self.gui = GUI(self)
        device_widgets = self.gui.device_widgets
        # initialize devices
        for i, device in enumerate(self.devices):
            device.initialize(device_widgets[i])
            device.active = True
        # begin freerunning
        self.set_freerun(True)
        # Ideally I would wait for the devices here
        # however the NI 6251 hangs forever for reasons I don't understand
        # finish
        self.wait_until_done()  # TODO:...
        time.sleep(3)
        for i, device in enumerate(self.devices):
            device.update_ui.connect(self.gui.create_main_tab)
        self.t_last = time.time()
        # fill out channel names
        for device in self.devices:
            for channel_name in device.data.cols:
                self.channel_names.append(channel_name)
        self.settings_updated.emit()
        print('DEVICE CONTROL INITIALIZE COMPLETE', self.channel_names)
        
    def initialize_scan(self, aqn, scan_folder, destinations_list):
        timestamp = wt.kit.TimeStamp()
        # stop freerunning
        self.set_freerun(False)
        # fill out pycmds_information in headers
        headers.pycmds_info['PyCMDS version'] = g.version.read()
        headers.pycmds_info['system name'] = g.system_name.read()
        headers.pycmds_info['file created'] = timestamp.RFC3339
        # apply device settings from aqn
        ms_wait.write(aqn.read('device settings', 'ms wait'))
        for device in self.devices:
            if not aqn.has_section(device.name):
                device.active = False
                continue
            if not aqn.read(device.name, 'use'):
                device.active = False
                continue
            # apply settings from aqn to device
            device.active = True
            device.load_settings(aqn)
            # record device axes, if applicable
            if device.has_map:
                for key in device.map_axes.keys():
                    # add axis
                    headers.axis_info['axis names'].append(key)
                    identity, units, points, centers, interpolate = device.get_axis_properties(destinations_list)
                    headers.axis_info['axis identities'].append(identity)
                    headers.axis_info['axis units'].append(units)
                    headers.axis_info['axis interpolate'].append(interpolate)
                    headers.axis_info[' '.join([key, 'points'])] = points
                    if centers is not None:
                        headers.axis_info[' '.join([key, 'centers'])] = centers
                    # expand exisiting axes (not current axis)
                    for subkey in headers.axis_info.keys():
                        if 'centers' in subkey and key not in subkey:
                            centers = headers.axis_info[subkey]
                            centers = np.expand_dims(centers, axis=-1)
                            centers = np.repeat(centers, points.size, axis=-1)
                            headers.axis_info[subkey] = centers
        # add cols information
        self.update_cols(aqn)
        # add channel signed choices
        # TODO: better implementation. for now, just assume not signed
        headers.channel_info['channel signed'] = [False for kind in headers.data_cols['kind'] if kind == 'channel']
        # add daq information to headers
        for device in self.devices:
            if device.active:
                for key, value in device.get_headers().items():
                    headers.daq_info[' '.join([device.name, key])] = value
        q('create_data', [aqn, scan_folder])
        # refresh current slice properties
        current_slice.begin([len(device.data.cols) for device in self.devices])
        # wait until daq is done before letting module continue
        self.wait_until_done()
        self.wait_until_file_done()
    
    def on_device_settings_updated(self):
        self.channel_names = []
        for device in self.devices:
            for channel_name in device.data.cols:
                self.channel_names.append(channel_name)
        self.settings_updated.emit()
        print('channel names', self.channel_names)

    def queue_control_update(self):
        if g.queue_control.read():
            self.set_freerun(False)
            self.wait_until_done()
        else:
            # TODO: something better...
            self.set_freerun(True)

    def set_freerun(self, state):
        for device in self.devices:
            device.set_freerun(state)
    
    def shutdown(self):
        # TODO
        pass
    
    def update_cols(self, aqn):
        for cols_type in ['data', 'shots']:
            kind = []
            tolerance = []
            units = []
            label = []
            name = []
            # indicies
            for n in headers.axis_info['axis names']:
                kind.append(None)
                tolerance.append(None)
                units.append(None)
                label.append('')
                name.append('_'.join([n, 'index']))
            if cols_type == 'shots':
                # shot indicies
                for device in self.devices:
                    if device.shots_compatible:
                        kind.append(None)
                        tolerance.append(None)
                        units.append(None)
                        label.append('')
                        name.append('_'.join([device.name, 'shot', 'index']))
            # time
            kind.append(None)
            tolerance.append(0.01)
            units.append('s')
            label.append('lab')
            name.append('time')
            # scan hardware positions
            for scan_hardware_module in scan_hardware_modules:
                for scan_hardware in scan_hardware_module.hardwares:
                    for key in scan_hardware.recorded:
                        kind.append('hardware')
                        tolerance.append(scan_hardware.recorded[key][2])
                        units.append(scan_hardware.recorded[key][1])
                        label.append(scan_hardware.recorded[key][3])
                        name.append(key)
            # acquisition maps
            for device in self.devices:
                if not aqn.has_section(device.name):
                    continue
                if not aqn.read(device.name, 'use'):
                    continue
                if device.has_map:
                    for i in range(len(device.map_axes)):
                        kind.append('hardware')
                        tolerance.append(None)
                        units.append(device.map_axes.values()[i][1])
                        label.append(device.map_axes.values()[i][0])
                        name.append(device.map_axes.keys()[i])
            # channels
            self.channel_names = []
            for device in self.devices:
                print(device.name, aqn.has_section(device.name))
                if not aqn.has_section(device.name):
                    continue
                if not aqn.read(device.name, 'use'):
                    continue
                if device.shots_compatible and cols_type == 'shots':
                    mutex = device.shots
                else:
                    mutex = device.data
                for col in mutex.cols:
                    kind.append('channel')
                    tolerance.append(None)
                    units.append('')  # TODO: better units support?
                    label.append('')  # TODO: ?
                    name.append(col)
                    self.channel_names.append(col)
            # clean up
            for i, s in enumerate(label):
                label[i] = s.replace('prime', r'\'')
            # finish
            if cols_type == 'data':
                cols = headers.data_cols
            elif cols_type == 'shots':
                cols = headers.shots_cols
            cols['kind'] = kind
            cols['tolerance'] = tolerance
            cols['label'] = label
            cols['units'] = units
            cols['name'] = name
        self.on_device_settings_updated()            
            
    def wait_until_file_done(self):
        while data_busy.read():
            data_busy.wait_for_update()
            
    def wait_until_done(self):
        '''
        Wait until the acquisition devices are no longer busy. Does not wait
        for the file writing queue to empty.
        '''
        for device in self.devices:
            if device.active:
                device.wait_until_done()

control = Control()


### gui #######################################################################


class Widget(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        # daq settings
        input_table = pw.InputTable()
        input_table.add('Device Settings', None)
        self.ms_wait = pc.Number(initial_value=0, limits=ms_wait_limits, 
                                 decimals=0, disable_under_queue_control=True)
        input_table.add('ms Wait', self.ms_wait)
        layout.addWidget(input_table)
        # device settings
        self.device_widgets = []
        for device in control.devices:
            widget = device.Widget()
            layout.addWidget(widget)
            self.device_widgets.append(widget)

    def load(self, aqn_path):
        # TODO:
        print('load_device_settings')
   
    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section('device settings')
        ini.write('device settings', 'ms wait', self.ms_wait.read())
        for device_widget in self.device_widgets:
            device_widget.save(aqn_path)
        
        
class DisplaySettings(QtCore.QObject):
    updated = QtCore.pyqtSignal()
    
    def __init__(self, device):
        '''
        Display settings for a particular device.
        '''
        QtCore.QObject.__init__(self)
        self.device = device
        #self.device.wait_until_done()
        self.widget = pw.InputTable()
        self.channel_combo = pc.Combo()
        self.channel_combo.updated.connect(lambda: self.updated.emit())
        self.widget.add('Channel', self.channel_combo)
        self.shape_controls = []
        if self.device.shape != (1,):
            map_axis_names = self.device.map_axes.keys()
            for i in range(len(self.device.shape)):
                limits = pc.NumberLimits(0, self.device.shape[i]-1)
                control = pc.Number(initial_value=0, decimals=0, limits=limits)
                self.widget.add(' '.join([map_axis_names[i], 'index']), control)
                self.shape_controls.append(control)
                control.updated.connect(lambda: self.updated.emit())
    
    def get_channel_index(self):
        return self.channel_combo.read_index()
        
    def get_map_index(self):
        if len(self.shape_controls) == 0:
            return None
        return tuple(c.read() for c in self.shape_controls)
    
    def hide(self):
        self.widget.hide()

    def show(self):
        self.widget.show()

    def update_channels(self):
        allowed_values = self.device.data.read_properties()[1]
        if not len(allowed_values) == 0:
            self.channel_combo.set_allowed_values(allowed_values)


class GUI(QtCore.QObject):

    def __init__(self, control):
        QtCore.QObject.__init__(self)
        self.control = control
        self.create_frame()
        self.main_tab_created = False

    def create_frame(self):
        # scan widget
        self.main_widget = QtGui.QWidget()
        # device widgets
        # get parent widget
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        self.parent_widget = parent_widget
        layout = parent_widget.layout()
        # create tab structure
        self.tabs = QtGui.QTabWidget()
        # create tabs for each device
        self.device_widgets = []
        for device in self.control.devices:
            widget = QtGui.QWidget()
            self.tabs.addTab(widget, device.name)
            self.device_widgets.append(widget)
        # finish
        layout.addWidget(self.tabs)
        
    def create_main_tab(self):
        if self.main_tab_created:
            return
        for device in control.devices:
            if len(device.data.read_properties()[1]) == 0:
                print('next time')
                return
        self.main_tab_created = True
        # create main daq tab
        main_widget = self.main_widget
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(layout)
        # display -------------------------------------------------------------
        # container widget
        display_container_widget = pw.ExpandingWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        # big number
        big_number_container_widget = QtGui.QWidget()
        big_number_container_widget.setLayout(QtGui.QHBoxLayout())
        big_number_container_layout = big_number_container_widget.layout()
        big_number_container_layout.setMargin(0)
        big_number_container_layout.addStretch(1)
        self.big_display = pw.SpinboxAsDisplay(font_size=100)
        big_number_container_layout.addWidget(self.big_display)
        display_layout.addWidget(big_number_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_scatter = self.plot_widget.add_scatter()
        self.plot_line = self.plot_widget.add_line()
        display_layout.addWidget(self.plot_widget)
        # vertical line -------------------------------------------------------
        line = pw.line('V')      
        layout.addWidget(line)
        # settings ------------------------------------------------------------
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
        # display settings
        input_table = pw.InputTable()
        input_table.add('Display', None)
        allowed_values = [device.name for device in control.devices]
        self.device_combo = pc.Combo(allowed_values=allowed_values)
        self.device_combo.updated.connect(self.on_update_device)
        input_table.add('Device', self.device_combo)
        settings_layout.addWidget(input_table)
        self.display_settings_widgets = collections.OrderedDict()
        for device in control.devices:
            display_settings = DisplaySettings(device)
            self.display_settings_widgets[device.name] = display_settings
            settings_layout.addWidget(display_settings.widget)
            device.settings_updated.connect(self.on_update_channels)
            display_settings.updated.connect(self.on_update_device)
        # global daq settings
        input_table = pw.InputTable()
        input_table.add('Settings', None)
        input_table.add('ms Wait', ms_wait)
        for device in control.devices:
            input_table.add(device.name, None)
            input_table.add('Status', device.busy)
            input_table.add('Freerun', device.freerun)
            input_table.add('Time', device.measure_time)
        input_table.add('File', None)
        data_busy.update_signal = data_obj.update_ui        
        input_table.add('Status', data_busy)
        input_table.add('Autocopy', autocopy_enable)
        input_table.add('Autocopy Path', autocopy_path)
        input_table.add('Scan', None)
        input_table.add('Loop Time', loop_time)
        self.idx_string = pc.String(initial_value='None', display=True)
        input_table.add('Scan Index', self.idx_string)
        settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)
        # finish --------------------------------------------------------------
        self.on_update_channels()
        self.on_update_device()
        for device in self.control.devices:
            device.update_ui.connect(self.update)
        current_slice.indexed.connect(self.on_slice_index)
        current_slice.appended.connect(self.on_slice_append)
        autocopy_enable.updated.connect(self.on_autocopy_updated)
        autocopy_path.updated.connect(self.on_autocopy_updated)
        self.on_autocopy_updated()

    def on_autocopy_updated(self):
        enable = str(autocopy_enable.read())
        path = autocopy_path.read()
        autocopy_ini.write('main', 'enable', enable)
        autocopy_ini.write('main', 'path', path)

    def on_slice_append(self):
        device_index = self.device_combo.read_index()
        device_display_settings = list(self.display_settings_widgets.values())[device_index]
        channel_index = device_display_settings.channel_combo.read_index()
        # limits
        ymin = current_slice.ymins[device_index][channel_index]
        ymax = current_slice.ymaxs[device_index][channel_index]
        self.plot_widget.set_ylim(ymin, ymax)
        # data
        xi = current_slice.xi
        # TODO: in case of device with shape...
        yi = [current_slice.data[i][device_index][channel_index] for i, _ in enumerate(xi)]
        # finish
        self.plot_scatter.setData(xi, yi)
        self.plot_line.setData(xi, yi)
        
    def on_slice_index(self):
        xlabel = '{0} ({1})'.format(current_slice.name, current_slice.units)
        self.plot_widget.set_labels(xlabel=xlabel)
        xmin = min(current_slice.points)
        xmax = max(current_slice.points)
        self.plot_widget.set_xlim(xmin, xmax)

    def on_update_channels(self):
        for display_settings in self.display_settings_widgets.values():
            display_settings.update_channels()
            
    def on_update_device(self):
        current_device_index = self.device_combo.read_index()
        for display_settings in self.display_settings_widgets.values():
            display_settings.hide()
        list(self.display_settings_widgets.values())[current_device_index].show()
        self.update()
        
    def update(self):
        '''
        Runs each time an update_ui signal fires (basically every run_task)
        '''
        # scan index
        self.idx_string.write(str(idx.read()))
        # big number
        current_device_index = self.device_combo.read_index()
        device = control.devices[current_device_index]        
        widget = list(self.display_settings_widgets.values())[current_device_index]
        channel_index = widget.get_channel_index()
        map_index = widget.get_map_index()
        if map_index is None:
            big_number = device.data.read()[channel_index]
        else:
            big_number = device.data.read()[channel_index][map_index]
        self.big_display.setValue(big_number)    

    def stop(self):
        pass


### start devices #############################################################


control.initialize()

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import hardware.delays.delays as delays
import hardware.filters.filters as filters
scan_hardware_modules = [opas, spectrometers, delays, filters]

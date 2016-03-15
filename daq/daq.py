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
import pyqtgraph as pg

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import project.ini_handler as ini
ini = ini.daq
main_dir = g.main_dir.read()


### define ####################################################################


# dictionary of how to access all PyCMDS-compatible DAQ devices
# [module path, class name, initialization arguments, friendly name]
device_dict = collections.OrderedDict()
device_dict['NI 6251'] = [os.path.join(main_dir, 'daq', 'NI_6251', 'NI_6251.py'), 'Device', [None], 'ni6251']
device_dict['InGaAs array'] = [os.path.join(main_dir, 'daq', 'InGaAs_array', 'InGaAs.py'), 'Device', [None], 'InGaAs']

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
        self.name = d['name']
        self.units = d['units']
        self.points = d['points']
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
        self.xi.append(position)
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
            print 'data dequeue:', method
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
        daq_widget = inputs[0]        
        # get info
        timestamp = headers.pycmds_info['file created']
        origin = headers.data_info['data origin']
        axes = str(headers.axis_info['axis names'])
        description = daq_widget.description.read()
        # generate file name
        self.filename = ' '.join([origin, axes, timestamp, description]).rstrip()
        self.filename = self.filename.replace('\'', '')
        # create folder
        data_folder = os.path.join(main_dir, 'data', self.filename)
        os.mkdir(data_folder)
        data_path.write(os.path.join(data_folder, self.filename + '.data'))
        # generate file
        dictionary = headers.read(kind='data')
        wt.kit.write_headers(data_path.read(), dictionary)
    
    def create_shots(self, inputs):
        # create shots must always be called after create data
        shot_path.write(data_path.read().replace('.data', '.shots'))
        dictionary = headers.read(kind='shots')
        wt.kit.write_headers(shot_path.read(), dictionary)
            
    def write_data(self, inputs):
        data_file = open(data_path.read(), 'a')
        if len(inputs[0].shape) == 2:
            for row in inputs[0].T:
                np.savetxt(data_file, row, fmt='%8.6f', delimiter='\t', newline = '\t')
                data_file.write('\n')
        else:
            np.savetxt(data_file, inputs, fmt='%8.6f', delimiter='\t', newline = '\t')
            data_file.write('\n')
        data_file.close()
        
    def write_shots(self, inputs):
        data_file = open(shot_path.read(), 'a')
        for row in inputs[0].T:
            np.savetxt(data_file, row, fmt='%8.6f', delimiter='\t', newline = '\t')
            data_file.write('\n')
        data_file.close()

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


### control ###################################################################


class Control():
    
    def __init__(self):
        self.devices = []
        g.main_window.read().module_control.connect(self.module_control_update)
        # import devices
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
    
    def acquire(self, save=False):
        # loop time
        now = time.time()
        loop_time.write(now - self.t_last)
        self.t_last = now
        # ms wait
        time.sleep(ms_wait.read()/1000.)
        # acquire
        for device in self.devices:
            if device.active:
                device.acquire()
        self.wait_until_done()
        # save
        if save:
            # TODO: everyting related to shots
            # 1D things -------------------------------------------------------
            data_rows = np.prod([d.data.size for d in self.devices if d.active])
            data_shape = (len(headers.data_cols['name']), data_rows)
            data_arr = np.full(data_shape, np.nan)
            data_i = 0
            # scan indicies
            for i in idx.read():  # scan device
                data_arr[data_i] = i
                data_i += 1
            for device in self.devices:  # daq
                if device.active and device.has_map:
                    map_indicies = [i for i in np.ndindex(device.data.shape)]
                    for i in range(len(device.data.shape)):
                        data_arr[data_i] = [mi[i] for mi in map_indicies]
                        data_i += 1
            # time
            data_arr[data_i] = time.time()  # seconds since epoch
            data_i += 1
            # hardware positions
            for scan_hardware_module in scan_hardware_modules:
                for scan_hardware in scan_hardware_module.hardwares:
                    for key in scan_hardware.recorded:
                        out_units = scan_hardware.recorded[key][1]
                        if out_units is None:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read()
                        else:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read(out_units)
                        data_i += 1
            # potentially multidimensional things -----------------------------
            # acquisition maps
            for device in self.devices:
                if device.active and device.has_map:
                    data_arr[data_i] = device.get_map()
                    data_i += 1
            # acquisitions
            for device in self.devices:
                if device.active:
                    channels = device.data.read()  # list of arrays
                    for arr in channels:
                        data_arr[data_i] = arr
                        data_i += 1
            # send to file_address
            q('write_data', [data_arr])
            # fill slice
            slice_axis_index = headers.data_cols['name'].index(current_slice.name)
            slice_position = np.mean(data_arr[slice_axis_index])
            native_units = headers.data_cols['units'][slice_axis_index]
            slice_position = wt.units.converter(slice_position, native_units, current_slice.units)
            data_arrs = []
            for device in self.devices:
                data_arrs.append(device.data.read())
            current_slice.append(slice_position, data_arrs)
        
    def initialize(self):
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
        for i, device in enumerate(self.devices):
            device.update_ui.connect(self.gui.create_main_tab)
        self.t_last = time.time()
        
    def initialize_scan(self, widget, destinations_list):
        # stop freerunning
        self.set_freerun(False)
        # fill out pycmds_information in headers
        headers.pycmds_info['PyCMDS version'] = g.version.read()
        headers.pycmds_info['system name'] = g.system_name.read()
        headers.pycmds_info['file created'] = wt.kit.get_timestamp()
        # apply daq settings from widget
        ms_wait.write(widget.ms_wait.read())
        save_shots.write(widget.save_shots.read())
        # add acquisition axes
        for device, device_widget in zip(self.devices, widget.device_widgets):
            if device_widget.use.read():
                # apply settings from widget to device
                device.active = True
                device.apply_settings_from_widget(device_widget)
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
            else:
                device.active = False
        # add cols information
        self.update_cols(widget)
        # add channel signed choices
        # TODO: better implementation. for now, just assume not signed
        headers.channel_info['channel signed'] = [False for kind in headers.data_cols['kind'] if kind == 'channel']
        # add daq information to headers
        for device in self.devices:
            if device.active:
                for key, value in device.get_headers().items():
                    headers.daq_info[' '.join([device.name, key])] = value
        # create files
        q('create_data', [widget])
        # refresh current slice properties
        current_slice.begin([len(device.data.cols) for device in self.devices])
        # wait until daq is done before letting module continue
        self.wait_until_done()
        self.wait_until_file_done()
        
    def module_control_update(self):
        if g.module_control.read():
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
    
    def update_cols(self, widget):
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
            for device, device_widget in zip(self.devices, widget.device_widgets):
                if device_widget.use.read():
                    if device.has_map:
                        for i in range(len(device.map_axes)):
                            kind.append('hardware')
                            tolerance.append(None)
                            units.append(device.map_axes.values()[i][1])
                            label.append(device.map_axes.values()[i][0])
            # acquisitions
            for device, device_widget in zip(self.devices, widget.device_widgets):
                if device_widget.use.read():
                    if device.shots_compatible and cols_type == 'shots':
                        mutex = device.shots
                    else:
                        mutex = device.data
                    for col in mutex.cols:
                        kind.append('channel')
                        tolerance.append(None)
                        units.append('V')  # TODO: better units support?
                        label.append('')  # TODO: ?
                        name.append(col)
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
        input_table.add('DAQ Settings', None)
        self.ms_wait = pc.Number(initial_value=0, limits=ms_wait_limits, 
                                 decimals=0, disable_under_module_control=True)
        input_table.add('ms Wait', self.ms_wait)
        layout.addWidget(input_table)
        # device settings
        self.device_widgets = []
        for device in control.devices:
            widget = device.Widget()
            layout.addWidget(widget)
            self.device_widgets.append(widget)
        # file
        input_table = pw.InputTable()
        input_table.add('File', None)
        self.save_shots = pc.Bool(disable_under_module_control=True)
        self.save_shots.set_disabled(True)
        input_table.add('Save Shots', self.save_shots)
        self.description = pc.String(disable_under_module_control=True)
        input_table.add('Description', self.description)
        self.name = pc.String(disable_under_module_control=True)
        input_table.add('Name', self.name)
        self.info = pc.String(disable_under_module_control=True)
        input_table.add('Info', self.info)
        layout.addWidget(input_table)
        
        
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
        # get parent widget
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
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
                print 'next time'
                return
        self.main_tab_created = True
        print 'create main tab'
        # create main daq tab
        main_widget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(layout)
        self.tabs.addTab(main_widget, 'Main')
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
            input_table.add('Time', device.acquisition_time)
        input_table.add('File', None)
        data_busy.update_signal = data_obj.update_ui        
        input_table.add('Status', data_busy)
        input_table.add('Save Shots', save_shots)
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
        # set tab structure to display main tab
        self.tabs.setCurrentIndex(self.tabs.count()-1)  # zero indexed

    def on_slice_append(self):
        device_index = self.device_combo.read_index()
        device_display_settings = self.display_settings_widgets.values()[device_index]
        channel_index = device_display_settings.channel_combo.read_index()
        # limits
        ymin = current_slice.ymins[device_index][channel_index]
        ymax = current_slice.ymaxs[device_index][channel_index]
        self.plot_widget.set_ylim(ymin, ymax)
        # data
        xi = current_slice.xi
        # TODO: in case of multidimensional devices...
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
        self.display_settings_widgets.values()[current_device_index].show()
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
        widget = self.display_settings_widgets.values()[current_device_index]
        channel_index = widget.get_channel_index()
        map_index = widget.get_map_index()
        if map_index is None:
            big_number = device.data.read()[channel_index]
        else:
            big_number = device.data.read()[channel_index][map_index]
        self.big_display.setValue(big_number)    

    def stop(self):
        pass


### start daq #################################################################


control.initialize()

import opas.opas as opas
import spectrometers.spectrometers as spectrometers
import delays.delays as delays
scan_hardware_modules = [opas, spectrometers, delays]

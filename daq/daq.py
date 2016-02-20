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
import opas.opas as opas
import spectrometers.spectrometers as spectrometers
import delays.delays as delays
scan_hardware_modules = [opas, spectrometers, delays]
app = g.app.read()
main_dir = g.main_dir.read()
ini = ini.daq


### define ####################################################################


# dictionary of how to access all PyCMDS-compatible DAQ hardwares
# [module path, class name, initialization arguments, friendly name]
hardware_dict = collections.OrderedDict()
hardware_dict['NI 6255'] = [os.path.join(main_dir, 'daq', 'NI_6255', 'NI_6255.py'), 'Hardware', [None], 'ni6255']
hardware_dict['InGaAs array'] = [os.path.join(main_dir, 'daq', 'InGaAs_array', 'InGaAs.py'), 'Hardware', [None], 'InGaAs'] 



axes = pc.Mutex()

array_detector_reference = pc.Mutex()

origin = pc.Mutex()

# additional
seconds_since_last_task = pc.Number(initial_value=np.nan, display=True, decimals=3)
seconds_for_acquisition = pc.Number(initial_value=np.nan, display=True, decimals=3)

idx = pc.Mutex()  # holds tuple


### file writing class ########################################################


data_busy = pc.Busy()

data_path = pc.Mutex()

enqueued_data = pc.Enqueued()

fit_path = pc.Mutex()

shot_path = pc.Mutex()


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
        #cleanly shut down
        #all hardware classes must have this
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
        self.hardwares = []
        g.main_window.read().module_control.connect(self.module_control_update)
        # import hardwares
        for key in hardware_dict.keys():
            if ini.read('hardware', key):
                lis = hardware_dict[key]
                module_path = lis[0]
                name = os.path.basename(module_path).split('.')[0]
                if False:
                    directory = os.path.dirname(module_path)
                    f, p, d = imp.find_module(name, [directory])
                    hardware_module = imp.load_module(name, f, p, d)
                else:
                    hardware_module = imp.load_source(name, module_path)
                hardware_class = getattr(hardware_module, lis[1])
                hardware_obj = hardware_class(inputs=lis[2])
                self.hardwares.append(hardware_obj)
    
    def acquire(self, save=False):
        for hardware in self.hardwares:
            if hardware.active:
                hardware.acquire()
        self.wait_until_done()
        if save:
            # TODO: everyting related to shots
            # 1D things -------------------------------------------------------
            data_rows = np.prod([h.data.size for h in self.hardwares if h.active])
            data_shape = (len(headers.data_cols['name']), data_rows)
            data_arr = np.full(data_shape, np.nan)
            data_i = 0
            # scan indicies
            for i in idx.read():  # scan hardware
                data_arr[data_i] = i
                data_i += 1
            for hardware in self.hardwares:  # daq
                if hardware.active and hardware.has_map:
                    map_indicies = [i for i in np.ndindex(hardware.data.shape)]
                    for i in range(len(hardware.data.shape)):
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
            for hardware in self.hardwares:
                if hardware.active and hardware.has_map:
                    data_arr[data_i] = hardware.get_map()
                    data_i += 1
            # acquisitions
            for hardware in self.hardwares:
                if hardware.active:
                    channels = hardware.data.read()  # list of arrays
                    for arr in channels:
                        data_arr[data_i] = arr
                        data_i += 1
            # send to file_address
            q('write_data', [data_arr])

    def index_slice(self):
        # TODO:
        pass

    def initialize(self):
        # initialize own gui
        self.gui = GUI(self)
        hardware_widgets = self.gui.hardware_widgets
        # initialize hardwares
        for i, hardware in enumerate(self.hardwares):
            hardware.initialize(hardware_widgets[i])
        # begin freerunning
        self.set_freerun(True)
        print '1 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
        print self.hardwares[0].data.read_properties()
        # finish
        self.wait_until_done()
        self.gui.create_main_tab()
        
    def initialize_scan(self, widget, destinations_list):
        # stop freerunning
        self.set_freerun(False)
        # fill out pycmds_information in headers
        headers.pycmds_info['PyCMDS version'] = g.version.read()
        headers.pycmds_info['system name'] = g.system_name.read()
        headers.pycmds_info['file created'] = wt.kit.get_timestamp()
        # add acquisition axes
        for hardware, hardware_widget in zip(self.hardwares, widget.hardware_widgets):
            if hardware_widget.use.read():
                # TODO: apply settings from widget to hardware
                hardware.active = True
                if hardware.has_map:
                    for key in hardware.map_axes.keys():
                        # add axis
                        headers.axis_info['axis names'].append(key)
                        identity, units, points, centers, interpolate = hardware.get_axis_properties(destinations_list)
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
                hardware.active = False
        # TODO: expand existing axes...
        # see https://github.com/wright-group/PyCMDS/blob/blaise-active/modules/scan.py#L206
        # add cols information
        self.update_cols(widget)
        # add channel signed choices
        # TODO: better implementation. for now, just assume not signed
        headers.channel_info['channel signed'] = [False for kind in headers.data_cols['kind'] if kind == 'channel']
        # add daq information to headers
        for hardware in self.hardwares:
            if hardware.active:
                for key, value in hardware.get_headers().items():
                    headers.daq_info[' '.join([hardware.name, key])] = value
        # create files
        q('create_data', [widget])
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
        for hardware in self.hardwares:
            hardware.set_freerun(state)
    
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
            for hardware, hardware_widget in zip(self.hardwares, widget.hardware_widgets):
                if hardware_widget.use.read():
                    if hardware.has_map:
                        for i in range(len(hardware.map_axes)):
                            kind.append('hardware')
                            tolerance.append(None)
                            units.append(hardware.map_axes.values()[i][1])
                            label.append(hardware.map_axes.values()[i][0])
                            name.append(hardware.map_axes.keys()[i])
            # acquisitions
            for hardware, hardware_widget in zip(self.hardwares, widget.hardware_widgets):
                if hardware_widget.use.read():
                    for col in hardware.data.cols:
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
        Wait until the acquisition hardwares are no longer busy. Does not wait
        for the file writing queue to empty.
        '''
        for hardware in self.hardwares:
            if hardware.active:
                hardware.wait_until_done()

control = Control()


### gui########################################################################


class Widget(QtGui.QWidget):
    # TODO: make the widget modular
    # perhaps the widget actually belongs in scan.py?

    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        # hardware
        self.hardware_widgets = []
        for hardware in control.hardwares:
            widget = hardware.Widget()
            layout.addWidget(widget)
            self.hardware_widgets.append(widget)
        # file
        input_table = pw.InputTable()
        input_table.add('File', None)
        self.save_shots = pc.Bool(disable_under_module_control=True)
        input_table.add('Save Shots', self.save_shots)
        self.description = pc.String(disable_under_module_control=True)
        input_table.add('Description', self.description)
        self.name = pc.String(disable_under_module_control=True)
        input_table.add('Name', self.name)
        self.info = pc.String(disable_under_module_control=True)
        input_table.add('Info', self.info)
        layout.addWidget(input_table)
        
        
class DisplaySettings:
    
    def __init__(self, device):
        '''
        Display settings for a particular device.
        '''
        self.device = device
        self.device.wait_until_done()
        self.widget = pw.InputTable()
        self.channel_combo = pc.Combo()
        self.widget.add('Channel', self.channel_combo)
        self.shape_controls = []
        if self.device.shape != (1,):
            map_axis_names = self.device.map_axes.keys()
            for i in range(len(self.device.shape)):
                limits = pc.NumberLimits(0, self.device.shape[i]-1)
                control = pc.Number(initial_value=0, decimals=0, limits=limits)
                self.widget.add(' '.join([map_axis_names[i], 'index']), control)
                self.shape_controls.append(control)
    
    def hide(self):
        self.widget.hide()

    def update_channels(self):
        time.sleep(10)
        return # TODO:
        while len(self.device.data.read_properties()[1]) == 0:
            print 'hello'
            self.device.acquire()
            self.device.wait_until_done()
        allowed_values = self.device.data.read_properties()[1]
        self.channel_combo.set_allowed_values(allowed_values)


class GUI(QtCore.QObject):

    def __init__(self, control):
        QtCore.QObject.__init__(self)
        self.control = control
        control.wait_until_done()
        self.create_frame()
        #daq.update_ui.connect(self.update)
        #data_obj.update_ui.connect(self.update)
        #shot_channel_combo.updated.connect(self.update)
        #value_channel_combo.updated.connect(self.update)
        #print 'daq gui init done'
        
    def create_frame(self):
        # get parent widget
        parent_widget = g.daq_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        layout = parent_widget.layout()
        # create tab structure
        self.tabs = QtGui.QTabWidget()
        # create tabs for each hardware
        self.hardware_widgets = []
        for hardware in self.control.hardwares:
            widget = QtGui.QWidget()
            self.tabs.addTab(widget, hardware.name)
            self.hardware_widgets.append(widget)
        # signals and slots
        for hardware in self.control.hardwares:
            hardware.update_ui.connect(self.update)
        # finish
        layout.addWidget(self.tabs)
        
    def create_main_tab(self):
        print '2 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
        # create main daq tab
        main_widget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(layout)
        self.tabs.addTab(main_widget, 'Main')
        # display -------------------------------------------------------------
        # container widget
        display_container_widget = pw.ExpandingWidget()
        #display_rect = display_container_widget.rect()
        #display_rectf = QtCore.QRectF(display_rect)
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
        self.values_plot_widget = pw.Plot1D()
        self.values_plot_scatter = self.values_plot_widget.add_scatter()
        display_layout.addWidget(self.values_plot_widget)
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
        self.hardware_combo = pc.Combo()
        input_table.add('Device', self.hardware_combo)
        settings_layout.addWidget(input_table)
        self.display_settings_widgets = {}
        for hardware in control.hardwares:
            display_settings = DisplaySettings(hardware)
            self.display_settings_widgets[hardware.name] = display_settings
            settings_layout.addWidget(display_settings.widget)
            hardware.settings_updated.connect(self.on_update_channels)
        # global daq settings
        input_table = pw.InputTable()
        input_table.add('Settings', None)
        for device in control.hardwares:    
            input_table.add(device.name + ' Freerun', device.freerun)
        data_busy.update_signal = data_obj.update_ui
        input_table.add('Data status', data_busy)
        input_table.add('Loop time', seconds_since_last_task)
        input_table.add('Acquisiton time', seconds_for_acquisition)
        self.idx_string = pc.String(initial_value='None', display=True)
        input_table.add('Scan Index', self.idx_string)
        settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)
        # finish --------------------------------------------------------------
        self.on_update_channels()
        
    def on_update_channels(self):
        for display_settings in self.display_settings_widgets.values():
            display_settings.update_channels()

    def set_slice_xlim(self, xmin, xmax):
        self.values_plot_widget.set_xlim(xmin, xmax)
        
    def update(self):
        '''
        Runs each time an update_ui signal fires (basically every run_task)
        '''
        # values
        #self.big_display.setValue(last_data.read()[value_channel_combo.read_index()])
        if False:        
            self.idx_string.write(str(idx.read()))
        
        # current slice display
        # TODO: fix this for new module implementation
        if False:
            if g.module_control.read():
                xcol = data_cols.read()[current_slice.col]['index']
                ycol_key = value_channel_combo.read()
                ycol = data_cols.read()[ycol_key]['index']       
                vals = np.array(current_slice.read())
                if vals.size == 0:
                    return  # this is probably not great implementation...
                if len(vals.shape) == 1:
                    vals = vals[None, :]
                xi = vals[:, xcol]
                yi = vals[:, ycol]
                self.values_plot_scatter.setData(xi, yi)

    def stop(self):
        pass


### start daq #################################################################


control.initialize()

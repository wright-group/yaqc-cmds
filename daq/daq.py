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

# values
value_channel_combo = pc.Combo()

axes = pc.Mutex()

array_detector_reference = pc.Mutex()

origin = pc.Mutex()

freerun = pc.Bool(initial_value=True)

# additional
seconds_since_last_task = pc.Number(initial_value=np.nan, display=True, decimals=3)
seconds_for_acquisition = pc.Number(initial_value=np.nan, display=True, decimals=3)

# column dictionaries
data_cols = pc.Mutex()
shot_cols = pc.Mutex()

idx = pc.Mutex()  # holds tuple


### file writing class ########################################################


data_busy = pc.Busy()

data_path = pc.Mutex()

enqueued_data = pc.Enqueued()

fit_path = pc.Mutex()

shot_path = pc.Mutex()

header_dictionary_mutex = pc.Mutex()


class FileAddress(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    def _make_file_with_header(self, filepath, cols_kind):
        header_dictionary = copy.deepcopy(header_dictionary_mutex.read())
        # get cols
        if cols_kind == 'data':
            cols = data_cols.read()
            # TODO: add proper 'signed' channel support
            # for now just take number of channels and say all are not signed
            # (for future compatability)
            header_dictionary['channel signed'] = [False for _ in value_channel_combo.allowed_values]
        elif cols_kind == 'shots':
            cols = shot_cols.read()
        # add col properties to header
        if False:  # TODO: recover this behavior
            header_dictionary['kind'] = [col['kind'] for col in cols.values()]
            header_dictionary['units'] = [col['units'] for col in cols.values()]
            header_dictionary['label'] = [col['label'] for col in cols.values()]
            header_dictionary['name'] = cols.keys()
        # create file
        wt.kit.write_headers(filepath, header_dictionary)
    
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
        daq_widget = inputs[0]
        # get info
        header_dictionary = header_dictionary_mutex.read()
        timestamp = header_dictionary['file created']
        origin = header_dictionary['data origin']
        axes = str(header_dictionary['axis names'])
        description = daq_widget.description.read()
        # generate file name
        self.filename = ' '.join([origin, axes, timestamp, description]).rstrip()
        self.filename = self.filename.replace('\'', '')
        # create folder
        data_folder = os.path.join(main_dir, 'data', self.filename)
        os.mkdir(data_folder)
        data_path.write(os.path.join(data_folder, self.filename + '.data'))
        # generate file
        self._make_file_with_header(data_path.read(), 'data')
    
    def create_shots(self, inputs):
        # create shots must always be called after create data
        shot_path.write(data_path.read().replace('.data', '.shots'))
        self._make_file_with_header(shot_path.read(), 'shots')
            
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
                # TODO: fix load_source RuntimeWarming spam
                module_name = os.path.basename(module_path)
                hardware_module = imp.load_source(module_name, module_path)
                hardware_class = getattr(hardware_module, lis[1])
                hardware_obj = hardware_class(inputs=lis[2])
                self.hardwares.append(hardware_obj)
    
    def acquire(self, save=False):
        for hardware in self.hardwares:
            hardware.acquire()
        if save:
            # 1D things -------------------------------------------------------
            data_shape = (50, )  # TODO: 
            data_row = np.full(data_shape, np.nan)
            data_i = 0
            # scan indicies
            for i in idx.read():
                data_row[data_i] = i
                data_i += 1
            # acquisition indicies
            # TODO:
            # hardware positions
            for scan_hardware_module in scan_hardware_modules:
                for scan_hardware in scan_hardware_module.hardwares:
                    for key in scan_hardware.recorded:
                        out_units = scan_hardware.recorded[key][1]
                        if out_units is None:
                            data_row[data_i] = scan_hardware.recorded[key][0].read()
                        else:
                            data_row[data_i] = scan_hardware.recorded[key][0].read(out_units)
                        data_i += 1
            # potentially multidimensional things -----------------------------
            # acquisition maps
            # acquisitions
            for hardware in self.hardwares:
                arr = hardware.data.read()
                for val in arr:
                    data_row[data_i] = val
                    data_i += 1
            # send to file_address
            q('write_data', [data_row])
    
    def set_freerun(self, state):
        for hardware in self.hardwares:
            hardware.set_freerun(state)
            
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
        # signals
        freerun.updated.connect(lambda: self.set_freerun(freerun.read()))
        # begin freerunning
        self.set_freerun(True)
        
    def initialize_scan(self, header_dictionary, widget):
        # create files
        print header_dictionary
        header_dictionary_mutex.write(header_dictionary)
        q('create_data', [widget])
        # wait until daq is done before letting module continue
        self.wait_until_done()
        self.wait_until_file_done()
        
    def module_control_update(self):
        if g.module_control.read():
            freerun.write(False)
            self.wait_until_done()
        else:
            freerun.write(True)
    
    def shutdown(self):
        # TODO
        pass
            
    def wait_until_file_done(self):
        # TODO:
        pass
            
    def wait_until_done(self):
        '''
        Wait until the acquisition hardwares are no longer busy. Does not wait
        for the file writing queue to empty.
        '''
        for hardware in self.hardwares:
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
        # create main daq tab
        main_widget = QtGui.QWidget()
        main_box = QtGui.QHBoxLayout()
        main_box.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(main_box)
        self.tabs.addTab(main_widget, 'Main')
        self.create_main_tab(main_box)
        # signals and slots
        for hardware in self.control.hardwares:
            hardware.update_ui.connect(self.update)
        # finish
        layout.addWidget(self.tabs)
        
    def create_main_tab(self, layout):
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
        # input table one
        input_table = pw.InputTable()
        input_table.add('Display', None)
        input_table.add('Channel', value_channel_combo)   
        input_table.add('Settings', None)
        input_table.add('Free run', freerun)
        data_busy.update_signal = data_obj.update_ui
        input_table.add('Data status', data_busy)
        input_table.add('Loop time', seconds_since_last_task)
        input_table.add('Acquisiton time', seconds_for_acquisition)
        self.idx_string = pc.String(initial_value=str(idx.read()), display=True)
        input_table.add('Scan Index', self.idx_string)
        settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)

    def set_slice_xlim(self, xmin, xmax):
        self.values_plot_widget.set_xlim(xmin, xmax)
        
    def update(self):
        '''
        Runs each time an update_ui signal fires (basically every run_task)
        '''
        # values
        #self.big_display.setValue(last_data.read()[value_channel_combo.read_index()])
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

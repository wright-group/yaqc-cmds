### import#####################################################################


import os
import sys
import time
import collections

import numpy as np

from PyQt4 import QtCore, QtGui

import serial

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
import project.kit as kit
from project.ini_handler import Ini
app = g.app.read()
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'daq',
                                 'InGaAs_array',
                                 'InGaAs.ini'))
                                 
import spectrometers.spectrometers as spectrometers


### define ####################################################################


pixel_width = 50.  # um


### globals####################################################################


acquisition_timer = pc.Number(display=True)

busy = pc.Busy()

enqueued = pc.Enqueued()

data = pc.Data()
data_map = pc.Data()
data_map.write(np.arange(256))

freerun = pc.Bool(initial_value=False)


### address####################################################################


class Address(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    def _read(self):
        # handle communication with special end of line 'ready'
        eol = r'ready\n'
        leneol = len(eol)
        line = ''
        while True:
            c = self.serial_port.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
            else:
                break
        self.serial_port.flush()
        return line
            
    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        '''
        if enqueued.read():
            time.sleep(0.1)
            busy.write(True)
        else:
            busy.write(False)
        
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        if g.debug.read(): print 'InGaAs dequeue:', method, inputs
        enqueued.pop()
        getattr(self, str(method))(inputs) #method passed as qstring
        if not enqueued.read(): 
            self.queue_emptied.emit()
            self.check_busy([])
            
    def initialize(self, inputs):
        if g.debug.read(): print 'InGaAs initializing'
        g.logger.log('info', 'InGaAs initializing')
        # initialize serial port
        self.serial_port = serial.Serial()
        self.serial_port.baudrate = 9600
        self.serial_port.port = 'COM' + str(ini.read('main', 'serial port'))
        self.serial_port.timeout = 0.1  # might need to make this larger...
        self.serial_port.open()
        # initialize arrays for later use
        self.spectra_averaged = 1
        self.out = np.zeros(256)
        self.buffer = np.zeros([256, self.spectra_averaged])
        # finish
        self.timer = wt.kit.Timer(verbose=False)
        self.read([])
        
    def loop(self, inputs):
        while freerun.read() and not enqueued.read():
            self.read()
            busy.write(False)
        else:
            print 'InGaAs exiting loop!'
    
    def read(self, inputs=[]):
        with self.timer:
            for i in range(self.spectra_averaged):
                done = False
                while not done:
                    # get data as string from arduino
                    self.serial_port.write('S')
                    raw_string = self._read()
                    if len(raw_string) == 519:
                        done = True
                    else:
                        print 'InGaAs array bad read!'
                # remove 'ready\n' from end
                string = raw_string[:512]
                # encode to hex
                vals = np.array([elem.encode("hex") for elem in string])
                # reshape
                vals = vals.reshape(256, -1)
                vals = np.flipud(vals)
                # transform to floats
                raw_pixels = [int('0x' + vals[j, 0] + vals[j, 1], 16) for j in np.arange(256)]
                # hardcoded processing
                pixels = 0.00195*(raw_pixels - (2060. + -0.0142*np.arange(256)))
                self.buffer[:, i] = pixels
            self.out = np.mean(self.buffer, axis=1)
        # finish
        data.write_properties((256,), ['array signal'], [self.out])
        self.update_ui.emit()
        acquisition_timer.write(self.timer.interval)    
                      
    def shutdown(self, inputs):
        '''
        cleanly shut down
        
        all hardware address objects must have this, even if trivial
        '''
        if self.serial_port.isOpen():
            self.serial_port.flush()
            self.serial_port.close()
        
    def write_settings(self, inputs):
        integration_time, spectra_averaged = inputs
        # write integration time
        integration_time_us = integration_time*1000
        integration_time_us = np.clip(integration_time_us, 50, 1e6)
        string = 'A%d'%integration_time_us
        self.serial_port.write(string)
        self._read()
        # write spectra averaged
        self.spectra_averaged = spectra_averaged
        self.buffer = np.zeros([256, self.spectra_averaged])
        # write gain
        self.serial_port.write('G1')  # currently gain does nothing: force high
        self._read()


#begin address object in seperate thread
address_thread = QtCore.QThread()
address_obj = Address()
address_obj.moveToThread(address_thread)
address_thread.start()

busy.update_signal = address_obj.update_ui

#create queue to communiate with address thread
q = pc.Q(enqueued, busy, address_obj)

### hardware ##################################################################


class Hardware(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    settings_updated = QtCore.pyqtSignal()
    
    def __init__(self, inputs=[]):
        QtCore.QObject.__init__(self)
        self.active = False
        self.busy = busy
        self.busy.update_signal = self.update_ui
        self.name = 'InGaAs'
        self.shape = (256, )
        self.data = data
        self.acquisition_time = acquisition_timer
        self.map = data_map
        self.has_map = True
        self.map_axes = {'wa': ['a', 'nm']}
        self.freerun = freerun
        self.freerun.updated.connect(lambda: q.push('loop'))
        # mutex attributes
        integration_time_limits = pc.NumberLimits(1, 1e3)
        self.integration_time = pc.Number(ini=ini, section='main',
                                          option='integration time (ms)',
                                          decimals=0,
                                          limits=integration_time_limits)
        self.integration_time.updated.connect(self.write_settings)
        spectra_averaged_limits = pc.NumberLimits(1, 100)
        self.spectra_averaged = pc.Number(ini=ini, section='main',
                                          option='spectra averaged',
                                          decimals=0,
                                          limits=spectra_averaged_limits)
        self.spectra_averaged.updated.connect(self.write_settings)
        # get spec hardware
        self.spectrometer_hardware = spectrometers.hardwares[0]
        self.spectrometer_hardware.current_position.updated.connect(self.calculate_map)
        # finish
        g.shutdown.read().connect(self.shutdown)
        self.Widget = Widget
        self.initialized = False

    def acquire(self):
        q.push('read')

    def calculate_map(self, mono_setpoint=None, write=True):
        '''
        mono setpoint in nm
        '''
        # get setpoint
        if mono_setpoint is None:
            mono_setpoint = self.spectrometer_hardware.get_position('nm')
        # calculate
        arr = kit.grating_linear_dispersion(spec_inclusion_angle=24.,
                                            spec_focal_length=140.,
                                            spec_focal_length_tilt=0.,
                                            spec_grooves_per_mm=150.,
                                            spec_central_wavelength=mono_setpoint,
                                            spec_order=1,
                                            number_of_pixels=256,
                                            pixel_width=50.,
                                            calibration_pixel=100)
        if write:
            self.map.write(arr)
        return arr
        
    def get_axis_properties(self, destinations_list):
        '''
        Get the axis properties to record for the given scan, given hardware
        positions.
        
        Parameters
        ----------
        destinations_list : list of modules.scan.Destination objects
            The scan destinations
            
        Returns
        -------
        tuple : (identity, units, points, centers, interpolate)
        '''
        scanned_hardware_names = [d.hardware.friendly_name for d in destinations_list]        
        if 'wm' in scanned_hardware_names:
            # calculate points, centers
            destinations = [d for d in destinations_list if d.hardware.friendly_name == 'wm'][0]
            centers_nm = wt.units.converter(destinations.arr, destinations.units, 'nm')
            centers_wn = wt.units.converter(destinations.arr, destinations.units, 'wn')
            map_nm = self.calculate_map(mono_setpoint=centers_nm.min(), write=False)
            map_wn = wt.units.converter(map_nm, 'nm', 'wn')
            map_wn -= centers_wn.max()
            map_nm = wt.units.converter(map_wn, 'wn', 'nm')
            # assemble outputs
            identity = 'Dwa'
            units = 'wn'
            points = map_wn
            centers = centers_wn
            interpolate = True
            print points
        else:
            identity = 'wa'
            units = 'nm'
            points = self.get_map()
            centers = None
            interpolate = False
        return identity, units, points, centers, interpolate
        
    def get_data(self):
        return self.data.read()
        
    def get_headers(self):
        out = collections.OrderedDict()
        out['integration time (ms)'] = self.integration_time.read()
        out['spectra averaged'] = self.spectra_averaged.read()
        return out
    
    def get_map(self):
        return self.map.read()
        
    def initialize(self, parent_widget):
        # detector
        q.push('initialize')
        self.write_settings()
        self.acquire()
        self.wait_until_done()
        # gui
        self.gui = GUI(self)
        self.gui.create_frame(parent_widget)
        # finish
        self.active = True
        self.initialized = True
        self.settings_updated.emit()
        
    def set_freerun(self, state):
        freerun.write(state)
        q.push('loop')
    
    def shutdown(self):
        self.set_freerun(False)
        if g.debug.read(): 
            print 'InGaAs shutting down'
        g.logger.log('info', 'InGaAs shutdown')
        q.push('shutdown')
        self.wait_until_done()
        address_thread.quit()
        self.gui.stop()
    
    def wait_until_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        '''
        start_time = time.time()
        while busy.read():
            time.sleep(0)  # yield?
            QtCore.QThread.yieldCurrentThread()
            if time.time()-start_time < timeout:
                busy.wait_for_update()
            else: 
                print 'InGaAs TIMED OUT!!!!!!!!!!!'
                g.logger.log('warning', 'InGaAs wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
            
    def write_settings(self):
        integration_time = int(self.integration_time.read())  # ms
        spectra_averaged = int(self.spectra_averaged.read())  # int
        q.push('write_settings', [integration_time, spectra_averaged])
        

### gui #######################################################################


class Widget(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = pw.InputTable()
        input_table.add('InGaAs', None)
        self.use = pc.Bool(disable_under_module_control=True)
        input_table.add('Use', self.use)
        self.integration_time = pc.Number(initial_value=10, decimals=0, disable_under_module_control=True)
        input_table.add('Integration Time (ms)', self.integration_time)
        self.spectra_averaged = pc.Number(initial_value=1, decimals=0, disable_under_module_control=True)
        input_table.add('Spectra Averaged', self.spectra_averaged)
        self.save_shots = pc.Bool(disable_under_module_control=True)
        layout.addWidget(input_table)


class GUI(QtCore.QObject):

    def __init__(self, hardware):
        QtCore.QObject.__init__(self)
        self.hardware = hardware
        address_obj.update_ui.connect(self.update)
        
    def create_frame(self, parent_widget):
        #get parent widget-----------------------------------------------------
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        layout = parent_widget.layout()
        #display area----------------------------------------------------------
        #container widget
        display_container_widget = pw.ExpandingWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        #big number
        big_number_container_widget = QtGui.QWidget()
        big_number_container_widget.setLayout(QtGui.QHBoxLayout())
        big_number_container_layout = big_number_container_widget.layout()
        big_number_container_layout.setMargin(0)
        big_number_container_layout.addStretch(1)
        self.big_display = pw.SpinboxAsDisplay(font_size=100)
        big_number_container_layout.addWidget(self.big_display)
        display_layout.addWidget(big_number_container_widget)        
        #plot
        self.plot_widget = pw.Plot1D()
        self.plot_widget.set_ylim(0, 4)
        self.plot_curve = self.plot_widget.add_line()
        self.plot_v_line = self.plot_widget.add_infinite_line(hide=False)
        self.plot_widget.set_labels(ylabel='arbitrary units', xlabel='nm')
        display_layout.addWidget(self.plot_widget)
        #vertical line---------------------------------------------------------
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
        # input table
        input_table = pw.InputTable()
        input_table.add('Display', None)
        pixel_limits = pc.NumberLimits(0, 255)
        self.display_pixel_index = pc.Number(ini=ini, section='main',
                                             option='display pixel index',
                                             limits=pixel_limits,
                                             decimals=0)
        input_table.add('Pixel Index', self.display_pixel_index)
        input_table.add('Settings', None)
        input_table.add('Integration Time (ms)', self.hardware.integration_time)
        input_table.add('Spectra Averaged', self.hardware.spectra_averaged)
        settings_layout.addWidget(input_table)
        #streach
        settings_layout.addStretch(1)
    
    def update(self):
        if not data.read() == None:
            # plot
            xi = data_map.read()
            yi = data.read()[0]
            self.plot_curve.clear()
            self.plot_curve.setData(xi, yi)
            self.plot_widget.set_xlim(xi.min(), xi.max())
            display_pixel_index = int(self.display_pixel_index.read())
            self.plot_v_line.setValue(xi[display_pixel_index])
            # data readout
            self.big_display.setValue(yi[display_pixel_index])
              
    def stop(self):
        pass

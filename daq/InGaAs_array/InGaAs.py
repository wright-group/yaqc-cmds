### import#####################################################################


import os
import sys
import time

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


acquisition_timer = pc.Number(display=True, units='s_t')

busy = pc.Busy()

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

class Data(QtCore.QMutex):
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
data = Data()
data_map = Data()
data_map.write(np.arange(256))

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
        
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        '''
        #DO NOT CHANGE THIS METHOD UNLESS YOU ~REALLY~ KNOW WHAT YOU ARE DOING!
        #if g.debug.read(): print 'InGaAs dequeue:', method, inputs
        getattr(self, str(method))(inputs) #method passed as qstring
        enqueued_actions.pop()
        if not enqueued_actions.read(): 
            self.queue_emptied.emit()
            self.check_busy([])
            
    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        '''
        if enqueued_actions.read():
            time.sleep(0.1)
            busy.write(True)
        else:
            busy.write(False)
            
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
        data.write(self.out)
        self.update_ui.emit()
        acquisition_timer.write(self.timer.interval, 's_t')
        
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
                      
    def shutdown(self, inputs):
        '''
        cleanly shut down
        
        all hardware address objects must have this, even if trivial
        '''
        if self.serial_port.isOpen():
            self.serial_port.flush()
            self.serial_port.close()

#begin address object in seperate thread
address_thread = QtCore.QThread()
address_obj = Address()
address_obj.moveToThread(address_thread)
address_thread.start()

busy.update_signal = address_obj.update_ui

#create queue to communiate with address thread
queue = QtCore.QMetaObject()
def q(method, inputs = []):
    #add to friendly queue list 
    enqueued_actions.push([method, time.time()])
    #busy
    if not busy.read(): busy.write(True)
    #send Qt SIGNAL to address thread
    queue.invokeMethod(address_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))


### control####################################################################


class Hardware():
    
    def __init__(self):
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
        self.initialize()
        self.gui = GUI(self)
        self.data = data
        self.map = data_map
        self.size = 256

        
    def get_data(self):
        return self.data.read()
    
    def get_map(self):
        return self.map.read()
        
    def initialize(self):
        q('initialize')
        self.write_settings()
        
    def calculate_map(self, mono_setpoint=None):
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
        self.map.write(arr)
        
    def read(self):
        q('read')
    
    def wait_until_done(self, timeout = 10):
        while busy.read():
            busy.wait_for_update()
            
    def write_settings(self):
        integration_time = int(self.integration_time.read())  # ms
        spectra_averaged = int(self.spectra_averaged.read())  # int
        q('write_settings', [integration_time, spectra_averaged])
                
    def shutdown(self):
        if g.debug.read(): 
            print 'InGaAs shutting down'
        g.logger.log('info', 'InGaAs shutdown')
        q('shutdown')
        self.wait_until_done()
        address_thread.quit()
        self.gui.stop()
        

### gui########################################################################

        
class GUI(QtCore.QObject):

    def __init__(self, hardware):
        QtCore.QObject.__init__(self)
        self.hardware = hardware
        address_obj.update_ui.connect(self.update)
        
    def create_frame(self, parent_widget):
        
        #get parent widget-----------------------------------------------------
        
        parent_widget.setLayout(QtGui.QHBoxLayout())
        layout = parent_widget.layout()
        
        #display area----------------------------------------------------------

        #container widget
        display_container_widget = pw.ExpandingWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        #big number
        self.big_display = pw.spinbox_as_display(font_size = 100)
        display_layout.addWidget(self.big_display)
        
        #plot
        self.plot_widget = pw.Plot1D()
        self.plot_curve = self.plot_widget.add_line()
        self.plot_v_line = self.plot_widget.add_infinite_line()
        self.plot_v_line.show()
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
        input_table.add('Status', busy)
        input_table.add('Acquisition Time', acquisition_timer)
        settings_layout.addWidget(input_table)

        #streach
        settings_layout.addStretch(1)
    
    def update(self):
        if not data.read() == None:
            # plot
            xi = data_map.read()
            yi = data.read()
            self.plot_curve.clear()
            self.plot_curve.setData(xi, yi)
            self.plot_widget.set_xlim(xi.min(), xi.max())
            display_pixel_index = int(self.display_pixel_index.read())
            self.plot_v_line.setValue(xi[display_pixel_index])
            # data readout
            self.big_display.setValue(yi[display_pixel_index])
              
    def stop(self):
        pass


hardware = Hardware()

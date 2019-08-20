# --- import --------------------------------------------------------------------------------------


import os
import sys
import time
import collections
import codecs

import numpy as np

from PySide2 import QtCore, QtWidgets

import serial

import WrightTools as wt

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
import project.kit as kit
from project.ini_handler import Ini
import hardware.spectrometers.spectrometers as spectrometers
from devices.devices import Device as BaseDevice
from devices.devices import Driver as BaseDriver
from devices.devices import DeviceGUI as BaseGUI
from devices.devices import DeviceWidget as BaseWidget


# --- define --------------------------------------------------------------------------------------


app = g.app.read()
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'devices',
                                 'InGaAs_array',
                                 'InGaAs.ini'))

pixel_width = 50.  # um


# --- device --------------------------------------------------------------------------------------


class Device(BaseDevice):
    
    def __init__(self, *args, **kwargs):
        kwargs['shape'] = (256, )
        kwargs['has_map'] = True
        kwargs['shots_compatible'] = False
        self.map_axes = {'wa': ['a', 'nm']}
        self.map = pc.Data()
        self.map.write(np.arange(256))
        BaseDevice.__init__(self, *args, **kwargs)
        # get spec hardware
        self.spectrometer_hardware = spectrometers.hardwares[0]
        self.spectrometer_hardware.position.updated.connect(self.calculate_map)


    def calculate_map(self, mono_setpoint=None, write=True):
        """mono setpoint in nm"""
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
        scanned_hardware_names = [d.hardware.name for d in destinations_list]        
        if 'wm' in scanned_hardware_names:
            # calculate points, centers
            destinations = [d for d in destinations_list if d.hardware.name == 'wm'][0]
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
            print(points)
        else:
            identity = 'wa'
            units = 'nm'
            points = self.map.read()
            centers = None
            interpolate = False
        return identity, units, points, centers, interpolate

    def load_settings(self, aqn):
        pass


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):
    
    def _read(self):
        # handle communication with special end of line 'ready'
        eol = r'ready\n'.encode()
        line = ''.encode()
        while True:
            c = self.serial_port.read(1)
            if c:
                line += c
                if line.endswith(eol):
                    break
            else:
                break
        self.serial_port.flush()
        return line

    def initialize(self):
        print('INGAAS INITIALIZE')
        if g.debug.read():
            print('InGaAs initializing')
        g.logger.log('info', 'InGaAs initializing')
        # initialize serial port
        self.serial_port = serial.Serial()
        self.serial_port.baudrate = 57600
        self.serial_port.port = 'COM16'#'COM' + str(ini.read('main', 'serial port'))
        self.serial_port.timeout = 0.1  # might need to make this larger...
        self.serial_port.open()
        # initialize arrays for later use
        self.spectra_averaged = 5 #int(ini.read('main', 'spectra averaged'))
        self.out = np.zeros(256)
        self.buffer = np.zeros([256, self.spectra_averaged])
        # finish
        self.timer = wt.kit.Timer(verbose=False)
        #self.measure()
		
    def measure(self):
        # prepare
        self.running = True
        # do
        with self.timer:
            for i in range(self.spectra_averaged):
                done = False
                while not done:
                    # get data as string from arduino
                    self.serial_port.write('S'.encode())
                    raw_string = self._read()
                    if len(raw_string) == 519:
                        done = True
                    else:
                        print('InGaAs array bad read!')
                # transform to floats
                raw_pixels = np.frombuffer(raw_string, dtype='>i2', count=256)
                # hardcoded processing
                pixels = 0.00195*(raw_pixels[::-1] - (2060. + -0.0142*np.arange(256)))
                self.buffer[:, i] = pixels
        self.out = np.mean(self.buffer, axis=1)
        self.data.write_properties((256,), ['array_signal'], [self.out])
        self.measure_time.write(self.timer.interval)
        # finish
        self.update_ui.emit()
        self.running = False 
        

    def shutdown(self):
        """cleanly shut down"""
        if self.serial_port.isOpen():
            self.serial_port.flush()
            self.serial_port.close()


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
        
    def create_frame(self, parent_widget):
        #get parent widget-----------------------------------------------------
        parent_widget.setLayout(QtWidgets.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        layout = parent_widget.layout()
        #display area----------------------------------------------------------
        #container widget
        display_container_widget = pw.ExpandingWidget()
        display_container_widget.setLayout(QtWidgets.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        #big number
        big_number_container_widget = QtWidgets.QWidget()
        big_number_container_widget.setLayout(QtWidgets.QHBoxLayout())
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
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area(130)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
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
        #input_table.add('Settings', None)
        #input_table.add('Integration Time (ms)', self.hardware.integration_time)
        #input_table.add('Spectra Averaged', self.hardware.spectra_averaged)
        settings_layout.addWidget(input_table)
        #streach
        settings_layout.addStretch(1)
        # signals and slots
        self.hardware.update_ui.connect(self.update)
    
    def update(self):
        if not self.hardware.data.read() == None:
            # plot
            xi = self.hardware.map.read()
            yi = self.hardware.data.read()[0]
            self.plot_curve.clear()
            self.plot_curve.setData(xi, yi)
            self.plot_widget.set_xlim(xi.min(), xi.max())
            display_pixel_index = int(self.display_pixel_index.read())
            self.plot_v_line.setValue(xi[display_pixel_index])
            # data readout
            self.big_display.setValue(yi[display_pixel_index])
              
    def stop(self):
        pass


class Widget(BaseWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = pw.InputTable()
        input_table.add('InGaAs', None)
        self.use = pc.Bool(initial_value=False)
        input_table.add('Use', self.use)
        layout.addWidget(input_table)
        
    def load(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        self.use.write(ini.read('InGaAs', 'use'))
   
    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section('InGaAs')
        ini.write('InGaAs', 'use', self.use.read())

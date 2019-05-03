# --- import --------------------------------------------------------------------------------------


from __future__ import print_function


import os
import sys
import imp
import time
import copy
import threading

import collections

import numpy as np

import scipy
import serial

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import project.ini_handler as ini
from project.ini_handler import Ini
from devices.devices import Device as BaseDevice
from devices.devices import Driver as BaseDriver
from devices.devices import DeviceGUI as BaseGUI
from devices.devices import DeviceWidget as BaseWidget


# --- define --------------------------------------------------------------------------------------


app = g.app.read()
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'devices',
                                 'environmental_sensors',
                                 'environmental_sensors.ini'))

    
# --- data mutex objects --------------------------------------------------------------------------
 

data = pc.Data()
shots = pc.Data()

axes = pc.Mutex()

origin = pc.Mutex()


# --- device --------------------------------------------------------------------------------------


class Device(BaseDevice):

    def __init__(self, *args, **kwargs):
        self.initialized = False
        kwargs['shots_compatible'] = False
        BaseDevice.__init__(self, *args, **kwargs)

    def load_settings(self, aqn):
        pass
        #self.nshots.write(aqn.read(self.name, 'shots'))
        

# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):

    def initialize(self):
        self.serial_port = serial.Serial(ini.read("main", "serial port"))
        self.serial_port.timeout = 1.
        self.timer = wt.kit.Timer(verbose=False)
        self.measure()
    
    def measure(self):
        """
        Acquire once using the created task.
        """
        self.running = True
        with self.timer:
            line = b""
            while not line:
                self.serial_port.write(b'r')
                line = self.serial_port.readline()
            temp, rel_hum, press = [float(b.strip(b',')) for b in line.split()]
        self.data.write_properties((1,), ['temperature', 'relative_humidity', 'pressure'], [temp, rel_hum, press])

        self.update_ui.emit()
        self.running = False



    def shutdown(self, inputs):
        """cleanly shut down"""
        if self.serial_port.isOpen():
            self.serial_port.flush()
            self.serial_port.close()
    

# --- gui -----------------------------------------------------------------------------------------

        
class GUI(BaseGUI):
    pass


class Widget(BaseWidget):

    def __init__(self):
        BaseWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = pw.InputTable()
        input_table.add('Environment Sensors', None)
        self.use = pc.Bool(initial_value=True)
        input_table.add('Use', self.use)
        self.shots = pc.Number(initial_value=100, decimals=0)
        input_table.add('Shots', self.shots)
        self.save_shots = pc.Bool(initial_value=False)
        
    def load(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        self.use.write(ini.read('environment sensors', 'use'))
        self.shots.write(ini.read('environment sensors', 'shots'))

    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section('environment sensors')
        ini.write('environment sensors', 'use', self.use.read())
        ini.write('environment sensors', 'shots', self.shots.read())

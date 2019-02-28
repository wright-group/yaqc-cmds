### import ####################################################################


import os
import time
import collections

import numpy as np

from PySide2 import QtWidgets

import WrightTools as wt

import project
import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.classes as pc
import hardware.hardware as hw


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))
ini = project.ini_handler.Ini(os.path.join(directory, 'spectrometers.ini'))


### driver ####################################################################


class Driver(hw.Driver):
    
    def __init__(self, *args, **kwargs):
        self.hardware_ini = ini
        hw.Driver.__init__(self, *args, **kwargs)
        self.limits.write(0., 10000.)


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *args, **kwargs):
        self.kind = 'spectrometer'
        hw.Hardware.__init__(self, *args, **kwargs)


### import ####################################################################


ini_path = os.path.join(directory, 'spectrometers.ini')
hardwares, gui, advanced_gui = hw.import_hardwares(ini_path, name='Spectrometers', Driver=Driver, GUI=GUI, Hardware=Hardware)

### import ####################################################################


import os
import collections
import time

import numpy as np

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI

from library.ThorlabsAPT.APT import APTMotor


### define ####################################################################


main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'delays',
                                 'LTS300',
                                 'LTS300.ini'))


### driver ####################################################################


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        kwargs['native_units'] = 'ps'
        self.index = kwargs.pop('index')
        self.native_per_mm = 6.671281903963041
        BaseDriver.__init__(self, *args, **kwargs)
        self.motor_limits = pc.NumberLimits(0, 300, 'mm')
        
    def close(self):
        self.motor.close()
    
    def initialize(self):
        #self.motor = APTMotor(int(self.serial), 42)
        # read from ini
        self.factor = pc.Number(ini=ini, section='D{}'.format(self.index), option='factor', decimals=0, disable_under_queue_control=True)
        self.factor.updated.connect(self.on_factor_updated)        
        self.zero_position = pc.Number(name='Zero', initial_value=12.5,
                                       ini=ini, section='D{}'.format(self.index),
                                       option='zero position (mm)', import_from_ini=True,
                                       save_to_ini_at_shutdown=True,
                                       limits=self.motor_limits,
                                       decimals=5,
                                       units='mm', display=True)                                   
        self.set_zero(self.zero_position.read())
        self.label = pc.String(ini=ini, section='D{}'.format(self.index), option='label', disable_under_queue_control=True)
        self.label.updated.connect(self.update_recorded)
        self.update_recorded()
        # finish
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()


### gui #######################################################################


class GUI(BaseGUI):
    pass

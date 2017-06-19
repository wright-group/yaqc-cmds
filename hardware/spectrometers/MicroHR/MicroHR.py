### import ####################################################################


import os
import collections
import time

from PyQt4 import QtGui, QtCore

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from hardware.spectrometers.spectrometers import Driver as BaseDriver
from hardware.spectrometers.spectrometers import GUI as BaseGUI

import hardware.spectrometers.MicroHR.gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
import hardware.spectrometers.MicroHR.gen_py.JYMono as JYMono


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        self.unique_id = kwargs.pop('unique_id')
        BaseDriver.__init__(self, *args, **kwargs)
        self.grating_index = pc.Combo(name='Grating', allowed_values=[1, 2],
                                      ini=self.hardware_ini, section=self.name,
                                      option='grating_index',
                                      import_from_ini=True, display=True,
                                      set_method='set_turret')
        self.exposed.append(self.grating_index)

    def close(self):
        self.ctrl.CloseCommunications()
        self.hardware_ini.write(self.name, 'grating_index', self.grating_index.read())
        BaseDriver.close(self)

    def get_grating_details(self):
        """
        grating density
        blaze, description
        """
        return self.ctrl.GetCurrentGratingWithDetails()

    def get_position(self):
        native_position = self.ctrl.GetCurrentWavelength()
        self.position.write(native_position, self.native_units)
        return self.position.read()

    def initialize(self, *args, **kwargs):
        # open control
        self.ctrl = JYMono.Monochromator()
        self.ctrl.Uniqueid = self.unique_id
        self.ctrl.Load()
        self.ctrl.OpenCommunications()
        # initialize hardware
        forceInit = True  # this toggles mono homing behavior
        emulate = False
        notThreaded = True  # no idea what this does...
        self.ctrl.Initialize(forceInit, emulate, notThreaded)
        # import some information from control
        self.description = self.ctrl.Description
        self.serial_number = self.ctrl.SerialNumber
        self.position.write(self.ctrl.GetCurrentWavelength())
        # import information from ini
        init_position = self.hardware_ini.read(self.name, 'position')
        init_grating_index = self.hardware_ini.read(self.name, 'grating_index')
        # recorded
        self.recorded['wm'] = [self.position, 'nm', 1., 'm', False]
        # go to old position after initialization is done
        while self.is_busy():
            time.sleep(0.1)
        self.set_turret(init_grating_index)
        self.set_position(init_position)
        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return self.ctrl.IsBusy()
    
    def set_position(self, destination):
        self.ctrl.MovetoWavelength(destination)
        while self.is_busy():
            time.sleep(0.01)
        self.get_position()

    def set_turret(self, destination_index):
        if type(destination_index) == list:
            destination_index = destination_index[0]
        # turret index on ActiveX call starts from zero
        destination_index_zero_based = destination_index - 1
        self.ctrl.MovetoTurret(destination_index_zero_based)
        self.grating_index.write(destination_index)
        while self.is_busy():
            time.sleep(0.01)
        # update own limits
        max_limit = self.hardware_ini.read(self.name, 'grating_%i_maximum_wavelength'%self.grating_index.read())
        if self.grating_index.read() == 1:
            self.limits.write(0, max_limit, 'nm')
        elif self.grating_index.read() == 2:
            self.limits.write(0, max_limit, 'nm')
        # set position for new grating
        self.set_position(self.position.read(self.native_units))


### gui #######################################################################


class GUI(BaseGUI):
    pass

### import ####################################################################


import time

import project.classes as pc
import project.project_globals as g
from hardware.spectrometers.spectrometers import Driver as BaseDriver
from hardware.spectrometers.spectrometers import GUI as BaseGUI

import yaqd_core

### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        self._yaqd_port = kwargs.pop("yaqd_port")
        BaseDriver.__init__(self, *args, **kwargs)
        self.grating_index = pc.Combo(name='Grating', allowed_values=[1, 2],
                                      section=self.name,
                                      option='grating_index',
                                      display=True,
                                      set_method='set_turret')
        self.exposed.append(self.grating_index)

    def close(self):
        self.ctrl.close()
        BaseDriver.close(self)

    def get_position(self):
        native_position = self.ctrl.get_position()
        self.position.write(native_position, self.native_units)
        return self.position.read()

    def initialize(self, *args, **kwargs):
        # open control
        self.ctrl = yaqd_core.Client(self._yaqd_port)
        # import some information from control
        id_dict = self.ctrl.id()
        self.serial_number = id_dict["serial"]
        self.position.write(self.ctrl.get_position())
        # recorded
        self.recorded['wm'] = [self.position, 'nm', 1., 'm', False]
        while self.is_busy():
            time.sleep(0.1)
        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return self.ctrl.busy()
    
    def set_position(self, destination):
        self.ctrl.set_position(destination)
        while self.is_busy():
            time.sleep(0.01)
        self.get_position()

    def set_turret(self, destination_index):
        if type(destination_index) == list:
            destination_index = destination_index[0]
        # turret index on ActiveX call starts from zero
        destination_index_zero_based = int(destination_index) - 1
        self.ctrl.set_turret(destination_index_zero_based)
        self.grating_index.write(destination_index)
        while self.is_busy():
            time.sleep(0.01)


        #TODO: move limit handling to daemon
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

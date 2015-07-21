### import ####################################################################


import os

import time

from PyQt4 import QtGui, QtCore

import WrightTools.units as wt_units

import project
import project.classes as pc
import project.project_globals as g
main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'spectrometers',
                                                     'MicroHR',
                                                     'MicroHR.ini'))

import gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
import gen_py.JYMono as JYMono


### mono object ###############################################################


# CRITICAL:
# FOR SOME REASON THE PHYSICAL USB KEY IS NEEDED FOR THIS CODE TO WORK

class MicroHR:

    def __init__(self, busy_method=None):
        self.busy_method = busy_method
        # list of objects to be exposed to PyCMDS
        self.native_units = 'nm'
        self.limits = pc.NumberLimits(min_value=0, max_value=20000, units='nm')
        self.current_position = pc.Number(name='Color',
                                          ini=ini, import_from_ini=True,
                                          section='main',
                                          option='position (nm)',
                                          limits=self.limits,
                                          units='nm', display=True,
                                          set_method='set_position')
        self.grating_index = pc.Combo(name='Grating', allowed_values=[1, 2],
                                      ini=ini, section='main',
                                      option='grating index',
                                      import_from_ini=True, display=True,
                                      set_method='set_turret')
        self.exposed = [self.current_position, self.grating_index]
        self.gui = gui()

    def close(self):
        # close control
        self.ctrl.CloseCommunications()
        # save current position to ini
        ini.write('main', 'grating index', self.grating_index.read())
        ini.write('main', 'position (nm)', self.current_position.read())

    def get_position(self):
        native_position = self.ctrl.GetCurrentWavelength()
        self.current_position.write(native_position, self.native_units)
        return self.current_position.read()

    def initialize(self, inputs=[]):
        # open control
        self.ctrl = JYMono.Monochromator()
        self.ctrl.Uniqueid = 'Mono1'
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
        self.current_position.write(self.ctrl.GetCurrentWavelength())
        # import information from ini
        init_grating_index = ini.read('main', 'grating index')
        init_wavelength = ini.read('main', 'position (nm)')
        # go to old position after initialization is done
        while self.is_busy():
            time.sleep(0.1)
        self.set_turret(init_grating_index)
        self.set_position(init_wavelength)

    def is_busy(self):
        return self.ctrl.IsBusy()

    def set_position(self, destination):
        if type(destination) == list:
            destination = destination[0]
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
        if self.grating_index.read() == 1:
            self.limits.write(0, 1500, 'nm')
        elif self.grating_index.read() == 2:
            self.limits.write(0, 15000, 'nm')
        # set position for new grating
        self.set_position(self.current_position.read(self.native_units))

    def stop(self):
        self.ctrl.Stop()


### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)

    def create_frame(self, layout):
        layout.setMargin(5)
       
        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by MicroHR')
        my_widget.setAutoFillBackground(True)
        layout.addWidget(my_widget)
        
        self.advanced_frame = QtGui.QWidget()   
        self.advanced_frame.setLayout(layout)
        
        g.module_advanced_widget.add_child(self.advanced_frame)
        
    def update(self):
        pass
        
    def on_set(self):
        pass
    
    def show_advanced(self):
        pass
              
    def stop(self):
        pass


### testing ###################################################################


if __name__ == '__main__':
    
    
    MicroHR = MicroHR()
    MicroHR.initialize()
    # wait for initialization to complete
    while MicroHR.is_busy():
        time.sleep(1)
    
    print MicroHR.get_position()
    
    MicroHR.set_position(1000)
    
    while MicroHR.is_busy():
        time.sleep(1)
    
    if False:
        MicroHR.set_position(1000)
        time.sleep(5)
        print MicroHR.get_position()
        MicroHR.set_position(1300)
    
    MicroHR.close()
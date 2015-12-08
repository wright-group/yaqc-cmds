### import ####################################################################


import os
import collections
import time

from PyQt4 import QtGui, QtCore

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g
main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'spectrometers',
                                                     'MicroHR',
                                                     'MicroHR.ini'))

if not g.offline.read():
    import spectrometers.MicroHR.gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
    import spectrometers.MicroHR.gen_py.JYMono as JYMono


### mono object ###############################################################


# CRITICAL:
# FOR SOME REASON THE PHYSICAL USB KEY IS NEEDED FOR THIS CODE TO WORK

class MicroHR:

    def __init__(self):
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
        self.offset = pc.Number(initial_value=0, units=self.native_units, display=True)
        self.grating_index = pc.Combo(name='Grating', allowed_values=[1, 2],
                                      ini=ini, section='main',
                                      option='grating index',
                                      import_from_ini=True, display=True,
                                      set_method='set_turret')
        self.exposed = [self.current_position, self.grating_index]
        self.recorded = collections.OrderedDict()
        self.gui = GUI(self)
        self.initialized = pc.Bool()

    def close(self):
        # close control
        self.ctrl.CloseCommunications()
        # save current position to ini
        ini.write('main', 'grating index', self.grating_index.read())
        ini.write('main', 'position (nm)', self.current_position.read())

    def get_grating_details(self):
        '''
        grating density
        blaze, description
        '''
        return self.ctrl.GetCurrentGratingWithDetails()

    def get_position(self):
        native_position = self.ctrl.GetCurrentWavelength()
        self.current_position.write(native_position, self.native_units)
        return self.current_position.read()

    def initialize(self, inputs, address):
        self.address = address
        # open control
        self.ctrl = JYMono.Monochromator()
        self.ctrl.Uniqueid = ini.read('main', 'unique id')
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
        # recorded
        self.recorded['wm'] = [self.current_position, 'nm', 1., 'm', False]
        # go to old position after initialization is done
        while self.is_busy():
            time.sleep(0.1)
        self.set_turret(init_grating_index)
        self.set_position(init_wavelength)
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return self.ctrl.IsBusy()
    
    def set_offset(self, offset):
        pass

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
        
        

class MicroHR_offline(MicroHR):

    def close(self):
        pass

    def get_grating_details(self):
        pass

    def get_position(self):
        return self.current_position.read()

    def initialize(self, inputs, address):
        self.address = address
        self.fake_busy = False
        # import information from ini
        init_grating_index = ini.read('main', 'grating index')
        init_wavelength = ini.read('main', 'position (nm)')
        # recorded
        self.recorded['wm'] = [self.current_position, 'nm', 1., 'm', False]
        # go to old position after initialization is done
        self.set_turret(init_grating_index)
        self.set_position(init_wavelength)
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return self.fake_busy

    def set_position(self, destination):
        self.fake_busy = True
        time.sleep(0.1)
        self.current_position.write(destination, self.native_units)
        self.fake_busy = False

    def set_turret(self, destination_index):
        if type(destination_index) == list:
            destination_index = destination_index[0]
        self.fake_busy = True
        time.sleep(0.1)
        self.grating_index.write(destination_index)
        self.fake_busy = False

    def stop(self):
        pass


### gui #######################################################################


class GUI(QtCore.QObject):

    def __init__(self, driver):
        QtCore.QObject.__init__(self)
        self.driver = driver

    def create_frame(self, layout):
        layout.setMargin(5)
        self.layout = layout
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        g.module_advanced_widget.add_child(self.frame)
        if self.driver.initialized.read():
            self.initialize()
        else:
            self.driver.initialized.updated.connect(self.initialize)

    def initialize(self):
        # settings container
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area(show_bar=False)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # input table
        input_table = pw.InputTable()
        self.current_position = self.driver.current_position.associate()
        input_table.add('Current', self.current_position)
        settings_layout.addWidget(input_table)
        # finish
        settings_layout.addStretch(1)
        self.layout.addStretch(1)
        self.driver.address.update_ui.connect(self.update)

    def update(self):
        self.current_position.write(self.driver.current_position.read())

    def stop(self):
        pass

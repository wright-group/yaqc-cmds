### import ####################################################################


import os
import collections
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

# JY code not loaded for virtual mono
# import spectrometers.MicroHR.gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
# import spectrometers.MicroHR.gen_py.JYMono as JYMono


### mono object ###############################################################


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
        self.gui = gui()
        self.initialized = pc.Bool()

    def close(self):
        pass

    def get_grating_details(self):
        # What form does this come in? I don't want to crash the program!!
        '''
        grating density
        blaze, description
        '''
        return [1000,2,5000,"Virtual grating, always returns grating 2"]
        #return self.ctrl.GetCurrentGratingWithDetails()

    def get_position(self):
        return self.current_position.read()

    def initialize(self, inputs, address):
        self.address = address
        self.description = 'Virtual Non-emulated Mono'
        self.serial_number = '00000'
        self.current_position.write(0)
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

    def is_busy(self):
        return False

    def set_position(self, destination):
        if type(destination) == list:
            destination = destination[0]
        self.current_position.write(destination)

    def set_turret(self, destination_index):

        if type(destination_index) == list:
            destination_index = destination_index[0]

        #Bug fix for type(destination_index) == 'NoneType'
        if g.offline.read():
            destination_index = 2

        self.grating_index.write(destination_index)
        # update own limits
        if self.grating_index.read() == 1:
            self.limits.write(0, 1500, 'nm')
            self.set_position(1000)
        elif self.grating_index.read() == 2:
            self.limits.write(0, 15000, 'nm')
            self.set_position(10000)
        # set position for new grating
        if not g.offline.read():
            self.set_position(self.current_position.read(self.native_units))

    def stop(self):
        pass


### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)

    def create_frame(self, layout):
        layout.setMargin(5)

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


    mono = MicroHR()
    mono.initialize()
    print mono.description
    print mono.serial_number
    print mono.get_grating_details()

    mono.close()






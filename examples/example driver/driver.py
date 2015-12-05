### import ####################################################################


import os
import collections
import time

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.widgets as pw
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'examples',
                                 'example driver',
                                 'driver.ini'))


### driver ####################################################################


class Driver():

    def __init__(self):
        self.native_units = 'wn'
        # mutex attributes
        self.limits = pc.NumberLimits(units=self.native_units)
        self.current_position = pc.Number(name='Color', initial_value=0.,
                                          limits=self.limits,
                                          units=self.native_units, 
                                          display=True,
                                          set_method='set_position')
        self.offset = pc.Number(initial_value=0, 
                                units=self.native_units, display=True)
        # objects to be sent to PyCMDS
        self.exposed = [self.current_position]
        self.recorded = collections.OrderedDict()
        # finish
        self.gui = GUI(self)
        self.initialized = pc.Bool()

    def close(self):
        pass

    def get_position(self):
        return self.current_position.read()

    def initialize(self, inputs, address):
        self.address = address
        # recorded
        self.recorded['w0'] = [self.current_position, self.native_units, 1., '0', False]
        # finish
        self.initialized.write(True)
        self.address.initialized_signal.emit()

    def is_busy(self):
        return False
        
    def set_offset(self, offset):
        pass        
        
    def set_position(self, destination):
        # set your hardware
        self.get_position()
        
        

class Driver_offline(Driver):
    
    def initialize(self, inputs, address):
        self.address = address
        # recorded
        self.recorded['w0'] = [self.current_position, self.native_units, 1., '0', False]
        # finish
        self.initialized.write(True)
        self.address.initialized_signal.emit()


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

### import ####################################################################


import os

import time

from PyQt4 import QtGui, QtCore

import WrightTools.units as wt_units

import project
import project.classes as pc
import project.project_globals as g
main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'delays',
                                                     'pico',
                                                     'pico_delay.ini'))


### OPA object ################################################################


class OPA:

    def __init__(self):
        # list of objects to be exposed to PyCMDS
        self.native_units = 'wn'
        self.limits = pc.NumberLimits(min_value=1100, max_value=1600, units='wn')
        self.current_position = pc.Number(name='Color', initial_value=1300.,
                                          limits=self.limits,
                                          units='wn', display=True,
                                          set_method='set_position')
        self.exposed = [self.current_position]
        self.gui = gui()

    def close(self):
        pass

    def get_curve(self):
        pass

    def get_position(self):
        pass
    
    def get_motor_positions(self):
        pass

    def initialize(self, inputs=[]):
        pass

    def is_busy(self):
        return False
        
    def set_curve(self):
        pass

    def set_position(self, destination):
        self.current_position.write(destination)
        
    def set_motors(self):
        pass #send motors to positions


### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)

    def create_frame(self, layout):
        layout.setMargin(5)
       
        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by ps OPA')
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
    
    
    pass
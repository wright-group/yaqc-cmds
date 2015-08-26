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
                                                     
import project.precision_micro_motors.precision_motors as motors

ps_per_mm = 6.671281903963041 # a mm on the delay stage (factor of 2)


### delay object ##############################################################


class Delay:

    def __init__(self):
        # list of objects to be exposed to PyCMDS
        self.native_units = 'ps'
        self.limits = pc.NumberLimits(min_value=-100, max_value=100, units='ps')
        self.current_position = pc.Number(name='Delay', initial_value=0.,
                                          limits=self.limits,
                                          units='ps', display=True,
                                          set_method='set_position')
        self.exposed = [self.current_position]
        self.gui = gui()

    def close(self):
        self.motor.close()

    def get_position(self):
        position = self.motor.get_position('mm')
        delay = (position - self.zero) * ps_per_mm
        self.current_position.write(delay, 'ps')
        return delay

    def initialize(self, inputs, address):
        self.address = address
        self.index = inputs[0]
        motor_identity = motors.identity['D{}'.format(self.index)]
        self.motor = motors.Motor(motor_identity)
        self.zero = ini.read('D{}'.format(self.index), 'zero position (mm)')
        self.get_position()
        self.set_zero(self.zero)

    def is_busy(self):
        return not self.motor.is_stopped()

    def set_position(self, destination):
        destination_mm = self.zero + destination/ps_per_mm  
        self.motor.move_absolute(destination_mm, 'mm')
        if g.module_control.read():
            self.motor.wait_until_still()
        else:
            while self.is_busy():
                time.sleep(0.1)
                print self.get_position()
        self.get_position()
        
    def set_zero(self, zero):
        '''
        float zero mm
        '''
        self.zero = zero
        min_value = -self.zero * ps_per_mm
        max_value = (50. - self.zero) * ps_per_mm        
        self.limits.write(min_value, max_value, 'ps') 


### advanced gui ##############################################################


class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)

    def create_frame(self, layout):
        layout.setMargin(5)
       
        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by ps delay')
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
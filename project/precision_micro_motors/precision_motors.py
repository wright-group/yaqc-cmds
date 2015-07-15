### import ####################################################################

import os
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

from mcapi import *

import project.project_globals as g
main_dir = g.main_dir.read()
import project.ini_handler as ini
ini = ini.Ini(os.path.join(main_dir, 'project', 'precision_micro_motors', 'precision_motors.ini'))

### define motors #############################################################

# import shared motor parameters from ini
acceleration = ini.read('shared', 'acceleration')
gain = ini.read('shared', 'gain')
velocity = ini.read('shared', 'velocity')
dwell = ini.read('shared', 'dwell')

derivative_sample = 0.000341

# this is a placeholder but it needs to be redone
# we will need to seperate the controller and motor objects eventually somehow...

class Motor():
    def __init__(self, controller, axis, initial_position, mode = 1):
        self.ctrl = Mcapi()
        self.ctrl.Open(controller, mode)
        #filter = [2000,0.000341,0,0,0,0,0,0]
        #print motor.SetFilterConfigEx(axis,filter)
        self.ctrl.SetAcceleration(axis, acceleration)
        self.ctrl.SetGain(axis, gain)
        self.ctrl.SetPosition(axis, initial_position)
        self.ctrl.EnableAxis(axis, True)
        # import
        self.axis = axis
    def close(self):
        self.ctrl.EnableAxis(self.axis, False)
        self.ctrl.Close()
    def get_position(self):
        return self.ctrl.GetPositionEx(self.axis)
    def move_absolute(self, destination):
        pass
    def move_relative(self, distance, wait = False):
        self.ctrl.MoveRelative(self.axis, 10000)
        if wait:
            self.ctrl.WaitForStop(self.axis, dwell)

### testing ###################################################################

if __name__ == '__main__':

    if True:
        
        motor1 = Motor(ini.read('motor1', 'controller'), 
                       ini.read('motor1', 'axis'), 
                       ini.read('motor1', 'current_position'))
        
        motor1.move_relative(1000, wait = False)
        
        print motor1.get_position()

        motor1.close()
            
            
        
        
        
        
        
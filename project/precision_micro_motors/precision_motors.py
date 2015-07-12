### import #####################################################################

import os
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

from mcapi import *

import project.project_globals as g
main_dir = g.main_dir.read()
import project.ini_handler as ini
ini_path =  os.path.join(main_dir, 'project', 'precision_micro_motors', 'precision_motors.ini')

### define motors ##############################################################

#import shared motor parameters from ini
acceleration = ini.read(ini_path, 'shared', 'acceleration')
gain = ini.read(ini_path, 'shared', 'gain')
velocity = ini.read(ini_path, 'shared', 'velocity')
period = ini.read(ini_path, 'shared', 'period')

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
    def close(self):
        self.ctrl.EnableAxis(axis, False)
        self.ctrl.Close()
    def get_position(self):
        pass
    def move_absolute(self, destination):
        pass
    def move_relative(self, distance):
        pass
    
### testing ####################################################################

if __name__ == '__main__':
    
    if True:
        motor0_controller = ini.read(ini_path, 'motor0', 'controller')
        motor0_axis = ini.read(ini_path, 'motor0', 'axis')
        motor0_inital_position = ini.read(ini_path, 'motor0', 'current_position')
        
        motor0 = Motor(1, 2, motor0_inital_position)
        
        motor0.ctrl.MoveRelative(1, 10000)
        motor0.ctrl.WaitForStop(axis, period)
        print motor0.ctrl.GetPositionEx(2)        
        
        motor0.close()

    if False:
        
        for _ in range(5):
            # create a controllerobject an open the controller at ID #0
            axis = 2
            #filter = [2000,0.000341,0,0,0,0,0,0]
            acceleration = 10000
            gain = 260
            velocity = 8000 
            position = 300000
            state = True
            distance = -100000
            period = 0.001
            mode = 1
             
            motor = Mcapi()
            print motor.Open(1, mode)
            #print motor.SetFilterConfigEx(axis,filter)
            print motor.SetAcceleration(axis, acceleration)
            print motor.SetGain(axis, gain)
            print motor.SetPosition(axis, position)
            print motor.EnableAxis(axis, True)
            
            print motor.MoveRelative(axis, distance)
            print motor.WaitForStop(axis, period)
            
            print motor.EnableAxis(axis,False)
            print motor.GetPositionEx(axis)
            print motor.Close()
            #init?
            
            
        
        
        
        
        
### import ####################################################################

import os
import time
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

from mcapi import *

import project.project_globals as g
main_dir = g.main_dir.read()
import project.ini_handler as ini
ini = ini.Ini(os.path.join(main_dir, 'project', 'precision_micro_motors', 'precision_motors.ini'))

### define ####################################################################

# import shared motor parameters from ini
acceleration = ini.read('shared', 'acceleration')
gain = ini.read('shared', 'gain')
velocity = ini.read('shared', 'velocity')
dwell = ini.read('shared', 'dwell')
integral_gain = ini.read('shared', 'integral_gain')

# hardcoded
counts_per_mm = 58200

# dictionary to contain motor correspondance
identity = {'D1': 'motor0', 
            'D2': 'motor1', 
            'OPA1 grating': '',
            'OPA1 BBO': '',
            'OPA1 mixer': '',
            'OPA2 grating': 'motor8',
            'OPA2 BBO': 'motor9',
            'OPA2 mixer': 'motor10',
            'OPA3 grating': '',
            'OPA3 BBO': '',
            'OPA3 mixer': ''}

### control ###################################################################

def open_controllers():
    mode = 1 # not sure what this argument does
    controller0 = Mcapi()
    controller0.Open(0, mode)
    controller1 = Mcapi()
    controller1.Open(1, mode)
    return [controller0, controller1]
# open controllers upon import
controllers = open_controllers()

def close_controllers():
    for controller in controllers:
        controller.Close()
        controllers.remove(controller)

# a list to contain initialized motors
initialized_motors = []

class Motor():
    
    def __init__(self, ini_section):
        # import from ini
        print 'ini section', ini_section
        print type(ini_section)
        self.ini_section = ini_section
        self.name = ini.read(self.ini_section, 'name')
        controller_index = ini.read(self.ini_section, 'controller')
        self.axis = ini.read(self.ini_section, 'axis')
        initial_position = ini.read(self.ini_section, 'current_position')
        # set conditions for motor
        self.ctrl = controllers[controller_index]
        self.filter = MCFILTEREX()
        self.filter.Gain = gain
        self.filter.IntegralGain = 0.
        self.filter.IntegrationLimit = 0.
        self.filter.IntegralOption = 0
        self.filter.DerivativeGain = 2000.
        self.filter.DerSamplePeriod = 0.000341
        self.filter.FollowingError = 0.
        self.filter.VelocityGain = 0.
        self.filter.AccelGain = 0.
        self.filter.DecelGain = 0.
        self.filter.EncoderScaling = 0.
        self.filter.UpdateRate = 0
        self.filter.PositionDeadband = 0.
        self.filter.DelayAtTarget = 0.
        self.filter.OutputOffset = 0.
        self.filter.OutputDeadband = 0.
        self.ctrl.SetFilterConfigEx(self.axis, self.filter)
        self.ctrl.SetAcceleration(self.axis, acceleration)
        self.ctrl.SetGain(self.axis, gain)
        self.ctrl.SetVelocity(self.axis, velocity)
        self.ctrl.SetPosition(self.axis, initial_position)
        self.ctrl.EnableAxis(self.axis, True)
        # add to list of initialized motors
        initialized_motors.append(self)
        
    def close(self, close_controllers_if_last=True):
        '''
        bool close_controllers_if_last toggles closing of precision motor API
        controllers if this motor is closing and no other motors are open
        '''
        self.get_position()
        self.ctrl.EnableAxis(self.axis, False)
        # remove from list of initialized motors
        initialized_motors.remove(self)
        # close controller if initialized motors is now empty
        if close_controllers_if_last:
            # wait for a while to prevent race conditions
            time.sleep(0.01)
            if len(initialized_motors) == 0:
                close_controllers()
        
    def get_position(self, returned_units='counts'):
        self.current_position = self.ctrl.GetPositionEx(self.axis)
        ini.write(self.ini_section, 'current_position', int(self.current_position))
        if returned_units == 'counts':
            return self.current_position
        elif returned_units == 'mm':
            return counts_per_mm*self.current_position
        else:
            print 'returned_units kind', returned_units, 'not recognized in precision_motors.get_position'
            
    def is_stopped(self, timeout=60):
        return bool(self.ctrl.IsStopped(self.axis, timeout))
        
    def move_absolute(self, destination, input_units='counts', wait=False):
        if input_units == 'counts':
            pass
        else:
            destination *= counts_per_mm
        self.ctrl.MoveAbsolute(self.axis, destination)
        if wait:
            self.wait_until_still()
    
    def move_relative(self, distance, wait=False):
        '''
        int distance steps
        '''
        self.ctrl.MoveRelative(self.axis, distance)
        if wait:
            self.wait_until_still()
    
    def wait_until_still(self):
        self.ctrl.WaitForStop(self.axis, dwell)
        self.get_position()
            

### testing ###################################################################

if __name__ == '__main__':
    
    if True:
        #move all motors to a destination
        motor_sections = ['motor0', 'motor1', 'motor8', 'motor9', 'motor10']
        
        # initialize motors
        motors = []
        for section in motor_sections:
            motors.append(Motor(section))
            
        # set motors
        destination = int(counts_per_mm*25)
        for motor in motors:
            motor.move_absolute(destination, wait=False)
            
        # wait
        for motor in motors:
            motor.wait_until_still()
            
        for motor in motors:
            print motor.is_stopped()
            
        # close
        for motor in motors:
            print motor.get_position()
            motor.close()
        
    if False:
        #mess with a single motor
        motor = Motor('motor10')
        distance = int(1*counts_per_mm)
        motor.move_relative(distance)
        motor.wait_until_still()
        motor.close()
        
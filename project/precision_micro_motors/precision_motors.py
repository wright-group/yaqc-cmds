### import ####################################################################

import os
import time
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

from mcapi import *

import project.project_globals as g
main_dir = g.main_dir.read()
import project.classes as pc
import project.ini_handler as ini
ini = ini.Ini(os.path.join(main_dir, 'project', 'precision_micro_motors', 'precision_motors.ini'))

### define ####################################################################

# import shared motor parameters from ini
acceleration = ini.read('shared', 'acceleration')
gain = ini.read('shared', 'gain')
velocity = ini.read('shared', 'velocity')
dwell = ini.read('shared', 'dwell')
integral_gain = ini.read('shared', 'integral_gain')
derivative_gain = ini.read('shared', 'derivative_gain')
derivative_sample = ini.read('shared','derivative_sample')


# hardcoded
counts_per_mm = 58200

# dictionary to contain motor correspondance
identity = {'D1': 'motor0', 
            'D2': 'motor1', 
            'OPA1 grating': 'motor2',
            'OPA1 BBO': 'motor3',
            'OPA1 mixer': 'motor4',
            'OPA2 grating': 'motor8',
            'OPA2 BBO': 'motor9',
            'OPA2 mixer': 'motor10',
            'OPA3 grating': 'motor5',
            'OPA3 BBO': 'motor6',
            'OPA3 mixer': 'motor7'}

### control ###################################################################


def translate(mm):
    return int((50-mm)*counts_per_mm)

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
        self.ini_section = ini_section
        self.name = ini.read(self.ini_section, 'name')
        controller_index = ini.read(self.ini_section, 'controller')
        self.axis = ini.read(self.ini_section, 'axis')
        initial_position = ini.read(self.ini_section, 'current_position')
        self.tolerance = ini.read(self.ini_section,'tolerance')
        # set conditions for motor
        self.ctrl = controllers[controller_index]
        self.ctrl.EnableAxis(self.axis, True)
        self.filter = MCFILTEREX()
        self.filter.Gain = gain
        self.filter.IntegralGain = integral_gain
        self.filter.IntegrationLimit = 0.
        self.filter.IntegralOption = 0
        self.filter.DerivativeGain = derivative_gain
        self.filter.DerSamplePeriod = derivative_sample
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
        # add to list of initialized motors
        initialized_motors.append(self)
        self.open = True
        self.offset = 0
        self.offset_list = []
        
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
        self.open = False
        
    def get_position(self, returned_units='mm'):
        self.current_position = self.ctrl.GetPositionEx(self.axis)
        ini.write(self.ini_section, 'current_position', int(self.current_position))
        if returned_units == 'counts':
            return self.current_position
        elif returned_units == 'mm':
            return 50. - self.current_position/counts_per_mm
        else:
            print 'returned_units kind', returned_units, 'not recognized in precision_motors.get_position'
        self._offset_adj(self.last_destination,self.current_position)
            
    def is_stopped(self, timeout=0.1):
        '''
        Timeout in seconds. It seems that the controller waits at least
        timeout if it is not stopped.
        '''
        if self.open:
            return bool(self.ctrl.IsStopped(self.axis, timeout))
        else:
            return True
        
    def move_absolute(self, destination, input_units='mm', wait=False):
        go = True
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            destination = 50*counts_per_mm - destination*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in precision_motors.move_absolute'
            go = False
        
        if go and abs(self.ctrl.GetPositionEx(self.axis)-destination) >= self.tolerance:
            ini.write(self.ini_section, 'last_destination', int(destination))
            self.last_destination = int(destination)
            print self.axis, int(destination+self.offset)
            self.ctrl.MoveAbsolute(self.axis, int(destination+self.offset))
        if wait:
            self.wait_until_still()
    
    def move_relative(self, distance, input_units='mm', wait=False):
        go = True
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            distance = - distance*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in precision_motors.move_relative'
            go = False
            
        if go and abs(self.ctrl.GetPositionEx(self.axis)-destination) >= self.tolerance:
            ini.write(self.ini_section, 'last_destination', int(self.current_position + distance))
            self.ctrl.MoveRelative(self.axis, int(distance+self.offset))
        if wait:
            self.wait_until_still()
    
    def wait_until_still(self, method=None):
        while not self.is_stopped():  # sleep is inside of is_stopped call, essentially
            self.get_position()
            if method:
                method()
        # self.ctrl.WaitForStop(self.axis, dwell)
        # the wait for stop method on the controller stops coms for all motors
        # connected to the board which isn't what we want here
        self.get_position()
        
    def stop(self):
        self.ctrl.Stop(self.axis)
        self.get_position()
     
    def get_FollowingError(self):
        return self.ctrl.GetFollowingError(self.axis)
        
    def get_target(self):
        return self.ctrl.GetTargetEx(self.axis)
        
    def at_target(self):
        return self.ctrl.IsAtTarget(self.axis,3)
    
    def MoveToPoint(self,index):
        self.ctrl.MoveToPoint(self.axis,index)
        
    def _offset_adj(self,goal,pos):
        if len(offset_list)>49:        
            self.offset_list.pop(0)
        self.offset_list.append(int(goal)-pos)
        self.offset = np.average(self.offset_list)+self.offset
        
### testing ###################################################################

if __name__ == '__main__':
    
    import numpy as np
    
    if False:
        # move all motors to a destination
        motor_sections = ['motor0', 'motor1']
        
        # initialize motors
        motors = []
        for section in motor_sections:
            motors.append(Motor(section))
            
        # set motors
        for motor in motors:
            motor.move_absolute(30, 'mm', wait=False)
            
        # wait
        for motor in motors:
            motor.wait_until_still()
            
        # close
        for motor in motors:
            print motor.get_position('mm')
            motor.close()
        
    if False:
        #mess with a single motor
        motor = Motor('motor1')
        motor.move_absolute(25, 'mm')
        motor.wait_until_still()
        print motor.is_stopped()
        print motor.get_position('mm')
        motor.close()
        
    if False:
        # move a single motor relative
        motor = Motor('motor9')
        motor.move_relative(-0.5, 'mm')
        motor.wait_until_still()
        print motor.get_position('mm')
        motor.close()

    if False:
        motor = Motor('motor7')
        motor.move_absolute(25.0000)
        move = 0.0005
        #pos_in_cn = counts_per_mm * np.arange(25.0,25.05,0.0005)
        final_pos = []
        for j in range(15):
            p = []
            for x in range(100):
                ini.write(motor.ini_section, 'last_destination', int(x))
                motor.move_relative(motor.axis, x)
                motor.wait_until_still()
                time.sleep(.01)
                p.append(motor.get_position('counts'))
            final_pos.append(p)
        motor.close()
        
    if False:
        motor = Motor('motor7')
        pos_in_cn = counts_per_mm * np.arange(25.05,25.0,-0.0005)
        final_pos = []
        targets = []
        for j in range(5):
            p = []
            t=[]
            for x in pos_in_cn:
                x = int(x)
                ini.write(motor.ini_section, 'last_destination', int(x))
                motor.ctrl.MoveAbsolute(motor.axis, x)
                t.append(x-motor.get_target())
                motor.wait_until_still()
                time.sleep(.01)
                p.append(x-motor.get_position('counts'))
            final_pos.append(p)
            targets.append(t)
        motor.close()
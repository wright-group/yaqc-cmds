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
            'OPA2 Grating': 'motor8',
            'OPA2 BBO': 'motor9',
            'OPA2 Mixer': 'motor10',
            'OPA3 Grating': 'motor2',
            'OPA3 BBO': 'motor3',
            'OPA3 Mixer': 'motor4'}

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



from PyQt4 import QtCore

class Busy(QtCore.QMutex):

    def __init__(self):
        '''
        QMutex object to communicate between threads that need to wait \n
        while busy.read(): busy.wait_for_update()
        '''
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
        self.type = 'busy'
        self.update_signal = None

    def read(self):
        return self.value

    def write(self, value):
        '''
        bool value
        '''
        self.tryLock(10)  # wait at most 10 ms before moving forward
        self.value = value
        self.unlock()
        self.WaitCondition.wakeAll()

    def wait_for_update(self, timeout=5000):
        '''
        wait in calling thread for any thread to call 'write' method \n
        int timeout in milliseconds
        '''
        if self.value:
            return self.WaitCondition.wait(self, msecs=timeout)

busy = Busy()





class Motor():
    
    def __init__(self, ini_section):
        # import from ini
        self.ini_section = ini_section
        self.name = ini.read(self.ini_section, 'name')
        controller_index = ini.read(self.ini_section, 'controller')
        self.axis = ini.read(self.ini_section, 'axis')
        initial_position = ini.read(self.ini_section, 'current_position')
        self.destination = initial_position
        self.tolerance = ini.read(self.ini_section,'tolerance')
        self.backlash_enabled = ini.read(self.ini_section, 'enable_backlash_correction')
        self.backlash = ini.read(self.ini_section, 'backlash')  # steps
        self.moving = False
        self.backlashing = False
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
        self.current_position = initial_position
        self.current_position_mm = 50. - float(self.current_position)/float(counts_per_mm)
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
        while busy.read():
            busy.wait_for_update()
        busy.write(True)
        time.sleep(0.1)  # limits the maximum rate of requests to control - cannot go lower than 50 ms
        self.current_position = int(self.ctrl.GetPositionEx(self.axis))
        self.current_position_mm = 50. - float(self.current_position)/float(counts_per_mm)
        busy.write(False)
        ini.write(self.ini_section, 'current_position', int(self.current_position))
        if returned_units == 'counts':
            return self.current_position
        elif returned_units == 'mm':
            return self.current_position_mm
        else:
            print 'returned_units kind', returned_units, 'not recognized in precision_motors.get_position'
        #self._offset_adj(self.last_destination, self.current_position)
            
    def is_stopped(self):
        if self.open and self.moving:
            current_destination = self.destination
            if self.backlash_enabled and self.backlashing:
                current_destination += self.backlash
            difference = abs(self.current_position - current_destination)
            #print(self.axis, self.current_position, current_destination, self.tolerance, difference)
            stopped = difference <= self.tolerance
            self.previously_recorded_counts = self.current_position
            if stopped and self.backlashing:
                self.backlashing = False
                self.move_relative(-self.backlash, input_units='counts', wait=False)
                out = False
            else:
                out = stopped
        else:
            out = True
        if out == True:
            self.moving = False
        return out
        
    def move_absolute(self, destination, input_units='mm', wait=False):
        self.moving = True
        go = True
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            destination = 50*counts_per_mm - destination*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in precision_motors.move_absolute'
            go = False
        self.destination = int(destination)  # counts
        if go and abs(self.current_position-destination) >= self.tolerance:
            # record destination (in case of crash during motion)
            ini.write(self.ini_section, 'last_destination', int(destination))            
            if self.backlash_enabled:
                # move to backlash position, if backlash enabled
                self.backlashing = True
                intermediate_destination = destination+self.backlash
                while busy.read():
                    busy.wait_for_update()
                busy.write(True)
                self.ctrl.MoveAbsolute(self.axis, int(intermediate_destination+self.offset))
                busy.write(False)
            else:
                # otherwise, go directly
                while busy.read():
                    busy.wait_for_update()
                busy.write(True)
                self.ctrl.MoveAbsolute(self.axis, int(destination+self.offset))
                busy.write(False)
            if wait:
                time.sleep(0.1)  # wait for the motor to start moving
                self.wait_until_still()
        
    def move_relative(self, distance, input_units='mm', wait=False):
        self.moving = True
        # does not apply backlash
        go = True
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            distance = - distance*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in precision_motors.move_relative'
            go = False
        while busy.read():
            busy.wait_for_update()
        busy.write(True)
        self.ctrl.MoveRelative(self.axis, int(distance+self.offset))
        busy.write(False)
        if wait:
            time.sleep(0.1)  # wait for the motor to start moving
            self.wait_until_still()
    
    def wait_until_still(self, method=None):
        while not self.is_stopped():
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
        # I'm not sure what this does
        # perhaps it should be removed
        # - Blaise 2016-09-07
        if len(offset_list)>49:        
            self.offset_list.pop(0)
        self.offset_list.append(int(goal)-pos)
        self.offset = np.average(self.offset_list)+self.offset

        
### testing ###################################################################


if __name__ == '__main__':
    if False:
        
        import numpy as np
    
        #mess with a single motor
        motor = Motor('motor4')
        motor.move_absolute(25, 'mm')
        motor.wait_until_still()
        print(motor.get_position('mm'))
        motor.close()

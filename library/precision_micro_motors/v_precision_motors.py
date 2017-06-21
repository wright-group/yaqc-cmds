### import ####################################################################
print "Virtual motor load attempted"

import os
import time
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

#from mcapi import * ### Not needed for virtual motors

import project.project_globals as g
main_dir = g.main_dir.read()
import project.ini_handler as ini
ini = ini.Ini(os.path.join(main_dir, 'library', 'precision_micro_motors', 'precision_motors.ini'))

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
            'OPA1 grating': 'motor2',
            'OPA1 BBO': 'motor3',
            'OPA1 mixer': 'motor4',
            'OPA2 grating': 'motor8',
            'OPA2 BBO': 'motor9',
            'OPA2 mixer': 'motor10',
            'OPA3 grating': 'motor6',
            'OPA3 BBO': 'motor7',
            'OPA3 mixer': 'motor8'}

### control ###################################################################


def translate(mm):
    return (50-mm)*counts_per_mm

def open_controllers():
    controller0 = 0
    controller1 = 1
    return [controller0, controller1]

# open controllers upon import
controllers = open_controllers()

def close_controllers():
    for controller in controllers:
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
        # set conditions for motor
        self.acceleration = acceleration
        self.velocity = velocity
        self.dwell = dwell
        self.current_position = initial_position

        # add to list of initialized motors
        initialized_motors.append(self)
        self.open = True

    def close(self, close_controllers_if_last=True):
        '''
        bool close_controllers_if_last toggles closing of precision motor API
        controllers if this motor is closing and no other motors are open
        '''
        self.get_position()
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
        if returned_units == 'counts':
            return self.current_position
        elif returned_units == 'mm':
            return 50. - self.current_position/counts_per_mm
        else:
            print 'returned_units kind', returned_units, 'not recognized in v_precision_motors.get_position'

    def is_stopped(self, timeout=60):
        return True

    def move_absolute(self, destination, input_units='mm', wait=False):
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            destination = 50*counts_per_mm - destination*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in v_precision_motors.move_absolute'
        self.current_position = destination
        if wait:
            self.wait_until_still()

    def move_relative(self, distance, input_units='mm', wait=False):
        if input_units == 'counts':
            pass
        elif input_units == 'mm':
            distance = - distance*counts_per_mm
        else:
            print 'input_units kind', input_units, 'not recognized in v_precision_motors.move_relative'
        self.current_position = self.current_position + distance
        if wait:
            self.wait_until_still()

    def wait_until_still(self):
        pass

    def stop(self):
        self.get_position()


### testing ###################################################################

if __name__ == '__main__':

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
        motor.move_absolute(20, 'mm')
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

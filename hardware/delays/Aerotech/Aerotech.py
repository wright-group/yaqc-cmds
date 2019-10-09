### import ####################################################################


import time

import project.project_globals as g
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI
import project.com_handler as com_handler


### define ####################################################################


main_dir = g.main_dir.read()


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        BaseDriver.__init__(self, *args, **kwargs)
        self.com_channel = kwargs.pop('port')
        kwargs['native_units'] = 'ps'
        self.index = kwargs.pop('index')
        self.native_per_mm = 6.671281903963041

    def close(self):
        self.port.write('S')
        self.port.close()

    def get_motor_position(self):
        # I am trying to prevent some timing condition that I don't understand fully
        # ---Blaise 2017-08-13
        try:
            p = float(self.port.write('G', then_read=True))
            self.motor_position.write(p)
            return(p)
        except BaseException as error:
            print('AEROTECH GET MOTOR POSITION EXCEPT', error)
            time.sleep(1)
            self.port.instrument.reset_input_buffer()
            self.port.instrument.reset_output_buffer()
            self.port.flush()
            return self.get_motor_position()

    def get_position(self):
        position = self.get_motor_position()
        # calculate delay
        delay = (position - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.position.write(delay, self.native_units)
        # return
        return delay
    
    def home(self):
        self.port.write('H')
        while self.is_busy():
            self.get_position()
            time.sleep(1)
        self.set_position(self.hardware.destination.read())

    def initialize(self):
        self.port = com_handler.get_com(self.com_channel)   
        self.motor_limits.write(0, 250, 'mm')
        self.update_recorded()
        self.set_zero(self.zero_position.read())
        self.get_position()
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        if self.port.is_open():
            self.port.flush()
            status = self.port.write('Q', then_read=True)
            if status == 'B':
                return True
            elif status == 'R':
                return False
        else:
            return False

    def set_position(self, destination):
        destination_mm = self.zero_position.read() + destination/(self.native_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)

    def set_motor_position(self, motor_position):
        command = 'M %f'%motor_position
        self.port.write(command)
        while self.is_busy():
            self.get_position()
            time.sleep(0.1)
        self.get_position()
        BaseDriver.set_motor_position(self, motor_position)
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * self.native_per_mm * self.factor.read()
        max_value = (250. - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'ps')


### gui #######################################################################


class GUI(BaseGUI):
    pass

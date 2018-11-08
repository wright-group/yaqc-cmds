### import ####################################################################


import os
import time
import warnings

import project.com_handler as com_handler
import project.classes as pc
import project.project_globals as g
from project.ini_handler import Ini
from hardware.delays.delays import Driver as BaseDriver
from hardware.delays.delays import GUI as BaseGUI


### define ####################################################################


main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'hardware', 'delays',
                                 'MFA',
                                 'MFA.ini'))


### define ####################################################################


# TODO: move com channel to .ini
COM_channel = 4

error_dict = {'0': None,
              '@': None,
              'A': 'Unknown message code or floating point controller address [A]',
              'B': 'Controller address not correct [B]',
              'C': 'Parameter missing or out of range [C]',
              'D': 'Command not allowed [D]',
              'E': 'Home sequence already started [E]',
              'F': 'ESP stage name unknown [F]',
              'G': 'Displacement out of limits [G]',
              'H': 'Command not allowed in NOT REFERENCED state [H]',
              'I': 'Command not allowed in CONFIGURATION state [I]',
              'J': 'Command not allowed in DISABLE state [J]',
              'K': 'Command not allowed in READY state [K]',
              'L': 'Command not allowed in HOMING state [L]',
              'M': 'Command not allowed in MOVING state [M]',
              'N': 'Current position out of software limit [N]',
              'S': 'Communication time-out [S]',
              'U': 'Error during EEPROM access [U]',
              'V': 'Error during command execution [V]',
              'W': 'Command not allowed for PP version [W]',
              'X': 'Command not allowed for CC version [X]'}

controller_states = {'0A': 'NOT REFERENCED from reset',
                     '0B': 'NOT REFERENCED from HOMING',
                     '0C': 'NOT REFERENCED from CONFIGURATION',
                     '0D': 'NON REFERENCED from DISABLE',
                     'OE': 'NOT REFERENCED from READY',
                     'OF': 'NOT REFERENCED from MOVING',
                     '10': 'NOT REFERENCED ESP stage error',
                     '11': 'NOT REFERENCED from JOGGING',
                     '14': 'CONFIGURATION',
                     '1E': 'HOMING command from RS-232-C',
                     '1F': 'HOMING command by SMC-RC',
                     '28': 'MOVING',
                     '32': 'READY from HOMING',
                     '33': 'READY from MOVING',
                     '34': 'READY from DISABLE',
                     '35': 'READY from JOGGING',
                     '3C': 'DISABLE from READY',
                     '3D': 'DISABLE from MOVING',
                     '3E': 'DISABLE from JOGGING',
                     '46': 'JOGGING from READY',
                     '47': 'JOGGING from DISABLE'}
              
status_dict = {value: key for key, value in controller_states.items()}


### driver ####################################################################


class Driver(BaseDriver):

    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index')
        self.axis = kwargs.pop('axis')
        self.native_per_mm = 6000.671281903963041
        self.status = pc.String(display=True)
        super(self.__class__, self).__init__(*args, **kwargs)
        self.motor_limits = pc.NumberLimits(0, 25, 'mm')
        self.motor_position.decimals = 5
        self.zero_position.decimals = 5
        
    def _tell_status(self):
        # read
        status = self.port.write(str(self.axis)+'TS', then_read=True)
        # process
        out = {}
        try:
            status = str(status).split('TS')[1]
            out['error'] = status[:4]
            out['state'] = status[4:6]
            self.status.write(controller_states[out['state']].split('from')[0])
        except:
            out['error'] = None
            out['state'] = None
        return out

    def close(self):
        self.port.close()

    def get_position(self):
        # read
        # KFS 2018-05-24: Loop was added because there was some miscommunication
        # Causing the response to be different than expected
        # The root cause is as yet unknown, but the strategy to mitigate is to simply
        # retry the request until the expected response is recieved.
        # Thus far, it has worked.
        while(True):
            try:
                position = self.port.write(str(self.axis)+'TP', then_read=True)
                # proccess (mm)
                position = float(str(position).split('TP')[1])
            except IndexError:
                warnings.warn("Unexpected reply from MFA: expected '#TP##', got '{}'".format(position))
            else:
                break
        self.motor_position.write(position, 'mm')
        # calculate delay (fs)
        delay = (position - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.position.write(delay, 'fs')
        # return
        return delay
        
    def home(self, inputs=[]):
        self.port.write(str(self.axis)+'RS')  # reset
        time.sleep(5)
        self.port.write(str(self.axis)+'OR')  # execute home search
        while not self._tell_status()['state'] == status_dict['READY from HOMING']:
            time.sleep(0.1)
        time.sleep(5)
        self.set_position(self.hardware.destination.read())

    def initialize(self):
        self.port = com_handler.get_com(COM_channel)   
        self.set_zero(self.zero_position.read())
        self.label.updated.connect(self.update_recorded)
        self.update_recorded()
        self.get_position()
        self._tell_status()
        self.initialized.write(True)
        self.initialized_signal.emit()
        
    def on_factor_updated(self):
        if self.factor.read() == 0:
            self.factor.write(1)
        # record factor
        self.factor.save()
        # update limits
        min_value = -self.zero_position.read() * self.native_per_mm * self.factor.read()
        max_value = (25. - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'fs')
        
    def set_position(self, destination):
        # get destination_mm
        destination_mm = self.zero_position.read() + destination/(self.native_per_mm * self.factor.read())
        self.set_motor_position(destination_mm)
        
    def set_motor_position(self, motor_position):
        """
        motor_position in mm
        """
        # move hardware
        # TODO: consider backlash correction? 
        self.port.write(str(self.axis)+'PA'+str(motor_position))
        while not self._tell_status()['state'] == status_dict['READY from MOVING']:
            time.sleep(0.01)
            self.get_position()
        # get final position
        self.get_position()
        
    def set_zero(self, zero):
        self.zero_position.write(zero)
        min_value = -self.zero_position.read() * self.native_per_mm * self.factor.read()
        max_value = (25. - self.zero_position.read()) * self.native_per_mm * self.factor.read()
        self.limits.write(min_value, max_value, 'fs')
        



### gui #######################################################################


class GUI(BaseGUI):
    
    def initialize(self):
        self.attributes_table.add('Status', self.hardware.driver.status)
        BaseGUI.initialize(self)

### import ####################################################################

import pyvisa

### define ####################################################################

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

### address motor #############################################################

class SMC100():

    def __init__(self): 
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource('ASRL%i::INSTR'%COM_channel)
        self.instrument.baud_rate = 57600
        self.instrument.end_input = pyvisa.constants.SerialTermination.termination_char 
        
    def move_absolute(self, axis, destination):
        '''
        int axis, float destination (mm)
        returns []
        '''
        self.instrument.write(unicode(str(axis)+'PA'+str(destination)))
        #print self.instrument.read()
        
    def shut_down(self): 
        self.instrument.close()
        
    def tell_control_status(self, axis):
        '''
        int axis
        returns [control status]
        '''
        self.instrument.write(unicode(str(axis)+'TS'))
        status = self.instrument.read()
        return [status]
        
    def tell_current_position(self, axis):
        '''
        int axis
        returns [position (mm)]
        '''
        self.instrument.write(unicode(str(axis)+'TP'))
        position = self.instrument.read()
        position = str(position).split('TP')[1]
        return float(position)

### testing ###################################################################

if __name__ == '__main__':

    delay = SMC100()
    
    print delay.tell_control_status(2)
    delay.move_absolute(2, 10.)
    print delay.tell_current_position(2)
    
    delay.shut_down()

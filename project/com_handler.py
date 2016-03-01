### import ####################################################################


import time

from PyQt4 import QtCore

import pyvisa
resource_manager = pyvisa.ResourceManager()

import project.project_globals as g
import project.classes as pc


### com class #################################################################


open_coms = {}

class COM(QtCore.QMutex):
    
    def __init__(self, port, baud_rate=57600):
        QtCore.QMutex.__init__(self)
        self.port_index = port
        self.rm = pyvisa.ResourceManager()
        self.instrument = resource_manager.open_resource('ASRL%i::INSTR'%self.port_index)
        self.instrument.baud_rate = baud_rate
        self.instrument.end_input = pyvisa.constants.SerialTermination.termination_char
        self.external_lock_control = False
        g.shutdown.add_method(self.close)

    def close(self):
        self.instrument.close()
    
    def read(self):
        if not self.external_lock_control: self.lock()
        value = self.instrument.read()
        if not self.external_lock_control: self.unlock()
        return value
        
    def write(self, string, then_read=False):
        if not self.external_lock_control: self.lock()
        self.instrument.write(unicode(string))
        if then_read:
            value = str(self.instrument.read())
        else:
            value = None
        if not self.external_lock_control: self.unlock()
        return value

creating_com = pc.Busy()

def get_com(port, baud_rate=57600):
    '''
    int port
    
    returns com object
    '''
    # one at a time
    while creating_com.read():
        creating_com.wait_for_update()
    creating_com.write(True)
    # return open com if already open
    out = None
    for key in open_coms.keys():
        if key == port:
            out = open_coms[key]
    # otherwise open new com
    if not out:
        out = COM(port, baud_rate)
        open_coms[port] = out 
    # finish
    creating_com.write(False)
    return out
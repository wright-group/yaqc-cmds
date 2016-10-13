'''
PyCMDS thread safe wrapper for pyvisa com port communication
'''


### import ####################################################################


import time

from PyQt4 import QtCore

import pyvisa

import project.project_globals as g
import project.classes as pc


### define ####################################################################


open_coms = {}


creating_com = pc.Busy()


### com class #################################################################



class COM(QtCore.QMutex):
    
    def __init__(self, port, baud_rate, timeout, write_termination=u'\r\n'):
        QtCore.QMutex.__init__(self)
        self.port_index = port
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource('ASRL%i::INSTR'%self.port_index)
        self.instrument.baud_rate = baud_rate
        self.instrument.end_input = pyvisa.constants.SerialTermination.termination_char
        self.instrument.timeout = timeout
        self.instrument.write_termination = write_termination
        self.external_lock_control = False
        g.shutdown.add_method(self.close)

    def _read(self):
        return str(self.instrument.read())

    def close(self):
        self.instrument.close()
        
    def flush(self, then_delay=0.):
        if not self.external_lock_control: self.lock()
        self.instrument.flush(pyvisa.constants.VI_IO_IN_BUF)
        self.instrument.flush(pyvisa.constants.VI_IO_OUT_BUF)
        if not self.external_lock_control: self.unlock()
    
    def read(self):
        if not self.external_lock_control: self.lock()
        value = self._read()
        if not self.external_lock_control: self.unlock()
        return str(value)
        
    def write(self, string, then_read=False):
        if not self.external_lock_control: self.lock()
        self.instrument.write(unicode(string))
        if then_read:
            value = self._read()
        else:
            value = None
        if not self.external_lock_control: self.unlock()
        return value


def get_com(port, baud_rate=57600, timeout=1000):
    '''
    int port
    
    returns com object
    
    timeout in ms
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
        out = COM(port, baud_rate, timeout)
        open_coms[port] = out 
    # finish
    creating_com.write(False)
    return out

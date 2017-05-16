'''
PyCMDS thread safe wrapper for pyvisa com port communication
'''


### import ####################################################################


import time

from PyQt4 import QtCore

import serial

#import project.project_globals as g
#import project.classes as pc


### define ####################################################################


open_coms = {}


#creating_com = pc.Busy()


### com class #################################################################



class COM(QtCore.QMutex):
    
    def __init__(self, port, baud_rate, timeout, write_termination='\n', data='ASCII', size=-1):
        QtCore.QMutex.__init__(self)
        self.port_index = port
        self.instrument = serial.Serial(port,baud_rate,timeout=timeout)
        self.external_lock_control = False
        self.data = data
        self.write_termination = write_termination
        self.size = size
#        g.shutdown.add_method(self.close)

    def _read(self):
        if self.data == 'pass':
            return self.instrument.read()
        elif self.data == 'ASCII':
            buf = b''
            char = self.instrument.read()
            while char != b'' and char != self.write_termination:
                buf = buf + char
                char = self.instrument.read()
            return buf.decode('utf-8')
        else:
            if size > 0:
                return [int(i) for i in self.instrument.read(size)]
            else:
                buf = b''
                char = self.instrument.read()
                while char != b'':
                    buf = buf + char
                    char = self.instrument.read()
                return [int (i) for i in buf]
                

    def close(self):
        self.instrument.close()
        
    def flush(self, then_delay=0.):
        if not self.external_lock_control: self.lock()
        self.instrument.flush()
        self.instrument.reset_input_buffer()
        self.instrument.reset_output_buffer()
        if not self.external_lock_control: self.unlock()
    
    def read(self):
        if not self.external_lock_control: self.lock()
        value = self._read()
        if not self.external_lock_control: self.unlock()
        return value
        
    def write(self, data, then_read=False):
        if not self.external_lock_control: self.lock()
        if self.data == 'pass':
            value = self.instrument.write(data)
        elif self.data == 'ASCII':
            value = self.instrument.write(data)#Python3: bytes(data,'utf-8'))
            if data[-1] != self.write_termination:
                self.instrument.write(self.write_termination)#Python 3: bytes(self.write_termination,'utf-8'))
                value+=1
        else:
            value = self.instrument.write(''.join([chr(i) for i in data]))# Python3: bytes(data))
        if then_read:
            value = self._read()
        if not self.external_lock_control: self.unlock()
        return value


def get_com(port, baud_rate=57600, timeout=1000, **kwargs):
    '''
    int port
    
    returns com object
    
    timeout in ms
    '''
    # one at a time
#    while creating_com.read():
#        creating_com.wait_for_update()
#    creating_com.write(True)
    # return open com if already open
    out = None
    for key in open_coms.keys():
        if key == port:
            out = open_coms[key]
    # otherwise open new com
    if not out:
        out = COM(port, baud_rate, timeout/1000., **kwargs)
        open_coms[port] = out 
    # finish
#    creating_com.write(False)
    return out

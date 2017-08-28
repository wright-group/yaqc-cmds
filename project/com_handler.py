"""
PyCMDS thread safe wrapper for serial communication.
"""


### import ####################################################################


import time
import sys

from PyQt4 import QtCore

import serial

import project.project_globals as g
import project.classes as pc


### define ####################################################################


open_coms = {}

creating_com = pc.Busy()


### com class #################################################################


class COM(QtCore.QMutex):
    
    def __init__(self, port, baud_rate, timeout, write_termination='\r\n', data='ASCII', size=-1, **kwargs):
        QtCore.QMutex.__init__(self)
        self.port_index = port
        self.instrument = serial.Serial(port,baud_rate,timeout=timeout, **kwargs)
        self.external_lock_control = False
        self.data = data
        self.write_termination = write_termination
        self.size = size
        g.shutdown.add_method(self.close)

    def _read(self,size=None):
        if self.data == 'pass':
            if size == None:
                size=1
            return self.instrument.read(size)
        elif self.data == 'ASCII':
            buf = b''
            char = self.instrument.read()
            while char != b'':
                buf = buf + char
                if buf.endswith(self.write_termination):
                    buf = buf.rstrip(self.write_termination)
                    break;
                char = self.instrument.read()
            return buf.decode('utf-8')
        else:
            if self.size > 0:
                return [ord(i) for i in self.instrument.read(self.size)]
            else:
                buf = b''
                char = self.instrument.read()
                while char != b'':
                    buf = buf + char
                    char = self.instrument.read()
                return [ord(i) for i in buf]

    def close(self):
        self.instrument.close()

    def open(self):
        self.instrument.open()
        
    def flush(self, then_delay=0.):
        if not self.external_lock_control: self.lock()
        self.instrument.flush()
        if not self.external_lock_control: self.unlock()
        
    def is_open(self):
        return self.instrument.isOpen()
    
    def read(self, size=None):
        if not self.external_lock_control: self.lock()
        value = self._read(size)
        if not self.external_lock_control: self.unlock()
        return value
        
    def write(self, data, then_read=False):
        if not self.external_lock_control:
            self.lock()
        version = int(sys.version[0])
        if self.data == 'pass':
            value = self.instrument.write(data)
        elif self.data == 'ASCII':
            if version == 2:
                data = str(data)  # just making sure
                value = self.instrument.write(data)
                if not data.endswith(self.write_termination):
                    value+=self.instrument.write(self.write_termination)
            else:
                data = bytes(data, 'utf-8')
                value = self.instrument.write(data)
                if not data.endswith(bytes(self.write_termination, 'utf-8')):
                    value+=self.instrument.write(bytes(self.write_termination, 'utf-8'))            
        else:
            value = self.instrument.write(''.join([chr(i) for i in data]))# Python3: bytes(data))
        if then_read:
            value = self._read()
        if not self.external_lock_control: self.unlock()
        return value


### helper methods ############################################################

 
def Serial(port,baud_rate=9600, timeout=1, **kwargs):
    """
    Convience method for pass_through serial communication.
    """
    return get_com(port,baud_rate,timeout*1000,data='pass',**kwargs)

def get_com(port, baud_rate=57600, timeout=1000, **kwargs):
    """
    int port
    
    returns com object
    
    timeout in ms
    """
    # one at a time
    while creating_com.read():
        creating_com.wait_for_update()
    creating_com.write(True)
    # return open com if already open
    if isinstance(port,int):
        port = "COM%d"%port
    out = None
    for key in open_coms.keys():
        if key == port:
            out = open_coms[key]
    # otherwise open new com
    if not out:
        out = COM(port, baud_rate, timeout/1000., **kwargs)
        open_coms[port] = out 
    # finish
    creating_com.write(False)
    return out

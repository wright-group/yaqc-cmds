### import ####################################################################


import os
import ast
import time

import ConfigParser

from PyQt4 import QtCore

import project_globals as g
main_dir = g.main_dir.read()
import classes as pc


### ini class #################################################################


class Ini(QtCore.QMutex):

    def __init__(self, filepath):
        QtCore.QMutex.__init__(self)
        self.filepath = filepath
        self.config = ConfigParser.SafeConfigParser()
        self.return_raw = False
        
    def _do(self, operation, section, option, value, with_apostrophe):
        '''
        put all interaction with ini file itself behind a 'busy' to make
        it a psuedo-Mutex. prevents bizzare race conditions that I don't 
        understand
        
        DO NOT CALL THIS METHOD DIRECTLY!
        '''
        self.lock()
        if operation == 'read':
            self.config.read(self.filepath)
            raw = self.config.get(section, option, raw=False)
            self.unlock()
            raw.replace('\\', '\\\\')
            if self.return_raw:
                return raw
            else:
                return ast.literal_eval(raw)
        elif operation == 'write':
            # ensure value is a string
            value = str(value) 
            if with_apostrophe: 
                value = '\'' + value + '\''
            self.config.read(self.filepath)
            # update
            self.config.set(section, option, value)  
            # save
            with open(self.filepath, 'w') as configfile: 
                self.config.write(configfile)
            self.unlock()

    def read(self, section, option):
        return self._do('read', 
                        section=section, 
                        option=option, 
                        value=None,
                        with_apostrophe=False)

    def write(self, section, option, value, with_apostrophe=False):
        if type(value) in [str] and not self.return_raw:
            with_apostrophe = True 
        self._do('write', 
                 section=section, 
                 option=option, 
                 value=value,
                 with_apostrophe=with_apostrophe)


### shared inis initialized here ##############################################


main = Ini(os.path.join(main_dir, 'main.ini'))
config = Ini(os.path.join(main_dir, 'config.ini'))
daq = Ini(os.path.join(main_dir, 'devices', 'devices.ini'))
delays = Ini(os.path.join(main_dir, 'hardware', 'delays', 'delays.ini'))
opas = Ini(os.path.join(main_dir, 'hardware', 'opas', 'opas.ini'))
filters = Ini(os.path.join(main_dir, 'hardware', 'filters', 'filters.ini'))
spectrometers = Ini(os.path.join(main_dir, 'hardware', 'spectrometers', 'spectrometers.ini'))

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
        
    def _do(self, operation, section, option, value, with_apostrophe):
        '''
        put all interaction with ini file itself behind a 'busy' to make
        it a psuedo-Mutex. prevents bizzare race conditions that I don't 
        understand
        '''
        self.lock()
        if operation == 'read':
            self.config.read(self.filepath)
            raw = self.config.get(section, option, raw=False)
            self.unlock()
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
        self._do('write', 
                 section=section, 
                 option=option, 
                 value=value,
                 with_apostrophe=with_apostrophe)


### shared inis initialized here ##############################################


main = Ini(os.path.join(main_dir, 'project', 'PyCMDS.ini'))
daq = Ini(os.path.join(main_dir, 'daq', 'daq.ini'))
delays = Ini(os.path.join(main_dir, 'delays', 'delays.ini'))
opas = Ini(os.path.join(main_dir, 'opas', 'opas.ini'))
spectrometers = Ini(os.path.join(main_dir, 'spectrometers', 'spectrometers.ini'))
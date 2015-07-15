### import #####################################################################

import os
import ast
import ConfigParser

from PyQt4 import QtCore

import project_globals as g
main_dir = g.main_dir.read()
import classes as pc

### ini class ##################################################################
             
class Ini():
    def __init__(self, filepath):
        self.filepath = filepath
        self.busy = pc.Busy()
        self.busy.write(False)
        self.config = ConfigParser.SafeConfigParser()
    def read(self, section, option):   
        self.config.read(self.filepath)
        return ast.literal_eval(self.config.get(section, option))    
    def write(self, section, option, value, with_apostrophe = False):
        #don't want write to be running in two threads at the same time
        while self.busy.read():
            self.busy.wait_for_update()
        self.busy.write(True)
        #ensure value is a string
        value = str(value) 
        if with_apostrophe: 
            value = '\'' + value + '\''
        self.config.read(self.filepath)
        #update
        self.config.set(section, option, value)  
        #save
        with open(self.filepath, 'w') as configfile: 
            self.config.write(configfile)        
        self.busy.write(False)
        
### shared inis initialized here ###############################################

main = Ini(os.path.join(main_dir, 'project', 'PyCMDS.ini'))
daq = Ini(os.path.join(main_dir, 'daq', 'daq.ini'))
delays = Ini(os.path.join(main_dir, 'delays', 'delays.ini'))
opas = Ini(os.path.join(main_dir, 'opas', 'opas.ini'))
spectrometers = Ini(os.path.join(main_dir, 'spectrometers', 'spectrometers.ini'))
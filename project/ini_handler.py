import os
import ast
import ConfigParser
config = ConfigParser.SafeConfigParser()

import project_globals as g
main_dir = g.main_dir.read()

ini_types = {'main': os.path.join(main_dir, 'project', 'PyCMDS.ini'),
             'daq': os.path.join(main_dir, 'daq', 'daq.ini'),
             'delays': os.path.join(main_dir, 'delays', 'delays.ini'),
             'opas': os.path.join(main_dir, 'opas', 'opas.ini'),
             'spectrometers': os.path.join(main_dir, 'spectrometers', 'spectrometers.ini')}

def read(ini_type, section, option):
    
    if ini_type in ini_types.keys(): ini_filepath = ini_types[ini_type]
    else: ini_filepath = ini_type 
    
    config.read(ini_filepath) 
    return ast.literal_eval(config.get(section, option))

def write(ini_type, section, option, value, with_apostrophe = False):
              
    if ini_type in ini_types.keys(): ini_filepath = ini_types[ini_type]
    else: ini_filepath = ini_type 
    
    value = str(value) #ensure value is a string
    if with_apostrophe: value = '\'' + value + '\''
    
    config.read(ini_filepath)
    config.set(section, option, value)  #update
    with open(ini_filepath, 'w') as configfile: #save
        config.write(configfile)
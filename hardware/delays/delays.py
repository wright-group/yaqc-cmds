### import ####################################################################


import os
import imp
import time
import collections

import WrightTools as wt

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import hardware.hardware as hw


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))
ini = wt.kit.INI(os.path.join(directory, 'delays.ini'))


### driver ####################################################################


class Driver(hw.Driver):
    
    def __init__(self, *args, **kwargs):
        kwargs['native_units'] = 'ps'
        hw.Driver.__init__(self, *args, **kwargs)
        self.position.write(0.)


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'delay'
        hw.Hardware.__init__(self, *arks, **kwargs)


### initialize ################################################################


hardwares = []    
for name in ini.sections:
    if ini.read(name, 'enable'):
        model = ini.read(name, 'model')
        if model == 'Virtual':
            hardware = Hardware(Driver, [None], GUI, name=name, model='Virtual')
        else:
            path = os.path.abspath(ini.read(name, 'path'))
            fname = os.path.basename(path).split('.')[0]
            mod = imp.load_source(fname, path)
            cls = getattr(mod, 'Driver')
            args = ini.read(name, 'initialization arguments')
            gui = getattr(mod, 'GUI')
            hardware = Hardware(cls, args, gui, name=name, model=model)
        hardwares.append(hardware)
gui = pw.HardwareFrontPanel(hardwares, name='Delays')
advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

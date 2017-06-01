### import ####################################################################


import os
import imp
import collections

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
ini = ini.opas
import project.classes as pc
import hardware.hardware as hw


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))


### driver ####################################################################


class Driver(hw.Driver):

    def __init__(self, *args, **kwargs):
        kwargs['native_units'] = 'nm'
        hw.Driver.__init__(self, *args, **kwargs)
        self.position.write(800.)


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'OPA'
        hw.Hardware.__init__(self, *arks, **kwargs)


### initialize ################################################################


ini_path = os.path.join(directory, 'opas.ini')
hardwares, gui, advanced_gui = hw.import_hardwares(ini_path, name='OPAs', Driver=Driver, GUI=GUI, Hardware=Hardware)

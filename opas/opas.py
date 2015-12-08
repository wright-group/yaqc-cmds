### import ####################################################################


import os
import imp
import collections

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
ini = ini.opas
import project.classes as pc


### address ###################################################################


class OPA(pc.Address):

    def dummy(self):
        print 'hello world im a dummy method'


# list module path, module name, class name, initialization arguments, friendly name
hardware_dict = collections.OrderedDict()
hardware_dict['OPA1 micro'] = [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [1], 'w1']
hardware_dict['OPA2 micro'] = [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [2], 'w2']
hardware_dict['OPA3 micro'] = [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [3], 'w3']
hardware_dict['OPA1 TOPAS-C'] = [os.path.join(main_dir, 'OPAs', 'TOPAS-C', 'TOPAS.py'), 'TOPAS', 'OPA', [1], 'w1']
hardware_dict['OPA2 TOPAS-C'] = [os.path.join(main_dir, 'OPAs', 'TOPAS-C', 'TOPAS.py'), 'TOPAS', 'OPA', [2], 'w2']

hardwares = []
for key in hardware_dict.keys():
    if ini.read('hardware', key):
        lis = hardware_dict[key]
        hardware_module = imp.load_source(lis[1], lis[0])
        hardware_class = getattr(hardware_module, lis[2])
        hardware_obj = pc.Hardware(hardware_class, lis[3], OPA, key, True, lis[4])
        hardwares.append(hardware_obj)


### gui #######################################################################


gui = pw.HardwareFrontPanel(hardwares, name='OPAs')
advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

### import ####################################################################


<<<<<<< HEAD
import time
import collections
=======
import os
import imp
>>>>>>> master

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
<<<<<<< HEAD
spectrometers_ini = ini.spectrometers
import project.classes as pc

import copy

=======
ini = ini.opas
import project.classes as pc

>>>>>>> master

### address ###################################################################


class OPA(pc.Address):

    def dummy(self):
        print 'hello world im a dummy method'

<<<<<<< HEAD
hardwares = []
=======

# list module path, module name, class name, initialization arguments
hardware_dict = {'OPA1 micro': [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [1]],
                 'OPA2 micro': [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [2]],
                 'OPA3 micro': [os.path.join(main_dir, 'OPAs', 'pico', 'pico_opa.py'), 'pico_opa', 'OPA', [3]],
                 'OPA1 TOPAS-C': [os.path.join(main_dir, 'OPAs', 'TOPAS', 'TOPAS.py'), 'TOPAS', 'TOPAS', [1]],
                 'OPA2 TOPAS-C': [os.path.join(main_dir, 'OPAs', 'TOPAS', 'TOPAS.py'), 'TOPAS', 'TOPAS', [2]],
                 'OPA1 Virtual': [os.path.join(main_dir, 'OPAs', 'virtual', 'v_pico_opa.py'), 'v_pico_opa', 'vOPA', [1]],
                 'OPA2 Virtual': [os.path.join(main_dir, 'OPAs', 'virtual', 'v_pico_opa.py'), 'v_pico_opa', 'vOPA', [2]],
                 'OPA3 Virtual': [os.path.join(main_dir, 'OPAs', 'virtual', 'v_pico_opa.py'), 'v_pico_opa', 'vOPA', [3]],
                 'OPA1 vTOPAS-C': [os.path.join(main_dir, 'OPAs', 'virtual', 'v_TOPAS.py'), 'v_TOPAS', 'vTOPAS', [1]],
                 'OPA2 vTOPAS-C': [os.path.join(main_dir, 'OPAs', 'virtual', 'v_TOPAS.py'), 'v_TOPAS', 'vTOPAS', [2]]}
hardwares = []
for key in hardware_dict.keys():
    if ini.read('hardware', key):
        lis = hardware_dict[key]
        hardware_module = imp.load_source(lis[1], lis[0])
        hardware_class = getattr(hardware_module, lis[2])
        hardware_obj = pc.Hardware(hardware_class, lis[3], OPA, key, True)
        hardwares.append(hardware_obj)
>>>>>>> master

### gui #######################################################################


gui = pw.HardwareFrontPanel(hardwares, name='OPAs')

advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

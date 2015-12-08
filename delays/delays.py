### import ####################################################################


import os
import imp
import time
import collections

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
ini = ini.delays
import project.classes as pc


### address ###################################################################


class Delay(pc.Address):

    def dummy(self):
        print 'hello world im a dummy method'


# list module path, module name, class name, initialization arguments, simple name
hardware_dict = collections.OrderedDict()
hardware_dict['LTS300'] = [os.path.join(main_dir, 'delays', 'LTS300', 'LTS300.py'), 'LTS300', 'app', [], 'd0']
hardware_dict['D1 micro'] = [os.path.join(main_dir, 'delays', 'pico', 'pico_delay.py'), 'pico_delay', 'Delay', [1], 'd1']
hardware_dict['D2 micro'] = [os.path.join(main_dir, 'delays', 'pico', 'pico_delay.py'), 'pico_delay', 'Delay', [2], 'd2']
hardware_dict['D1 SMC100'] = [os.path.join(main_dir, 'delays', 'SMC100', 'SMC100.py'), 'SMC100', 'SMC100', [1], 'd1']
hardware_dict['D2 SMC100'] = [os.path.join(main_dir, 'delays', 'SMC100', 'SMC100.py'), 'SMC100', 'SMC100', [2], 'd2']

hardwares = []
for key in hardware_dict.keys():
    if ini.read('hardware', key):
        lis = hardware_dict[key]
        hardware_module = imp.load_source(lis[1], lis[0])
        hardware_class = getattr(hardware_module, lis[2])
        hardware_obj = pc.Hardware(hardware_class, lis[3], Delay, key, True, lis[4])
        hardwares.append(hardware_obj)
        time.sleep(1)


### gui #######################################################################


gui = pw.HardwareFrontPanel(hardwares, name='Delays')

advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

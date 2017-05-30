### import ####################################################################


import os
import imp
import time
import collections

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
ini = ini.delays
import hardware.hardware as hw


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


if False:
    # list module path, module name, class name, initialization arguments, simple name
    hardware_dict = collections.OrderedDict()
    hardware_dict['D0 LTS300'] = [os.path.join(main_dir, 'hardware', 'delays', 'LTS300', 'LTS300.py'), 'LTS300', 'app', [], 'd0']
    hardware_dict['D1 micro'] = [os.path.join(main_dir, 'hardware', 'delays', 'pico', 'pico_delay.py'), 'pico_delay', 'Delay', [1], 'd1']
    hardware_dict['D2 micro'] = [os.path.join(main_dir, 'hardware', 'delays', 'pico', 'pico_delay.py'), 'pico_delay', 'Delay', [2], 'd2']
    hardware_dict['D1 SMC100'] = [os.path.join(main_dir, 'hardware', 'delays', 'SMC100', 'SMC100.py'), 'SMC100', 'SMC100', [1], 'd1']
    hardware_dict['D2 SMC100'] = [os.path.join(main_dir, 'hardware', 'delays', 'SMC100', 'SMC100.py'), 'SMC100', 'SMC100', [2], 'd2']
    
    hardwares = []
    for key in hardware_dict.keys():
        if ini.read('hardware', key):
            lis = hardware_dict[key]
            hardware_module = imp.load_source(lis[1], lis[0])
            hardware_class = getattr(hardware_module, lis[2])
            hardware_obj = Hardware(hardware_class, lis[3], Driver, key, True, lis[4])
            hardwares.append(hardware_obj)
            time.sleep(1)
else:
    hardwares = [Hardware(Driver, [None], name='d0', model='Virtual')]
    hardwares += [Hardware(Driver, [None], name='d1', model='Virtual')]
    hardwares += [Hardware(Driver, [None], name='d2', model='Virtual')]

gui = pw.HardwareFrontPanel(hardwares, name='Delays')
advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

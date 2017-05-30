### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
import imp
import collections

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
ini = ini.filters
import project.classes as pc
import hardware.hardware as hw


### driver ####################################################################


class Driver(hw.Driver):
    pass


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    
    def __init__(self, *arks, **kwargs):
        self.kind = 'filter'
        hw.Hardware.__init__(self, *arks, **kwargs)


### initialize ################################################################

if False:
    # list module path, module name, class name, initialization arguments, friendly name
    hardware_dict = collections.OrderedDict()
    hardware_dict['ND0 homebuilt'] = [os.path.join(main_dir, 'hardware', 'filters', 'homebuilt', 'homebuilt.py'), 'homebuilt_NDs', 'Driver', [0], 'nd0']
    hardware_dict['ND1 homebuilt'] = [os.path.join(main_dir, 'hardware', 'filters', 'homebuilt', 'homebuilt.py'), 'homebuilt_NDs', 'Driver', [1], 'nd1']
    hardware_dict['ND2 homebuilt'] = [os.path.join(main_dir, 'hardware', 'filters', 'homebuilt', 'homebuilt.py'), 'homebuilt_NDs', 'Driver', [2], 'nd2']
    
    hardwares = []
    for key in hardware_dict.keys():
        if ini.read('hardware', key):
            lis = hardware_dict[key]
            hardware_module = imp.load_source(lis[1], lis[0])
            hardware_class = getattr(hardware_module, lis[2])
            hardware_obj = Hardware(hardware_class, lis[3], Driver, key, True, lis[4])
            hardwares.append(hardware_obj)
else:
    hardwares = [Hardware(Driver, [None], name='f0', model='Virtual')]
    hardwares += [Hardware(Driver, [None], name='f1', model='Virtual')]
    hardwares += [Hardware(Driver, [None], name='f2', model='Virtual')]

gui = pw.HardwareFrontPanel(hardwares, name='NDs')
advanced_gui = pw.HardwareAdvancedPanel(hardwares, gui.advanced_button)

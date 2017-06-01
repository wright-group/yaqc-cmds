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


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))


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


### import ####################################################################


ini_path = os.path.join(directory, 'filters.ini')
hardwares, gui, advanced_gui = hw.import_hardwares(ini_path, name='Filters', Driver=Driver, GUI=GUI, Hardware=Hardware)

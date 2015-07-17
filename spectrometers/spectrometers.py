### import ####################################################################


import time
import collections

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.widgets as pw
import project.ini_handler as ini
spectrometers_ini = ini.spectrometers
import project.classes as pc

import copy


### address ###################################################################


class Monochromator(pc.Address):

    def dummy(self):
        print 'hello world im a dummy method'

import MicroHR
MicroHR_class = MicroHR.MicroHR.MicroHR

hardware = pc.Hardware(MicroHR_class, [], Monochromator, 'MicroHR', True)
hardwares = [hardware]


### gui #######################################################################

gui = pw.HardwareFrontPanel(hardwares, name='Spectrometers')

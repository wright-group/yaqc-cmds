### import ####################################################################


import time
import collections

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read() # What is this used for? Why redudantly defined?
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


class Gui(QtCore.QObject): # different from gui?

    def __init__(self):
        QtCore.QObject.__init__(self)
        # link hardware object signals
        for hardware in hardwares:
            hardware.update_ui.connect(self.update)
        # create gui
        self.create_frame()
        
    def create_frame(self):   
        
        layout_widget = pw.HardwareLayoutWidget('Spectrometers', hardwares[0].update_ui)
        layout = layout_widget.layout()

        input_table = pw.InputTable(125)
        input_table.add('MicroHR', hardwares[0].busy)
        input_table.add('Color', hardwares[0].exposed[0])
        input_table.add('Grating', hardwares[0].exposed[1])
        self.destination_color = pc.attach_object(hardwares[0].exposed[0], False)
        destination_grating = pc.Number()
        input_table.add('Destination Color', self.destination_color)
        input_table.add('Destination Grating', destination_grating)        
        layout.addWidget(input_table)

        layout_widget.add_buttons(self.on_set, self.show_advanced, hardwares)
        
        g.hardware_widget.add_to(layout_widget)
    
    def update(self):
        pass
        
    def on_set(self):
        # placeholder
        hardwares[0].set_position(self.destination_color.read(),
                                  self.destination_color.units)

    def show_advanced(self):
        pass

    def stop(self):
        pass

gui = Gui()

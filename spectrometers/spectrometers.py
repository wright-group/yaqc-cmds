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


### address ###################################################################


class Monochromator(pc.Address):

    def dummy(self):
        print 'hello world im a dummy method'

import MicroHR
MicroHR_class = MicroHR.MicroHR.MicroHR

hardware = pc.Hardware(MicroHR_class, [], Monochromator, 'MicroHR', True)
hardwares = [hardware]


### gui #######################################################################


class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        # link hardware object signals
        for hardware in hardwares:
            hardware.update_ui.connect(self.update)
        # create gui
        self.create_frame()
        
    def create_frame(self):
        
        busy = pc.Busy()        
        
        layout_widget = pw.hardware_layout_widget('Monochromator', busy, hardwares[0].update_ui)
        layout = layout_widget.layout()

        input_table = pw.input_table(125)
        input_table.add('MicroHR', None)
        input_table.add('Color', hardwares[0].current_position)
        layout.addWidget(input_table)

        layout_widget.add_buttons(self.on_set, self.show_advanced)
        
        g.hardware_widget.add_to(layout_widget)
    
    def update(self):
        pass
        
    def on_set(self):
        # placeholder
        hardwares[0].set_position(1400)

    def show_advanced(self):
        pass

    def stop(self):
        pass

gui = gui()

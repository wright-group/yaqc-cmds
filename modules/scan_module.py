### define ####################################################################


module_name = 'SCAN'


### import ####################################################################


import sys
import time
import numexpr as ne

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

from PyQt4 import QtCore, QtGui
import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import modules.scan as scan
app = g.app.read()


### import hardware control ###################################################


import spectrometers.spectrometers as specs
import delays.delays as delays
import opas.opas as opas

 
### gui #######################################################################


class GUI(scan.GUI):

    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)
        
    def launch_scan(self):
        pass
        
    def on_done(self):
        pass
        
gui = GUI(module_name)

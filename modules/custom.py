#to do##########################################################################

#import#########################################################################

import sys

import numpy as np

import project.project_globals as g

from PyQt4 import QtCore, QtGui
app = g.app.read()
 
#gui############################################################################

class gui_panel(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()
        g.shutdown.read().connect(self.stop)
        
    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        
        how_to = QtGui.QLabel('this module not yet complete')
        layout.addWidget(how_to)
        
        self.filepath_textbox = QtGui.QLineEdit()
        self.filepath_textbox.setText('add_new filepath')
        layout.addWidget(self.filepath_textbox)
        
        layout.addStretch(1)
        
        self.frame = QtGui.QWidget()   
        self.frame.setLayout(layout)

        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module('CUSTOM', self.show_frame)
        self.show_frame() #check once at startup

    def show_frame(self):
        self.frame.hide()
        if g.module_combobox.get_text() == 'CUSTOM':
            self.frame.show()
            

    def stop(self):
        pass
        
gui_panel = gui_panel()
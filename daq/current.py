### import ####################################################################


import numpy as np

from PyQt4 import QtCore, QtGui

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import project.ini_handler as ini
app = g.app.read()
main_dir = g.main_dir.read()
daq_ini = ini.daq

if not g.offline.read(): 
    from PyDAQmx import *
    
import daq

### objects ###################################################################

tab_channel = pc.Combo(['vai0', 'vai1', 'vai2', 'vai3', 'vai4'], ini=daq_ini, section='DAQ', option='Tab channel', import_from_ini = True)
tab_property = pc.Combo(['Mean', 'Variance', 'Differential'], ini=daq_ini, section='DAQ', option='Tab property', import_from_ini = True)

### gui #######################################################################


class Gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()
        daq.address_obj.update_ui.connect(lambda: self.update(True))
        tab_channel.updated.connect(self.update)
        tab_property.updated.connect(self.update)
        self.xi = []
        self.yi = []
        
    def create_frame(self):
        # get parent widget
        parent_widget = g.current_slice_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        layout = parent_widget.layout()
        
        # plot ----------------------------------------------------------------        
        
        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_curve = self.plot_widget.add_line()
        self.plot_widget.set_labels(ylabel = 'volts')
        self.plot_green_line = self.plot_widget.add_line(color = 'g')   
        self.plot_red_line = self.plot_widget.add_line(color = 'r')   
        display_layout.addWidget(self.plot_widget)
        
        # vertical line
        line = pw.line('V')      
        layout.addWidget(line)
        
        # settings container --------------------------------------------------
        
        # container widget / scroll area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        
        # input table one
        input_table = pw.InputTable()
        input_table.add('Display', None)
        input_table.add('Channel', tab_channel)
        input_table.add('Property', tab_property)
        settings_layout.addWidget(input_table)
        
        # streach
        settings_layout.addStretch(1)
        
    def update(self, check_for_control=False):
        if check_for_control:
            if not g.module_control.read():
                return
        vals = np.array(daq.current_slice.read())
        xcol = daq.data_cols.read()[daq.current_slice.col]['index']
        ycol_key = tab_channel.read() + '_' + tab_property.read()
        ycol = daq.data_cols.read()[ycol_key]['index']
        self.xi = vals[:, xcol]
        self.yi = vals[:, ycol]
        self.plot()
        
    def plot(self):
        self.plot_curve.clear()
        self.plot_curve.setData(self.xi, self.yi)
        
    def set_xlim(self, xmin, xmax):
        self.plot_widget.set_xlim(xmin, xmax)
        
    def set_ylim(self, ymin, ymax):
        self.plot_widget.set_ylim(ymin, ymax)

    def stop(self):
        pass
        
gui = Gui()

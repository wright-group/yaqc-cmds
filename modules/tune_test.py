### define ####################################################################


module_name = 'TUNE TEST'


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
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed, disable_under_module_control=True)
        # mono
        self.mono_width = pc.Number(initial_value=500, units='wn', disable_under_module_control=True)
        self.mono_width.set_disabled_units(True)
        self.mono_npts = pc.Number(initial_value=51, decimals=0, disable_under_module_control=True)
        # input table
        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        input_table.add('Spectrometer', None)
        input_table.add('Width', self.mono_width)
        input_table.add('Number', self.mono_npts)
        layout.addWidget(input_table)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def launch_scan(self):
        axes = []
        # get OPA properties
        opa_index = self.opa_combo.read_index()
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune point axis
        axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, opa_friendly_name)
        axes.append(axis)
        # mono axis
        name = 'wm'
        identity = 'DwmF' + opa_friendly_name
        kwargs = {'centers': curve.colors,
                  'centers_units': curve.units,
                  'centers_follow': opa_friendly_name}
        width = self.mono_width.read()/2.
        npts = self.mono_npts.read()
        points = np.linspace(-width, width, npts)
        hardware = specs.hardwares[0]
        axis = scan.Axis(points, 'wn', name, identity, **kwargs)
        axes.append(axis)
        # launch
        self.scan.launch(axes) 

gui = GUI(module_name)

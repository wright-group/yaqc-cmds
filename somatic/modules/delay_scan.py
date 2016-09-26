### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
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
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.delays.delays as delays

 
### define ####################################################################


module_name = 'DELAY SCAN'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def run(self):
        # assemble axes
        axes = []
        width = self.aqn.read('delay', 'width') 
        npts = int(self.aqn.read('delay', 'number'))
        points = np.linspace(-width/2., width/2., npts)
        units = 'ps'        
        axis = acquisition.Axis(points=points, units=units, name='d0', identity='d0')
        axes.append(axis)
        # do scan
        self.scan(axes)
        self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        input_table.add('Delay', None)
        self.width = pc.Number(initial_value=10., units='ps')
        input_table.add('Width', self.width)
        self.npts = pc.Number(initial_value=51, decimals=0)
        input_table.add('Number', self.npts)
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        self.width.write(ini.read('delay', 'width'))
        self.npts.write(ini.read('delay', 'number'))
        self.device_widget.load(aqn_path)
        
    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section('delay')
        ini.write('delay', 'width', self.width.read())
        ini.write('delay', 'number', self.npts.read())
        ini.write('info', 'description', 'module description text')
        self.device_widget.save(aqn_path)
        
gui = GUI(module_name)

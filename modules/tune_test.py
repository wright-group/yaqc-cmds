### define ####################################################################


module_name = 'TUNE TEST'


### import ####################################################################


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
import modules.scan as scan
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'modules', 'tune_test.ini'))
app = g.app.read()


### import hardware control ###################################################


import spectrometers.spectrometers as specs
import opas.opas as opas
import daq.daq as daq

 
### gui #######################################################################


class GUI(scan.GUI):

    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed, disable_under_module_control=True)
        # mono
        self.mono_width = pc.Number(ini=ini, units='wn', disable_under_module_control=True,
                                    section='main', option='mono width (wn)',
                                    import_from_ini=True, save_to_ini_at_shutdown=True)
        self.mono_width.set_disabled_units(True)
        self.mono_npts = pc.Number(initial_value=51, decimals=0, disable_under_module_control=True)
        # input table
        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        input_table.add('Spectrometer', None)
        input_table.add('Width', self.mono_width)
        input_table.add('Number', self.mono_npts)
        self.channel_choice_combo = pc.Combo(ini=ini, section='main',
                                             option='channel name',
                                             import_from_ini=True,
                                             save_to_ini_at_shutdown=True,
                                             disable_under_module_control=True)
        input_table.add('Processing', None)
        input_table.add('Channel', self.channel_choice_combo)
        layout.addWidget(input_table)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)
        daq.daq.task_changed.connect(self.on_daq_task_changed)
        self.on_daq_task_changed()

    def launch_scan(self):
        axes = []
        # get OPA properties
        opa_index = self.opa_combo.read_index()
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.friendly_name
        curve = opa_hardware.address.ctrl.curve.copy()
        curve.convert('wn')
        # tune point axis
        axis = scan.Axis(curve.colors, 'wn', opa_friendly_name, opa_friendly_name)
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
        
    def on_daq_task_changed(self):
        allowed_values = daq.value_channel_combo.allowed_values
        self.channel_choice_combo.set_allowed_values(allowed_values)
        
    def on_done(self):
        '''
        Make pickle and figures.
        '''
        # get path
        data_path = daq.data_path.read() 
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        data.save(data_path.replace('.data', '.p'), verbose=False)
        # make image
        data_folder, file_name, file_extension = wt.kit.filename_parse(data_path)
        channel_name = self.channel_choice_combo.read()
        data.transpose()
        artist = wt.artists.mpl_2D(data)
        artist.plot(channel_name, autosave=True, output_folder=data_folder, fname=file_name)
        output_image_path = wt.kit.glob_handler('.png', folder=data_folder)[0]
        # send message on slack
        if g.slack_enabled.read():
            slack = g.slack_control.read()
            slack.send_message('scan complete - {} elapsed'.format(g.progress_bar.time_elapsed.text()))
            if len(data.shape) < 3:
                print output_image_path
                slack.upload_file(output_image_path)

gui = GUI(module_name)

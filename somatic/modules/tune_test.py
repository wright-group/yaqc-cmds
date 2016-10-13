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

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'TUNE TEST'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        data_path = wt.kit.glob_handler('.data', folder=scan_folder)[0]
        data = wt.data.from_PyCMDS(data_path)
        data.transpose()
        data.bring_to_front(self.aqn.read('processing', 'channel'))
        # make tuning curve, if user desires
        if self.aqn.read('processing', 'make new curve'):
            # TODO:
            print('make new curve not yet implemented')
        # plot
        artist = wt.artists.mpl_2D(data)
        function = wt.fit.Moments()
        fitter = wt.fit.Fitter(function, data, 'wm')
        outs = fitter.run()
        xi = outs.w1.points
        yi = outs.one.values
        artist.onplot(xi, yi)
        output_image_path = artist.plot(autosave=True, output_folder=scan_folder)[0]
        # upload
        self.upload(scan_folder, reference_image=output_image_path)
    
    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.friendly_name
        opa_friendly_name = opa_hardware.friendly_name
        curve = opa_hardware.address.ctrl.curve.copy()
        curve.convert('wn')
        axis = acquisition.Axis(curve.colors, 'wn', opa_friendly_name, opa_friendly_name)
        axes.append(axis)
        # mono
        name = 'wm'
        identity = 'Dwm'
        kwargs = {'centers': curve.colors}
        width = self.aqn.read('spectrometer', 'width')/2.
        npts = self.aqn.read('spectrometer', 'number')
        points = np.linspace(-width, width, npts)
        axis = acquisition.Axis(points, 'wn', name, identity, **kwargs)
        axes.append(axis)
        # do scan
        self.scan(axes)
        # finish
        if self.go:
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add('OPA', None)
        input_table.add('OPA', self.opa_combo)
        # mono
        input_table.add('Spectrometer', None)
        self.mono_width = pc.Number(ini=ini, units='wn',
                                    section='main', option='mono width (wn)',
                                    import_from_ini=True, save_to_ini_at_shutdown=True)
        self.mono_width.set_disabled_units(True)
        input_table.add('Width', self.mono_width)
        self.mono_npts = pc.Number(initial_value=51, decimals=0)
        input_table.add('Number', self.mono_npts)
        # processing
        input_table.add('Processing', None)
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names, ini=ini, section='main', option='channel name')
        input_table.add('Channel', self.channel_combo)
        self.make_new_curve = pc.Bool()
        input_table.add('Make New Curve', self.make_new_curve)
        # finish
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        self.mono_width.write(aqn.read('spectrometer', 'width'))
        self.mono_npts.wriite(aqn.read('spectrometer', 'number'))
        self.channel_combo.write(aqn.read('processing', 'channel'))
        self.make_new_curve.write(aqn.read('processing', 'make new curve'))
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', '{} tune test'.format(self.opa_combo.read()))
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())
        aqn.add_section('spectrometer')
        aqn.write('spectrometer', 'width', self.mono_width.read())
        aqn.write('spectrometer', 'number', self.mono_npts.read())
        aqn.add_section('processing')
        aqn.write('processing', 'channel', self.channel_combo.read())
        aqn.write('processing', 'make new curve', self.make_new_curve.read())
        # allow devices to write settings
        print(self.device_widget)
        self.device_widget.save(aqn_path)
        
gui = GUI(module_name)

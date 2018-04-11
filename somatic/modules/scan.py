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
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'scan.ini'))
app = g.app.read()

import hardware.spectrometers.spectrometers as spectrometers
import hardware.delays.delays as delays
import hardware.opas.opas as opas
import hardware.filters.filters as filters
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares
import devices.devices as devices

 
### define ####################################################################


module_name = 'SCAN'


### custom classes ############################################################


class Axis():
    
    def __init__(self, units_kind, axis_index):
        print(filters.hardwares)
        self.units_kind = units_kind
        if self.units_kind == 'energy':
            self.units = 'wn'
            initial_start = 1500
            initial_stop = 1200
        elif self.units_kind == 'delay':
            self.units = 'ps'
            initial_start = -1
            initial_stop = 1
        elif self.units_kind == 'angle':
            self.units = 'deg'
            initial_start = 0.
            initial_stop = 360.
        self.widget = pw.InputTable()
        self.widget.add(str(axis_index) + ' (' + self.units_kind + ')', None)
        # start
        self.start = pc.Number(initial_value=initial_start, units=self.units)
        self.start.set_disabled_units(True)
        self.widget.add('Initial', self.start)
        # stop
        self.stop = pc.Number(initial_value=initial_stop, units=self.units)
        self.stop.set_disabled_units(True)
        self.widget.add('Final', self.stop)
        # number
        self.number = pc.Number(initial_value=51, decimals=0)
        self.widget.add('Number', self.number)
        # hardwares
        if self.units_kind == 'energy':
            hardware_objs = opas.hardwares + spectrometers.hardwares
        elif self.units_kind == 'delay':
            hardware_objs = delays.hardwares
        elif self.units_kind == 'angle':
            hardware_objs = filters.hardwares
        self.hardwares = {}
        for hw in hardware_objs:
            checkbox = pc.Bool()
            self.widget.add(hw.name, checkbox)
            self.hardwares[hw.name] = checkbox
    
    def get_name(self):
        return '='.join([key for key in self.hardwares if self.hardwares[key].read()])  
    
    def hide(self):
        self.widget.hide()
        
        
class Constant():
    
    def __init__(self):
        self.widget = pw.InputTable()
        self.widget.add('Constant', None)
        # hardware name
        allowed_values = [h.name for h in all_hardwares]
        self.hardware_name_combo = pc.Combo(allowed_values=allowed_values)
        self.hardware_name_combo.write(spectrometers.hardwares[0].name)
        #self.hardware_name_combo.set_disabled(True)
        self.widget.add('Hardware', self.hardware_name_combo)
        # expression
        opanames = [h.name for h in opas.hardwares]
        self.expression = pc.String(initial_value="+".join(opanames))
        self.widget.add('Expression', self.expression)

    def get_name(self):
        return self.hardware_name_combo.read()     
        
    def hide(self):
        self.widget.hide()


### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        # get path
        data_path = devices.data_path.read() 
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        # decide which channels to make plots for
        if self.aqn.read('processing', 'process all channels'):
            channels = data.channel_names
        else:
            channels = [self.aqn.read('processing', 'main channel')]
        # chop data if over 2D
        if len(data.shape) > 2:
            chopped_datas = data.chop(0, 1, verbose=False)
        # make figures for each channel
        data_folder, file_name, file_extension = wt.kit.filename_parse(data_path)
        # make all images
        for channel_name in channels:
            channel_index = data.channel_names.index(channel_name)
            image_fname = channel_name
            if len(data.shape) == 1:
                artist = wt.artists.mpl_1D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            elif len(data.shape) == 2:
                artist = wt.artists.mpl_2D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            else:
                channel_folder = os.path.join(data_folder, channel_name)
                os.mkdir(channel_folder)
                for index, chopped_data in enumerate(chopped_datas):
                    this_image_fname = image_fname + ' ' + str(index).zfill(3)
                    artist = wt.artists.mpl_2D(chopped_data, verbose=False)
                    artist.plot(channel_index, autosave=True, output_folder=channel_folder,
                                fname=this_image_fname, verbose=False)
        # get output image
        main_channel = self.aqn.read('processing', 'main channel')
        if len(data.shape) <= 2:
            output_image_path = os.path.join(scan_folder, main_channel + ' 000.png')
        else:
            output_folder = os.path.join(data_folder, main_channel)
            output_image_path = os.path.join(output_folder, 'animation.gif')
            images = wt.kit.glob_handler('.png', folder=output_folder)
            wt.artists.stitch_to_animation(images=images, outpath=output_image_path)
        # upload
        self.upload(scan_folder, reference_image=output_image_path)
    
    def run(self):
        # axes
        axes = []
        for axis_name in self.aqn.read('scan', 'axis names'):
            start = self.aqn.read(axis_name, 'start')
            stop = self.aqn.read(axis_name, 'stop')
            number = self.aqn.read(axis_name, 'number')
            points = np.linspace(start, stop, number)
            units = self.aqn.read(axis_name, 'units')
            axis = acquisition.Axis(points, units, axis_name, axis_name)
            axes.append(axis)
        # constants
        constants = []
        for constant_name in self.aqn.read('scan', 'constant names'):
            units = 'wn'  # TODO: this is a hack, remove it
            name = constant_name
            identity = expression = self.aqn.read(constant_name, 'expression')
            constant = acquisition.Constant(units, name, identity, expression=expression, static=False)
            constants.append(constant)
        # do scan
        self.scan(axes, constants)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def add_axis(self, units_kind):
        axis = Axis(units_kind, len(self.axes))
        self.axes_container_widget.layout().addWidget(axis.widget)
        self.axes.append(axis)

    def add_buttons(self):
        colors = g.colors_dict.read()
        # layout
        button_container = QtGui.QWidget()
        button_container.setLayout(QtGui.QHBoxLayout())
        button_container.layout().setMargin(0)
        # remove
        remove_button = QtGui.QPushButton()
        remove_button.setText('REMOVE')
        remove_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['stop'])
        remove_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(remove_button)
        # add
        add_button = QtGui.QPushButton()
        add_button.setText('ADD')
        add_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['set'])
        add_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(add_button)
        # finish
        self.layout.addWidget(button_container)
        return [add_button, remove_button]

    def add_constant(self):
        #if len(self.constants) == 1: return  # temporary...
        constant = Constant()
        self.constants_container_widget.layout().addWidget(constant.widget)
        self.constants.append(constant)

    def create_frame(self):
        # axes
        self.axes = []
        input_table = pw.InputTable()
        input_table.add('Axes', None)
        self.layout.addWidget(input_table)
        self.axes_container_widget = QtGui.QWidget()
        self.axes_container_widget.setLayout(QtGui.QVBoxLayout())
        self.axes_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.axes_container_widget)
        add_energy_axis_button = pw.SetButton('ADD ENERGY AXIS')
        add_energy_axis_button.clicked.connect(lambda: self.add_axis('energy'))
        self.layout.addWidget(add_energy_axis_button)
        add_delay_axis_button = pw.SetButton('ADD DELAY AXIS')
        add_delay_axis_button.clicked.connect(lambda: self.add_axis('delay'))
        self.layout.addWidget(add_delay_axis_button)
        add_delay_axis_button = pw.SetButton('ADD ANGLE AXIS')
        add_delay_axis_button.clicked.connect(lambda: self.add_axis('angle'))
        self.layout.addWidget(add_delay_axis_button)
        remove_axis_button = pw.SetButton('REMOVE AXIS', 'stop')
        remove_axis_button.clicked.connect(self.remove_axis)
        self.layout.addWidget(remove_axis_button)
        # constants
        self.constants = []
        input_table = pw.InputTable()
        input_table.add('Constants', None)
        self.layout.addWidget(input_table)
        self.constants_container_widget = QtGui.QWidget()
        self.constants_container_widget.setLayout(QtGui.QVBoxLayout())
        self.constants_container_widget.layout().setMargin(0)
        self.layout.addWidget(self.constants_container_widget)
        add_constant_button, remove_constant_button = self.add_buttons()
        add_constant_button.clicked.connect(self.add_constant)
        remove_constant_button.clicked.connect(self.remove_constant)
        # processing
        input_table = pw.InputTable()
        input_table.add('Processing', None)
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names, ini=ini, section='main', option='main channel')
        input_table.add('Main Channel', self.channel_combo)
        self.process_all_channels = pc.Bool(ini=ini, section='main', option='process all channels')
        input_table.add('Process All Channels', self.process_all_channels)
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        # clear old
        for axis in self.axes:
            axis.hide()
        for constant in self.constants:
            constant.hide()
        self.axes = []
        self.channels = []
        self.constants = []
        # read new
        aqn = wt.kit.INI(aqn_path)
        # axes
        axis_names = aqn.read('scan', 'axis names')
        for axis_index, axis_name in enumerate(axis_names):
            units = aqn.read(axis_name, 'units')
            units_kind = None
            for d in wt.units.unit_dicts:
                if units in d.keys():
                    units_kind = d['kind']
            axis = Axis(units_kind, axis_index)
            axis.start.write(aqn.read(axis_name, 'start'))
            axis.stop.write(aqn.read(axis_name, 'stop'))
            axis.number.write(aqn.read(axis_name, 'number'))
            hardwares = aqn.read(axis_name, 'hardware')
            for hardware in hardwares:
                axis.hardwares[hardware].write(True)
            self.axes.append(axis)
            self.axes_container_widget.layout().addWidget(axis.widget)
        # constants
        constant_names = aqn.read('scan', 'constant names')
        for constant_index, constant_name in enumerate(constant_names):
            constant = Constant()
            constant.hardware_name_combo.write(aqn.read(constant_name, 'hardware'))
            constant.expression.write(aqn.read(constant_name, 'expression'))
            self.constants.append(constant)
            self.constants_container_widget.layout().addWidget(constant.widget)
        # processing
        try:
            self.channel_combo.write(aqn.read('processing', 'main channel'))
        except ValueError:
            pass  # TODO: log warning or something
        self.process_all_channels.write(aqn.read('processing', 'process all channels'))     
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)

    def remove_axis(self):
        # remove trailing axis
        if len(self.axes) > 0:
            axis = self.axes[-1]
            self.axes_container_widget.layout().removeWidget(axis.widget)
            axis.hide()
            self.axes.pop(-1)

    def remove_constant(self):
        # remove trailing constant
        if len(self.constants) > 0:
            constant = self.constants[-1]
            self.constants_container_widget.layout().removeWidget(constant.widget)
            constant.hide()
            self.constants.pop(-1)

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        # general
        axis_names = str([str(a.get_name()) for a in self.axes]).replace('\'', '')
        aqn.write('info', 'description', 'SCAN: {}'.format(axis_names))
        aqn.add_section('scan')
        aqn.write('scan', 'axis names', [a.get_name() for a in self.axes])
        aqn.write('scan', 'constant names', [c.get_name() for c in self.constants])
        # axes
        for axis in self.axes:
            name = axis.get_name()
            aqn.add_section(name)
            aqn.write(name, 'start', axis.start.read())
            aqn.write(name, 'stop', axis.stop.read())
            aqn.write(name, 'number', axis.number.read())
            aqn.write(name, 'units', axis.units)
            hardwares = []
            for key, bool_mutex in axis.hardwares.items():
                if bool_mutex.read():
                    hardwares.append(key)
            aqn.write(name, 'hardware', hardwares)
        # constants
        for constant in self.constants:
            name = constant.get_name()
            aqn.add_section(name)
            aqn.write(name, 'hardware', constant.hardware_name_combo.read())
            aqn.write(name, 'expression', constant.expression.read())
        # processing
        aqn.add_section('processing')
        aqn.write('processing', 'main channel', self.channel_combo.read())
        aqn.write('processing', 'process all channels', self.process_all_channels.read())
        # allow devices to write settings
        self.device_widget.save(aqn_path)
        
def load():
    return True
def mkGUI():        
    global gui
    gui = GUI(module_name)

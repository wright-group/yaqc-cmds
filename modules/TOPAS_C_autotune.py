### define ####################################################################


module_name = 'TOPAS-C AUTOTUNE'


### import ####################################################################


import os
import sys
import time
import collections
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
ini = ini_handler.Ini(os.path.join(main_dir, 'modules', 'TOPAS_C_autotune.ini'))
app = g.app.read()


### import hardware control ###################################################


import spectrometers.spectrometers as spectrometers
import opas.opas as opas
import daq.daq as daq


### procedure classes #########################################################


class Procedure:
    
    def hide(self):
        self.input_table.hide()
        
    def show(self):
        self.input_table.show()
        

class Preamp(Procedure):
    
    def __init__(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Procedure', None)
        self.width = pc.Number(ini=ini, section='preamp', option='width', save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('D1 Width', self.width)        
        self.number = pc.Number(ini=ini, section='preamp', option='number', decimals=0, save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('Number', self.number)
        
    def assemble_axes(self, opa_index):
        axes = []
        # get OPA properties
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opas.hardwares[opa_index].friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune points        
        motors_excepted = [1]  # list of indicies
        identity = opa_friendly_name + '=wm'
        hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]],
                         'wm': [spectrometers.hardwares[0], 'set_position', None]}
        axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, identity, hardware_dict)
        axes.append(axis)
        # motor points
        motor_units = None
        name = '_'.join([opa_friendly_name, 'Delay_1'])
        width = self.width.read()/2.
        npts = self.number.read()
        center = 0.
        identity = 'D'+name
        curve_motor_index = curve.get_motor_names(full=False).index('Delay_1')
        motor_positions = curve.motors[curve_motor_index].positions
        kwargs = {'centers': motor_positions, 
                  'centers_units': motor_units,
                  'centers_follow': opa_friendly_name}
        points = np.linspace(center-width, center+width, npts)
        hardware_dict = {name: [opa_hardware, 'set_motor', ['Delay_1', 'destination']]}
        axis = scan.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
        axes.append(axis)
        # fnish
        return axes
    
    def process(self, OPA_index, data_filepath, old_crvs):
        wt.tuning.TOPAS_C.process_preamp_motortune(OPA_index, data_filepath, old_crvs)
        # TODO: return output image path
        
        
class PowerampD2(Procedure):
    
    def __init__(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Procedure', None)
        self.width = pc.Number(ini=ini, section='poweramp d2', option='width', save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('D2 Width', self.width)        
        self.number = pc.Number(ini=ini, section='poweramp d2', option='number', decimals=0, save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('Number', self.number)
        
    def assemble_axes(self, opa_index):
        axes = []
        # get OPA properties
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opas.hardwares[opa_index].friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune points        
        motors_excepted = [3]  # list of indicies
        identity = opa_friendly_name + '=wm'
        hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]],
                         'wm': [spectrometers.hardwares[0], 'set_position', None]}
        axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, identity, hardware_dict)
        axes.append(axis)
        # motor points
        motor_units = None
        name = '_'.join([opa_friendly_name, 'Delay_2'])
        width = self.width.read()/2.
        npts = self.number.read()
        center = 0.
        identity = 'D'+name
        curve_motor_index = curve.get_motor_names(full=False).index('Delay_2')
        motor_positions = curve.motors[curve_motor_index].positions
        kwargs = {'centers': motor_positions, 
                  'centers_units': motor_units,
                  'centers_follow': opa_friendly_name}
        points = np.linspace(center-width, center+width, npts)
        hardware_dict = {name: [opa_hardware, 'set_motor', ['Delay_2', 'destination']]}
        axis = scan.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
        axes.append(axis)
        # fnish
        return axes
    
    def process(self, OPA_index, data_filepath, old_crvs):
        wt.tuning.TOPAS_C.process_D2_motortune(OPA_index, data_filepath, old_crvs)
        # TODO: return output image path
        
        
class PowerampC2(Procedure):
    
    def __init__(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Procedure', None)
        self.width = pc.Number(ini=ini, section='poweramp c2', option='width', save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('C2 Width', self.width)        
        self.number = pc.Number(ini=ini, section='poweramp c2', option='number', decimals=0, save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('Number', self.number)
        
    def assemble_axes(self, opa_index):
        axes = []
        # get OPA properties
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opas.hardwares[opa_index].friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune points        
        motors_excepted = [2]  # list of indicies
        identity = opa_friendly_name + '=wm'
        hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]],
                         'wm': [spectrometers.hardwares[0], 'set_position', None]}
        axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, identity, hardware_dict)
        axes.append(axis)
        # motor points
        motor_units = None
        name = '_'.join([opa_friendly_name, 'Crystal_2'])
        width = self.width.read()/2.
        npts = self.number.read()
        center = 0.
        identity = 'D'+name
        curve_motor_index = curve.get_motor_names(full=False).index('Crystal_2')
        motor_positions = curve.motors[curve_motor_index].positions
        kwargs = {'centers': motor_positions, 
                  'centers_units': motor_units,
                  'centers_follow': opa_friendly_name}
        points = np.linspace(center-width, center+width, npts)
        hardware_dict = {name: [opa_hardware, 'set_motor', ['Crystal_2', 'destination']]}
        axis = scan.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
        axes.append(axis)
        # fnish
        return axes
    
    def process(self, OPA_index, data_filepath, old_crvs):
        wt.tuning.TOPAS_C.process_C2_motortune(OPA_index, data_filepath, old_crvs)
        # TODO: return output image path
        

class SHS(Procedure):
    
    def __init__(self):
        self.input_table = pw.InputTable()
        self.input_table.add('Procedure', None)
        self.width = pc.Number(ini=ini, section='shs', option='width', save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('M2 Width', self.width)        
        self.number = pc.Number(ini=ini, section='shs', option='number', decimals=0, save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('M2 Number', self.number)
        self.mono_width = pc.Number(ini=ini, section='shs', option='mono width', save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('Mono. Width', self.mono_width)
        self.mono_number = pc.Number(ini=ini, section='shs', option='mono number', decimals=0, save_to_ini_at_shutdown=False, disable_under_module_control=True)
        self.input_table.add('Mono. Number', self.mono_number)
        
    def assemble_axes(self, opa_index):
        axes = []
        # get OPA properties
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opas.hardwares[opa_index].friendly_name
        curve = opa_hardware.address.ctrl.curve
        # tune points        
        motors_excepted = [5]  # list of indicies
        identity = opa_friendly_name
        hardware_dict = {opa_friendly_name: [opa_hardware, 'set_position_except', ['destination', motors_excepted]]}
        axis = scan.Axis(curve.colors, curve.units, opa_friendly_name, identity, hardware_dict)
        axes.append(axis)
        # motor points
        motor_units = None
        name = '_'.join([opa_friendly_name, 'Mixer_2'])
        width = self.width.read()/2.
        npts = self.number.read()
        identity = 'D'+name
        curve_motor_index = curve.get_motor_names(full=False).index('Mixer_2')
        motor_positions = curve.motors[curve_motor_index].positions
        kwargs = {'centers': motor_positions, 
                  'centers_units': motor_units,
                  'centers_follow': opa_friendly_name}
        points = np.linspace(-width, width, npts)
        hardware_dict = {name: [opa_hardware, 'set_motor', ['Mixer_2', 'destination']]}
        axis = scan.Axis(points, motor_units, name, identity, hardware_dict, **kwargs)
        axes.append(axis)
        # monochromator points
        name = 'wm'
        identity = 'Dwm'
        points = np.linspace(-self.mono_width.read()/2., self.mono_width.read()/2., self.mono_number.read())
        centers = wt.units.converter(curve.colors, 'nm', 'wn')
        kwargs = {'centers': centers,
                  'centers_units': 'wn',
                  'centers_follow': opa_friendly_name}
        axis = scan.Axis(points, 'wn', name, identity, **kwargs)
        axes.append(axis)
        # fnish
        return axes
    
    def process(self, OPA_index, data_filepath, old_crvs):
        wt.tuning.TOPAS_C.process_SHS_motortune(OPA_index, data_filepath, old_crvs)
        # TODO: return output image path
        
 
### gui #######################################################################


class GUI(scan.GUI):

    def create_frame(self):
        # compile procedure dictionary
        self.procedures = collections.OrderedDict()
        self.procedures['preamp'] = Preamp()
        self.procedures['poweramp D2'] = PowerampD2()
        self.procedures['poweramp C2'] = PowerampC2()
        self.procedures['SHS'] = SHS()
        # initialize gui
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed, disable_under_module_control=True)
        input_table.add('OPA', self.opa_combo)
        # procedure combo
        self.procedure_combo = pc.Combo(allowed_values=self.procedures.keys(), disable_under_module_control=True)
        self.procedure_combo.updated.connect(self.on_procedures_updated)
        input_table.add('Procedure', self.procedure_combo)
        layout.addWidget(input_table)
        # procedure guis
        for procedure in self.procedures.values():
            layout.addWidget(procedure.input_table)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)
        self.on_procedures_updated()

    def launch_scan(self):
        opa_index = self.opa_combo.read_index()
        procedure_key = self.procedure_combo.read()
        axes = self.procedures[procedure_key].assemble_axes(opa_index)
        self.scan.launch(axes)

    def on_done(self):
        # begin
        self.wait_window.show()
        # get path
        data_path = daq.data_path.read()
        data_folder, file_name, file_extension = wt.kit.filename_parse(data_path)
        # process using loaded procedure
        procedure_name = self.procedure_combo.read()
        opa_index = self.opa_combo.read_index()
        old_crvs = opas.hardwares[opa_index].address.ctrl.get_crv_paths()
        output_image_path = self.procedures[procedure_name].process(opa_index+1, data_path, old_crvs)
        # send message on slack
        if g.slack_enabled.read():
            slack = g.slack_control.read()
            slack.send_message('scan complete - {} elapsed'.format(g.progress_bar.time_elapsed.text()))
            slack.upload_file(output_image_path)
        # upload on google drive
        if g.google_drive_enabled.read():
            g.google_drive_control.read().upload(data_folder)
        # finish
        self.autocopy(data_folder)
        self.wait_window.hide()
    
    def on_procedures_updated(self):
        for procedure in self.procedures.values():
            procedure.hide()
        self.procedures[self.procedure_combo.read()].show()

gui = GUI(module_name)

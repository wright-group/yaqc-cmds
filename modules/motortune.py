### define ####################################################################

module_name = 'MOTORTUNE'

### import ####################################################################

import sys
import time
import collections

import numpy as np

import project.project_globals as g
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.classes as pc
import project.widgets as pw

### import hardware control ###################################################

import spectrometers.spectrometers as spectrometers
import delays.delays as delays
import opas.opas as opas
import daq.daq as daq

### objects ###################################################################

# to do with communication between threads
fraction_complete = pc.Mutex()
go = pc.Busy()
going = pc.Busy()
pause = pc.Busy()
paused = pc.Busy()


class motor_gui():
    
    def __init__(self, name, center, width, number, use_tune_points):
        self.name = name
        self.use_tune_points = use_tune_points
        self.input_table = pw.InputTable()
        self.input_table.add(name, None)
        allowed = ['Set', 'Scan', 'Static']
        self.method = pc.Combo(allowed_values=allowed, disable_under_module_control=True)
        self.use_tune_points.updated.connect(self.update_disabled)
        self.method.updated.connect(self.update_disabled)
        self.input_table.add('Method', self.method)
        self.center = pc.Number(initial_value=center, disable_under_module_control=True)
        self.input_table.add('Center', self.center)
        self.width = pc.Number(initial_value=width, disable_under_module_control=True)
        self.input_table.add('Width', self.width)
        self.npts = pc.Number(initial_value=number, decimals=0, disable_under_module_control=True)
        self.input_table.add('Number', self.npts)
        self.update_disabled()
        
    def update_disabled(self):
        self.center.set_disabled(True)
        self.width.set_disabled(True)
        self.npts.set_disabled(True)
        method = self.method.read()
        if method == 'Set':
            self.center.set_disabled(self.use_tune_points.read())
        elif method == 'Scan':
            self.center.set_disabled(self.use_tune_points.read())
            self.width.set_disabled(False)
            self.npts.set_disabled(False)
        elif method == 'Static':
            self.center.set_disabled(False)


class OPA_gui():
    
    def __init__(self, hardware, layout, use_tune_points):
        self.hardware = hardware
        motor_names = self.hardware.address.ctrl.motor_names
        self.motors = []
        for name in motor_names:
            motor = motor_gui(name, 30, 1, 11, use_tune_points)
            layout.addWidget(motor.input_table)
            self.motors.append(motor)
        self.hide()  # initialize hidden
            
    def hide(self):
        for motor in self.motors:
            motor.input_table.hide()
    
    def show(self):
        for motor in self.motors:
            motor.input_table.show()
        

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()

    @QtCore.pyqtSlot(list)
    def run(self, inputs):

        # unpack inputs -------------------------------------------------------

        scan_dictionary, daq_widget, gui = inputs
        opa_gui = gui.opa_guis[gui.opa_combo.read_index()]
        opa_hardware = opa_gui.hardware
        
        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        # setup scan ----------------------------------------------------------

        # discover axes
        scan_axes = []
        opa_friendly_name = opas.hardwares[gui.opa_combo.read_index()].friendly_name
        if gui.use_tune_points.read():
            scan_axes.append(opa_friendly_name)
        for motor in opa_gui.motors:
            if motor.method.read() == 'Scan':
                scan_axes.append('_'.join([opa_friendly_name, motor.name]))
        if gui.mono_method_combo.read() == 'Scan':
            scan_axes.append('wm')
        
        # calculate npts
        npts = 1
        if gui.use_tune_points.read():
            npts *= len(opa_gui.hardware.address.ctrl.get_points()[0])
        for motor in opa_gui.motors:
            if motor.method.read() == 'Scan':
                npts *= motor.npts.read()
        if gui.mono_method_combo.read() == 'Scan':
            npts *= gui.mono_npts.read()
        
        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, module_name, scan_axes=scan_axes, fit=False)

        # set static motors
        for motor_index, motor in enumerate(opa_gui.motors):
            if motor.method.read() == 'Static':
                motor_name = opa_gui.motors[motor_index].name
                motor_destination = opa_gui.motors[motor_index].center.read()
                opa_hardware.q.push('set_motor', [motor_name, motor_destination])

        # do loop -------------------------------------------------------------

        break_scan = False
        idx = 0
        # tune points
        if gui.use_tune_points.read():
            tune_point_destinations = opa_gui.hardware.address.ctrl.get_points()[0]
        else:
            tune_point_destinations = [None]
        for tune_point_destination in tune_point_destinations:
            if tune_point_destination is not None:
                motor_positions = opa_gui.hardware.address.ctrl.curve.get_motor_positions(tune_point_destination)
                for motor_index, motor in enumerate(opa_gui.motors):
                    if not motor.method.read() == 'Static':
                        motor_name = motor.name
                        motor_destination = motor_positions[motor_index]
                        opa_hardware.q.push('set_motor', [motor_name, motor_destination])
                opa_hardware.q.push('get_motor_positions')
                opa_hardware.wait_until_still()  # need to wait before reading position in inner loop
            # motor positions
            motor_position_dictionary = collections.OrderedDict()
            for motor_index, motor in enumerate(opa_gui.motors):
                if motor.method.read() == 'Scan':
                    current_position = opa_gui.hardware.address.ctrl.get_motor_positions()[motor_index]
                    width = motor.width.read()/2.  # width is total width of scan
                    number = motor.npts.read()
                    motor_position_dictionary[motor.name] = np.linspace(current_position-width, current_position+width, number)
            for motor_idx in np.ndindex(*[arr.size for arr in motor_position_dictionary.values()]):
                if not gui.mono_method_combo.read() == 'Scan':  # if motor is innermost index
                    if motor_idx[-1] == 0:
                        motor_name = motor_position_dictionary.keys()[-1]
                        daq.control.index_slice(col='_'.join([opa_friendly_name, motor_name]))
                        motor_points = motor_position_dictionary[motor_name]
                        daq.gui.set_slice_xlim(motor_points.min(), motor_points.max())
                for motor_index, position_index in enumerate(motor_idx):
                    motor_name = motor_position_dictionary.keys()[motor_index]
                    motor_destination = motor_position_dictionary[motor_name][position_index]
                    opa_hardware.q.push('set_motor', [motor_name, motor_destination])
                opa_hardware.q.push('wait_until_still')
                opa_hardware.q.push('get_motor_positions')
                # spec positions
                if gui.mono_method_combo.read() == 'Scan':
                    if gui.use_tune_points.read():
                        spec_center = tune_point_destination
                    else:
                        spec_center = gui.mono_center.read()
                    spec_width = gui.mono_width.read()/2.
                    spec_number = gui.mono_npts.read()
                    spec_destinations = np.linspace(spec_center-spec_width, spec_center+spec_width, spec_number)
                    daq.control.index_slice(col='wm')
                    daq.gui.set_slice_xlim(spec_destinations.min(), spec_destinations.max())
                elif gui.mono_method_combo.read() == 'Set':
                    spec_destinations = [tune_point_destination]
                elif gui.mono_method_combo.read() == 'Static':
                    spec_destinations = [None]
                for spec_destination in spec_destinations:
                    if spec_destination is not None:
                        spectrometers.hardwares[0].set_position(spec_destination, 'wn')
                    # wait for hardware
                    g.hardware_waits.wait()
                    # read from daq
                    daq.control.acquire()
                    daq.control.wait_until_daq_done()
                    idx += 1
                    fraction_complete.write(float(idx)/float(npts))
                    self.update_ui.emit()
                    if not self.check_continue():
                        break_scan = True
                    if break_scan: break
                if break_scan: break
            if break_scan: break
            
        # end -----------------------------------------------------------------

        print 'end'
        fraction_complete.write(1.)
        going.write(False)
        g.module_control.write(False)
        g.logger.log('info', 'Scan done', 'some info describing this scan')
        self.update_ui.emit()
        self.done.emit()

    def check_continue(self):
        '''
        you should put this method into your scan loop wherever you want to check
        for pause or stop commands from the main program

        at the very least this method MUST go into your innermost loop

        for loops, use it as follows: if not self.check_continue(): break
        '''
        while pause.read():
            paused.write(True)
            pause.wait_for_update()
        paused.write(False)
        return go.read()

#move scan to own thread
scan_obj = scan()
scan_obj.moveToThread(scan_thread)

### gui #######################################################################

class GUI(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        scan_obj.update_ui.connect(self.update)
        self.create_frame()
        self.create_advanced_frame()
        self.show_frame() #check once at startup
        g.shutdown.read().connect(self.stop)

    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        # shared settings
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed, disable_under_module_control=True)
        self.opa_combo.updated.connect(self.update_opa_display)
        self.use_tune_points = pc.Bool(initial_value=True, disable_under_module_control=True)
        self.use_tune_points.updated.connect(self.update_mono_settings)
        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        input_table.add('Use Tune Points', self.use_tune_points)
        layout.addWidget(input_table)

        # OPA settings
        self.opa_guis = [OPA_gui(hardware, layout, self.use_tune_points) for hardware in opas.hardwares]
        self.opa_guis[0].show()
        
        # line
        line = pw.line('H')
        layout.addWidget(line)
        
        # mono settings
        allowed = ['Scan', 'Set', 'Static']
        self.mono_method_combo = pc.Combo(allowed, disable_under_module_control=True)
        self.mono_method_combo.updated.connect(self.update_mono_settings)
        self.mono_center = pc.Number(initial_value=7000, units='wn', disable_under_module_control=True)
        self.mono_center.set_disabled_units(True)
        self.mono_width = pc.Number(initial_value=500, units='wn', disable_under_module_control=True)
        self.mono_width.set_disabled_units(True)
        self.mono_npts = pc.Number(initial_value=51, decimals=0, disable_under_module_control=True)
        input_table = pw.InputTable()
        input_table.add('Spectrometer', None)
        input_table.add('Method', self.mono_method_combo)
        input_table.add('Center', self.mono_center)
        input_table.add('Width', self.mono_width)
        input_table.add('Number', self.mono_npts)
        layout.addWidget(input_table)
        self.update_mono_settings()
        
        # line
        line = pw.line('H')
        layout.addWidget(line)

        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)

        # go button
        self.go_button = pw.module_go_button()
        self.go_button.give_launch_scan_method(self.launch_scan)
        self.go_button.give_stop_scan_method(self.stop)
        self.go_button.give_scan_complete_signal(scan_obj.done)
        self.go_button.give_pause_objects(pause, paused)

        layout.addWidget(self.go_button)

        layout.addStretch(1)

        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)

        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == module_name:
            self.frame.show()
            self.advanced_frame.show()

    def launch_scan(self):
        go.write(True)
        print 'running'
        scan_dictionary = {}
        inputs = [scan_dictionary, self.daq_widget, self]
        QtCore.QMetaObject.invokeMethod(scan_obj, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(list, inputs))
        g.progress_bar.begin_new_scan_timer()

    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())

    def update_mono_settings(self):
        self.mono_center.set_disabled(True)
        self.mono_width.set_disabled(True)
        self.mono_npts.set_disabled(True)
        method = self.mono_method_combo.read()
        if method == 'Set':
            self.mono_center.set_disabled(self.use_tune_points.read())
        elif method == 'Scan':
            self.mono_center.set_disabled(self.use_tune_points.read())
            self.mono_width.set_disabled(False)
            self.mono_npts.set_disabled(False)
        elif method == 'Static':
            self.mono_center.set_disabled(False)

        
    def update_opa_display(self):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[self.opa_combo.read_index()].show()

    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'

gui = GUI()
### define ####################################################################

module_name = 'TEMPLATE EXPERIMENT'
common_name = 'Template'

### import ####################################################################

import sys
import time

import numpy as np
import numexpr as ne

import matplotlib
matplotlib.pyplot.ioff()

import project.project_globals as g
import project.classes as pc
import project.widgets as pw

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets
from modules.snake import Snake

import WrightTools as wt

### import hardware control ###################################################

import spectrometers.spectrometers as specs
MicroHR = specs.hardwares[0]
import delays.delays as delays
D1 = delays.hardwares[0]
D2 = delays.hardwares[1]
Delays = [D1,D2]
import opas.opas as opas
OPA1 = opas.hardwares[0]
OPA2 = opas.hardwares[1]
#OPA3 = opas.hardwares[2]
OPAs = [OPA1,OPA2]
import daq.daq as daq

### objects ###################################################################

# to do with communication between threads
fraction_complete = pc.Mutex()
go = pc.Busy()
going = pc.Busy()
pause = pc.Busy()
paused = pc.Busy()

axis_limits = pc.NumberLimits(1,5)

class hw_table():
    def __init__(self,hardware):
        self.hardware = hardware
        self.input_table = pw.InputTable()

        allowed = ['Static','Scan','Equation']
        self.method = pc.Combo(allowed_values=allowed, disable_under_module_control=True)
        self.equ = pc.String()
        self.axis = pc.Number(initial_value=1, limits=axis_limits, decimals=0)
        self.start = pc.Number(initial_value=0, units=None)
        self.stop = pc.Number(initial_value=0, units=None)
        self.npts = pc.Number(initial_value=0, decimals=0)

        self.input_table.add('Method',self.method)
        self.input_table.add('Axis',self.axis)
        self.input_table.add('Equation',self.equ)
        self.input_table.add('Start',self.start)
        self.input_table.add('Stop',self.stop)
        self.input_table.add('Points',self.npts)

        self.update_disabled()
        self.input_table.hide()

        self.inputs = [self.method,self.axis,self.equ,self.start,self.stop,self.npts]

    def update_disabled(self):
        for i in self.inputs[1:]:
            i.set_disabled(True)
        method = self.method.read()
        if method == 'Equation':
            self.equ.set_disabled(False)
            self.axis.set_disabled(False)
        elif method == 'Scan':
            self.axis.set_disabled(False)
            self.start.set_disabled(False)
            self.stop.set_disabled(False)
            self.npts.set_disabled(False)
        elif method == 'Static':
            self.start.set_disabled(False)

class OPA_table(hw_table):
    def __init__(self,hardware):
        hw_table.__init__(self,hardware)

        self.usespd = pc.Bool()
        self.start = pc.Number(initial_value=1700, units='wn')
        self.stop = pc.Number(initial_value=1200, units='wn')
        self.npts = pc.Number(initial_value=10, decimals=0)
        self.inputs = [self.usespd,self.method,self.axis,self.equ,self.start,self.stop,self.npts]

        self.update_disabled()
        self.input_table.hide()

def Delay_table(hw_table):
    def __init__(self,hardware):
        hw_table.__init__(self,hardware)

        self.start = pc.Number(initial_value=-3, units='ps')
        self.stop = pc.Number(initial_value=5, units='ps')
        self.npts = pc.Number(initial_value=10, decimals=0)

        self.update_disabled()
        self.input_table.hide()

class Mono_table(hw_table):
    def __init__(self,hardware):
        hw_table.__init__(self,hardware)

        self.start = pc.Number(initial_value=1400, units='wn')
        self.stop = pc.Number(initial_value=1600, units='wn')
        self.npts = pc.Number(initial_value=10, decimals=0)

        self.update_disabled()
        self.input_table.hide()

class Mono_gui():

    def __init__(self,layout):
        self.mono = Mono_table(MicroHR)
        layout.addWidget(self.mono.input_table)
        self.hide()

    def hide(self):
        self.mono.input_table.hide()

    def show(self):
        self.mono.input_table.show()

class Delay_gui():

    def __init__(self,layout):
        self.delays = []
        for obj in Delays:
            delay = Delay_table(obj)
            layout.addWidget(delay.input_table)
            self.delays.append(delay)
        self.hide() # initialize hidden

    def hide(self):
        for opa in self.opas:
            opa.input_table.hide()

    def show(self):
        for opa in self.opas:
            opa.input_table.show()

class OPA_gui():

    def __init__(self,layout):
        self.opas = []
        for obj in OPAs:
            opa = OPA_table(obj)
            layout.addWidget(opa.input_table)
            self.opas.append(opa)
        self.hide() # initialize hidden

    def hide(self):
        for opa in self.opas:
            opa.input_table.hide()

    def show(self):
        for opa in self.opas:
            opa.input_table.show()

'''
choose1 = pc.bool(initial_value = False)
choose2 = pc.bool(initial_value = False)
'''

usespd = pc.bool(initial_value = True)


### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()

    @QtCore.pyqtSlot(list)
    def run(self, inputs):

        # unpack inputs -------------------------------------------------------

        scan_dictionary = inputs[0]
        daq_widget = inputs[1]
        gui = inputs[2]

        OPA1_destinations = np.linspace(OPA1_start.read('wn'), OPA1_stop.read('wn'), OPA1_npts.read())
        OPA2_destinations = np.linspace(OPA2_start.read('wn'), OPA2_stop.read('wn'), OPA2_npts.read())
        #OPA3_destinations = np.linspace(OPA3_start.read('wn'), OPA3_stop.read('wn'), OPA3_npts.read())

        #D1_destinations = np.linspace(D1_start.read('ps'), D1_stop.read('ps'), D1_npts.read())
        #D2_destinations = np.linspace(D2_start.read('ps'), D2_stop.read('ps'), D2_npts.read())

        #MircorHR_destinations = np.linspace(MircorHR_start.read('ps'), MircorHR_stop.read('ps'), MircorHR_npts.read())

        #nd1_destinations = np.linspace(nd1_start.read('OD'), nd1_stop.read('OD'), nd1_npts.read())
        #nd2_destinations = np.linspace(nd2_start.read('OD'), nd2_stop.read('OD'), nd2_npts.read())

        ind_axes=[OPA1_destinations,OPA2_destinations]
        equ_axes=[D1,D2,MicroHR]

        #total_npts =

        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', common_name + 'begun', '')

        # scan ----------------------------------------------------------------

        scan_axes = []


        # Create grid for/with Snake
        grid = np.array(np.meshgrid(*ind_axes))
        grid = np.resize(grid,np.insert(grid.shape[1:],0,grid.shape[0]+len(equ_axes)))
        mono_destinations = np.array([12500+2*o for o in OPA1_destinations])
        mono_mesh = np.tile(mono_destinations,[D1_npts,1])
        grid[-1] = mono_mesh

        if usecrv.read():

            for idx in np.ndindex(*grid[1].shape):
                OPA1.q.push('spd',[grid[0][idx]])
                g.hardware_waits.wait()
                grid[1][idx] = g.OPA1_spd.read() + grid[1][idx]

        grid = np.transpose(grid)
        units = ['wn','ps','wn']
        hw = [OPA1,D1,MicroHR]

        destinations = [OPA1_destinations,D1_destinations]
        data_cols = ['OPA1','d1','MicroHR']

        idx, t = Snake(grid,hw,units)
        # idx, t, slice_dim_index, slices = Snake(grid, hw, units)
        slices = np.full(OPA1_npts,D1_npts)
        slice_dim_index = 1

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, scan_origin=module_name, scan_axes=scan_axes, fit=False)


        # D1 slices for OPA1 setpoints (for now, get Snake slice support)
        daq.gui.set_slice_xlim(D1_destinations.min(), D1_destinations.max())
        # do loop
        break_scan = False
        point_num = 0
        daq.gui.set_slice_xlim(destinations[slice_dim_index].min(), destinations[slice_dim_index].max())
        for point in idx:
            if point_num % slices[0] == 0:
                if point_num > 0:
                    np.delete(slices,0)
                if len(slices) > 0:
                    daq.control.index_slice(col=data_cols[slice_dim_index])
            for i in len(idx):
                hw[i].set_position(idx[i],units[i])
            g.hardware_waits.wait()
            # read from daq
            daq.control.acquire()
            daq.control.wait_until_daq_done()
            # update
            point_num += 1
            fraction_complete.write(float(point_num)/float(total_npts))
            self.update_ui.emit()
            if not self.check_continue():
                break_scan = True
            if break_scan:
                break
        g.logger.log('info', 'OPA1-D1 scan done', 'Spectra Delay Correction Scan for OPA1 Done')


        #end-------------------------------------------------------------------

        fraction_complete.write(1.)
        going.write(False)
        g.module_control.write(False)
        g.logger.log('info', 'Scan done', 'spec_delay has finished a scan')
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

# scan object exists in the shared scan thread
scan_obj = scan()
scan_thread = g.scan_thread.read()
scan_obj.moveToThread(scan_thread)

### gui #######################################################################

class GUI(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        scan_obj.update_ui.connect(self.update)
        self.create_frame()
        self.create_advanced_frame()
        self.show_frame()  # check once at startup
        g.shutdown.read().connect(self.stop)
        scan_obj.done.connect(self.plot)

    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        # input table

        OPA_table.add('Use current spectral delay correction:',usespd)

        self.opa_gui = OPA_gui(layout)

        self.delay_gui =
        elay_table = pw.InputTable()
        '''
        Delay_table.add('D1 Start', D1_start)
        Dealy_table.add('D1 Stop', D1_stop)
        Dealy_table.add('D1 Number', D1_npts)
        Dealy_table.add('D1 Number', D1_npts)
        '''
        '''
        Dealy_table.add('D2 Start', D2_start)
        Dealy_table.add('D2 Stop', D2_stop)
        Dealy_table.add('D2 Number', D2_npts)
        '''
        Mono_table = pw.InputTable()

        layout.addWidget(OPA_table)
        layout.addWidget(Delay_table)
        layout.addWidget(Mono_table)

        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)

        # go button
        self.go_button = custom_widgets.module_go_button()
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
        if choose1.read() or choose2.read():
            go.write(True)
            print 'running'
            scan_dictionary = {}
            inputs = [scan_dictionary, self.daq_widget, self]
            QtCore.QMetaObject.invokeMethod(scan_obj, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(list, inputs))
            g.progress_bar.begin_new_scan_timer()

    def plot(self):
        print 'plotting'
        data_path = daq.data_path.read()
        data_obj = wt.data.from_PyCMDS(data_path)
        if len(data_obj.axes) == 1:
            artist = wt.artists.mpl_1D(data_obj)
        else:
            artist = wt.artists.mpl_2D(data_obj)
        fname = data_path.replace('.data', '')
        artist.plot(fname=fname, autosave=True)

    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())

    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'

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

gui = gui()

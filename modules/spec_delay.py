### define ####################################################################

module_name = 'SPECTRAL DELAY CORRECTION'

### import ####################################################################

import sys
import time

import numpy as np

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
import opas.opas as opas
OPA1 = opas.hardwares[0]
OPA2 = opas.hardwares[1]
import daq.daq as daq

### objects ###################################################################

# to do with communication between threads
fraction_complete = pc.Mutex()
go = pc.Busy()
going = pc.Busy()
pause = pc.Busy()
paused = pc.Busy()

# control objects
OPA1_start = pc.Number(initial_value=1700, units='wn')
OPA1_stop = pc.Number(initial_value=1200, units='wn')
OPA1_npts = pc.Number(initial_value=10, decimals=0)

OPA2_start = pc.Number(initial_value=1700, units='wn')
OPA2_stop = pc.Number(initial_value=1200, units='wn')
OPA2_npts = pc.Number(initial_value=10, decimals=0)

D1_start = pc.Number(initial_value=-5, units='ps')
D1_stop = pc.Number(initial_value=5, units='ps')
D1_npts = pc.Number(initial_value=20, decimals=0)

D2_start = pc.Number(initial_value=-5, units='ps')
D2_stop = pc.Number(initial_value=5, units='ps')
D2_npts = pc.Number(initial_value=20, decimals=0)

choose1 = pc.bool(initial_value = False)
choose2 = pc.bool(initial_value = False)

usecrv = pc.bool(initial_value = True)


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

        D1_destinations = np.linspace(D1_start.read('ps'), D1_stop.read('ps'), D1_npts.read())
        D2_destinations = np.linspace(D2_start.read('ps'), D2_stop.read('ps'), D2_npts.read())

        total_npts = len(D1_destinations)*len(OPA1_destinations)*choose1.read() + len(D2_destinations)*len(OPA2_destinations)*choose2.read()

        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'spec_delay begun', '')

        # scan ----------------------------------------------------------------

        if choose1.read():
            scan_axes = []
            scan_axes.append('d1')
            scan_axes.append('OPA1')

            # Create grid for/with Snake
            grid = np.array(np.meshgrid(OPA1_destinations,D1_destinations))
            grid = np.resize(grid,np.insert(grid.shape[1:],0,grid.shape[0]+1))
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


        if choose2.read():
            scan_axes = []
            scan_axes.append('d2')
            scan_axes.append('OPA2')

            # Create grid for/with Snake
            grid = np.array(np.meshgrid(OPA2_destinations,D2_destinations))
            grid = np.resize(grid,np.insert(grid.shape[1:],0,grid.shape[0]+1))
            mono_destinations = np.array([12500+2*o for o in OPA2_destinations])
            mono_mesh = np.tile(mono_destinations,[D2_npts,1])
            grid[-1] = mono_mesh

            if usecrv.read():
                for idx in np.ndindex(*grid[1].shape):
                    grid[1][idx] = OPA2.spd(grid[0][idx]) + grid[1][idx]

            grid = np.transpose(grid)
            units = ['wn','ps','wn']
            hw = [OPA2,D2,MicroHR]

            destinations = [OPA2_destinations,D2_destinations]
            data_cols = ['OPA2','d2','MicroHR']

            idx, t = Snake(grid,hw,units)
            # idx, t, slice_dim_index, slices = Snake(grid, hw, units)
            slices = np.full(OPA2_npts,D2_npts)
            slice_dim_index = 1

            # initialize scan in daq
            daq.control.initialize_scan(daq_widget, scan_origin=module_name, scan_axes=scan_axes, fit=False)

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
            g.logger.log('info', 'OPA2-D2 scan done', 'Spectra Delay Correction Scan for OPA2 Done')

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

class gui(QtCore.QObject):

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
        input_table = pw.InputTable()
        input_table.add('Use current spectral delay correction:',usecrv)

        input_table.add('OPA/D 1', choose1)
        input_table.add('OPA1 Start', OPA1_start)
        input_table.add('OPA1 Stop', OPA1_stop)
        input_table.add('OPA1 Number', OPA1_npts)
        input_table.add('D1 Start', D1_start)
        input_table.add('D1 Stop', D1_stop)
        input_table.add('D1 Number', D1_npts)

        input_table.add('',None)

        input_table.add('OPA/D 2', choose2)
        input_table.add('OPA2 Start', OPA2_start)
        input_table.add('OPA2 Stop', OPA2_stop)
        input_table.add('OPA2 Number', OPA2_npts)
        input_table.add('D2 Start', D2_start)
        input_table.add('D2 Stop', D2_stop)
        input_table.add('D2 Number', D2_npts)
        layout.addWidget(input_table)

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

gui = gui()

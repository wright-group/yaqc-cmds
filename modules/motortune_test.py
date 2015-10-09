### define ####################################################################

module_name = 'MOTORTUNE OPA1 TEST'

### import ####################################################################

import sys
import time

import numpy as np

import project.project_globals as g
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.classes as pc
import project.widgets as pw

### import hardware control ###################################################

import spectrometers.spectrometers as spectrometers
MicroHR=spectrometers.hardwares[0]
import delays.delays as delays
D1 = delays.hardwares[0]
D2 = delays.hardwares[1]
import opas.opas as opas
OPA1 = opas.hardwares[0]
OPA2 = opas.hardwares[1]
OPA3 = opas.hardwares[2]
import daq.daq as daq

### scan globals ##############################################################

# These scan globals are used to communicated between the gui and the scan,
# which are running in different threads. All are mutex for this reason.

class fraction_complete:
    def __init__(self):
        self.value = 0
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
fraction_complete = fraction_complete()

class go:
    def __init__(self):
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
go = go()

class going(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=5000):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
going = going()

class pause(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self):
        if self.value: return self.WaitCondition.wait(self)
pause = pause()

class paused(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()
    def wait_for_update(self, timeout=100):
        if self.value: return self.WaitCondition.wait(self, msecs=timeout)
paused = paused()

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()

    @QtCore.pyqtSlot(list)
    def run(self, inputs):

        # unpack inputs -------------------------------------------------------

        scan_dictionary = inputs[0]

        daq_widget = inputs[1]

        # startup -------------------------------------------------------------

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        # Scan Setup----------------------------------------------------------------
        a0 = [14.999906259999984, 15.229863000000014, 15.689312999999997, 16.148814000000012,
              16.837973000000005, 17.06766300000001, 18.216271000000003, 18.905515000000012,
              19.135172000000008, 20.513521999999988, 20.972973000000014, 21.202783999999983,
              21.662131000000016, 21.89189, 22.121581000000003, 22.351340000000015,
              22.810773000000008, 23.270222999999991, 23.729655999999988, 23.959398999999998,
              24.189123999999996, 24.418917999999998, 24.878281999999992, 25.108024000000022,
              25.337749000000013, 25.567473999999969, 25.797250999999978, 26.026924000000005,
              26.256632000000014, 26.716100000000015, 26.945842000000003, 27.175533000000009,
              27.405275000000007, 27.634982999999988, 27.864708, 28.09445000000003,
              28.553951999999985, 28.783625000000026, 29.013333000000024, 29.243058000000016,
              29.472800999999968, 29.702526000000017]

        a1 = [43.394308930613171, 43.518112129667379, 43.532080922360429, 43.516672800999523,
              43.454756718339077, 43.424470299099916, 43.311650391995606, 43.216239365030425,
              43.19516957793045, 42.982986008344028, 42.911810538566321, 42.8641948624078,
              42.779283142494812, 42.720637286368216, 42.684186248509619, 42.619198990625264,
              42.514388845765779, 42.395745785481076, 42.270623676719445, 42.20069956988619,
              42.132543221067607, 42.055016209382465, 41.894041818061837, 41.808700974576645,
              41.717128782668475, 41.632078518730864, 41.537918589771493, 41.43418488290007,
              41.344862931311098, 41.146030321178785, 41.027103169062848, 40.91467748260137,
              40.789605630360704, 40.671492451339702, 40.536458902603648, 40.396147928816283,
              40.107782922081867, 39.946997995456165, 39.781415867637435, 39.614855164113202,
              39.431505214307357, 39.230174177186854]

        spec_destinations = np.linspace(1100, 1620, 200)
        grating_destinations = np.linspace(35, 37, 20)
        #bbo_destinations = np.linspace()        
        bbo_points = 50
        bbo_half_width = 2.5
        bbo_equ = 37.5#lambda gra: np.interp(gra,a0,a1)

        npts = len(spec_destinations)*bbo_points#*len(grating_destinations)

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, module_name, scan_axes=['w1_grating','w1_bbo'], fit=False)

        # do loop - No need to change
        break_scan = False
        idx = 0
        for k in range(len(grating_destinations)):
            # Use the BBO perameters above to get the center point, width, etc.
            center = bbo_equ#(grating_destinations[k])
            print 'center at', center
            bbo_destinations = np.linspace(center-bbo_half_width,center+bbo_half_width,bbo_points)
            daq.control.index_slice(col='w2_bbo')
            daq.gui.set_slice_xlim(bbo_destinations.min(), bbo_destinations.max())
            for j in range(bbo_points):
                inputs = [grating_destinations[k], bbo_destinations[j], -1.] #negative numbers don't move moter
                OPA1.q.push('set_motors', inputs)
                # slice index
                
                #for i in range(len(bbo_destinations)):
                    # set mono
                    #MicroHR.set_position(spec_destinations[i], 'nm')
                    # wait for all hardware
                g.hardware_waits.wait()
                    # read from daq
                daq.control.acquire()
                daq.control.wait_until_daq_done()
                    # update
                idx += 1
                fraction_complete.write(float(idx)/float(npts))
                self.update_ui.emit()
                if not self.check_continue():
                    break_scan = True
                    #if break_scan:
                    #    break
                if break_scan:
                    break
                # fit each slice
                #daq.control.fit('MicroHR', 'vai0 Mean')
            if break_scan:
                break

        #end-------------------------------------------------------------------

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

class gui(QtCore.QObject):

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

        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)

        input_table = pw.InputTable()
        input_table.add('OPA', self.opa_combo)
        layout.addWidget(input_table)

        motor_names = ['grating', 'bbo', 'mixer']
        input_table = pw.InputTable()
        for i in range(len(motor_names)):
            width = pc.Number()
            center = pc.Number()
            npts = pc.Number()
            input_table.add(motor_names[i], None)
            input_table.add('Width', width)
            input_table.add('Center', center)
            input_table.add('Number', npts)
        layout.addWidget(input_table)

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
        inputs = [scan_dictionary, self.daq_widget]
        QtCore.QMetaObject.invokeMethod(scan_obj, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(list, inputs))
        g.progress_bar.begin_new_scan_timer()

    def update(self):
        g.progress_bar.set_fraction(fraction_complete.read())

    def stop(self):
        print 'stopping'
        go.write(False)
        while going.read(): going.wait_for_update()
        print 'stopped'

gui = gui()
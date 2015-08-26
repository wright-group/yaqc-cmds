#to do##########################################################################

# Alll Data Processing - This should be it's own module?
# Generalize selection of OPA. Right now, OPA1 is used universally
# Interface plotting tuning curve output/fit to curve selection.
#   This could happen in OPA advanced or something instead.

#import#########################################################################

import sys
import time

import numpy as np

import project.project_globals as g
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets

#import hardware control#######################################################

import spectrometers.spectrometers as spec
MicroHR = spec.hardwares[0]
import delays.delays as delay
D1 = delay.hardwares[0]
D2 = delay.hardwares[1]
import opas.pico.pico_opa as opa
OPA1 = opa.hardwares[0]
OPA2 = opa.hardwares[1]
OPA3 = opa.hardwares[2]

import daq.daq as daq

#scan globals##################################################################

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

        #startup---------------------------------------------------------------
        # Leave this alone.
        g.module_control.write(True)    # Disables GUI, gives control to module
        going.write(True)               # communication, see above
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', 'some info describing this scan')

        #scan------------------------------------------------------------------

        new_tune_curve = []
        # after running this a couple of times, we should know the ideal perameters
        bbo_width = 0.3 # half width of bbo scan
        bbo_step  = .02 # step size in mm
        mix_width = 1.0 # half width of mixer scan
        mix_step = .1 # step size in mm
        mono_width = 50 # half width of mono scan
        mono_step = 4 # step size in wavenumbers

        bbo_pts = np.ceil(bbo_width * 2 / bbo_step)
        mix_pts = np.ceil(mix_width * 2 / mix_step)
        mono_pts = np.ceil(mono_width * 2 / mono_step)

        color_pts = np.linspace(1250, 1800, 14)

        for i in color_pts:
            m_center = OPA1.crv.new_motor_positions(i)
            OPA1.set_motors(0, m_center[0])

            bbo_destinations = np.linspace(m_center[1] - bbo_width, m_center[1] + bbo_width + bbo_step, bbo_pts)
            mix_destinations = np.linspace(m_center[2] - mix_width, m_center[2] + mix_width + mix_step, mix_pts )
            mono_destinations = np.linspace(i - mono_width, i + mono_width + mono_step, mono_pts )

            print i, ' wn, BBO scan'
            for j in bbo_destinations: # BBO scan loop, runs for each color
                OPA1.set_motors(1,j)
                g.hardware_waits.wait()
                daq.control.acquire()
                daq.control.wait_until_done()
                if not self.check_continue(): break
            # process obtained data here to fit a gaussian, find max OF PYRO
            bbo_max = m_center[1] #This is just a filler for the actual max
            OPA1.set_motors(1,bbo_max)

            print i, ' wn, Mixer scan'
            for j in mix_destinations: # Mixer loop
                OPA1.set_motors(2,j)
                g.hardware_waits.wait()
                daq.control.acquire()
                daq.control.wait_until_done()
                if not self.check_continue(): break
            # process obtained data here to fit a gaussian, find max OF PYRO
            mix_max = m_center[2] #This is just a filler for the actual max
            OPA1.set_motors(2,mix_max)

            print i, ' wn, Mono scan'
            for j in mono_destinations: # determine color. Replace with array detector?
                MicroHR.set_position(j, 'wn')
                g.hardware_waits.wait()
                daq.control.acquire()
                daq.control.wait_until_done()
                if not self.check_continue(): break
            # find center color, max FROM DETECTOR THROUGH MONO (a0)
            center_color = i

            new_tune_curve.append([center_color, m_center[0], bbo_max, mix_max])


            print i, ' wn, update bar'

            fraction_complete.write(float(i+1)/float(npts))
            self.update_ui.emit()
            if not self.check_continue(): break

        #end-------------------------------------------------------------------
        # Save the tuning curve somehow. Maybe see if Rachel has a way to do this.
        # MAKE SURE YOU HAVE CORRECTED THIS SYNTAX IN THE END!!
        OPA1.crv.write_curve(new_tune_curve,new_file_path)
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

        # daq widget
        daq_widget = daq.Widget()
        layout.addWidget(daq_widget)

        #go button
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
        g.module_combobox.add_module('TEMPLATE', self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by template')
        my_widget.setAutoFillBackground(True)
        layout.addWidget(my_widget)

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == 'TEMPLATE':
            self.frame.show()
            self.advanced_frame.show()

    def launch_scan(self):
        go.write(True)
        print 'running'
        inputs = ['hey this is inputs']
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
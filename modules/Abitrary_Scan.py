### The Scan Dictionary #######################################################
# The scan dictionary is used by the scan module to run the scan. Not all of
# these dictionary values are used and some of them are redundant. I've included
# everything here to allow any of the math that should be done in the GUI to be
# done there. We can decide if the GUI should pass the positions or the start,
# stop, and num points arrays, since they contain each other.

# 'Num Points': 1-D array of numper of points on an axis
# 'Hardwares': 2-D array of [axis][hardware object].
# 'Units': 2-D array of [axis][hardware units]
# 'Limits': 2-D array of [axis][limit object]
# 'Start' and 'Stop': 2-D arrays of [axis][number object] <<Not currently used in scan opbject>>
# 'Positions':pos_a[i][j] = np.linspace(start_a[i][j].read(unit_list[i][j]),
#                                       stop_a[j].read(unit_list[i][j]),
#                                       num_a[i].read())
# 'Snake' = Boolian, reserved for future use
# 'Description' = a string, an informative discription of the scan to be used
# in the logger and/or the save file, or something.
###import#########################################################################

import sys
import time

import numpy as np

import project.project_globals as g
import project.classes as pc
scan_thread = g.scan_thread.read()

from PyQt4 import QtCore, QtGui
app = g.app.read()

import project.widgets as custom_widgets

###import hardware control#######################################################

import spectrometers.spectrometers as spec
MicroHR = spec.hardwares[0]
import delays.delays as delay
D1 = delay.hardwares[0]
D2 = delay.hardwares[1]
D3 = None
import opas.opas as opa
OPA1 = None
OPA2 = opa.hardwares[0]
OPA3 = None
# import nds.nds as nd
ND1 = None
ND2 = None
ND3 = None
import daq.daq as daq
import daq.current as daq_current

###scan globals##################################################################

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

### Scan Perameters (to be replaced by GUI)####################################

hard_axis = [[D1],[D2]]
unit_list = [['ps'],['ps']]
a = pc.NumberLimits(min_value=-10000, max_value=10000)
limits = [[a],[a]]
snake = False
start_a = [] # Start position array
stop_a = [] # Stop position array
num_a = [] # Number of points to take for each axis
pos_a = [] # N x hardwares x dimentions aray with values for each point

for i in range(len(hard_axis)):
    start_a.append([])
    stop_a.append([])
    pos_a.append([])
    num_a.append(pc.Number(initial_value=3, decimals=0))
    for j in len(hard_axis[i]):
        start_a[i].append(pc.Number(initial_value=-5, units=unit_list[i][j], limits=limits[i][j]))
        stop_a[i].append(pc.Number(initial_value=5, units=unit_list[i][j], limits=limits[i][j]))
        pos_a[i].append(np.linspace(start_a[i][j].read(unit_list[i][j]), stop_a[j].read(unit_list[i][j]), num_a[i].read()))


Scan_dic = {'Hardwares':hard_axis, 'Units':unit_list,
            'Limits':limits,'Start':start_a,'Stop':stop_a,'Num Points':num_a,
            'Positions':pos_a,'Snake':snake,'Description':'Two-D Delay Scan'}

### scan object ###############################################################

class scan(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    @QtCore.pyqtSlot(list)

    def recursive_scan(self, Dim_index=0):
        if self.cont:
            if Dim_index < self.Dim.size:
                for pnt_index in range(self.npts[Dim_index]):
                    for hdw_index in range(self.Dim[Dim_index]):
                        self.hdws[Dim_index][hdw_index].set_position(self.pos[Dim_index][hdw_index][pnt_index],
                                                                     unit_list[Dim_index][hdw_index])
                    self.recursive_scan(Dim_index+1)
            # Put all tasks that should be done between instrument moves here.
            else:
                # wait for all hardware
                g.hardware_waits.wait()
                # read from daq
                daq.control.acquire()
                daq.control.wait_until_daq_done()
                # update
                self.idx += 1
                fraction_complete.write(float(self.idx)/float(self.npts))
                self.update_ui.emit()
                if not self.check_continue():
                    self.cont = False

    def ndindex_scan(self):
        '''
        This could work, but I think it isn't necessary.

        At any rate, my solution works.
        '''

    def run(self, inputs):
        self.cont = True
        self.idx = 0
        ### unpack inputs

        #scan_dictionary = inputs[0]
        self.sd = Scan_dic
        self.npts = np.array(self.sd['Num Points'])
        self.pos = np.array(self.sd['Positions'])
        self.hdws = np.array(np.array(B) for B in self.sd['Hardwares'])
        self.Dim =        [L.size for L in self.hdws]
        self.total_pts =         sum([M.size for M in self.npts])
        self.snake = self.sd['Snake']
        self.scan_description = self.sd['Description']

        ### Insert getting values from the Scan Dictionary here

        daq_widget = inputs[1]

        ### startup

        g.module_control.write(True)
        going.write(True)
        fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', self.scan_description)

        ### scan

        # initialize scan in daq
        daq.control.initialize_scan(daq_widget, fit=True)
        daq_current.gui.set_xlim(self.pos[self.Dim.size-1][0].min(), self.pos[self.Dim.size-1][0].max())

        ### do loop
        self.idx = 0

        self.recursive_scan()

        # What does this do and where does it go?
        daq.control.fit('MicroHR', 'vai0 Mean')


        ### end

        print 'end'
        fraction_complete.write(1.)
        going.write(False)
        g.module_control.write(False)
        g.logger.log('info', 'Scan done', self.scan_description)
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

        # input table one
        input_table = custom_widgets.InputTable()
        input_table.add('Initial', start_d)
        input_table.add('Final', stop_d)
        input_table.add('Number', num_d)
        layout.addWidget(input_table)

        # daq widget
        self.daq_widget = daq.Widget()
        layout.addWidget(self.daq_widget)

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
        g.module_combobox.add_module('N-D Scan', self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)

        my_widget = QtGui.QLineEdit('this is a placeholder widget produced by N-D Scan')
        my_widget.setAutoFillBackground(True)
        layout.addWidget(my_widget)

        self.advanced_frame = QtGui.QWidget()
        self.advanced_frame.setLayout(layout)

        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == 'N-D Scan':
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
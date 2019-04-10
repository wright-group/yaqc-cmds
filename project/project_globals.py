import sys
import time

from PyQt4 import QtGui, QtCore

### global classes ############################################################

class SimpleGlobal:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value

class GlobalWithIni():
    def __init__(self, ini, section, option):
        self.ini = ini
        self.section = section
        self.option = option
        self.get_saved()
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
    def get_saved(self):
        self.value = self.ini.read(self.section, self.option)
        return self.value
    def save(self, value = None):
        if not value == None: self.value = value
        self.ini.write(self.section, self.option, self.value)

### order sensitive globals  ##################################################

class main_dir:
    def __init__(self):
        import os
        self.value = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, self.value)
    def read(self):
        return self.value
    def write(self, value):
        self.value = str(value)
main_dir = main_dir()

import project.ini_handler as ini #must come after main_dir has been defined

debug = GlobalWithIni(ini.config, 'main', 'debug')

class PollTimer:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
    def connect_to_timeout(self, slot):
        QtGui.QAction.connect(self.value, QtCore.SIGNAL("timeout()"), slot)
poll_timer = PollTimer()
slack_poll_timer = PollTimer()

class logger: #must come before other globals
    def __init__(self):
        pass
    def load(self):
        import project.logging_handler as logging_handler
        self.value = logging_handler.log
        if debug.read(): self.log('info', 'Debug', 'PyCMDS is in debug mode')
        if offline.read(): self.log('info', 'Offline', 'PyCMDS is offline')
    def log(self, level, name, message = '', origin = 'name'):
        '''
        wrapper of logging method for PyCMDS

        accepts strings

        levels: debug, info, warning, error, critical
        '''
        self.value(level, name, message, origin)
logger = logger()

### other globals #############################################################
#alphabetical

app = SimpleGlobal()

colors_dict = SimpleGlobal()

coset_control = SimpleGlobal()

coset_widget = SimpleGlobal()

class daq_widget:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
daq_widget = daq_widget()

class daq_array_widget:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
daq_array_widget = daq_array_widget()

class daq_plot_widget:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
daq_plot_widget = daq_plot_widget()

hardware_advanced_box = SimpleGlobal()

hardware_initialized = SimpleGlobal()
hardware_initialized.write(False)

google_drive_control = SimpleGlobal()

google_drive_enabled = SimpleGlobal()

class hardware_waits:
    def __init__(self):
        '''
        holds value, a list of hardware wait_until_still methods
        '''
        self.value = []
    def add(self, method):
        self.value.append(method)
    def give_coset_control(self, control):
        self.coset_control = control
    def wait(self, coset=True):
        if coset:
            self.coset_control.launch()
        for method in self.value:
            method()
hardware_waits = hardware_waits()

class hardware_widget:
    def __init__(self):
        self.value = None
        self.number_of_widgets = 0
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
        self.value.setLayout(QtGui.QVBoxLayout())
        self.value.layout().setMargin(5)
        self.value.layout().addStretch(1)
    def add_to(self, widget):
        self.value.layout().takeAt(self.number_of_widgets)
        self.value.layout().addWidget(widget)
        self.number_of_widgets += 1
        self.value.layout().addStretch(1)
hardware_widget = hardware_widget()

class main_thread:
    def __init__(self):
        self.value = QtCore.QThread.currentThread()
    def read(self):
        return self.value
    def write(self, value):
        self.value = str(value)
main_thread = main_thread()

class main_window:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
main_window = main_window()

class module_advanced_widget:
    def __init__(self):
        self.value = None
        self.child = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
    def add_child(self, widget):
        self.value.setLayout(QtGui.QVBoxLayout())
        self.child = widget
        self.value.layout().setMargin(0)
        self.value.layout().addWidget(self.child)
module_advanced_widget = module_advanced_widget()

class QueueControl(QtCore.QObject):
    def __init__(self):
        self.value = None
        self.widgets_to_disable = []
    def read(self):
        return self.value
    def write(self, value):
        for widget in self.widgets_to_disable:
            try:
                widget.setDisabled(value)
            except RuntimeError:
                # widget has been deleted, probably
                self.widgets_to_disable.remove(widget)
        self.value = value
        main_window.read().queue_control.emit()
    def disable_when_true(self, widget):
        self.widgets_to_disable.append(widget)
queue_control = QueueControl()

offline = GlobalWithIni(ini.config, 'main', 'offline')

class progress_bar:
    def __init__(self):
        self.value = None
    def write(self, value):
        self.value = value
    def give_time_display_elements(self, time_elapsed, time_remaining):
        self.time_elapsed = time_elapsed
        self.time_remaining = time_remaining
    def begin_new_scan_timer(self):
        self.start_time = time.time()
    def set_fraction(self, fraction):
        self.value.setValue(fraction*100)
        #time elapsed
        time_elapsed = time.time() - self.start_time
        m, s = divmod(time_elapsed, 60)
        h, m = divmod(m, 60)
        self.time_elapsed.setText('%02d:%02d:%02d' % (h, m, s))
        #time remaining
        if fraction == 0:
            self.time_remaining.setText('??:??:??')
        else:
            time_remaining = (time_elapsed / fraction) - time_elapsed
            m, s = divmod(time_remaining, 60)
            h, m = divmod(m, 60)
            self.time_remaining.setText('%02d:%02d:%02d' % (h, m, s))
progress_bar = progress_bar()

class scan_thread:
    def __init__(self):
        self.value = None
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
scan_thread = scan_thread()

class shutdown:
    '''
    holds the reference of MainWindow.shutdown Qt signal

    during startup, add your shutdown method to this object using the 'add_method' method it will be called upon shutdown.
    your method must not have any arguments
    '''
    def __init__(self):
        self.value = False
        self.methods = []
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
    def add_method(self, method):
        self.methods.append(method)
    def fire(self):
        for method in self.methods:
            method()
        main_window.read().close()
shutdown = shutdown()

slack_control = SimpleGlobal()

slack_enabled = SimpleGlobal()

system_name = GlobalWithIni(ini.config, 'main', 'system name')

class UseArray:
    def __init__(self):
        self.value = False
    def read(self):
        return self.value
    def write(self, value):
        self.value = value
use_array = UseArray()

version = SimpleGlobal()

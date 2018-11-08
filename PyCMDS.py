#! /usr/bin/env python
### ensure folders exist ######################################################


import os

folders = []
folders.append(['data'])
folders.append(['logs'])
folders.append(['autonomic', 'files'])
folders.append(['hardware', 'opas', 'OPA-800', 'OPA2 curves'])
folders.append(['hardware', 'opas', 'OPA-800', 'OPA3 curves'])
folders.append(['hardware', 'opas', 'TOPAS', 'OPA1 (10743) curves'])
folders.append(['hardware', 'opas', 'TOPAS', 'OPA2 (10742) curves'])
folders.append(['hardware', 'opas', 'TOPAS', 'configuration'])

for folder in folders:
    folder_path = os.path.join(os.getcwd(), *folder)
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)


# TODO: create config.ini if none exists


#### import ###################################################################
#BEWARE OF CHANGING ORDER OF IMPORTS!!!!!!!!!


import sys
import imp
import copy
import glob
import inspect
import subprocess

import matplotlib
matplotlib.use('ps')  # important - images will be generated in worker threads

from PyQt4 import QtGui, QtCore

import project.project_globals as g
app = QtGui.QApplication(sys.argv)
g.app.write(app)
g.logger.load()
import project.ini_handler as ini
g.logger.log('info', 'Startup', 'PyCMDS is attempting startup')

import project.style as style
import project.widgets as pw
import project.classes as pc
import project.file_dialog_handler

from hardware.hardware import all_initialized

import WrightTools as wt


### define ####################################################################


directory = os.path.abspath(os.path.dirname(__file__))


### version information #######################################################


# MAJOR.MINOR.PATCH (semantic versioning)
# major version changes may break backwards compatibility
__version__ = '0.9.0'

# add git branch, if appropriate
p = os.path.join(directory, '.git', 'HEAD')
if os.path.isfile(p):
    with open(p) as _f:
        __branch__ = _f.readline().rstrip().split(r'/')[-1]
    if __branch__ != 'master':
        __version__ += '-' + __branch__
else:
    __branch__ = None

g.version.write(__version__)


### main window ###############################################################


class MainWindow(QtGui.QMainWindow):
    shutdown = QtCore.pyqtSignal()
    queue_control = QtCore.pyqtSignal()
    
    def __init__(self):
        QtGui.QMainWindow.__init__(self, parent=None)
        g.main_window.write(self)
        g.shutdown.write(self.shutdown)
        self.setWindowTitle('PyCMDS %s'%__version__)
        # begin poll timer
        self._begin_poll_loop()
        # disable 'x'
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        # set size, position
        self.window_verti_size = 600
        self.window_horiz_size = 1000
        self.setGeometry(0,0, self.window_horiz_size, self.window_verti_size)
        self._center()
        self.resize(self.window_horiz_size, self.window_verti_size)
        self._create_main_frame()
        # initialize program
        self._initialize_hardware()
        self._initialize_widgets()
        # open internet things
        self._load_google_drive()
        self._load_witch()
        # populate self
        self.data_folder = os.path.join(directory, 'data')
        # somatic system
        from somatic import queue
        self.queue_gui = queue.GUI(self.queue_widget, self.queue_message)
        self.queue_gui.load_modules()
        # log completion
        if g.debug.read():
            print('PyCMDS_ui.MainWindow.__init__ complete')
        g.logger.log('info', 'Startup', 'PyCMDS MainWindow __init__ finished')
        all_initialized()
        
    
    def _create_main_frame(self):
        self.main_frame = QtGui.QWidget()
        hbox = QtGui.QHBoxLayout()  
        # hardware ------------------------------------------------------------
        hardware_box = QtGui.QVBoxLayout()
        # exit button
        exit_button = pw.Shutdown_button()
        exit_button.setMinimumWidth(300)
        exit_button.setMinimumHeight(30)
        exit_button.shutdown_go.connect(self._shutdown)
        hardware_box.addWidget(exit_button)
        g.queue_control.disable_when_true(exit_button)
        # hardware container widget
        hardware_widget = QtGui.QWidget()
        g.hardware_widget.write(hardware_widget)
        # hardware scroll area
        hardware_scroll_area = pw.scroll_area()
        hardware_scroll_area.setWidget(hardware_widget)
        hardware_box.addWidget(hardware_scroll_area)
        hbox.addLayout(hardware_box)
        # box -----------------------------------------------------------------
        box = QtGui.QVBoxLayout()
        box.setMargin(0)
        # module progress bar
        progress_bar = QtGui.QProgressBar()
        progress_bar.setTextVisible(False)
        g.progress_bar.write(progress_bar)
        box.addWidget(progress_bar)
        # time elapsed/remaining, queue message
        progress_bar.setLayout(QtGui.QHBoxLayout())
        time_elapsed = QtGui.QLabel('00:00:00')
        self.queue_message = QtGui.QLabel('NO QUEUE')
        time_remaining = QtGui.QLabel('00:00:00')
        StyleSheet = 'QLabel{color: custom_color; font: bold 14px}'.replace('custom_color', g.colors_dict.read()['text_light'])
        time_elapsed.setStyleSheet(StyleSheet)
        self.queue_message.setStyleSheet(StyleSheet)
        time_remaining.setStyleSheet(StyleSheet)
        progress_bar.layout().addWidget(time_elapsed)
        progress_bar.layout().addStretch(1)
        progress_bar.layout().addWidget(self.queue_message)
        progress_bar.layout().addStretch(1)
        progress_bar.layout().addWidget(time_remaining)
        g.progress_bar.give_time_display_elements(time_elapsed, time_remaining)
        # program box
        program_widget = QtGui.QWidget()
        # hardware box
        hardware_advanced_widget = QtGui.QWidget()
        hardware_advanced_box = QtGui.QVBoxLayout()
        hardware_advanced_box.setContentsMargins(0, 10, 0, 0)
        hardware_advanced_widget.setLayout(hardware_advanced_box)
        g.hardware_advanced_box.write(hardware_advanced_box)
        # device box
        device_widget = QtGui.QWidget()
        g.daq_widget.write(device_widget)
        # autonomic box
        coset_widget = QtGui.QWidget()
        g.coset_widget.write(coset_widget)
        # sonomic box
        somatic_widget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        somatic_widget.setLayout(layout)
        somatic_tabs = pw.TabWidget()
        self.queue_widget = QtGui.QWidget()
        somatic_tabs.addTab(self.queue_widget, 'Queue')
        self.scan_widget = QtGui.QWidget()
        somatic_tabs.addTab(self.scan_widget, 'Scan')
        somatic_tabs.setContentsMargins(0., 0., 0., 0.)
        layout.addWidget(somatic_tabs)
        # plot box
        plot_widget = QtGui.QWidget()
        g.daq_plot_widget.write(plot_widget)
        # tab widget
        self.tabs = pw.TabWidget()
        self.tabs.addTab(program_widget, 'Program')
        self.tabs.addTab(hardware_advanced_widget, 'Hardware')
        self.tabs.addTab(device_widget, 'Devices')
        self.tabs.addTab(coset_widget, 'Autonomic')
        self.tabs.addTab(somatic_widget, 'Somatic')
        self.tabs.addTab(plot_widget, 'Plot')
        self.tabs.setCurrentIndex(4)  # start on sonomic tab
        self.tabs.setContentsMargins(0., 0., 0., 0.)
        box.addWidget(self.tabs)    
        # vertical stretch
        box.addStretch(1)
        hbox.addLayout(box)
        # frame ---------------------------------------------------------------
        hbox.setStretchFactor(box, 100)
        hbox.setGeometry(QtCore.QRect(300, 300, 300, 300))
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)

    def _begin_poll_loop(self):
        # polling is done by a q timer
        timer = QtCore.QTimer()
        timer.start(10000)  # milliseconds
        self.shutdown.connect(timer.stop)
        g.poll_timer.write(timer)
        # connect MainWindow poll method to pool timeout
        g.poll_timer.connect_to_timeout(self.poll)
        # now we can begin the CPU watcher (which is triggered by poll)
        import project.logging_handler as logging_handler
        logging_handler.begin_cpu_watcher()
        
    def poll(self):
        pass

    def _initialize_hardware(self):
        g.offline.get_saved()
        if g.debug.read():
            print('initialize hardware')
        # import
        import hardware
        import hardware.opas.opas
        import hardware.spectrometers.spectrometers
        import hardware.delays.delays
        import hardware.filters.filters
        import devices.devices
    
    def _initialize_widgets(self):
        if g.debug.read():
            print('initialize widgets')
        # import widgets
        import autonomic.coset
                
    def _load_google_drive(self):
        google_drive_ini = ini.Ini(os.path.join(g.main_dir.read(), 'project', 'google_drive', 'google_drive.ini'))
        g.google_drive_enabled.write(google_drive_ini.read('main', 'enable'))
        if g.google_drive_enabled.read():
            import project.google_drive.google_drive as google_drive
                
    def _load_witch(self):
        # check if witch is enabled
        bots_ini = ini.Ini(os.path.join(g.main_dir.read(), 'project', 'slack', 'bots.ini'))
        g.slack_enabled.write(bots_ini.read('bots', 'enable'))
        if g.slack_enabled.read():
            import project.slack as slack
            # create witch
            self.witch = slack.control
            # begin poll timer
            timer = QtCore.QTimer()
            timer.start(500)  # milliseconds
            self.shutdown.connect(timer.stop)
            g.slack_poll_timer.write(timer)
            g.slack_poll_timer.connect_to_timeout(self.witch.poll)
        
    def _shutdown(self):
        '''
        attempt a clean shutdown
        '''
        if g.debug.read():
            print('shutdown')
        g.logger.log('info', 'Shutdown', 'PyCMDS is attempting shutdown')
        self.shutdown.emit()
        g.shutdown.fire()
        
    def _center(self):
        # a function which ensures that the window appears in the center of the screen at startup
        screen = QtGui.QDesktopWidget().screenGeometry() 
        size = self.geometry() 
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
    def get_status(self):
        # called by slack
        return self.queue_gui.get_status()

def main():
    global MainWindow
    MainWindow = MainWindow()
    style.set_style()
    MainWindow.show()
    MainWindow.showMaximized()
    app.exec_()
    return MainWindow
main_form = main()

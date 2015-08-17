#to do##########################################################################

#[ ] error event handling

#import#########################################################################
#BEWARE OF CHANGING ORDER OF IMPORTS!!!!!!!!!

import os
import sys
import imp
import copy
import glob
import inspect
import subprocess

from PyQt4 import QtGui, QtCore

import project.project_globals as g
app = QtGui.QApplication(sys.argv)
g.app.write(app)
g.logger.load()
import project.ini_handler as ini
g.logger.log('info', 'Startup', 'PyCMDS is attempting startup')


import project.style as style
import project.widgets as custom_widgets

#main window####################################################################

class MainWindow(QtGui.QMainWindow):
    shutdown = QtCore.pyqtSignal()
    module_control = QtCore.pyqtSignal()
    
    def __init__(self):
        
        QtGui.QMainWindow.__init__(self, parent=None)
        
        g.main_window.write(self)
        g.shutdown.write(self.shutdown)
        
        self.setWindowTitle('Coherent Multidimensional Spectroscopy | Python')

        self._begin_poll_loop()

        #disable 'x'
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

        self.window_verti_size = 600
        self.window_horiz_size = 1000
        self.setGeometry(0,0, self.window_horiz_size, self.window_verti_size)
        self._center()
        self.resize(self.window_horiz_size, self.window_verti_size)
        self._create_main_frame()
        
        self._initialize_hardware()
        self._load_modules()
        
        #log completion
        if g.debug.read(): print 'PyCMDS_ui.MainWindow.__init__ complete'
        g.logger.log('info', 'Startup', 'PyCMDS MainWindow __init__ finished')
    
    def _create_main_frame(self):
        
        self.main_frame = QtGui.QWidget()
        
        #module-----------------------------------------------------------------

        module_box = QtGui.QVBoxLayout()
        
        #module combobox
        module_combobox = custom_widgets.module_combobox()
        module_combobox.setMinimumWidth(300)
        module_combobox.setMinimumHeight(30)
        g.module_combobox.write(module_combobox)
        module_box.addWidget(module_combobox)
        g.module_control.disable_when_true(module_combobox)
        
        #module container widget
        module_widget = QtGui.QWidget()
        g.module_widget.write(module_widget)
        
        #module scroll area
        module_scroll_area = custom_widgets.scroll_area()
        module_scroll_area.setWidget(module_widget)
        module_box.addWidget(module_scroll_area)    
        
        #hardware---------------------------------------------------------------

        hardware_box = QtGui.QVBoxLayout()
        
        #exit button
        exit_button = custom_widgets.Shutdown_button()
        exit_button.setMinimumWidth(300)
        exit_button.setMinimumHeight(30)
        exit_button.shutdown_go.connect(self._shutdown)
        hardware_box.addWidget(exit_button)
        g.module_control.disable_when_true(exit_button)
        
        #hardware container widget
        hardware_widget = QtGui.QWidget()
        g.hardware_widget.write(hardware_widget)
    
        #hardware scroll area
        hardware_scroll_area = custom_widgets.scroll_area()
        hardware_scroll_area.setWidget(hardware_widget)
        hardware_box.addWidget(hardware_scroll_area)        

        # daq -----------------------------------------------------------------
        
        daq_box = QtGui.QVBoxLayout()
        daq_box.setMargin(0)
        
        #module progress bar
        progress_bar = QtGui.QProgressBar()
        progress_bar.setTextVisible(False)
        g.progress_bar.write(progress_bar)
        daq_box.addWidget(progress_bar)
        
        #time elapsed/remaining
        progress_bar.setLayout(QtGui.QHBoxLayout())
        time_elapsed = QtGui.QLabel('00:00:00')
        time_remaining = QtGui.QLabel('00:00:00')
        StyleSheet = 'QLabel{color: custom_color; font: bold 14px}'.replace('custom_color', g.colors_dict.read()['text_light'])
        time_elapsed.setStyleSheet(StyleSheet)
        time_remaining.setStyleSheet(StyleSheet)
        progress_bar.layout().addWidget(time_elapsed)
        progress_bar.layout().addStretch(1)
        progress_bar.layout().addWidget(time_remaining)
        g.progress_bar.give_time_display_elements(time_elapsed, time_remaining)
        
        #create widgets
        hardware_advanced_widget = QtGui.QWidget()
        hardware_advanced_box = QtGui.QVBoxLayout()
        hardware_advanced_box.setContentsMargins(0, 10, 0, 0)
        hardware_advanced_widget.setLayout(hardware_advanced_box)
        g.hardware_advanced_box.write(hardware_advanced_box)
        comove_widget = QtGui.QWidget()
        module_advanced_widget = QtGui.QWidget()
        g.module_advanced_widget.write(module_advanced_widget)
        daq_single_widget = QtGui.QWidget()
        g.daq_widget.write(daq_single_widget)
        current_slice_widget = QtGui.QWidget()
        g.current_slice_widget.write(current_slice_widget)
        daq_plot_widget = QtGui.QWidget()
        g.daq_plot_widget.write(daq_plot_widget)
        
        #tab widget
        daq_tabs = QtGui.QTabWidget()
        daq_tabs.addTab(hardware_advanced_widget, 'Hardware')
        daq_tabs.addTab(comove_widget, 'Comove')
        daq_tabs.addTab(module_advanced_widget, 'Module')
        daq_tabs.addTab(daq_single_widget, 'DAQ')
        daq_tabs.addTab(current_slice_widget, 'Current')
        daq_tabs.addTab(daq_plot_widget, 'Plot')
        daq_tabs.setCurrentIndex(3) #start on DAQ tab
        daq_tabs.setContentsMargins(0., 0., 0., 0.)
        daq_box.addWidget(daq_tabs)    
        
        #vertical stretch
        daq_box.addStretch(1)
        
        # frame ---------------------------------------------------------------

        hbox = QtGui.QHBoxLayout()
        
        hbox.addLayout(module_box)
        hbox.addLayout(hardware_box)
        hbox.addLayout(daq_box)
        
        hbox.setStretchFactor(daq_box, 100)
        
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
        if g.debug.read(): print 'initialize hardware'
        
        # import
        import opas.opas
        import spectrometers.spectrometers
        import delays.delays
        import daq.daq
        
        #self.daq = daq.daq
    
    def _load_modules(self):
        
        g.module_control.write(False)
        
        if g.debug.read(): print 'load modules'
        
        g.module_combobox.read()
        
        #create scan thread-----------------------------------------------------
        
        scan_thread = QtCore.QThread()
        g.scan_thread.write(scan_thread)
        scan_thread.start()
        
        #import modules---------------------------------------------------------
        
        import modules.template
        import modules.custom
        
    def _shutdown(self):
        '''
        attempt a clean shutdown
        '''
        if g.debug.read(): print 'shutdown'
        g.logger.log('info', 'Shutdown', 'PyCMDS is attempting shutdown')
        #g.shutdown.write(True)
        self.shutdown.emit()
        g.shutdown.fire()
        
    def _center(self):
        #a function which ensures that the window appears in the center of the screen at startup
        
        screen = QtGui.QDesktopWidget().screenGeometry() 
        size = self.geometry() 
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
    
def main():
    global MainWindow
    MainWindow = MainWindow()
    style.set_style()
    MainWindow.show()
    MainWindow.showMaximized()
    app.exec_()
    return MainWindow
main_form = main()
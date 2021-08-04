#! /usr/bin/env python
### ensure folders exist ######################################################

import matplotlib

matplotlib.use("ps")  # important - images will be generated in worker threads

import sys
from PySide2 import QtWidgets, QtCore

app = QtWidgets.QApplication(sys.argv)

import pathlib


#### import ###################################################################
# BEWARE OF CHANGING ORDER OF IMPORTS!!!!!!!!!

from .project import project_globals as g

g.app.write(app)
g.logger.load()

g.logger.log("info", "Startup", "Yaqc_cmds is attempting startup")

from .project import widgets as pw

from .hardware.hardware import all_initialized


### version information #######################################################

from .__version__ import __version__


### main window ###############################################################


class MainWindow(QtWidgets.QMainWindow):
    shutdown = QtCore.Signal()
    queue_control = QtCore.Signal()

    def __init__(self, config):
        QtWidgets.QMainWindow.__init__(self, parent=None)
        self.config = config
        g.system_name.write(self.config["system_name"])
        g.main_window.write(self)
        g.shutdown.write(self.shutdown)
        self.setWindowTitle("yaqc-cmds %s" % __version__)
        # disable 'x'
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        # set size, position
        self.window_verti_size = 600
        self.window_horiz_size = 1000
        self.setGeometry(0, 0, self.window_horiz_size, self.window_verti_size)
        # self._center()
        self.resize(self.window_horiz_size, self.window_verti_size)
        self._create_main_frame()
        # initialize program
        self._initialize_hardware()
        self._initialize_widgets()
        # populate self
        self.data_folder = pathlib.Path.home() / "yaqc-cmds-data"
        self.data_folder.mkdir(exist_ok=True)
        # somatic system
        from yaqc_cmds.somatic import queue

        self.queue_gui = queue.GUI(self.queue_widget, self.queue_message)
        # self.queue_gui.load_modules()
        # log completion
        if g.debug.read():
            print("Yaqc_cmds_ui.MainWindow.__init__ complete")
        g.logger.log("info", "Startup", "Yaqc_cmds MainWindow __init__ finished")
        all_initialized()

    def _create_main_frame(self):
        self.main_frame = QtWidgets.QWidget(parent=self)
        hbox = QtWidgets.QHBoxLayout()
        # hardware ------------------------------------------------------------
        hardware_box = QtWidgets.QVBoxLayout()
        # exit button
        exit_button = pw.Shutdown_button()
        exit_button.setMinimumWidth(300)
        exit_button.setMinimumHeight(30)
        exit_button.shutdown_go.connect(self._shutdown)
        hardware_box.addWidget(exit_button)
        g.queue_control.disable_when_true(exit_button)
        # hardware container widget
        hardware_widget = QtWidgets.QWidget(parent=self.main_frame)
        g.hardware_widget.write(hardware_widget)
        # hardware scroll area
        hardware_scroll_area = pw.scroll_area()
        hardware_scroll_area.setWidget(hardware_widget)
        hardware_box.addWidget(hardware_scroll_area)
        hbox.addLayout(hardware_box)
        # box -----------------------------------------------------------------
        box = QtWidgets.QVBoxLayout()
        box.setMargin(0)
        # module progress bar
        progress_bar = QtWidgets.QProgressBar()
        progress_bar.setTextVisible(False)
        g.progress_bar.write(progress_bar)
        box.addWidget(progress_bar)
        # time elapsed/remaining, queue message
        progress_bar.setLayout(QtWidgets.QHBoxLayout())
        time_elapsed = QtWidgets.QLabel("00:00:00")
        self.queue_message = QtWidgets.QLabel("")
        time_remaining = QtWidgets.QLabel("00:00:00")
        StyleSheet = "QLabel{color: custom_color; font: bold 14px}".replace(
            "custom_color", g.colors_dict.read()["text_light"]
        )
        time_elapsed.setStyleSheet(StyleSheet)
        self.queue_message.setStyleSheet(StyleSheet)
        time_remaining.setStyleSheet(StyleSheet)
        progress_bar.layout().addWidget(time_elapsed)
        progress_bar.layout().addStretch(1)
        progress_bar.layout().addWidget(self.queue_message)
        progress_bar.layout().addStretch(1)
        progress_bar.layout().addWidget(time_remaining)
        g.progress_bar.give_time_display_elements(time_elapsed, time_remaining)
        # hardware box
        hardware_advanced_widget = QtWidgets.QWidget(parent=self.main_frame)
        hardware_advanced_box = QtWidgets.QVBoxLayout()
        hardware_advanced_box.setContentsMargins(0, 10, 0, 0)
        hardware_advanced_widget.setLayout(hardware_advanced_box)
        g.hardware_advanced_box.write(hardware_advanced_box)
        self.hardware_advanced_box = hardware_advanced_box
        # autonomic box
        coset_widget = QtWidgets.QWidget(parent=self.main_frame)
        g.coset_widget.write(coset_widget)
        # sonomic box
        self.queue_widget = QtWidgets.QWidget(parent=self.main_frame)
        # plot box
        self.plot_widget = QtWidgets.QWidget(parent=self.main_frame)
        # tab widget
        self.tabs = pw.TabWidget()
        self.tabs.addTab(hardware_advanced_widget, "Hardware")
        self.tabs.addTab(coset_widget, "Autonomic")
        self.tabs.addTab(self.queue_widget, "Queue")
        self.tabs.addTab(self.plot_widget, "Plot")
        self.tabs.setCurrentIndex(2)  # start on queue tab
        self.tabs.setContentsMargins(0.0, 0.0, 0.0, 0.0)
        box.addWidget(self.tabs)
        # vertical stretch
        box.addStretch(1)
        hbox.addLayout(box)
        # frame ---------------------------------------------------------------
        hbox.setStretchFactor(box, 100)
        hbox.setGeometry(QtCore.QRect(300, 300, 300, 300))
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)

    def _initialize_hardware(self):
        if g.debug.read():
            print("initialize hardware")
        from . import hardware

    def _initialize_widgets(self):
        if g.debug.read():
            print("initialize widgets")
        # import widgets
        import yaqc_cmds.autonomic.coset

        import yaqc_cmds._plot

    def _shutdown(self):
        """
        attempt a clean shutdown
        """
        if g.debug.read():
            print("shutdown")
        g.logger.log("info", "Shutdown", "Yaqc_cmds is attempting shutdown")
        self.shutdown.emit()
        g.shutdown.fire()

    def _center(self):
        # a function which ensures that the window appears in the center of the screen at startup
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2)

    def get_status(self, full=False):
        return self.queue_gui.get_status(full)

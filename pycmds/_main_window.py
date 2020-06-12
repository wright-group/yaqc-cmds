#! /usr/bin/env python
### ensure folders exist ######################################################
from .__version__ import __version__

import matplotlib

matplotlib.use("ps")  # important - images will be generated in worker threads

import sys

import pathlib
from PySide2 import QtWidgets, QtCore

folders = []
folders.append("data")
folders.append("logs")
folders.append("autonomic/files")

for folder in folders:
    folder_path =  pathlib.Path.home() / "pycmds" / folder
    folder_path.mkdir(exist_ok=True, parents=True)


#### import ###################################################################
# BEWARE OF CHANGING ORDER OF IMPORTS!!!!!!!!!


from .project import project_globals as g

g.logger.load()
g.logger.log("info", "Startup", "PyCMDS is attempting startup")

from .project import style as style
from .project import widgets as pw
from .project import classes as pc
from .project import file_dialog_handler

from .hardware import initialize_hardwares

import yaqc


### define ####################################################################


directory = pathlib.Path(__file__).resolve().parent.parent


### main window ###############################################################


class MainWindow(QtWidgets.QMainWindow):
    shutdown = QtCore.Signal()
    queue_control = QtCore.Signal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, parent=None)
        g.main_window.write(self)
        g.shutdown.write(self.shutdown)
        self.setWindowTitle("PyCMDS %s" % __version__)
        # begin poll timer
        self._begin_poll_loop()
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
        # open internet things
        # self._load_google_drive()
        # self._load_witch()
        # populate self
        self.data_folder = pathlib.Path.home()/"pycmds"/ "data"
        # somatic system
        from .somatic import queue

        self.queue_gui = queue.GUI(self.queue_widget, self.queue_message)
        self.queue_gui.load_modules()
        # log completion
        print("PyCMDS_ui.MainWindow.__init__ complete")
        g.logger.log("info", "Startup", "PyCMDS MainWindow __init__ finished")

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
        self.queue_message = QtWidgets.QLabel("NO QUEUE")
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
        # program box
        program_widget = QtWidgets.QWidget(parent=self.main_frame)
        # hardware box
        hardware_advanced_widget = QtWidgets.QWidget(parent=self.main_frame)
        hardware_advanced_box = QtWidgets.QVBoxLayout()
        hardware_advanced_box.setContentsMargins(0, 10, 0, 0)
        hardware_advanced_widget.setLayout(hardware_advanced_box)
        g.hardware_advanced_box.write(hardware_advanced_box)
        self.hardware_advanced_box = hardware_advanced_box
        # device box
        device_widget = QtWidgets.QWidget(parent=self.main_frame)
        g.daq_widget.write(device_widget)
        # autonomic box
        coset_widget = QtWidgets.QWidget(parent=self.main_frame)
        g.coset_widget.write(coset_widget)
        # sonomic box
        somatic_widget = QtWidgets.QWidget(parent=self.main_frame)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        somatic_widget.setLayout(layout)
        somatic_tabs = pw.TabWidget()
        self.queue_widget = QtWidgets.QWidget(parent=self.main_frame)
        somatic_tabs.addTab(self.queue_widget, "Queue")
        self.scan_widget = QtWidgets.QWidget(parent=self.main_frame)
        somatic_tabs.addTab(self.scan_widget, "Scan")
        somatic_tabs.setContentsMargins(0.0, 0.0, 0.0, 0.0)
        layout.addWidget(somatic_tabs)
        # plot box
        plot_widget = QtWidgets.QWidget(parent=self.main_frame)
        g.daq_plot_widget.write(plot_widget)
        # tab widget
        self.tabs = pw.TabWidget()
        self.tabs.addTab(program_widget, "Program")
        self.tabs.addTab(hardware_advanced_widget, "Hardware")
        self.tabs.addTab(device_widget, "Devices")
        self.tabs.addTab(coset_widget, "Autonomic")
        self.tabs.addTab(somatic_widget, "Somatic")
        self.tabs.addTab(plot_widget, "Plot")
        self.tabs.setCurrentIndex(4)  # start on sonomic tab
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

    def _begin_poll_loop(self):
        # polling is done by a q timer
        timer = QtCore.QTimer()
        timer.start(10000)  # milliseconds
        self.shutdown.connect(timer.stop)
        g.poll_timer.write(timer)
        # connect MainWindow poll method to pool timeout
        g.poll_timer.connect_to_timeout(self.poll)
        # now we can begin the CPU watcher (which is triggered by poll)
        from .project import logging_handler as logging_handler

        logging_handler.begin_cpu_watcher()

    def poll(self):
        pass

    def _initialize_hardware(self):
        print("initialize hardware")
        # import
        initialize_hardwares()
        from .devices import devices

    def _initialize_widgets(self):
        print("initialize widgets")
        # import widgets
        from .autonomic import coset

    def _load_google_drive(self):
        raise NotImplementedError
        google_drive_config = toml.loads(appdirs.user_config_dir("pycmds", "pycmds") + "/config.toml").get()
        g.google_drive_enabled.write(google_drive_ini.read("main", "enable"))
        if g.google_drive_enabled.read():
            g.google_drive_control.write(yaqc.Client(google_drive_ini.read("main", "port")))

    def _load_witch(self):
        raise NotImplementedError
        # check if witch is enabled
        bots_ini = ini.Ini(os.path.join(g.main_dir.read(), "project", "slack", "bots.ini"))
        g.slack_enabled.write(bots_ini.read("bots", "enable"))
        if g.slack_enabled.read():
            from .project import slack as slack

            # create witch
            self.witch = slack.control
            # begin poll timer
            timer = QtCore.QTimer()
            timer.start(500)  # milliseconds
            self.shutdown.connect(timer.stop)
            g.slack_poll_timer.write(timer)
            g.slack_poll_timer.connect_to_timeout(self.witch.poll)

    def _shutdown(self):
        """
        attempt a clean shutdown
        """
        print("shutdown")
        g.logger.log("info", "Shutdown", "PyCMDS is attempting shutdown")
        self.shutdown.emit()
        g.shutdown.fire()

    def _center(self):
        # a function which ensures that the window appears in the center of the screen at startup
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2)

    def get_status(self, full=False):
        # called by slack
        return self.queue_gui.get_status(full)


#! /usr/bin/env python

import sys
import pathlib

from qtpy import QtWidgets, QtCore

from .__version__ import __version__
from .project import project_globals as g

app = QtWidgets.QApplication(sys.argv)
g.app.write(app)
g.logger.load()


class MainWindow(QtWidgets.QMainWindow):
    shutdown = QtCore.Signal()
    queue_control = QtCore.Signal()

    def __init__(self, config):
        QtWidgets.QMainWindow.__init__(self, parent=None)
        self.config = config
        g.main_window.write(self)
        g.shutdown.write(self.shutdown)
        self.setWindowTitle("yaqc-cmds %s" % __version__)
        # set size, position
        self.window_verti_size = 600
        self.window_horiz_size = 1000
        self.setGeometry(0, 0, self.window_horiz_size, self.window_verti_size)
        # self._center()
        self.resize(self.window_horiz_size, self.window_verti_size)
        self._create_main_frame()
        # initialize program
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

    def _create_main_frame(self):
        self.main_frame = QtWidgets.QWidget(parent=self)
        hbox = QtWidgets.QHBoxLayout()
        # box -----------------------------------------------------------------
        box = QtWidgets.QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
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
        # sonomic box
        self.queue_widget = QtWidgets.QSplitter(parent=self.main_frame)
        # plot box
        self.plot_widget = QtWidgets.QSplitter(parent=self.main_frame)
        # tab widget
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.queue_widget, "Queue")
        self.tabs.addTab(self.plot_widget, "Plot")
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

    def _initialize_widgets(self):
        if g.debug.read():
            print("initialize widgets")
        # import widgets
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

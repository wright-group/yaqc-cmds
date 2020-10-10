import time

from PySide2 import QtWidgets, QtCore

### global classes ############################################################


class SimpleGlobal:
    def __init__(self, initial_value=None):
        self.value = initial_value

    def read(self):
        return self.value

    def write(self, value):
        self.value = value


debug = SimpleGlobal(False)


class PollTimer(SimpleGlobal):
    def connect_to_timeout(self, slot):
        QtWidgets.QAction.connect(self.value, QtCore.SIGNAL("timeout()"), slot)


poll_timer = PollTimer()
slack_poll_timer = PollTimer()


class logger:  # must come before other globals
    def __init__(self):
        pass

    def load(self):
        import yaqc_cmds.project.logging_handler as logging_handler

        self.value = logging_handler.log
        if debug.read():
            self.log("info", "Debug", "Yaqc_cmds is in debug mode")

    def log(self, level, name, message="", origin="name"):
        """
        wrapper of logging method for Yaqc_cmds

        accepts strings

        levels: debug, info, warning, error, critical
        """
        self.value(level, name, message, origin)


logger = logger()

### other globals #############################################################
# alphabetical

app = SimpleGlobal()

colors_dict = SimpleGlobal()

coset_control = SimpleGlobal()

coset_widget = SimpleGlobal()

hardware_advanced_box = SimpleGlobal()

hardware_initialized = SimpleGlobal(False)

google_drive_control = SimpleGlobal()

google_drive_enabled = SimpleGlobal()


class hardware_waits:
    def __init__(self):
        """
        holds value, a list of hardware wait_until_still methods
        """
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


class hardware_widget(SimpleGlobal):
    def __init__(self, initial_value=None):
        super().__init__(initial_value)
        self.number_of_widgets = 0

    def write(self, value):
        super().write(value)
        self.value.setLayout(QtWidgets.QVBoxLayout())
        self.value.layout().setMargin(5)
        self.value.layout().addStretch(1)

    def add_to(self, widget):
        self.value.layout().takeAt(self.number_of_widgets)
        self.value.layout().addWidget(widget)
        self.number_of_widgets += 1
        self.value.layout().addStretch(1)


hardware_widget = hardware_widget()

main_thread = SimpleGlobal(QtCore.QThread.currentThread())

main_window = SimpleGlobal()

scan_thread = SimpleGlobal()


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
        self.value.setValue(fraction * 100)
        # time elapsed
        time_elapsed = time.time() - self.start_time
        m, s = divmod(time_elapsed, 60)
        h, m = divmod(m, 60)
        self.time_elapsed.setText("%02d:%02d:%02d" % (h, m, s))
        # time remaining
        if fraction == 0:
            self.time_remaining.setText("??:??:??")
        else:
            time_remaining = (time_elapsed / fraction) - time_elapsed
            m, s = divmod(time_remaining, 60)
            h, m = divmod(m, 60)
            self.time_remaining.setText("%02d:%02d:%02d" % (h, m, s))


progress_bar = progress_bar()


class shutdown(SimpleGlobal):
    """
    holds the reference of MainWindow.shutdown Qt signal

    during startup, add your shutdown method to this object using the 'add_method' method it will be called upon shutdown.
    your method must not have any arguments
    """

    def __init__(self, initial_value=None):
        super().__init__(initial_value)
        self.methods = []

    def add_method(self, method):
        self.methods.append(method)

    def fire(self):
        for method in self.methods:
            method()
        main_window.read().close()


shutdown = shutdown()

slack_control = SimpleGlobal()

slack_enabled = SimpleGlobal()

system_name = SimpleGlobal()

version = SimpleGlobal()

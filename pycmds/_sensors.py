"""Sensors."""


import appdirs
import pathlib

import collections

import numpy as np
import toml

from PySide2 import QtCore, QtWidgets

import WrightTools as wt
import yaqc

import pycmds.project.classes as pc
import pycmds.project.widgets as pw


config = toml.load(pathlib.Path(appdirs.user_config_dir("pycmds", "pycmds")) / "config.toml")


class Data(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.shape = (1,)
        self.size = 1
        self.channels = []
        self.cols = []
        self.signed = []
        self.map = None

    def read(self):
        return self.channels

    def read_properties(self):
        """
        Returns
        -------
        tuple
            shape, cols, map
        """
        self.lock()
        outs = self.shape, self.cols, self.map
        self.unlock()
        return outs

    def write(self, channels):
        self.lock()
        self.channels = channels
        self.WaitCondition.wakeAll()
        self.unlock()

    def write_properties(self, shape, cols, channels, signed=False, map=None):
        self.lock()
        self.shape = shape
        self.size = np.prod(shape)
        self.channels = channels
        self.cols = cols
        self.signed = signed
        if not signed:
            self.signed = [False] * len(self.cols)
        self.map = map
        self.WaitCondition.wakeAll()
        self.unlock()

    def wait_for_update(self, timeout=5000):
        if self.value:
            self.lock()
            self.WaitCondition.wait(self, timeout)
            self.unlock()


class Sensor(pc.Hardware):
    settings_updated = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        self.freerun = pc.Bool(initial_value=False)
        self.Widget = kwargs.pop("Widget")
        self.data = Data()
        self.active = True
        # shape
        if "shape" in kwargs.keys():
            self.shape = kwargs.pop("shape")
        else:
            self.shape = (1,)
        # map
        if "has_map" in kwargs.keys():
            self.has_map = kwargs.pop("has_map")
        else:
            self.has_map = False
        self.has_map = False  # turning this feature off for now  --Blaise 2020-09-25
        self.measure_time = pc.Number(initial_value=np.nan, display=True, decimals=3)
        pc.Hardware.__init__(self, *args, **kwargs)
        self.settings_updated.emit()

    @property
    def channel_names(self):
        return self.data.cols

    def get_headers(self):
        out = collections.OrderedDict()
        return out

    def give_widget(self, widget):
        self.widget = widget
        self.gui.create_frame(widget)

    def initialize(self):
        self.wait_until_still()
        self.freerun.updated.connect(self.on_freerun_updated)
        self.update_ui.emit()
        self.driver.update_ui.connect(self.on_driver_update_ui)
        self.settings_updated.emit()

    def load_settings(self, aqn):
        pass

    def measure(self):
        self.q.push("measure")

    def on_driver_update_ui(self):
        self.update_ui.emit()

    def on_freerun_updated(self):
        self.q.push("loop")

    def set_freerun(self, state):
        self.freerun.write(state)
        self.on_freerun_updated()
        self.settings_updated.emit()  # TODO: should probably remove this

    def wait_until_still(self):
        while self.busy.read():
            self.busy.wait_for_update()


class Driver(pc.Driver):
    settings_updated = QtCore.Signal()
    running = False

    def __init__(self, sensor, yaqd_port):
        pc.Driver.__init__(self)
        self.client = yaqc.Client(yaqd_port)
        # attributes
        self.name = self.client.id()["name"]
        self.enqueued = sensor.enqueued
        self.busy = sensor.busy
        self.freerun = sensor.freerun
        self.data = sensor.data
        self.shape = sensor.shape
        self.measure_time = sensor.measure_time
        self.thread = sensor.thread

    def initialize(self):
        self.measure()

    def loop(self):
        while self.freerun.read() and not self.enqueued.read():
            self.measure()
            self.busy.write(False)

    def measure(self):
        timer = wt.kit.Timer(verbose=False)
        with timer:
            self.busy.write(True)
            self.client.measure(loop=False)
            while self.client.busy():
                time.sleep(0.1)
            out_names = self.client.get_channel_names()
            signed = [False for _ in out_names]
            out = list(self.client.get_measured().values())[:-1]
            self.data.write_properties(self.shape, out_names, out, signed)
            self.busy.write(False)
        self.measure_time.write(timer.interval)
        self.update_ui.emit()

    def shutdown(self):
        pass


class SensorWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)

    def load(self, aqn_path):
        # TODO:
        pass

    def save(self, aqn_path):
        # TODO:
        ini = wt.kit.INI(aqn_path)
        ini.add_section("Virtual")
        ini.write("Virtual", "use", True)


class Widget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        input_table = pw.InputTable()
        input_table.add("Virtual", None)
        self.use = pc.Bool(initial_value=True)
        input_table.add("Use", self.use)
        layout.addWidget(input_table)

    def load(self, aqn_path):
        pass

    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section("virtual")
        ini.write("virtual", "use", self.use.read())


sensors = []
for section in config["sensors"].keys():
    if section == "settings":
        continue
    if config["sensors"][section]["enable"]:
        # collect arguments
        kwargs = collections.OrderedDict()
        for option in config["sensors"][section].keys():
            if option in ["enable", "model", "serial", "path", "__name__"]:
                continue
            else:
                kwargs[option] = config["sensors"][section][option]
        sensor = Sensor(
            Driver,
            kwargs,
            None,
            Widget=SensorWidget,
            name=section,
            model="Virtual",
        )
        sensors.append(sensor)

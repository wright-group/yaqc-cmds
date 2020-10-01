"""Gathering data and writing to disk."""


import os
import time
import appdirs
import pathlib

import collections

import numpy as np


import toml

from PySide2 import QtCore, QtWidgets

import WrightTools as wt
import tidy_headers

import pycmds.project.project_globals as g
import pycmds.project.classes as pc
import pycmds.project.widgets as pw
from pycmds._sensors import Sensor, Driver, SensorWidget


config = toml.load(pathlib.Path(appdirs.user_config_dir("pycmds", "pycmds")) / "config.toml")

axes = pc.Mutex()

array_detector_reference = pc.Mutex()

origin = pc.Mutex()

# additional
loop_time = pc.Number(initial_value=np.nan, display=True, decimals=3)

idx = pc.Mutex()  # holds tuple

ms_wait_limits = pc.NumberLimits(0, 10000)
ms_wait = pc.Number(
    initial_value=config["sensors"]["settings"]["ms_wait"],
    decimals=0,
    limits=ms_wait_limits,
    display=True,
)


class CurrentSlice(QtCore.QObject):
    indexed = QtCore.Signal()
    appended = QtCore.Signal()

    def __init__(self):
        QtCore.QObject.__init__(self)

    def begin(self, shape):
        """
        Tell current slice that a new scan is beginning. Mostly works to
        reset y limits.

        Parameters
        ----------
        shape : list of ints
            Number of channels for all sensors.
        """
        self.xi = []
        self.data = []
        self.ymins = []
        self.ymaxs = []
        self.use_actual = False
        for n_channels in shape:
            self.ymins.append([-1e-6] * n_channels)
            self.ymaxs.append([1e-6] * n_channels)

    def index(self, d):
        """
        Clear the old data from memory, and define new parameters for the next
        slice.

        Parameters
        ----------
        d : dictionary
            The new slice dictionary, passed all the way from the acquisition
            orderer module.
        """
        self.name = str(d["name"])  # somehow a qstring is getting here? - Blaise 2016.07.27
        self.units = d["units"]
        self.points = d["points"]
        self.use_actual = d["use actual"]
        self.xi = []
        self.data = []
        self.indexed.emit()

    def append(self, position, data):
        """
        Add new values into the slice.

        Parameters
        ----------
        position : float
            The axis position (in the slices' own axis / units)
        data : list of lists of arrays
            List of 1) sensors, 2) channels, containing arrays
        """
        if self.use_actual:
            self.xi.append(position)
        else:
            self.xi.append(self.points[len(self.xi)])
        self.data.append(data)
        for sensor_index, sensor in enumerate(data):
            for channel_index, channel in enumerate(data[sensor_index]):
                minimum = np.min(data[sensor_index][channel_index])
                maximum = np.max(data[sensor_index][channel_index])
                if self.ymins[sensor_index][channel_index] > minimum:
                    self.ymins[sensor_index][channel_index] = minimum
                if self.ymaxs[sensor_index][channel_index] < maximum:
                    self.ymaxs[sensor_index][channel_index] = maximum
        self.appended.emit()


current_slice = CurrentSlice()


class Headers:
    def __init__(self):
        """
        Contains all the seperate dictionaries that go into assembling file
        headers.
        """
        self.clear()

    def clear(self):
        """
        All dictionaries are now empty OrderedDicts.
        """
        self.pycmds_info = collections.OrderedDict()
        self.scan_info = collections.OrderedDict()
        self.data_info = collections.OrderedDict()
        self.axis_info = collections.OrderedDict()
        self.constant_info = collections.OrderedDict()
        self.channel_info = collections.OrderedDict()
        self.daq_info = collections.OrderedDict()
        self.data_cols = collections.OrderedDict()

    def read(self):
        """
        Assemble contained dictionaries into a single dictionary.
        """
        cols = self.data_cols
        channel_info = self.channel_info
        # assemble
        dicts = [
            self.pycmds_info,
            self.data_info,
            self.scan_info,
            self.axis_info,
            self.constant_info,
            channel_info,
            self.daq_info,
            cols,
        ]
        out = collections.OrderedDict()
        for d in dicts:
            for key, value in d.items():
                out[key] = value
        return out


headers = Headers()


data_busy = pc.Busy()

data_path = pc.Mutex()

enqueued_data = pc.Enqueued()


class FileAddress(QtCore.QObject):
    update_ui = QtCore.Signal()
    queue_emptied = QtCore.Signal()

    @QtCore.Slot(str, list)
    def dequeue(self, method, inputs):
        """
        accepts queued signals from 'queue' (address using q method)
        method must be string, inputs must be list
        """
        getattr(self, str(method))(inputs)  # method passed as qstring
        enqueued_data.pop()
        if not enqueued_data.read():
            self.queue_emptied.emit()
            self.check_busy([])

    def check_busy(self, inputs):
        """
        must always write busy whether answer is True or False
        should include a sleep if answer is True to prevent very fast loops: time.sleep(0.1)
        """
        if enqueued_data.read():
            time.sleep(0.01)
            data_busy.write(True)
        else:
            time.sleep(0.01)
            data_busy.write(False)

    def create_data(self, inputs):
        # unpack inputs
        aqn, scan_folder = inputs
        file_index = 0
        # pixels --------------------------------------------------------------
        # file name
        file_index_str = str(file_index).zfill(3)
        self.filename = " ".join([file_index_str]).rstrip()
        # create folder
        data_path.write(os.path.join(scan_folder, self.filename + ".data"))
        # generate file
        dictionary = headers.read()
        tidy_headers.write(data_path.read(), dictionary)

    def write_data(self, inputs):
        data_arr = inputs[0]
        # pixels --------------------------------------------------------------
        data_file = open(data_path.read(), "ab")
        if len(data_arr.shape) == 2:  # case of multidimensional sensors
            for row in data_arr.T:
                np.savetxt(data_file, row, fmt=str("%8.6f"), delimiter="\t", newline="\t")
                data_file.write(b"\n")
        else:
            np.savetxt(data_file, data_arr, fmt=str("%8.6f"), delimiter="\t", newline="\t")
            data_file.write(b"\n")
        data_file.close()

    def initialize(self, inputs):
        pass

    def shutdown(self, inputs):
        # TODO: ?
        pass


# begin address object in seperate thread
data_thread = QtCore.QThread()
data_obj = FileAddress()
data_obj.moveToThread(data_thread)
data_thread.start()

# create queue to communiate with address thread
class DataQueue(QtCore.QObject):
    signal = QtCore.Signal(str, list)

    def __init__(self):
        super(DataQueue, self).__init__()


data_queue = DataQueue()
data_queue.signal.connect(data_obj.dequeue, type=QtCore.Qt.QueuedConnection)


def q(method, inputs=[]):
    # add to friendly queue list
    enqueued_data.push([method, time.time()])
    # busy
    data_busy.write(True)
    # send Qt SIGNAL to address thread
    data_queue.signal.emit(method, inputs)
    # data_queue.invokeMethod(data_obj, 'dequeue', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, method), QtCore.Q_ARG(list, inputs))


class Widget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setMargin(0)
        # daq settings
        input_table = pw.InputTable()
        input_table.add("Sensor Settings", None)
        self.ms_wait = pc.Number(
            initial_value=0, limits=ms_wait_limits, decimals=0, disable_under_queue_control=True,
        )
        input_table.add("ms Wait", self.ms_wait)
        layout.addWidget(input_table)
        # sensor settings
        self.sensor_widgets = []
        for sensor in control.sensors:
            widget = sensor.Widget()
            layout.addWidget(widget)
            self.sensor_widgets.append(widget)

    def load(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        self.ms_wait.write(ini.read("sensor settings", "ms wait"))
        for sensor_widget in self.sensor_widgets:
            sensor_widget.load(aqn_path)

    def save(self, aqn_path):
        ini = wt.kit.INI(aqn_path)
        ini.add_section("sensor settings")
        ini.write("sensor settings", "ms wait", self.ms_wait.read())
        for sensor_widget in self.sensor_widgets:
            sensor_widget.save(aqn_path)


class SensorGUI(QtCore.QObject):
    def __init__(self, hardware):
        QtCore.QObject.__init__(self)
        self.hardware = hardware
        self.samples_tab_initialized = False

    def close(self):
        pass

    def create_frame(self, parent_widget):
        # get layout
        parent_widget.setLayout(QtWidgets.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        self.layout = parent_widget.layout()




class DisplaySettings(QtCore.QObject):
    updated = QtCore.Signal()

    def __init__(self, sensor):
        """
        Display settings for a particular sensor.
        """
        QtCore.QObject.__init__(self)
        self.sensor = sensor
        # self.sensor.wait_until_done()
        self.widget = pw.InputTable()
        self.channel_combo = pc.Combo()
        self.channel_combo.updated.connect(lambda: self.updated.emit())
        self.widget.add("Channel", self.channel_combo)
        self.shape_controls = []
        if self.sensor.shape != (1,):
            map_axis_names = list(self.sensor.map_axes.keys())
            for i in range(len(self.sensor.shape)):
                limits = pc.NumberLimits(0, self.sensor.shape[i] - 1)
                control = pc.Number(initial_value=0, decimals=0, limits=limits)
                self.widget.add(" ".join([map_axis_names[i], "index"]), control)
                self.shape_controls.append(control)
                control.updated.connect(lambda: self.updated.emit())

    def get_channel_index(self):
        return self.channel_combo.read_index()

    def get_map_index(self):
        if len(self.shape_controls) == 0:
            return None
        return tuple(c.read() for c in self.shape_controls)

    def hide(self):
        self.widget.hide()

    def show(self):
        self.widget.show()

    def update_channels(self):
        allowed_values = self.sensor.data.read_properties()[1]
        if not len(allowed_values) == 0:
            self.channel_combo.set_allowed_values(allowed_values)


control = Control()

import pycmds.hardware.opas.opas as opas
import pycmds.hardware.spectrometers.spectrometers as spectrometers
import pycmds.hardware.delays as delays
import pycmds.hardware.filters.filters as filters

scan_hardware_modules = [opas, spectrometers, delays, filters]

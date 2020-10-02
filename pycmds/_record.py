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


class Control(QtCore.QObject):
    """
    Only one instance in the entire program.
    """

    settings_updated = QtCore.Signal()

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.sensors = []
        g.main_window.read().queue_control.connect(self.queue_control_update)
        self.channel_names = []
        # import sensors
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
                    Driver, kwargs, SensorGUI, Widget=SensorWidget, name=section, model="Virtual",
                )
                self.sensors.append(sensor)
        # gui
        self.gui = GUI(self)
        for sensor in self.sensors:
            sensor.update_ui.connect(self.gui.create_main_tab)
        # initialize
        for sensor in self.sensors:
            sensor.initialize()
        self.set_freerun(True)
        self.wait_until_done()  # TODO:...
        # time.sleep(3)  # TOD: remove
        # connect
        for sensor in self.sensors:
            sensor.settings_updated.connect(self.on_sensor_settings_updated)
        self.t_last = time.time()
        # initialize channel names
        for sensor in self.sensors:
            for channel_name in sensor.data.cols:
                self.channel_names.append(channel_name)
        # finish
        self.settings_updated.emit()

    def acquire(self, save=False, index=None):
        # loop time
        now = time.time()
        loop_time.write(now - self.t_last)
        self.t_last = now
        # ms wait
        time.sleep(ms_wait.read() / 1000.0)
        # acquire
        for sensor in self.sensors:
            if sensor.active:
                sensor.measure()
        self.wait_until_done()
        # save
        if save:
            # 1D things -------------------------------------------------------
            data_rows = np.prod([d.data.size for d in self.sensors if d.active])
            data_shape = (len(headers.data_cols["name"]), int(data_rows))
            data_arr = np.full(data_shape, np.nan)
            data_i = 0
            # scan indicies
            for i in idx.read():  # scan sensor
                data_arr[data_i] = i
                data_i += 1
            for sensor in self.sensors:  # daq
                if sensor.active and sensor.has_map:
                    map_indicies = [i for i in np.ndindex(sensor.data.shape)]
                    for i in range(len(sensor.data.shape)):
                        data_arr[data_i] = [mi[i] for mi in map_indicies]
                        data_i += 1
            # time
            now = time.time()  # seconds since epoch
            data_arr[data_i] = now
            data_i += 1
            # hardware positions
            for scan_hardware_module in scan_hardware_modules:
                for scan_hardware in scan_hardware_module.hardwares:
                    for key in scan_hardware.recorded:
                        out_units = scan_hardware.recorded[key][1]
                        if out_units is None:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read()
                        else:
                            data_arr[data_i] = scan_hardware.recorded[key][0].read(out_units)
                        data_i += 1
            # potentially multidimensional things -----------------------------
            # acquisition maps
            for sensor in self.sensors:
                if sensor.active and sensor.has_map:
                    data_arr[data_i] = sensor.map.read()
                    data_i += 1
            # acquisitions
            for sensor in self.sensors:
                if sensor.active:
                    channels = sensor.data.read()  # list of arrays
                    for arr in channels:
                        data_arr[data_i] = arr
                        data_i += 1
            # send to file_address --------------------------------------------
            q("write_data", [data_arr])
            # fill slice ------------------------------------------------------
            slice_axis_index = headers.data_cols["name"].index(current_slice.name)
            slice_position = np.mean(data_arr[slice_axis_index])
            native_units = headers.data_cols["units"][slice_axis_index]
            slice_position = wt.units.converter(slice_position, native_units, current_slice.units)
            data_arrs = []
            for sensor in self.sensors:
                data_arrs.append(sensor.data.read())
            current_slice.append(slice_position, data_arrs)

    def initialize_scan(self, aqn, scan_folder, destinations_list):
        timestamp = wt.kit.TimeStamp()
        # stop freerunning
        self.set_freerun(False)
        # fill out pycmds_information in headers
        headers.pycmds_info["PyCMDS version"] = g.version.read()
        headers.pycmds_info["system name"] = g.system_name.read()
        headers.pycmds_info["file created"] = timestamp.RFC3339
        # apply sensor settings from aqn
        ms_wait.write(aqn.read("sensor settings", "ms wait"))
        for sensor in self.sensors:
            # if not aqn.has_section(sensor.name):
            #    sensor.active = False
            #    continue
            # if not aqn.read(sensor.name, "use"):
            #    sensor.active = False
            #    continue
            # apply settings from aqn to sensor
            sensor.active = True
            sensor.load_settings(aqn)
            # record sensor axes, if applicable
            if sensor.has_map:
                for key in sensor.map_axes.keys():
                    # add axis
                    headers.axis_info["axis names"].append(key)
                    (identity, units, points, centers, interpolate,) = sensor.get_axis_properties(
                        destinations_list
                    )
                    headers.axis_info["axis identities"].append(identity)
                    headers.axis_info["axis units"].append(units)
                    headers.axis_info["axis interpolate"].append(interpolate)
                    headers.axis_info[" ".join([key, "points"])] = points
                    if centers is not None:
                        headers.axis_info[" ".join([key, "centers"])] = centers
                    # expand exisiting axes (not current axis)
                    for subkey in headers.axis_info.keys():
                        if "centers" in subkey and key not in subkey:
                            centers = headers.axis_info[subkey]
                            centers = np.expand_dims(centers, axis=-1)
                            centers = np.repeat(centers, points.size, axis=-1)
                            headers.axis_info[subkey] = centers
        # add cols information
        self.update_cols(aqn)
        # add channel signed choices
        # TODO: better implementation. for now, just assume not signed
        signed = []
        for sensor in self.sensors:
            signed += sensor.data.signed
        headers.channel_info["channel signed"] = signed
        # add daq information to headers
        for sensor in self.sensors:
            if sensor.active:
                for key, value in sensor.get_headers().items():
                    headers.daq_info[" ".join([sensor.name, key])] = value
        q("create_data", [aqn, scan_folder])
        # refresh current slice properties
        current_slice.begin([len(sensor.data.cols) for sensor in self.sensors])
        # wait until daq is done before letting module continue
        self.wait_until_done()
        self.wait_until_file_done()

    def on_sensor_settings_updated(self):
        self.channel_names = []
        for sensor in self.sensors:
            for channel_name in sensor.data.cols:
                self.channel_names.append(channel_name)
        self.settings_updated.emit()

    def queue_control_update(self):
        if g.queue_control.read():
            self.set_freerun(False)
            self.wait_until_done()
        else:
            # TODO: something better...
            self.set_freerun(True)

    def set_freerun(self, state):
        for sensor in self.sensors:
            sensor.set_freerun(state)

    def shutdown(self):
        self.set_freerun(False)
        self.wait_until_done()
        for sensor in self.sensors:
            sensor.close()

    def update_cols(self, aqn):
        kind = []
        tolerance = []
        units = []
        label = []
        name = []
        # indicies
        for n in headers.axis_info["axis names"]:
            kind.append(None)
            tolerance.append(None)
            units.append(None)
            label.append("")
            name.append("_".join([n, "index"]))
        # time
        kind.append(None)
        tolerance.append(0.01)
        units.append("s")
        label.append("lab")
        name.append("time")
        # scan hardware positions
        for scan_hardware_module in scan_hardware_modules:
            for scan_hardware in scan_hardware_module.hardwares:
                for key in scan_hardware.recorded:
                    kind.append("hardware")
                    tolerance.append(scan_hardware.recorded[key][2])
                    units.append(scan_hardware.recorded[key][1])
                    label.append(scan_hardware.recorded[key][3])
                    name.append(key)
        # acquisition maps
        for sensor in self.sensors:
            if not aqn.has_section(sensor.name):
                continue
            if not aqn.read(sensor.name, "use"):
                continue
            if sensor.has_map:
                for i in range(len(sensor.map_axes)):
                    kind.append("hardware")
                    tolerance.append(None)
                    vals = list(sensor.map_axes.values())
                    units.append(vals[i][1])
                    label.append(vals[i][0])
                    name.append(list(sensor.map_axes.keys())[i])
        # channels
        self.channel_names = []
        for sensor in self.sensors:
            # if not aqn.has_section(sensor.name):
            #    continue
            # if not aqn.read(sensor.name, "use"):
            #    continue
            mutex = sensor.data
            for col in mutex.cols:
                kind.append("channel")
                tolerance.append(None)
                units.append("")  # TODO: better units support?
                label.append("")  # TODO: ?
                name.append(col)
                self.channel_names.append(col)
        # clean up
        for i, s in enumerate(label):
            label[i] = s.replace("prime", r"\'")
        # finish
        cols = headers.data_cols
        cols["kind"] = kind
        cols["tolerance"] = tolerance
        cols["label"] = label
        cols["units"] = units
        cols["name"] = name
        self.on_sensor_settings_updated()

    def wait_until_file_done(self):
        while data_busy.read():
            data_busy.wait_for_update()

    def wait_until_done(self):
        """
        Wait until the acquisition sensors are no longer busy. Does not wait
        for the file writing queue to empty.
        """
        for sensor in self.sensors:
            if sensor.active:
                sensor.wait_until_still()


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


class GUI(QtCore.QObject):
    def __init__(self, control):
        QtCore.QObject.__init__(self)
        self.control = control
        self.create_frame()
        self.main_tab_created = False

    def create_frame(self):
        # scan widget
        self.main_widget = g.main_window.read().scan_widget

    def create_main_tab(self):
        if self.main_tab_created:
            return
        for sensor in self.control.sensors:
            if len(sensor.data.read_properties()[1]) == 0:
                return
        self.main_tab_created = True
        # create main daq tab
        main_widget = self.main_widget
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(layout)
        # display -------------------------------------------------------------
        # container widget
        display_container_widget = pw.ExpandingWidget()
        display_container_widget.setLayout(QtWidgets.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        # big number
        big_number_container_widget = QtWidgets.QWidget()
        big_number_container_widget.setLayout(QtWidgets.QHBoxLayout())
        big_number_container_layout = big_number_container_widget.layout()
        big_number_container_layout.setMargin(0)
        self.big_display = pw.SpinboxAsDisplay(font_size=100)
        self.big_channel = pw.Label("channel", font_size=72)
        big_number_container_layout.addWidget(self.big_channel)
        big_number_container_layout.addStretch(1)
        big_number_container_layout.addWidget(self.big_display)
        display_layout.addWidget(big_number_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_scatter = self.plot_widget.add_scatter()
        self.plot_line = self.plot_widget.add_line()
        display_layout.addWidget(self.plot_widget)
        # vertical line -------------------------------------------------------
        line = pw.line("V")
        layout.addWidget(line)
        # settings ------------------------------------------------------------
        # container widget / scroll area
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        # display settings
        input_table = pw.InputTable()
        input_table.add("Display", None)
        allowed_values = [sensor.name for sensor in self.control.sensors]
        self.sensor_combo = pc.Combo(allowed_values=allowed_values)
        self.sensor_combo.updated.connect(self.on_update_sensor)
        input_table.add("Sensor", self.sensor_combo)
        settings_layout.addWidget(input_table)
        self.display_settings_widgets = collections.OrderedDict()
        for sensor in self.control.sensors:
            display_settings = DisplaySettings(sensor)
            self.display_settings_widgets[sensor.name] = display_settings
            settings_layout.addWidget(display_settings.widget)
            sensor.settings_updated.connect(self.on_update_channels)
            display_settings.updated.connect(self.on_update_sensor)
        # global daq settings
        input_table = pw.InputTable()
        input_table.add("Settings", None)
        input_table.add("ms Wait", ms_wait)
        for sensor in self.control.sensors:
            input_table.add(sensor.name, None)
            input_table.add("Status", sensor.busy)
            input_table.add("Freerun", sensor.freerun)
            input_table.add("Time", sensor.measure_time)
        input_table.add("File", None)
        data_busy.update_signal = data_obj.update_ui
        input_table.add("Status", data_busy)
        input_table.add("Scan", None)
        input_table.add("Loop Time", loop_time)
        self.idx_string = pc.String(initial_value="None", display=True)
        input_table.add("Scan Index", self.idx_string)
        settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)
        # finish --------------------------------------------------------------
        self.on_update_channels()
        self.on_update_sensor()
        for sensor in self.control.sensors:
            sensor.update_ui.connect(self.update)
        current_slice.indexed.connect(self.on_slice_index)
        current_slice.appended.connect(self.on_slice_append)

    def on_slice_append(self):
        sensor_index = self.sensor_combo.read_index()
        sensor_display_settings = list(self.display_settings_widgets.values())[sensor_index]
        channel_index = sensor_display_settings.channel_combo.read_index()
        # limits
        ymin = current_slice.ymins[sensor_index][channel_index]
        ymax = current_slice.ymaxs[sensor_index][channel_index]
        self.plot_widget.set_ylim(ymin, ymax)
        # data
        xi = current_slice.xi
        # TODO: in case of sensor with shape...
        yi = [current_slice.data[i][sensor_index][channel_index] for i, _ in enumerate(xi)]
        # finish
        self.plot_scatter.setData(xi, yi)
        self.plot_line.setData(xi, yi)

    def on_slice_index(self):
        xlabel = "{0} ({1})".format(current_slice.name, current_slice.units)
        self.plot_widget.set_labels(xlabel=xlabel)
        xmin = min(current_slice.points)
        xmax = max(current_slice.points)
        self.plot_widget.set_xlim(xmin, xmax)

    def on_update_channels(self):
        for display_settings in self.display_settings_widgets.values():
            display_settings.update_channels()

    def on_update_sensor(self):
        current_sensor_index = self.sensor_combo.read_index()
        for display_settings in self.display_settings_widgets.values():
            display_settings.hide()
        list(self.display_settings_widgets.values())[current_sensor_index].show()
        self.update()

    def update(self):
        """
        Runs each time an update_ui signal fires (basically every run_task)
        """
        # scan index
        self.idx_string.write(str(idx.read()))
        # big number
        current_sensor_index = self.sensor_combo.read_index()
        sensor = self.control.sensors[current_sensor_index]
        widget = list(self.display_settings_widgets.values())[current_sensor_index]
        channel_index = widget.get_channel_index()
        map_index = widget.get_map_index()
        if map_index is None:
            big_number = sensor.data.read()[channel_index]
        else:
            big_number = sensor.data.read()[channel_index][map_index]
        if len(self.control.channel_names) > channel_index:
            self.big_channel.setText(self.control.channel_names[channel_index])
        self.big_display.setValue(big_number)

    def stop(self):
        pass


control = Control()

import pycmds.hardware.opas.opas as opas
import pycmds.hardware.spectrometers as spectrometers
import pycmds.hardware.delays as delays
import pycmds.hardware.filters.filters as filters

scan_hardware_modules = [opas, spectrometers, delays, filters]

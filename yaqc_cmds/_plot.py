"""GUI for displaying scans in progress, current slice etc."""

from collections import deque
from contextlib import contextmanager
import itertools

from PySide2 import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg

from bluesky.callbacks import CallbackBase
from bluesky_widgets.qt.zmq_dispatcher import RemoteDispatcher

import WrightTools as wt
import yaqc_cmds
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.classes as pc
import yaqc_cmds.somatic as somatic


class GUI(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()
        self.create_settings()
        self.data = None
        self._units_map = {}

    def create_frame(self):
        self.main_widget = g.main_window.read().plot_widget
        # create main daq tab
        main_widget = self.main_widget
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        main_widget.setLayout(layout)
        # display
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
        # vertical line
        line = pw.line("V")
        layout.addWidget(line)
        # settings
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.settings_layout = settings_container_widget.layout()
        self.settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        g.shutdown.read().connect(self.on_shutdown)

    def create_settings(self):
        # display settings
        input_table = pw.InputTable()
        input_table.add("Display", None)
        self.channel = pc.Combo()
        input_table.add("Channel", self.channel)
        self.axis = pc.Combo()
        input_table.add("X-Axis", self.axis)
        self.axis_units = pc.Combo()
        input_table.add("X-Units", self.axis_units)
        self.settings_layout.addWidget(input_table)
        # global daq settings
        input_table = pw.InputTable()
        # input_table.add("ms Wait", ms_wait)
        input_table.add("Scan", None)
        # input_table.add("Loop Time", loop_time)
        self.idx_string = pc.String(initial_value="None", display=True)
        input_table.add("Scan Index", self.idx_string)
        self.settings_layout.addWidget(input_table)
        # stretch
        self.settings_layout.addStretch(1)

    def set_units_map(self, units_map):
        self._units_map = units_map
        self.on_axis_updated()

    def on_axis_updated(self):
        units = self._units_map.get(self.axis.read())
        units = [units] + list(wt.units.get_valid_conversions(units))
        self.axis_units.set_allowed_values(units)

    def update_plot(self):
        # data
        if not plot_callback.events:
            return
        x_units = self.axis_units.read()
        axis = self.axis.read()
        channel = self.channel.read()
        self.plot_widget.clear()

        def plot(start, stop, color="c"):
            stop = min(stop, len(plot_callback.events))
            if stop == len(plot_callback.events):
                color = "c"
            if axis == "time":
                x = [plot_callback.events[i]["time"] for i in range(start, stop)]
            else:
                x = [plot_callback.events[i]["data"][axis] for i in range(start, stop)]
            y = [plot_callback.events[i]["data"][channel] for i in range(start, stop)]
            try:
                xi = wt.units.convert(
                    x,
                    self._units_map.get(axis),
                    x_units,
                )
                self.plot_widget.plot_object.plot(
                    # self.plot_scatter.addPoints(
                    xi,
                    y,
                    size=5,
                    pen=pg.mkPen(color),
                    brush=pg.mkBrush(color),
                    symbol="o",
                    symbolPen=pg.mkPen(color),
                    symbolBrush=pg.mkBrush(color),
                )
            except (TypeError, ValueError) as e:
                print(e)
                pass

        start = 0
        cidx = 0
        print(len(plot_callback.events), plot_callback.slice_size)
        ncolors = int(np.ceil(len(plot_callback.events) / plot_callback.slice_size))
        colors = np.linspace([60, 60, 60], [0, 180, 180], ncolors, dtype="u1")

        idx = plot_callback.events[-1].get("seq_num", len(plot_callback.events))
        if len(plot_callback.events) == plot_callback.events.maxlen:
            start = plot_callback.slice_size - idx % plot_callback.slice_size
            plot(0, start, [60, 60, 60])
        while start < len(plot_callback.events):
            plot(start, start + plot_callback.slice_size, colors[cidx])
            start += plot_callback.slice_size
            cidx += 1
            cidx %= len(colors)

        num = plot_callback.events[-1]["data"][channel]
        if not np.isscalar(num):
            channel = f"max({channel})"
            num = np.max(num)
        self.big_channel.setText(channel)
        self.big_display.setValue(num)
        # limits
        """
        try:
            self.plot_widget.set_xlim(min(limits), max(limits))
            self.plot_widget.set_ylim(np.min(channel), np.max(channel))
        except Exception as e:
            print(e)
            pass
        """

    def on_shutdown(self):
        pass

    def stop(self):
        pass


gui = GUI()


class PlotCallback(CallbackBase):
    def __init__(self):
        self.start_doc = None
        self.stop_doc = None
        self.events = None
        self.descriptor_doc = None
        self.dimensions = []
        self.units_map = {}
        self.slice_size = 2 ** 64
        self.progress_bar = g.progress_bar

    def start(self, doc):
        self.start_doc = doc
        super().start(doc)
        self.progress_bar.begin_new_scan_timer()
        self.expected_events = doc.get("num_points", -1)
        # Set X-axis to last dimension as available options, first one as default
        # Currently assuming only one stream, because otherwise too complicated for MVP
        if self.start_doc.get("hints", {}).get("dimensions"):
            # Get the list of hinted dimension fields for the last (scanned) dimension
            self.dimensions = self.start_doc["hints"]["dimensions"][-1][0]
            self.all_dimensions = list(
                itertools.chain(*[dim[0] for dim in self.start_doc["hints"]["dimensions"]])
            )
        else:
            # Default if the hints are not given
            self.dimensions = ["time"]
            self.all_dimensions = ["time"]
        gui.axis.set_allowed_values(self.dimensions)

        if self.start_doc.get("shape"):
            self.shape = self.start_doc["shape"]
            # TODO not hardcode number of slices
            self.events = deque(maxlen=5 * self.shape[-1])
            self.slice_size = self.shape[-1]
        else:
            self.events = deque()
            self.shape = None
            self.slice_size = 2 ** 64

    def descriptor(self, doc):
        # Currently assuming only one stream, thus only one descriptor doc
        # A more full representation would account for multiple descriptors
        self.descriptor_doc = doc
        super().descriptor(doc)
        self.units_map = {
            dim: self.descriptor_doc.get("data_keys", {}).get(dim, {}).get("units")
            for dim in self.dimensions
        }

        gui.set_units_map(self.units_map)

        self.channels = []
        for hint in self.descriptor_doc.get("hints", {}).values():
            for field in hint.get("fields", []):
                if field not in self.all_dimensions:
                    self.channels.append(field)
        gui.channel.set_allowed_values(self.channels)

    def event(self, doc):
        super().event(doc)
        if self.expected_events > 0:
            self.progress_bar.set_fraction(doc["seq_num"] / self.expected_events)
        self.events.append(doc)
        index = doc["seq_num"] - 1
        if self.shape and index:
            index = np.unravel_index(index, self.shape)
        gui.idx_string.write(str(index))

        somatic.signals.update_plot.emit()

    def end(self, doc):
        super().end(doc)
        self.progress_bar.set_fraction(1)


# TODO config rather than hardcode address
dispatcher = RemoteDispatcher("localhost:5568")
plot_callback = PlotCallback()
dispatcher.subscribe(plot_callback)
dispatcher.start()
# TODO ensure workers quit


somatic.signals.update_plot.connect(gui.update_plot)
# somatic.signals.data_file_created.connect(gui.on_data_file_created)
gui.axis.updated.connect(gui.on_axis_updated)
gui.axis.updated.connect(gui.update_plot)
gui.axis_units.updated.connect(gui.update_plot)
gui.channel.updated.connect(gui.update_plot)

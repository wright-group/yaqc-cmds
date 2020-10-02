"""GUI for displaying scans in progress, current slice etc."""


import collections

from PySide2 import QtCore, QtWidgets

import pycmds.project.project_globals as g
from pycmds._sensors import sensors
import pycmds.project.widgets as pw
import pycmds.project.classes as pc


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
        allowed_values = self.sensor.channel_names
        if not len(allowed_values) == 0:
            self.channel_combo.set_allowed_values(allowed_values)


class GUI(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()

    def create_frame(self):
        # scan widget
        self.main_widget = g.main_window.read().plot_widget
        self.create_main_tab()

    def create_main_tab(self):
        for sensor in sensors:
            if len(sensor.channel_names) == 0:
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
        allowed_values = [sensor.name for sensor in sensors]
        self.sensor_combo = pc.Combo(allowed_values=allowed_values)
        self.sensor_combo.updated.connect(self.on_update_sensor)
        input_table.add("Sensor", self.sensor_combo)
        settings_layout.addWidget(input_table)
        self.display_settings_widgets = collections.OrderedDict()
        for sensor in sensors:
            display_settings = DisplaySettings(sensor)
            self.display_settings_widgets[sensor.name] = display_settings
            settings_layout.addWidget(display_settings.widget)
            sensor.settings_updated.connect(self.on_update_channels)
            display_settings.updated.connect(self.on_update_sensor)
        # global daq settings
        input_table = pw.InputTable()
        input_table.add("Settings", None)
        # input_table.add("ms Wait", ms_wait)
        for sensor in sensors:
            input_table.add(sensor.name, None)
            input_table.add("Status", sensor.busy)
            input_table.add("Freerun", sensor.freerun)
            input_table.add("Time", sensor.measure_time)
        input_table.add("Scan", None)
        # input_table.add("Loop Time", loop_time)
        self.idx_string = pc.String(initial_value="None", display=True)
        input_table.add("Scan Index", self.idx_string)
        settings_layout.addWidget(input_table)
        # stretch
        settings_layout.addStretch(1)
        # finish --------------------------------------------------------------
        self.on_update_channels()
        self.on_update_sensor()
        for sensor in sensors:
            sensor.update_ui.connect(self.update)

    def on_slice_append(self):
        sensor_name = self.sensor_combo.read()
        sensor_display_settings = self.display_settings_widgets[sensor_name]
        channel_name = sensor_display_settings.channel_combo.read()
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
        # scan index
        # self.idx_string.write(str(idx.read()))
        # big number
        current_sensor_index = self.sensor_combo.read_index()
        current_sensor_name = self.sensor_combo.read()
        sensor = sensors[current_sensor_index]
        widget = self.display_settings_widgets[current_sensor_name]
        channel_name = widget.channel_combo.read()
        map_index = None  # widget.get_map_index()
        if map_index is None:
            big_number = sensor.channels[channel_name]
        else:
            big_number = sensor.data.read()[channel_index][map_index]
        channel_names = [l for s in sensors for l in s.channel_names]
        self.big_channel.setText(channel_name)
        self.big_display.setValue(big_number)

    def stop(self):
        pass


gui = GUI()

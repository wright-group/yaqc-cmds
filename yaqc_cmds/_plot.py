"""GUI for displaying scans in progress, current slice etc."""

from PySide2 import QtCore, QtWidgets
import numpy as np

import WrightTools as wt
import yaqc_cmds
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.sensors as sensors
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.classes as pc
import yaqc_cmds.somatic as somatic


class GUI(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()
        self.create_settings()
        self.on_sensors_changed()
        self.data = None

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
        input_table.add("Settings", None)
        # input_table.add("ms Wait", ms_wait)
        for sensor in sensors.sensors:
            input_table.add(sensor.name, None)
            input_table.add("Status", sensor.busy)
            input_table.add("Freerun", sensor.freerun)
            input_table.add("Time", sensor.measure_time)
        input_table.add("Scan", None)
        # input_table.add("Loop Time", loop_time)
        self.idx_string = pc.String(initial_value="None", display=True)
        input_table.add("Scan Index", self.idx_string)
        self.settings_layout.addWidget(input_table)
        # stretch
        self.settings_layout.addStretch(1)

    def on_channels_changed(self):
        new = list(sensors.get_channels_dict())
        if "ingaas" in new:
            new.remove("ingaas")
        self.channel.set_allowed_values(new)

    def on_data_file_created(self):
        with somatic._wt5.data_container as data:
            allowed = [x.split()[0] for x in data.attrs["axes"]]
            if "wa" in allowed:
                allowed.remove("wa")
            self.axis.set_allowed_values(allowed)
            self.on_axis_updated()

    def on_axis_updated(self):
        with somatic._wt5.data_container as data:
            axis = data[self.axis.read()]
            units = axis.attrs.get("units")
            units = [units] + list(wt.units.get_valid_conversions(units))
            self.axis_units.set_allowed_values(units)

    def on_data_file_written(self):
        with somatic._wt5.data_container as data:
            last_idx_written = somatic._wt5.data_container.last_idx_written
            self.idx_string.write(str(last_idx_written))
            if data is None or last_idx_written is None:
                return
            # data
            x_units = self.axis_units.read()
            idx = last_idx_written
            axis = data[self.axis.read()]
            limits = list(
                wt.units.convert(
                    [np.min(axis.full), np.max(axis.full)], axis.attrs.get("units"), x_units
                )
            )
            channel = data[self.channel.read()]
            plot_idx = list(last_idx_written + (0,) * (channel.ndim - len(last_idx_written)))
            plot_idx[self.axis.read_index()] = slice(None)

            plot_idx = tuple(plot_idx)
            try:
                xi = wt.units.convert(
                    axis[wt.kit.valid_index(plot_idx, axis.shape)],
                    axis.attrs.get("units"),
                    x_units,
                )
                yi = channel[wt.kit.valid_index(plot_idx, channel.shape)]
                self.plot_scatter.setData(xi, yi)
            except (TypeError, ValueError) as e:
                print(e)
                pass
            # limits
            try:
                self.plot_widget.set_xlim(min(limits), max(limits))
                self.plot_widget.set_ylim(np.min(channel), np.max(channel))
            except Exception:
                pass

    def on_sensors_changed(self):
        for s in sensors.sensors:
            s.update_ui.connect(self.update_big_number)
        self.on_channels_changed()

    def on_shutdown(self):
        pass

    def stop(self):
        pass

    def update_big_number(self):
        channel = self.channel.read()
        if channel == "None":
            return
        sensor = sensors.get_channels_dict()[channel]
        num = sensor.channels[channel]
        if not np.isscalar(num):
            channel = f"max({channel})"
            num = np.max(num)
        self.big_channel.setText(channel)
        self.big_display.setValue(num)


gui = GUI()
somatic.signals.data_file_written.connect(gui.on_data_file_written)
somatic.signals.data_file_created.connect(gui.on_data_file_created)
sensors.signals.channels_changed.connect(gui.on_channels_changed)
sensors.signals.sensors_changed.connect(gui.on_sensors_changed)
gui.axis.updated.connect(gui.on_axis_updated)
gui.axis.updated.connect(gui.on_data_file_written)
gui.axis_units.updated.connect(gui.on_data_file_written)

### import ####################################################################


import os
import traceback
import imp
import time
import datetime
import dateutil
import collections
import pathlib
import pprint

from PySide2 import QtCore, QtWidgets

import appdirs
import toml

from bluesky_queueserver.manager.comms import zmq_single_request
import WrightTools as wt

import yaqc_cmds.__main__
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.file_dialog_handler as file_dialog_handler

import yaqc_cmds.hardware.spectrometers as spectrometers
import yaqc_cmds.hardware.delays as delays
import yaqc_cmds.hardware.opas as opas
import yaqc_cmds.hardware.filters as filters

all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares


### GUI #######################################################################


class GUI(QtCore.QObject):
    def __init__(self, parent_widget, message_widget):
        QtCore.QObject.__init__(self)
        self.progress_bar = g.progress_bar
        # frame, widgets
        self.message_widget = message_widget
        self.parent_widget = parent_widget
        parent_widget.setLayout(QtWidgets.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        self.layout = parent_widget.layout()
        self.create_frame()
        self.interrupt_choice_window = pw.ChoiceWindow(
            "QUEUE INTERRUPTED", button_labels=["RESUME", "SKIP", "STOP"]
        )
        # queue
        self.queue = []
        self.queue_get = {"plan_history_uid": None}
        # self.queue_status = QueueStatus()
        self.update_ui()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100)

    def add_button_to_table(self, i, j, text, color, method):
        # for some reason, my lambda function does not work when called outside
        # of a dedicated method - Blaise 2016-09-14
        button = pw.SetButton(text, color=color)
        button.setProperty("TableRowIndex", i)
        button.clicked.connect(lambda: method(button.property("TableRowIndex")))
        self.table.setCellWidget(i, j, button)
        return button

    def add_index_to_table(self, i, max_value):
        # for some reason, my lambda function does not work when called outside
        # of a dedicated method - Blaise 2016-09-14
        index = QtWidgets.QDoubleSpinBox()
        StyleSheet = "QDoubleSpinBox{color: custom_color; font: 14px;}".replace(
            "custom_color", g.colors_dict.read()["text_light"]
        )
        StyleSheet += "QScrollArea, QWidget{background: custom_color;  border-color: black; border-radius: 0px;}".replace(
            "custom_color", g.colors_dict.read()["background"]
        )
        StyleSheet += "QWidget:disabled{color: custom_color_1; font: 14px; border: 0px solid black; border-radius: 0px;}".replace(
            "custom_color_1", g.colors_dict.read()["text_disabled"]
        ).replace(
            "custom_color_2", g.colors_dict.read()["widget_background"]
        )
        index.setStyleSheet(StyleSheet)
        index.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        index.setSingleStep(1)
        index.setDecimals(0)
        index.setMaximum(max_value)
        index.setAlignment(QtCore.Qt.AlignCenter)
        index.setValue(i)
        index.setProperty("TableRowIndex", i)
        index.editingFinished.connect(
            lambda: self.on_index_changed(index.property("TableRowIndex"), int(index.value()))
        )
        self.table.setCellWidget(i, 0, index)
        return index

    def create_frame(self):
        # queue display -------------------------------------------------------
        # container widget
        display_container_widget = pw.ExpandingWidget()
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        self.layout.addWidget(display_container_widget)
        # table
        self.table = pw.TableWidget()
        self.table.verticalHeader().hide()
        self.table_cols = collections.OrderedDict()
        self.table_cols["Index"] = 50
        self.table_cols["Type"] = 75
        self.table_cols["Status"] = 85
        self.table_cols["Started"] = 110
        self.table_cols["Exited"] = 110
        self.table_cols["Description"] = 200  # expanding
        self.table_cols["Remove"] = 75
        self.table_cols["Load"] = 75
        for i in range(len(self.table_cols.keys())):
            self.table.insertColumn(i)
        labels = list(self.table_cols.keys())
        labels[-1] = ""
        labels[-2] = ""
        self.table.setHorizontalHeaderLabels(labels)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        for i, width in enumerate(self.table_cols.values()):
            self.table.setColumnWidth(i, width)
        display_layout.addWidget(self.table)
        # line ----------------------------------------------------------------
        line = pw.Line("V")
        self.layout.addWidget(line)
        # controls ------------------------------------------------------------
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area()
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        line = pw.line("H")
        settings_layout.addWidget(line)
        # adjust queue label
        input_table = pw.InputTable()
        input_table.add("Control Queue", None)
        settings_layout.addWidget(input_table)
        # go button
        self.queue_control = pw.QueueControl()
        self.queue_control.clicked.connect(self.on_queue_control_clicked)
        settings_layout.addWidget(self.queue_control)
        self.queue_control.setDisabled(True)
        # queue runtime
        input_table = pw.InputTable()
        self.runtime = pc.String(initial_value="000:00:00", display=True)
        input_table.add("Queue Runtime", self.runtime)
        settings_layout.addWidget(input_table)
        # horizontal line
        line = pw.Line("H")
        settings_layout.addWidget(line)
        # type combobox
        input_table = pw.InputTable()
        input_table.add("Add to Queue", None)
        settings_layout.addWidget(input_table)
        # frames
        self.type_frames = collections.OrderedDict()
        # self.type_frames["Acquisition"] = self.create_acquisition_frame()
        for frame in self.type_frames.values():
            settings_layout.addWidget(frame)
            frame.hide()
        # append button
        self.append_button = pw.SetButton("APPEND TO QUEUE")
        self.append_button.setDisabled(True)
        self.append_button.clicked.connect(self.on_append_to_queue)
        settings_layout.addWidget(self.append_button)
        # finish --------------------------------------------------------------
        settings_layout.addStretch(1)

    def on_append_to_queue(self):
        return

    def on_queue_control_clicked(self):
        return

    def on_load_item(self, row):
        return

    def update_ui(self):
        """
        # buttons -------------------------------------------------------------
        if self.queue:
            queue_go = self.queue_status.go.read()
            queue_going = self.queue_status.going.read()
            # queue control
            self.queue_control.setDisabled(False)
            if queue_go:
                if queue_going:
                    self.queue_control.set_style("INTERRUPT QUEUE", "stop")
                else:
                    self.queue_control.set_style("STOP QUEUE", "stop")
                    self.message_widget.setText("QUEUE WAITING")
            else:
                self.queue_control.set_style("RUN QUEUE", "go")
                self.message_widget.setText("QUEUE STOPPED")
            # append button
            self.append_button.setDisabled(False)
        """
        # table ---------------------------------------------------------------

        queue_get = zmq_single_request("history_get")[0]
        if self.queue_get["plan_history_uid"] == queue_get["plan_history_uid"]:
            return
        self.queue_get = queue_get
        self.queue = self.queue_get.get("items", [])

        # clear table
        for _ in range(self.table.rowCount()):
            self.table.removeRow(0)

        # add elements from queue
        for i, item in enumerate(self.queue):
            self.table.insertRow(i)
            # index
            index = self.add_index_to_table(i, len(self.queue) - 1)
            # type
            label = pw.Label(item["name"])
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(i, 1, label)
            # status
            label = pw.Label(item["result"]["exit_status"])
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(i, 2, label)
            # started
            if False:  # item.started is not None:
                text = item.started.hms
                label = pw.Label(text)
                label.setAlignment(QtCore.Qt.AlignCenter)
                label.setMargin(3)
                self.table.setCellWidget(i, 3, label)
            # exited
            if False:  # item.exited is not None:
                text = item.exited.hms
                label = pw.Label(text)
                label.setAlignment(QtCore.Qt.AlignCenter)
                label.setMargin(3)
                self.table.setCellWidget(i, 4, label)
            # description
            label = pw.Label(repr(item.get("args", [])) + repr(item.get("kwargs", {})))
            label.setMargin(3)
            label.setToolTip(pprint.pformat(item))
            self.table.setCellWidget(i, 5, label)
            # load
            self.add_button_to_table(i, 7, "LOAD", "go", self.on_load_item)

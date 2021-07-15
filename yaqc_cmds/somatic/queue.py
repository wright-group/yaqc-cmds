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
import yaqc_cmds.somatic as somatic

from . import plan_ui

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
        self.queue = None
        self.queue_get = {"plan_queue_uid": None}
        self.update_ui()
        somatic.signals.queue_updated.connect(self.update_ui)

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
        self.table_cols["Description"] = 200  # expanding
        self.table_cols["Remove"] = 75
        self.table_cols["Load"] = 75
        for i in range(len(self.table_cols.keys())):
            self.table.insertColumn(i)
        labels = list(self.table_cols.keys())
        labels[-1] = ""
        labels[-2] = ""
        self.table.setHorizontalHeaderLabels(labels)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
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
        self.settings_layout = settings_layout
        settings_layout.setMargin(5)
        self.layout.addWidget(settings_scroll_area)
        # adjust queue label
        input_table = pw.InputTable()
        input_table.add("Control Queue", None)
        settings_layout.addWidget(input_table)
        # go button
        self.queue_start = pw.SetButton("START QUEUE")
        self.queue_start.clicked.connect(self.on_queue_start_clicked)
        settings_layout.addWidget(self.queue_start)
        self.queue_stop = pw.SetButton("STOP QUEUE", "advanced")
        self.queue_stop.clicked.connect(self.on_queue_stop_clicked)
        settings_layout.addWidget(self.queue_stop)
        self.interrupt = pw.SetButton("INTERRUPT", "stop")
        self.interrupt.clicked.connect(self.on_interrupt_clicked)
        settings_layout.addWidget(self.interrupt)
        line = pw.Line("H")
        settings_layout.addWidget(line)
        self.clear = pw.SetButton("CLEAR QUEUE", "stop")
        self.clear.clicked.connect(self.on_clear_clicked)
        settings_layout.addWidget(self.clear)
        self.clear_history = pw.SetButton("CLEAR HISTORY", "stop")
        self.clear_history.clicked.connect(self.on_clear_history_clicked)
        settings_layout.addWidget(self.clear_history)
        # horizontal line
        line = pw.Line("H")
        settings_layout.addWidget(line)
        # type combobox
        input_table = pw.InputTable()
        allowed_values = ["plan", "instruction"]
        self.type_combo = pc.Combo(allowed_values=allowed_values)
        self.type_combo.updated.connect(self.update_type)
        input_table.add("Add to Queue", None)
        input_table.add("Type", self.type_combo)
        settings_layout.addWidget(input_table)
        # frames
        self.type_frames = {
            "plan": self.create_plan_frame(),
            "instruction": self.create_instruction_frame(),
        }
        for frame in self.type_frames.values():
            settings_layout.addWidget(frame)
            frame.hide()
        self.update_type()
        # append button
        self.append_button = pw.SetButton("APPEND TO QUEUE")
        self.append_button.clicked.connect(self.on_append_to_queue)
        settings_layout.addWidget(self.append_button)
        # finish --------------------------------------------------------------
        settings_layout.addStretch(1)

    def create_instruction_frame(self):
        button = pw.SetButton("Append Queue Stop")
        button.clicked.connect(
            lambda: zmq_single_request(
                "queue_item_add",
                {
                    "item": {"item_type": "instruction", "name": "queue_stop"},
                    "user_group": "admin",
                    "user": "yaqc-cmds",
                },
            )
        )
        return button

    def create_plan_frame(self):
        frame = QtWidgets.QWidget()
        frame.setLayout(QtWidgets.QVBoxLayout())
        layout = frame.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        input_table = pw.InputTable()
        allowed_plans = zmq_single_request("plans_allowed", {"user_group": "admin"})[0]
        allowed_values = allowed_plans["plans_allowed"].keys()
        self.plan_combo = pc.Combo(allowed_values=allowed_values)
        self.plan_combo.updated.connect(self.on_plan_selected)
        input_table.add("Plan", self.plan_combo)
        layout.addWidget(input_table)
        self.plan_widgets = {x: plan_ui.plan_ui_lookup[x] for x in allowed_values}
        self.on_plan_selected()
        for widget in self.plan_widgets.values():
            layout.addWidget(widget.frame)
        return frame

    def on_append_to_queue(self):
        plan_name = self.plan_combo.read()
        widget = self.plan_widgets[plan_name]
        print(widget.args, widget.kwargs)
        zmq_single_request(
            "queue_item_add",
            {
                "item": {
                    "item_type": "plan",
                    "name": plan_name,
                    "args": widget.args,
                    "kwargs": widget.kwargs,
                },
                "user_group": "admin",
                "user": "yaqc-cmds",
            },
        )

    def on_queue_start_clicked(self):
        zmq_single_request("queue_start")

    def on_queue_stop_clicked(self):
        zmq_single_request("queue_stop")

    def on_interrupt_clicked(self):
        zmq_single_request("re_pause", {"option": "immediate"})
        self.interrupt_choice_window.set_text("Please choose how to proceed.")
        index = self.interrupt_choice_window.show()
        if index == 0:  # RESUME
            zmq_single_request("re_resume")
        elif index == 1:  # SKIP
            zmq_single_request("re_abort")
            time.sleep(0.2)
            zmq_single_request("queue_item_remove", {"pos": "front"})
            time.sleep(0.2)
            zmq_single_request("queue_start")
        elif index == 2:  # HALT
            zmq_single_request("re_abort")

    def on_clear_clicked(self):
        zmq_single_request("queue_clear")

    def on_clear_history_clicked(self):
        zmq_single_request("history_clear")

    def on_index_changed(self, row, new_index):
        if isinstance(row, int):
            index = row
        else:
            index = row.toInt()[0]  # given as QVariant
        item = self.queue[row]
        zmq_single_request("queue_item_move", {"uid": item["item_uid"], "pos_dest": new_index})

    def on_remove_item(self, row):
        if isinstance(row, int):
            index = row
        else:
            index = row.toInt()[0]  # given as QVariant
        item = self.queue[row]
        zmq_single_request("queue_item_remove", {"uid": item["item_uid"]})

    def update_type(self):
        for frame in self.type_frames.values():
            frame.hide()
        self.type_frames[self.type_combo.read()].show()

    def on_plan_selected(self):
        for frame in self.plan_widgets.values():
            frame.frame.hide()
        self.plan_widgets[self.plan_combo.read()].frame.show()

    def update_ui(self):
        # table ---------------------------------------------------------------

        queue_get = zmq_single_request("queue_get")[0]
        if self.queue_get["plan_queue_uid"] == queue_get["plan_queue_uid"]:
            return
        self.queue_get = queue_get
        self.queue = self.queue_get.get("items", [])
        self.running = self.queue_get.get("running_item", {})

        # clear table
        for _ in range(self.table.rowCount()):
            self.table.removeRow(0)

        # add elements from queue
        for i, item in enumerate(self.queue):
            if item == {}:
                continue
            self.table.insertRow(i)
            # index
            index = self.add_index_to_table(i, len(self.queue) - 1)
            # type
            label = pw.Label(item["name"])
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(i, 1, label)
            # status
            label = pw.Label("RUNNING" if item == self.running else "ENQUEUED")
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(i, 2, label)
            # description
            label = pw.Label(repr(item.get("args", [])) + repr(item.get("kwargs", {})))
            label.setMargin(3)
            label.setToolTip(repr(item))
            self.table.setCellWidget(i, 3, label)
            # remove
            button = self.add_button_to_table(i, 4, "REMOVE", "stop", self.on_remove_item)
            # load
            # self.add_button_to_table(i, 7, "LOAD", "go", self.on_load_item)

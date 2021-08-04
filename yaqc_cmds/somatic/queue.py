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
            "QUEUE INTERRUPTED", button_labels=["RESUME", "STOP AFTER PLAN", "STOP NOW"]
        )
        # queue
        self.queue = []
        self.history = []
        self.running = {}
        self.update_ui()
        somatic.signals.queue_updated.connect(self.update_queue)
        somatic.signals.history_updated.connect(self.update_history)

    def add_button_to_table(self, i, j, text, color):
        button = pw.SetButton(text, color=color)
        button.setProperty("TableRowIndex", i)
        self.table.setCellWidget(i, j, button)
        return button

    def add_index_to_table(self, table_index, queue_index, max_value):
        # for some reason, my lambda function does not work when called outside
        # of a dedicated method - Blaise 2016-09-14
        index = QtWidgets.QSpinBox()
        colors = g.colors_dict.read()
        StyleSheet = f"QSpinBox{{color: {colors['text_light']}; font: 14px;}}"
        StyleSheet += f"QScrollArea, QWidget{{background: {colors['background']};  border-color: black; border-radius: 0px;}}"
        StyleSheet += f"QWidget:disabled{{color: {colors['text_disabled']}; font: 14px; border: 0px solid black; border-radius: 0px;}}"
        index.setStyleSheet(StyleSheet)
        # index.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        index.setMaximum(max_value)
        index.setAlignment(QtCore.Qt.AlignCenter)
        index.setValue(queue_index)
        index.setProperty("TableRowIndex", table_index)
        index.editingFinished.connect(
            lambda: self.on_index_changed(queue_index, int(index.value()))
        )
        self.table.setCellWidget(table_index, 0, index)
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
        self.table_cols["Type"] = 150
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
        somatic.signals.queue_relinquishing_control.connect(self.queue_start.show)
        somatic.signals.queue_taking_control.connect(self.queue_start.hide)
        self.interrupt = pw.SetButton("INTERRUPT", "stop")
        self.interrupt.clicked.connect(self.on_interrupt_clicked)
        settings_layout.addWidget(self.interrupt)
        somatic.signals.queue_relinquishing_control.connect(self.interrupt.hide)
        somatic.signals.queue_taking_control.connect(self.interrupt.show)
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

    def on_interrupt_clicked(self):
        zmq_single_request("re_pause", {"option": "immediate"})
        self.interrupt_choice_window.set_text("Please choose how to proceed.")
        index = self.interrupt_choice_window.show()
        if index == 0:  # RESUME
            zmq_single_request("re_resume")
        elif index == 1:  # SKIP
            zmq_single_request("re_resume")
            zmq_single_request("queue_stop")
        elif index == 2:  # HALT
            zmq_single_request("re_abort")
        # TODO Recover skip behavior... may require upstream change to be sane

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

    def on_load_item(self, item):
        self.plan_combo.write(item["name"])
        self.plan_widgets[item["name"]].args = item.get("args", [])
        self.plan_widgets[item["name"]].kwargs = item.get("kwargs", [])

    def update_type(self):
        for frame in self.type_frames.values():
            frame.hide()
        self.type_frames[self.type_combo.read()].show()

    def on_plan_selected(self):
        for frame in self.plan_widgets.values():
            frame.frame.hide()
        self.plan_widgets[self.plan_combo.read()].frame.show()

    def update_queue(self):
        self.queue_get = zmq_single_request("queue_get")[0]
        self.queue = self.queue_get.get("items", [])
        self.running = self.queue_get.get("running_item", {})
        self.update_ui()

    def update_history(self):
        self.history_get = zmq_single_request("history_get")[0]
        self.history = self.history_get.get("items", [])
        self.update_ui()

    def update_ui(self):
        # clear table
        for _ in range(self.table.rowCount()):
            self.table.removeRow(0)

        def add_item(item, status=None, queue_index=None, append=False):
            table_index = self.table.rowCount() if append else 0
            self.table.insertRow(table_index)
            if queue_index is not None:
                self.add_index_to_table(table_index, queue_index, len(self.queue) - 1)
            # type
            label = pw.Label(item["name"])
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(table_index, 1, label)
            # status
            label = pw.Label(item.get("result", {}).get("exit_status", status))
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(3)
            self.table.setCellWidget(table_index, 2, label)
            # description
            label = pw.Label(repr(item.get("args", [])) + repr(item.get("kwargs", {})))
            label.setMargin(3)
            label.setToolTip(pprint.pformat(item))
            label.setDisabled(True)
            self.table.setCellWidget(table_index, 3, label)
            # remove
            if status == "enqueued":
                button = self.add_button_to_table(table_index, 4, "REMOVE", "stop")

                def rem():
                    self.on_remove_item(queue_index)

                button.clicked.connect(rem)
            if status in ("enqueued", "RUNNING"):
                label.setDisabled(False)
            # load
            def load():
                self.on_load_item(item)

            button = self.add_button_to_table(table_index, 5, "LOAD", "go")
            button.clicked.connect(load)

        # add elements from history
        for i, item in enumerate(self.history):
            if item == {}:
                continue
            item = add_item(item)

        if self.running:
            add_item(self.running, "RUNNING")

        # add elements from queue
        for i, item in enumerate(self.queue):
            if item == {}:
                continue
            add_item(item, "enqueued", i)

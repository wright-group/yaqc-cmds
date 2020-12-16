import os
import pathlib
import ast

import appdirs
import numpy as np
import toml
from PySide2 import QtWidgets, QtCore
import WrightTools as wt
import attune

import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.project_globals as g
import yaqc_cmds.hardware.opas as opas
import yaqc_cmds.hardware.spectrometers as spectrometers
import yaqc_cmds.hardware.delays as delays
import yaqc_cmds.hardware.filters as filters
import yaqc_cmds.somatic as somatic


all_hardwares = {}
all_hardwares.update({h.name: h for h in opas.hardwares})
all_hardwares.update({h.name: h for h in spectrometers.hardwares})
all_hardwares.update({h.name: h for h in delays.hardwares})


class CoSetHW:
    def __init__(self, hardware):
        """
        This object contains all of the GUI and state for one low-level tab of the
        autonomic system.
        """
        self.hardware = hardware
        self.state_path = (
            pathlib.Path(appdirs.user_data_dir("yaqc-cmds", "yaqc-cmds"))
            / "autonomic"
            / f"{self.hardware.name}.toml"
        )
        self.state_path.parent.mkdir(exist_ok=True)
        # instrument
        try:
            self.instrument = attune.load(f"autonomic_{self.hardware.name}")
        except ValueError:
            self.instrument = attune.Instrument(
                arrangements={}, setables={}, name=f"autonomic_{self.hardware.name}"
            )
            attune.store(self.instrument)
        # make own widget
        self.widget = QtWidgets.QWidget()
        self.box = QtWidgets.QHBoxLayout()
        self.box.setContentsMargins(0, 10, 0, 0)
        self.widget.setLayout(self.box)
        self.create_frame(self.box)
        # initialize
        self.visit_store()
        self.update_display()

    def create_frame(self, layout):
        # container widget
        display_container_widget = QtWidgets.QWidget()
        display_container_widget.setLayout(QtWidgets.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_scatter = self.plot_widget.add_scatter()
        display_layout.addWidget(self.plot_widget)
        # vertical line
        line = pw.line("V")
        layout.addWidget(line)
        # settings area
        settings_container_widget = QtWidgets.QWidget()
        settings_scroll_area = pw.scroll_area(130)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        # input table
        input_table = pw.InputTable()
        input_table.add("Display", None)
        self.hardware_combobox = pc.Combo()  # which control hardware is currently displayed
        self.hardware_combobox.updated.connect(self.on_hardware_combobox_updated)
        input_table.add("Hardware", self.hardware_combobox)
        self.arrangement_combobox = pc.Combo()  # which arrangement of the control hardware
        self.arrangement_combobox.updated.connect(self.update_display)
        input_table.add("Arrangement", self.arrangement_combobox)
        input_table.add("Settings", None)
        input_table.add("Current Offset", self.hardware.offset)
        settings_layout.addWidget(input_table)
        # control arrangement choice table
        self.control_arrangement_table = pw.InputTable()
        self.control_arrangement_bools = {}
        settings_layout.addWidget(self.control_arrangement_table)
        # button
        self.visit_store_button = pw.SetButton("VISIT STORE", color="go")
        g.queue_control.disable_when_true(self.visit_store_button)
        settings_layout.addWidget(self.visit_store_button)
        # stretch
        settings_layout.addStretch(1)

    def launch(self):
        """
        Apply offsets.
        """
        new = 0
        for control in self.instrument.arrangements.keys():
            if not self.control_arrangement_bools[control].read():
                continue
            position = all_hardwares[control].get_position(all_hardwares[control].native_units)
            note = self.instrument(position, arrangement_name=control)
            try:
                key = all_hardwares[control].driver.client.get_arrangement()
                new += note[key]
            except Exception as e:  # TODO: better exception handling
                new += note["auto"]  # default key
        if g.hardware_initialized.read():
            self.hardware.set_offset(new, self.hardware.native_units)

    def on_control_arrangement_bools_updated(self):
        out = {k: v.read() for k, v in self.control_arrangement_bools.items()}
        with open(self.state_path, "w") as f:
            toml.dump(out, f)

    def on_hardware_combobox_updated(self):
        try:
            current_control_arrangement = self.instrument.arrangements[
                self.hardware_combobox.read()
            ]
            self.arrangement_combobox.set_allowed_values(current_control_arrangement.tunes.keys())
        except KeyError:  # probably an instrument without any arrangements
            pass
        self.update_display()

    def update_display(self):
        try:
            arrangement = self.instrument.arrangements[self.hardware_combobox.read()]
            tune = arrangement.tunes[self.arrangement_combobox.read()]
        except KeyError:  # probably an empty instrument
            return
        self.plot_widget.set_labels(tune.ind_units, tune.dep_units)
        self.plot_scatter.clear()
        self.plot_scatter.setData(tune.independent, tune.dependent)

    def visit_store(self):
        self.instrument = attune.load(f"autonomic_{self.hardware.name}")
        # update hardware combobox options
        self.hardware_combobox.set_allowed_values(self.instrument.arrangements.keys())
        self.on_hardware_combobox_updated()
        # add new checkboxes if needed
        for control_name in self.instrument.arrangements.keys():
            if control_name in self.control_arrangement_bools.keys():
                continue
            checkbox = pc.Bool()
            self.control_arrangement_table.add(control_name, checkbox)
            self.control_arrangement_bools[control_name] = checkbox
            checkbox.updated.connect(self.on_control_arrangement_bools_updated)
        # update checkboxes based on saved state
        if not self.state_path.exists():
            self.on_control_arrangement_bools_updated()  # initializes state as false
        for k, v in toml.load(self.state_path).items():
            if k in self.control_arrangement_bools.keys():
                self.control_arrangement_bools[k].write(v)
        self.update_display()

    def zero(self):
        """
        Offsets to zero for all corrs based on current positions.
        """
        instr = self.instrument
        for control in self.instrument.arrangements.keys():
            if not self.control_arrangement_bools[control].read():
                continue
            try:
                tune = all_hardwares[control].driver.client.get_arrangement()
                print(tune)
            except (AttributeError, KeyError) as e:
                print(e)
                tune = "auto"
            print(instr[control].keys(), tune)
            instr = attune.offset_to(
                instr, control, tune, 0, all_hardwares[control].get_position()
            )
        attune.store(instr)
        somatic.signals.updated_attune_store.emit()


coset_hardwares = []  # gets filled by GUI.create_hardware_frame


class Control:
    def __init__(self):
        pass

    def launch(self):
        for coset_hardware in coset_hardwares:
            coset_hardware.launch()

    def visit_store(self):
        for coset_hardware in coset_hardwares:
            coset_hardware.visit_store()

    def zero(self, hardware_name):
        """
        Offsets to zero forr all corrs based on current positions.
        """
        for coset_harware in coset_hardwares:
            if coset_harware.hardware.name == hardware_name:
                coset_harware.zero()
                break


control = Control()
g.hardware_waits.give_coset_control(control)
g.coset_control.write(control)
somatic.signals.updated_attune_store.connect(control.visit_store)


class GUI(QtCore.QObject):
    def __init__(self):
        """Top-level GUI"""
        QtCore.QObject.__init__(self)
        self.create_frame()

    def create_frame(self):
        # get parent layout
        parent_widget = g.coset_widget.read()
        parent_widget.setLayout(QtWidgets.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        parent_layout = parent_widget.layout()
        # create own layout
        self.tabs = QtWidgets.QTabWidget()
        # OPAs
        if len(opas.hardwares) > 0:
            self.create_hardware_frame("OPAs", opas.hardwares)
        # spectrometers
        if len(spectrometers.hardwares) > 0:
            self.create_hardware_frame("Spectrometers", spectrometers.hardwares)
        # delays
        if len(delays.hardwares) > 0:
            self.create_hardware_frame("Delays", delays.hardwares)
        # filters
        if len(filters.hardwares) > 0:
            self.create_hardware_frame("Filters", filters.hardwares)
        parent_layout.addWidget(self.tabs)

    def create_hardware_frame(self, name, hardwares):
        container_widget = QtWidgets.QWidget()
        container_box = QtWidgets.QHBoxLayout()
        container_box.setContentsMargins(0, 10, 0, 0)
        container_widget.setLayout(container_box)
        self.tabs.addTab(container_widget, name)
        # sub-tabs
        tabs = pw.TabWidget()
        container_box.addWidget(tabs)
        for hardware in hardwares:
            coset_hardware = CoSetHW(hardware)
            coset_hardwares.append(coset_hardware)
            tabs.addTab(coset_hardware.widget, hardware.name)


gui = GUI()

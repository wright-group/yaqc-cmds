### import ####################################################################

import os
import pathlib
import ast
import collections

import numpy as np

import scipy

from PyQt4 import QtGui, QtCore

import WrightTools as wt

import project
import project.classes as pc
import project.widgets as pw
import project.project_globals as g

# hardwares (also ensure present in GUI)
import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import hardware.delays.delays as delays
import hardware.filters.filters as filters
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares

main_dir = g.main_dir.read()
ini = project.ini_handler.Ini(os.path.join(main_dir, 'autonomic', 'coset.ini'))
ini.return_raw = True

# ensure that all elements are in the ini file
all_hardware_names = [hw.name for hw in all_hardwares]
ini.config.read(ini.filepath)
for section in all_hardware_names:
    if not ini.config.has_section(section):
        ini.config.add_section(section)
        ini.write(section, 'offset', 0.)
    # 'use' bool
    if not ini.config.has_option(section, 'use'):
        ini.write(section, 'use', False)
    # hardware names
    for option in all_hardware_names:
        if not section == option:
            if not ini.config.has_option(section, option):
                ini.write(section, option, None)
                ini.write(section, option + ' offset', 0.)


### objects ###################################################################


class Corr:

    def __init__(self, path):
        self.path = path
        # headers
        self.headers = collections.OrderedDict()
        for line in open(self.path):
            if line[0] == '#':
                split = line.split(':')
                key = split[0][2:]
                item = split[1].split('\t')
                if item[0] == '':
                    item = [item[1]]
                item = [i.strip() for i in item]  # remove dumb things
                item = [ast.literal_eval(i) for i in item]
                if len(item) == 1:
                    item = item[0]
                self.headers[key] = item
            else:
                # all header lines are at the beginning
                break
        self.offset_name = self.headers['offset']
        self.offset_units = self.headers['offset units']
        self.control_name = self.headers['control']
        self.control_units = self.headers['control units']
        # control hardware object
        self.control_hardware = [hw for hw in all_hardwares if hw.name == self.control_name][0]
        # array
        arr = np.genfromtxt(self.path).T
        self.control_points = arr[0]
        self.offset_points = arr[1]
        # initial offset
        change = float(ini.read(self.offset_name, self.control_name + ' offset'))
        self.offset_points -= change
        self.interpolate()

    def evaluate(self):
        '''
        Get the current corrections.
        '''
        control_position = self.control_hardware.get_destination(self.control_units)
        # coerce control position to be within control_points array
        control_position = np.clip(
            control_position, self.control_points.min(), self.control_points.max())
        out = self.function(control_position)
        return out

    def interpolate(self):
        '''
        Generate interpolation function.
        '''
        self.function = scipy.interpolate.interp1d(self.control_points, self.offset_points)

    def zero(self):
        '''
        Zero based on current positions.
        '''
        change = self.evaluate()
        self.offset_points -= change
        self.interpolate()
        return change


class CoSetHW:

    def __init__(self, hardware):
        self.hardware = hardware
        # directly write stored offset to hardware
        stored_offset = float(ini.read(self.hardware.name, 'offset'))
        self.hardware.offset.write(stored_offset)
        self.corrs = []
        # make own widget
        self.widget = QtGui.QWidget()
        self.box = QtGui.QHBoxLayout()
        self.box.setContentsMargins(0, 10, 0, 0)
        self.widget.setLayout(self.box)
        self.create_frame(self.box)
        # load files
        ini.config.read(ini.filepath)
        for option in ini.config.options(self.hardware.name):
            if 'offset' in option:
                continue
            value = ini.read(self.hardware.name, option)
            if value not in ['None', 'False', 'True']:
                value = value[1:]
                value = value[:-1]
                self.load_file(value)
        stored_use_state = ast.literal_eval(ini.read(self.hardware.name, 'use'))
        self.use_bool.write(stored_use_state)
        # initialize
        self.update_display()
        self.update_use_bool()

    def add_table_row(self, corr):
        # insert into table
        new_row_index = self.table.rowCount()
        self.table.insertRow(new_row_index)
        # hardware
        label = pw.Label(corr.headers['control'])
        label.setMargin(3)
        self.table.setCellWidget(new_row_index, 0, label)
        # path
        _, name, _ = wt.kit.filename_parse(corr.path)
        name = pathlib.Path(corr.path).stem
        label = pw.Label(name)
        label.setMargin(3)
        label.setToolTip(corr.path)
        self.table.setCellWidget(new_row_index, 1, label)
        # button
        button = pw.SetButton('REMOVE', color='stop')
        g.queue_control.disable_when_true(button)
        button.setProperty('TableRowIndex', new_row_index)
        button.clicked.connect(lambda: self.on_remove_file(button.property('TableRowIndex')))
        self.table.setCellWidget(new_row_index, 2, button)

    def create_frame(self, layout):
        # container widget
        display_container_widget = QtGui.QWidget()
        display_container_widget.setLayout(QtGui.QVBoxLayout())
        display_layout = display_container_widget.layout()
        display_layout.setMargin(0)
        layout.addWidget(display_container_widget)
        # plot
        self.plot_widget = pw.Plot1D()
        self.plot_scatter = self.plot_widget.add_scatter()
        display_layout.addWidget(self.plot_widget)
        # vertical line
        line = pw.line('V')
        layout.addWidget(line)
        # settings area
        settings_container_widget = QtGui.QWidget()
        settings_scroll_area = pw.scroll_area(130)
        settings_scroll_area.setWidget(settings_container_widget)
        settings_scroll_area.setMinimumWidth(300)
        settings_scroll_area.setMaximumWidth(300)
        settings_container_widget.setLayout(QtGui.QVBoxLayout())
        settings_layout = settings_container_widget.layout()
        settings_layout.setMargin(5)
        layout.addWidget(settings_scroll_area)
        # input table
        input_table = pw.InputTable()
        input_table.add('Display', None)
        self.display_combobox = pc.Combo()
        self.display_combobox.updated.connect(self.update_display)
        input_table.add('Hardware', self.display_combobox)
        input_table.add('Settings', None)
        self.use_bool = pc.Bool()
        self.use_bool.updated.connect(self.on_toggle_use)
        g.queue_control.disable_when_true(self.use_bool)
        input_table.add('Use', self.use_bool)
        input_table.add('Current Offset', self.hardware.offset)
        settings_layout.addWidget(input_table)
        # add button
        self.add_button = pw.SetButton('ADD FILE', color='go')
        self.add_button.clicked.connect(self.on_add_file)
        g.queue_control.disable_when_true(self.add_button)
        settings_layout.addWidget(self.add_button)
        # table
        self.table = pw.TableWidget()
        self.table.verticalHeader().hide()
        self.table.insertColumn(0)
        self.table.insertColumn(1)
        self.table.insertColumn(2)
        self.table.setHorizontalHeaderLabels(['Hardware', 'File Name', ''])
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setStretchLastSection(True)
        settings_layout.addWidget(self.table)

    def launch(self):
        '''
        Apply offsets.
        '''
        if self.use_bool.read():
            corr_results = [wt.units.converter(
                corr.evaluate(), corr.offset_units, self.hardware.native_units) for corr in self.corrs]
            new_offset = np.sum(corr_results)
            if g.hardware_initialized.read():
                self.hardware.set_offset(new_offset, self.hardware.native_units)
                ini.write(self.hardware.name, 'offset', new_offset)

    def load_file(self, path):
        '''
        Load a file.
        '''
        corr = Corr(path)
        self.corrs.append(corr)
        self.add_table_row(corr)
        self.update_combobox()
        self.update_use_bool()
        return corr

    def on_add_file(self):
        '''
        Add a file through file dialog.
        '''
        # get filepath
        caption = 'Import a coset file'
        directory = os.path.join(g.main_dir.read(), 'coset', 'files')
        options = 'COSET (*.coset);;All Files (*.*)'
        path = project.file_dialog_handler.open_dialog(caption, directory, options)
        if not os.path.isfile(path):  # presumably user canceled
            return
        corr = Corr(path)  # this object is throwaway
        if not corr.offset_name == self.hardware.name:
            print('incorrect hardware')
            return
        for i, loaded_corr in enumerate(self.corrs):
            if loaded_corr.control_name == corr.control_name:  # will not allow two of same control
                self.unload_file(i)  # unload old one
                break  # should only be one
        # load in
        self.load_file(path)
        ini.write(self.hardware.name, corr.control_name, corr.path, with_apostrophe=True)
        self.display_combobox.write(corr.control_name)

    def on_remove_file(self, row):
        '''
        Fires when one of the REMOVE buttons gets pushed.
        '''
        # get row as int (given as QVariant)
        try:
            row = row.toInt()[0]
        except AttributeError:
            pass # already an int?
        self.unload_file(row)

    def on_toggle_use(self):
        ini.write(self.hardware.name, 'use', self.use_bool.read())
        if self.use_bool.read():
            self.launch()
        else:
            if g.hardware_initialized.read():
                self.hardware.set_offset(0., self.hardware.native_units)
                ini.write(self.hardware.name, 'offset', 0.)

    def unload_file(self, index):
        removed_corr = self.corrs.pop(index)
        ini.write(self.hardware.name, removed_corr.headers['control'], None)
        ini.write(self.hardware.name, removed_corr.control_name + ' offset', 0.)
        # clear table
        for i in range(self.table.rowCount()):
            self.table.removeRow(0)
        # remake table
        for corr in self.corrs:
            self.add_table_row(corr)
        self.update_combobox()
        self.update_use_bool()

    def update_combobox(self):
        if len(self.corrs) == 0:
            allowed_values = [None]
        else:
            allowed_values = [corr.headers['control'] for corr in self.corrs]
        self.display_combobox.set_allowed_values(allowed_values)
        self.update_display()

    def update_use_bool(self):
        if len(self.corrs) == 0:
            self.use_bool.write(False)
            self.use_bool.set_disabled(True)
        else:
            self.use_bool.set_disabled(False)

    def update_display(self):
        if len(self.corrs) > 0:
            corr = self.corrs[self.display_combobox.read_index()]
            xi = corr.control_points
            yi = corr.offset_points
            x_label = corr.control_name + ' (' + corr.control_units + ')'
            y_label = corr.offset_name + ' (' + corr.offset_units + ')'
            self.plot_widget.set_labels(x_label, y_label)
            self.plot_scatter.clear()
            self.plot_scatter.setData(xi, yi)
        else:
            # this doesn't work as expected, but that isn't crucial right now
            # - Blaise 2015.10.24
            self.plot_widget.set_labels('', '')
            self.plot_scatter.clear()
            self.plot_widget.update()
            self.plot_scatter.update()

    def zero(self):
        '''
        Offsets to zero for all corrs based on current positions.
        '''
        for corr in self.corrs:
            change = corr.zero()
            # record the total change in ini file
            old_change = float(ini.read(self.hardware.name, corr.control_name + ' offset'))
            new_change = old_change + change
            ini.write(self.hardware.name, corr.control_name + ' offset', new_change)
        self.launch()
        self.update_display()


coset_hardwares = []  # list to contain all coset hardware objects


### control ###################################################################


class Control():

    def __init__(self):
        pass

    def launch(self):
        for coset_hardware in coset_hardwares:
            coset_hardware.launch()

    def zero(self, hardware_name):
        '''
        Offsets to zero forr all corrs based on current positions.
        '''
        for coset_harware in coset_hardwares:
            if coset_harware.hardware.name == hardware_name:
                coset_harware.zero()
                break


control = Control()
g.hardware_waits.give_coset_control(control)
g.coset_control.write(control)

### gui #######################################################################


class GUI(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.create_frame()

    def create_frame(self):
        # get parent layout
        parent_widget = g.coset_widget.read()
        parent_widget.setLayout(QtGui.QHBoxLayout())
        parent_widget.layout().setContentsMargins(0, 10, 0, 0)
        parent_layout = parent_widget.layout()
        # create own layout
        self.tabs = QtGui.QTabWidget()
        # OPAs
        if len(opas.hardwares) > 0:
            self.create_hardware_frame('OPAs', opas.hardwares)
        # spectrometers
        if len(spectrometers.hardwares) > 0:
            self.create_hardware_frame('Spectrometers', spectrometers.hardwares)
        # delays
        if len(delays.hardwares) > 0:
            self.create_hardware_frame('Delays', delays.hardwares)
        # filters
        if len(filters.hardwares) > 0:
            self.create_hardware_frame('Filters', filters.hardwares)
        parent_layout.addWidget(self.tabs)

    def create_hardware_frame(self, name, hardwares):
        container_widget = QtGui.QWidget()
        container_box = QtGui.QHBoxLayout()
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


### testing ###################################################################


if __name__ == '__main__':
    pass

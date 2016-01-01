'''
Acquisition infrastructure shared by all modules.
'''


### import ####################################################################


import os
import sys
import imp
import time
import copy
import collections
import ConfigParser

import numpy as np

import numexpr

from PyQt4 import QtCore, QtGui

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
app = g.app.read()


### import hardware control ###################################################


import spectrometers.spectrometers as spectrometers
import delays.delays as delays
import opas.opas as opas
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares

import daq.daq as daq


### container objects #########################################################


class Axis:
    
    def __init__(self, points, units, name, identity, hardware_dict={}, **kwargs):
        self.points = points
        self.units = units
        self.name = name
        self.identity = identity
        self.hardware_dict = hardware_dict.copy()
        self.__dict__.update(kwargs)
        # fill hardware dictionary with defaults
        names, operators = wt.kit.parse_identity(self.identity)
        if 'F' in operators:  # last name should be a 'following' in this case
            names.pop(-1)
        for name in names:
            if name.replace('D', '') not in self.hardware_dict.keys():
                hardware_object = [h for h in all_hardwares if h.friendly_name == name.replace('D', '')][0]
                self.hardware_dict[name] = [hardware_object, 'set_position', None]

        
class Constant:
    
    def __init__(self, units, name, identity, static=True, expression=''):
        self.units = units
        self.name = name
        self.identity = identity
        self.static = static
        self.expression = expression
        self.hardware = [h for h in all_hardwares if h.friendly_name == self.name][0]


class Destinations:
    
    def __init__(self, arr, units, hardware, method, passed_args):
        self.arr = arr
        self.units = units
        self.hardware = hardware
        self.method = method
        self.passed_args = passed_args


class Order:
    
    def __init__(self, name, path):
        self.name = name
        self.module = imp.load_source(name, path)
        self.process = self.module.process

orderers = []
config = ConfigParser.SafeConfigParser()
config.read(r'modules\order\order.ini')
for name in config.options('load'):
    if config.get('load', name) == 'True':
        path = os.path.join(g.main_dir.read(), 'modules', 'order', name + '.py')
        orderers.append(Order(name, path))


### scan objects ##############################################################


class Address(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    
    def __init__(self, scan):
        '''
        Hidden class. Runs in special scan thread.
        '''
        QtCore.QObject.__init__(self)
        self.scan = scan
        self.fraction_complete = scan.fraction_complete
        self.go = scan.go
        self.going = scan.going
        self.pause = scan.pause
        self.paused = scan.paused
    
    @QtCore.pyqtSlot(collections.OrderedDict)
    def run(self, scan_dictionary):

        # create destination objects ------------------------------------------

        # get destination arrays
        axes = scan_dictionary['axes']
        if len(axes) == 1:
            arrs = [axes[0].points]
        else:
            arrs = np.meshgrid(*[a.points for a in axes], indexing='ij')

        # treat 'scan about center' axes
        for axis_index, axis in enumerate(axes):
            if 'D' in axis.identity:
                centers = axis.centers
                centers_follow = axis.centers_follow
                centers_follow_index = [a.name for a in axes].index(centers_follow)
                # transpose so following index is last
                transpose_order = range(len(axes))
                transpose_order[-1] = centers_follow_index
                transpose_order[centers_follow_index] = len(transpose_order)-1
                arrs[axis_index] = np.transpose(arrs[axis_index], axes=transpose_order)
                # add centers to transposed array
                arrs[axis_index] += centers
                # transpose out
                arrs[axis_index] = np.transpose(arrs[axis_index], axes=transpose_order)
                
        # create destination objects
        destinations_list = []
        for i in range(len(axes)):
            axis = axes[i]
            arr = arrs[i]
            for key in axis.hardware_dict.keys():
                hardware = axis.hardware_dict[key][0]
                method = axis.hardware_dict[key][1]
                passed_args = axis.hardware_dict[key][2]
                destinations = Destinations(arr, axis.units, hardware, method, passed_args)
                destinations_list.append(destinations)
                
        # add constants
        constants = scan_dictionary['constants']
        for constant in constants:
            if constant.static:
                pass
            else:
                # initialize
                expression = constant.expression
                arr = np.full(arrs[0].shape, np.nan)
                # set vals
                vals = {}
                for hardware in all_hardwares:
                    vals[hardware.friendly_name] = hardware.get_position()
                for idx in np.ndindex(arrs[0].shape):
                    for destination in destinations_list:
                        vals[destination.hardware.friendly_name] = destination.arr[idx]
                    arr[idx] = numexpr.evaluate(expression, vals)
                # finish
                units = constant.units
                hardware = constant.hardware
                destinations = Destinations(arr, units, hardware, 'set_position', None)
                destinations_list.append(destinations)

        # check if scan is valid for hardware ---------------------------------
                
        # TODO: !!!

        # run through aquisition order handler --------------------------------

        order = orderers[self.scan.aquisition_order_combo.read_index()]
        idxs, slices = order.process(destinations_list)
        
        # initialize scan -----------------------------------------------------
        
        g.module_control.write(True)
        self.going.write(True)
        self.fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', '')
        
        # initialize DAQ
        header_dictionary = collections.OrderedDict()
        header_dictionary['PyCMDS version'] = g.version.read()
        header_dictionary['system name'] = g.system_name.read()
        header_dictionary['file created'] = wt.kit.get_timestamp()
        header_dictionary['data name'] = self.scan.daq_widget.name.read()
        header_dictionary['data info'] = self.scan.daq_widget.info.read()
        header_dictionary['data origin'] = self.scan.gui.module_name
        header_dictionary['axis names'] = [a.name for a in axes]
        header_dictionary['axis identities'] = [a.identity for a in axes]
        header_dictionary['axis units'] = [a.units for a in axes]
        for axis in axes:
            header_dictionary[axis.name + ' points'] = axis.points
            if 'D' in axis.identity:
                header_dictionary[axis.name + ' centers'] = axis.centers
        if self.scan.daq_widget.use_array.read():
            header_dictionary['axis names'].append('wa')
            header_dictionary['wa points'] = np.linspace(-1000, 3000, 256)
            header_dictionary['axis units'].append('wn')
            if 'wm' in header_dictionary['axis names']:
                header_dictionary['axis identities'].append('Dwa')
                for axis in axes:
                    if axis.name == 'wm':
                        header_dictionary['wa centers'] = axis.points
            else:
                header_dictionary['axis identities'].append('wa')
        header_dictionary['constant names'] = [c.name for c in constants]
        header_dictionary['constant identities'] = [c.identity for c in constants]
        header_dictionary['shots'] = self.scan.daq_widget.shots.read()
        daq.control.initialize_scan(header_dictionary, self.scan.daq_widget)
        
        # acquire -------------------------------------------------------------
        
        npts = float(len(idxs))
        for i, idx in enumerate(idxs):
            idx = tuple(idx)
            daq.idx.write(idx)
            # launch hardware
            for d in destinations_list:
                print d.method
                destination = d.arr[idx]
                if d.method == 'set_position':
                    d.hardware.set_position(destination, d.units)
                else:
                    inputs = copy.copy(d.passed_args)
                    for input_index, input_val in enumerate(inputs):
                        if input_val == 'destination':
                            inputs[input_index] = destination
                        elif input_val == 'units':
                            inputs[input_index] = d.units
                    d.hardware.q.push(d.method, inputs)
            # execute pre_wait_methods
            for method in scan_dictionary['pre_wait_methods']:
                method()
            # wait for hardware
            g.hardware_waits.wait()
            # launch DAQ
            daq.control.acquire()
            # wait for DAQ
            daq.control.wait_until_daq_done()
            # update
            self.fraction_complete.write(i/npts)
            self.update_ui.emit()
            # check continue
            if not self.check_continue():
                break
        
        # finish scan ---------------------------------------------------------

        self.fraction_complete.write(1.)    
        self.going.write(False)
        g.module_control.write(False)
        g.logger.log('info', 'Scan done', '')
        self.update_ui.emit()
        self.done.emit()
        
    def check_continue(self):
        while self.pause.read(): 
            self.paused.write(True)
            self.pause.wait_for_update()
        self.paused.write(False)
        return self.go.read()


class Scan(QtCore.QObject):

    def __init__(self, gui):
        '''
        Control class for scan operations. Runs in main thread.
        '''
        QtCore.QObject.__init__(self)
        self.gui = gui
        # mutex objects
        self.fraction_complete = pc.Mutex()
        self.go = pc.Busy()
        self.going = pc.Busy()
        self.pause = pc.Busy()
        self.paused = pc.Busy()
        # address object exists in the shared scan thread   
        self.address = Address(self)
        scan_thread = g.scan_thread.read()
        self.address.moveToThread(scan_thread)
        self.update_ui = self.address.update_ui
        self.update_ui.connect(self.update)
        self.done = self.address.done
        # widget
        self.create_widget()
        # connections
        g.shutdown.read().connect(self.stop)
        
    def create_widget(self):
        self.widget = QtGui.QWidget()
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        # aquisition order combobox
        allowed_values = [o.name for o in orderers]
        self.aquisition_order_combo = pc.Combo(allowed_values=allowed_values)
        g.module_control.disable_when_true(self.aquisition_order_combo)
        input_table = pw.InputTable()
        input_table.add('Acquisition', None)
        input_table.add('Order', self.aquisition_order_combo)
        self.layout.addWidget(input_table)
        # daq widget
        self.daq_widget = daq.Widget()
        self.layout.addWidget(self.daq_widget)
        # go button
        self.go_button = pw.module_go_button()
        self.go_button.give_stop_scan_method(self.stop)  
        self.go_button.give_scan_complete_signal(self.address.done)
        self.go_button.give_pause_objects(self.pause, self.paused)
        self.layout.addWidget(self.go_button)
        # finish
        self.widget.setLayout(self.layout)

    def launch(self, axes, constants=[], pre_wait_methods=[]):
        '''
        Launch a scan.
        
        Parameters
        ----------
        axes : list of Axis objects
            As a guideline (obviously this depends on the order module used), 
            the aquisition is taken so that the trailing axis is the innermost
            loop (matrix indexing).
        constants : list of Constant objects (optional)
            Constants...
        '''
        self.go.write(True)
        scan_dictionary = collections.OrderedDict()
        scan_dictionary['origin'] = self.gui.module_name
        scan_dictionary['axes'] = axes
        scan_dictionary['constants'] = constants
        scan_dictionary['pre_wait_methods'] = pre_wait_methods
        QtCore.QMetaObject.invokeMethod(self.address, 'run', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(collections.OrderedDict, scan_dictionary))    
        g.progress_bar.begin_new_scan_timer()
    
    def stop(self):
        self.go.write(False)
        while self.going.read(): 
            self.going.wait_for_update()
        
    def update(self):
        g.progress_bar.set_fraction(self.fraction_complete.read())


### gui base class ############################################################


class GUI(QtCore.QObject):

    def __init__(self, module_name):
        QtCore.QObject.__init__(self)
        self.module_name = module_name
        # create scan object
        self.scan = Scan(self)
        self.scan.update_ui.connect(self.update)
        self.scan.done.connect(self.on_done)
        self.scan.go_button.give_launch_scan_method(self.launch_scan)
        # create frame
        self.create_frame()
        self.create_advanced_frame()
        self.show_frame()  # check once at startup
        
    def create_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtGui.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def create_advanced_frame(self):
        layout = QtGui.QVBoxLayout()
        layout.setMargin(5)
        # finish
        self.advanced_frame = QtGui.QWidget()   
        self.advanced_frame.setLayout(layout)
        g.module_advanced_widget.add_child(self.advanced_frame)

    def show_frame(self):
        self.frame.hide()
        self.advanced_frame.hide()
        if g.module_combobox.get_text() == self.module_name:
            self.frame.show()
            self.advanced_frame.show()

    def launch_scan(self):
        pass
        
    def on_done(self):
        '''
        Make pickle and figures.
        '''
        # get path
        data_path = daq.data_path.read() 
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        data.save(data_path.replace('.data', '.p'), verbose=False)
        # chop data if over 2D
        if len(data.shape) > 2:
            chopped_datas = data.chop(0, 1, verbose=False)
        # make figures for each channel
        data_folder, file_name, file_extension = wt.kit.filename_parse(data_path)
        # chop data if over 2D
        for channel_index, channel_name in enumerate(data.channel_names):
            image_fname = channel_name + ' ' + file_name
            if len(data.shape) == 1:
                artist = wt.artists.mpl_1D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            elif len(data.shape) == 2:
                artist = wt.artists.mpl_2D(data, verbose=False)
                artist.plot(channel_index, autosave=True, output_folder=data_folder,
                            fname=image_fname, verbose=False)
            else:
                channel_folder = os.path.join(data_folder, channel_name)
                os.mkdir(channel_folder)
                for index, chopped_data in enumerate(chopped_datas):
                    this_image_fname = image_fname + str(index).zfill(3)
                    artist = wt.artists.mpl_2D(chopped_data, verbose=False)
                    artist.plot(channel_index, autosave=True, output_folder=channel_folder,
                                fname=this_image_fname, verbose=False)
                    g.app.read().processEvents()  # gui should not hang...
            # hack in a way to get the first image written
            if channel_index == 0:
                output_image_path = os.path.join(data_folder, image_fname + ' 000.png')
        # send message on slack
        if g.slack_enabled.read():
            slack = g.slack_control.read()
            slack.send_message('scan complete - {} elapsed'.format(g.progress_bar.time_elapsed.text()))
            if len(data.shape) < 3:
                print output_image_path
                slack.upload_file(output_image_path)
                    
        
    def update(self):
        pass

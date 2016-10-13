'''
Acquisition infrastructure shared by all modules.
'''


### import ####################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import imp
import time
import copy
import shutil
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

import hardware.spectrometers.spectrometers as spectrometers
import hardware.delays.delays as delays
import hardware.opas.opas as opas
all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares

import devices.devices as devices


### define ####################################################################


app = g.app.read()

somatic_folder = os.path.dirname(__file__)


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
            if name[0] == 'D':
                clean_name = name.replace('D', '', 1)
            else:
                clean_name = name
            if clean_name not in self.hardware_dict.keys():
                hardware_object = [h for h in all_hardwares if h.friendly_name == clean_name][0]
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
p = os.path.join(somatic_folder, 'order', 'order.ini')
config.read(p)
for name in config.options('load'):
    if config.get('load', name) == 'True':
        path = os.path.join(somatic_folder, 'order', name + '.py')
        orderers.append(Order(name, path))


### Worker base ##############################################################


class Worker(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    scan_complete = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    
    def __init__(self, aqn_path, queue_worker, finished):
        # do not overload this method
        QtCore.QObject.__init__(self)
        self.aqn_path = aqn_path
        self.aqn = wt.kit.INI(self.aqn_path)
        self.queue_worker = queue_worker
        self.finished = finished
        # unpack
        self.fraction_complete = self.queue_worker.fraction_complete
        self.pause = self.queue_worker.queue_status.pause
        self.paused = self.queue_worker.queue_status.paused
        self.going = self.queue_worker.queue_status.going
        self.stop = self.queue_worker.queue_status.stop
        self.stopped = self.queue_worker.queue_status.stopped
        # create acquisition folder
        self.folder = self.aqn_path[:-4]
        os.mkdir(self.folder)
        # initialize
        self.scan_index = None
        self.scan_folders = []
        self.scan_urls = []
        
    def process(self, scan_folder):
        # get path
        data_path = devices.data_path.read() 
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
        # upload
        self.upload(self.scan_folders[self.scan_index], reference_image=output_image_path)

    def scan(self, axes, pre_wait_methods=[], constants=[],
             processing_method='process', module_reserved=''):
        # do not overload this method
        # scan index ----------------------------------------------------------
        if self.scan_index is None:
            self.scan_index = 0
        else:
            self.scan_index += 1
        # create destination objects ------------------------------------------
        # get destination arrays
        if len(axes) == 1:
            arrs = [axes[0].points]
        else:
            arrs = np.meshgrid(*[a.points for a in axes], indexing='ij')
        # treat 'scan about center' axes
        for axis_index, axis in enumerate(axes):
            if axis.identity[0] == 'D':
                centers = axis.centers
                # transpose so own index is first
                transpose_order = range(len(axes))
                transpose_order[0] = axis_index
                transpose_order[axis_index] = 0
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
        order = orderers[0]  # TODO: real orderer support
        idxs, slices = order.process(destinations_list)
        # initialize scan -----------------------------------------------------       
        g.queue_control.write(True)
        self.going.write(True)
        self.fraction_complete.write(0.)
        g.logger.log('info', 'Scan begun', '')
        # put info into headers -----------------------------------------------
        # clear values from previous scan
        devices.headers.clear()
        # data info
        devices.headers.data_info['data name'] = self.aqn.read('info', 'name')
        devices.headers.data_info['data info'] = self.aqn.read('info', 'info')
        devices.headers.data_info['data origin'] = self.aqn.read('info', 'module')
        # axes (will be added onto in devices, potentially)
        devices.headers.axis_info['axis names'] = [a.name for a in axes]
        devices.headers.axis_info['axis identities'] = [a.identity for a in axes]
        devices.headers.axis_info['axis units'] = [a.units for a in axes]
        devices.headers.axis_info['axis interpolate'] = [False for a in axes]
        for axis in axes:
            devices.headers.axis_info[axis.name + ' points'] = axis.points
            if axis.identity[0] == 'D':
                devices.headers.axis_info[axis.name + ' centers'] = axis.centers
        # constants
        devices.headers.constant_info['constant names'] = [c.name for c in constants]
        devices.headers.constant_info['constant identities'] = [c.identity for c in constants]
        # create scan folder
        scan_index_str = str(self.scan_index).zfill(3)
        axis_names = str([str(a.name) for a in axes]).replace('\'', '')
        scan_folder_name = ' '.join([scan_index_str, axis_names, module_reserved]).rstrip()
        scan_folder = os.path.join(self.folder, scan_folder_name)
        os.mkdir(scan_folder)
        self.scan_folders.append(scan_folder)
        # create scan folder on google drive
        if g.google_drive_enabled.read():
            scan_url = g.google_drive_control.read().create_folder(scan_folder)
            self.scan_urls.append(scan_url)
        else:
            self.scan_urls.append(None)
        # add urls to headers
        if g.google_drive_enabled.read():
            devices.headers.scan_info['queue url'] = self.queue_worker.queue_url
            devices.headers.scan_info['acquisition url'] = self.aqn.read('info', 'url')
            devices.headers.scan_info['scan url'] = scan_url
        # initialize devices
        devices.control.initialize_scan(self.aqn, scan_folder, destinations_list)
        # acquire -------------------------------------------------------------
        slice_index = 0
        npts = float(len(idxs))
        for i, idx in enumerate(idxs):
            idx = tuple(idx)
            devices.idx.write(idx)
            # launch hardware
            for d in destinations_list:
                print(d.method)
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
            for method in pre_wait_methods:
                method()
            # slice
            if slice_index < len(slices):  # takes care of last slice
                if slices[slice_index]['index'] == i:
                    devices.current_slice.index(slices[slice_index])
                    slice_index += 1
            # wait for hardware
            g.hardware_waits.wait()
            # launch devices
            devices.control.acquire(save=True)
            # wait for devices
            devices.control.wait_until_done()
            # update
            self.fraction_complete.write(i/npts)
            self.update_ui.emit()
            # check continue
            while self.pause.read(): 
                self.paused.write(True)
                self.pause.wait_for_update()
            self.paused.write(False)
            if self.stop.read():
                self.stopped.write(True)
                break
        # finish scan ---------------------------------------------------------
        devices.control.wait_until_file_done()
        self.fraction_complete.write(1.)  
        self.going.write(False)
        g.queue_control.write(False)
        g.logger.log('info', 'Scan done', '')
        self.update_ui.emit()
        self.scan_complete.emit()
        # process scan --------------------------------------------------------
        getattr(self, processing_method)(scan_folder)
    
    def upload(self, scan_folder, message='scan complete', reference_image=None):
        # create folder on google drive, upload reference image
        if g.google_drive_enabled.read():
            folder_url, image_url = g.google_drive_control.read().upload_scan(scan_folder, reference_image)
        else:
            folder_url = image_url = None
        # send message on slack
        if g.slack_enabled.read():
            slack = g.slack_control.read()
            field = {}
            field['title'] = scan_folder.split(os.sep)[-1]
            field['title_link'] = folder_url
            field['image_url'] = image_url
            message = ':tada: scan complete - {} elapsed'.format(g.progress_bar.time_elapsed.text())
            slack.send_message(message, attachments=[field])
        # automatically copy to user-defined folder
        if devices.autocopy_enable.read():
            src = scan_folder
            name = src.split(os.sep)[-1]
            dst = os.path.join(devices.autocopy_path.read(), name)
            shutil.copytree(src, dst)
        
        

### GUI base ##################################################################


class GUI(QtCore.QObject):

    def __init__(self, module_name):
        QtCore.QObject.__init__(self)
        self.module_name = module_name
        self.wait_window = pw.MessageWindow(title=self.module_name, text='Please wait.')
        # create frame
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.create_frame()  # add module-specific widgets to out layout
        # device widget
        self.device_widget = devices.Widget()
        self.layout.addWidget(self.device_widget)
        # finish
        self.frame = QtGui.QWidget()
        self.frame.setLayout(self.layout)
        # signals and slots
        devices.control.settings_updated.connect(self.on_device_settings_updated)
        
    def autocopy(self, data_folder):
        '''
        Copy the data to the data folder defined in devices (if enabled).
        '''
        if devices.autocopy_enable.read():
            src = data_folder
            name = src.split(os.sep)[-1]
            dst = os.path.join(devices.autocopy_path.read(), name)
            shutil.copytree(src, dst)
            
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


    def hide(self):
        self.frame.hide()

    def on_device_settings_updated(self):
        # overload this if your gui has device-dependent settings
        pass
        
    def show(self):
        self.frame.show()        
        
    def update(self):
        pass

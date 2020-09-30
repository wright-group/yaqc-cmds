"""
Acquisition infrastructure shared by all modules.
"""


### import ####################################################################


import re
import os
import imp
import copy
import shutil
import pathlib
import time
import traceback

import appdirs
import toml
import numpy as np

import numexpr

from PySide2 import QtCore, QtWidgets

import WrightTools as wt

import pycmds.project.project_globals as g

import pycmds.hardware.spectrometers.spectrometers as spectrometers
import pycmds.hardware.delays as delays
import pycmds.hardware.opas as opas
import pycmds.hardware.filters.filters as filters

all_hardwares = opas.hardwares + spectrometers.hardwares + delays.hardwares + filters.hardwares

import pycmds._record as record

from . import constant_resolver


### define ####################################################################


__here__ = pathlib.Path(__file__).parent


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
        names = re.split("[=F]+", self.identity)
        # KFS 2018-12-07: Is this still used at all? replacing wt2 kit.parse_identity
        if "F" in self.identity:  # last name should be a 'following' in this case
            names.pop(-1)
        for name in names:
            if name[0] == "D":
                clean_name = name.replace("D", "", 1)
            else:
                clean_name = name
            if clean_name not in self.hardware_dict.keys():
                hardware_object = [h for h in all_hardwares if h.name == clean_name][0]
                self.hardware_dict[name] = [hardware_object, "set_position", None]


class Constant:
    def __init__(self, units, name, identity, static=True, expression=""):
        self.units = units
        self.name = name
        self.identity = identity
        self.static = static
        self.expression = expression
        self.hardware = [h for h in all_hardwares if h.name == self.name][0]


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
        self.module = imp.load_source(name, str(path))
        self.process = self.module.process


orderers = []
orderers.append(Order("ndindex", __here__ / "order" / "ndindex.py"))


### Worker base ##############################################################


class Worker(QtCore.QObject):
    update_ui = QtCore.Signal()
    scan_complete = QtCore.Signal()
    done = QtCore.Signal()

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
        # move aqn file into queue folder
        ini = wt.kit.INI(aqn_path)
        module_name = ini.read("info", "module")
        item_name = ini.read("info", "name")
        aqn_path = pathlib.Path(aqn_path)
        aqn_index_str = str(self.queue_worker.index.read()).zfill(3)
        aqn_name = " ".join([aqn_index_str, module_name, item_name]).rstrip()
        folder_path = pathlib.Path(self.queue_worker.folder.read()).joinpath(aqn_name)
        if aqn_path != folder_path.with_suffix(".aqn"):
            shutil.copyfile(aqn_path, folder_path.with_suffix(".aqn"))
            if aqn_path.parent == folder_path.parent:
                aqn_path.unlink()
        self.aqn_path = folder_path.with_suffix(".aqn")
        self.aqn = wt.kit.INI(self.aqn_path)
        self.folder = pathlib.Path(folder_path)
        self.folder.mkdir(exist_ok=True)
        # create acquisition folder
        # initialize
        self.scan_index = None
        self.scan_folders = []
        self.scan_urls = []

    def process(self, scan_folder):
        # get path
        data_path = record.data_path.read()
        # make data object
        data = wt.data.from_PyCMDS(data_path, verbose=False)
        data.save(data_path.replace(".data", ".p"), verbose=False)
        # make figures for each channel
        data_path = pathlib.Path(data_path)
        data_folder = data_path.parent
        file_name = data_path.stem
        file_extension = data_path.suffix
        # chop data if over 2D
        for channel_index, channel_name in enumerate(data.channel_names):
            output_folder = data_folder if data.ndim <= 2 else data_folder / channel_name
            output_folder.mkdir(exist_ok=True)
            image_fname = channel_name + " " + file_name
            if len(data.shape) == 1:
                outs = wt.artists.quick1D(
                    data,
                    channel=channel_index,
                    autosave=True,
                    save_directory=output_folder,
                    fname=image_fname,
                    verbose=False,
                )
            else:
                outs = wt.artists.quick2D(
                    data,
                    -1,
                    -2,
                    channel=channel_index,
                    autosave=True,
                    save_directory=output_folder,
                    fname=image_fname,
                    verbose=False,
                )
            # hack in a way to get the first image written
            if channel_index == 0:
                output_image_path = outs[0]
        # upload
        self.upload(self.scan_folders[self.scan_index], reference_image=output_image_path)

    def scan(
        self,
        axes,
        constants=[],
        pre_wait_methods=[],
        processing_method="process",
        module_reserved="",
        multiple_scans=False,
    ):
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
            arrs = np.meshgrid(*[a.points for a in axes], indexing="ij")
        # treat 'scan about center' axes
        for axis_index, axis in enumerate(axes):
            if axis.identity[0] == "D":
                centers = axis.centers
                # transpose so own index is first (all others slide down)
                transpose_order = list(range(len(axes)))
                transpose_order.insert(0, transpose_order.pop(axis_index))
                arrs[axis_index] = np.transpose(arrs[axis_index], axes=transpose_order)
                # add centers to transposed array
                arrs[axis_index] += centers
                # transpose out
                transpose_order = list(range(len(axes)))
                transpose_order.insert(axis_index, transpose_order.pop(0))
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
        constant_dict = {c.name: c for c in constants}
        for constant in constant_resolver.const_order(
            **{c.name: c.expression for c in constants}
        ):  # must follow axes
            constant = constant_dict[constant]
            if constant.static:
                pass
            else:
                # initialize
                expression = constant.expression
                arr = np.full(arrs[0].shape, np.nan)
                units = constant.units
                units_kind = wt.units.kind(units)
                vals = {}
                # populate all hardwares not scanned here
                for hardware in all_hardwares:
                    if wt.units.kind(hardware.units) == units_kind:
                        vals[hardware.name] = hardware.get_position(units)
                for idx in np.ndindex(arrs[0].shape):
                    for destination in destinations_list:
                        if wt.units.kind(destination.units) == units_kind:
                            val = wt.units.converter(
                                destination.arr[idx], destination.units, units
                            )
                            vals[destination.hardware.name] = val
                    arr[idx] = numexpr.evaluate(expression, vals)
                # finish
                hardware = constant.hardware
                destinations = Destinations(arr, units, hardware, "set_position", None)
                destinations_list.insert(0, destinations)
        # check if scan is valid for hardware ---------------------------------
        # TODO: !!!
        # run through aquisition order handler --------------------------------
        order = orderers[0]  # TODO: real orderer support
        idxs, slices = order.process(destinations_list)
        # initialize scan -----------------------------------------------------
        g.queue_control.write(True)
        self.going.write(True)
        self.fraction_complete.write(0.0)
        g.logger.log("info", "Scan begun", "")
        # put info into headers -----------------------------------------------
        # clear values from previous scan
        record.headers.clear()
        # data info
        record.headers.data_info["data name"] = self.aqn.read("info", "name")
        record.headers.data_info["data info"] = self.aqn.read("info", "info")
        record.headers.data_info["data origin"] = self.aqn.read("info", "module")
        # axes (will be added onto in devices, potentially)
        record.headers.axis_info["axis names"] = [a.name for a in axes]
        record.headers.axis_info["axis identities"] = [a.identity for a in axes]
        record.headers.axis_info["axis units"] = [a.units for a in axes]
        record.headers.axis_info["axis interpolate"] = [False for a in axes]
        for axis in axes:
            record.headers.axis_info[axis.name + " points"] = axis.points
            if axis.identity[0] == "D":
                record.headers.axis_info[axis.name + " centers"] = axis.centers
        # constants
        record.headers.constant_info["constant names"] = [c.name for c in constants]
        record.headers.constant_info["constant identities"] = [c.identity for c in constants]
        # create scan folder
        scan_index_str = str(self.scan_index).zfill(3)
        axis_names = str([str(a.name) for a in axes]).replace("'", "")
        if multiple_scans:
            scan_folder_name = " ".join([scan_index_str, axis_names, module_reserved]).rstrip()
            scan_folder = os.path.join(self.folder, scan_folder_name)
            os.mkdir(scan_folder)
            self.scan_folders.append(scan_folder)
        else:
            scan_folder = str(self.folder)
            self.scan_folders.append(self.folder)
        # create scan folder on google drive
        if g.google_drive_enabled.read():
            scan_url = g.google_drive_control.read().reserve_id(scan_folder)
            self.scan_urls.append(g.google_drive_control.read().id_to_open_url(scan_folder))
        else:
            self.scan_urls.append(None)
        # add urls to headers
        if g.google_drive_enabled.read():
            record.headers.scan_info["queue url"] = self.queue_worker.queue_url
            record.headers.scan_info["acquisition url"] = self.aqn.read("info", "url")
            record.headers.scan_info["scan url"] = scan_url
        # initialize devices
        record.control.initialize_scan(self.aqn, scan_folder, destinations_list)
        # acquire -------------------------------------------------------------
        self.fraction_complete.write(0.0)
        slice_index = 0
        npts = float(len(idxs))
        for i, idx in enumerate(idxs):
            idx = tuple(idx)
            record.idx.write(idx)
            # launch hardware
            for d in destinations_list:
                destination = d.arr[idx]
                if d.method == "set_position":
                    d.hardware.set_position(destination, d.units)
                else:
                    inputs = copy.copy(d.passed_args)
                    for input_index, input_val in enumerate(inputs):
                        if input_val == "destination":
                            inputs[input_index] = destination
                        elif input_val == "units":
                            inputs[input_index] = d.units
                    d.hardware.q.push(d.method, *inputs)
            # execute pre_wait_methods
            for method in pre_wait_methods:
                method()
            # slice
            if slice_index < len(slices):  # takes care of last slice
                if slices[slice_index]["index"] == i:
                    record.current_slice.index(slices[slice_index])
                    slice_index += 1
            # wait for hardware
            g.hardware_waits.wait()
            # launch devices
            record.control.acquire(save=True, index=idx)
            # wait for devices
            record.control.wait_until_done()
            # update
            self.fraction_complete.write(i / npts)
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
        record.control.wait_until_file_done()
        self.fraction_complete.write(1.0)
        self.going.write(False)
        g.queue_control.write(False)
        g.logger.log("info", "Scan done", "")
        self.update_ui.emit()
        self.scan_complete.emit()
        # process scan --------------------------------------------------------
        try:
            getattr(self, processing_method)(scan_folder)
        except BaseException:
            # Yeah, yeah, excepting BaseException.... KFS and BJT
            # deal with it ---sunglasses---  ---BJT 2018-10-25
            traceback.print_exc()
            self.upload(scan_folder)
        return scan_folder

    def upload(self, scan_folder, message="scan complete", reference_image=None):
        # create folder on google drive, upload reference image
        if g.google_drive_enabled.read():
            folder_url = g.google_drive_control.read().id_to_open_url(scan_folder)
            g.google_drive_control.read().upload_folder(
                path=scan_folder, parent_id=str(pathlib.Path(scan_folder).parent), id=scan_folder,
            )
            image_url = None
            if reference_image is not None:
                reference_id = f"{scan_folder} reference"
                g.google_drive_control.read().reserve_id(reference_id)
                image_url = g.google_drive_control.read().id_to_download_url(reference_id)
                g.google_drive_control.read().create_file(
                    path=reference_image, parent_id=scan_folder, id=reference_id
                )
        else:
            folder_url = image_url = None
        # send message on slack
        if g.slack_enabled.read():
            if g.google_drive_enabled.read() and reference_image is not None:
                start = time.time()
                while time.time() - start < 10 and not g.google_drive_control.read().is_uploaded(
                    reference_id
                ):
                    time.sleep(0.01)
            slack = g.slack_control.read()
            field = {}
            field["title"] = pathlib.Path(scan_folder).name
            field["title_link"] = folder_url
            field["image_url"] = image_url
            message = ":tada: scan complete - {} elapsed".format(
                g.progress_bar.time_elapsed.text()
            )
            slack.send_message(message, attachments=[field])


### GUI base ##################################################################


class GUI(QtCore.QObject):
    def __init__(self, module_name):
        QtCore.QObject.__init__(self)
        self.module_name = module_name
        self.state_path = (
            pathlib.Path(appdirs.user_data_dir("pycmds", "pycmds"))
            / "modules"
            / f"{self.module_name.lower()}.toml"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.touch(exist_ok=True)
        self.state = toml.load(self.state_path)
        # create frame
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.create_frame()  # add module-specific widgets to out layout
        # device widget
        self.device_widget = record.Widget()
        self.layout.addWidget(self.device_widget)
        # finish
        self.frame = QtWidgets.QWidget()
        self.frame.setLayout(self.layout)
        # signals and slots
        record.control.settings_updated.connect(self.on_sensor_settings_updated)

    def create_frame(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setMargin(5)
        # scan widget
        layout.addWidget(self.scan.widget)
        # finish
        layout.addStretch(1)
        self.frame = QtWidgets.QWidget()
        self.frame.setLayout(layout)
        g.module_widget.add_child(self.frame)
        g.module_combobox.add_module(module_name, self.show_frame)

    def hide(self):
        self.frame.hide()

    def on_sensor_settings_updated(self):
        # overload this if your gui has device-dependent settings
        pass

    def save_state(self):
        with open(self.state_path, "w") as f:
            f.write(toml.dumps(self.state))

    def show(self):
        self.frame.show()

    def update(self):
        pass

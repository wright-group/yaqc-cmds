"""bwt5 data file functions"""


import time

import h5py
import WrightTools as wt

import pycmds.project.project_globals as g
import pycmds.somatic as somatic


data = None
data_filepath = None
last_idx_written = None


def create_data(path, headers, destinations, axes, constants, hardware, sensors):
    """Create new data object.

    Parameters
    ----------
    path : path-like
        Full path to new file.
    headers : dictionary
        Metadata
    destinations : list of pycmds.acquisition.Destination objects
        New scan destinations.
    axes : list of pycmds.acqusition.Axis objects
        New scan axes.
    constants : list of pycmds.acquisition.Constant objects
        New scan constants.
    hardware: list of pycmds.hardware.Hardware objects
        all active hardware
    sensors: list of pycmds._sensors.Sensor objects
        all active sensors
    """
    f = h5py.File(path, "w", libver="latest")
    global data, data_filepath
    data = wt.Data(f, name=headers["name"])
    data_filepath = path

    # fill out pycmds_information in headers
    headers["PyCMDS version"] = g.version.read()
    headers["system name"] = g.system_name.read()

    data.attrs.update(headers)

    full_scan_shape = tuple(a.points.size for a in axes)
    variable_shapes = {"labtime": full_scan_shape}
    variable_units = {"labtime": "s"}
    variable_labels = {}

    for i, axis in enumerate(axes):
        shape = [1] * len(axes)
        shape[i] = axis.points.size
        variable_shapes[f"{axis.name}_points"] = tuple(shape)
        variable_units[f"{axis.name}_points"] = axis.units

    for hw in hardware:
        for rec, (_, units, _, label, _) in hw.recorded.items():
            variable_shapes[rec] = full_scan_shape
            variable_units[rec] = units
            variable_labels[rec] = label

    channel_shapes = {}
    channel_units = {}

    for sensor in sensors:
        # TODO allow sensors to be inactive
        # TODO allow multi-D sensors
        sensor.active = True
        for ch in sensor.channel_names:
            channel_shapes[ch] = full_scan_shape
            # TODO: channel units?
            channel_units[ch] = None

    for var, sh in variable_shapes.items():
        units = variable_units[var]
        label = variable_labels.get(var)
        if label:
            data.create_variable(var, shape=sh, units=units, label=label)
        else:
            data.create_variable(var, shape=sh, units=units)

    for axis in axes:
        sh = data[f"{axis.name}_points"].shape
        data[f"{axis.name}_points"][:] = axis.points.reshape(sh)

    data.transform(*[a.name for a in axes])

    for ch, sh in channel_shapes.items():
        units = channel_units[ch]
        data.create_channel(ch, shape=sh, units=units)
        # TODO signed?
        # TODO labels?

    f.swmr_mode = True
    f.flush()
    somatic.signals.data_file_created.emit()


def get_data_readonly():
    if data_filepath is not None:
        f = h5py.File(data_filepath, "r", libver="latest", swmr=True)
        return wt.Data(f)


def close_data():
    data.close()


def write_data(idx, hardware, sensors):
    data["labtime"][idx] = time.time()
    for hw in hardware:
        for rec, (obj, *_) in hw.recorded.items():
            data[rec][idx] = obj.read(data[rec].units)
    for s in sensors:
        for ch, val in s.channels.items():
            data[ch][idx] = val
    data.flush()
    global last_idx_written
    last_idx_written = idx
    somatic.signals.data_file_written.emit()

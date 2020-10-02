"""wt5 data file functions"""


import time

import h5py
import WrightTools as wt

import pycmds.project.project_globals as g

data = None
data_filepath = None


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
    variables = ["labtime"] + [f"{a.name}_points" for a in axes] + [h.name for h in hardware]
    variable_shapes = {n: full_scan_shape for n in variables}
    variable_units = {n: None for n in variables}
    variable_units["labtime"] = "s"
    for i, axis in enumerate(axes):
        shape = [1] * len(axes)
        shape[i] = axis.points.size
        variable_shapes[f"{axis.name}_points"] = tuple(shape)
        variable_units[f"{axis.name}_units"] = axis.units

    for hw in hardware:
        variable_units[hw.name] = hw.native_units

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


def get_data_readonly():
    f = h5py.File(data_filepath, "r", libver="latest", swmr=True)
    return wt.Data(f)


def close_data():
    data.close()


def write_data(idx, hardware, sensors):
    data["labtime"][idx] = time.time()
    for hw in hardware:
        data[hw.name][idx] = hw.get_position()
    for s in sensors:
        for ch, val in s.channels.items():
            data[ch][idx] = val

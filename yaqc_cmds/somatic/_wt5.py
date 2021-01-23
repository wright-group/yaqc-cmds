"""wt5 data file functions"""


import time
import threading

import h5py
import WrightTools as wt

import yaqc_cmds.project.project_globals as g
import yaqc_cmds.somatic as somatic


class DataContainer(object):
    def __init__(self):
        self._data = None
        self.data_filepath = None
        self.last_idx_written = None
        self.lock = threading.RLock()

    def __enter__(self):
        self.lock.acquire()
        if self.data_filepath:
            self._data = wt.open(self.data_filepath, edit_local=True)
        return self._data

    def __exit__(self, exc_type, exc_value, traceback):
        if self._data:
            self._data.close()
        self._data = None
        self.lock.release()


data_container = DataContainer()


def create_data(path, headers, destinations, axes, constants, hardware, sensors):
    """Create new data object.

    Parameters
    ----------
    path : path-like
        Full path to new file.
    headers : dictionary
        Metadata
    destinations : list of yaqc_cmds.acquisition.Destination objects
        New scan destinations.
    axes : list of yaqc_cmds.acqusition.Axis objects
        New scan axes.
    constants : list of yaqc_cmds.acquisition.Constant objects
        New scan constants.
    hardware: list of yaqc_cmds.hardware.Hardware objects
        all active hardware
    sensors: list of yaqc_cmds._sensors.Sensor objects
        all active sensors
    """
    f = h5py.File(path, "w")
    global data_container
    with data_container as data:
        data = wt.Data(f, name=headers["name"], edit_local=True)
        data_container.data_filepath = path

        # fill out yaqc_cmds_information in headers
        headers["Yaqc_cmds version"] = g.version.read()
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
            if hasattr(axis, "centers"):
                shape = list(full_scan_shape)
                shape[i] = 1
                variable_shapes[f"{axis.name}_centers"] = tuple(shape)
                variable_units[f"{axis.name}_centers"] = axis.units

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

            # InGaAs array detector
            if hasattr(sensor.driver.client, "get_map"):
                map_shape = full_scan_shape + tuple(sensor.shape)
                full_scan_shape = full_scan_shape + (1,)
                for k, v in variable_shapes.items():
                    variable_shapes[k] = v + (1,)
                for k, v in channel_shapes.items():
                    channel_shapes[k] = v + (1,)

                variable_shapes["wa"] = map_shape
                variable_units["wa"] = "nm"
                variable_labels["wa"] = "a"

                for ch in sensor.channel_names:
                    channel_shapes[ch] = map_shape
                    channel_units[ch] = None

            else:
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
            if hasattr(axis, "centers"):
                sh = data[f"{axis.name}_centers"].shape
                data[f"{axis.name}_centers"][:] = axis.centers.reshape(sh)

        # This check was originally if there was _centers_ use the points arrays
        # This was changed to always use the points arrays (except for the array detector)
        # Because chopping full shaped arrays caused incorrect behavior for 3D+ data
        # When we have some better hinting in WT itself, this should likely be reverted
        # KFS 2020-11-13
        transform = [f"{a.name}_points" if hasattr(a, "points") else a.name for a in axes]
        if "wa" in variable_shapes:
            transform += ["wa"]
        data.transform(*transform)

        for ch, sh in channel_shapes.items():
            units = channel_units[ch]
            data.create_channel(ch, shape=sh, units=units)
            # TODO signed?
            # TODO labels?

        somatic.signals.data_file_created.emit()


def write_data(idx, hardware, sensors):
    global data_container
    with data_container as data:
        in_idx = idx
        idx = idx + (...,)
        data["labtime"][idx] = time.time()
        for hw in hardware:
            for rec, (obj, *_) in hw.recorded.items():
                data[rec][idx] = obj.read(data[rec].units)
        for s in sensors:
            for ch, val in s.channels.items():
                data[ch][idx] = val
            if s.shape[0] > 1:
                data["wa"][idx] = s.driver.client.get_map(data["wm"][idx])
        data.flush()
        data_container.last_idx_written = in_idx

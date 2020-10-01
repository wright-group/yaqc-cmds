"""wt5 data file functions"""


import h5py

import WrightTools as wt


data = None


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
    data = wt.Data(f, name=headers["name"])

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
        variable_shapes[f"{a.name}_points"] = tuple(shape)
        variable_units[f"{a.name}_points"] = axis.units

    for hw in hardware:
        variable_units[hw.name] = hw.units

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
    fp = data.filepath
    f = h5py.File(fp, "r", libver="latest", swmr=True)
    return wt.Data(f)


def write_data(idx, hardware, sensors):

    # loop time
    now = time.time()
    loop_time.write(now - self.t_last)
    self.t_last = now
    # ms wait
    time.sleep(ms_wait.read() / 1000.0)
    # acquire
    for sensor in self.sensors:
        if sensor.active:
            sensor.measure()
    self.wait_until_done()
    # save
    if save:
        # 1D things -------------------------------------------------------
        data_rows = np.prod([d.data.size for d in self.sensors if d.active])
        data_shape = (len(headers.data_cols["name"]), int(data_rows))
        data_arr = np.full(data_shape, np.nan)
        data_i = 0
        # scan indicies
        for i in idx.read():  # scan sensor
            data_arr[data_i] = i
            data_i += 1
        for sensor in self.sensors:  # daq
            if sensor.active and sensor.has_map:
                map_indicies = [i for i in np.ndindex(sensor.data.shape)]
                for i in range(len(sensor.data.shape)):
                    data_arr[data_i] = [mi[i] for mi in map_indicies]
                    data_i += 1
        # time
        now = time.time()  # seconds since epoch
        data_arr[data_i] = now
        data_i += 1
        # hardware positions
        for scan_hardware_module in scan_hardware_modules:
            for scan_hardware in scan_hardware_module.hardwares:
                for key in scan_hardware.recorded:
                    out_units = scan_hardware.recorded[key][1]
                    if out_units is None:
                        data_arr[data_i] = scan_hardware.recorded[key][0].read()
                    else:
                        data_arr[data_i] = scan_hardware.recorded[key][0].read(out_units)
                    data_i += 1
        # potentially multidimensional things -----------------------------
        # acquisition maps
        for sensor in self.sensors:
            if sensor.active and sensor.has_map:
                data_arr[data_i] = sensor.map.read()
                data_i += 1
        # acquisitions
        for sensor in self.sensors:
            if sensor.active:
                channels = sensor.data.read()  # list of arrays
                for arr in channels:
                    data_arr[data_i] = arr
                    data_i += 1
        # send to file_address --------------------------------------------
        q("write_data", [data_arr])
        # fill slice ------------------------------------------------------
        slice_axis_index = headers.data_cols["name"].index(current_slice.name)
        slice_position = np.mean(data_arr[slice_axis_index])
        native_units = headers.data_cols["units"][slice_axis_index]
        slice_position = wt.units.converter(slice_position, native_units, current_slice.units)
        data_arrs = []
        for sensor in self.sensors:
            data_arrs.append(sensor.data.read())
        current_slice.append(slice_position, data_arrs)

    pass

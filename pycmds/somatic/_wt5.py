"""wt5 data file functions"""



data = None



def create_file(path):

    timestamp = wt.kit.TimeStamp()
    # stop freerunning
    self.set_freerun(False)
    # fill out pycmds_information in headers
    headers.pycmds_info["PyCMDS version"] = g.version.read()
    headers.pycmds_info["system name"] = g.system_name.read()
    headers.pycmds_info["file created"] = timestamp.RFC3339
    # apply sensor settings from aqn
    ms_wait.write(aqn.read("sensor settings", "ms wait"))
    for sensor in self.sensors:
        # if not aqn.has_section(sensor.name):
        #    sensor.active = False
        #    continue
        # if not aqn.read(sensor.name, "use"):
        #    sensor.active = False
        #    continue
        # apply settings from aqn to sensor
        sensor.active = True
        sensor.load_settings(aqn)
        # record sensor axes, if applicable
        if sensor.has_map:
            for key in sensor.map_axes.keys():
                # add axis
                headers.axis_info["axis names"].append(key)
                (identity, units, points, centers, interpolate,) = sensor.get_axis_properties(
                    destinations_list
                )
                headers.axis_info["axis identities"].append(identity)
                headers.axis_info["axis units"].append(units)
                headers.axis_info["axis interpolate"].append(interpolate)
                headers.axis_info[" ".join([key, "points"])] = points
                if centers is not None:
                    headers.axis_info[" ".join([key, "centers"])] = centers
                # expand exisiting axes (not current axis)
                for subkey in headers.axis_info.keys():
                    if "centers" in subkey and key not in subkey:
                        centers = headers.axis_info[subkey]
                        centers = np.expand_dims(centers, axis=-1)
                        centers = np.repeat(centers, points.size, axis=-1)
                        headers.axis_info[subkey] = centers
    # add cols information
    self.update_cols(aqn)
    # add channel signed choices
    # TODO: better implementation. for now, just assume not signed
    signed = []
    for sensor in self.sensors:
        signed += sensor.data.signed
    headers.channel_info["channel signed"] = signed
    # add daq information to headers
    for sensor in self.sensors:
        if sensor.active:
            for key, value in sensor.get_headers().items():
                headers.daq_info[" ".join([sensor.name, key])] = value
    q("create_data", [aqn, scan_folder])
    # refresh current slice properties
    current_slice.begin([len(sensor.data.cols) for sensor in self.sensors])
    # wait until daq is done before letting module continue
    self.wait_until_done()
    self.wait_until_file_done()



    kind = []
    tolerance = []
    units = []
    label = []
    name = []
    # indicies
    for n in headers.axis_info["axis names"]:
        kind.append(None)
        tolerance.append(None)
        units.append(None)
        label.append("")
        name.append("_".join([n, "index"]))
    # time
    kind.append(None)
    tolerance.append(0.01)
    units.append("s")
    label.append("lab")
    name.append("time")
    # scan hardware positions
    for scan_hardware_module in scan_hardware_modules:
        for scan_hardware in scan_hardware_module.hardwares:
            for key in scan_hardware.recorded:
                kind.append("hardware")
                tolerance.append(scan_hardware.recorded[key][2])
                units.append(scan_hardware.recorded[key][1])
                label.append(scan_hardware.recorded[key][3])
                name.append(key)
    # acquisition maps
    for sensor in self.sensors:
        if not aqn.has_section(sensor.name):
            continue
        if not aqn.read(sensor.name, "use"):
            continue
        if sensor.has_map:
            for i in range(len(sensor.map_axes)):
                kind.append("hardware")
                tolerance.append(None)
                vals = list(sensor.map_axes.values())
                units.append(vals[i][1])
                label.append(vals[i][0])
                name.append(list(sensor.map_axes.keys())[i])
    # channels
    self.channel_names = []
    for sensor in self.sensors:
        # if not aqn.has_section(sensor.name):
        #    continue
        # if not aqn.read(sensor.name, "use"):
        #    continue
        mutex = sensor.data
        for col in mutex.cols:
            kind.append("channel")
            tolerance.append(None)
            units.append("")  # TODO: better units support?
            label.append("")  # TODO: ?
            name.append(col)
            self.channel_names.append(col)
    # clean up
    for i, s in enumerate(label):
        label[i] = s.replace("prime", r"\'")
    # finish
    cols = headers.data_cols
    cols["kind"] = kind
    cols["tolerance"] = tolerance
    cols["label"] = label
    cols["units"] = units
    cols["name"] = name





def get_file_readonly():
    return data




def write_data():

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

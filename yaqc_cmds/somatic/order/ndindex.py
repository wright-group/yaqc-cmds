import numpy as np


def process(destinations_list):
    # out
    out = [idx for idx in np.ndindex(destinations_list[0].arr.shape)]
    # generate slices list of dictionaries
    if len(destinations_list[-1].arr.shape) > 1:
        # multidimensional scan
        slices = []
        for i, idx in enumerate(np.ndindex(destinations_list[-1].arr.shape[:-1])):
            s = {}
            s["index"] = destinations_list[-1].arr.shape[-1] * i
            s["name"] = destinations_list[-1].hardware.name
            s["units"] = destinations_list[-1].units
            s["points"] = destinations_list[-1].arr[idx]
            if destinations_list[-1].method == "set_position":
                s["use actual"] = True
            else:
                s["use actual"] = False
            slices.append(s)
    else:
        # 1D scan
        s = {}
        s["index"] = 0
        s["name"] = destinations_list[0].hardware.name
        s["units"] = destinations_list[0].units
        s["points"] = destinations_list[0].arr
        if destinations_list[0].method == "set_position":
            s["use actual"] = True
        else:
            s["use actual"] = False
        slices = [s]
    return out, slices

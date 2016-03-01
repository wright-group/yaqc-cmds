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
            s['index'] = destinations_list[-1].arr.shape[-1]*i
            s['name'] = destinations_list[-1].hardware.friendly_name
            s['units'] = destinations_list[-1].units
            s['points'] = destinations_list[-1].arr[idx]
            slices.append(s)
    else:
        # 1D scan
        s = {}
        s['index'] = 0
        s['name'] = destinations_list[0].hardware.friendly_name
        s['units'] = destinations_list[0].units
        s['points'] = destinations_list[0].arr
        slices = [s]
    return out, slices

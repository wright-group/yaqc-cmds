import collections

import numpy as np

def process(destinations_list):
    data_size = destinations_list[0].arr.size
    data_shape = destinations_list[0].arr.shape
    # generate indicies array
    out = np.full([data_size, len(data_shape)], np.nan, dtype=np.int16)
    i = 0
    for idx in np.ndindex(data_shape):
        out[i] = idx
        i += 1
    # generate slices list of dictionaries
    slices = []
    #slice_axis = destinations_list[-1]
    #slice_gp = destinations_list[-1]
    '''
    for inner_index in range(grid_points[0][-1]):
        s = collections.OrderedDict()
        s['name'] = slice_axis.name
        s['units'] = slice_axis.units
        s['points'] = slice_gp[..., inner_index]
        slices.append(s)
    '''
    return out, slices
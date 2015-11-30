import numpy as np

def process(shots, names, kinds):
    channel_indicies = [i for i, x in enumerate(kinds) if x == 'channel']
    out = np.full(len(channel_indicies)*2, np.nan)
    out_index = 0
    out_names = []
    for i in channel_indicies:
        out[out_index] = np.mean(shots[i])
        out_names.append(names[i] + '_mean')
        out_index += 1
        out[out_index] = np.var(shots[i])
        out_names.append(names[i] + '_variance')
        out_index += 1
    return [out, out_names]
    
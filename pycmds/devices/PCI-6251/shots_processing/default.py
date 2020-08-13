import numpy as np


def process(shots, names, kinds):
    """
    Mean of everything
    
    Parameters
    ----------
    shots : ndarray
        A ndarray (inputs, shots)
    names : list of str
        A list of input names
    kinds : list of {'channel', 'chopper'}
        Kind of each input
        
    Returns
    -------
    list
        [ndarray (channels), list of channel names]
    """
    out = [np.mean(arr) for arr in shots]
    return [out, names]

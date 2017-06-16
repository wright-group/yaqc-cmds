### import ####################################################################


from hardware.opas.TOPAS.TOPAS import Driver as BaseDriver
from hardware.opas.TOPAS.TOPAS import GUI as BaseGUI
from hardware.opas.TOPAS.TOPAS import AutoTune as BaseAutoTune


### autotune ##################################################################


class AutoTune(BaseAutoTune):
    pass


### driver ####################################################################


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        self.motor_names = ['Crystal_1', 'Delay_1', 'Crystal_2', 'Delay_2', 'Mixer_1', 'Mixer_2', 'Mixer_3']
        self.curve_indices = {'Base': 1, 'Mixer 1': 2, 'Mixer 2': 3, 'Mixer 3': 4}
        self.kind = 'TOPAS-C'
        BaseDriver.__init__(self, *args, **kwargs)


### gui #######################################################################


class GUI(BaseGUI):
    pass

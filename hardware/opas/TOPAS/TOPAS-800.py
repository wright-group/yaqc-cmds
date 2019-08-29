### import ####################################################################


from hardware.opas.TOPAS.TOPAS import Driver as BaseDriver
from hardware.opas.TOPAS.TOPAS import GUI as BaseGUI


### autotune ##################################################################



### driver ####################################################################


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        #self.motor_names = ['Crystal', 'Amplifier', 'Grating', 'NDFG_Crystal', 'NDFG_Mirror', 'NDFG_Delay']
        self.motor_names = ['0', '1', '2', '3', '4', '5']
        self.curve_indices = {'Base': 1, 'Mixer 3': 4}
        self.kind = "TOPAS-800"
        BaseDriver.__init__(self, *args, **kwargs)


### gui #######################################################################


class GUI(BaseGUI):
    pass

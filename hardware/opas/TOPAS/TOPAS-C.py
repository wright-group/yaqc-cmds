# --- import --------------------------------------------------------------------------------------


from hardware.opas.TOPAS.TOPAS import Driver as BaseDriver
from hardware.opas.TOPAS.TOPAS import GUI as BaseGUI


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):
    
    def __init__(self, *args, **kwargs):
        self.motor_names = ['Crystal 1', 'Delay 1', 'Crystal 2', 'Delay 2',
                            'Mixer 1', 'Mixer 2','Mixer 3']
        self.curve_indices = {'Base': 1, 'Mixer 1': 2, 'Mixer 2': 3, 'Mixer 3': 4}
        self.kind = 'TOPAS-C'
        BaseDriver.__init__(self, *args, **kwargs)


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
    pass

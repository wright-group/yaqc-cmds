# --- import --------------------------------------------------------------------------------------


from hardware.opas.TOPAS.TOPAS import Driver as BaseDriver
from hardware.opas.TOPAS.TOPAS import GUI as BaseGUI


# --- driver --------------------------------------------------------------------------------------


class Driver(BaseDriver):
    def __init__(self, *args, **kwargs):
        self.motor_names = [
            "Crystal_1",
            "Delay_1",
            "Crystal_2",
            "Delay_2",
            "Mixer_1",
            "Mixer_2",
            "Mixer_3",
        ]
        self.curve_indices = {"Base": 1, "Mixer_1": 2, "Mixer_2": 3, "Mixer_3": 4}
        self.kind = "TOPAS-C"
        BaseDriver.__init__(self, *args, **kwargs)


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
    pass

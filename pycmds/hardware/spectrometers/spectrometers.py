### import ####################################################################


import pathlib

import appdirs
import toml

import hardware.hardware as hw


### driver ####################################################################


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        hw.Driver.__init__(self, *args, **kwargs)
        self.limits.write(0.0, 10000.0)


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    def __init__(self, *args, **kwargs):
        self.kind = "spectrometer"
        hw.Hardware.__init__(self, *args, **kwargs)


### import ####################################################################


conf = pathlib.Path(appdirs.user_config_dir("pycmds", "pycmds")) / "config.toml"
conf = toml.load(conf)
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("spectrometers", {}),
    name="Spectrometers",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

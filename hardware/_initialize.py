__all__ = ["delays", "spectrometers", "opas", "filters", "hardwares", "initialize_hardwares"]

import pathlib

import appdirs
import toml

from ._delay import Delay
from ._spectrometer import Spectrometer
from ._opa import OPA
from ._filter import Filter

config_dir = pathlib.Path(appdirs.user_config_dir("PyCMDS", "PyCMDS"))

delays = {}
spectrometers = {}
opas = {}
filters = {}
hardwares = {}

def initialize_hardwares():
    config = toml.load(config_dir / "config.toml")["hardware"]
    for id_ in config["delays"]:
        hw = Delay(**config[id_])
        delays[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(delays, name="Delays")
    pw.HardwareAdvancedPanel(delays, gui.advanced_button)

    for id_ in config["spectrometers"]:
        hw = Spectrometer(**config[id_])
        spectrometers[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(spectrometers, name="Spectrometers")
    pw.HardwareAdvancedPanel(spectrometers, gui.advanced_button)

    for id_ in config["opas"]:
        hw = OPA(**config[id_])
        opas[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(opas, name="OPAs")
    pw.HardwareAdvancedPanel(opas, gui.advanced_button)

    for id_ in config["filters"]:
        hw = Filter(**config[id_])
        filters[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(filters, name="Filters")
    pw.HardwareAdvancedPanel(filters, gui.advanced_button)



    



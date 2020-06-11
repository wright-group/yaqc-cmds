__all__ = ["delays", "spectrometers", "opas", "filters", "hardwares", "initialize_hardwares"]

import pathlib
from pprint import pprint

import appdirs
import toml

from ._delay import Delay
from ._spectrometer import Spectrometer
from ._opa import OPA
from ._filter import Filter
from project import widgets as pw

config_dir = pathlib.Path(appdirs.user_config_dir("pycmds", "pycmds"))

delays = {}
spectrometers = {}
opas = {}
filters = {}
hardwares = {}

def initialize_hardwares():
    config = toml.load(config_dir / "config.toml")["hardware"]
    pprint(config)
    for id_ in config.get("delays", {}):
        pprint(config["delays"][id_])
        hw = Delay(id_, **(config["delays"][id_]))
        delays[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(delays, name="Delays")
    pw.HardwareAdvancedPanel(delays, gui.advanced_button)

    for id_ in config.get("spectrometers", {}):
        hw = Spectrometer(id_, **(config["spectrometers"][id_]))
        spectrometers[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(spectrometers, name="Spectrometers")
    pw.HardwareAdvancedPanel(spectrometers, gui.advanced_button)

    for id_ in config.get("opas", {}):
        hw = OPA(id_, **(config["opas"][id_]))
        opas[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(opas, name="OPAs")
    pw.HardwareAdvancedPanel(opas, gui.advanced_button)

    for id_ in config.get("filters", {}):
        hw = Filter(id_, **(config["filters"][id_]))
        filters[id_] = hw
        hardwares[id_] = hw
    gui = pw.HardwareFrontPanel(filters, name="Filters")
    pw.HardwareAdvancedPanel(filters, gui.advanced_button)



    



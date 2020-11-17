### import ####################################################################


import yaqc_cmds.__main__
import yaqc_cmds.project.classes as pc
import yaqc_cmds.hardware.hardware as hw
import pathlib
import appdirs
import toml
import yaqc


### driver ####################################################################


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self._yaqd_port = kwargs.pop("yaqd_port")
        super().__init__(*args, **kwargs)
        self.grating_index = pc.Combo(
            name="Grating",
            allowed_values=[1, 2],
            section=self.name,
            option="grating_index",
            display=True,
            set_method="set_turret",
        )
        self.exposed.append(self.grating_index)

    def get_position(self):
        native_position = self.ctrl.get_position()
        self.position.write(native_position, self.native_units)
        return self.position.read()

    def initialize(self, *args, **kwargs):
        # open control
        self.ctrl = yaqc.Client(self._yaqd_port)
        # import some information from control
        id_dict = self.ctrl.id()
        self.serial_number = id_dict["serial"]
        self.position.write(self.ctrl.get_position())
        # recorded
        self.recorded[self.name] = [self.position, self.native_units, 1.0, "m", False]
        self.limits.write(*self.ctrl.get_limits())
        self.wait_until_still()
        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()

    def is_busy(self):
        return self.ctrl.busy()

    def set_position(self, destination):
        self.ctrl.set_position(float(destination))
        self.wait_until_still()

    def set_turret(self, destination_index):
        if type(destination_index) == list:
            destination_index = destination_index[0]
        # turret index on ActiveX call starts from zero
        destination_index_zero_based = int(destination_index) - 1
        self.ctrl.set_turret(destination_index_zero_based)
        self.grating_index.write(destination_index)
        self.wait_until_still()
        self.limits.write(*self.ctrl.get_limits(), self.native_units)


### gui #######################################################################


class GUI(hw.GUI):
    pass


### hardware ##################################################################


class Hardware(hw.Hardware):
    def __init__(self, *args, **kwargs):
        self.kind = "spectrometer"
        hw.Hardware.__init__(self, *args, **kwargs)


### import ####################################################################


conf = yaqc_cmds.__main__.config
hardwares, gui, advanced_gui = hw.import_hardwares(
    conf.get("hardware", {}).get("spectrometers", {}),
    name="Spectrometers",
    Driver=Driver,
    GUI=GUI,
    Hardware=Hardware,
)

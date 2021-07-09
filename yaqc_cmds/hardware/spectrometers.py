### import ####################################################################


import yaqc_cmds.__main__
import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.hardware.hardware as hw
import yaqc_cmds.project.project_globals as g
import pathlib
import appdirs
import toml
import yaqc


### driver ####################################################################


class Driver(hw.Driver):
    def __init__(self, *args, **kwargs):
        self._yaqd_port = kwargs.pop("yaqd_port")
        super().__init__(*args, **kwargs)

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

        self.grating = pc.Combo(
            name="Grating",
            allowed_values=self.ctrl.get_turret_options(),
            display=True,
            set_method="set_turret",
        )
        self.exposed.append(self.grating)

        # finish
        self.initialized.write(True)
        self.initialized_signal.emit()

    def get_position(self):
        native_position = self.ctrl.get_position()
        self.position.write(native_position, self.native_units)
        return self.position.read()

    def is_busy(self):
        return self.ctrl.busy()

    def set_position(self, destination):
        self.ctrl.set_position(float(destination))
        self.wait_until_still()

    def set_turret(self, destination):
        if type(destination) == list:
            destination = destination[0]
        self.ctrl.set_turret(destination)
        self.grating.write(destination)
        self.wait_until_still()
        self.limits.write(*self.ctrl.get_limits(), self.native_units)

    def set_exit_mirror(self, destination):
        if type(destination) == list:
            destination = destination[0]
        self.ctrl.set_exit_mirror(destination)
        self.hardware.exit_mirror.write(destination)

    def set_entrance_mirror(self, destination):
        if type(destination) == list:
            destination = destination[0]
        self.ctrl.set_entrance_mirror(destination)
        self.hardware.entrance_mirror.write(destination)

    def set_front_entrance_slit(self, destination):
        self.ctrl.set_front_entrance_slit(float(destination))
        self.hardware.front_entrance_slit.write(destination)

    def set_side_entrance_slit(self, destination):
        self.ctrl.set_side_entrance_slit(float(destination))
        self.hardware.side_entrance_slit.write(destination)

    def set_front_exit_slit(self, destination):
        self.ctrl.set_front_exit_slit(float(destination))
        self.hardware.front_exit_slit.write(destination)

    def set_side_exit_slit(self, destination):
        self.ctrl.set_side_exit_slit(float(destination))
        self.hardware.side_exit_slit.write(destination)


### gui #######################################################################


class GUI(hw.GUI):
    def initialize(self):
        super().initialize()
        # self.layout.addWidget(self.scroll_area)
        # attributes
        mirror_list = ["front", "side"]
        input_table = pw.InputTable()
        self.scroll_layout.addWidget(pw.line("H"))

        has_mirror = False
        if hasattr(self.driver.ctrl, "set_entrance_mirror"):
            has_mirror = True
            input_table.add("Entrance Mirror", None)
            input_table.add("Current", self.hardware.entrance_mirror)
            self.entrance_mirror_dest = self.hardware.entrance_mirror.associate(display=False)
            input_table.add("Destination", self.entrance_mirror_dest)
        if hasattr(self.driver.ctrl, "set_exit_mirror"):
            has_mirror = True
            input_table.add("Exit Mirror", None)
            input_table.add("Current", self.hardware.exit_mirror)
            self.exit_mirror_dest = self.hardware.exit_mirror.associate(display=False)
            input_table.add("Destination", self.exit_mirror_dest)

        if has_mirror:
            self.scroll_layout.addWidget(input_table)
            input_table = pw.InputTable()
            self.set_mirror_button = pw.SetButton("SET MIRRORS")
            self.scroll_layout.addWidget(self.set_mirror_button)
            self.set_mirror_button.clicked.connect(self.on_set_mirror)
            g.queue_control.disable_when_true(self.set_mirror_button)
            self.scroll_layout.addWidget(pw.line("H"))

        has_slit = False
        if hasattr(self.driver.ctrl, "set_front_entrance_slit"):
            has_slit = True
            input_table.add("Front Entrance Slit", None)
            input_table.add("Current", self.hardware.front_entrance_slit)
            self.front_entrance_slit_dest = self.hardware.front_entrance_slit.associate(
                display=False
            )
            input_table.add("Destination", self.front_entrance_slit_dest)
        if hasattr(self.driver.ctrl, "set_side_entrance_slit"):
            has_slit = True
            input_table.add("Side Entrance Slit", None)
            input_table.add("Current", self.hardware.side_entrance_slit)
            self.side_entrance_slit_dest = self.hardware.side_entrance_slit.associate(
                display=False
            )
            input_table.add("Destination", self.side_entrance_slit_dest)
        if hasattr(self.driver.ctrl, "set_front_exit_slit"):
            has_slit = True
            input_table.add("Front Exit Slit", None)
            input_table.add("Current", self.hardware.front_exit_slit)
            self.front_exit_slit_dest = self.hardware.front_exit_slit.associate(display=False)
            input_table.add("Destination", self.front_exit_slit_dest)
        if hasattr(self.driver.ctrl, "set_side_exit_slit"):
            has_slit = True
            input_table.add("Side Exit Slit", None)
            input_table.add("Current", self.hardware.side_exit_slit)
            self.side_exit_slit_dest = self.hardware.side_exit_slit.associate(display=False)
            input_table.add("Destination", self.side_exit_slit_dest)
        if has_slit:
            self.scroll_layout.addWidget(input_table)
            self.set_slit_button = pw.SetButton("SET SLITS")
            self.scroll_layout.addWidget(self.set_slit_button)
            self.set_slit_button.clicked.connect(self.on_set_slit)
            g.queue_control.disable_when_true(self.set_slit_button)
            self.scroll_layout.addWidget(pw.line("H"))

    def on_set_mirror(self):
        entrance = self.entrance_mirror_dest.read()
        self.driver.set_entrance_mirror(entrance)
        exit = self.exit_mirror_dest.read()
        self.driver.set_exit_mirror(exit)
        self.driver.get_position()
        self.driver.save_status()

    def on_set_slit(self):
        front_entrance = self.front_entrance_slit_dest.read("mm")
        self.driver.set_front_entrance_slit(front_entrance)

        side_entrance = self.side_entrance_slit_dest.read("mm")
        self.driver.set_side_entrance_slit(side_entrance)

        front_exit = self.front_exit_slit_dest.read("mm")
        self.driver.set_front_exit_slit(front_exit)

        side_exit = self.side_exit_slit_dest.read("mm")
        self.driver.set_side_exit_slit(side_exit)

        self.driver.get_position()
        self.driver.save_status()


### hardware ##################################################################


class Hardware(hw.Hardware):
    def __init__(self, *args, **kwargs):
        self.kind = "spectrometer"
        mirror_list = ["front", "side"]
        self.entrance_mirror = pc.Combo(
            allowed_values=mirror_list,
            display=True,
        )
        self.exit_mirror = pc.Combo(
            allowed_values=mirror_list,
            display=True,
        )
        self.slit_limits = pc.NumberLimits(min_value=0, max_value=7, units="mm")
        self.front_entrance_slit = pc.Number(limits=self.slit_limits, units="mm", display=True)
        self.front_exit_slit = pc.Number(limits=self.slit_limits, units="mm", display=True)
        self.side_entrance_slit = pc.Number(limits=self.slit_limits, units="mm", display=True)
        self.side_exit_slit = pc.Number(limits=self.slit_limits, units="mm", display=True)
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

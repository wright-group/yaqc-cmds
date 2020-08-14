import os
import time
import collections
import pathlib

import attune
import yaqc

import pycmds.project
import pycmds.project.classes as pc
import pycmds.project.project_globals as g
from project.ini_handler import Ini
from hardware.opas.opas import Driver as BaseDriver
from hardware.opas.opas import GUI as BaseGUI


__here__ = pathlib.Path(__file__)


class Driver(BaseDriver):
    def __init__(self, *args, **kwargs):
        self.motors = {}
        self.curve_paths = collections.OrderedDict()
        self.ini = project.ini_handler.Ini(__here__ / "TOPAS.ini")
        self.has_shutter = kwargs["has_shutter"]
        self.motor_ports = kwargs["motor_ports"]
        if self.has_shutter:
            self.shutter_position = pc.Bool(name="Shutter", display=True, set_method="set_shutter")
            self.shutter = yaqc.Client(kwargs["shutter_port"])
        BaseDriver.__init__(self, *args, **kwargs)
        self.serial_number = self.ini.read("OPA" + str(self.index), "serial number")

        if self.has_shutter:
            self.shutter.set_position(0)

        # motor positions
        for motor_name, motor_port in zip(self.motor_names, self.motor_ports):
            self.motors[motor_name] = yaqc.Client(motor_port)
            min_position, max_position = self.motors[motor_name].get_limits()
            limits = pc.NumberLimits(min_position, max_position)
            number = pc.Number(initial_value=0, limits=limits, display=True, decimals=6)
            self.motor_positions[motor_name] = number
            self.recorded["w%d_" % self.index + motor_name] = [
                number,
                None,
                1.0,
                motor_name,
            ]
        # finish

        if self.has_shutter:
            self.exposed += [self.shutter_position]
        # tuning curves
        self.serial_number = self.ini.read(f"OPA{self.index}", "serial number")
        self.TOPAS_ini_filepath = os.path.join(
            __here__,
            "..",
            "configuration",
            str(self.serial_number) + ".ini",
        )
        self.TOPAS_ini = Ini(self.TOPAS_ini_filepath)
        self.TOPAS_ini.return_raw = True
        for curve_type in self.curve_indices.keys():
            section = "Optical Device"
            option = "Curve " + str(self.curve_indices[curve_type])
            initial_value = self.TOPAS_ini.read(section, option)
            options = ["CRV (*.crv)"]
            curve_filepath = pc.Filepath(initial_value=initial_value, options=options)
            curve_filepath.updated.connect(self.load_curve)
            self.curve_paths[curve_type] = curve_filepath
        # interaction string
        paths = self.curve_paths.copy()
        paths.pop("Poynting", None)
        paths = [v.read() for v in paths.values()]
        all_crvs = attune.TopasCurve.read_all(paths)
        allowed_values = list(all_crvs.keys())
        self.interaction_string_combo = pc.Combo(allowed_values=allowed_values)
        current_value = self.ini.read("OPA%i" % self.index, "current interaction string")
        self.interaction_string_combo.write(current_value)
        self.interaction_string_combo.updated.connect(self.load_curve)
        g.queue_control.disable_when_true(self.interaction_string_combo)
        self.load_curve(update=False)
        self.homeable = {m: True for m in self.motor_names}

    def _get_motor_index(self, name):
        c = self.curve
        while c is not None:
            if name in c.dependents:
                return c[name].index
            c = c.subcurve
        raise KeyError(name)

    def _home_motors(self, motor_names):
        for m in motor_names:
            self.motors[m].home()
        self.wait_until_still()

    def _load_curve(self, interaction):
        interaction = self.interaction_string_combo.read()
        curve_paths_copy = self.curve_paths.copy()
        if "Poynting" in curve_paths_copy.keys():
            del curve_paths_copy["Poynting"]
        crv_paths = [m.read() for m in curve_paths_copy.values()]
        all_curves = attune.TopasCurve.read_all(crv_paths)
        for curve in all_curves.values():
            for dependent in curve.dependent_names:
                if dependent not in self.motor_names:
                    try:
                        curve.rename_dependent(dependent, self.motor_names[int(dependent)])
                    except:
                        pass
        self.interaction_string_combo.set_allowed_values(list(all_curves.keys()))
        self.curve = all_curves[interaction]
        return self.curve

    def _set_motors(self, motor_destinations):
        for motor_name, destination in motor_destinations.items():
            destination = float(destination)
            self.motors[motor_name].set_position(destination)

    def _update_api(self, interaction):
        # write to TOPAS ini
        for curve_type, curve_path_mutex in self.curve_paths.items():
            if curve_type == "Poynting":
                continue
            curve_path = curve_path_mutex.read()
            section = "Optical Device"
            option = "Curve " + str(self.curve_indices[curve_type])
            self.TOPAS_ini.write(section, option, curve_path)
        # save current interaction string
        self.ini.write("OPA%i" % self.index, "current interaction string", interaction)

    def _wait_until_still(self):
        while self.is_busy():
            time.sleep(0.1)

    def close(self):
        if self.has_shutter:
            self.shutter.set_position(0)

    def get_motor_positions(self):
        for m, motor_mutex in self.motor_positions.items():
            position = self.motors[m].get_position()
            motor_mutex.write(position)
        if self.poynting_correction:
            self.poynting_correction.get_motor_positions()

    def is_busy(self):
        return any(self.motors[m].busy() for m in self.motor_names)

    def set_shutter(self, inputs):
        shutter_state = inputs[0]
        error = self.shutter.set_position(shutter_state)
        self.shutter_position.write(shutter_state)
        return error


# --- gui -----------------------------------------------------------------------------------------


class GUI(BaseGUI):
    pass

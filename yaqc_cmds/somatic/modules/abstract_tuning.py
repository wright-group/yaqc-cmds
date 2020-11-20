import configparser
import pathlib

import numpy as np
import WrightTools as wt

import yaqc_cmds
import somatic.acquisition as acquisition
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.project.classes as pc
import yaqc_cmds.hardware.opas as opas
import yaqc_cmds.hardware.spectrometers as spectrometers
import yaqc_cmds.devices.devices as devices


class Worker(acquisition.Worker):
    def process(self, scan_folder):
        config = self.config_dictionary
        data_path = wt.kit.glob_handler(".data", folder=str(scan_folder))[0]
        data = wt.data.from_Yaqc_cmds(data_path)
        kwargs = {k.lower(): v for k, v in config["Processing"].items()}
        apply_ = kwargs.pop("apply")
        old_path = self.curve.save(scan_folder, plot=False)
        old_path.rename(old_path.with_suffix(f".old{old_path.suffix}"))
        curve = self._process(data, self.curve, config=config, scan_folder=scan_folder, **kwargs)
        if apply_ and not self.stopped.read():
            path = curve.save(pathlib.Path(self.opa_hardware.curve_paths[self.curve_id]).parent)
            self.opa_hardware.driver.curve_paths[self.curve_id].write(str(path))
            yaqc_cmds.somatic.updated_attune_store.emit()
        self.upload(
            scan_folder,
            reference_image=str(pathlib.Path(scan_folder) / self.reference_image),
        )

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        ...

    @property
    def config_dictionary(self):
        out = {}
        for section in self.aqn.sections:
            out[section] = {k: self.aqn.read(section, k) for k in self.aqn.get_options(section)}
        return out

    def run(self):
        full_shape = []
        axes = []

        config = self.config_dictionary
        opa_name = config["OPA"]["opa"]
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        self.opa_hardware = opas.hardwares[opa_index]

        self.curve = self.opa_hardware.curve.copy()
        curve_ids = list(self.opa_hardware.driver.curve_paths.keys())
        for section, conf in config.items():
            if not section.startswith("Motor"):
                continue
            name = conf["motor"]
            break
        else:
            # KFS 2019-10-28: Only applys to tune test in current tuning functions
            # Do not want it using poynting in this case
            if self.curve.kind == "poynting":
                self.curve = self.curve.subcurve
            name = self.curve.dependent_names[0]
        while not name in self.curve.dependent_names:
            self.curve = self.curve.subcurve
            curve_ids = curve_ids[:-1]
        self.curve_id = curve_ids[-1]
        self.curve.convert("wn")

        spec_name = config["Spectrometer"]["spectrometer"]
        spec_action = config["Spectrometer"]["action"]
        spec_names = [spec.name for spec in spectrometers.hardwares]
        spec_index = spec_names.index(spec_name)
        self.spec_hardware = spectrometers.hardwares[spec_index]

        if spec_action == "Zero Order":
            self.spec_hardware.set_position(0)

        axis_identity = opa_name
        if spec_action == "Tracking":
            axis_identity = f"{opa_name}={spec_name}"
        axes.append(acquisition.Axis(self.curve.setpoints[:], "wn", axis_identity, axis_identity))
        full_shape.append(len(self.curve.setpoints))
        for section, conf in config.items():
            if not section.startswith("Motor"):
                continue
            if "num" not in conf:
                continue
            full_shape.append(int(conf["num"]))
        if spec_action == "Scanned":
            for section, conf in config.items():
                if not section.startswith("Spectral"):
                    continue
                full_shape.append(int(conf["num"]))
        print(f"{full_shape}")
        index = 1

        for section, conf in config.items():
            if not section.startswith("Motor"):
                continue
            if "num" not in conf:
                continue
            name = conf["motor"]
            width = conf["width"]
            npts = int(conf["num"])
            points = np.linspace(-width / 2.0, width / 2.0, npts)
            sh = [1] * (len(full_shape) - 1)
            sh[0] = len(self.curve[name])
            centers = self.curve[name][:].reshape(sh)
            print(f"{sh}")
            centers = np.broadcast_to(centers, full_shape[:index] + full_shape[index + 1 :])
            hardware_dict = {opa_name: [self.opa_hardware, "set_motor", [name, "destination"]]}
            axes.append(
                acquisition.Axis(
                    points,
                    None,
                    f"{opa_name}_{name}",
                    f"D{opa_name}",
                    hardware_dict,
                    centers=centers,
                )
            )
            index += 1

        if spec_action == "Scanned":
            for section, conf in config.items():
                if not section.startswith("Spectral"):
                    continue
                name = conf["axis"]
                width = conf["width"]
                npts = int(conf["num"])
                points = np.linspace(-width / 2.0, width / 2.0, npts)
                sh = [1] * (len(full_shape) - 1)
                sh[0] = len(self.curve.setpoints)
                centers = self.curve.setpoints[:].reshape(sh)
                centers = np.broadcast_to(centers, full_shape[:index] + full_shape[index + 1 :])
                axes.append(acquisition.Axis(points, "wn", f"{name}", f"D{name}", centers=centers))
                index += 1

        self.scan(axes)

        if not self.stopped.read():
            self.finished.write(True)


class GUI(acquisition.GUI):
    def __init__(self, module_name):
        self.items.update(
            {
                "OPA": OpaSectionWidget("OPA", self),
                "Spectrometer": SpectrometerSectionWidget("Spectrometer", self),
                "Processing": ProcessingSectionWidget("Processing", self),
            }
        )
        super().__init__(module_name)
        for item in self.items.values():
            for i in item.items.values():
                i.updated.connect(self.on_update)
        self.items["Device Settings"] = self.device_widget
        self.on_update()

    def create_frame(self):
        self.layout.addWidget(self["OPA"].input_table)
        self.layout.addWidget(self["Spectrometer"].input_table)
        for name, item in self.items.items():
            if name in ("OPA", "Spectrometer", "Processing", "Device Settings"):
                continue
            self.layout.addWidget(item.input_table)
        self.layout.addWidget(self["Processing"].input_table)

    def load(self, aqn_path):
        for item in self.items.values():
            item.load(aqn_path)

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write("info", "description", f"{self['OPA']['OPA'].read()} {self.module_name}")
        for item in self.items.values():
            item.save(aqn_path)

    def on_device_settings_updated(self):
        self.on_update()

    def on_update(self):
        for item in self.items.values():
            if isinstance(item, AqnSectionWidget):
                item.on_update()

    def __getitem__(self, name):
        return self.items[name]


class AqnSectionWidget:
    def __init__(self, section_name, parent):
        self.section_name = section_name
        self.parent = parent
        self.items = {}

    @property
    def input_table(self):
        input_table = pw.InputTable()
        input_table.add(self.section_name, None)
        for name, item in self.items.items():
            input_table.add(name, item)
        return input_table

    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        for name, item in self.items.items():
            item.write(aqn.read(self.section_name, name))

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        try:
            aqn.add_section(self.section_name)
        except configparser.DuplicateSectionError:
            pass
        for name, item in self.items.items():
            aqn.write(self.section_name, name, item.read())

    def on_update(self):
        pass

    def __getitem__(self, name):
        return self.items[name]


class OpaSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        allowed = [hardware.name for hardware in opas.hardwares]
        self.items["OPA"] = pc.Combo(allowed)


class SpectrometerSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        allowed = [hardware.name for hardware in spectrometers.hardwares]
        self.items["Action"] = pc.Combo(
            ["Scanned", "None", "Tracking", "Zero Order"], initial_value="Scanned"
        )
        self.items["Spectrometer"] = pc.Combo(allowed)

    def on_update(self):
        self.items["Spectrometer"].set_disabled(self.items["Action"].read() == "None")


class ProcessingSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Channel"] = pc.Combo(devices.control.channel_names)
        self.items["level"] = pc.Bool(initial_value=False)
        self.items["gtol"] = pc.Number(initial_value=1e-3, decimals=5)
        self.items["ltol"] = pc.Number(initial_value=1e-2, decimals=5)
        self.items["Apply"] = pc.Bool(initial_value=False)

    def on_update(self):
        self.items["Channel"].set_allowed_values(devices.control.channel_names)


class SpectralAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Axis"] = pc.Combo()
        self.items["Width"] = pc.Number(initial_value=-250)
        self.items["Num"] = pc.Number(initial_value=51, decimals=0)

    def on_update(self):
        if self.parent["Spectrometer"]["Action"].read() == "Scanned":
            allowed = [self.parent["Spectrometer"]["Spectrometer"].read()]
            for value in self.items.values():
                value.set_disabled(False)
            self["Axis"].set_disabled(True)
        else:
            for value in self.items.values():
                value.set_disabled(True)
            allowed = []
            for dev in devices.control.devices:
                if dev.has_map:
                    allowed.extend(dev.map_axes.keys())
            if not allowed:
                allowed = [""]
        self.items["Axis"].set_allowed_values(allowed)
        self.items["Axis"].set_disabled(len(allowed) > 1)


class MotorAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Motor"] = pc.Combo()
        self.items["Width"] = pc.Number(initial_value=1, decimals=3)
        self.items["Num"] = pc.Number(initial_value=31, decimals=0)

    def on_update(self):
        hardware = next(h for h in opas.hardwares if h.name == self.parent["OPA"]["OPA"].read())
        self.items["Motor"].set_allowed_values(hardware.curve.dependent_names)


def load():
    return False

### import ####################################################################

import os

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

import WrightTools as wt
import attune

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'TUNE TEST'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        data_path = wt.kit.glob_handler('.data', folder=str(scan_folder))[0]
        data = wt.data.from_PyCMDS(data_path)
        # make tuning curve
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa = opas.hardwares[opa_index]
        curve = opa.curve.copy()
        if curve.kind == 'poynting':
            curve = curve.subcurve
        channel_name = self.aqn.read('processing', 'channel')
        order = int(self.aqn.read('spectrometer', 'order'))
        transform = list(data.axis_names)[:2]
        spectral_axis = self.aqn.read("processing", "spectral_axis")
        if self.aqn.read("spectrometer", "action") == "Scanned":
            spectral_axis = self.aqn.read("spectrometer", "spectrometer")
        transform = [opa_name, f"{spectral_axis}-{opa_name}"]
        if order != 1:
            if order > 0:
                transform[1] = f"({transform[-1]})/{order}"
            else:
                transform[1] = f"({transform[-1]})*{abs(order)}"


        data.transform(*transform)
        data.print_tree()
        attune.workup.tune_test(
            data,
            channel_name,
            curve,
            save_directory=scan_folder,
            level=self.aqn.read("processing", "level"),
            gtol=self.aqn.read("processing", "gtol"),
            ltol=self.aqn.read("processing", "ltol"),
        )
        if not self.stopped.read() and self.aqn.read("processing", "apply_curve"):
            p = wt.kit.glob_handler('.curve', folder = str(scan_folder))[0]
            self.opa_hardware.driver.curve_paths[self.curve_id].write(p)
        # upload
        self.upload(scan_folder, reference_image=os.path.join(scan_folder, 'tune_test.png'))
    
    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve.copy()
        if curve.kind == 'poynting':
            curve = curve.subcurve
        curve.convert('wn')
        spectrometer = self.aqn.read("spectrometer", "spectrometer")

        if self.aqn.read("spectrometer", "action") == "Scanned":
            axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_friendly_name, opa_friendly_name)
            axes.append(axis)
            # mono
            identity = f'D{spectrometer}'
            try:
                order = self.aqn.read('spectrometer', 'order')
            except KeyError:
                order = 1
            if order == 0:
                raise ValueError("Spectrometer order cannot be 0")
            elif order > 0:
                kwargs = {'centers': curve.setpoints[:] * self.aqn.read('spectrometer', 'order')}
            else:
                kwargs = {'centers': curve.setpoints[:] / abs(self.aqn.read('spectrometer', 'order'))}
            width = self.aqn.read('spectrometer', 'width')/2.
            npts = self.aqn.read('spectrometer', 'number')
            points = np.linspace(-width, width, npts)
            axis = acquisition.Axis(points, 'wn', spectrometer, identity, **kwargs)
            axes.append(axis)
        elif self.aqn.read("spectrometer", "action").startswith("Tracking"):
            axis = acquisition.Axis(curve.setpoints[:], 'wn', f"{opa_friendly_name}={spectrometer}", f"{opa_friendly_name}={spectrometer}")
            axes.append(axis)
        else:
            axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_friendly_name, opa_friendly_name)
            axes.append(axis)
        # do scan
        self.scan(axes)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add('OPA', None)
        input_table.add('OPA', self.opa_combo)
        # mono
        input_table.add('Spectrometer', None)
        self.spec_action = pc.Combo(["Scanned", "None (array detected)", "Tracking (array detected)"], initial_value = "Scanned")
        self.spec_action.updated.connect(self.on_spec_action_updated)
        self.spectrometer = pc.Combo(allowed_values=[h.name for h in spectrometers.hardwares])
        input_table.add("Action", self.spec_action)
        input_table.add("Spectrometer", self.spectrometer)
        self.mono_width = pc.Number(ini=ini, units='wn',
                                    section='main', option='mono width (wn)',
                                    import_from_ini=True, save_to_ini_at_shutdown=True)
        self.mono_width.set_disabled_units(True)
        input_table.add('Width', self.mono_width)
        self.mono_npts = pc.Number(initial_value=51, decimals=0)
        input_table.add('Number', self.mono_npts)
        self.mono_order = pc.Number(initial_value=1, decimals=0)
        input_table.add('Order', self.mono_order)
        # processing
        input_table.add('Processing', None)
        allowed = []
        for dev in devices.control.devices:
            if dev.has_map:
                allowed.extend(dev.map_axes.keys())
        if not allowed:
            allowed = [""]
        self.spectral_axis = pc.Combo(allowed_values=allowed)
        self.spectral_axis.set_disabled(True)
        input_table.add("Spectral Axis", self.spectral_axis)

        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names, ini=ini, section='main', option='channel name')
        self.level = pc.Bool(initial_value=False)
        self.gtol = pc.Number(initial_value=1e-3, decimals=5)
        self.ltol = pc.Number(initial_value=1e-2, decimals=5)
        self.apply_curve = pc.Bool(initial_value=False)
        input_table.add('Channel', self.channel_combo)
        input_table.add('level', self.level)
        input_table.add('gtol', self.gtol)
        input_table.add('ltol', self.ltol)
        input_table.add('Apply Curve', self.apply_curve)

        # finish
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        self.mono_width.write(aqn.read('spectrometer', 'width'))
        self.mono_npts.write(aqn.read('spectrometer', 'number'))
        self.mono_order.write(aqn.read('spectrometer', 'order'))
        self.spectrometer.write(aqn.read('spectrometer', 'spectrometer'))
        self.spec_action.write(aqn.read('spectrometer', 'action'))
        self.spectral_axis.write(aqn.read('processing', 'spectral_axis'))
        self.channel_combo.write(aqn.read('processing', 'channel'))
        self.level.write(aqn.read("processing", "level"))
        self.ltol.write(aqn.read("processing", "ltol"))
        self.gtol.write(aqn.read("processing", "gtol"))
        self.apply_curve.write(aqn.read("processing", "apply_curve"))
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_device_settings_updated(self):
        self.channel_combo.set_allowed_values(devices.control.channel_names)

    def on_spec_action_updated(self):
        scanned = self.spec_action.read() == "Scanned"
        self.spectrometer.set_disabled(self.spec_action.read().startswith("None"))
        self.mono_width.set_disabled(not scanned)
        self.mono_npts.set_disabled(not scanned)
        self.mono_order.set_disabled(not scanned)
        self.spectral_axis.set_disabled(scanned)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', '{} tune test'.format(self.opa_combo.read()))
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())
        aqn.add_section('spectrometer')
        aqn.write('spectrometer', 'width', self.mono_width.read())
        aqn.write('spectrometer', 'number', self.mono_npts.read())
        aqn.write('spectrometer', 'order', self.mono_order.read())
        aqn.write('spectrometer', 'spectrometer', self.spectrometer.read())
        aqn.write('spectrometer', 'action', self.spec_action.read())
        aqn.add_section('processing')
        aqn.write('processing', 'channel', self.channel_combo.read())
        aqn.write('processing', 'level', self.level.read())
        aqn.write('processing', 'gtol', self.gtol.read())
        aqn.write('processing', 'ltol', self.ltol.read())
        aqn.write('processing', 'apply_curve', self.apply_curve.read())
        aqn.write('processing', 'spectral_axis', self.spectral_axis.read())
        # allow devices to write settings
        self.device_widget.save(aqn_path)
        
def load():
    return True
def mkGUI():        
    global gui
    gui = GUI(module_name)

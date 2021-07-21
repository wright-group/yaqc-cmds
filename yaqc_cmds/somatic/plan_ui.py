from collections import defaultdict
import itertools
import json

import toolz
from qtpy import QtWidgets
from bluesky_queueserver.manager.comms import zmq_single_request

import WrightTools as wt
from yaqc_cmds.project import widgets as pw
from yaqc_cmds.project import classes as pc

devices_all = zmq_single_request("devices_allowed", {"user_group": "admin"})[0]["devices_allowed"]
devices_movable = list(filter(lambda x: devices_all[x]["is_movable"], devices_all))
devices_not_movable = list(filter(lambda x: not devices_all[x]["is_movable"], devices_all))


class PlanUI:
    def __init__(self, items=None):
        if items is None:
            self.items = [
                MetadataWidget(),
                ArgsWidget(),
                KwargsWidget(),
            ]
        else:
            self.items = items
        self.frame = QtWidgets.QWidget()
        self.frame.setLayout(QtWidgets.QVBoxLayout())
        layout = self.frame.layout()
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        for x in self.items:
            layout.addWidget(x.frame)

    @property
    def args(self):
        return list(itertools.chain(*[x.args for x in self.items]))

    @property
    def kwargs(self):
        out = {}
        for x in self.items:
            out.update(x.kwargs)
        return out

    def load(self, *args, **kwargs):
        for x in self.items:
            if x.nargs < 0:
                x.args = args
                args = []
            elif x.nargs > 0:
                x.args = args[: x.nargs]
                args = args[x.nargs :]
            x.kwargs = kwargs


class MetadataWidget:
    def __init__(self):
        self.nargs = 0
        self.fields = {
            "Name": pc.String(),
            "Info": pc.String(),
            "Experimentor": pc.Combo(["Kyle", "Emily", "Kelson", "Dan"]),
        }

    @property
    def frame(self):
        frame = pw.InputTable()
        frame.add("Metadata", None)
        for k, v in self.fields.items():
            frame.add(k, v)
        return frame

    @property
    def args(self):
        return []

    @args.setter
    def args(self, arg):
        pass

    @property
    def kwargs(self):
        return {"md": {k: v.read() for k, v in self.fields.items()}}

    @kwargs.setter
    def kwargs(self, kwargs):
        md = kwargs.get("md", {})
        for k, v in self.fields.items():
            if k in md:
                v.write(md[k])


class ArgsWidget:
    def __init__(self):
        self.nargs = -1
        self.frame = pw.InputTable()
        self.args_input = pc.String()
        self.frame.add("Args", self.args_input)

    @property
    def args(self):
        return json.loads(self.args_input.read() or "[]")

    @args.setter
    def args(self, *args):
        self.args_input.write(json.dumps(args))

    @property
    def kwargs(self):
        return {}

    @kwargs.setter
    def kwargs(self, **kwargs):
        pass


class KwargsWidget:
    def __init__(self):
        self.nargs = 0
        self.frame = pw.InputTable()
        self.kwargs_input = pc.String()
        self.frame.add("Kwargs", self.kwargs_input)

    @property
    def kwargs(self):
        return json.loads(self.kwargs_input.read() or "{}")

    @kwargs.setter
    def kwargs(self, **kwargs):
        self.kwargs_input.write(json.dumps(kwargs))

    @property
    def args(self):
        return []

    @args.setter
    def args(self, *args):
        pass


class SingleWidget:
    def __init__(self, name, kwarg=None):
        self.nargs = 1
        self.frame = pw.InputTable()
        self.frame.add(name, self.input)
        self.kwarg = kwarg

    @property
    def args(self):
        return [self.input.read()] if not self.kwarg else []

    @args.setter
    def args(self, arg):
        if not self.kwarg:
            self.input.write(arg)

    @property
    def kwargs(self):
        return {self.kwarg: self.input.read()} if self.kwarg else {}

    @kwargs.setter
    def kwargs(self, **kwargs):
        if self.kwarg in kwargs:
            self.input.write(kwargs[self.kwarg])


class BoolWidget(SingleWidget):
    def __init__(self, name, kwarg=None):
        self.input = pc.Bool()
        super().__init__(name, kwarg)


class StrWidget(SingleWidget):
    def __init__(self, name, kwarg=None):
        self.input = pc.String()
        super().__init__(name, kwarg)


class EnumWidget(SingleWidget):
    def __init__(self, name, options: dict, kwarg=None):
        self.input = pc.Combo(options.keys())
        super().__init__(name, kwarg)
        self.options = options

    @property
    def args(self):
        return [self.options[self.input.read()]] if not self.kwarg else []

    @args.setter
    def args(self, arg):
        if not self.kwarg:
            self.input.write(next([k for k, v in self.options.items() if arg == v]))

    @property
    def kwargs(self):
        return {self.kwarg: self.options[self.input.read()]} if self.kwarg else {}

    @kwargs.setter
    def kwargs(self, **kwargs):
        if self.kwarg in kwargs:
            arg = kwargs[kwarg]
            self.input.write(next([k for k, v in self.options.items() if arg == v]))


class DeviceListWidget:
    def __init__(self):
        self.nargs = 1
        self.inputs = {k: pc.Bool(True) for k in devices_not_movable}
        self.frame = pw.InputTable()
        self.frame.add("Devices", None)
        for k, v in self.inputs.items():
            self.frame.add(k, v)

    @property
    def kwargs(self):
        return {}

    @kwargs.setter
    def kwargs(self, kwargs):
        pass

    @property
    def args(self):
        return [[k for k, v in self.inputs.items() if v.read()]]

    @args.setter
    def args(self, args):
        arg = args[0]
        for device in self.inputs:
            if device in arg:
                self.inputs[device].write(True)
            else:
                self.inputs[device].write(False)


class ConstantWidget:
    def __init__(self):
        self.nargs = 0
        self.frame = QtWidgets.QWidget()
        self.frame.setLayout(QtWidgets.QVBoxLayout())
        self.frame.layout().setMargin(0)
        label = pw.InputTable()
        label.add("Constants", None)
        self.frame.layout().addWidget(label)
        self.constants_container_widget = QtWidgets.QWidget()
        self.constants_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.constants_container_widget.layout().setMargin(0)
        self.constants = []
        self.frame.layout().addWidget(self.constants_container_widget)
        add_button = pw.SetButton("ADD")
        remove_button = pw.SetButton("REMOVE", "stop")
        add_button.clicked.connect(self.add_constant)
        remove_button.clicked.connect(self.remove_constant)
        self.frame.layout().addWidget(add_button)
        self.frame.layout().addWidget(remove_button)

    def add_constant(self, hardware="d0", units="mm", terms=None):
        # TODO better default
        if terms is None:
            terms = [[1, "d1"]]
        const = Constant(hardware, units, terms)
        self.constants.append(const)
        self.constants_container_widget.layout().addWidget(const)

    def remove_constant(self):
        if not self.constants:
            return
        const = self.constants[-1]
        self.constants = self.constants[:-1]
        self.constants_container_widget.layout().removeWidget(const)
        del const

    @property
    def args(self):
        return []

    @args.setter
    def args(self, args):
        pass

    @property
    def kwargs(self):
        return {"constants": [c.args for c in self.constants]}

    @kwargs.setter
    def kwargs(self, kwargs):
        while self.constants.count():
            self.remove_constant()
        for c in kwargs.get("constants", []):
            self.add_constant(*c)


class Constant(pw.InputTable):
    def __init__(self, hardware, units, terms):
        super().__init__()
        self.add("Constant", None)
        self.hardware = pc.Combo(devices_movable)
        self.hardware.write(hardware)
        self.add("Hardware", self.hardware)
        self.units = pc.Combo(wt.units.blessed_units)
        self.units.write(units)
        self.add("Units", self.units)
        self.expression = pc.String()
        self.expression.write(
            " + ".join(f"{coeff}*{hw}" if hw else f"{coeff}" for coeff, hw in terms)
        )
        self.add("Expression", self.expression)

    @property
    def args(self):
        return [self.hardware.read(), self.units.read(), self.terms]

    @property
    def terms(self):
        import sympy

        expr = sympy.parse_expr(self.expression.read())
        coeffs = expr.as_coefficients_dict()
        return [[float(coeff), i.name if i != 1 else None] for i, coeff in coeffs.items()]


class GridScanArgsWidget:
    def __init__(self):
        self.nargs = -1
        self.frame = QtWidgets.QWidget()
        self.frame.setLayout(QtWidgets.QVBoxLayout())
        # self.frame.layout().setMargin(0)
        label = pw.InputTable()
        label.add("Axes", None)
        self.frame.layout().addWidget(label)
        self.axis_container_widget = QtWidgets.QWidget()
        self.axis_container_widget.setLayout(QtWidgets.QVBoxLayout())
        self.axis_container_widget.layout().setMargin(0)
        self.axes = []
        self.frame.layout().addWidget(self.axis_container_widget)
        add_button = pw.SetButton("ADD")
        remove_button = pw.SetButton("REMOVE", "stop")
        add_button.clicked.connect(self.add_axis)
        remove_button.clicked.connect(self.remove_axis)
        self.frame.layout().addWidget(add_button)
        self.frame.layout().addWidget(remove_button)
        self.add_axis()

    def add_axis(self, hardware="d0", start=0, stop=1, npts=11, units="mm"):
        # TODO better default
        axis = Axis(hardware, start, stop, npts, units)
        self.axes.append(axis)
        self.axis_container_widget.layout().addWidget(axis)

    def remove_axis(self):
        if not self.axes:
            return
        const = self.axes[-1]
        self.axes = self.axes[:-1]
        self.axis_container_widget.layout().removeWidget(const)
        del const

    @property
    def args(self):
        return list(itertools.chain(*[a.args for a in self.axes]))

    @args.setter
    def args(self, args):
        while self.axis.count():
            self.remove_axis()
        for c in toolz.partition(5, args):
            self.add_axis(*c)

    @property
    def kwargs(self):
        return {}

    @kwargs.setter
    def kwargs(self, kwargs):
        pass


class Axis(pw.InputTable):
    def __init__(self, hardware, start, stop, npts, units):
        super().__init__()
        self.add("Axis", None)
        self.hardware = pc.Combo(devices_movable)
        self.hardware.write(hardware)
        self.add("Hardware", self.hardware)
        self.start = pc.Number(start)
        self.add("Start", self.start)
        self.stop = pc.Number(stop)
        self.add("Stop", self.stop)
        self.npts = pc.Number(npts, decimals=0)
        self.add("Npts", self.npts)
        self.units = pc.Combo(wt.units.blessed_units)
        self.units.write(units)
        self.add("Units", self.units)

    @property
    def args(self):
        return [
            self.hardware.read(),
            self.start.read(),
            self.stop.read(),
            int(self.npts.read()),
            self.units.read(),
        ]


plan_ui_lookup = defaultdict(PlanUI)
plan_ui_lookup["grid_scan"] = PlanUI(
    [
        MetadataWidget(),
        DeviceListWidget(),
        GridScanArgsWidget(),
        ConstantWidget(),
    ]
)
plan_ui_lookup["rel_grid_scan"] = PlanUI(
    [
        MetadataWidget(),
        DeviceListWidget(),
        GridScanArgsWidget(),
        ConstantWidget(),
    ]
)

import itertools
import json

from qtpy import QtWidgets

from yaqc_cmds.project import widgets as pw
from yaqc_cmds.project import classes as pc


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
        self.args = []
        self.kwargs = {}
        self.frame = pw.InputTable()

    @property
    def args(self):
        return []

    @args.setter
    def args(self, arg):
        pass

    @property
    def kwargs(self):
        return {"md": {}}


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

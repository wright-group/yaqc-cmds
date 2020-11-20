from qtpy import QtCore


class SignalContainer(QtCore.QObject):
    channels_changed = QtCore.Signal()
    sensors_changed = QtCore.Signal()


_signal_container = SignalContainer()
channels_changed = _signal_container.channels_changed
sensors_changed = _signal_container.sensors_changed

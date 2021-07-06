from qtpy import QtCore


class SignalContainer(QtCore.QObject):
    queue_relinquishing_control = QtCore.Signal()
    queue_taking_control = QtCore.Signal()
    updated_attune_store = QtCore.Signal()


_signal_container = SignalContainer()
queue_relinquishing_control = _signal_container.queue_relinquishing_control
queue_taking_control = _signal_container.queue_taking_control
updated_attune_store = _signal_container.updated_attune_store

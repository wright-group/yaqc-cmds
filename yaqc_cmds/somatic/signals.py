from qtpy import QtCore


class SignalContainer(QtCore.QObject):
    data_file_created = QtCore.Signal()
    data_file_written = QtCore.Signal()
    queue_relinquishing_control = QtCore.Signal()
    queue_taking_control = QtCore.Signal()
    updated_attune_store = QtCore.Signal()


_signal_container = SignalContainer()
data_file_created = _signal_container.data_file_created
data_file_written = _signal_container.data_file_written
queue_relinquishing_control = _signal_container.queue_relinquishing_control
queue_taking_control = _signal_container.queue_taking_control
updated_attune_store = _signal_container.updated_attune_store

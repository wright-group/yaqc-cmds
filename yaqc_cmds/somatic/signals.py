from qtpy import QtCore
from bluesky_queueserver.manager.comms import zmq_single_request


class SignalContainer(QtCore.QObject):
    queue_updated = QtCore.Signal()
    history_updated = QtCore.Signal()
    devices_allowed_updated = QtCore.Signal()
    plans_allowed_updated = QtCore.Signal()
    manager_state_updated = QtCore.Signal(str)

    update_plot = QtCore.Signal()

    queue_relinquishing_control = QtCore.Signal()
    queue_taking_control = QtCore.Signal()
    updated_attune_store = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.status = {}
        self.heartbeat = QtCore.QTimer()
        self.heartbeat.timeout.connect(self.process_status)
        self.heartbeat.start(500)

    def process_status(self):
        status = zmq_single_request("status")[0]
        if not status:
            return
        if not status.get("worker_environment_exists"):
            zmq_single_request("environment_open")
        if self.status.get("devices_allowed_uid") != status.get("devices_allowed_uid"):
            self.devices_allowed_updated.emit()
        if self.status.get("manager_state") != status.get("manager_state"):
            self.manager_state_updated.emit(status["manager_state"])
            if status["manager_state"] == "idle":
                self.queue_relinquishing_control.emit()
            else:
                self.queue_taking_control.emit()
        if self.status.get("plan_history_uid") != status.get("plan_history_uid"):
            self.history_updated.emit()
        if self.status.get("plan_queue_uid") != status.get("plan_queue_uid"):
            self.queue_updated.emit()
        if self.status.get("plans_allowed_uid") != status.get("plans_allowed_uid"):
            self.plans_allowed_updated.emit()
        self.status = status


_signal_container = SignalContainer()

queue_updated = _signal_container.queue_updated
history_updated = _signal_container.history_updated
devices_allowed_updated = _signal_container.devices_allowed_updated
plans_allowed_updated = _signal_container.plans_allowed_updated
manager_state_updated = _signal_container.manager_state_updated
update_plot = _signal_container.update_plot
queue_relinquishing_control = _signal_container.queue_relinquishing_control
queue_taking_control = _signal_container.queue_taking_control
updated_attune_store = _signal_container.updated_attune_store

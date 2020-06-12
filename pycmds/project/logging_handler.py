# import#########################################################################

import os
import time
import logging
import inspect
import threading

from PySide2 import QtCore

# import packages.psutil as psutil #why doesn't this work!?!?!
import psutil
from . import project_globals as g

app = g.app.read()

# cpu watcher####################################################################


class busy(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = False

    def read(self):
        return self.value

    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()

    def wait_for_update(self):
        if self.value:
            self.lock()
            self.WaitCondition.wait(self)
            self.unlock()


busy = busy()


class cpu(QtCore.QMutex):
    def __init__(self):
        QtCore.QMutex.__init__(self)
        self.WaitCondition = QtCore.QWaitCondition()
        self.value = "??"

    def read(self):
        return self.value

    def write(self, value):
        self.lock()
        self.value = value
        self.WaitCondition.wakeAll()
        self.unlock()

    def wait_for_update(self):
        if self.value:
            self.lock()
            self.WaitCondition.wait(self)
            self.unlock()


cpu = cpu()


class cpu_watcher(QtCore.QObject):
    @QtCore.Slot()
    def get_cpu(self):
        pass
        busy.write(True)
        cpu_now = psutil.cpu_percent(interval=1)
        cpu.write(cpu_now)
        time.sleep(1)  # not meant to loop quickly
        busy.write(False)


cpu_thread = QtCore.QThread()


def begin_cpu_watcher():

    # begin cpu_watcher object in seperate thread
    g.shutdown.add_method(cpu_thread.quit)
    cpu_obj = cpu_watcher()
    cpu_obj.moveToThread(cpu_thread)

    caller = QtCore.QMetaObject()

    def call_cpu_watcher():
        if not busy.read():
            caller.invokeMethod(cpu_obj, "get_cpu")

    g.poll_timer.connect_to_timeout(call_cpu_watcher)
    cpu_thread.start()

    g.shutdown.read().connect(cpu_thread.quit)


# logger#########################################################################

# filepath
filepath = os.path.join(
    g.main_dir.read(), "logs", str(time.strftime("%Y.%m.%d  %H.%M.%S")) + ".log"
)
log_file = open(filepath, "w")
log_file.close()

# setup
logger = logging.getLogger("PyCMDS")
formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs).03d | CPU %(cpu)-2s RAM %(ram)-2s | %(levelname)-8s | Thread %(thread)-5s | %(origin)-20s | %(name)-20s | %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

# set level
logger.setLevel(logging.DEBUG)  # default is info


class ContextFilter(logging.Filter):
    def __init__(self, origin, name):
        self.origin = origin
        self.name = name

    def filter(self, record):
        record.thread = threading.current_thread().ident
        record.origin = self.origin
        record.name = self.name
        cpu_now = cpu.read()
        if cpu_now == "??":
            record.cpu = cpu_now
        else:
            record.cpu = str(int(cpu.read())).zfill(2)
        record.ram = str(int(psutil.swap_memory().percent)).zfill(2)
        return True


def log(level, name, message="", origin="name"):
    """
    logging method for PyCMDS
    accepts strings
    levels: debug, info, warning, error, critical
    """
    # open
    handler = logging.FileHandler(filepath)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # additional context
    if origin == "name":
        origin = str(inspect.stack()[2][1]).split("\\")[-1].replace(".py", "")
    logger.addFilter(ContextFilter(origin, name))

    # log
    getattr(logger, level)(message)

    # close
    logger.removeHandler(handler)
    handler.close()

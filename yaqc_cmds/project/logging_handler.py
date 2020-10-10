# import#########################################################################

import os
import time
import logging
import inspect
import threading
import pathlib
import appdirs

from PySide2 import QtCore

from yaqc_cmds.project import project_globals as g

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


# logger#########################################################################

# filepath
filepath = (
    pathlib.Path(appdirs.user_log_dir("yaqc-cmds", "yaqc-cmds"))
    / f"{str(time.strftime('%Y%m%dT%H%M%S%z'))}.log"
)
filepath.parent.mkdir(parents=True, exist_ok=True)
log_file = open(filepath, "w")
log_file.close()

# setup
logger = logging.getLogger("Yaqc_cmds")
formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs).03d | %(levelname)-8s | Thread %(thread)-5s | %(origin)-20s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

logger.setLevel(logging.DEBUG)


class ContextFilter(logging.Filter):
    def __init__(self, origin, name):
        self.origin = origin
        self.name = name
        super().__init__()

    def filter(self, record):
        record.thread = threading.current_thread().ident
        record.origin = self.origin
        record.name = self.name
        return True


def log(level, name, message="", origin="name"):
    """
    logging method for Yaqc_cmds
    accepts strings
    levels: debug, info, warning, error, critical
    """
    # open
    handler = logging.FileHandler(filepath)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # additional context
    if origin == "name":
        origin = str(inspect.stack()[2][1]).split(os.sep)[-1].replace(".py", "")
    logger.addFilter(ContextFilter(origin, name))
    # log
    getattr(logger, level)(message)
    # close
    handler.flush()
    logger.removeHandler(handler)
    handler.close()

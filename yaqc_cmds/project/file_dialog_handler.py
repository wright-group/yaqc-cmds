"""
QFileDialog objects can only be run in the main thread.
"""


### imports ###################################################################


import os
import time

from PySide2 import QtCore
from PySide2 import QtWidgets

from yaqc_cmds.project import project_globals as g
from yaqc_cmds.project import classes as pc


### FileDialog object #########################################################


directory_filepath = pc.Mutex()
open_filepath = pc.Mutex()
save_filepath = pc.Mutex()


class FileDialog(QtCore.QObject):
    update_ui = QtCore.Signal()
    queue_emptied = QtCore.Signal()

    def __init__(self, enqueued_object, busy_object):
        QtCore.QObject.__init__(self)
        self.name = "file_dialog"
        self.enqueued = enqueued_object
        self.busy = busy_object

    @QtCore.Slot(str, list)
    def dequeue(self, method, inputs):
        """
        Slot to accept enqueued commands from main thread.

        Method passed as qstring, inputs as list of [args, kwargs].

        Calls own method with arguments from inputs.
        """
        self.update_ui.emit()
        method = str(method)  # method passed as qstring
        args, kwargs = inputs
        if g.debug.read():
            print(self.name, " dequeue:", method, inputs, self.busy.read())
        self.enqueued.pop()
        getattr(self, method)(*args, **kwargs)
        if not self.enqueued.read():
            self.queue_emptied.emit()
            self.check_busy()

    def check_busy(self):
        """
        decides if the hardware is done and handles writing of 'busy' to False
        """
        # must always write busy whether answer is True or False
        if self.enqueued.read():
            time.sleep(0.1)  # don't loop like crazy
            self.busy.write(True)
        else:
            self.busy.write(False)
            self.update_ui.emit()

    def clean(self, out):
        """
        takes the output and returns a string that has the properties I want
        """
        out = str(out)
        out = out.replace("/", os.sep)
        return out

    def getExistingDirectory(self, inputs=[]):
        caption, directory, options = inputs
        options = QtWidgets.QFileDialog.ShowDirsOnly
        out = self.clean(
            QtWidgets.QFileDialog.getExistingDirectory(
                g.main_window.read(), caption, str(directory), options
            )
        )
        directory_filepath.write(out)

    def getOpenFileName(self, inputs=[]):
        caption, directory, options = inputs
        out = self.clean(
            QtWidgets.QFileDialog.getOpenFileName(
                g.main_window.read(), caption, str(directory), options
            )[0]
        )
        open_filepath.write(out)

    def getSaveFileName(self, inputs=[]):
        caption, directory, savefilter, selectedfilter, options = inputs
        out = self.clean(
            QtWidgets.QFileDialog.getSaveFileName(
                g.main_window.read(),
                caption,
                directory,
                savefilter,
                selectedfilter,
                options,
            )[0]
        )
        save_filepath.write(out)


busy = pc.Busy()
enqueued = pc.Enqueued()
file_dialog = FileDialog(enqueued, busy)
q = pc.Q(enqueued, busy, file_dialog)


### thread-safe file dialog methods ###########################################

# the q method only works between different threads
# call directly if the calling object is in the main thread


def dir_dialog(caption, directory, options=None):
    inputs = [caption, directory, options]
    if QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getExistingDirectory(inputs)
    else:
        q.push("getExistingDirectory", inputs)
        while busy.read():
            time.sleep(0.1)
    return directory_filepath.read()


def open_dialog(caption, directory, options):
    inputs = [caption, directory, options]
    if QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getOpenFileName(inputs)
    else:
        q.push("getOpenFileName", inputs)
        while busy.read():
            time.sleep(0.1)
    return open_filepath.read()


def save_dialog(caption, directory, savefilter, selectedfilter, options):
    inputs = [caption, directory, savefilter, selectedfilter, options]
    if QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getSaveFileName(inputs)
    else:
        q.push("getSaveFileName", inputs)
        while busy.read():
            time.sleep(0.1)
    return save_filepath.read()

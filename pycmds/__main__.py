import sys

from PySide2 import QtWidgets

from .project import project_globals as g

app = QtWidgets.QApplication(sys.argv)
print(app)
print(g.app.read())
g.app.write(app)
print(g.app.read())

from ._main_window import MainWindow

from .project import style

def main():
    main_window = MainWindow()
    style.set_style(app)
    main_window.show()
    main_window.showMaximized()
    app.exec_()
    return main_window

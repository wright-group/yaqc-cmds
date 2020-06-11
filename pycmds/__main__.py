from ._main_window import MainWindow

def main():
    global MainWindow
    MainWindow = MainWindow()
    style.set_style()
    MainWindow.show()
    MainWindow.showMaximized()
    app.exec_()
    return MainWindow

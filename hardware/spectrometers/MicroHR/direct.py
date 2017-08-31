import time
import gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
import gen_py.JYMono as JYMono

ctrl = JYMono.Monochromator()
ctrl.Uniqueid = 'Mono1'
ctrl.Load()
ctrl.OpenCommunications()

forceInit = True  # this toggles mono homing behavior
emulate = False
notThreaded = True  # no idea what this does...
ctrl.Initialize(forceInit, emulate, notThreaded)

ctrl.MovetoWavelength(632.8)  # nm

while ctrl.IsBusy():
    print(ctrl.GetCurrentWavelength())
    time.sleep(0.1)
print(ctrl.GetCurrentWavelength())

ctrl.CloseCommunications()

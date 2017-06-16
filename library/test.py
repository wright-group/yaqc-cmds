### import ####################################################################


from PyAPT import PyAPT


### workspace #################################################################


motor = PyAPT.APTMotor(45837036, HWTYPE=42)
print(motor.getPos())


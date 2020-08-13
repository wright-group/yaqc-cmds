### import ####################################################################


import os
import shutil
import platform
import collections

import ctypes


### define ####################################################################


directory = os.path.dirname(os.path.abspath(__file__))


### first-time ################################################################


d = os.path.join(directory, "APTDLLPAck", "DLL")
if platform.architecture()[0] == "32bit":
    d = os.path.join(d, "x86")
else:
    d = os.path.join(d, "x64")
ns = ["APT.dll", "APT.lib"]
for n in ns:
    destination = os.path.join(directory, n)
    if not os.path.isfile(destination):
        source = os.path.join(d, n)
        shutil.copy(source, directory)


### hardware types ############################################################


hardware_types = collections.OrderedDict()
hardware_types[11] = "1 Ch benchtop stepper driver"
hardware_types[12] = "1 Ch benchtop stepper driver"
hardware_types[13] = "2 Ch benchtop stepper driver"
hardware_types[14] = "1 Ch benchtop DC servo driver"
hardware_types[21] = "1 Ch stepper driver card (used within BSC102,103 units)"
hardware_types[22] = "1 Ch DC servo driver card (used within BDC102,103 units)"
hardware_types[24] = "1 Ch DC servo driver cube"
hardware_types[25] = "1 Ch stepper driver cube"
hardware_types[26] = "2 Ch modular stepper driver module"
hardware_types[29] = "1 Ch Stepper driver T-Cube"
hardware_types[31] = "1 Ch DC servo driver T-Cube"
hardware_types[42] = "LTS300/LTS150 Long Travel Integrated Driver/Stages"
hardware_types[43] = "L490MZ Integrated Driver/Labjack"
hardware_types[44] = "1/2/3 Ch benchtop brushless DC servo driver"


### status codes ##############################################################


status_codes = collections.OrderedDict()
status_codes[0] = "stopped and disconnected"
status_codes[-2147478512] = "moving"
status_codes[-2147479552] = "stopped not homed"
status_codes[-2147478528] = "stopped and homed"
status_codes[-2147478496] = "???"


### units codes ###############################################################


units_codes = collections.OrderedDict()
units_codes[1] = "mm"
units_codes[2] = "deg"


### motor #####################################################################


class APTMotor:
    def __init__(self, serial_number=None, hardware_type=None):
        self.serial_number = serial_number
        self.hardware_type = hardware_type
        # create dll
        p = os.path.join(directory, "APT.dll")
        self.dll = ctypes.windll.LoadLibrary(str(p))
        # initialize hardware
        self.dll.EnableEventDlg(True)
        self.dll.APTInit()
        error = self.dll.InitHWDevice(ctypes.c_long(serial_number))

    def _get_hardware_information(self):
        serial_number = ctypes.c_long(self.serial_number)
        model = ctypes.c_buffer(255)
        softwareVersion = ctypes.c_buffer(255)
        hardwareNotes = ctypes.c_buffer(255)
        error = self.dll.GetHWInfo(
            serial_number, model, 255, softwareVersion, 255, hardwareNotes, 255
        )
        return model.value, softwareVersion.value, hardwareNotes.value

    def _get_stage_axis_information(self):
        serial_number = ctypes.c_long(self.serial_number)
        minimumPosition = ctypes.c_float()
        maximumPosition = ctypes.c_float()
        units = ctypes.c_long()
        pitch = ctypes.c_float()
        error = self.dll.MOT_GetStageAxisInfo(
            serial_number,
            ctypes.pointer(minimumPosition),
            ctypes.pointer(maximumPosition),
            ctypes.pointer(units),
            ctypes.pointer(pitch),
        )
        return minimumPosition.value, maximumPosition.value, units.value, pitch.value

    def _get_velocity_parameters(self):
        serial_number = ctypes.c_long(self.serial_number)
        minimumVelocity = ctypes.c_float()
        acceleration = ctypes.c_float()
        maximumVelocity = ctypes.c_float()
        error = self.dll.MOT_GetVelParams(
            serial_number,
            ctypes.pointer(minimumVelocity),
            ctypes.pointer(acceleration),
            ctypes.pointer(maximumVelocity),
        )
        return minimumVelocity.value, acceleration.value, maximumVelocity.value

    def _get_velocity_parameter_limits(self):
        serial_number = ctypes.c_long(self.serial_number)
        maximumAcceleration = ctypes.c_float()
        maximumVelocity = ctypes.c_float()
        error = self.dll.MOT_GetVelParamLimits(
            serial_number,
            ctypes.pointer(maximumAcceleration),
            ctypes.pointer(maximumVelocity),
        )
        return maximumAcceleration.value, maximumVelocity.value

    def _set_velocity_parameters(
        self, minimum_velocity, acceleration, maximum_velocity
    ):
        serial_number = ctypes.c_long(self.serial_number)
        minimumVelocity = ctypes.c_float(minimum_velocity)
        acceleration = ctypes.c_float(acceleration)
        maximumVelocity = ctypes.c_float(maximum_velocity)
        error = self.dll.MOT_SetVelParams(
            serial_number, minimumVelocity, acceleration, maximumVelocity
        )
        return error

    @property
    def acceleration(self):
        return self._get_velocity_parameters()[1]

    @property
    def backlash_distance(self):
        serial_number = ctypes.c_long(self.serial_number)
        BLashDist = ctypes.c_float()
        error = self.dll.MOT_GetBLashDist(serial_number, ctypes.pointer(BLashDist))
        return BLashDist.value

    def blink(self):
        """
        Blink the Active LED.
        """
        serial_number = ctypes.c_long(self.serial_number)
        error = self.dll.MOT_Identify(serial_number)
        return error

    def close(self):
        self.dll.APTCleanUp()

    def go_home(self):
        """
        Move the stage home.
        """
        serial_number = ctypes.c_long(self.serial_number)
        error = self.dll.MOT_MoveHome(serial_number, True)
        return error

    @property
    def maximum_acceleration(self):
        return self._get_velocity_parameter_limits()[0]

    @property
    def maximum_position(self):
        return self._get_stage_axis_information()[1]

    @property
    def maximum_velocity(self):
        return self._get_velocity_parameters()[2]

    @property
    def minimum_position(self):
        return self._get_stage_axis_information()[0]

    @property
    def minimum_velocity(self):
        return self._get_velocity_parameters()[0]

    @property
    def model(self):
        return self._get_hardware_information()[0]

    @property
    def notes(self):
        return self._get_hardware_information()[2]

    @property
    def pitch(self):
        return self._get_stage_axis_information()[3]

    @property
    def position(self):
        serial_number = ctypes.c_long(self.serial_number)
        position = ctypes.c_float()
        error = self.dll.MOT_GetPosition(serial_number, ctypes.pointer(position))
        return position.value

    def set_acceleration(self, acceleration):
        if acceleration > self.maximum_acceleration:
            raise ValueError("acceleration too large")
        self._set_velocity_parameters(
            self.minimum_velocity, acceleration, self.maximum_velocity
        )

    def set_backlash_distance(self, distance):
        serial_number = ctypes.c_long(self.serial_number)
        BLashDist = ctypes.c_float(distance)
        error = self.dll.MOT_SetBLashDist(serial_number, BLashDist)
        return BLashDist.value

    def set_maximum_velocity(self, maximum_velocity):
        self._set_velocity_parameters(
            self.minimum_velocity, self.acceleration, maximum_velocity
        )

    def set_minimum_velocity(self, minimum_velocity):
        self._set_velocity_parameters(
            minimum_velocity, self.acceleration, self.maximum_velocity
        )

    def set_position(self, position, wait=False):
        serial_number = ctypes.c_long(self.serial_number)
        absolutePosition = ctypes.c_float(position)
        error = self.dll.MOT_MoveAbsoluteEx(serial_number, absolutePosition, wait)
        return error

    @property
    def software_version(self):
        return self._get_hardware_information()[1]

    @property
    def status(self):
        serial_number = ctypes.c_long(self.serial_number)
        bits = ctypes.c_long()
        error = self.dll.MOT_GetStatusBits(serial_number, ctypes.pointer(bits))
        return status_codes[bits.value]

    @property
    def units(self):
        return units_codes[self._get_stage_axis_information()[2]]


### testing ###################################################################


if __name__ == "__main__":
    motor = APTMotor(serial_number=45837036, hardware_type=42)
    print("acceleration", motor.acceleration)
    print("maximum_acceleration", motor.maximum_acceleration)
    print("maximum_position", motor.maximum_position)
    print("maximum_velocity", motor.maximum_velocity)
    print("minimum_position", motor.minimum_position)
    print("minimum_velocity", motor.minimum_velocity)
    print("model", motor.model)
    print("notes", motor.notes)
    print("pitch", motor.pitch)
    print("position", motor.position)
    print("software_version", motor.software_version)
    print("units", motor.units)

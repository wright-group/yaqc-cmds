if __name__ == '__main__':
    import os 
    os.chdir('C:\Users\John\Desktop\PyCMDS 00.02')






#see http://pyvisa.readthedocs.org/en/master/

from packages import pyvisa

rm = pyvisa.ResourceManager()
print rm.list_resources()


instrument = rm.open_resource('ASRL4::INSTR')
instrument.baud_rate = 57600
instrument.end_input = pyvisa.constants.SerialTermination.termination_char



instrument.write(unicode("1PA0.000000\r"))
instrument.write(unicode("1TS\r"))
instrument.write(unicode("1TP\r"))
print instrument.read()


instrument.close()
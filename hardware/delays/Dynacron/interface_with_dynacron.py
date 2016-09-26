import serial

ser = serial.Serial('/dev/tty.usbmodemfa131', 57600)

line = ''
while not 'ready' in line:
    line = ser.readline()
    print line

print 'now writing H'
ser.write('H')
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()

print 'now writing P'
ser.write('P')
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()

print 'now writing M'
ser.write('M 1')
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()

print 'now writing A'
ser.write('A 10')
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()

print 'now writing G'
ser.write('G')
print 'line', ser.readline()
print 'line', ser.readline()
print 'line', ser.readline()

ser.close()

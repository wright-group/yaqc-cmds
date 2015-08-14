# written mostly by Rachel with updates by Nathan, Summer 2015

import time
import numpy as np

import matplotlib.pyplot as plt

class Curve:

    def __init__(self, filepath, n = 4):
        '''
        filepath string \npoints
        n integer degree of polynomial fit
        '''
        self.filepath = filepath
        self.read_new_curve(self.filepath,n)

    def adjust_curve(self, old_color, adjusted_color, write_curve=False):
        adjustment = [0,0,0]
        old = self.new_motor_positions(old_color)
        adj = self.new_motor_positions(adjusted_color)
        for i in range (3):
            adjustment[i] = old[i] - adj[i]
            self.motor_functions[i][0][0] += adjustment[i]

    def read_new_curve(self,filepath, n=4):
        '''
        This allows function allows the object to be updated to a new crv file
        without destroying and creating a new curve object. This way, the same
        curve object can be kept throughout the program, even when a new curve is loaded.
        '''
        self.filepath = filepath
        self.points = np.genfromtxt(filepath).T
        self.polyorder = n

        #fit motor polynomials-------------------------------------------------

        moda1 = np.polynomial.polynomial.polyfit(self.points[0], self.points[1], n, full=True)
        moda2 = np.polynomial.polynomial.polyfit(self.points[0], self.points[2], n, full=True)
        moda3 = np.polynomial.polynomial.polyfit(self.points[0], self.points[3], n, full=True)
        self.motor_functions = [moda1, moda2, moda3]



    def new_motor_positions(self, wn):
        '''
        returns list [m0, m1, m2]
        '''

        out = [np.polynomial.polynomial.polyval(wn, self.motor_functions[0][0]),
               np.polynomial.polynomial.polyval(wn, self.motor_functions[1][0]),
               np.polynomial.polynomial.polyval(wn, self.motor_functions[2][0])]

        return out

    def get_color(self, m0, m1, m2, n=4):
        '''
        returns color from motor positions
        '''
        # Modify stored function by subtracting motor position, find roots-----

        a1 = self.motor_functions[0][0][::-1]
        a2 = self.motor_functions[1][0][::-1]
        a3 = self.motor_functions[2][0][::-1]

        a1[4]-=m0
        a2[4]-=m1
        a3[4]-=m2

        color_a1 = np.roots(a1)
        color_a2 = np.roots(a2)
        color_a3 = np.roots(a3)

        # Round the color values to make them equal-----------------------------

        d = 1
        color = [0,0,0]
        color[0] = np.around(color_a1, decimals=d )[3]
        color[1] = np.around(color_a2, decimals=d )[3]
        color[2] = np.around(color_a3, decimals=d )[3]

        #only return color if all motors signify same wavenumber---------------
        if color[0] == color[1] and color [0] == color[2]:
            return np.real(color[0])
        else:
            return float('nan')

    def plot(self):
        '''
        generate plots of each motor position vs color for each curve
        '''
        plt.close('all')
        colors = self.points[0]
        for i, function, motor_positions in zip(range(3), self.motor_functions, self.points[1:]):
            plt.figure()
            plt.title(i)
            plt.scatter(colors, motor_positions)
            plt.plot(colors, np.polynomial.polynomial.polyval(colors, function[0]))

    def write_curve(self, new_tune_curve = [[]], new_file_path = '', update_curve = False, polyorder = 0):
        '''
        Save a list of lists as a new tuning curve file. The default file path appends the date to the current file path.
        Each interior list is in the form [wn,motor0,motor1,motor2], our present default is that these motors are
        the grating, BBO, and mixer respectively.

        The default file type does not look for a date at the end of the old file name. This should be changed.
        '''
        if not new_file_path:
            new_file_path = self.filepath[:self.filepath.index('.')]
            split_path = new_file_path.split('_')
            for s in split_path:
                if s.isdigit() and len(s) == 6:
                    new_file_path = new_file_path[:new_file_path.index(s)]
                    break
            new_file_path = new_file_path + '_' + time.strftime('%y%m%d_%H_%M',time.localtime()) + '.curve'
        if new_tune_curve == [[]]:
            new_tune_curve = [list(i) for i in zip(*self.points)]
        np.savetxt(new_file_path,new_tune_curve)

        if update_curve:
            polyorder = int(polyorder)
            if polyorder < 1:
                polyorder = self.polyorder # uses old polyorder if none or 0 is specified.
            self.filepath = new_file_path
            #fit motor polynomials-------------------------------------------------

            moda1 = np.polynomial.polynomial.polyfit(self.points[0], self.points[1], polyorder, full=True)
            moda2 = np.polynomial.polynomial.polyfit(self.points[0], self.points[2], polyorder, full=True)
            moda3 = np.polynomial.polynomial.polyfit(self.points[0], self.points[3], polyorder, full=True)
            self.motor_functions = [moda1, moda2, moda3]

### testing ###################################################################

if __name__ == '__main__':

    path = 'C:\\Users\\Nathan\\Documents\\GitHub\\PyCMDS\\opas\\pico\\w1_tuning_curve.curve'

    OPA1_curve = curve(path)
#    OPA1_curve.plot()
    mp=OPA1_curve.new_motor_positions(1700)
    print mp
#   adjust curve
    OPA1_curve.adjust_curve(1700,1710)

#    print OPA1_curve.motor_functions

    print OPA1_curve.get_color(mp[0], mp[1], mp[2])
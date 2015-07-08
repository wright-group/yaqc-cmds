import numpy as np
from numpy.polynomial.polynomial import polyval

import matplotlib.pyplot as plt

class curve:
    
    def __init__(self, filepath, n = 2):
        '''
        filepath string \n
        n integer degree of polynomial fit
        '''        
    
        #generate array from file----------------------------------------------
        
        self.filepath = filepath
        self.points = np.genfromtxt(filepath).T
        
        #fit motor polynomials-------------------------------------------------
        
        moda1 = np.polynomial.polynomial.polyfit(self.points[0], self.points[1], n, full=True)
        moda2 = np.polynomial.polynomial.polyfit(self.points[0], self.points[2], n, full=True)        
        moda3 = np.polynomial.polynomial.polyfit(self.points[0], self.points[3], n, full=True)        
        self.motor_functions = [moda1, moda2, moda3]
        
    def get_motor_positions(self, wn):
        '''
        returns list [m0, m1, m2]
        '''
        
        out = [np.polynomial.polynomial.polyval(wn, self.motor_functions[0][0]),
               np.polynomial.polynomial.polyval(wn, self.motor_functions[1][0]),
               np.polynomial.polynomial.polyval(wn, self.motor_functions[2][0])]

        return out            
            
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


    
### testing ###################################################################

if __name__ == '__main__':
    
    path = 'C:\\Users\\Rachel\\Desktop\\tuning\\w1_tuning_curve.curve'

    OPA1_curve = curve(path)
    OPA1_curve.plot()
    print OPA1_curve.get_motor_positions(2000)
    
#import~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#os interaction packages
import os
import re
import sys
import imp
import time
import copy
import inspect
import subprocess
import ConfigParser
import glob #used to search through folders for filesd

#qt is used for gui handling, see Qtforum.org for info
from PyQt4.QtCore import * #* means import all
from PyQt4.QtGui import *

#matplotlib is used for plot generation and manipulation
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.gridspec as grd
from mpl_toolkits.axes_grid1 import make_axes_locatable

#numpy is used for general math in python
import numpy as np
from numpy import sin, cos
                
#scipy is used for some nice array manipulation
import scipy
from scipy.interpolate import griddata, interp1d, interp2d, UnivariateSpline
import scipy.integrate as integrate
from scipy.optimize import leastsq

#pylab
from pylab import *

#filepath for relative navigation purposes
filepath_of_folder = os.path.abspath( __file__ )
filepath_of_folder = filepath_of_folder.replace(r'\topas_tune.pyc', '')
filepath_of_folder = filepath_of_folder.replace(r'\topas_tune.py', '')
topas_tune_ini_filepath = filepath_of_folder + r'\topas_tune.ini'

#constants~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

spitfire_output = 800. #nm
             
wright_colormap_array = ['#FFFFFF','#0000FF','#00FFFF','#00FF00','#FFFF00','#FF0000','#881111']
wright_colormap = mplcolors.LinearSegmentedColormap.from_list('wright', wright_colormap_array)
wright_colormap.set_bad('grey',1.)

#internal format of tune point arrays
#  0 - setpoint      - nm
#  1 - m0(c1)        - us
#  2 - m1(d1)        - us
#  3 - m2(c2)        - us
#  4 - m3(d2)        - us
#  5 - m4(M1)        - us
#  6 - m5(M2)        - us
#  7 - m6(M3)        - us
#  8 - fit center    - nm
#  9 - fit amplitude - a.u.
# 10 - fit FWHM      - nm
# 11 - fit GoF       - percent
# 12 - fit mismatch  - nm
# 13 - source color  - nm
# 14 - reserved
# 15 - reserved
# 16 - reserved
# 17 - reserved
# 18 - reserved
# 19 - reserved

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def crv(interaction,
        OPA,
        filepath = None,
        interaction_string = None,
        curve = None, 
        source_colors = 'old',
        dummy = False,
        output_filepath_seed = None):
    
    if interaction == 'read': #-------------------------------------------------
    
        #currently hardcoded to import base curves...

        #initialize objects- - - - - - - - - - - - - - - - - - - - - - - - - - -
    
        mcf = _get_motor_conversion_factors(OPA)

        #get filepath if not provided- - - - - - - - - - - - - - - - - - - - - -

        if filepath:
            pass
        else:
            #use currently loaded curve
            if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig', 'NON-NON-NON-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 1') #base
            elif interaction_string in ['NON-NON-SF-Sig', 'NON-NON-SH-Idl', 'NON-NON-SF-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 2') #mixer 1
            elif interaction_string in ['NON-SH-NON-Sig', 'NON-SH-SH-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 3') #mixer 2
            elif interaction_string in ['SH-SH-NON-Sig', 'DF1-NON-NON-Sig']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 4') #mixer 3
            else:
                print 'error in _crv'

        #import array- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig', 'NON-NON-NON-Idl']:
            lines_between = 7
        elif interaction_string == 'DF1-NON-NON-Sig':
            lines_between = 9
        else:
            lines_between = 10

        crv = open(filepath, 'r')
        crv_lines = crv.readlines()

        #collect a friendly array of the params for each interactions
        num_points = []
        for i in range(len(crv_lines)):
            if 'NON' in crv_lines[i]:
                num_points.append([i+lines_between, crv_lines[i].replace('\n', ''), int(crv_lines[i+lines_between])])
        num_points = np.array(num_points)
        
        #pick out which interaction string you want to pay attention to
        if interaction_string in ['preamp', 'poweramp']:
            num_points = num_points[0]
        else:
            index = np.where(num_points[:, 1] == interaction_string)[0][0]
            num_points = num_points[index]
        
        row = int(num_points[0]) + 1
        num_tune_points = int(num_points[2])
        points = np.zeros([num_tune_points, 20])
        points[:] = np.nan

        #fill into internal format - - - - - - - - - - - - - - - - - - - - - - -        

        if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig', 'NON-NON-NON-Idl']:        
            #base curves
        
            for i in range(num_tune_points):
                line =  re.split(r'\t+', crv_lines[row])
                points[i, 0] = float(line[1])
                points[i, 1] = int((float(line[3]) - mcf['m0'][1])*mcf['m0'][0])
                points[i, 2] = int((float(line[4]) - mcf['m1'][1])*mcf['m1'][0])
                points[i, 3] = int((float(line[5]) - mcf['m2'][1])*mcf['m2'][0])
                points[i, 4] = int((float(line[6]) - mcf['m3'][1])*mcf['m3'][0])
                points[i, 13] = float(line[0])
                row = row+1
        
        elif interaction_string in ['NON-NON-SH-Idl', 'NON-NON-SF-Idl', 'NON-NON-SF-Sig']:
            #mixer 1 curves
            
            for i in range(num_tune_points):
                line =  re.split(r'\t+', crv_lines[row])
                points[i, 0] = float(line[1])
                points[i, 5] = int((float(line[3]) - mcf['m4'][1])*mcf['m4'][0])
                points[i, 13] = float(line[0])
                row = row+1
                
        elif interaction_string in ['NON-SH-NON-Sig', 'NON-SH-SH-Idl']:
            #mixer 2 curves
            
            for i in range(num_tune_points):
                line =  re.split(r'\t+', crv_lines[row])
                points[i, 0] = float(line[1])
                points[i, 6] = int((float(line[3]) - mcf['m5'][1])*mcf['m5'][0])
                points[i, 13] = float(line[0])
                row = row+1
                
        elif interaction_string in ['SH-SH-NON-Sig', 'DF1-NON-NON-Sig']:
            #mixer 3 curves
            
            for i in range(num_tune_points):
                line =  re.split(r'\t+', crv_lines[row])
                points[i, 0] = float(line[1])
                points[i, 7] = int((float(line[3]) - mcf['m6'][1])*mcf['m6'][0])
                points[i, 13] = float(line[0])
                row = row+1
                
        else:
            
            print 'error filling in _crv read'
            
        return points
            
    elif interaction == 'write': #----------------------------------------------
    
        #initialize objects- - - - - - - - - - - - - - - - - - - - - - - - - - -
    
        to_insert = []
        
        mcf = _get_motor_conversion_factors(OPA)

        #import template filepath- - - - - - - - - - - - - - - - - - - - - - - -
        
        if filepath:
            pass
        else:
            #use currently loaded curve
            if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig', 'NON-NON-NON-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 1') #base
            elif interaction_string in ['NON-NON-SF-Sig', 'NON-NON-SH-Idl', 'NON-NON-SF-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 2') #mixer 1
            elif interaction_string in ['NON-SH-NON-Sig', 'NON-SH-SH-Idl']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 3') #mixer 2
            elif interaction_string in ['SH-SH-NON-Sig', 'DF1-NON-NON-Sig']:
                filepath = _ini_handler('OPA{}'.format(OPA), 
                                        'read',
                                        'Optical Device',
                                        'Curve 4') #mixer 3
            else:
                print 'error in _crv - interaction string =', interaction_string

        old_crv = open(filepath, 'r')
        crv_lines = old_crv.readlines()
        
        if output_filepath_seed:
            pass
        else: 
            output_filepath_seed = filepath

        #decide on output filepath - - - - - - - - - - - - - - - - - - - - - - -

        if dummy:
            if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig', 'NON-NON-NON-Idl']:
                output_filepath = filepath_of_folder + r'\dummy_curves\base dummy.crv'
            elif interaction_string in ['NON-NON-SF-Sig', 'NON-NON-SH-Idl', 'NON-NON-SF-Idl']:
                output_filepath = filepath_of_folder + r'\dummy_curves\mixer1 dummy.crv'
            elif interaction_string in ['NON-SH-NON-Sig', 'NON-SH-SH-Idl']:
                output_filepath = filepath_of_folder + r'\dummy_curves\mixer2 dummy.crv'
            elif interaction_string in ['SH-SH-NON-Sig', 'DF1-NON-NON-Sig']:
                output_filepath = filepath_of_folder + r'\dummy_curves\mixer3 dummy.crv'
        else:
            output_filepath = output_filepath_seed.split('-', 1)[0]
            output_filepath = output_filepath + '- ' + time.strftime("%Y.%m.%d %H_%M_%S") + '.crv'
        
        #create otput array- - - - - - - - - - - - - - - - - - - - - - - - - - -

        #create to_insert
        #a list where each element is [interaction string, array]
        #here interaction string is formatted as in the CRV
        #array must also be formatted as in the CRV

        if interaction_string in ['preamp', 'poweramp', 'NON-NON-NON-Sig']:
            #must create both signal and idler array
        
            lines_between = 7
            
            #create signal curve from array
            signal_curve = np.zeros([len(curve), 7])
            idler_curve = np.zeros([len(curve), 7])
            for i in range(len(curve)):
                signal_curve[i, 0] = spitfire_output
                signal_curve[i, 1] = curve[i][0]
                signal_curve[i, 2] = 4
                signal_curve[i, 3] = (curve[i][1]/mcf['m0'][0]) + mcf['m0'][1]
                signal_curve[i, 4] = (curve[i][2]/mcf['m1'][0]) + mcf['m1'][1]
                signal_curve[i, 5] = (curve[i][3]/mcf['m2'][0]) + mcf['m2'][1]
                signal_curve[i, 6] = (curve[i][4]/mcf['m3'][0]) + mcf['m3'][1]
                
            #create idler curve
            idler_curve = np.zeros([len(curve), 7])
            for i in range(len(signal_curve)):
                idler_curve[i, 0] = signal_curve[i, 0]
                idler_curve[i, 1] = 1/((1/spitfire_output) - (1/signal_curve[i, 1]))
                idler_curve[i, 2] = signal_curve[i, 2]
                idler_curve[i, 3] = signal_curve[i, 3]
                idler_curve[i, 4] = signal_curve[i, 4]
                idler_curve[i, 5] = signal_curve[i, 5]
                idler_curve[i, 6] = signal_curve[i, 6]
            idler_curve = np.flipud(idler_curve)
                
            #construct to_insert
            to_insert = (['NON-NON-NON-Sig', signal_curve], ['NON-NON-NON-Idl', idler_curve])
                
            #construct image of tuning curve
            plt.close()
            fig_a1 = plt.subplot(211)
            fig_b1 = plt.subplot(212, sharex=fig_a1)
            fig_a2 = fig_a1.twinx()
            fig_b2 = fig_b1.twinx()
            fig_a1.plot(signal_curve[:, 1], signal_curve[:, 3], color = 'b', linewidth = 2.0)
            for tl in fig_a1.get_yticklabels(): tl.set_color('b')
            fig_a1.set_ylabel('c1 (deg)', color = 'b')
            fig_a2.plot(signal_curve[:, 1], signal_curve[:, 4], color = 'r', linewidth = 2.0)
            for tl in fig_a2.get_yticklabels(): tl.set_color('r')
            fig_a2.set_ylabel('d1 (mm)', color = 'r')            
            fig_b1.plot(signal_curve[:, 1], signal_curve[:, 5], color = 'b', linewidth = 2.0)
            for tl in fig_b1.get_yticklabels(): tl.set_color('b')
            fig_b1.set_ylabel('c2 (deg)', color = 'b')              
            fig_b2.plot(signal_curve[:, 1], signal_curve[:, 6], color = 'r', linewidth = 2.0)
            for tl in fig_b2.get_yticklabels(): tl.set_color('r')
            fig_b2.set_ylabel('d2 (deg)', color = 'r')
            fig_a1.grid()
            fig_b1.grid()
            fig_a1.set_xlim(signal_curve[:, 1].min(), signal_curve[:, 1].max())
            setp(fig_a1.get_xticklabels(), visible=False)
            fig_b1.set_xlabel('tunepoint (nm)')
            fig_a1.set_title('OPA{} Signal Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'NON-NON-NON-Idl':
            
            lines_between = 7
            
            print 'Idler crv creation not yet supported'
            
        elif interaction_string == 'NON-NON-SH-Idl':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 5]/mcf['m4'][0]) + mcf['m4'][1]
        
            #construct to_insert
            to_insert = [['NON-NON-SH-Idl', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 5]/mcf['m4'][0]) + mcf['m4'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Second Harmonic Idler Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'NON-SH-NON-Sig':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 6]/mcf['m5'][0]) + mcf['m5'][1]
        
            #construct to_insert
            to_insert = [['NON-SH-NON-Sig', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 6]/mcf['m5'][0]) + mcf['m5'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Second Harmonic Signal Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'NON-NON-SF-Idl':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 5]/mcf['m4'][0]) + mcf['m4'][1]
        
            #construct to_insert
            to_insert = [['NON-NON-SF-Idl', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 5]/mcf['m4'][0]) + mcf['m4'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Sum Frequency Idler Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'NON-NON-SF-Sig':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 5]/mcf['m4'][0]) + mcf['m4'][1]
        
            #construct to_insert
            to_insert = [['NON-NON-SF-Sig', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 5]/mcf['m4'][0]) + mcf['m4'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Sum Frequency Signal Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'NON-SH-SH-Idl':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 6]/mcf['m5'][0]) + mcf['m5'][1]
        
            #construct to_insert
            to_insert = [['NON-SH-SH-Idl', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 6]/mcf['m5'][0]) + mcf['m5'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Fourth Harmonic Idler Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'SH-SH-NON-Sig':
            
            lines_between = 10
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 7]/mcf['m6'][0]) + mcf['m6'][1]
        
            #construct to_insert
            to_insert = [['SH-SH-NON-Sig', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 7]/mcf['m6'][0]) + mcf['m6'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Fourth Harmonic Idler Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        elif interaction_string == 'DF1-NON-NON-Sig':
            
            lines_between = 9
            
            #import source colors
            old_crv_array = _crv('read', OPA, interaction_string = interaction_string)
            if source_colors == 'old':
                source_colors = old_crv_array[:, 13]
            else:
                source_colors = curve[:, 13]
            
            #construct crv_array
            crv_array = np.zeros([len(curve), 4])
            for i in range(len(curve)):
                crv_array[i, 0] = source_colors[i]
                crv_array[i, 1] = curve[i, 0]
                crv_array[i, 2] = 1
                crv_array[i, 3] = (curve[i, 7]/mcf['m6'][0]) + mcf['m6'][1]
        
            #construct to_insert
            to_insert = [['DF1-NON-NON-Sig', crv_array]]
            
            #construct image of tuning curve
            plt.close()
            plt.plot(old_crv_array[:, 0], (old_crv_array[:, 7]/mcf['m6'][0]) + mcf['m6'][1], color = 'k', linewidth = 1)
            plt.plot(crv_array[:, 1], crv_array[:, 3], color = 'k', linewidth = 2.5)
            plt.xlabel('tunepoint (nm)')
            plt.ylabel('mixer 1 (deg)')
            plt.grid()
            plt.title('OPA{} Difference Frequency Tuning Curve'.format(OPA))
            image_filepath = output_filepath.replace('.crv', '.png')
            plt.savefig(image_filepath, transparent = True)
            plt.close()
            
        else:
            
            print 'interaction_string {} not recognized in _crv'.format(interaction_string)

        #insert array(s) into file - - - - - - - - - - - - - - - - - - - - - - -

        for interaction in to_insert:            
            
            to_replace = interaction[0]
            input_points = interaction[1]
            
            #get relevant properties of curve in its old state
            num_points = []
            for i in range(len(crv_lines)):
                if 'NON' in crv_lines[i]:
                    num_points.append([i+lines_between, crv_lines[i].replace('\n', ''), int(crv_lines[i+lines_between])])

            #remove old points
            index = ''
            to_remove = ''
            for i in range(len(num_points)):
                if num_points[i][1] == to_replace:
                    index = num_points[i][0]
                    to_remove = num_points[i][2]
            if index == '':
                print 'interaction {0} not found in {1}'.format(to_replace, filepath)
                return
            del crv_lines[index:index+to_remove+1]
            
            #put in new points (gets done 'backwards')
            input_points = np.flipud(input_points)
            for tune_point in input_points:
                line = ''
                for value in tune_point:
                    #the number of motors must be an integer - so dumb
                    if value == 4:
                        value_as_string = '4'
                    elif value == 1:
                        value_as_string = '1'
                    else:
                        value_as_string = str(np.round(value, decimals=6))
                        portion_before_decimal = value_as_string.split('.')[0]
                        portion_after_decimal = value_as_string.split('.')[1].ljust(6, '0')
                        value_as_string = portion_before_decimal + '.' + portion_after_decimal
                    line = line + value_as_string + '\t'
                line = line + '\n'
                crv_lines.insert(index, line)
            crv_lines.insert(index, str(len(input_points)) + '\n') #length of new curve
        
        #create new file, write to it
        new_crv = open(output_filepath, 'w')
        for line in crv_lines:
            new_crv.write(line)
        new_crv.close()

    #return---------------------------------------------------------------------

    return output_filepath

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _ini_handler(ini_type,
                 interaction,
                 section,
                 option,
                 value = None):
                        
    #handles reading and writing to ini files with ConfigParser package      
    
    #get correct filepath based on ini_type-------------------------------------
    
    ini_filepath = ''
    if ini_type == 'COLORS':
        ini_filepath = COLORS_ini_filepath
    elif ini_type == 'OPA1':
        ini_filepath = OPA1_ini_filepath
    elif ini_type == 'OPA2':
        ini_filepath = OPA2_ini_filepath
    elif ini_type == 'OPA3':
        ini_filepath = OPA3_ini_filepath
    elif ini_type == 'topas_tune':
        ini_filepath = topas_tune_ini_filepath
    else:
        print 'ini_type not recognized in ini_handler'
        return
        
    #clean up filepath
    ini_filepath = ini_filepath.replace('\\', '\\\\')
        
    #check if real
    if not os.path.isfile(ini_filepath):
        print 'ini_filepath {} is not a file!'.format(ini_filepath)
        
    #do action------------------------------------------------------------------
    
    config = ConfigParser.SafeConfigParser()
    
    if interaction == 'read':
        config.read(ini_filepath) 
        return config.get(section, option)
    elif interaction == 'write':
        value = str(value) #ensure 'value' is a string
        config.read(ini_filepath)
        config.set(section, option, value) #update
        with open(ini_filepath, 'w') as configfile: 
            config.write(configfile) #save

COLORS_ini_filepath = _ini_handler('topas_tune', 'read', 'general', 'COLORS.ini filepath')
DATA_folderpath =  _ini_handler('topas_tune', 'read', 'general', 'DATA folderpath')
OPA1_ini_filepath = _ini_handler('COLORS', 'read', 'OPA', 'OPA1 device').replace('\"', '')
OPA2_ini_filepath = _ini_handler('COLORS', 'read', 'OPA', 'OPA2 device').replace('\"', '') 
OPA3_ini_filepath = _ini_handler('COLORS', 'read', 'OPA', 'OPA3 device').replace('\"', '')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def _load_fit(filepath):
    
    fit_cols =  {'num':       (0, 0.0, None, 'acquisition number'),
                 'w':         (1, 5.0, 'nm', r'$\mathrm{\bar\nu_1=\bar\nu_m (cm^{-1})}$'),
                 'm0':        (2, 0.0, 'us', r'm0'),
                 'm1':        (3, 0.0, 'us', r'm1'),
                 'm2':        (4, 0.0, 'us', r'm2'),
                 'm3':        (5, 0.0, 'us', r'm3'),
                 'm4':        (6, 0.0, 'us', r'm4'),
                 'm5':        (7, 0.0, 'us', r'm5'),
                 'm6':        (8, 0.0, 'us', r'm6'),
                 'center':    (9, 0.0, 'nm', r'center'),
                 'amplitude': (10, 0.0, 'a.u.', r'amplitude'),
                 'fwhm':      (11, 0.0, 'nm', r'fwhm'),
                 'gof':       (12, 0.0, '%', r'gof'),
                 'mismatch':  (13, 0.0, 'nm', r'mismatch')}

    #load raw array from fit file-----------------------------------------------

    raw_fit = np.loadtxt(filepath)
    raw_fit.T
    
    #construct fit array in topas_tune format-----------------------------------
    
    fit_array = np.empty([len(raw_fit), 20])
    fit_array[:] = np.nan
    for i in range(len(fit_array)):
        for j in range(13):
            fit_array[i][j] = raw_fit[i][j+1]
            
    #return---------------------------------------------------------------------
    
    return fit_array

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _load_dat(filepath, xvar, yvar, tune_test = False, zvar = 'mc'):
    
    dat_cols =  {'num':  (0, 0.0, None, 'acquisition number'),
                 'w1':   (1, 5.0, 'nm', r'$\mathrm{\bar\nu_1=\bar\nu_m (cm^{-1})}$'),
                 'w2':   (3, 5.0, 'nm', r'$\mathrm{\bar\nu_2=\bar\nu_{2^{\prime}} (cm^{-1})}$'),
                 'w3':   (5, 5.0, 'nm', r'$\mathrm{\bar\nu_3 (cm^{-1})}$'),
                 'wm':   (7, 1.0, 'nm', r'$\bar\nu_m / cm^{-1}$'),
                 'wa':   (8, 1.0, 'nm', r'array'),
                 'ai0':  (16, 0.0, 'V', 'Signal 0'),
                 'ai1':  (17, 0.0, 'V', 'Signal 1'),
                 'ai2':  (18, 0.0, 'V', 'Signal 2'),
                 'ai3':  (19, 0.0, 'V', 'Signal 3'),
                 'ai4':  (20, 0.0, 'V', 'Signal 4'),
                 'mc':   (21, 0.0, 'a.u.', 'array signal')}

    #load raw array-------------------------------------------------------------

    raw_dat = np.genfromtxt(filepath, dtype=np.float)
    dat = raw_dat.T
    
    #grid data------------------------------------------------------------------
    
    grid_factor = 1    
    
    #x
    xlis = dat[dat_cols[xvar][0]]
    xtol = dat_cols[xvar][1]
    xstd = []
    xs = []
    while len(xlis) > 0:
        set_val = xlis[0]
        xi_lis = [xi for xi in xlis if np.abs(set_val - xi) < xtol]
        xlis = [xi for xi in xlis if not np.abs(xi_lis[0] - xi) < xtol]
        xi_lis_average = sum(xi_lis) / len(xi_lis)
        xs.append(xi_lis_average)
        xstdi = sum(np.abs(xi_lis - xi_lis_average)) / len(xi_lis)
        xstd.append(xstdi)
    tol = sum(xstd) / len(xstd)
    tol = max(tol, 1e-1)
    xi = np.linspace(min(xs)+tol,max(xs)-tol, num=(len(xs) + (len(xs)-1)*(grid_factor-1)))    
    
    #y
    if tune_test:
        ylis = dat[dat_cols[yvar][0]] - dat[dat_cols[xvar][0]]
    else:
        ylis = dat[dat_cols[yvar][0]]
    ytol = dat_cols[yvar][1]
    ystd = []
    ys = []
    while len(ylis) > 0:
        set_val = ylis[0]
        yi_lis = [yi for yi in ylis if np.abs(set_val - yi) < ytol]
        ylis = [yi for yi in ylis if not np.abs(yi_lis[0] - yi) < ytol]
        yi_lis_average = sum(yi_lis) / len(yi_lis)
        ys.append(yi_lis_average)
        ystdi = sum(np.abs(yi_lis - yi_lis_average)) / len(yi_lis)
        ystd.append(ystdi)
    tol = sum(ystd) / len(ystd)
    tol = max(tol, 1e-1)
    yi = np.linspace(min(ys)+tol,max(ys)-tol, num=(len(ys) + (len(ys)-1)*(grid_factor-1)))
    
    #z
    xlis = dat[dat_cols[xvar][0]]
    if tune_test:
        ylis = dat[dat_cols[yvar][0]] - dat[dat_cols[xvar][0]]
    else:
        ylis = dat[dat_cols[yvar][0]]
    zlis = dat[dat_cols[zvar][0]]
    zi = scipy.interpolate.griddata((xlis, ylis), zlis, (xi[None,:], yi[:,None]), method='cubic', fill_value = 0.0)    
    
    #return---------------------------------------------------------------------
    
    return zi, xi, yi

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _get_motor_conversion_factors(OPA):
    
    #for any motor
    #  geo = ustep*((1/mcf[motor][0]) + mcf[motor][1])
    #  ustep = (geo - mcf[motor][1])*mcf[motor][0]
    
    OPA_str = 'OPA{}'.format(OPA)    
    motor_conversion_factors = {'m0': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 0'))),
                                'm1': (3200, float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 1'))),
                                'm2': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 2'))),
                                'm3': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 3'))),
                                'm4': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 4'))),
                                'm5': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 5'))),
                                'm6': (240 , float(_ini_handler(OPA_str, 'read', 'Motors logical parameters', 'Affix 6')))}
    
    return motor_conversion_factors     

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _say(text, informative_text = '', window_title = 'topas_tune'):

    text = str(text)
    informative_text = str(informative_text)
    
    msgBox = QMessageBox()
    msgBox.setWindowTitle(window_title)
    msgBox.setText(text);
    msgBox.setInformativeText(informative_text);  
    msgBox.isActiveWindow()
    msgBox.setFocusPolicy(Qt.StrongFocus)
    msgBox.exec_();
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _get_color(value):
    
    colormap_input = ['#0000FF', #blue
                      '#00FFFF', #aqua
                      '#00FF00', #green
                      '#FFFF00', #yellow
                      '#FF0000', #red
                      '#881111', #burgandy
                      '#0000FF', #blue
                      '#00FFFF', #aqua
                      '#00FF00', #green
                      '#FFFF00', #yellow
                      '#FF0000', #red
                      '#881111', #burgandy
                      '#0000FF', #blue
                      '#00FFFF', #aqua
                      '#00FF00', #green
                      '#FFFF00', #yellow
                      '#FF0000', #red
                      '#881111'] #burgandy
                      
    global rainbow_cmap
    
    rainbow_cmap = mplcolors.LinearSegmentedColormap.from_list('my colormap',colormap_input)

    return rainbow_cmap(value)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _gauss_residuals(p, y, x):

    A, mu, sigma = p
    
    err = y-np.abs(A)*np.exp(-(x-mu)**2 / (2*np.abs(sigma)**2))
    
    return np.abs(err)
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
def _exp_value(y, x):
    
    y_internal = np.ma.copy(y)
    x_internal = np.ma.copy(x)

    #get sum
    sum_y = 0.
    for i in range(len(y_internal)):
        if np.ma.getmask(y_internal[i]) == True:
            pass
        elif np.isnan(y_internal[i]):
            pass
        else:
            sum_y = sum_y + y_internal[i]
    
    #divide by sum
    for i in range(len(y_internal)):
        if np.ma.getmask(y_internal[i]) == True:
            pass
        elif np.isnan(y_internal[i]):
            pass
        else:
            y_internal[i] = y_internal[i] / sum_y

    #get expectation value    
    value = 0.
    for i in range(len(x_internal)):
        if np.ma.getmask(y_internal[i]) == True:
            pass
        elif np.isnan(y_internal[i]):
            pass
        else:
            value = value + y_internal[i]*x_internal[i]
    return value

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
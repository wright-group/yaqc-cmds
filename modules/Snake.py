"""
Created on Thu Sep 03 13:05:37 2015

@author: Nathan Neff-Mallon

Snaker: This function takes an np.array() of hardware points and checks several
likely shortest paths. It then returns the shortest path as a array of indicies
one dimention smaller than the grid (to allow looping over harware externally).
"""

import numpy as np
from matplotlib.cbook import flatten as flatten
# import project.project_globals as g

### Dummy hardware class for things that don't need the full proper class:

class HDW:

    def __init__(self,kind):
        assert type(kind) == str
        self.type = kind

### Peramiterizing Traveling Salesman Problem

def ps_to_mm(t):
    return t*.2998/2

def m_pos(curve, destination_in_wavenumbers):
    ''' Returns list of interators that defines order of points.'''
    return curve.get_motor_positions(destination_in_wavenumbers)

class Path:
    # Point_grid is the (n+1)D array containing the list of the points.
    # Each array dimention is a potential scan dimention.
    def __init__(self,point_grid,hws,units,start_pos=None):
        self.grid = np.array(point_grid)
        self.shape = self.grid.shape
        self.hws = hws
        self.units = units
        self.path = None
        self.length = 1000000000000000

        self.OPA_dictionary()

        #self.set_indicies()
        #self.calc_length() # finds total length
        return

    def __cmp__(self,other):
        return cmp(self.length,other.length)

    def OPA_dictionary(self):
        OPAc = []
        for o in self.hws:
            if o.type == 'Curve':
                OPAc.append(o)
            elif o.type == 'OPA':
                OPAc.append(o.curve)
            else:
                OPAc.append(None)

        color_dics = []
        for i in range(len(self.hws)):
            if OPAc[i]:
                color_dics.append(dict())
                colors = set(flatten(self.grid[:,:,hardwares.index(self.hws[i])]))
                for color in colors:
                    color_dics[-1][color] = m_pos(OPAc[i],color)
            else:
                color_dics.append(None)
        self.cd = color_dics

    def OPAd (self,h_index,color):
        if any(self.cd[h_index]):
            return np.array(self.cd[h_index][color])
        else:
            assert False

    def p_plot(self, dim = [0,2], path=None, l=None):
        if not any(path):
            if any(self.path):
                path = self.path
                l = self.length
            else:
                path = np.reshape(self.grid,[-1,self.grid.shape[-1]])

        #assert type(path) == np.ndarray
        #assert len(path.shape) == 2
        assert path.shape[0] == np.product(self.grid.shape[:-1])

        plt.figure()
        plt.scatter(path[:,dim[0]],path[:,dim[1]])
        plt.xlabel(self.hws[dim[0]].type + ' (' + self.units[dim[0]] + ')')
        plt.ylabel(self.hws[dim[1]].type + ' (' + self.units[dim[1]] + ')')
        if l:
            try:
                plt.title('Total Overhead time: ' + str(round(l,1)) + ' sec')
                plt.text(0,-1,"Min Estimated data time: .5*"+ str(len(path)) + "=" + str(.5*len(path))+' seconds')
                plt.text(0,-2,"Max Overhead percentage: " + str(round(100*(l)/(.5*len(path)+l),1)) + "%")
            except TypeError:
                plt.title("Given length: " + str(l))
                print "l not a number"
        else:
            plt.title('Length not given')

        plt.plot(list(path[:,dim[0]]),list(path[:,dim[1]]))

    def calc_length(self,path=None):
        if path == None: # No path specified
            path = np.reshape(self.grid,[-1,self.grid.shape[-1]])

        # Check that the path is a valid one

        assert type(path) == np.ndarray
        assert len(path.shape) == 2
        assert path.shape[0] == np.product(self.grid.shape[:-1])

        # Do the calculations!

        total_time_f = 0
        total_time_b = 0
        for i in range(len(path)-1):
            times_f = []
            times_b = []
            for h in range(len(self.hws)):
                times_f.append(self.time_cost(h,self.grid[tuple(path[i])][h],
                                                          self.grid[tuple(path[i+1])][h]))
                times_b.append(self.time_cost(h,self.grid[tuple(path[-i-1])][h],
                                                          self.grid[tuple(path[-i-2])][h]))
                total_time_f += max(times_f)
                total_time_b += max(times_b)
        if total_time_f < total_time_b:
            tt = total_time_f
            f = 1
        else:
            tt = total_time_b
            f = -1

        if tt < self.length:
            self.length = tt
            self.path = path[::f]

        return total_time_f,total_time_b


    def time_cost(self,hw_idx, start, stop):
        '''
        Function that determines the cost of moving a particular hardware a
        defined distance and direcction. This is the cost function used in the
        traveling salesman optimization. Returns time in seconds. If a hardware
        isn't listed, the difference in the start and stop values is returned.
        '''

        hw = self.hws[hw_idx]
        units = self.units[hw_idx]
        mono_cost = 1 # Number of seconds of extra time per high->low step
        # motor_cost = 0
        moter_speed = 0.2
        if round(start,2) == round(stop,2):
            return 0

        elif hw.type == 'Curve' or hw.type == 'OPA':
            m_start = self.OPAd(hw_idx,start)
            m_stop = self.OPAd(hw_idx,stop)
            return moter_speed*max([abs(m) for m in m_start-m_stop])+.1

        elif hw.type == 'Delay':
            if units == 'ps':
                return moter_speed*ps_to_mm(abs(stop-start))+.1
            elif units == 'mm':
                return moter_speed*abs(stop-start)+.1

        elif hw.type == "Motor":
            return moter_speed*abs(stop-start)+.1

        elif hw.type == 'Mono':
            if stop-start > 0:
                return .1
            elif stop-start < 0:
                return mono_cost
        else:
            return abs(start-stop)

class Snake:

    def __init__(self,input_grid,hardwares,units,start_point = None):
        self.grid = input_grid
        self.hws = hardwares
        self.units = units
        self.start_point = start_point
        try: assert len(self.grid.shape) == 3
        except: pass #Figure out how to handle more than 2D

        if any(start_point):
            try: assert len(start_point) == len(units)
            except: pass #Figure out how to encorporate starting/current position
        self.mypath = Path(self.grid,self.hws,self.units,self.start_point)

    def best(self):
        ''' Finds and returns the best guess for the fasted scan'''

        self.costs = []
        for p in self._linear1_():
            p = np.array(p)
            self.costs.append(self.mypath.calc_length(p))
        for p in self._linear2_():
            p = np.array(p)
            self.costs.append(self.mypath.calc_length(p))
        for p in self._Diagonal_():
            p = np.array(p)
            self.costs.append(self.mypath.calc_length(p))

        return self.mypath.path,self.mypath.length


    def plot_best(self):
        self.mypath.p_plot([0,1])
        return


    def _linear1_(self):
        m = self.grid.shape[0]
        n = self.grid.shape[1]
        paths = [[] for i in range(4)]
        '''### List Index and Snake styles, 1st Axis'''
        for idx in np.ndindex(*[m,n]):
            i,j = idx
            paths[0].append(idx)
            paths[1].append((i,n-j-1))
            if i%2 == 0:
                paths[2].append(idx)
                paths[3].append((i,n-j-1))
            else:
                paths[2].append((i,n-j-1))
                paths[3].append(idx)
        return paths


    def _linear2_(self):
        '''List Index and Snake styles, 2nd Axis'''
        m = self.grid.shape[0]
        n = self.grid.shape[1]
        paths = [[] for i in range(4)]
        for idx in np.ndindex(*[n,m]):
            i,j = idx
            paths[0].append((j,i))
            paths[1].append((m-j-1,i))
            if i%2 == 0:
                paths[2].append((j,i))
                paths[3].append((m-j-1,i))
            else:
                paths[2].append((m-j-1,i))
                paths[3].append((j,i))
        return paths

    def _Diagonal_(self):
        m = self.grid.shape[0]
        n = self.grid.shape[1]
        paths = [[] for i in range(8)]
        # Index array for diagonal checks
        idx = np.array([[(i,j) for j in range(m)] for i in range(n)])
        idx_f = idx[::-1]
        # TL-BR is 8-11, TR-BL is 12-15
        tpd = lambda x,i: np.transpose(x.diagonal(i,0,1))
        for i in range(1-n,m):
            paths[0].append(tpd(idx,i))
            paths[1].append(tpd(idx,i)[::-1])
            paths[4].append(tpd(idx_f,i))
            paths[5].append(tpd(idx_f,i)[::-1])
            if i%2 == 0:
                paths[2].append(tpd(idx,i)[::-1])
                paths[3].append(tpd(idx,i))
                paths[6].append(tpd(idx_f,i)[::-1])
                paths[7].append(tpd(idx_f,i))
            else:
                paths[2].append(tpd(idx,i))
                paths[3].append(tpd(idx,i)[::-1])
                paths[6].append(tpd(idx_f,i))
                paths[7].append(tpd(idx_f,i)[::-1])

        # Cleaning up the diagonal slices

        for p in range(8):
            k = np.array([],dtype=int)
            for arr in paths[p]:
                k = np.append(k,arr)
            paths[p] = np.array([arr[::-1] for arr in k.reshape([-1,2])])

        return paths


### Testing ##############################################
if True:
    #g.offline.get_saved()

    if True: #g.offline.read():
        # import
        a = 'C:\Users\Nathan\Documents\GitHub\PyCMDS\opas\pico\OPA1 curves\OPA1 - 2015.08.27 17_14_47.curve'
        b = 'C:\Users\Nathan\Documents\GitHub\PyCMDS\opas\pico\OPA2 curves\OPA2 - 2015.08.27 17_16_16.curve'
        c = 'C:\Users\Nathan\Documents\GitHub\PyCMDS\opas\pico\OPA3 curves\OPA3 - 2015.08.27 17_17_49.curve'

        # It might be faster (computer-wise) to translate all the opa points
        # into moter points only once.

        import project.classes as pc
        import matplotlib.pyplot as plt
        from opas.pico.pico_opa import Curve

        OPA1 = Curve(a)
        OPA2 = Curve(b)
        OPA3 = Curve(c)


        MicroHR = HDW('Mono')
        D1 = HDW('Delay')
        D2 = HDW('Delay')
        D3 = None

    if True:
        ### Scan setup ##################################################
        hardwares = [OPA1,OPA2,MicroHR]
        u = ['wn','wn','wn']
        axis_pts = [(1600-1250)/5,(1600-1500)/5]
        OPA1_start = pc.Number(initial_value=1250, units=u[0])
        OPA1_stop = pc.Number(initial_value=1600, units=u[0])
        OPA1_pos = np.linspace(OPA1_start.read(), OPA1_stop.read(), axis_pts[0])

        OPA2_start = pc.Number(initial_value=1250, units=u[2])
        OPA2_stop = pc.Number(initial_value=1400, units=u[2])
        OPA2_pos = np.linspace(OPA2_start.read(), OPA2_stop.read(), axis_pts[1])

        axis1 = OPA1_pos
        axis2 = OPA2_pos

        grid = np.transpose(np.array(np.meshgrid(axis1,axis2)))
        new_grid = np.zeros(np.append(axis_pts,len(hardwares)))

        for i in range(axis_pts[0]):
            for j in range(axis_pts[1]):
                try:
                    new_grid[i,j] = np.insert(grid[i][j],2,12500+grid[i][j][0]-grid[i][j][1])
                except IndexError:
                    print "Index Error in scan setup"

    ### Using the Snake class #################################################
    answer = Snake(new_grid,hardwares,u)
    answer.best()
    answer.plot_best()


    ### Initial SNAKE code ####################################################
    # The test code used to develop the snake class lives here, in eternal death
    '''
    if False:


        assert len(new_grid.shape) == 3 # only 2D scans for now

        input_grid = new_grid


        ### 2-D Paths ##########################################
        m = input_grid.shape[0]
        n = input_grid.shape[1]
        paths = [[] for i in range(16)]
        ### List Index and Snake styles, 1st Axis
        for idx in np.ndindex(*[m,n]):
            i,j = idx
            paths[0].append(idx)
            paths[1].append((i,n-j-1))
            if i%2 == 0:
                paths[2].append(idx)
                paths[3].append((i,n-j-1))
            else:
                paths[2].append((i,n-j-1))
                paths[3].append(idx)
        ### List Index and Snake styles, 2nd Axis
        for idx in np.ndindex(*[n,m]):
            i,j = idx
            paths[4].append((j,i))
            paths[5].append((m-j-1,i))
            if i%2 == 0:
                paths[6].append((j,i))
                paths[7].append((m-j-1,i))
            else:
                paths[6].append((m-j-1,i))
                paths[7].append((j,i))

        ### Diagonals #############################################################

        # Index array for diagonal checks
        idx = np.array([[(i,j) for j in range(m)] for i in range(n)])
        idx_f = idx[::-1]
        # TL-BR is 8-11, TR-BL is 12-15
        tpd = lambda x,i: np.transpose(x.diagonal(i,0,1))
        for i in range(1-n,m):
            paths[8].append(tpd(idx,i))
            paths[9].append(tpd(idx,i)[::-1])
            paths[12].append(tpd(idx_f,i))
            paths[13].append(tpd(idx_f,i)[::-1])
            if i%2 == 0:
                paths[10].append(tpd(idx,i)[::-1])
                paths[11].append(tpd(idx,i))
                paths[14].append(tpd(idx_f,i)[::-1])
                paths[15].append(tpd(idx_f,i))
            else:
                paths[10].append(tpd(idx,i))
                paths[11].append(tpd(idx,i)[::-1])
                paths[14].append(tpd(idx_f,i))
                paths[15].append(tpd(idx_f,i)[::-1])

        # Cleaning up the diagonal slices

        for p in range(8,16):
            k = np.array([],dtype=int)
            for arr in paths[p]:
                k = np.append(k,arr)
            paths[p] = np.array([arr[::-1] for arr in k.reshape([-1,2])])


        ### Plotting Paths (optional) ################################

        for p in paths:
            p = np.array(p)
            plt.figure()
            plt.scatter(p[:,0],p[:,1])
            plt.plot(p[:,0],p[:,1])

        ### Using the Path object #################################################
        mypath = Path(input_grid,hardwares,u)
        costs = []
        for p in paths:
            p = np.array(p)
            costs.append(mypath.calc_length(p))
        mypath.p_plot([0,1])
        '''
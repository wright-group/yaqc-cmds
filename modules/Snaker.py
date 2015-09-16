# Copyright 2010-2013 Google
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This has been heavily edited and ammended by Nathan Neff-Mallon
# As of this release, details about or-tools can be found at
#
#    https://developers.google.com/optimization/?hl=en
#
# and the example typ.py can be found in the or-tools examples, avalible
# as a link from the or-tools installation page
#
#    https://developers.google.com/optimization/docs/installing
#
#

"""
Created on Thu Sep 03 13:05:37 2015

@author: Nathan Neff-Mallon

Snaker: This function takes an arbitrary np.array of hardware points and
finds the shortest possible path through those points, starting at the
current hardware position. A large part of the code is taken from tsp.py

Version 0.1: Default optimization settings are used. More details on options
can be found at
https://developers.google.com/optimization/routing/tsp?hl=en#options
"""
import WrightTools.units.converter as Convert

import numpy as np

import gflags
from ortools.constraint_solver import pywrapcp

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('tsp_use_random_matrix', False,
                      'Use random cost matrix.')
gflags.DEFINE_integer('tsp_random_forbidden_connections', 0,
                      'Number of random forbidden connections.')
gflags.DEFINE_integer('tsp_random_seed', 0, 'Random seed.')
gflags.DEFINE_boolean('light_propagation', False, 'Use light propagation')

### Peramiterizing Traveling Salesman Problem

def ps_to_mm(t):
    return t*.2998/2

def m_pos(opa, destination_in_wavenumbers):
    ''' Returns list of interators that defines order of points.'''
    return opa.curve.new_motor_positions(destination_in_wavenumbers)

def time_cost(hw, start, stop, units):
    '''
    Function that determines the cost of moving a particular hardware a
    defined distance and direcction. This is the cost function used in the
    traveling salesman optimization. Returns time in seconds. If a hardware
    isn't listed, the difference in the start and stop values is returned.
    '''
    mono_cost = 1 # Number of seconds of extra time per high->low step
    # motor_cost = 0
    moter_speed = 0.2
    if start == stop:
        return 0

    elif hw.type == 'OPA':
       m_start = np.array(m_pos(hw,Convert(start,units,'wn')))
       m_stop = np.array(m_pos(hw,Convert(stop,units,'wn')))
       return moter_speed*max([abs(m) for m in m_start-m_stop])+.1

    elif hw.type == 'Delay':
        if units == 'ps':
            return moter_speed*ps_to_mm(abs(stop-start))+.1
        elif units == 'mm':
            return moter_speed*abs(stop-start)+.1

    elif hw.type == 'Mono':
        if stop-start > 0:
            return .1
        elif stop-start < 0:
            return mono_cost
    else:
        return abs(start-stop)

def snaker(point_grid, hws, units):
    '''
    Snaker Function: This takes a list of the experimental points
    (pos0, pos1, pos2, ..., pos_n) in a scan, the corresponding hardwares
    (hw0, hw1, hw2, ..., hw_n) and their units and finds the shortest path
    (in time) along those ponits, starting from the current position.

    What it returns is still tbd, but probably it will be a list of the
    indicies of the scan points. It could also return a 1-D list of the scan
    points themselves, in order.
    '''

    current_position = [hw.get_position() for hw in hws]

    idx = np.ndindex(*np.delete(point_grid.shape,-1))
    # Make the list of points a list of experimental points
    points = np.reshape(point_grid,[-1,point_grid.shape[-1]])
    # Start with the current position
    points = np.insert(points,0,current_position)
    idx = np.insert(idx,0,(-1,-1,-1))

    def Distance(from_idx, to_idx):
        ''' The cost function. Ortools requires that this function take only
        the two indicies as arguments, so this function must be defined after
        hws and units are defined and the points list is set up.

        The cost to get back to 0 is constant and large so the solutions won't
        be influenced by the default of returning to the starting point.
        '''
        if to_idx == 0:
            return 300
        else:
            return max([time_cost(hw[x],points[from_idx][x],points[to_idx][x],units[x]) for x in len(hws)])

    gflags.DEFINE_integer('tsp_size', points.size,
                      'Size of Traveling Salesman Problem instance.')

    # Set a global parameter.
    param = pywrapcp.RoutingParameters()
    param.use_light_propagation = FLAGS.light_propagation
    pywrapcp.RoutingModel.SetGlobalParameters(param)

    # TSP of size FLAGS.tsp_size
    # Second argument = 1 to build a single tour (it's a TSP).
    # Nodes are indexed from 0 to FLAGS_tsp_size - 1, by default the start of
    # the route is node 0.
    routing = pywrapcp.RoutingModel(FLAGS.tsp_size, 1)

    parameters = pywrapcp.RoutingSearchParameters()
    # Setting first solution heuristic (cheapest addition).
    parameters.first_solution = 'PathCheapestArc'
    # Disabling Large Neighborhood Search, comment out to activate it.
    parameters.no_lns = True
    parameters.no_tsp = False

    # Setting the cost function.
    # Put a callback to the distance accessor here. The callback takes two
    # arguments (the from and to node inidices) and returns the distance between
    # these nodes.

    routing.SetArcCostEvaluatorOfAllVehicles(Distance)

      # Solve, returns a solution if any.

    assignment = routing.SolveWithParameters(parameters, None)
    if assignment:
      # Solution cost.
      scan_time = assignment.ObjectiveValue()-300
      # Inspect solution.
      # Only one route here; otherwise iterate from 0 to routing.vehicles() - 1
      route_number = 0
      node = assignment.Value(routing.NextVar(routing.Start(route_number)))
      route = []
      ordered_idx = []
      ordered_points = []
      while not routing.IsEnd(node):
          route = route.append(node)
          ordered_idx = ordered_idx.append(idx[node])
          ordered_points = ordered_points.append(points[node])
          node = assignment.Value(routing.NextVar(node))
    else:
        print('No solution found.')

    ordered_idx = np.delete(ordered_idx,0)
    ordered_points = np.delete(ordered_points,0)

    return (ordered_idx,ordered_points),scan_time
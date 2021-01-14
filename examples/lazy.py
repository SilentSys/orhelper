import orhelper
import math
import numpy as np
from scipy.optimize import fmin
from matplotlib import pyplot as plt

with orhelper.OpenRocketInstance('OpenRocket-test.jar'):
    orh = orhelper.Helper()
    
    # Load document, run simulation and get data and events
    doc = orh.load_doc('simple.ork')
    sim = doc.getSimulation(0)
    
    # Define some functions for simulating and optimizing
    def simulate_at_angle(ang, sim):
        sim.getOptions().setLaunchRodAngle(math.radians(ang))
        orh.run_simulation(sim)
        return orh.get_timeseries(sim, ['Altitude', 'Position upwind'] )
    
    def to_min(ang, sim):
        data = simulate_at_angle(ang, sim)
        half_len = len(data['Altitude'])/2.0  # Don't want the launch
        min_upwind_index = np.abs(data['Altitude'][half_len:]).argmin()
        min_upwind_position = data['Position upwind'][half_len:][min_upwind_index]
        return np.abs(min_upwind_position)
    
    # Find and include the maximum upwind distance
    optimal = fmin( to_min, [40], args=[sim] )
    
    angles = np.linspace(0, 30.0, num=10)
    angles = np.append(angles, optimal)
    angles.sort()
    
    # Calculate all the curves for plotting
    data_runs = []
    for ang in angles:
        data_dict = simulate_at_angle(ang, sim)
        data_dict['Angle'] = ang
        data_runs.append(data_dict)
    
    # Do the plotting
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    for data in data_runs:
        ax1.plot(data['Position upwind'], data['Altitude'], 
                label='%3.1f$^\circ$' % data['Angle'], 
                linestyle = '-' if data['Angle'] == optimal else '--')
        
    ax1.legend()
    ax1.set_xlabel('Position upwind (m)')
    ax1.set_ylabel('Altitude (m)')
    ax1.set_title('Optimal launch rod angle for easy recovery')
    ax1.grid(True)
    plt.show()

import numpy as np
from matplotlib import pyplot as plt

import orhelper

with orhelper.OpenRocketInstance():
    orh = orhelper.Helper()
    
    # Load document, run simulation and get data and events
    
    doc = orh.load_doc('estes_gnome.ork')
    sim = doc.getSimulation(0)
    orh.run_simulation(sim)
    data = orh.get_timeseries(sim, ['Time', 'Altitude', 'Vertical velocity'] )
    events = orh.get_events(sim)
    
    # Make a custom plot the simulation
    
    events_to_annotate = ['Motor burnout', 'Apogee', 'Launch rod clearance']
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()
    
    ax1.plot(data['Time'], data['Altitude'], 'b-')
    ax2.plot(data['Time'], data['Vertical velocity'], 'r-')    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Altitude (m)', color='b')
    ax2.set_ylabel('Vertical Velocity (m/s)', color='r')
    change_color = lambda ax, col : [x.set_color(col) for x in ax.get_yticklabels()]
    change_color(ax1, 'b')
    change_color(ax2, 'r')
        
    index_at = lambda t : (np.abs(data['Time']-t)).argmin()
    for name, time in events.items():
        if not name in events_to_annotate: continue
        ax1.annotate(name, xy=(time, data['Altitude'][index_at(time)] ), xycoords='data',
                    xytext=(20, 0), textcoords='offset points',
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3")
                    )
    
    ax1.grid(True)
    plt.show()

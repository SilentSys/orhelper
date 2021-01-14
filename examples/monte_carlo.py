import numpy as np
from jpype import *
import numpy as np
import orhelper
from random import gauss
import math
        
class LandingPoints(list):
    "A list of landing points with ability to run simulations and populate itself"    
    
    def add_simulations(self, num):
        with orhelper.OpenRocketInstance('OpenRocket-test.jar', log_level='ERROR'):
            
            # Load the document and get simulation
            orh = orhelper.Helper()
            doc = orh.load_doc('simple.ork')
            sim = doc.getSimulation(0)
            
            # Randomize various parameters
            opts = sim.getOptions()
            rocket = opts.getRocket()
            
            # Run num simulations and add to self
            for p in range(num):
                print 'Running simulation ', p
                
                opts.setLaunchRodAngle(math.radians( gauss(45, 5) ))    # 45 +- 5 deg in direction
                opts.setLaunchRodDirection(math.radians( gauss(0, 5) )) # 0 +- 5 deg in direction
                opts.setWindSpeedAverage( gauss(15, 5) )                # 15 +- 5 m/s in wind
                for component_name in ('Nose cone', 'Body tube'):       # 5% in the mass of various components
                    component = orh.get_component_named( rocket, component_name )
                    mass = component.getMass()
                    component.setMassOverridden(True)
                    component.setOverrideMass( mass * gauss(1.0, 0.05) )
                
                airstarter = AirStart( gauss(1000, 50) ) # simulation listener to drop from 1000 m +- 50        
                lp = LandingPoint()
                orh.run_simulation(sim, listeners=(airstarter, lp) )
                self.append( lp )
    
    def print_stats(self):
        
        ranges = [p.range for p in self]
        bearings = [p.bearing for p in self]
        
        print 'Rocket landing zone %3.2f m +- %3.2f m bearing %3.2f deg +- %3.4f deg from launch site. Based on %i simulations.' % \
            (np.mean(ranges), np.std(ranges), np.degrees(np.mean(bearings)), np.degrees(np.std(bearings)), len(self) )

class LandingPoint(orhelper.AbstractSimulationListener):

    def endSimulation(self, status, simulation_exception):
        
        worldpos = status.getRocketWorldPosition()
        conditions = status.getSimulationConditions()
        launchpos = conditions.getLaunchSite()
        geodetic_computation = conditions.getGeodeticComputation()
        
        self.range = geodetic_computation.range(launchpos, worldpos)
        self.bearing = geodetic_computation.bearing(launchpos, worldpos)
        
class AirStart(orhelper.AbstractSimulationListener):
    
    def __init__(self, altitude) :
        self.start_altitude = altitude
    
    def startSimulation(self, status) :        
        position = status.getRocketPosition()
        position = position.add(0.0, 0.0, self.start_altitude)
        status.setRocketPosition(position)

if __name__ == '__main__':
    points = LandingPoints()
    points.add_simulations(20)
    points.print_stats()

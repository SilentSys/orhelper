import sys, traceback
import jpype
import numpy as np

import os
os.environ['CLASSPATH'] = "/home/jbbowen/Desktop/OpenRocket Stuff/OpenRocket-15.03.jar"

import jnius_config
jnius_config.add_options('-ea')
jnius_config.set_classpath('.', '/home/jbbowen/Desktop/OpenRocket Stuff/OpenRocket-15.03.jar')
import jnius
from jnius import autoclass

class OpenRocketInstance(object):
    """ When instantiated, this class starts up a new openrocket instance.
        This class is designed to be called using the 'with' construct. This
        will ensure that no matter what happens within that context, the 
        JVM will always be shutdown.
    """
    
    def __init__(self, jar_path, log_level='ERROR'):
        """ jar_path is the full path of the OpenRocket .jar file to use
            log_level can be either ERROR, WARN, USER, INFO, DEBUG or VBOSE
        """
            
        jpype.startJVM(jpype.getDefaultJVMPath(), '-ea', "-Djava.class.path=%s" % jar_path)
        orp = jpype.JPackage("net").sf.openrocket
        startup = jpype.JClass('net.sf.openrocket.startup.Application')
        startup.initializeLogging()
        log_level = orp.logging.LogLevel.fromString(log_level, orp.logging.LogLevel.ERROR)
        orp.startup.Application.setLogOutputLevel(log_level)
        orp.startup.Startup.initializeL10n()
        orp.startup.Startup2.loadMotor()
    
    def __enter__(self):
        print 'Starting openrocket'
             
    def __exit__(self, ty, value, tb):
        
        jpype.shutdownJVM()
        
        if not ty is None:
            print 'Exception while calling openrocket'
            print 'Exception info : ', ty, value, tb
            print 'Traceback : '
            traceback.print_exception(ty, value, tb)
        
class Helper(object):
    """ This class contains a variety of useful helper functions and wrapper for using
        openrocket via jpype. These are intended to take care of some of the more
        cumbersome aspects of calling methods, or provide more 'pythonic' data structures
        for general use.
    """
    
    def __init__(self):
        self.orp = jpype.JPackage("net").sf.openrocket

    def load_doc(self, or_filename):
        """ Loads a .ork file and returns the corresponding openrocket document """
        
        or_java_file = jpype.java.io.File(or_filename)
        loader = self.orp.file.GeneralRocketLoader()
        doc = loader.load(or_java_file)
        return doc
            
    def run_simulation(self, sim, listeners=None ):
        """ This is a wrapper to the Simulation.simulate() for running a simulation
            The optional listeners parameter is a sequence of objects which extend orh.AbstractSimulationListener.
        """
                
        if listeners == None:
            # this method takes in a vararg of SimulationListeners, which is just a fancy way of passing in an array, so 
            # we have to pass in an array of length 0 ..
            listener_array = jpype.JArray(self.orp.simulation.listeners.AbstractSimulationListener, 1)(0)
        else:
            listener_array = [jpype.JProxy( ( self.orp.simulation.listeners.SimulationListener,
                                        self.orp.simulation.listeners.SimulationEventListener,
                                        self.orp.simulation.listeners.SimulationComputationListener
                                        ) , inst=c) for c in listeners]

        sim.getOptions().randomizeSeed() # Need to do this otherwise exact same numbers will be generated for each identical run
        sim.simulate( listener_array )

    def get_timeseries(self, simulation, variables, branch_number = 0):
        """Gets a dictionary of timeseries data (as numpy arrays) from a simulation given variable names.
           First parameter is an openrocket simulation object.
           Second parameter is a sequence of strings representing the variable names according to default locale.
        """
        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:            
            try:
                data_type = filter( lambda x : x.getName() == unicode(v) , branch.getTypes() ) [0]
            except:
                continue
            
            #openrocket returns an array of Double objects rather than primatives to have to get the data out this way
            output[v] = np.array( [i.value for i in branch.get(data_type)] ) 
        
        return output

    def get_final_values(self, simulation, variables, branch_number = 0):
        
        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:            
            try:
                data_type = filter( lambda x : x.getName() == unicode(v) , branch.getTypes() ) [0]
            except:
                continue
            
            #openrocket returns an array of Double objects rather than primatives to have to get the data out this way
            output[v] = branch.get(data_type)[-1].value
        
        return output

    def get_events(self, simulation):
        """Returns a dictionary of all the flight events in a given simulation.
           Key is the name of the event and value is the time of the event.
        """
        branch = simulation.getSimulatedData().getBranch(0)
        
        output = dict()
        for ev in branch.getEvents():
            output[str(ev.getType().toString())] = ev.getTime()
        
        return output

    def get_component_named(self, root, name):
        """ Finds and returns the first rocket component with the given name.
            Requires a root RocketComponent, usually this will be a RocketComponent.rocket instance.
            Raises a ValueError if no component found.
        """
        
        for component in JIterator(root):
            if component.getName() == name:
                return component
        raise ValueError(root.toString()+' has no component named '+name)

class JIterator(object):
    "This class is a wrapper for java iterators to allow them to be used as python iterators"
    
    def __init__(self, jit):
        "Give this any java object which implements iterable"
        self.jit = jit.iterator(True)
    
    def __iter__(self):
        return self
    
    def next(self):
        if not self.jit.hasNext():
            raise StopIteration()
        else:
            return self.jit.next()

class AbstractSimulationListener(object):
    """ This is a python implementation of openrocket.simulation.AbstractSimulationListener.
        Subclasses of this are suitable for passing to helper.run_simulation.
    """
    
    def __str__(self):
        return "'" + 'Python simulation listener proxy : ' + str(self.__class__.__name__) + "'"
    
    def toString(self):
        return str(self)
    
    # SimulationListener
    def startSimulation(self, status):
        pass
    
    def endSimulation(self, status, simulation_exception):
        pass
    
    def preStep(self, status):
        return True
        
    def postStep(self, status):
        pass
    
    def isSystemListener(self):
        return False
    
    # SimulationEventListener
    def addFlightEvent(self, status, flight_event):
        return True
    
    def handleFlightEvent(self, status, flight_event):
        return True
    
    def motorIgnition(self, status, motor_id, motor_mount, motor_instance):
        return True
        
    def recoveryDeviceDeployment(self, status, recovery_device):
        return True

    # SimulationComputationListener
    def preAccelerationCalculation(self, status):
        return None
    
    def preAerodynamicCalculation(self, status):
        return None
    
    def preAtmosphericModel(self, status):
        return None
    
    def preFlightConditions(self, status):
        return None
    
    def preGravityModel(self, status):
        return float('nan')
    
    def preMassCalculation(self, status):
        return None
        
    def preSimpleThrustCalculation(self, status):
        return float('nan')
        
    def preWindModel(self, status):
        return None
        
    def postAccelerationCalculation(self, status, acceleration_data):
        return None
        
    def postAerodynamicCalculation(self, status, aerodynamic_forces):
        return None
        
    def postAtmosphericModel(self, status, atmospheric_conditions):
        return None
    
    def postFlightConditions(self, status, flight_conditions):
        return None
    
    def postGravityModel(self, status, gravity):
        return float('nan')
    
    def postMassCalculation(self, status, mass_data):
        return None
    
    def postSimpleThrustCalculation(self, status, thrust):
        return float('nan')
    
    def postWindModel(self, status, wind):
        return None
    

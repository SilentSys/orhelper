import os
import logging
from copy import copy
from typing import Union, List, Iterable, Dict

import jpype
import jpype.imports
import numpy as np

from ._enums import *

logger = logging.getLogger(__name__)

CLASSPATH = os.environ.get("CLASSPATH", "OpenRocket-15.03.jar")

__all__ = [
    'OpenRocketInstance',
    'AbstractSimulationListener',
    'Helper',
    'JIterator',
]

class OpenRocketInstance:
    """ This class is designed to be called using the 'with' construct. This
        will ensure that no matter what happens within that context, the 
        JVM will always be shutdown.
    """

    def __init__(self, jar_path: str = CLASSPATH, log_level: Union[OrLogLevel, str] = OrLogLevel.ERROR):
        """ jar_path is the full path of the OpenRocket .jar file to use
            log_level can be either OFF, ERROR, WARN, INFO, DEBUG, TRACE and ALL
        """
        self.openrocket = None
        self.started = False

        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"Jar file {os.path.abspath(jar_path)} does not exist")
        self.jar_path = jar_path

        if isinstance(log_level, str):
            self.or_log_level = OrLogLevel[log_level]
        else:
            self.or_log_level = log_level

    def __enter__(self):
        jvm_path = jpype.getDefaultJVMPath()

        logger.info(f"Starting JVM from {jvm_path} CLASSPATH={self.jar_path}")

        jpype.startJVM(jvm_path, "-ea", f"-Djava.class.path={self.jar_path}")

        # ----- Java imports -----
        self.openrocket = jpype.JPackage("net").sf.openrocket
        guice = jpype.JPackage("com").google.inject.Guice
        LoggerFactory = jpype.JPackage("org").slf4j.LoggerFactory
        Logger = jpype.JPackage("ch").qos.logback.classic.Logger
        # -----

        # Effectively a minimally viable translation of openrocket.startup.SwingStartup
        gui_module = self.openrocket.startup.GuiModule()
        plugin_module = self.openrocket.plugin.PluginModule()

        injector = guice.createInjector(gui_module, plugin_module)

        app = self.openrocket.startup.Application
        app.setInjector(injector)

        gui_module.startLoader()

        # Ensure that loaders are done loading before continuing
        # Without this there seems to be a race condition bug that leads to the whole thing freezing
        preset_loader = _get_private_field(gui_module, "presetLoader")
        preset_loader.blockUntilLoaded()
        motor_loader = _get_private_field(gui_module, "motorLoader")
        motor_loader.blockUntilLoaded()

        or_logger = LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME)
        or_logger.setLevel(self._translate_log_level())

        self.started = True

        return self

    def __exit__(self, ex, value, tb):

        # Dispose any open windows (usually just a loading screen) which can prevent the JVM from shutting down
        for window in jpype.java.awt.Window.getWindows():
            window.dispose()

        jpype.shutdownJVM()
        logger.info("JVM shut down")
        self.started = False

        if ex is not None:
            logger.exception("Exception while calling OpenRocket", exc_info=(ex, value, tb))

    def _translate_log_level(self):
        # ----- Java imports -----
        Level = jpype.JPackage("ch").qos.logback.classic.Level
        # -----

        return getattr(Level, self.or_log_level.name)


class AbstractSimulationListener:
    """ This is a python implementation of openrocket.simulation.listeners.AbstractSimulationListener.
        Subclasses of this are suitable for passing to helper.run_simulation.
    """

    def __str__(self):
        return (
                "'"
                + "Python simulation listener proxy : "
                + str(self.__class__.__name__)
                + "'"
        )

    def toString(self):
        return str(self)

    # SimulationListener
    def startSimulation(self, status) -> None:
        pass

    def endSimulation(self, status, simulation_exception) -> None:
        pass

    def preStep(self, status) -> bool:
        return True

    def postStep(self, status) -> None:
        pass

    def isSystemListener(self) -> bool:
        return False

    # SimulationEventListener
    def addFlightEvent(self, status, flight_event) -> bool:
        return True

    def handleFlightEvent(self, status, flight_event) -> bool:
        return True

    def motorIgnition(self, status, motor_id, motor_mount, motor_instance) -> bool:
        return True

    def recoveryDeviceDeployment(self, status, recovery_device) -> bool:
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
        return float("nan")

    def preMassCalculation(self, status):
        return None

    def preSimpleThrustCalculation(self, status):
        return float("nan")

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
        return float("nan")

    def postMassCalculation(self, status, mass_data):
        return None

    def postSimpleThrustCalculation(self, status, thrust):
        return float("nan")

    def postWindModel(self, status, wind):
        return None

    def clone(self):
        return jpype.JProxy((
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationListener,
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationEventListener,
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationComputationListener,
            jpype.java.lang.Cloneable,),
            inst=copy(self))


class Helper:
    """ This class contains a variety of useful helper functions and wrapper for using
        openrocket via jpype. These are intended to take care of some of the more
        cumbersome aspects of calling methods, or provide more 'pythonic' data structures
        for general use.
    """

    def __init__(self, open_rocket_instance: OpenRocketInstance):
        if not open_rocket_instance.started:
            raise Exception("OpenRocketInstance not yet started")

        self.openrocket = open_rocket_instance.openrocket

    def load_doc(self, or_filename):
        """ Loads a .ork file and returns the corresponding openrocket document """

        or_java_file = jpype.java.io.File(or_filename)
        loader = self.openrocket.file.GeneralRocketLoader(or_java_file)
        doc = loader.load()
        return doc

    def save_doc(self, or_filename, doc):
        """ Saves an openrocket document to a .ork file """
        
        or_java_file = jpype.java.io.File(or_filename)
        saver = self.openrocket.file.GeneralRocketSaver()
        saver.save(or_java_file, doc)

    def run_simulation(self, sim, listeners: List[AbstractSimulationListener] = None):
        """ This is a wrapper to the Simulation.simulate() for running a simulation
            The optional listeners parameter is a sequence of objects which extend orh.AbstractSimulationListener.
        """

        if listeners is None:
            # this method takes in a vararg of SimulationListeners, which is just a fancy way of passing in an array, so
            # we have to pass in an array of length 0 ..
            listener_array = jpype.JArray(
                self.openrocket.simulation.listeners.AbstractSimulationListener, 1
            )(0)
        else:
            listener_array = [
                jpype.JProxy(
                    (
                        self.openrocket.simulation.listeners.SimulationListener,
                        self.openrocket.simulation.listeners.SimulationEventListener,
                        self.openrocket.simulation.listeners.SimulationComputationListener,
                        jpype.java.lang.Cloneable,
                    ),
                    inst=c,
                )
                for c in listeners
            ]

        sim.getOptions().randomizeSeed()  # Need to do this otherwise exact same numbers will be generated for each identical run
        sim.simulate(listener_array)

    def translate_flight_data_type(self, flight_data_type:Union[FlightDataType, str]):
        if isinstance(flight_data_type, FlightDataType):
            name = flight_data_type.name
        elif isinstance(flight_data_type, str):
            name = flight_data_type
        else:
            raise TypeError("Invalid type for flight_data_type")

        return getattr(self.openrocket.simulation.FlightDataType, name)

    def get_timeseries(self, simulation, variables: Iterable[Union[FlightDataType, str]], branch_number=0) \
            -> Dict[Union[FlightDataType, str], np.array]:
        """
        Gets a dictionary of timeseries data (as numpy arrays) from a simulation given specific variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number:
        :return:
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:
            output[v] = np.array(branch.get(self.translate_flight_data_type(v)))

        return output

    def get_final_values(self, simulation, variables: Iterable[Union[FlightDataType, str]], branch_number=0) \
            -> Dict[Union[FlightDataType, str], float]:
        """
        Gets a the final value in the time series from a simulation given variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number:
        :return:
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:
            output[v] = branch.get(self.translate_flight_data_type(v))[-1]

        return output

    def translate_flight_event(self, flight_event) -> FlightEvent:
        return {getattr(self.openrocket.simulation.FlightEvent.Type, x.name): x for x in FlightEvent}[flight_event]

    def get_events(self, simulation) -> Dict[FlightEvent, float]:
        """Returns a dictionary of all the flight events in a given simulation.
           Key is FlightEvent and value is a list of all the times at which the event occurs.
        """
        branch = simulation.getSimulatedData().getBranch(0)

        output = dict()
        for ev in branch.getEvents():
            type = self.translate_flight_event(ev.getType())
            if type in output:
                output[type].append(float(ev.getTime()))
            else:
                output[type] = [float(ev.getTime())]

        return output

    def get_component_named(self, root, name):
        """ Finds and returns the first rocket component with the given name.
            Requires a root RocketComponent, usually this will be a RocketComponent.rocket instance.
            Raises a ValueError if no component found.
        """

        for component in JIterator(root):
            if component.getName() == name:
                return component
        raise ValueError(root.toString() + " has no component named " + name)


class JIterator:
    """This class is a wrapper for java iterators to allow them to be used as python iterators"""

    def __init__(self, jit):
        """Give this any java object which implements iterable"""
        self.jit = jit.iterator(True)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.jit.hasNext():
            raise StopIteration()
        else:
            return next(self.jit)

def _get_private_field(obj, field_name):
    field = obj.getClass().getDeclaredField(field_name)
    field.setAccessible(True)
    ret = field.get(obj)
    field.setAccessible(False)
    return ret
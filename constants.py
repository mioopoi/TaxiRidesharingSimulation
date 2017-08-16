"""
Date of creation: 2016/12/15

Description: This module contains the global constants used in this project.
"""

from utilities import sim_time_convert


MAX_INT = 0x3f3f3f3f  # the value to represent a very large integer


# === For GeoComputing ===
R = 6371.0 * 10**3  # radius of the Earth in meters
PRECISION = 5     # The precision of GeoHash encoding


# === The basic setting of taxi ===
NUM_TAXI = 2980      # the number of taxis
AVERAGE_SPEED = 7.0    # average speed of taxis, unit: m/s (7 m/s = 25.2 km/h)
TAXI_CAPACITY = 1    # maximum number of passengers that a taxi can hold


# === The basic setting of passenger ===
PATIENCE = 5 * 60    # the maximum waiting time of a passenger (the size of the pickup window), unit: s


# === Query status ===
WAITING = "waiting"      # the passenger is waiting
CANCELLED = "cancelled"  # the passenger has cancelled the query
RIDING = "riding"        # the passenger is in the taxi and on the way to destination
SATISFIED = "satisfied"  # the passenger has arrived at the destination


# === The basic setting of simulation ===
START_TIME = "09:00:00"  # the start time of simulation
END_TIME = "09:30:00"    # the end time of simulation
TIME_STEP = 1            # step of the time goes
SIM_START_TIME = sim_time_convert(START_TIME)
SIM_END_TIME = sim_time_convert(END_TIME)

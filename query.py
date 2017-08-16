"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/16
Date of completion (1st time): 2016/12/16

Description: This module contains the abstraction of the Query of the passengers.

"""


import os

from geohash import geo_encode
from constants import PRECISION, PATIENCE, WAITING, CANCELLED, MAX_INT, SIM_START_TIME, SIM_END_TIME
from location import Location
from container import PriorityQueue
from road_network import RoadNetwork
from spatio_temporal_index import SpatioTemporalDatabase
from routing import ScheduleNode, map_match


class TimeWindow:
    """
    This class is the abstraction of a time window.
    """
    def __init__(self, early, late):
        """
        Initialize a TimeWindow.

        :param early: early time of a time window
        :param late: late time of a time window
        :type early: int
        :type late: int
        :return: None
        """
        self.early = early
        self.late = late

    def __str__(self):
        return "({}, {})".format(self.early, self.late)


class Query:
    """
    This class is the abstraction of the passenger's query.

    A Query instance is a passenger's request for a taxi ride.
    """
    def __init__(self, identifier, timestamp, origin, destination,
                 o_schedule_node=None, d_schedule_node=None):
        """
        Initialize a Query.

        In practice, a passenger only needs to explicitly indicate Query.destination, as most information of a query
        can be automatically obtained from a passenger's mobile phone, e.g., Query.origin and Query.timestamp.

        :param identifier: id of a query
        :param timestamp: current timestamp of the simulation
        :param origin: location of the origin
        :param destination: location of the destination
        :type identifier: int
        :type timestamp: int
        :type origin: Location
        :type destination: Location
        :type o_schedule_node: ScheduleNode
        :type d_schedule_node: ScheduleNode
        :return: None
        """
        self.id = identifier
        self.timestamp = timestamp
        self.origin = origin
        self.destination = destination

        self.o_geohash = geo_encode(origin.lat, origin.lon, PRECISION)
        self.d_geohash = geo_encode(destination.lat, destination.lon, PRECISION)

        self.o_schedule_node = o_schedule_node
        self.d_schedule_node = d_schedule_node

        self.pickup_window = TimeWindow(timestamp, timestamp + PATIENCE)  # @type pickup_window: TimeWindow
        self.delivery_window = TimeWindow(timestamp, timestamp + MAX_INT)  # @type delivery_window: TimeWindow

        self.matched_taxi = None  # @type matched_taxi: int
        self.status = WAITING
        self.waiting_time = 0

    def __str__(self):
        return "Query:\n- id: {}\n- timestamp: {}\n- origin: {}\n- destination: {}"\
            .format(self.id, self.timestamp, self.origin, self.destination)

    def __eq__(self, other):
        return self.id == other.id

    def init_schedule_node(self, road_network, database):
        """
        Initialize the two ScheduleNode of a query.

        :param road_network: the road network
        :param database: the spatio-temporal database
        :type road_network: RoadNetwork
        :type database: SpatioTemporalDatabase
        :return: None
        """
        self.o_schedule_node = map_match(self.id, self.origin, True, road_network, database)
        self.d_schedule_node = map_match(self.id, self.destination, False, road_network, database)

    def update_status(self, timestamp):
        """
        Update the status of a query.
        :param timestamp: the current time of the simulation system
        :type timestamp: int
        :return: None
        """
        if self.status == WAITING:
            self.waiting_time += 1
            if timestamp > self.pickup_window.late:
                self.cancel()

    def cancel(self):
        """
        Cancel the ride request.
        :return: None
        """
        self.status = CANCELLED
        print("Query %d is cancelled" % self.id)


def load_query():
    """
    Load taxi queries from file.

    :return: PriorityQueue[(int, Query)]
    :rtype: [dict[int, Query], PriorityQueue]
    """
    from datetime import datetime
    import time

    print("Loading queries and create query queue (will take about 20 sec)...")
    start_time = time.clock()

    query_set = dict()
    query_queue = PriorityQueue()
    start_time_tuple = datetime.strptime('00:00:00', '%H:%M:%S')
    identifier = 0

    i = 0
    file_list = os.listdir("./data/queries")
    for file_name in file_list:
        i += 1
        print("Loading the %d-th file..." % i)
        cur_file = open("./data/queries/" + file_name)
        for line in cur_file:
            [time_str, ori_lat, ori_lon, des_lat, des_lon] = line.split(',')
            time_tuple = datetime.strptime(time_str, '%H:%M:%S')
            timestamp = (time_tuple - start_time_tuple).seconds + 1

            if timestamp < SIM_START_TIME or timestamp > SIM_END_TIME:
                continue

            ori_lat = float(ori_lat)
            ori_lon = float(ori_lon)
            des_lat = float(des_lat)
            des_lon = float(des_lon)
            origin = Location(ori_lat, ori_lon)
            destination = Location(des_lat, des_lon)

            query = Query(identifier, timestamp, origin, destination)
            query_set[identifier] = query
            query_queue.put(query, timestamp)

            identifier += 1
        cur_file.close()
    print("Done. Elapsed time is %f seconds" % (time.clock() - start_time))
    return [query_set, query_queue]


def init_schedule_node(query_queue, road_network, database):
    """
    Create ScheduleNode of all the queries.

    :param query_queue: query queue
    :param road_network: road network
    :param database: spatio-temporal database
    :type query_queue: PriorityQueue
    :type road_network: RoadNetwork
    :type database: SpatioTemporalDatabase
    :return: None
    """
    import time

    print("Initializing the schedule node of queries (will take about 88 sec)...")
    start_time = time.clock()

    cnt = 0
    for item in query_queue.elements:
        item[1].init_schedule_node(road_network, database)
        cnt += 1
        if divmod(cnt, 1000)[1] == 0:
            print cnt

    print("Done. Elapsed time is %f seconds" % (time.clock() - start_time))

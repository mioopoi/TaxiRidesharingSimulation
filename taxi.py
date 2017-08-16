"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/16
Date of completion (1st time): 2016/12/24

Description: This module contains the abstraction of the taxi.

"""


from constants import AVERAGE_SPEED, TAXI_CAPACITY, NUM_TAXI, PRECISION, TIME_STEP, WAITING, RIDING, SATISFIED
from geohash import geo_encode
from location import Location, get_distance, bearing, end_pos
from road_network import RoadNetwork, Path, get_shortest_path
from spatio_temporal_index import SpatioTemporalDatabase
from query import Query
from routing import ScheduleNode
from dispatcher import Dispatcher


class Taxi:
    def __init__(self, identifier,
                 location,
                 speed=AVERAGE_SPEED,
                 capacity=TAXI_CAPACITY,
                 num_riders=0,
                 schedule=None,
                 route=None,
                 serving_queries=None):
        """
        Initialize a Taxi.

        :param identifier: id of the taxi
        :param location: current location of the taxi
        :param speed: the speed of the taxi
        :param capacity: the passenger capacity of the taxi

        :param num_riders: current number of passengers in the taxi
        :param schedule: the schedule of the taxi (a sequence of query.origin/destination that the taxi should finish)
        :param route: the route of the taxi to the first node of the schedule
        :param serving_queries: the current queries served by the taxi

        :type identifier: int
        :type location: Location
        :type speed: float
        :type capacity: int

        :type num_riders: int
        :type schedule: list[ScheduleNode]
        :type route: Path
        :type serving_queries: dict[int, Query]

        :return: None
        """
        self.id = identifier
        self.speed = speed
        self.capacity = capacity

        self.location = location
        self.geohash = geo_encode(location.lat, location.lon, PRECISION)
        self.num_riders = num_riders

        if schedule is None:
            self.schedule = list()
        else:
            self.schedule = schedule
        self.route = route

        if serving_queries is None:
            self.serving_queries = dict()
        else:
            self.serving_queries = serving_queries

        self.v_id = None       # the current vertex (id) that the taxi is on
        self.e_id = None      # the current edge (id) that the taxi is on
        self.__eid_index = None  # the index of e_id in route.edge_list
        self.driving_distance = 0.0

    def __str__(self):
        return "Taxi:\n- id: {}\n- location: {}\n- geohash: {}"\
            .format(self.id, self.location, self.geohash)

    def __eq__(self, other):
        return self.id == other.id

    def is_available(self):
        return self.num_riders < self.capacity and len(self.schedule) != 0

    def drive(self, timestamp, road_network, dispatcher, query_set, database):
        """
        Simulate taxi's movement and update the status of the taxi. Including:

        1. Update the new position of the taxi after a time step.
        2. Update Some corresponding information such as Taxi.e_id, Taxi.schedule and Taxi.route.
        3. Update stats such as Taxi.driving_distance.
        :param timestamp: current timestamp of the simulation system
        :param road_network: the road network
        :param dispatcher: the dispatcher
        :param query_set: the database of the query
        :param database: the s-t database
        :type timestamp: int
        :type road_network: RoadNetwork
        :type dispatcher: Dispatcher
        :type query_set: dict[Query]
        :type database: SpatioTemporalDatabase
        :return: None
        """

        # First check if the taxi has any query to be done.
        if self.route is None or len(self.route.edge_list) == 0:
            return

        # Drive according to its route.
        d = self.speed * TIME_STEP  # driving distance in a timestamp
        self.driving_distance += d

        cur_edge = road_network.get_edge(self.e_id)
        to_vertex = road_network.get_vertex(cur_edge.end_vid)
        to_location = to_vertex.location

        theta = bearing(self.location, to_location)
        next_pos = end_pos(self.location, theta, d)

        e_start_vertex = road_network.get_vertex(cur_edge.start_vid)
        edge_offset = get_distance(e_start_vertex.location, next_pos)
        if edge_offset < cur_edge.weight:
            self.__update_pos(timestamp, next_pos, database)
        else:  # The taxi has arrived at the end of the current edge.
            self.__update_pos(timestamp, to_location, database)
            self.v_id = road_network.get_edge(self.e_id).end_vid
            next_eid = self.__get_next_eid()
            if next_eid is not None:
                self.e_id = next_eid
                self.__eid_index += 1
            else:
                # It is now the last edge of current route, which means the taxi arrives at the first ScheduleNode
                # in Taxi.schedule, so we need to re-compute a new route from current ScheduleNode to next ScheduleNode.
                schedule_node = self.schedule.pop(0)
                query = query_set[schedule_node.query_id]
                if schedule_node.is_origin:
                    if query.status == WAITING:
                        self.serve_query(query)
                        dispatcher.add_serving_query(query)
                    else:  # delete the 'destination ScheduleNode' of the query in the schedule
                        i = 0
                        for item in self.schedule:
                            if item.query_id == query.id:
                                self.schedule.pop(i)
                                break
                            i += 1
                else:
                    self.satisfy_query(query)
                    dispatcher.add_completed_query(query)

                self.update_route(road_network, schedule_node)  # update the route
                database.update_taxi_list(timestamp, self, self.route, road_network)  # update the database

    def __update_pos(self, timestamp, new_pos, database):
        """
        Update taxi's geo-info.

        If the taxi's geo-hash changes, we also need to update the grid's taxi list, including:
        1. Remove the taxi from the previous grid's taxi list.
        2. Insert the taxi into the newly entered grid's taxi list.

        :param timestamp: current timestamp of the simulation system
        :param new_pos: new position of the taxi
        :param database: the spatio-temporal database
        :type timestamp: int
        :type new_pos: Location
        :type database: SpatioTemporalDatabase
        :return: None
        """
        self.location = new_pos
        next_geohash = geo_encode(new_pos.lat, new_pos.lon, PRECISION)
        if next_geohash != self.geohash:
            database.grid[self.geohash].remove_taxi(self.id)
            database.grid[next_geohash].add_taxi(self.id, timestamp)
            self.geohash = next_geohash

    def __get_next_eid(self):
        """
        Get next edge that the taxi should drive to, according to current route.

        If it is the last edge of current route, return None.

        :return: id of next edge
        :rtype: int
        """
        if self.__eid_index == len(self.route.edge_list)-1:
            return None
        return self.route.edge_list[self.__eid_index + 1]

    def serve_query(self, query):
        """
        A query "get in" a taxi and starts the journey.
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        print("Taxi %d picks query %d" % (self.id, query.id))
        query.status = RIDING
        self.serving_queries[query.id] = query
        self.num_riders += 1

    def satisfy_query(self, query):
        """
        A query "get off" a taxi and ends the journey.
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        print("Taxi %d drops off query %d" % (self.id, query.id))
        query.status = SATISFIED
        self.serving_queries.pop(query.id)
        self.num_riders -= 1

    def update_route(self, road_network, schedule_node=None):
        """
        Update the route of a taxi.
        :param road_network: the road network
        :param schedule_node: the current ScheduleNode that the taxi is on
        :type road_network: RoadNetwork
        :type schedule_node: ScheduleNode
        :return: None
        """
        if len(self.schedule) == 0:
            self.route = None
            return

        if schedule_node is None:  # means that the taxi has the first ScheduleNode to be done
            from_vid = self.v_id
        else:
            from_vid = schedule_node.matched_vid
        to_vid = self.schedule[0].matched_vid
        self.route = get_shortest_path(road_network, from_vid, to_vid)
        if len(self.route.edge_list) != 0:
            self.e_id = self.route.edge_list[0]
            self.__eid_index = 0


def gen_taxi(database, road_network):
    """
    Generate entities of taxi.

    :param database: the spatio-temporal database
    :param road_network: the road network
    :type database: SpatioTemporalDatabase
    :type road_network: RoadNetwork
    :return: a dictionary with key the id of a taxi and value the corresponding Taxi instance
    :rtype: dict[int, Taxi]
    """
    import time

    print("Generating taxis...")
    start_time = time.clock()

    taxi_set = dict()
    total_num_vertex = road_network.num_vertex
    identifier = 1

    # total_taxi = 0
    for i in database.grid:
        grid = database.grid[i]
        num_vertex = len(grid.vertex_list)
        num_taxi = round(float(num_vertex) / total_num_vertex * NUM_TAXI)  # the number of taxi put in the grid
        if num_taxi == 0:
            continue
        # total_taxi += num_taxi

        cnt = 0
        for v_id in grid.vertex_list:
            location = road_network.vertex_set[v_id].location
            taxi = Taxi(identifier, location)
            taxi.v_id = v_id
            taxi_set[identifier] = taxi

            identifier += 1
            cnt += 1
            if cnt == num_taxi:
                break
    print("Done. Elapsed time is %f seconds." % (time.clock() - start_time))
    # print total_taxi
    return taxi_set

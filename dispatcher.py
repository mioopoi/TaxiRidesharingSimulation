"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/20
Date of completion (1st time): 2016/12/22

Description: This module contains the interfaces for taxi dispatching.

"""


from location import get_distance
from road_network import RoadNetwork
from spatio_temporal_index import SpatioTemporalDatabase
from query import Query
# from taxi import Taxi
from container import Queue
from constants import MAX_INT


class Dispatcher:

    def __init__(self,
                 failed_queries=None,
                 waiting_queries=None,
                 completed_queries=None,
                 cancelled_queries=None):
        """
        Initialize a Dispatcher.

        :param failed_queries: a Queue stores the queries that the dispatcher failed to find a taxi, these queries
        need to be processed in the next timestamp
        :param waiting_queries: a dict stores the queries that are dispatched a taxi and under waiting
        :param completed_queries: a list stores successfully completed queries
        :param cancelled_queries: a list stores cancelled queries
        :type failed_queries: Queue[Query]
        :type waiting_queries: dict[int, Query]
        :type completed_queries: list[Query]
        :type cancelled_queries: list[Query]
        :return: None
        """

        if failed_queries is None:
            self.failed_queries = Queue()
        else:
            self.failed_queries = failed_queries

        if waiting_queries is None:
            self.waiting_queries = dict()
        else:
            self.waiting_queries = waiting_queries

        if completed_queries is None:
            self.completed_queries = list()
        else:
            self.completed_queries = completed_queries

        if cancelled_queries is None:
            self.cancelled_queries = list()
        else:
            self.cancelled_queries = cancelled_queries

    def dispatch_taxi(self, timestamp, query, database, taxi_set, road_network):
        """
        Respond to the query and try to dispatch a taxi for the query.
        :param timestamp: the current time of the simulation system
        :param query: the query
        :param database: the spatio-temporal database
        :param taxi_set: the taxi set
        :param road_network: the road network
        :type timestamp: int
        :type query: Query
        :type database: SpatioTemporalDatabase
        :type taxi_set: dict[int, Taxi]
        :type road_network: RoadNetwork

        :return: if the dispatch is successful or not
        :rtype: void
        """

        candi_taxi_list = self.__single_side_search(timestamp, query, database)
        if self.__schedule(query, candi_taxi_list, taxi_set, road_network):
            self.add_waiting_query(query)
        else:
            self.add_failed_query(query)

    def add_cancelled_query(self, query):
        """
        Cancel a query.
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        self.cancelled_queries.append(query)

    def add_waiting_query(self, query):
        """
        Cancel a query.
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        self.waiting_queries[query.id] = query

    def add_serving_query(self, query):
        """
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        self.waiting_queries.pop(query.id)

    def add_failed_query(self, query):
        """
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        self.failed_queries.put(query)

    def add_completed_query(self, query):
        """
        :param query: a Query instance
        :type query: Query
        :return: None
        """
        self.completed_queries.append(query)

    @staticmethod
    def __single_side_search(timestamp, query, database):
        """
        Single-side taxi searching.

        :param timestamp: current time of the simulation system
        :param query: the query
        :param database: the spatio-temporal database
        :type timestamp: int
        :type query: Query
        :type database: SpatioTemporalDatabase
        :return: a list of candidate taxis
        :rtype: list[int]
        """

        o_grid = query.o_geohash
        candi_taxi_list = []

        for item in database.grid[o_grid].temporal_grid_list:
            if item[1] + timestamp > query.pickup_window.late:
                break

            grid_id = item[0]
            grid = database.grid[grid_id]

            # scan the taxi list of the grid and filter the taxis that satisfies the pickup time window
            for taxi_id in grid.taxi_list:
                eta = grid.taxi_list[taxi_id]  # arrival time of the taxi that comes into the gird in the near future
                if item[1] + eta <= query.pickup_window.late:
                    candi_taxi_list.append(taxi_id)
        return candi_taxi_list

    def __schedule(self, query, candi_taxi_list, taxi_set, road_network):
        """
        Taxi scheduling.

        The purpose of scheduling is to insert the origin and destination (ScheduleNode) of the query into the schedule
        of the taxi which satisfies the query with minimum additional travel distance.

        :param query: the query
        :param candi_taxi_list: list of taxi id
        :param taxi_set: the taxi set
        :param road_network: the road network
        :type query: Query
        :type candi_taxi_list: list[int]
        :type taxi_set: dict[int, Taxi]
        :type road_network: RoadNetwork
        :return: if the dispatch is successful or not
        :rtype: bool
        """
        if len(candi_taxi_list) == 0:
            return False

        picked_taxi_id = candi_taxi_list[0]
        min_dis = MAX_INT
        for taxi_id in candi_taxi_list:
            taxi = taxi_set[taxi_id]
            if not taxi.is_available():
                continue
            dis = get_distance(taxi.location, query.origin)
            if dis < min_dis:
                picked_taxi_id = taxi_id
                min_dis = dis

        picked_taxi = taxi_set[picked_taxi_id]
        query.matched_taxi = picked_taxi_id
        picked_taxi.schedule.append(query.o_schedule_node)
        picked_taxi.schedule.append(query.d_schedule_node)
        picked_taxi.update_route(road_network)

        return True

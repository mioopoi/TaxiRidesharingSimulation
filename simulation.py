"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/20
Date of completion (1st time): 2016/12/28

Description: This is the main module for taxi ride-sharing simulation.

"""


from road_network import load_data
from spatio_temporal_index import SpatioTemporalDatabase
from query import load_query, init_schedule_node
from taxi import gen_taxi
from dispatcher import Dispatcher

from constants import SIM_START_TIME, SIM_END_TIME, WAITING, CANCELLED
from container import PriorityQueue

import time


class Simulation:
    """
    This is a class which is responsible for setting up and running a simulation.
    """

    def __init__(self):
        road_network = load_data()
        self.road_network = road_network

        db = SpatioTemporalDatabase()
        db.load_road_network(road_network)
        db.init_static_info(road_network)
        self.taxi_set = gen_taxi(db, self.road_network)
        db.init_dynamic_info(self.taxi_set, SIM_START_TIME)
        self.db = db

        [self.query_set, self.query_queue] = load_query()
        init_schedule_node(self.query_queue, self.road_network, self.db)

        self.dispatcher = Dispatcher()

    def run(self):

        print("The simulation system is running...")
        start_time = time.clock()

        waiting_queries = PriorityQueue()

        for timestamp in range(SIM_START_TIME, SIM_END_TIME+1):
            print("Time: %d" % timestamp)
            # Catch the queries to be processed in this timestamp. The queries consists of two parts:
            # 1. queries that happened in this timestamp
            # 2. queries that stranded in previous timestamps
            while not self.query_queue.empty():
                new_query = self.query_queue.get()
                if new_query.timestamp == timestamp:
                    waiting_queries.put(new_query, new_query.timestamp)
                else:
                    self.query_queue.put(new_query, new_query.timestamp)
                    break
            while not self.dispatcher.failed_queries.empty():
                old_query = self.dispatcher.failed_queries.get()
                waiting_queries.put(old_query, old_query.timestamp)

            # Process the queries.
            while not waiting_queries.empty():
                query = waiting_queries.get()
                if query.status == CANCELLED:
                    self.dispatcher.add_cancelled_query(query)
                else:
                    self.dispatcher.dispatch_taxi(timestamp, query, self.db, self.taxi_set, self.road_network)

            # Update the status of all the queries
            for query in self.query_set.values():
                if query.timestamp <= timestamp and query.status == WAITING:
                    query.update_status(timestamp)

            # All the taxis drive according to their schedule.
            for taxi in self.taxi_set.values():
                taxi.drive(timestamp, self.road_network, self.dispatcher, self.query_set, self.db)

        print("The simulation is end. Elapsed time is %f." % (time.clock() - start_time))


# if __name__ == "__main__":
    # sim = Simulation()

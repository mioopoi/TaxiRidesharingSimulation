"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/22
Date of completion (1st time):

Description: This module contains the interfaces for taxi scheduling.

"""


from location import Location, get_distance
from road_network import RoadNetwork
from spatio_temporal_index import SpatioTemporalDatabase


class ScheduleNode:
    def __init__(self, query_id, is_origin, matched_vid):
        """
        Initialize a ScheduleNode.

        :param query_id: id of a query
        :param is_origin: bool param indicates that if the ScheduleNode is an origin of a query
        :param matched_vid: id of the matched vertex in the road network
        :type query_id: int
        :type is_origin: bool
        :type matched_vid: int
        :return: None
        """
        self.query_id = query_id
        self.is_origin = is_origin
        self.matched_vid = matched_vid

    def __str__(self):
        return "ScheduleNode:\n- query id: {}\n- is origin: {}\n- matched vertex id:{}\n"\
            .format(self.query_id, self.is_origin, self.matched_vid)


def map_match(query_id, location, is_origin, road_network, database):
    """
    Find the best matched vertex in the road network for the location of a query.

    :param query_id: id of a query
    :param location: location of a query
    :param is_origin: bool param indicates that if the location is an origin of a query
    :param road_network: the road network
    :param database: the spatio-temporal database
    :type query_id: int
    :type location: Location
    :type is_origin: bool
    :type road_network: RoadNetwork
    :type database: SpatioTemporalDatabase
    :return: a ScheduleNode
    :rtype: ScheduleNode
    """
    geohash = location.geohash
    matched_vid = None
    min_dis = float('inf')

    # Scan all the vertex in the grid and pick the one closest to the location.
    for v_id in database.grid[geohash].vertex_list:
        vertex = road_network.get_vertex(v_id)
        v_loc = vertex.location
        dis = get_distance(v_loc, location)
        if dis < min_dis:
            matched_vid = v_id
            min_dis = dis

    # Create the ScheduleNode.
    schedule_node = ScheduleNode(query_id, is_origin, matched_vid)
    return schedule_node

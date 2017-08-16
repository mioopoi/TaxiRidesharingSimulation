"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/14
Date of completion (1st time): 2016/12/16

Description: This module contains the abstraction of the City-Grid (Spatio-Temporal Index).

"""


import pickle

from road_network import *
from geohash import geo_decode
from location import Location, get_distance
from constants import AVERAGE_SPEED


class GridCell:
    def __init__(self, geohash):
        """
        Initialize a GridCell.

        :param geohash: str
        :return: None
        """
        self.geohash = geohash
        self.center_location = self.__get_center_location()
        self.anchor = None
        self.vertex_list = set()

        self.spatial_grid_list = []
        self.temporal_grid_list = []
        self.taxi_list = dict()

    def __str__(self):

        return "GridCell:\n- geohash: {}\n- anchor: {}\n- num vertex: {}"\
            .format(self.geohash, self.anchor, len(self.vertex_list))

    def __eq__(self, other):

        return self.geohash == other.geohash

    def __get_center_location(self):
        [lat, lon] = geo_decode(self.geohash)
        location = Location(lat, lon)
        return location

    def get_num_vertex(self):

        return len(self.vertex_list)

    def get_num_taxi(self):

        return len(self.taxi_list)

    def remove_taxi(self, taxi_id):
        self.taxi_list.pop(taxi_id)

    def add_taxi(self, taxi_id, t_arrive):
        self.taxi_list[taxi_id] = t_arrive


class MatrixCell:
    """
    This class is the encapsulation of the element of the grid distance matrix.
    """
    def __init__(self, d, t):
        """
        Initialize a MatrixCell.

        :param d: the spatial distance between grid[i] and grid[j], unit: m
        :param t: the temporal distance between grid[i] and grid[j], unit: s
        :type d: float
        :type t: float
        :return: None
        """
        self.d = d
        self.t = t

    def __str__(self):

        return "({}, {})".format(self.d, self.t)


class SpatioTemporalDatabase:
    def __init__(self, grid=None, grid_distance_matrix=None):
        """
        Initialize a SpatioTemporalDatabase.

        SpatioTemporalDatabase is the abstraction data type of the spatio-temporal database.

        :param grid: a {key: value} Hash Map, with geohash str as the key, and GridCell
        the value
        :type grid: dict[str, GridCell]
        :return: None
        """
        self.num_grid = 0

        if grid is None:
            self.grid = dict()
        else:
            self.grid = grid

        if grid_distance_matrix is None:
            self.grid_distance_matrix = dict()
        else:
            self.grid_distance_matrix = grid_distance_matrix

    def __str__(self):

        return "SpatioTemporalDatabase:\n- num grid cell: {}".format(self.num_grid)

    def load_road_network(self, road_network):
        """
        Load road network. This process will create a few of grid cells based on the road network.

        :param road_network: RoadNetwork
        :return: None
        """
        # Scan all the vertices and create grid cells.
        for v_id in road_network.vertex_set:
            vertex = road_network.get_vertex(v_id)
            geohash = vertex.get_geohash()
            if geohash not in self.grid:
                new_grid_cell = GridCell(geohash)
                new_grid_cell.vertex_list.add(v_id)
                self.grid[geohash] = new_grid_cell
                self.num_grid += 1
            else:
                self.grid[geohash].vertex_list.add(v_id)

    def init_static_info(self, road_network):
        """
        Pre-compute the static info of grid cells. Including:
        1. Determine the anchor of grid cells.
        2. Compute the grid distance matrix.
        3. Construct the spatial grid list and the temporal grid list of all the grid cells.

        :param road_network: RoadNetwork
        :return: None
        """
        import time

        print("Determining the anchor nodes...")
        start_time = time.clock()
        self.__determine_anchor(road_network)
        print("Done. Elapsed time is %f seconds." % (time.clock() - start_time))

        print("Computing the grid distance matrix (about 32 minutes)...")
        start_time = time.clock()
        #self.__compute_distance_matrix(road_network)  # re-compute the grid distance matrix
        # call the function pickle.load() and restore the grid distance through "byte stream deserialization"
        f = open('grid_distance_matrix', 'rb')
        self.grid_distance_matrix = pickle.load(f)
        f.close()
        print("Done. Elapsed time is %f seconds." % (time.clock() - start_time))

        print("Constructing the spatial grid list and temporal grid list (about 8 seconds)...")
        start_time = time.clock()
        self.__construct_static_list()
        print("Done. Elapsed time is %f seconds." % (time.clock() - start_time))

    def __determine_anchor(self, road_network):
        """
        Determine the anchor of all grid cells.

        :param road_network: RoadNetwork
        :return: None
        """
        for geohash in self.grid:
            center_location = self.grid[geohash].center_location
            anchor = None
            min_dis = float('inf')

            # Scan all the vertexes in the grid and pick the one closest to the center location.
            for v_id in self.grid[geohash].vertex_list:
                vertex = road_network.get_vertex(v_id)
                location = vertex.location
                dis = get_distance(location, center_location)
                if dis < min_dis:
                    anchor = v_id
                    min_dis = dis
            self.grid[geohash].anchor = anchor

    def __compute_distance_matrix(self, road_network):
        """
        Compute the grid distance matrix.

        :param road_network: RoadNetwork
        :return: None
        """

        # Double-scan all the grid cells.
        for i in self.grid:
            anchor_i = self.grid[i].anchor
            anchor_i_location = road_network.get_vertex(anchor_i).location
            come_from = single_source_dijkstra(road_network, anchor_i)
            self.grid_distance_matrix[i] = dict()
            for j in self.grid:
                anchor_j = self.grid[j].anchor
                anchor_j_location = road_network.get_vertex(anchor_j).location
                d = get_distance(anchor_i_location, anchor_j_location)  # the spatial distance
                shortest_path = construct_path(road_network, anchor_i, anchor_j, come_from)
                if len(shortest_path.vertex_list) == 0:
                    t = d / AVERAGE_SPEED
                else:
                    t = shortest_path.distance / AVERAGE_SPEED  # the temporal distance

                # Put (d, t) into the grid distance matrix.
                matrix_cell = MatrixCell(d, t)
                self.grid_distance_matrix[i][j] = matrix_cell

    def __construct_static_list(self):
        """
        Construct the spatial grid list and the temporal grid list of all the grid cells, according to the grid
        distance matrix.

        :return: None
        """
        for i in self.grid:

            # spatial grid list
            spatial_list = {key: value.d for key, value in self.grid_distance_matrix[i].items()}
            spatial_grid_list = sorted(spatial_list.items(), lambda x, y: cmp(x[1], y[1]))
            self.grid[i].spatial_grid_list = spatial_grid_list

            # temporal grid list
            temporal_list = {key: value.t for key, value in self.grid_distance_matrix[i].items()}
            temporal_grid_list = sorted(temporal_list.items(), lambda x, y: cmp(x[1], y[1]))
            self.grid[i].temporal_grid_list = temporal_grid_list

    def init_dynamic_info(self, taxi_set, start_time):
        """
        Initialize the dynamic info of grid cells. Including:
        1. Initialize the taxi list of each grid cell.

        :param taxi_set: the taxi set
        :param start_time: the start time of the simulation
        :type taxi_set: dict[int, Taxi]
        :type start_time: int
        :return: None
        """
        for identifier in taxi_set:
            taxi = taxi_set[identifier]
            geohash = taxi.geohash
            self.grid[geohash].taxi_list[identifier] = start_time

    def update_taxi_list(self, timestamp, taxi, route, road_network):
        """
        Update grid cell's taxi list according to a new route.

        :param timestamp: the current time of the simulation system
        :param taxi: a Taxi instance
        :param route: a new route of a taxi
        :param road_network: the road network
        :type timestamp: int
        :type taxi: Taxi
        :type route: Path
        :type road_network: RoadNetwork
        :return: None
        """
        if route is None or len(route.edge_list) == 0:
            return

        cur_vid = route.vertex_list[0]
        cur_geohash = road_network.get_vertex(cur_vid).get_geohash()
        dis = 0.0
        for e_id in route.edge_list:
            next_edge = road_network.get_edge(e_id)
            end_vid = next_edge.end_vid
            next_geohash = road_network.get_vertex(end_vid).get_geohash()
            dis += next_edge.weight
            if next_geohash != cur_geohash:
                self.grid[next_geohash].taxi_list[taxi.id] = timestamp + dis / AVERAGE_SPEED
                cur_vid = end_vid
                cur_geohash = road_network.get_vertex(cur_vid).get_geohash()

"""
Author: Huafan Li <fanfan199308@gmail.com>

Date of creation: 2016/12/11
Date of completion (1st time): 2016/12/13

Description: This module contains the abstraction of the road network and some utilities for graph computing.

=== Constants ===
NEIGHBOR: str
    A constant used for the Vertex category.
OUT_EDGE: str
    A constant used for the Edge category.
"""


from location import Location, get_distance
from container import Queue, PriorityQueue

import pandas as pd


class Vertex:
    def __init__(self, v_id, location):
        """
        Initialize a Vertex.

        The Vertex class is the abstraction of road intersection.

        :param v_id: int
            id of a vertex
        :param location: Location
            geo location of a vertex
        :return: None
        """
        self.id = v_id
        self.location = location

        self.connected_to = {}        # dict of neighbor vertexes of this vertex

    def __str__(self):
        """
        Return a string representation.

        :return: str

        >>> location = Location(39.564540, 115.739662)
        >>> v1 = Vertex(1, location)
        >>> print(v1)
        Vertex:
        - id: 1
        - location: (39.56454, 115.739662)
        - connected to: {}
        """
        return "Vertex:\n- id: {}\n- location: {}\n- connected to: {}"\
            .format(self.id, self.location, self.connected_to)

    def __eq__(self, other):
        """
        Return True if self equals other, and False otherwise.

        :param other: Vertex
        :return: bool
        """
        return self.id == other.v_id

    def add_neighbor(self, nbr_id, e_id):
        """
        Add a neighbor vertex for this vertex.

        :param nbr_id: int
            id of the neighbor vertex
        :param e_id: int
            id of the edge from self to neighbor
        :return: None
        """
        self.connected_to[nbr_id] = e_id

    def get_connections(self):
        return self.connected_to.keys()

    def get_id(self):
        return self.id

    def get_location(self):
        """
        Return the location (lat, lon) of a vertex.

        :return: Location
        """
        return self.location

    def get_geohash(self):
        """
        Return the GeoHash of the location of a vertex.

        :return: str
        """
        return self.location.geohash

    def get_edge(self, nbr_id):
        """
        Return the id of the edge from this vertex to its neighbor vertex passed as a parameter.

        :param nbr_id: int
        :return: float
        """
        return self.connected_to[nbr_id]


class Edge:
    def __init__(self, e_id, start_vid, end_vid, weight):
        """
        Initialize an Edge.

        The Edge class the the abstraction of road segment.

        :param e_id: int
            id of an edge
        :param start_vid: int
            id of the start vertex of the edge
        :param end_vid: int
            id of the end vertex of the edge
        :return: None
        """
        self.id = e_id
        self.start_vid = start_vid
        self.end_vid = end_vid
        self.weight = weight    # the length of the edge in meters

    def __str__(self):
        """
        Return a string representation.

        :return: str

        >>> edge = Edge(1, 123, 222, 500.2)
        >>> print(edge)
        Edge:
        - id: 1
        - start vid: 123
        - end vid: 222
        - length: 500.2
        """
        return "Edge:\n- id: {}\n- start vid: {}\n- end vid: {}\n- length: {}".\
            format(self.id, self.start_vid, self.end_vid, self.weight)

    def __eq__(self, other):
        """
        Return True if self equals other, and False otherwise.

        :param other: Edge
        :return: bool
        """
        return self.id == other.id

    def get_id(self):
        return self.id

    def get_start_vid(self):
        return self.start_vid

    def get_end_vid(self):
        return self.end_vid

    def get_weight(self):
        return self.weight


class RoadNetwork:
    """
    The abstraction data type of the road network.
    """

    def __init__(self):
        """
        Initialize a RoadNetwork.

        :return: None
        """
        self.num_vertex = 0
        self.num_edge = 0
        self.vertex_set = dict()
        self.edge_set = dict()

    def __str__(self):
        return "RoadNetwork:\n- num vertex: {}\n- num edge: {}".format(self.num_vertex, self.num_edge)

    def add_vertex(self, v_id, lat=None, lon=None):
        """
        Add a vertex.

        :param v_id: int
        :param lat: float
        :param lon: float
        :return: None
        """
        if v_id not in self.vertex_set:
            self.num_vertex += 1
        location = Location(lat, lon)
        vertex = Vertex(v_id, location)
        self.vertex_set[v_id] = vertex

    def add_edge(self, e_id, start_vid, end_vid, weight):
        """
        Add an edge.

        :param e_id: int
        :param start_vid: int
        :param end_vid: int
        :param weight: float
        :return: None
        """

        if e_id not in self.edge_set:
            self.num_edge += 1
        if start_vid not in self.vertex_set:
            self.add_vertex(start_vid)
        if end_vid not in self.vertex_set:
            self.add_vertex(end_vid)
        edge = Edge(e_id, start_vid, end_vid, weight)
        self.edge_set[edge.id] = edge
        self.vertex_set[start_vid].add_neighbor(end_vid, e_id)

    def get_vertex(self, v_id):
        """
        :param v_id: id of the required vertex
        :type v_id: int
        :return: Vertex instance
        :rtype: Vertex
        """
        if v_id in self.vertex_set:
            return self.vertex_set[v_id]
        else:
            return None

    def get_edge(self, e_id):
        """
        :param e_id: id of the required edge
        :type e_id: int
        :return: required Edge instance
        :rtype: Edge
        """

        if e_id in self.edge_set:
            return self.edge_set[e_id]
        else:
            return None

    def get_neighbors(self, s_vid):
        """
        Return the neighbor list of vertex s_vid.

        :param s_vid: int
        :return: list[int]
        """
        return self.vertex_set[s_vid].connected_to.keys()

    def get_eid(self, start_vid, end_vid):
        """
        Return the id of the edge (start_vid, end_vid).

        :param start_vid: int
        :param end_vid: int
        :return: int
        """
        if end_vid not in self.vertex_set[start_vid].connected_to:
            return None

        return self.vertex_set[start_vid].connected_to[end_vid]

    def get_weight(self, start_vid, end_vid):
        """
        Return the weight of edge (start_vid, end_vid)

        :param start_vid: int
        :param end_vid: int
        :return: float
        """
        if end_vid in self.vertex_set[start_vid].connected_to:
            e_id = self.vertex_set[start_vid].connected_to[end_vid]
            return self.edge_set[e_id].weight
        else:
            return float('inf')

    def get_straight_distance(self, start_vid, end_vid):
        """
        Return the straight-line distance between vertex start_vid and vertex end_vid.

        :param start_vid: int
        :param end_vid: int
        :return: float
        """
        v_start = self.get_vertex(start_vid)
        v_end = self.get_vertex(end_vid)
        return get_distance(v_start.location, v_end.location)


def load_data():
    """
    load vertices and edges data from "./data" using Pandas and create the road network.

    It will take about 30 seconds.

    :return: RoadNetwork
    """
    import time

    print("Loading data and create road network (about 30 sec)...")
    start_time = time.clock()

    road_network = RoadNetwork()

    vertices = pd.read_csv("./data/vertices.csv")
    edges = pd.read_csv("./data/edges.csv")

    print("Loading vertices...")
    for index, row in vertices.iterrows():
        road_network.add_vertex(int(row['v_id']), row['lat'], row['lon'])

    print("Loading edges...")
    for index, row in edges.iterrows():
        road_network.add_edge(int(row['e_id']), int(row['start_vid']), int(row['end_vid']), row['length'])

    print("Done. Elapsed time is %f seconds" % (time.clock() - start_time))

    return road_network


def is_reachable(road_network, s_vid, e_vid):
    """
    Return True if there exist a path from s_vid to e_vid, otherwise return False.

    The algorithm is basic Breadth-First-Search (with early exit).

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :return: bool
    """
    frontier = Queue()
    frontier.put(s_vid)
    came_from = dict()
    came_from[s_vid] = None

    while not frontier.empty():
        current = frontier.get()
        if current == e_vid:
            return True
        for neighbor in road_network.get_neighbors(current):
            if neighbor not in came_from:
                frontier.put(neighbor)
                came_from[neighbor] = current
    return False


class Path:
    def __init__(self, vertex_list=None, edge_list=None, distance=0.0):
        """

        :param vertex_list: the sequence of the vertex id of a path
        :param edge_list: the sequence of the edge id of a path
        :param distance: the length of a path
        :type vertex_list: list[int]
        :type edge_list: list[int]
        :type distance: float
        :return: None
        """
        self.vertex_list = vertex_list
        self.edge_list = edge_list
        self.distance = distance

    def __str__(self):
        return "Path:\n- vertex list: {}\n- edge list: {}\n- distance: {}"\
            .format(self.vertex_list, self.edge_list, self.distance)


def construct_path(road_network, s_vid, e_vid, came_from):
    """
    Reconstruct the path.

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :param came_from: dict[int: int]
    :return: Path
    """
    current = e_vid
    v_list = [current]
    while current != s_vid:

        if current not in came_from:    # s_vid-->e_vid is unreachable
            v_list = []
            break

        current = came_from[current]
        v_list.append(current)
    v_list.reverse()

    # Construct the edge list.
    e_list = []
    distance = 0.0
    len_v = len(v_list)
    for i in range(len_v-1):
        u = v_list[i]
        v = v_list[i+1]
        e_id = road_network.get_eid(u, v)
        e_list.append(e_id)
        distance += road_network.get_weight(u, v)

    path = Path(v_list, e_list, distance)
    return path


def bfs(road_network, s_vid, e_vid):
    """
    Return the path from vertex s_vid to vertex e_vid using Dijkstra's algorithm.

    The implementation is the same as the function is_reachable(), except that instead of bool type, we return a Path
    found by Breadth First Search.

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :return: Path
    """
    frontier = Queue()
    frontier.put(s_vid)
    came_from = dict()
    came_from[s_vid] = None

    while not frontier.empty():
        current = frontier.get()
        if current == e_vid:
            break
        for neighbor in road_network.get_neighbors(current):
            if neighbor not in came_from:
                frontier.put(neighbor)
                came_from[neighbor] = current
    return construct_path(road_network, s_vid, e_vid, came_from)


def dijkstra(road_network, s_vid, e_vid):
    """
    Return the exact shortest path from vertex s_vid to vertex e_vid using Dijkstra's algorithm.

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :return: Path
    """
    frontier = PriorityQueue()
    frontier.put(s_vid, 0)
    came_from = dict()
    cost_so_far = dict()
    came_from[s_vid] = None
    cost_so_far[s_vid] = 0

    while not frontier.empty():
        current = frontier.get()

        if current == e_vid:
            break

        for neighbor in road_network.get_neighbors(current):
            new_cost = cost_so_far[current] + road_network.get_weight(current, neighbor)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost    # relax
                priority = new_cost
                frontier.put(neighbor, priority)
                came_from[neighbor] = current

    return construct_path(road_network, s_vid, e_vid, came_from)


def greedy_bfs(road_network, s_vid, e_vid):
    """
    Return the shortest path from vertex s_vid to vertex e_vid using Greedy-Best-First-Search.

    In Greedy-BFS, the heuristic function is road_network.get_straight_distance().

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :return: Path
    """
    frontier = PriorityQueue()
    frontier.put(s_vid, 0)
    came_from = dict()
    came_from[s_vid] = None

    while not frontier.empty():
        current = frontier.get()

        if current == e_vid:
            break

        for neighbor in road_network.get_neighbors(current):
            if neighbor not in came_from:
                priority = road_network.get_straight_distance(neighbor, e_vid)
                frontier.put(neighbor, priority)
                came_from[neighbor] = current

    return construct_path(road_network, s_vid, e_vid, came_from)


def get_shortest_path(road_network, s_vid, e_vid):
    """
    Return the shortest path from vertex s_vid to vertex e_vid using A* algorithm.

    If s_vid-->e_vid is unreachable, return None.

    :param road_network: RoadNetwork
    :param s_vid: int
    :param e_vid: int
    :return: Path
    """
    frontier = PriorityQueue()
    frontier.put(s_vid, 0)
    came_from = dict()
    cost_so_far = dict()
    came_from[s_vid] = None
    cost_so_far[s_vid] = 0

    while not frontier.empty():
        current = frontier.get()
        # Take a look at the number of lines of code:) date: 2016/12/13 23:12
        if current == e_vid:
            break

        for neighbor in road_network.get_neighbors(current):
            new_cost = cost_so_far[current] + road_network.get_weight(current, neighbor)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + road_network.get_straight_distance(neighbor, e_vid)
                frontier.put(neighbor, priority)
                came_from[neighbor] = current

    return construct_path(road_network, s_vid, e_vid, came_from)


def floyd_warshall(road_network):
    """
    Find the length of the shortest paths between all pairs of vertices using Floyd-Warshall algorithm.

    !!! DO NOT run this algorithm if the number of vertex is huge, eg. larger than 5000, since the space complexity
    is O(|V|^2).

    :param road_network: RoadNetwork
    :return: dict[int, dict[int, float]]
        the matrix of length of shortest path of all pairs of vertices
    """
    import time
    print("Start Floyd-Warshall algorithm...")
    start_time = time.clock()

    # Initialize the minimum distance matrix.
    dist = dict()
    for u in road_network.vertex_set:
        dist[u] = dict()
        for v in road_network.vertex_set:
            dist[u][v] = float('inf')
    for v in road_network.vertex_set:
        dist[v][v] = 0.0
    for e in road_network.edge_set:
        dist[e.start_vid][e.end_vid] = e.weight

    # Dynamic programming part of Floyd-Warshall algorithm.
    # Note: Although road_network.vertex_set is a hash map, statement "for k in road_network.vertex_set" actually equals
    # to "for k from 1 to |V|" where |V| is the size of the vertex set, if the id of the vertex is consecutive. That is,
    # the iteration of dict() is ordered.

    for k in road_network.vertex_set:
        for i in road_network.vertex_set:
            for j in road_network.vertex_set:
                if dist[i][j] > dist[i][k] + dist[k][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]

    print("Done. Elapsed time is %f. seconds" % (time.clock() - start_time))

    return dist


def single_source_dijkstra(road_network, start):
    """
    Compute the shortest paths from a vertex, whose id is start, to all other vertices using Dijkstra's algorithm.

    :param road_network: RoadNetwork
    :param start: int
    :return: dict[int, int]
        the "came from" array
    """
    import time
    start_time = time.clock()

    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = dict()
    cost_so_far = dict()
    came_from[start] = None
    cost_so_far[start] = 0

    while not frontier.empty():
        current = frontier.get()
        for neighbor in road_network.get_neighbors(current):
            new_cost = cost_so_far[current] + road_network.get_weight(current, neighbor)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost    # relax
                priority = new_cost
                frontier.put(neighbor, priority)
                came_from[neighbor] = current

    print("Elapsed time is %f seconds." % (time.clock() - start_time))

    return came_from

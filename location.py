"""
Author: Huafan Li <fanfan199308@gmail.com>

Date: 2016/12/09

Description: This module contains the abstraction for the geographical location on the earth and some utilities for
GeoComputing.

"""


from geohash import geo_encode
from constants import R, PRECISION
import math


class Location:
    def __init__(self, lat, lon):
        """
        Initialize a location.

        The Location class is the abstraction of a geographical position on the earth.

        :param lat: float
            latitude of a location
        :param lon: float
            longitude of a location
        :return: None
        """
        self.lat = lat
        self.lon = lon
        self.geohash = geo_encode(lat, lon, PRECISION)

    def __str__(self):
        """
        Return a string representation.

        :return: str

        >>> location = Location(39.564540, 115.739662)
        >>> print(location)
        (39.56454, 115.739662)
        >>> print(location.geohash)
        wx431
        """
        return "({}, {})".format(self.lat, self.lon)

    def __eq__(self, other):
        """
        Return True if self equals other, and false otherwise.

        :param other: Location
        :return: bool

        >>> pos_a = Location(39.564540, 115.739662)
        >>> pos_b = Location(39.564540, 115.739662)
        >>> pos_a == pos_b
        True
        """
        return self.lat == other.lat and self.lon == other.lon


def get_distance(pos_a, pos_b):
    """
    Compute the distance between two location in meters.

    :param pos_a: Location
    :param pos_b: Location
    :return: float

    >>> pos_a = Location(39.564540, 115.739662)
    >>> pos_b = Location(39.564540, 115.739662)
    >>> pos_c = Location(39.533867, 115.746735)
    >>> print(get_distance(pos_a, pos_b))
    0.0
    >>> print(get_distance(pos_a, pos_c))
    3464.17661119
    """
    x1 = math.radians(pos_a.lat)
    y1 = math.radians(pos_a.lon)
    x2 = math.radians(pos_b.lat)
    y2 = math.radians(pos_b.lon)
    temp = math.cos(x1) * math.cos(x2) * math.cos(y1 - y2) + math.sin(x1) * math.sin(x2)
    if temp > 1.000:
        temp = 1.0
    elif temp < -1.000:
        temp = -1.0
    dis = R * math.acos(temp)
    return dis


def bearing(pos_a, pos_b):
    """
    Compute the bearing (direction angle) between two location in degrees.

    Please resort to the following web page for the detailed tutorial:
    http://www.igismap.com/formula-to-find-bearing-or-heading-angle-between-two-points-latitude-longitude/

    :param pos_a: from location
    :param pos_b: to location
    :type pos_a: Location
    :type pos_b: Location
    :return: the bearing from pos_a to pos_b in radians
    :rtype: float

    >>> pos_a = Location(39.46696, 116.03663)
    >>> pos_b = Location(38.35996, 114.03663)
    >>> print(bearing(pos_a, pos_b))
    -2.17808092766
    """
    lat_a = math.radians(pos_a.lat)
    lon_a = math.radians(pos_a.lon)
    lat_b = math.radians(pos_b.lat)
    lon_b = math.radians(pos_b.lon)

    d_lon = lon_b - lon_a
    y = math.cos(lat_b) * math.sin(d_lon)
    x = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * math.cos(lat_b) * math.cos(d_lon)
    theta = math.atan2(y, x)
    return theta


def end_pos(start_pos, theta, d):
    """
    Find out the other point, given the starting point, the bearing and actual distance.

    Please resort to the following web page for the detailed tutorial:
    http://www.igismap.com/formula-to-find-bearing-or-heading-angle-between-two-points-latitude-longitude/

    :param start_pos: the starting point
    :param theta: the bearing in radians
    :param d: the actual distance (whose unit is the same as the radius of the Earth)
    :return: the other point
    :type start_pos: Location
    :type theta: float
    :type d: float
    :rtype: Location

    >>> start_pos = Location(39.564540, 115.739662)
    >>> theta = 2.96558662977
    >>> d = 3464.17661119
    >>> print end_pos(start_pos, theta, d)
    (39.533867, 115.746735)
    >>> start_pos = Location(40.103722, 116.425209)
    >>> theta = -3.128233061823583
    >>> d = 7
    >>> print end_pos(start_pos, theta, d)
    (40.1036590531, 116.4252079)
    """
    lat_start = math.radians(start_pos.lat)
    lon_start = math.radians(start_pos.lon)
    ad = d / R  # the angular distance

    lat = math.asin(math.sin(lat_start) * math.cos(ad) + math.cos(lat_start) * math.sin(ad) * math.cos(theta))
    lon = lon_start + math.atan2(math.sin(theta) * math.sin(ad) * math.cos(lat_start),
                                 math.cos(ad) - math.sin(lat_start) * math.sin(lat))

    return Location(math.degrees(lat), math.degrees(lon))

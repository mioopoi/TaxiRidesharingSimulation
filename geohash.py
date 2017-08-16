"""
Author: Huafan Li <fanfan199308@gmail.com>

Date: 2016/12/09

Description: This module contains the utilities for the encoding and decoding of GeoHash.

=== Constants ===
BASE32: list
    A list used for base32 encoding and decoding of GeoHash
"""

BASE32 = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'b', 'c', 'd', 'e', 'f', 'g',
          'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']


def geo_encode(lat, lon, precision):
    global BASE32

    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    length = precision * 5  # the demand length of binary code
    geohash = ""
    bits = 0
    for i in range(1, length + 1):
        if not(i % 2 == 0):  # odd: lon
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                bits = bits * 2 + 1  # binary code is set to 1
                lon_interval[0] = mid  # update the corresponding interval
            else:
                bits *= 2  # binary code is set to 0
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                bits = bits * 2 + 1
                lat_interval[0] = mid
            else:
                bits *= 2
                lat_interval[1] = mid
        if i % 5 == 0:
            geohash += BASE32[bits]
            bits = 0  # reset binary code
    return geohash


def geo_decode(geohash):
    global BASE32

    odd = True
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    for char in geohash:
        bits = BASE32.index(char)
        for j in range(4, -1, -1):
            bit = (bits >> j) & 1
            if odd:
                mid = (lon_interval[0] + lon_interval[1]) / 2
                lon_interval[1-bit] = mid
            else:
                mid = (lat_interval[0] + lat_interval[1]) / 2
                lat_interval[1-bit] = mid
            odd = not odd
    lat = (lat_interval[0] + lat_interval[1]) / 2
    lon = (lon_interval[0] + lon_interval[1]) / 2
    return [lat, lon]

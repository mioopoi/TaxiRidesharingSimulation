"""
Date of creation: 2016/12/22

Description: This module contains some utilities used in this project.

"""


from datetime import datetime


def sim_time_convert(time_str):
    """
    Convert a time string to int time used in the simulation.

    :param time_str: the time str with format '%H:%M:%S'
    :type time_str: str
    :return: accumulated seconds from the beginning of a day
    :rtype: int
    """
    day_start_time = datetime.strptime("00:00:00", '%H:%M:%S')
    sim_time = (datetime.strptime(time_str, '%H:%M:%S') - day_start_time).seconds + 1
    return sim_time

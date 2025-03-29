"""
The helpers module provides useful utility functions to the main application code.
"""
import math

def format_net_timespan(time: int) -> str:
    """
    Formats a given millisecond time into a .net-compliant timespan stamp.
    
    Parameters:
    time (int): A duration in milliseconds.

    Returns:
    str: A .net-compliant timespan stamp.
    """
    hours = math.floor((time / 1000 / 60 / 60))
    minutes = math.floor((time - (hours * 60 * 60 * 1000)) / 1000 / 60)
    seconds = math.floor((time - (hours * 60 * 60 * 1000) - (minutes * 60 * 1000)) / 1000)
    millis = (time - (hours * 60 * 60 * 1000) - (minutes * 60 * 1000) - (seconds * 1000))
    micros = millis * 1000

    return f"{hours}:{minutes}:{seconds}.{micros}"

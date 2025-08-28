# -*- coding: utf-8 -*-
"""
utils.py

This module provides utility functions and classes 
"""

import logging
import pyproj

def detect_delimiter(filepath):
    """
    Detects the delimiter of a CSV or TXT file by reading the first few lines.
    Args:
        filepath (str): Path to the file.
    Returns:
        str: Detected delimiter (comma or tab).
    """
    try:
        with open(filepath, 'r') as file:
            lines = [file.readline() for _ in range(5)]
        comma_count = sum(line.count(',') for line in lines)
        tab_count = sum(line.count('\t') for line in lines)
        return ',' if comma_count > tab_count else '\t'
    except Exception as e:
        logging.error(f"Error detecting delimiter: {e}")
        return ','
    
def transform_coords_to_WGS84(input_epsg):

    transformer = pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", "EPSG:4326", always_xy=True)

    return transformer
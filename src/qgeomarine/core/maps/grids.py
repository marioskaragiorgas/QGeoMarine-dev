"""
Grids.py
"""
import numpy as np
from scipy.interpolate import griddata
import logging

def grid(x, y, z, method, resolution):
    try:
            x = x.astype(float).values
            y = y.astype(float).values
            z = z.astype(float).values

            resolution = resolution
            method = method

            # Define grid range
            xi = np.linspace(np.nanmin(x), np.nanmax(x), resolution)
            yi = np.linspace(np.nanmin(y), np.nanmax(y), resolution)
            grid_x, grid_y = np.meshgrid(xi, yi)

            # Interpolate
            grid_z = griddata((x, y), z, (grid_x, grid_y), method=method)

            # Handle NaNs
            grid_z = np.nan_to_num(grid_z, nan=0.0)
            
            return grid_x, grid_y, grid_z, xi, yi
    
    except Exception as e:
            logging.error("Error", f"Gridding failed:\n{e}")
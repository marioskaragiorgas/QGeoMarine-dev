"""
I/O for seismic & magnetic data.
Keeps imports light and exposes the common entry points.
"""
from .seismic_io import SEGY          # if your class is named SEGY
from .magy_io import MAGGY            # class from mag_io.py (your snippet)

__all__ = ["SEGY", "MAGGY"]

"""
NNavigation.py

This module provides utilities for handling navigation data in marine geophysical surveys,
specifically for sub-bottom profiler (SBP) operations. It supports navigation data extraction
from both SEG-Y files and external GPS-based sources.

Classes:
    - NavigationFromTowFish: Parses navigation data embedded in SEG-Y trace headers.
    - NavigationFromShip: Parses external navigation files (e.g., CSV, TXT, NAV, P190) and 
      computes the coordinates of the towed SBP based on ship data and towing parameters.

Overview:
---------
Marine surveys often involve towing geophysical instruments like SBP devices behind the vessel.
Since the ship's GPS records the position of the antenna (usually mounted at the bow), it's
necessary to calculate the actual coordinates of the towed equipment using geometry and
navigation principles.

This module implements two main workflows:

1. NavigationFromTowFish
    - Extracts embedded navigation (X, Y) values directly from the SEG-Y headers.
    - Returns a list of geographic coordinates (typically in EPSG:4326).

2. NavigationFromShip
    - Loads navigation logs from external sources (CSV, TXT, Excel, etc.).
    - Applies geometric corrections to estimate SBP location from the ship’s track using
      cable length, operating depth, and sheave offset.

Layback Calculation:
--------------------
To determine the horizontal offset (layback) of the SBP behind the ship, the following formulas are used:

    Let:
        L = Cable length (meters)
        D = Depth of SBP below water (meters)
        S = Sheave offset from GPS antenna to cable deployment point (meters)

    1. Compute horizontal layback (Lx) using the Pythagorean theorem:
        Lx = sqrt(L² - D²)

    2. Total offset from GPS antenna to SBP:
        Offset = S + Lx

    3. Apply ship heading (θ in radians) to compute SBP coordinates:
        X_sbp = X_ship + Offset * cos(θ)
        Y_sbp = Y_ship + Offset * sin(θ)

This approach ensures the calculated position of the SBP accounts for towing geometry and
ship orientation, enabling more accurate mapping and data correlation.

"""
import numpy as np
import pandas as pd
import segyio
from matplotlib import pyplot as plt
from qgeomarine.utils.utils import detect_delimiter, transform_coords_to_WGS84

class NavigationFromTowFish:
    """
    Handles the navigation data processing from SEG-Y files. 
    This class extracts source and receiver coordinates from the SEG-Y file trace headers 
    and assigns geometry (source-receiver offsets) to the traces.
    
    Attributes:

        source_coords (list): List to store source coordinates [(X_s, Y_s), ...].

        receiver_coords (list): List to store receiver coordinates [(X_r, Y_r), ...].

        distance (None): Placeholder for storing distances, if needed.

        segyfile (segyio.SegyFile): The opened SEG-Y file.
    """

    def __init__(self):
        self.source_coords = []  # Initialize empty list for source coordinates
        self.receiver_coords = []  # Initialize empty list for receiver coordinates
        self.distance = None
        self.segyfile = None

    def load_Nav_data_from_segyfile(self, segy_file_path):
        """
        Load navigation data directly from the SEG-Y file headers, including source and receiver coordinates.

        Parameters:
        - segy_file_path (str): Path to the SEG-Y file.

        Returns:
        - source_coords (list): List of source coordinates [(X_s, Y_s), ...].
        - receiver_coords (list): List of receiver coordinates [(X_r, Y_r), ...].

        Raises:
        - Exception: If the SEG-Y file cannot be read or coordinates cannot be extracted.
        """
        try:
            with segyio.open(segy_file_path, 'r', ignore_geometry=True) as segyfile:
                
                segyfile.mmap()

                # Header words for Source X and Y (default SEG-Y positions)
                source_x = []
                source_y = []
                receiver_x = []
                receiver_y = []
                    
                for trace_header in segyfile.header:
                    x_s = trace_header[segyio.TraceField.SourceX]
                    y_s = trace_header[segyio.TraceField.SourceY]
                    x_r = trace_header[segyio.TraceField.GroupX]
                    y_r = trace_header[segyio.TraceField.GroupY]
                    # Append to lists
                    source_x.append(x_s)
                    source_y.append(y_s)
                    receiver_x.append(x_r)
                    receiver_y.append(y_r)

                # Remove Nan ar zero values
                source_x = [x for x in source_x if x != 0]
                source_y = [y for y in source_y if y != 0]
                receiver_x = [x for x in receiver_x if x != 0]
                receiver_y = [y for y in receiver_y if y != 0]

                """
                # Print extracted coordinates
                print("Source X Coordinates:", source_x)
                print("Source Y Coordinates:", source_y)
                print("Receiver X Coordinates:", receiver_x)
                print("Receiver Y Coordinates:", receiver_y)
                """

                self.source_coords = zip(source_x, source_y)
                self.receiver_coords = zip(receiver_x, receiver_y)

                return self.source_coords #, self.receiver_coords
        
        except Exception as e:
            raise Exception(f"Cannot extract the SEG-Y file coordinates: {e}")    

    def assign_geometry(self, segy_file_path, source_coords, receiver_coords):
        """
        Assign geometry (source-receiver offsets) to the SEG-Y file's trace headers.

        Parameters:
        - segy_file_path (str): Path to the SEG-Y file.
        - source_coords (list): List of source coordinates [(X_s, Y_s), ...].
        - receiver_coords (list): List of receiver coordinates [(X_r, Y_r), ...].

        Returns:
        - segyfile (segyio.SegyFile): The SEG-Y file with assigned geometry.

        Raises:
        - ValueError: If the trace count does not match the number of source or receiver coordinates.
        """
        with segyio.open(segy_file_path, "r+", ignore_geometry=True) as segyfile:
            n_traces = segyfile.tracecount
            if n_traces != len(source_coords) or n_traces != len(receiver_coords):
                raise ValueError("Mismatch between trace count and number of source/receiver coordinates")

            for trace_idx in range(n_traces):
                X_s, Y_s = source_coords[trace_idx]
                X_r, Y_r = receiver_coords[trace_idx]
                offset = np.sqrt((X_r - X_s)**2 + (Y_r - Y_s)**2)  # Calculate offset
                X_cmp = (X_s + X_r) / 2  # Midpoint X (CMP)
                Y_cmp = (Y_s + Y_r) / 2  # Midpoint Y (CMP)

                # Write source, receiver, and offset to trace headers
                segyfile.header[trace_idx][segyio.TraceField.SourceX] = X_s
                segyfile.header[trace_idx][segyio.TraceField.SourceY] = Y_s
                segyfile.header[trace_idx][segyio.TraceField.GroupX] = X_r
                segyfile.header[trace_idx][segyio.TraceField.GroupY] = Y_r
                segyfile.header[trace_idx][segyio.TraceField.offset] = int(offset)

            print("Geometry assignment completed!")
            self.segyfile = segyfile
            return self.segyfile


class NavigationFromShip:
    """
    Handles the navigation data processing from the ship's navigation files.
    This class supports loading navigation data from various file formats 
    (CSV, Excel, NAV, P190) and computes sub-bottom profiler (SBP) source 
    coordinates based on cable length, offset, and depth.

    This class also includes the analytical procedure to calculate the SBP coordinates 
    from the ship's GPS coordinates based on the following steps:

    1. Calculate the layback using the Pythagorean theorem.

    2. Add the sheave offset to find the total horizontal offset.

    3. Adjust the ship's GPS coordinates based on the heading and total offset to 
       calculate the SBP's X, Y coordinates.

    Attributes:
        
        source_coords (list): List to store calculated SBP source coordinates.

        receiver_coords (list): List to store calculated SBP receiver coordinates.

        nav_data (DataFrame): DataFrame to hold the loaded navigation data.

    """

    def __init__(self):
        self.source_coords = []
        self.receiver_coords = []
        self.nav_data = None  # DataFrame to store ship navigation data
        self.segy_file_path = None

    def load_navigation_data(self, nav_file_path):
        """
        Load navigation data from .csv, .xlsx, .txt, .nav, or .p190 file formats.

        Parameters:
        - nav_file_path (str): Path to the navigation file.

        Returns:
        - nav_data (DataFrame): Loaded navigation data in a pandas DataFrame.

        Raises:
        - Exception: If the file cannot be loaded.
        """
        try:
            if nav_file_path.endswith('.csv') or nav_file_path.endswith('.CSV'):
                self.nav_data = pd.read_csv(nav_file_path)

            elif nav_file_path.endswith('.xlsx') or nav_file_path.endswith('.xls'):
                self.nav_data = pd.read_excel(nav_file_path)

            elif nav_file_path.endswith('.txt'):
                self.nav_data = pd.read_csv(nav_file_path, sep=" ")

            elif nav_file_path.endswith('.nav') or nav_file_path.endswith('.NAV'):
                with open(nav_file_path, 'r') as file:
                    lines = file.readlines()

                data = []
                for line in lines:
                    parts = line.split()
                    shot_number = int(parts[0])
                    x_coord = float(parts[1])
                    y_coord = float(parts[2])
                    other_params = ','.join(parts[3:])
                    data.append([shot_number, None, x_coord, y_coord, other_params])

                self.nav_data = pd.DataFrame(data, columns=['shot_number', 'time', 'x_coord', 'y_coord', 'other_params'])

            elif nav_file_path.endswith('.p190') or nav_file_path.endswith('.P190'):
                with open(nav_file_path, 'r') as file:
                    lines = file.readlines()

                data = []
                for line in lines:
                    shot_number = int(line[0:6].strip())
                    time = line[7:16].strip()
                    x_coord = float(line[17:25].strip())
                    y_coord = float(line[26:34].strip())
                    other_params = line[35:].strip()
                    data.append([shot_number, time, x_coord, y_coord, other_params])

                self.nav_data = pd.DataFrame(data, columns=['shot_number', 'time', 'x_coord', 'y_coord', 'other_params'])

            else:
                raise ValueError("Unsupported file format. Please select a valid file.")

            print("Success: Data loaded successfully.")
            return self.nav_data

        except Exception as e:
            raise Exception(f"Error loading data: {e}")

    def calculate_total_offset(self, row):
        """
        Calculate the total horizontal offset (layback + sheave offset) for each row in the DataFrame.

        This method reads the `cable_length`, `depth`, and `sheave_offset` directly from the 
        DataFrame and calculates the total offset.

        Parameters:
        - row (pd.Series): A row from the DataFrame containing navigation data (cable_length, depth, and sheave_offset).

        Returns:
        - total_offset (float): Total horizontal offset from the ship's GPS to the SBP (towfish).
        """
        cable_length = row['cable_length']  # Cable length (in meters) from the DataFrame
        depth = row['depth']  # Depth of the SBP (in meters)
        sheave_offset = row['sheave_offset']  # Horizontal distance from ship GPS to the sheave

        # Calculate layback using the Pythagorean theorem
        layback = self.calculate_layback(cable_length, depth)

        # Total offset is the sheave offset + layback
        total_offset = sheave_offset + layback
        return total_offset

    def calculate_layback(self, cable_length, depth):
        """
        Calculate the layback (horizontal distance) using the Pythagorean theorem.

        Parameters:
        - cable_length (float): Total length of cable paid out (in meters).
        - depth (float): Depth of the towed equipment (in meters).

        Returns:
        - layback (float): Horizontal distance (layback).
        """
        if cable_length < depth:
            raise ValueError("Cable length must be greater than depth to apply the Pythagorean theorem.")
        layback = np.sqrt(cable_length**2 - depth**2)
        return layback

    def calculate_heading(self, gps_coords1, gps_coords2):
        """
        Calculate the ship's heading based on two GPS points.

        Parameters:
        - gps_coords1 (tuple): First GPS point (X, Y).
        - gps_coords2 (tuple): Second GPS point (X, Y).

        Returns:
        - heading (float): Heading in radians.
        """
        X1, Y1 = gps_coords1
        X2, Y2 = gps_coords2
        heading = np.arctan2(Y2 - Y1, X2 - X1)
        return heading

    def calculate_sbp_coords(self, ship_gps_coords, total_offset, ship_heading):
        """
        Calculate the SBP source coordinates based on the ship's GPS position and heading.

        Parameters:
        - ship_gps_coords (tuple): Ship's GPS coordinates (X, Y).
        - total_offset (float): Total horizontal offset from ship to SBP.
        - ship_heading (float): Ship's heading in radians.

        Returns:
        - (X_sbp, Y_sbp): Calculated SBP source coordinates.
        """
        X_ship, Y_ship = ship_gps_coords
        X_sbp = X_ship + total_offset * np.cos(ship_heading)
        Y_sbp = Y_ship + total_offset * np.sin(ship_heading)
        return X_sbp, Y_sbp
    def assign_sbp_coords_to_segy(self, segy_file_path, sbp_coords):
            """
            Assign the SBP source coordinates to the SEG-Y file headers.

            Parameters:
            - segy_file_path (str): Path to the SEG-Y file.
            - sbp_coords (list): List of SBP source coordinates [(X_sbp, Y_sbp), ...].
            
            The SBP coordinates are assigned to the trace headers as `SourceX` and `SourceY`.
            """
            try:
                # Open the SEG-Y file in read/write mode
                with segyio.open(segy_file_path, "r+", ignore_geometry=True) as segyfile:
                    n_traces = segyfile.tracecount
                    
                    # Ensure the number of SBP coordinates matches the number of traces
                    if len(sbp_coords) != n_traces:
                        raise ValueError("Mismatch between trace count and number of SBP coordinates.")
                    
                    # Loop through each trace and assign the SBP coordinates
                    for trace_idx in range(n_traces):
                        X_sbp, Y_sbp = sbp_coords[trace_idx]
                        
                        # Assign the SBP coordinates to the trace headers
                        segyfile.header[trace_idx][segyio.TraceField.SourceX] = int(X_sbp)
                        segyfile.header[trace_idx][segyio.TraceField.SourceY] = int(Y_sbp)
                        
                        # Optionally: Calculate and assign the offset if receiver coordinates are available
                        if len(self.receiver_coords) == n_traces:
                            X_r, Y_r = self.receiver_coords[trace_idx]
                            offset = np.sqrt((X_r - X_sbp)**2 + (Y_r - Y_sbp)**2)
                            segyfile.header[trace_idx][segyio.TraceField.offset] = int(offset)

                print("SBP coordinates successfully assigned to SEG-Y file headers!")
            
            except Exception as e:
                raise Exception(f"Error assigning SBP coordinates to SEG-Y file: {e}")

    def ship_to_sbp_nav(self, navigation_df, segyfile):
        """
        Convert the ship's navigation data to SBP (towfish) navigation and assign coordinates to SEG-Y file.

        This method reads the `cable_length`, `depth`, and `sheave_offset` directly from the DataFrame and 
        calculates the SBP coordinates for each navigation point.

        Returns:
        - ship_gps_df (DataFrame): DataFrame with calculated SBP positions.
        - sbp_coords (list): SBP source coordinates.
        """
        ship_gps_df = navigation_df
        segy_file_path = self.segy_file_path
        sbp_coords = []

        # Loop through the navigation DataFrame and calculate SBP coordinates for each entry
        for i in range(len(ship_gps_df) - 1):
            # Get ship GPS coordinates for the current point and the next one
            gps_coords1 = (ship_gps_df['X_ship'][i], ship_gps_df['Y_ship'][i])
            gps_coords2 = (ship_gps_df['X_ship'][i+1], ship_gps_df['Y_ship'][i+1])

            # Calculate total offset using the row's cable_length, depth, and sheave_offset
            total_offset = self.calculate_total_offset(ship_gps_df.iloc[i])

            # Calculate the ship's heading between the current and next point
            if 'Heading' in ship_gps_df.columns:
                heading = ship_gps_df['Heading'][i]
            else:
                heading = self.calculate_heading(gps_coords1, gps_coords2)

            # Calculate SBP coordinates based on ship GPS, total offset, and heading
            sbp_coord = self.calculate_sbp_coords(gps_coords1, total_offset, heading)
            sbp_coords.append(sbp_coord)

        # Store the calculated SBP coordinates in the DataFrame
        ship_gps_df['X_sbp'], ship_gps_df['Y_sbp'] = zip(*sbp_coords)

        # Assign SBP coordinates to SEG-Y headers
        self.assign_sbp_coords_to_segy(segy_file_path, sbp_coords)

        # Return the updated DataFrame and the list of SBP coordinates
        return ship_gps_df, sbp_coords


    def plot_ship_sbp_positions(self, ship_gps_df):
        """
        Plot the ship's track and the SBP (towfish) track.

        Parameters:
        - ship_gps_df (DataFrame): DataFrame containing ship and SBP coordinates.
        """
        plt.figure(figsize=(10, 6))
        plt.plot(ship_gps_df['X_ship'], ship_gps_df['Y_ship'], label='Ship Track', color='blue')
        plt.plot(ship_gps_df['X_sbp'], ship_gps_df['Y_sbp'], label='SBP Track', color='red')
        plt.xlabel('X Coordinate (m)')
        plt.ylabel('Y Coordinate (m)')
        plt.title('Ship and SBP Positions')
        plt.legend()
        plt.grid()
        plt.show()

class NavigationFromFile:

    def __init__(self):
        self.coords_data = {} 
        self.file_path = None
        
    def load_navigation_data(self, file_path, line_col, x_col, y_col, input_epsg):
        """
        Load and transform coordinates grouped by line.
        """
        try:
            self.file_path = file_path

            if str(file_path).endswith((".csv", ".txt")):
                delimiter = detect_delimiter(file_path)
                df = pd.read_csv(file_path, delimiter=delimiter)
            elif str(file_path).endswith((".xls", ".xlsx")):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                raise ValueError("Unsupported file format")

            # EPSG to WGS84
            transformer = transform_coords_to_WGS84(input_epsg)

            # Group by line and store transformed coordinates
            grouped = df.groupby(line_col)
            self.coords_data = {
                 line: [transformer.transform(x, y) for x, y in zip(group[x_col], group[y_col])]
                 for line, group in grouped
            }

            return self.coords_data
        except Exception as e:
            raise Exception(f"Error loading navigation from {file_path}: {e}")
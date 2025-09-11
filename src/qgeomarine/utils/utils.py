# -*- coding: utf-8 -*-
"""
utils.py

This module provides utility functions and classes 
"""

import logging
import pyproj
import sqlite3
import zlib 
import numpy as np
import multiprocessing as mp

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
    """
    Transforms coordinates from a given EPSG to WGS84 (EPSG:4326).
    Args:
        input_epsg (int): EPSG code of the input coordinate system.
    Returns:
        pyproj.Transformer: Transformer object to convert coordinates to WGS84.
    """
    transformer = pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", "EPSG:4326", always_xy=True)

    return transformer

def compress_trace(trace):
    """Helper function to compress seismic trace using zlib.
    Parameters:
        trace (np.ndarray): The seismic trace data as a NumPy array.
    Returns:
        bytes: The compressed trace data as a byte string.
    """
    # Convert to binary
    binary_trace = trace.astype(np.float32).tobytes()
    return zlib.compress(binary_trace)

class DatabaseManager:
    """Class to manage SQLite database connections and operations.
    Parameters:
        db_file_path (str): Path to the SQLite database file.
    Methods:
        establish_connection(): Establish a connection to the database.
        close_connection(conn): Close the given database connection.
        execute_query(query, params=None): Execute a query on the database.
        fetch_query(query, params=None): Fetch data from the database.
        decompress_data(compressed_blob): Decompress seismic trace data.
        compress_data(trace): Compress seismic trace data.
    """
    def __init__(self, db_file_path):
        self.db_file_path = db_file_path

    def establish_connection(self):
        try:
            conn = sqlite3.connect(self.db_file_path)
            return conn
        except sqlite3.Error as e:
            logging.error(f"Error connecting to the database: {e}")
            return None   
        
    def close_connection(self, conn):
        if conn is not None:
            conn.close()
            logging.info("Database connection closed successfully.")
        else:
            logging.error("Connection is already closed.")      

    def execute_query(self, query, params=None):
        """
        Execute a query on the database using the provided query and parameters.
        Parameters:
            query (str): The SQL query to execute.
            params (tuple): The parameters to pass to the query.
        """
        conn = self.establish_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                cursor.close()
                self.close_connection(conn)
            except sqlite3.Error as e:
                logging.error(f"Error executing query: {e}")
        else:
            logging.error("Error: Unable to establish a connection to the database.")

    def executemany_query(self, query, sequence, params=None):
        """
        Execute many times a query on the database using the provided query and parameters.
        Parameters:
            query (str): The SQL query to execute.
            params (tuple): The parameters to pass to the query.
        """
        conn = self.establish_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                if params is not None:
                    cursor.executemany(query, sequence, params)
                else:
                    cursor.executemany(query, sequence)
                conn.commit()
                cursor.close()
                self.close_connection(conn)
            except sqlite3.Error as e:
                logging.error(f"Error executing query: {e}")
        else:
            logging.error("Error: Unable to establish a connection to the database.")

    def fetch_query(self, query, params=None):
        """
        Fetch data from the database using the provided query and parameters.
        Parameters:
            query (str): The SQL query to execute.
            params (tuple): The parameters to pass to the query.
        Returns:
            list: The fetched data as a list of tuples.
        """
        conn = self.establish_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                self.close_connection(conn)
                return result
            except sqlite3.Error as e:
                logging.error(f"Error fetching query: {e}")
        else:
            logging.error("Error: Unable to establish a connection to the database.")

    def decompress_data(self, compressed_blob):
        """Decompress seismic trace data and return a NumPy array of float32 values."""
        decompressed_bytes = zlib.decompress(compressed_blob)

        # Convert bytes directly into a NumPy array (float32)
        return np.frombuffer(decompressed_bytes, dtype=np.float32)

    
    def compress_data(self, trace):
         # Step 1: Process data before interacting with SQLite
        with mp.Pool(mp.cpu_count()) as pool:
            compressed_trace = pool.map(compress_trace(compressed_trace), trace)  # Process before SQLite
            return compressed_trace
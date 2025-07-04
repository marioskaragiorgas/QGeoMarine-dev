"""
Data_handling.py

This module is designed to handle the loading, processing, and saving of seismic data from SEG-Y files. 
It uses two primary libraries: `segyio` for efficient handling of SEG-Y files and `obspy` for reading 
seismic data formats. The module provides functionality to:
  - Load seismic data using either `segyio` or `obspy`.
  - Extract basic seismic metadata such as sample rate, number of traces, and two-way travel time (TWT).
  - Save processed seismic data back to SEG-Y format.
  - Close any open seismic files gracefully.

Classes:
    SEGYHandler: Handles loading, saving, and processing seismic data from SEG-Y files.
"""
import sys
import pandas as pd
import segyio
import obspy
import sqlite3
import zlib
import logging
import os
import multiprocessing as mp
import numpy as np 
import gc
import re

logging.basicConfig(
    level=logging.DEBUG,      
    format='%(levelname)s: %(message)s',
    stream=sys.stdout
    )

def compress_trace(trace):
    """Helper function to compress seismic trace using zlib."""
    # Convert to binary
    binary_trace = trace.astype(np.float32).tobytes()
    return zlib.compress(binary_trace)

class SEISMIC:
    class SEGYHandler:
        def __init__(self, db_file_path, bin_file_path):
            self.db_file_path = db_file_path
            self.bin_file_path = bin_file_path
            self.segyio_file = None
            self.stream = None
            self.spec = None
            
        def create_database(self):
            """Create tables in the SQLite database for SEGY metadata storage."""
            try:
                with sqlite3.connect(self.db_file_path) as conn:
                    cursor = conn.cursor()
                    cursor.executescript('''
                        CREATE TABLE IF NOT EXISTS textual_headers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            header_line TEXT
                        );
                        CREATE TABLE IF NOT EXISTS binary_headers (
                            key TEXT PRIMARY KEY,
                            value INTEGER
                        );
                        CREATE TABLE IF NOT EXISTS trace_headers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            trace_number INTEGER,
                            field_record INTEGER,
                            shot_point INTEGER,
                            cdp INTEGER,
                            cdp_x REAL,
                            cdp_y REAL,
                            source_x REAL,
                            source_y REAL,
                            group_x REAL,
                            group_y REAL,
                            offset INTEGER
                        );
                        CREATE TABLE IF NOT EXISTS binary_file (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            binfile_path TEXT NOT NULL
                        );
                    ''')
                    conn.commit()
                    logging.info("Database tables created successfully.")
            except sqlite3.Error as e:
                logging.error(f"Error creating database tables: {e}")

        def insert_textual_headers(self, segyfile):
            """Insert segy textual headers into the database."""
            try:
                textual_header = segyio.tools.wrap(segyfile.text[0])
                with sqlite3.connect(self.db_file_path) as conn:
                    conn.executemany("INSERT INTO textual_headers (header_line) VALUES (?)", 
                                     [(line.strip(),) for line in textual_header.splitlines()])
                    conn.commit()
                    logging.info("Textual headers inserted successfully.")
            except sqlite3.Error as e:
                logging.error(f"Error inserting textual headers: {e}")

        def insert_binary_headers(self, segyfile):
            """Insert segy binary headers into the database."""
            try:
                with sqlite3.connect(self.db_file_path) as conn:
                    conn.executemany("INSERT INTO binary_headers (key, value) VALUES (?, ?)",
                                     [(str(k), v) for k, v in segyfile.bin.items()])
                    conn.commit()
                    logging.info("Binary headers inserted successfully.")
            except sqlite3.Error as e:
                logging.error(f"Error inserting binary headers: {e}")
    
        def insert_trace_headers(self, segyfile):
            """Insert trace headers in small batches and return a trace_id_map."""
            try:
                with sqlite3.connect(self.db_file_path) as conn:
                    cursor = conn.cursor()

                    def header_generator():
                        for i in range(segyfile.tracecount):
                            yield (
                                int(segyfile.attributes(segyio.TraceField.TraceNumber)[i][0]),
                                int(segyfile.attributes(segyio.TraceField.FieldRecord)[i][0]),
                                int(segyfile.attributes(segyio.TraceField.ShotPoint)[i][0]),
                                int(segyfile.attributes(segyio.TraceField.CDP)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.CDP_X)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.CDP_Y)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.SourceX)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.SourceY)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.GroupX)[i][0]),
                                float(segyfile.attributes(segyio.TraceField.GroupY)[i][0]),
                                int(segyfile.attributes(segyio.TraceField.offset)[i][0])
                            )

                    # Insert trace headers into the database
                    cursor.executemany("""
                        INSERT INTO trace_headers 
                        (trace_number, field_record, shot_point, cdp, cdp_x, cdp_y, source_x, source_y, group_x, group_y, offset)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, header_generator())

                    conn.commit()
                    logging.info("Trace Headers inserted successfully.")

            except sqlite3.Error as e:
                logging.error(f"Error inserting trace headers: {e}")
                return None

        def insert_trace_data(self, segyfile, bin_filepath):
            """
            Store trace data in binary format and save the file path in SQLite.
            :param segyfile: The SEG-Y file being read.
            :param bin_filepath: Path to the binary file.
            """
            try:

                logging.info(f"Storing trace data in binary file {bin_filepath}.")

                # Extract trace data from the SEG-Y file
                trace_data = segyfile.trace.raw[:]  # Assuming this returns a 2D array
                trace_data = trace_data.astype(np.float32)  # Ensure it's in float32 format

                # Check the shape of the trace data
                if not isinstance(trace_data, np.ndarray):
                    logging.error("Trace data is not a numpy array.")
                    return

                # Log the shape of the data
                logging.info(f"Trace data shape: {trace_data.shape}")

                # Write the data to a binary file
                with open(bin_filepath, 'wb') as binary_file:
                    trace_data.tofile(binary_file)

                logging.info(f"Trace data successfully stored in {bin_filepath}.")

            except ValueError as ve:
                logging.error(f"Value error: {ve}")
            except IOError as ioe:
                logging.error(f"I/O error: {ioe}")
            except Exception as e:
                logging.error(f"Error storing trace data: {e}")

            try:
                # Insert all trace paths into SQLite at once
                with sqlite3.connect(self.db_file_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO binary_file (binfile_path) VALUES (?)", (bin_filepath,))
                    conn.commit()

                logging.info("Binary file path recorded in SQLite.")

            except sqlite3.Error as e:
                logging.error(f"Error storing binary file path: {e}")

        def get_bin_filepath(self):
            """Retrieve the HDF5 file path from the SQLite database."""
            try:
                with sqlite3.connect(self.db_file_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT binfile_path FROM binary_file")
                    result = cursor.fetchone()
                    if result:
                        return result[0]  # File path
                    else:
                        logging.error("No binary file path found in the database.")
                        return None
            except sqlite3.Error as e:
                logging.error(f"Error retrieving binary file path: {e}")
                return None

        def load_traces_from_bin(self):
            """Retrieve all seismic traces from the seismic binary file."""
            bin_path = self.get_bin_filepath()
            
            if not bin_path:
                logging.error("Binary file path not found. Cannot load traces.")
                return None

            try:
                with sqlite3.connect(self.db_file_path) as conn:
                    cursor = conn.cursor()
                        
                    # Fetch the number of traces
                    cursor.execute("SELECT COUNT(id) FROM trace_headers")
                    trace_num = cursor.fetchone()
                    n_traces = trace_num[0] if trace_num else 0
                    
                    # Fetch the number of samples
                    cursor.execute("SELECT key, value FROM binary_headers Where key = 'Samples'")
                    samples = cursor.fetchall()
                    n_samples = samples[0][1] if samples else 0
                    
                    conn.commit()
                    
                    # Read the data from the binary file
                    trace_data = np.memmap(filename=bin_path, dtype=np.float32, mode='r', shape=(n_traces, n_samples))

                    # Check if the loaded data size matches the expected size
                    expected_size = n_traces * n_samples
                    
                    if trace_data.size != expected_size:
                        logging.error(f"Loaded data size {trace_data.size} does not match expected size {expected_size}.")
                        
                        # Reshape the trace data array to the correct dimensions
                        trace_data = trace_data.reshape((n_traces, n_samples))
                        logging.info(f"Trace data successfully loaded from {bin_path}. Shape: {trace_data.shape}")
                        return trace_data
                    
                    else:
                        logging.info(f"Trace data successfully loaded from {bin_path}. Shape: {trace_data.shape}")
                        return trace_data
                    
            except Exception as e:
                logging.error(f"Error loading trace data: {e}")
                return None

        def load_data_segyio(self, file_path):
            """
            Load seismic data from a SEG-Y file using Segyio, insert the metadata
            to the seismic database and create the binary file containing the seismic traces.
            """
            logging.info(f"Opening the seismic file '{file_path}' with Segyio library.")

            try:
                if not file_path or not os.path.exists(file_path):
                    raise FileNotFoundError(f"The file '{file_path}' does not exist.")

                with segyio.open(file_path, 'r', ignore_geometry=True) as segyfile:
                    
                    spec = segyio.tools.metadata(segyfile)
                    n_traces = segyfile.tracecount
                    sample_interval = segyfile.bin[segyio.BinField.Interval] / 1e6  # Convert to seconds
                    sample_rate = 1 / sample_interval
                    n_samples = segyfile.samples.size
                    twt = segyfile.samples
                    data_format = segyfile.format
                    self.n_traces = n_traces
                    self.n_samples = n_samples

                    logging.info(f"Number of Traces: {n_traces}, Sample Rate: {sample_rate} Hz")

                    self.create_database()
                    self.insert_textual_headers(segyfile)
                    self.insert_binary_headers(segyfile)
                    self.insert_trace_headers(segyfile)
                    self.insert_trace_data(segyfile, self.bin_file_path)

                    return segyfile, spec, n_samples, twt, data_format, sample_interval, sample_rate

            except Exception as e:
                logging.error(f"Error opening SEG-Y file: {e}")
                return None # Ensure calling function doesn't break on unpacking

        def load_data_obspy(self, file_path):
            logging.info("Opening the seismic file with Obspy.")
            try:
                self.stream = obspy.read(file_path, format='segy')
                trace = self.stream[0]
                return self.stream, trace.data.dtype
            except Exception as e:
                logging.error(f"Error loading file with ObsPy: {e}")

        def close_file(self, filepath, seismicdata):
            """Saves processed seismic data to the database and closes the file."""
            if self.segyio_file:
                try:
                    # Step 1: Process data before interacting with SQLite
                    with mp.Pool(mp.cpu_count()) as pool:
                        compressed_traces = pool.map(compress_trace, seismicdata)  # Process before SQLite
                        
                    with sqlite3.connect(filepath) as conn:
                            try:

                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM trace_data")  # Clear old data
                                
                                # Insert processed data
                                cursor.executemany("INSERT INTO trace_data (compressed_data) VALUES (?)", 
                                                [(ct,) for ct in compressed_traces])
                                
                                # Ensure index exists (only if trace_id exists)
                                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON trace_data (trace_id)")

                                conn.commit()  # Save changes
                                logging.info("Database updated sucessfully")
                            
                            except sqlite3.Error as e:
                                logging.error(f"Error saving data to database file: {e}")
    

                    # Step 2: Close SEG-Y file
                    if hasattr(self.segyio_file, 'close'):
                        self.segyio_file.close()
                        self.segyio_file = None

                

                    # Step 3: Clear any remaining stream references
                    if self.stream:
                        self.stream.clear()
                        self.stream = None

                    # Step 4: Cleanup memory
                    del seismicdata
                    gc.collect()
                    logging.info("File closed successfully.")

                except Exception as e:
                    logging.error(f"Error closing the seismic file: {e}")

        def save_segy_file(self, file_path, file_spec, save_data):
            
            """
            Save processed seismic data back to a SEG-Y file.

            Parameters:
                file_path (str): The output path where the SEG-Y file will be saved.
                file_spec (dict): The SEG-Y file specification (metadata) to be used for the saved file.
                save_data (ndarray): The seismic data that will be written into the SEG-Y file.

            Returns:
                segyio.SegyFile: The saved SEG-Y file object.

            Raises:
                ValueError: If the file cannot be saved due to an error.
            """
            try:
                with segyio.create(file_path, file_spec) as dst_file:
                    self.dst_segyfile = dst_file
                    dst_file.trace = save_data
                    
                    return self.dst_segyfile
                
            except (ValueError, IndexError, Exception) as e:
                raise ValueError(f"Error saving SEG-Y file: {e}")    

class MAGGY:

    class CSV_TXT_XLS:
        """
        Load data from a CSV, TXT, or XLS file into a Pandas DataFrame.
        Create a database from the DataFrame containing a table for each magnetic line number.
        """

        def __init__(self, mag_db_file_path, Line_column_name, table_prefix="line_"):
            self.mag_db_file_path = mag_db_file_path 
            self.Line_column_name = Line_column_name
            self.table_prefix = table_prefix  # Allows user-defined table prefixes

        def detect_delimiter(self, filepath):
            """ Detects the delimiter (comma or tab) in a text file. """
            try:
                with open(filepath, 'r') as file:
                    lines = [file.readline() for _ in range(5)]
                comma_count = sum(line.count(',') for line in lines)
                tab_count = sum(line.count('\t') for line in lines)
                return ',' if comma_count > tab_count else '\t'
            except Exception as e:
                logging.error(f"Error detecting delimiter: {e}")
                return ','  # Default to comma

        def preview_data(self, filepath):
            """Preview the first 5 lines of the file."""
            try:
                file_ext = filepath.lower().split('.')[-1]  # Get file extension

                with open(filepath, 'r') as file:
                    if file_ext == "csv":
                        df = pd.read_csv(file, nrows=5)
                    elif file_ext == "txt":
                        delimiter = self.detect_delimiter(filepath)
                        df = pd.read_csv(file, delimiter=delimiter, nrows=5)
                    elif file_ext in ["xls", "xlsx"]:
                        df = pd.read_excel(filepath, engine='openpyxl', nrows=5)

                    elif file_ext in ["ascii", "asc"]:
                        df = pd.read_csv(file, sep="\s+", header=None, nrows=5)

                    else:
                        logging.error("Unsupported file format.")
                        return None
                # check all the header columns for spaces replace them with _ or special characters like [],(), etc. and remove them
                df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in df.columns]
                return df

            except Exception as e:
                logging.error(f"Error previewing data: {e}")
                return None
            
        def load_files(self, filepath):
            """ Load data from a file and create an SQLite database with magnetic line tables. """
            try:
                file_ext = filepath.lower().split('.')[-1]  # Get file extension

                with open(filepath, 'r') as file:
                    if file_ext == "csv":
                        self.df = pd.read_csv(file, low_memory=False)
                    elif file_ext == "txt":
                        delimiter = self.detect_delimiter(filepath)
                        self.df = pd.read_csv(file, delimiter=delimiter, low_memory=False) 
                    elif file_ext in ["xls", "xlsx"]:
                        self.df = pd.read_excel(filepath, engine='openpyxl')

                    elif file_ext in "[ascii, asc]":
                        self.df = pd.read_csv(file, sep="\s+", header=None, low_memory=False)
                        
                    else:
                        logging.error("Unsupported file format.")
                        return None
                    
                    # check all the header columns for spaces replace them with _ or special characters like [],(), etc. and remove them
                    self.df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in self.df.columns]

                logging.info(f"File '{filepath}' loaded successfully.")

            except Exception as e:
                logging.error(f"Error loading file: {e}")
                return None

            # Check if column exists
            if self.Line_column_name not in self.df.columns:
                logging.error(f"Column '{self.Line_column_name}' not found in data.")
                return None

            try:
                with sqlite3.connect(self.mag_db_file_path) as conn:
                    self.df.to_sql('magnetic_data', conn, if_exists='replace', index=False)
                    logging.info("Main table 'magnetic_data' created.")
                    
                    # Add Index for Faster Queries
                    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.Line_column_name} ON magnetic_data({self.Line_column_name})")
            
                    # Group data by Line_column_name
                    grouped = self.df.groupby(self.Line_column_name)

                    # Process groups sequentially 
                    for line_number, group in grouped:
                        table_name = f"{self.table_prefix}{re.sub(r'[^a-zA-Z0-9_]', '_', str(line_number))}"
                        group.to_sql(table_name, conn, if_exists='replace', index=False)
                        logging.info(f"Table '{table_name}' created.")

            except sqlite3.Error as e:
                logging.error(f"Database error: {e}")
                return None
            
        def save_data(self, output_path):
            if self.db is not None:
                try:
                    if output_path.endswith('.csv'):
                        self.db.to_csv(output_path, index=False)
                    elif output_path.endswith('.xlsx'):
                        self.db.to_excel(output_path, index=False, engine='openpyxl')
                    elif output_path.endswith('.txt'):
                        self.db.to_csv(output_path, sep='\t', index=False)  # Save as tab-delimited text
                    else:
                        raise ValueError("Unsupported file format. Please specify a .csv, .xlsx, or .txt file.")
                except Exception as e:
                    raise Exception(f"Error occurred while saving the data: {e}")
            else:
                raise ValueError("No data to save. Please load data first.")


class DatabaseManager:
    def __init__(self, db_file_path):
        self.db_file_path = db_file_path

    def enstablish_connection(self):
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
        conn = self.enstablish_connection()
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
        conn = self.enstablish_connection()
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
        conn = self.enstablish_connection()
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
        
class ExportData:
    """ 
    Export data to different formats. 
    param: data: The data to be exported.
    param: output_path: The path to save the exported data.
    """

    def __init__(self, data, output_path, db_file_path):
        self.data = data
        self.output_path = output_path
        self.db_file_path = db_file_path

    def load_metadata_from_db(self):
        """Load SEG-Y metadata (binary headers, trace headers) from SQLite database."""
        try:
            with sqlite3.connect(self.db_file_path) as conn:
                cursor = conn.cursor()
                
                # Load binary headers
                cursor.execute("SELECT key, value FROM binary_headers")
                binary_headers = {row[0]: int(row[1]) for row in cursor.fetchall()}

                # Load trace headers
                cursor.execute("""
                    SELECT trace_number, field_record, shot_point, cdp, cdp_x, cdp_y, 
                        source_x, source_y, group_x, group_y, offset 
                    FROM trace_headers
                """)
                trace_headers = cursor.fetchall()

                return binary_headers, trace_headers

        except sqlite3.Error as e:
            print(f"Error loading metadata from database: {e}")
            return None, None
        
    def export_segy(self):
        """Export seismic data to SEG-Y format."""
        # Load metadata and trace data
        binary_headers, trace_headers = self.load_metadata_from_db()
        trace_data = self.data

        if binary_headers is None or trace_data is None:
            print("Failed to retrieve necessary data. Aborting SEG-Y export.")
            return

        # Ensure trace count matches
        n_traces, n_samples = trace_data.shape
        if len(trace_headers) != n_traces:
            print(f"Warning: Number of traces in database ({len(trace_headers)}) does not match NumPy array ({n_traces})")

        # Define SEG-Y file structure
        spec = segyio.spec()
        spec.ilines = range(n_traces)
        spec.xlines = [1]  # Since it's 2D, set crossline as 1 else if 3D, set to range(n_traces)
        spec.format = 1  # IEEE Floating Point
        spec.samples = range(n_samples)
        spec.tracecount = n_traces

        try:

            # Create and write SEG-Y file
            with segyio.create(self.output_path, spec) as segyfile:

                """Generate a SEG-Y textual header with 40 lines."""
                text_header = {i: f"C{i:2}  This is line {i} of the SEG-Y header." for i in range(1, 41)}
                textual_header = segyio.create_text_header(text_header)
                segyfile.text[0] = textual_header

                # Write binary headers
                for key, value in binary_headers.items():
                    segyfile.bin[key] = value

                # Write trace headers and trace data
                for i, trace in enumerate(trace_data):
                    trace_number, field_record, shot_point, cdp, cdp_x, cdp_y, \
                        source_x, source_y, group_x, group_y, offset = trace_headers[i]

                    # Assign trace headers
                    segyfile.header[i] = {
                        segyio.TraceField.TraceNumber: trace_number,
                        segyio.TraceField.FieldRecord: field_record,
                        segyio.TraceField.ShotPoint: shot_point,
                        segyio.TraceField.CDP: cdp,
                        segyio.TraceField.CDP_X: cdp_x,
                        segyio.TraceField.CDP_Y: cdp_y,
                        segyio.TraceField.SourceX: source_x,
                        segyio.TraceField.SourceY: source_y,
                        segyio.TraceField.GroupX: group_x,
                        segyio.TraceField.GroupY: group_y,
                        segyio.TraceField.offset: offset,
                        #segyio.TraceField.Inline: trace_number,  # Inline number
                        #segyio.TraceField.Crossline: 1  # Since it's 2D, crossline stays fixed
                    }

                    # Assign trace data
                    segyfile.trace[i] = trace

                logging.info(f"Data successfully exported to SEG-Y file: {self.output_path}")

        except Exception as e:
            logging.error(f"Error exporting data to SEG-Y file: {e}")

    def export_su(self):
        """Export seismic data to SU format."""
        
        pass

    def export_image(self, delta ,filename):
        """Export seismic data to image format."""
        try:
            import matplotlib.pyplot as plt
        except ImportError: 
            logging.error("Matplotlib is not installed. Please install it to export data to image format.")
            return
        n_traces, n_samples = self.data.shape
    
        # Compute the time axis for the seismic image (in milliseconds)
        time_axis = np.arange(0, n_samples * delta, delta)
        fig, ax = plt.subplots(figsize=(10, 6))
        img = ax.imshow(self.data.T, cmap='seismic', aspect='auto', interpolation='bicubic', extent=[0, n_traces, time_axis[-1], time_axis[0]])  # Time axis on y-axis
        ax.set_xlabel("Trace Number")
        ax.set_ylabel("Two-Way Travel Time (ms)")
        ax.set_title(f"Seismic Section of {filename} line")
        fig.colorbar(img, label="Amplitude Polarity") 

        fig.savefig(self.output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        logging.info(f"Data successfully exported to image file: {self.output_path}")



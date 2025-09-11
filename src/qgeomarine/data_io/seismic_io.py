"""seismic_io.py
This module handles the input and output operations for seismic data files.
It provides functions to read and write seismic data in various formats,
including SEGY and other common formats used in geophysical data processing.

Key Functions:
- read_seismic_data(file_path): Reads seismic data from a SEGY file.
- write_seismic_data(file_path, data): Writes seismic data to a SEGY file.
- convert_segy_to_other_format(input_path, output_path): Converts SEGY data to another format.
- convert_other_format_to_segy(input_path, output_path): Converts data from another format to SEGY.
"""

import sys
import segyio
import obspy
import sqlite3
import logging
from pathlib import Path
import multiprocessing as mp
import numpy as np 
import gc
from qgeomarine.utils.utils import compress_trace


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout
    )


class SEGY:
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
        """Retrieve the binary file path from the SQLite database."""
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
            if not file_path or not Path(file_path).exists():
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
            
        finally:
            if self.dst_segyfile:
                self.dst_segyfile.close()
                self.dst_segyfile = None

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
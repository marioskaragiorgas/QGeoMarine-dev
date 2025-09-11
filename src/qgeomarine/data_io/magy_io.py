"""
magy_io.py

"""

import pandas as pd
import sqlite3
import logging
import sys
import re
from qgeomarine.utils.utils import detect_delimiter

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout
    )

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


        def preview_data(self, filepath):
            """Preview the first 5 lines of the file."""
            try:
                file_ext = filepath.lower().split('.')[-1]  # Get file extension

                with open(filepath, 'r') as file:
                    if file_ext == "csv":
                        df = pd.read_csv(file, nrows=5)
                    elif file_ext == "txt":
                        delimiter = detect_delimiter(filepath)
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
                        delimiter = detect_delimiter(filepath)
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
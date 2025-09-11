"""
Seismic Editor.py

This module provides a GUI application for seismic data editing and analysis.
It allows users to load seismic data, apply various processing techniques, and visualize the results.
"""

import sys
from pathlib import Path
import gc
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QVBoxLayout, QWidget, QSplitter,
    QSizePolicy, QInputDialog, QMessageBox, QToolBar, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QDialog, QGridLayout, QLineEdit, QPushButton
)
from PyQt6.QtCore import pyqtSlot, QSize, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QAction
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib import pyplot as plt
from qgeomarine.utils.utils import DatabaseManager
from qgeomarine.data_io import seismic_io as SEISMIC
from qgeomarine.data_io import magy_io as MAGY
from qgeomarine.core.signals.filters import IIR_Filters, FIR_Filters
from qgeomarine.core.signals.mute import Mute, PredefinedMute
from qgeomarine.core.signals.gains import agc_gain, tvg_gain, constant_gain
from qgeomarine.visualizatiuon.plots import  plot_seismic_image, plot_spectrogram, plot_wavelet_transform
from qgeomarine.core.processing.trace_analysis import trace_periodogram, trace_welch_periodogram, trace_wavelet_transform, trace_spectrogram, instantaneous_attributes
from qgeomarine.core.signals.deconvolution import Wavelets, Deconvolution
from qgeomarine.core.processing.trace_qc import TraceQC
from qgeomarine.core.interpretation.interpretation import SeismicInterpretationWindow
from qgeomarine.ui.ui import bandass_filter_UI, highpass_filter_UI, lowpass_filter_UI, TraceAnalysisWindowUI, WaveletWindowUI, TraceQCUI

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)

class FileParseWorker(QThread):
    """
    Worker thread for parsing seismic files in the background.
    This class handles the parsing of seismic data from a file and emits signals when finished or if an error occurs.
    It retrieves the sample interval, sample rate, data format, and trace data from the seismic database.
    It uses the SEISMIC.SEGYHandler to load traces from a binary file.
    Attributes:
        finished (pyqtSignal): Signal emitted when parsing is finished.
        error (pyqtSignal): Signal emitted when an error occurs during parsing.
        file_path (str): Path to the seismic database file to be parsed.
        segy_handler (SEISMIC.SEGYHandler): Handler for reading seismic data from the binary file.

    Methods:
        run(): The main method that runs in the background thread to parse the seismic file.
            It retrieves the sample interval, sample rate, data format, and trace data, and emits the results.
        It handles exceptions and emits error messages if any issues occur during parsing.
    """

    finished = pyqtSignal(object)  # Signal to emit when parsing is finished
    error = pyqtSignal(str)        # Signal to emit when an error occurs

    def __init__(self, file_path):
        """
        Initializes the FileParseWorker with the given file path.
        Args:
            file_path (str): Path to the seismic database file to be parsed.
        """
        super().__init__()
        self.file_path = file_path
        self.segy_handler = SEISMIC.SEGY(db_file_path=self.file_path, bin_file_path=None)

    def run(self):
        """
        The main method that runs in the background thread to parse the seismic file.
        It retrieves the sample interval, sample rate, data format, and trace data from the seismic database.
        It emits the results when parsing is finished or emits an error message if any issues occur.
        This method is executed when the thread is started.
        """

        try:
            logging.info(f"Starting to parse file: {self.file_path}")
            seismic_database = DatabaseManager(self.file_path)

            # Run queries to retrieve sample interval
            sample_interval_query = "SELECT key, value FROM binary_headers WHERE key = 'Interval'"
            sample_interval_result = seismic_database.fetch_query(sample_interval_query)

            # Check if sample interval exists
            if sample_interval_result and len(sample_interval_result) > 0:
                sample_interval = sample_interval_result[0][1] / 1e6  # Convert to seconds
            else:
                raise ValueError("Sample interval not found in the database.")

            sample_rate = 1 / sample_interval

            # Retrieve data format
            data_format_query = "SELECT key, value FROM binary_headers WHERE key = 'Format'"
            data_format_result = seismic_database.fetch_query(data_format_query)

            if data_format_result and isinstance(data_format_result, list) and len(data_format_result) > 0:
                data_format = data_format_result[0][1]
            else:
                data_format = "Unknown"

            # Load the binary file path containing the seismic traces
            trace_data = self.segy_handler.load_traces_from_bin()
            if trace_data is None:
                raise ValueError("Failed to load trace data.")

            # Emit the result when done
            result = {
                'trace_data': trace_data,
                'sample_interval': sample_interval,
                'sample_rate': sample_rate,
                'data_format': data_format
            }
            self.finished.emit(result)

        except Exception as e:
            logging.error(f"Error during file parsing: {e}")
            self.error.emit(str(e))

class ProcessWorker(QThread):
    """
    Worker thread for applying processing techniques to seismic data.
    This class handles the application of various processing methods to seismic data in the background.
    It emits signals when the processing is finished or if an error occurs.
    Attributes:
        finished (pyqtSignal): Signal emitted when processing is finished.
        error (pyqtSignal): Signal emitted when an error occurs during processing.
        progress (pyqtSignal): Signal to report progress (optional).
        process_func (callable): The processing function to apply to the seismic data.
        data (np.ndarray): The seismic data to process.
        args (tuple): Additional arguments for the processing function.
    Methods:
        run(): The main method that runs in the background thread to apply the processing function to the seismic data.
            It applies the processing function to the entire data (2D array) or trace by trace, depending
            on the function type. It emits the processed result when finished or emits an error message if any issues occur.
    """
    
    finished = pyqtSignal(object)  # Signal to emit when processing method is finished
    error = pyqtSignal(str)        # Signal to emit when an error occurs
    progress = pyqtSignal(int)      # Signal to report progress (optional)

    def __init__(self, process_func, data, *args):
        """
        Initializes the ProcessWorker with the processing function, seismic data, and additional arguments.
        Args:
            process_func (callable): The processing function to apply to the seismic data.
            data (np.ndarray): The seismic data to process.
            *args: Additional arguments for the processing function.
        """

        super().__init__()
        self.process_func = process_func
        self.data = data
        self.args = args

    def run(self):
        """
        The main method that runs in the background thread to apply the processing function to the seismic data.
        It applies the processing function to the entire data (2D array) or trace by trace, depending on the function type.
        It emits the processed result when finished or emits an error message if any issues occur.
        This method is executed when the thread is started.
        It checks if the provided process_func is callable and applies the processing technique accordingly.
        If the process_func is one of the F-K filter or Wiener Deconvolution, it applies it to the entire data.
        Otherwise, it applies the function trace by trace and emits progress updates.
        """
        try:
            if not callable(self.process_func):
                raise ValueError("The provided process_func is not callable.")

            if self.process_func in (FIR_Filters.fk_filter, Deconvolution.wiener_deconvolution):
                # Apply the F-K filter and Wiener Deconvolution processing methods to the entire data (2D array)
                result = self.process_func(self.data, *self.args)
            else:
                # Apply other methods trace by trace    
                result = np.array([self.process_func(trace, *self.args) for trace in self.data])
                # Optionally report progress
                for i, trace in enumerate(self.data):
                    self.progress.emit(int((i + 1) / len(self.data) * 100))  # Emit progress as a percentage

            self.finished.emit(result)
        except Exception as e:
            logging.error(f"Processing technique application failed: {e}")
            self.error.emit(str(e))


class SeismicEditor(QMainWindow):
    """
    Main class for the Seismic Editor application.
    This class initializes the main window, sets up the UI components, and handles file parsing, data processing,
    and various seismic data analysis techniques.
    It provides a GUI for loading seismic data, applying processing techniques, and visualizing the results.
    Attributes:
        seismic_filepath (str): Path to the seismic file to be loaded.
        db_file_path (str): Path to the seismic database file (SQLite).
        parent (QWidget): Parent widget for the main window.
    Methods:
        __init__(seismic_filepath, db_file_path, parent=None): Initializes the SeismicEditor with the given file paths and parent widget.
        init_ui(): Initializes the main UI components, including the central widget, tree view, and plot area.
        create_menus(): Creates the application menus and submenus for various seismic data processing techniques.
        create_toolbar(): Creates the application toolbar with actions for importing files.
        show_error(title, message): Displays an error message dialog with the given title and message.
        create_side_panel(): Creates a side panel for additional functionality (not implemented).
        start_file_parsing(file_path): Starts the file parsing in a separate thread to load seismic data.
        on_parsing_finished(result): Handles the result of the parsing, updates the UI, and plots the seismic data.
        on_parsing_error(error_message): Handles errors during parsing and updates the UI with the error message.
        parse_file(file_path): Parses the seismic database file and retrieves metadata and trace data.
        export_file(): Exports the seismic file to a selected output format (e.g., SEG-Y, SU, image).
        close_file(): Closes the currently open seismic file, clears displayed data, and updates the database.
        plot_raw_seismic_image(): Plots the seismic image from the raw data.
        plot_processed_seismic_image(): Plots the seismic image from the processed data.
    """

    def __init__(self, seismic_filepath, db_file_path, parent = None):
        """
        Initializes the SeismicEditor with the given file paths and parent widget.
        Args:
            seismic_filepath (str): Path to the seismic file to be loaded.
            db_file_path (str): Path to the seismic database file (SQLite).
            parent (QWidget, optional): Parent widget for the main window. Defaults to None.
        """

        super().__init__(parent)
        self.init_ui()
        self.create_menus()
        self.create_toolbar()
        self.seismic_filepath = seismic_filepath
        self.db_file_path = db_file_path
        self.segy_handler = SEISMIC.SEGY(db_file_path=db_file_path, bin_file_path=None)
        self.mute_functions = Mute(self)
        self.segy_file = None
        self.spec = None
        self.data = None # Raw seismic data
        self.processed_data = None  # Processed seismic data
        self.sample_interval = None 
        self.sample_rate = None
        self.interpretation_window = None
        
        # Check if the file path is valid before parsing
        if db_file_path:
            print(f"Database path: {db_file_path}")
            self.start_file_parsing(file_path= db_file_path)
            
        else:
            logging.error("Invalid seismic database path provided.")
            self.data_info_label.setText("Invalid seismic database path provided.")

    def init_ui(self):
        """
        Initialize the main UI components of the Seismic Editor application.
        This method sets up the main window, creates a central widget, and adds a splitter to separate the tree view
        and the plot area. It also creates a tree view to display opened seismic files and a plot area for visualizing seismic data.
        It sets the window title and resizes the central widget.
        """

        self.setWindowTitle("Seismic Editor")

        # Create central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.central_widget.resize(1000, 800)

        # Create a splitter for TreeView (left) and plot area (right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self.central_widget)

        # Treeview widget to display opened Seismic files
        self.treeview = QTreeWidget()
        self.treeview.setHeaderLabel("Opened Seismic Files")
        self.treeview_root = QTreeWidgetItem(self.treeview)
        self.treeview_root.setText(0, "Loaded Files")

        # Add Treeview to the splitter
        splitter.addWidget(self.treeview)

        # Create right side (plot area) of the splitter
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Data info label for showing loaded data info
        self.data_info_label = QLabel("No Data Loaded")
        right_layout.addWidget(self.data_info_label)

        # Matplotlib figure for displaying plots
        self.figure = plt.Figure(figsize=(30, 10))
        self.ax = self.figure.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.canvas)

        # Add Matplotlib Navigation Toolbar for zooming and panning
        self.toolbar = NavigationToolbar(self.canvas, self)
        right_layout.addWidget(self.toolbar)

        # Add the right widget (plot area) to the splitter
        splitter.addWidget(right_widget)
        
        # Set initial sizes for the splitter (TreeView gets less space)
        splitter.setSizes([150, 750])  # Adjust these values as needed

        # Main layout for the window, which includes the splitter
        layout = QHBoxLayout(self.central_widget)
        layout.addWidget(splitter)

    def create_menus(self):
        """Create application menus and submenus."""

        # Create the menu bar
        self.menu_bar = self.menuBar()

        # File menu
        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction(self.create_action("Export as...", self.export_file))
        file_menu.addAction(self.create_action("Save and Quit", self.close_file))

        # Trace Analysis menu
        self.trace_menu = self.menu_bar.addMenu("Trace Analysis")
        self.add_trace_menu_action("Trace Analysis Window", self.TraceAnalysisWin)
    
        # Deconvolution menu 
        deconvolution_menu = self.menu_bar.addMenu("Deconvolution")
        deconvolution_menu.addAction(self.create_action("Spiking", self.apply_spiking_dec))
        deconvolution_menu.addAction(self.create_action("Predictive", self.apply_predictive_dec))
        deconvolution_menu.addAction(self.create_action("Wiener", self.apply_wiener_dec))

        # Interpretation menu
        interpretation_menu = self.menu_bar.addMenu("Interpretation")
        interpretation_menu.addAction(self.create_action("Horizon Picking", self.apply_Horizon_pick))

        # Preprocessing menu
        preprocessing_menu = self.menu_bar.addMenu("Pre-processing/Quality Control (QC)")
        # QC action
        preprocessing_menu.addAction(self.create_action("Trace QC", self.apply_trace_qc))
        # Mute submenu
        mute_submenu = preprocessing_menu.addMenu("Trace Muting")
        mute_functions_submenu = mute_submenu.addMenu("Mutting Functions")
        mute_functions_submenu.addAction(self.create_action("Top Mute", self.apply_top_mute))
        mute_functions_submenu.addAction(self.create_action("Bottom Mute", self.apply_bottom_mute))
        #mute_functions_submenu.addAction(self.create_action("Offset Mute", self.apply_offset_mute))
        mute_functions_submenu.addAction(self.create_action("Time Variant Mute", self.apply_time_variant_mute))
        mute_functions_submenu.addAction(self.create_action("User Interactive Mute", self.apply_userinteractive_mute))
        mute_predifined_functions_submenu = mute_submenu.addMenu("Predifined Mutting Functions")
        mute_predifined_functions_submenu.addAction(self.create_action("Shallow Zone Mute ", self.apply_SZ_mute))
        mute_predifined_functions_submenu.addAction(self.create_action("Deep Zone Mute ", self.apply_DZ_mute))
        mute_predifined_functions_submenu.addAction(self.create_action("Direct Wave Mute ", self.apply_DW_mute))
        # Fitlering submenu
        filter_submenu = preprocessing_menu.addMenu("Trace Filtering")
        IIR_filter_submenu = filter_submenu.addMenu("IIR Filters")
        butterworth_menu = IIR_filter_submenu.addMenu("Butterworth")
        butterworth_menu.addAction(self.create_action("Bandpass Filter", self.apply_butter_bandpass_filter))
        butterworth_menu.addAction(self.create_action("Highpass Filter", self.apply_butter_highpass_filter))
        butterworth_menu.addAction(self.create_action("Lowpass Filter", self.apply_butter_lowpass_filter))
        cheby_menu = IIR_filter_submenu.addMenu("Chebyshev")
        cheby_menu.addAction(self.create_action("Bandpass Filter", self.apply_cheby_bandpass_filter))
        cheby_menu.addAction(self.create_action("Highpass Filter", self.apply_cheby_highpass_filter))
        cheby_menu.addAction(self.create_action("Lowpass Filter", self.apply_cheby_lowpass_filter))
        FIR_filter_submenu = filter_submenu.addMenu("FIR Filters")
        FIR_filter_submenu.addAction(self.create_action("Bandpass Filter", self.apply_fir_bandpass_filter))
        FIR_filter_submenu.addAction(self.create_action("Highpass Filter", self.apply_fir_highpass_filter))
        FIR_filter_submenu.addAction(self.create_action("Lowpass Filter", self.apply_fir_lowpass_filter))
        FIR_filter_submenu.addAction(self.create_action("F-K Filter", self.apply_fk_filter))
        FIR_filter_submenu.addAction(self.create_action("Zero Phase Filter", self.apply_zero_phase_filter))
        FIR_filter_submenu.addAction(self.create_action("Wavelet Filter", self.apply_wavelet_filter))
        # Gain submenu
        gain_submenu = preprocessing_menu.addMenu("Gains")
        gain_submenu.addAction(self.create_action("AGC Gain", self.agc_gain))
        gain_submenu.addAction(self.create_action("TVG Gain", self.tvg_gain))
        gain_submenu.addAction(self.create_action("Constant Gain", self.const_gain))

    def create_action(self, name, method):
        """Helper function to create a QAction."""
        action = QAction(name, self)
        action.triggered.connect(method)
        return action

    def add_trace_menu_action(self, name, method):
        """Add an action to the Trace Analysis menu."""
        action = self.create_action(name, method)
        self.trace_menu.addAction(action)

    def create_toolbar(self):
        """Create application toolbar."""
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(36)

        # Specify the path to your icon file
        open_file_icon_path = Path(__file__).resolve().parent.parent.parent.parent /"resources" / "images" / "mIconFolderOpen.png"

        # Create the QIcon object
        open_file_icon = QIcon(open_file_icon_path)

        # Create the QAction with the icon and connect it to the function
        import_file_action = QAction(open_file_icon, "Import file", self)
        

        # Add the action to the toolbar
        self.toolbar.addAction(import_file_action)
        self.addToolBar(self.toolbar)

    def show_error(self, title, message):
        """
        Show an error message dialog with the given title and message.
        """
        QMessageBox.critical(self, title, message)

    def start_file_parsing(self, file_path):
        """
        Initiates parsing of the specified file in a separate thread.

        This method updates the UI to indicate that data is being loaded, creates a worker thread to parse the file,
        and connects the worker's signals to appropriate handler methods for completion and error events.

        Args:
            file_path (str): The path to the file to be parsed.
        """
        self.data_info_label.setText("Loading data...")  # Update UI to indicate loading
        self.worker = FileParseWorker(file_path)
        self.worker.finished.connect(self.on_parsing_finished)
        self.worker.error.connect(self.on_parsing_error)
        self.worker.start()  # Start the worker thread

    def on_parsing_finished(self, result):
        """
        Handles the completion of the seismic data parsing process.
        Updates internal data attributes with the parsed results, refreshes UI elements to display
        information about the loaded seismic data, and updates the tree view with file and data details.
        Finally, triggers plotting of the raw seismic image.
        
        Args:
            result (dict): A dictionary containing parsed seismic data and metadata with keys:
                - 'trace_data': numpy.ndarray, the seismic trace data.
                - 'sample_interval': float, the sample interval in seconds.
                - 'sample_rate': float, the sample rate in Hz.
                - 'data_format': str, the format of the seismic data.
        """

        self.data = result['trace_data']
        self.sample_interval = result['sample_interval']
        self.sample_rate = result['sample_rate']
        data_format = result['data_format']

        # Update UI elements
        n_traces = self.data.shape[0] if self.data is not None else 0
        samples_per_trace = self.data.shape[1] if self.data is not None and self.data.ndim > 1 else 0

        self.data_info_label.setText(f"Loaded {n_traces} traces from {self.db_file_path} (SQLite)")

        # Add the file to the treeview
        file_item = QTreeWidgetItem(self.treeview_root)
        file_item.setText(0, Path(self.db_file_path).name)

        # Update TreeView with trace count and sample interval
        sample_interval_ms = self.sample_interval * 1e3  # Convert to milliseconds
        sample_rate_khz = self.sample_rate / 1e3  # Convert to kHz

        trace_item = QTreeWidgetItem(file_item)
        trace_item.setText(0, f"Number of Traces: {n_traces}")
        sample_item = QTreeWidgetItem(file_item)
        sample_item.setText(0, f"Samples: {samples_per_trace}")
        sample_interval_item = QTreeWidgetItem(file_item)
        sample_interval_item.setText(0, f"Sample Interval: {sample_interval_ms:.2f} ms")
        sample_rate_item = QTreeWidgetItem(file_item)
        sample_rate_item.setText(0, f"Sample Rate: {sample_rate_khz:.2f} kHz")
        format_item = QTreeWidgetItem(file_item)
        format_item.setText(0, f"Data Format: {data_format}")

        # Plot the seismic data
        self.plot_raw_seismic_image()

    def on_parsing_error(self, error_message):
        """Handle errors during parsing."""
        logging.error(f"Parsing error: {error_message}")
        self.data_info_label.setText(f"Error loading data: {error_message}")

    def parse_file(self, file_path):
        """
        Parses a seismic database file, extracts metadata, loads seismic trace data, and updates the UI accordingly.
        
        Args:
            file_path (str): The path to the seismic database file (SQLite).
        
        Workflow:
            - Logs the start of the parsing process.
            - Validates the provided file path.
            - Initializes a DatabaseManager instance to interact with the database.
            - Retrieves the sample interval from the binary headers and computes the sample rate.
            - Retrieves the data format from the binary headers.
            - Loads seismic trace data using the segy_handler.
            - Logs and validates the shape of the loaded trace data.
            - Updates UI elements with metadata such as number of traces, samples per trace, sample interval, sample rate, and data format.
            - Adds the file and its metadata to a tree view for display.
            - Plots the raw seismic data.
        Raises:
            ValueError: If required metadata (e.g., sample interval) or trace data is missing or invalid.
            Exception: For any other errors encountered during file parsing or data loading.
        
        Side Effects:
            - Updates UI labels and tree view items.
            - Logs information and errors.
            - Plots seismic data.
        """

        if not file_path:
            logging.error("No file path provided")
            return

        print(f"Database path: {file_path}")
        try:
            # Create an instance of DatabaseManager and parse the file
            seismic_database = DatabaseManager(file_path)

            # Run queries
            sample_interval_query = "SELECT key, value FROM binary_headers WHERE key = 'Interval'"
            sample_interval_result = seismic_database.fetch_query(sample_interval_query)

            # Check if sample interval exists
            if sample_interval_result and len(sample_interval_result) > 0:
                self.sample_interval = sample_interval_result[0][1] / 1e6  # Convert to seconds
            else:
                raise ValueError("Sample interval not found in the database.")

            self.sample_rate = 1 / self.sample_interval

            # Ensure data format retrieval is safe
            data_format_query = "SELECT key, value FROM binary_headers WHERE key = 'Format'"
            data_format_result = seismic_database.fetch_query(data_format_query)

            # Debugging: Log the result of the data format query
            logging.info(f"Data format query result: {data_format_result}")

            # Check if data_format_result is valid
            if data_format_result and isinstance(data_format_result, list) and len(data_format_result) > 0:
                data_format = data_format_result[0][1]
            else:
                data_format = "Unknown"

            # Retrieve the binary file path containing the seismic traces
            trace_data = self.segy_handler.load_traces_from_bin()
            self.data = trace_data

            # Debugging: Log the shape of the loaded trace data
            if self.data is not None:
                logging.info(f"Trace data shape: {self.data.shape}")
            else:
                logging.error("Trace data is None.")

            # Metadata for display
            n_traces = self.data.shape[0] if self.data is not None else 0
            samples_per_trace = self.data.shape[1] if self.data is not None and self.data.ndim > 1 else 0

            # Check if n_traces and samples_per_trace are valid
            if n_traces == 0 or samples_per_trace == 0:
                raise ValueError("No valid trace data found.")

            # Update UI elements
            self.data_info_label.setText(f"Loaded {n_traces} traces from {file_path} (SQLite)")

            # Add the file to the treeview
            file_item = QTreeWidgetItem(self.treeview_root)
            file_item.setText(0, Path(file_path).name)

            # Update TreeView with trace count and sample interval
            sample_interval_ms = self.sample_interval * 1e3  # Convert to milliseconds
            sample_rate_khz = self.sample_rate / 1e3  # Convert to kHz

            trace_item = QTreeWidgetItem(file_item)
            trace_item.setText(0, f"Number of Traces: {n_traces}")
            sample_item = QTreeWidgetItem(file_item)
            sample_item.setText(0, f"Samples: {samples_per_trace}")
            sample_interval_item = QTreeWidgetItem(file_item)
            sample_interval_item.setText(0, f"Sample Interval: {sample_interval_ms:.2f} ms")
            sample_rate_item = QTreeWidgetItem(file_item)
            sample_rate_item.setText(0, f"Sample Rate: {sample_rate_khz:.2f} kHz")
            format_item = QTreeWidgetItem(file_item)
            format_item.setText(0, f"Data Format: {data_format}")

            # Plot the seismic data
            self.plot_raw_seismic_image()

        except ValueError as ve:
            logging.error(f"Value error: {ve}")
            self.data_info_label.setText(f"Error loading data: {ve}")
        except Exception as e:
            logging.error(f"Failed to load seismic database file: {e}")
            self.data_info_label.setText(f"Error loading data: {e}")

    @pyqtSlot()
    def export_file(self):
        """
        Export the seismic data to a user-selected file format.
        This method allows the user to export the currently loaded or processed seismic data
        to various supported formats, including SEG-Y (.sgy, .segy), SU (.su), and image formats
        (.png, .jpeg, .jpg, .svg, .bmp, .tiff). The user is prompted with a file dialog to select
        the desired output file path and format. The method then delegates the export operation
        to the appropriate handler based on the selected file extension.
        
        Supported formats:
            - SEG-Y (.sgy, .segy)
            - SU (.su)
            - Image files (.png, .jpeg, .jpg, .svg, .bmp, .tiff)
        If the user cancels the dialog or selects an unsupported format, the export is aborted
        and a warning message is displayed.
        
        Raises:
            QMessageBox.warning: If the selected file format is not supported.
        """
        
        # Get the processed data (or raw data if no processing done)
        data = self.processed_data.astype(np.float32) if self.processed_data is not None else self.data.astype(np.float32)
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export seismic file", "", "SEG-Y Files (*.sgy *.segy);;SU Files (*.su);; Image files(*.png, *.jpeg, *.svg, *.bmp, *.tiff)")
        
        if not file_path:
            return  # User canceled the dialog

        file_extension = Path(file_path).suffix.lower()

        if file_extension in ['.sgy', '.segy']:
            export = SEISMIC.ExportData(data, file_path, self.db_file_path)
            export.export_segy()
        
        elif file_extension == '.su':
            export = SEISMIC.ExportData(data, file_path, self.db_file_path)
            export.export_su()
        
        elif file_extension in ['.png', '.jpeg', '.jpg', '.svg', '.bmp', '.tiff']:
            export = SEISMIC.ExportData(data, file_path, self.db_file_path)
            export.export_image(delta=self.sample_interval*1e3, filename=Path(file_path).stem)
        else:
            QMessageBox.warning(self, "Warning", "Unsupported file format.")



    @pyqtSlot()
    def close_file(self):
        """
        Closes the currently open SEG-Y file, saves any processed or raw seismic data to a binary file via the database,
        clears all loaded data and resources, updates the UI, and closes the editor window.
        
        Steps performed:
        - Retrieves the database file path and initializes the database manager.
        - Determines whether to save processed or raw data, and writes it to the binary file specified in the database.
        - Handles exceptions during the save process and updates the UI accordingly.
        - Frees memory by setting large data attributes to None and forcing garbage collection.
        - Clears any displayed plots and updates the UI label.
        - Closes the editor window gracefully, handling any exceptions that may occur.
        
        Raises:
            Updates the UI and logs errors if any exceptions occur during saving or closing operations.
        """
        
        filepath = self.db_file_path
        if filepath:
            print(f"Database path: {filepath}")
            try:
                # Initialize Database Manager
                seismic_database = DatabaseManager(filepath)

                # Get the processed data (or raw data if no processing done)
                data = self.processed_data.astype(np.float32) if self.processed_data is not None else self.data.astype(np.float32)
                
                if data is None:
                    logging.warning("No data to save.")
                    self.data_info_label.setText("No data to save.")
                    return

                bin_file= seismic_database.fetch_query("SELECT binfile_path FROM binary_file")[0][0]
                logging.info(f'binary_file located at:{bin_file}')

                
                # Write the data to a binary file
                with open(bin_file, 'wb') as binary_file:
                    data.tofile(binary_file)

                logging.info(f"Trace data successfully stored in {bin_file}.")
                
            except Exception as e:
                logging.error(f"Error updating database: {e}")
                self.data_info_label.setText("Error updating database.") 

            try:
                # Set large objects to None (frees memory safely)
                self.data = None
                self.processed_data = None
                self.segy_handler = None
                self.mute_functions = None
                self.segy_file = None
                self.spec = None
                self.sample_interval = None
                self.sample_rate = None
                self.interpretation_window = None

                # Force garbage collection
                gc.collect()

                # Clear the plots
                self.ax.clear()
                self.canvas.draw()
                self.data_info_label.setText("Files closed successfully.")

                # Close the window instead of force-quitting the program
                self.close()

            except Exception as e:
                logging.error(f"Error closing file: {e}")
                self.data_info_label.setText(f"Error closing file: {e}")


    def plot_raw_seismic_image(self):
        """
        Plot the seismic image using the raw seismic data.

        This method clears the current axes, checks if seismic data is loaded,
        and then plots the seismic image using the provided plotting function.
        It updates the canvas to reflect the new plot. If no data is loaded,
        an error message is displayed.
        """

        if self.data is None:
            QMessageBox.critical(self, "Error", "No data loaded.")
            return
        self.ax.clear()
        plot_seismic_image(self.ax, self.data, delta=self.sample_interval*1e3)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def plot_processed_seismic_image(self):
        """
        Plots the seismic image using the processed seismic data.

        This method checks if processed data is available. If not, it displays an error message.
        If processed data exists, it clears the current axes, plots the seismic image using the
        `plot_seismic_image` function with the appropriate sample interval, adjusts the layout,
        and redraws the canvas.

        """
        if self.processed_data is None:
            QMessageBox.critical(self, "Error", "No processed data available.")
            return
        self.ax.clear()
        plot_seismic_image(self.ax, self.processed_data, delta=self.sample_interval*1e3)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def TraceAnalysisWin(self):
        """
        Opens the Trace Analysis window for seismic trace visualization and analysis.
        This method creates a new window that allows the user to select and analyze individual seismic traces
        using various signal processing techniques. The available analyses include:
            - FFT (Fast Fourier Transform)
            - Periodogram
            - Welch Periodogram
            - Spectrogram
            - Wavelet Transform
            - Instantaneous Amplitude
            - Instantaneous Phase
            - Instantaneous Frequency
        
        The user can select the trace number and analysis method via the UI. The corresponding plot is updated
        dynamically based on user selections. Handles errors such as missing data or out-of-range trace numbers.
        
        Requirements:
            - self.data: Loaded seismic data (numpy array or similar)
            - self.processed_data: Optionally processed data (same shape as self.data)
            - self.sample_interval: Sampling interval of the data
            - self.sample_rate: Sampling rate of the data
            - TraceAnalysisWindowUI: UI class for the analysis window
            - trace_periodogram, trace_welch_periodogram, trace_spectrogram, trace_wavelet_transform,
            instantaneous_attributes: Helper functions for signal analysis
        
        Raises:
            QMessageBox.critical: If no data is loaded or if analysis fails.
            QMessageBox.warning: If the selected trace number is out of range.
        """
   
        if self.data is None:
            QMessageBox.critical(self, "Error", "No data loaded.")
            return
        
        # Create a new Trace Analysis window
        self.tracewin = QWidget(self, Qt.WindowType.Window)
        self.ui = TraceAnalysisWindowUI()
        self.ui.setupUI(self.tracewin, traceCount=len(self.processed_data if self.processed_data is not None else self.data))
        self.tracewin.setWindowTitle("Trace Analysis Window")
        
        def trace_update():
            """Update the trace plot based on the selected trace number."""
            trace_number = self.ui.traceNumberInput.value()
            if trace_number >= len(self.data):
                QMessageBox.warning(self, "Warning", "Trace number out of range.")
                return None, None, None
            
            trace = self.processed_data[trace_number] if self.processed_data is not None else self.data[trace_number]
            t = np.arange(0, len(trace)) * self.sample_interval
            self.ui.tracePlot.clear()
            self.ui.tracePlot.plot(t, trace, pen='b')
            self.ui.tracePlot.setTitle(f"Raw Trace {trace_number}")
            self.ui.tracePlot.setLabel('bottom', 'Time', units='seconds')
            self.ui.tracePlot.setLabel('left', 'Amplitude', units='dB')
            self.ui.tracePlot.showGrid(x=True, y=True)
            return trace, t, trace_number

        def update_analysis(index):
            """Update the analysis plot based on the selected method."""
            trace, t, trace_number = trace_update()
            if trace is None:
                return
            
            # Determine if we need to toggle between frequencyPlot and imagePlot
            show_image = index in [3, 4]  # Spectrogram or Wavelet Transform
            self.ui.togglePlots(show_image)

            try:
                if index == 0:  # FFT
                    trace_fft = np.fft.fft(trace)
                    freqs = np.fft.fftfreq(len(trace), self.sample_interval)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(np.abs(freqs), np.abs(trace_fft), pen='b')
                    self.ui.frequencyPlot.setTitle(f"FFT of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power', units='')

                elif index == 1:  # Periodogram
                    f, Pxx = trace_periodogram(trace, fs=self.sample_rate)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(f, Pxx, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Periodogram of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power Spectral Density', units='')

                elif index == 2:  # Welch Periodogram
                    f, Pxx = trace_welch_periodogram(trace, fs=self.sample_rate)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(f, Pxx, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Welch Periodogram of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power Spectral Density', units='')

                elif index == 3:  # Spectrogram
                    try:
                        f, t, Sxx = trace_spectrogram(trace, self.sample_rate)
                        
                        self.ui.imagePlot.clear()
                        self.ui.image.setImage(Sxx, autoLevels=True)
                        self.ui.imagePlot.addItem(self.ui.image)
                        self.ui.imagePlot.setTitle(f"Spectrogram of Trace {trace_number}")
                        self.ui.imagePlot.setLabel('right', 'Amplitude', units='')
                        #self.ui.imagePlot.setXRange(t[0], t[-1])
                        #self.ui.imagePlot.setYRange(f[0], f[-1])
                        #self.ui.imagePlot.setLevels([0, 1])  # Set levels for color mapping
                        #self.ui.imagePlot.setColorMap(plt.get_cmap('viridis'))  # Set colormap

                        
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to plot spectrogram: {str(e)}")

                elif index == 4:  # Wavelet Transform
                    widths = np.arange(1, 128)
                    cwt_matrix = trace_wavelet_transform(trace, widths)
                    normalized_cwt = np.abs(cwt_matrix) / np.max(np.abs(cwt_matrix))
                    self.ui.imagePlot.clear()
                    self.ui.image.setImage(normalized_cwt, autoLevels=True)
                    self.ui.imagePlot.setTitle(f"Wavelet Transform of Trace {trace_number}")
                    self.ui.imagePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.imagePlot.setLabel('left', 'Scale', units='')
                    self.ui.imagePlot.setLabel('right', 'Amplitude', units='')

                elif index == 5: # Instantaneous amplitude
                    instamplitude = instantaneous_attributes(trace, self.sample_rate)['instantaneous_amplitude']
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(t, instamplitude, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Instantaneous Amplitude of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.frequencyPlot.setLabel('left', 'Amplitude', units='')

                elif index == 6: # Instantaneous phase
                    instphase = instantaneous_attributes(trace, self.sample_rate)['instantaneous_phase']
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(t, instphase, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Instantaneous Phase of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.frequencyPlot.setLabel('left', 'Phase', units='radians')

                elif index == 7: # Instantaneous frequency
                    instfreq = instantaneous_attributes(trace, self.sample_rate)['instantaneous_frequency']
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(t, instfreq, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Instantaneous Frequency of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.frequencyPlot.setLabel('left', 'Frequency', units='Hz')
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update analysis plot: {str(e)}")
            
            # Show grid for frequencyPlot if visible
            if not show_image:
                self.ui.frequencyPlot.showGrid(x=True, y=True)

        # Connect signals to slots
        self.ui.traceNumberInput.valueChanged.connect(trace_update)
        self.ui.analysisComboBox.currentIndexChanged.connect(update_analysis)

        self.tracewin.show()

    def get_filter_params(self, bandpass=False, filter_type='IIR'):
        """
        Prompts the user to input filter parameters via dialog boxes.
        
        Parameters:
            bandpass (bool): If True, prompts for both minimum and maximum critical frequencies (for bandpass filter).
            filter_type (str): The type of filter to use (default is 'IIR').
        
        Returns:
            tuple:
                - If bandpass is False: (order, freq)
                - If bandpass is True: (order, freq, freqmax)
        
        Workflow:
            - Displays input dialogs for filter order and critical frequency (and maximum frequency if bandpass).
            - Calls self.show_error() if the user cancels any dialog.
            - Calls self.validate_filter_params() to validate the entered parameters.
        """
        order, ok = QInputDialog.getInt(self, "Enter Filter Order", "Filter Order:", 4, 1, 100, 1)
        if not ok:
            self.show_error("No filter order provided")
        freq, ok = QInputDialog.getDouble(self, "Enter Critical Frequency (Hz)", "Critical Frequency (Hz):", 10, 0, 10000, 1)
        if not ok:
            self.show_error("No critical frequency provided")
        if bandpass:
            freqmax, ok = QInputDialog.getDouble(self, "Enter Maximum Critical Frequency (Hz)", "Maximum Critical Frequency (Hz):", 100, 0, 10000, 1)
            if not ok:
                self.show_error("No maximum critical frequency provided")
            self.validate_filter_params(order, freq, self.sample_rate, filter_type, bandpass=True, freqmax=freqmax)
            return order, freq, freqmax
        self.validate_filter_params(order, freq, self.sample_rate, filter_type)
        return order, freq

    def validate_filter_params(self, order, freq, sample_rate, filter_type, bandpass=False, freqmax=None):
        """
        Validates the parameters for a digital filter.
        
        Parameters:
            order (int): The order of the filter. Must be between 1 and 100.
            freq (float): The cutoff frequency (or minimum frequency for bandpass). Must be greater than 0 and less than the Nyquist frequency.
            sample_rate (float): The sampling rate of the signal.
            filter_type (str): The type of filter (e.g., 'lowpass', 'highpass', 'bandpass').
            bandpass (bool, optional): Whether the filter is a bandpass filter. Defaults to False.
            freqmax (float, optional): The maximum frequency for a bandpass filter. Required if bandpass is True.
        """

        nyquist = sample_rate / 2
        if order < 1 or order > 100:
            self.show_error("Filter order must be between 1 and 100.")
        if freq <= 0 or freq >= nyquist:
            self.show_error(f"{filter_type.capitalize()} filter frequency must be between 0 and Nyquist frequency {nyquist}.")
        if bandpass and (freqmax is None or freqmax <= freq or freqmax >= nyquist):
            self.show_error(f"Bandpass filter max frequency must be between {freq} and Nyquist frequency {nyquist}.")

    def apply_procces_method(self, process_func, *args):
        """
        Applies a processing function to the seismic data asynchronously to keep the GUI responsive.
        
        Parameters:
            process_func (callable): The processing function to apply to the data.
            *args: Additional arguments to pass to the processing function.

        Workflow:
            - Uses `self.processed_data` if available, otherwise falls back to `self.data`.
            - If no data is loaded, displays an error message and returns.
            - Logs the shape of the data before processing.
            - Creates a `ProcessWorker` to run the processing function in a separate thread.
            - Connects worker signals to appropriate handlers for completion and error reporting.
            - Starts the worker thread.
        """

        data_to_process = self.processed_data if self.processed_data is not None else self.data
        if data_to_process is None:
            self.show_error("Error", "No data loaded.")
            return
        else:
            logging.info(f"Data shape before processing: {data_to_process.shape}")
            self.worker = ProcessWorker(process_func, data_to_process, *args)
            self.worker.finished.connect(self.on_method_finished)
            self.worker.error.connect(self.show_error)
            self.worker.start()

    def on_method_finished(self, result):
        """
        Handles the completion of a processing method.
        This method updates the processed data with the result from the worker,
        plots the processed seismic image, and updates the data info label to reflect
        that the processing method has been applied successfully.
        
        Parameters:
            result (numpy.ndarray): The processed seismic data returned by the worker.
        """

        self.processed_data = result
        self.plot_processed_seismic_image()
        self.data_info_label.setText("Process method applied and processed data updated.")

    #def update_progress(self, percent):
    # Update a progress bar or similar UI element
    #self.progress_bar.setValue(percent)
    

    def filt_preview(self, filter_type, type):
        """
        Opens a filter preview dialog for seismic trace filtering and allows interactive parameter selection.
        Depending on the filter type ('bandpass', 'lowpass', or 'highpass'), this method creates a dialog window
        that enables the user to preview the effect of the selected filter on a chosen seismic trace. The dialog
        provides controls for selecting the trace number, adjusting filter parameters (cutoff frequencies and order),
        and visualizing both the original and filtered traces in real time.
        
        Parameters:
            filter_type (str): The type of filter to preview (e.g., 'butterworth', 'chebyshev').
            type (str): The filter mode, one of 'bandpass', 'lowpass', or 'highpass'.
        
        Returns:
            tuple: The selected filter parameters, which vary depending on the filter mode:
                - For 'bandpass': (order, low_cut, high_cut)
                - For 'lowpass': (order, low_cut)
                - For 'highpass': (order, high_cut)
            Returns None if the dialog is cancelled.
        
        Raises:
            Shows an error dialog if invalid filter parameters are selected.
        
        Notes:
            - The preview plots are updated in real time as the user changes parameters.
            - The method assumes that self.data or self.processed_data contains the seismic traces,
              and that self.sample_interval and self.sample_rate are defined.
        """

        if type == 'bandpass':
            # Create a dialog for the filter preview
                self.filterDialog = QDialog(self)
                self.ui = bandass_filter_UI()
                self.ui.setupUi(self.filterDialog, traceCount=len(self.processed_data if self.processed_data is not None else self.data))
                self.filterDialog.setWindowTitle(f"{filter_type.capitalize()} Bandpass Filter Preview")
                # default trace number (can be changed by the user)
                self.ui.traceNumberInput.setValue(0)
                self.ui.traceNumberInput.setRange(0, len(self.processed_data if self.processed_data is not None else self.data) - 1)

                @pyqtSlot()
                # Function to get the user slected trace number plot the trace and perform FFT
                def trace_update():
                    """
                    Updates the trace plot in the UI based on the selected trace number.
                    Retrieves the specified trace from either the processed or raw data, computes the corresponding time axis,
                    and updates the plot widget with the trace data. The plot is labeled and grid lines are shown for better visualization.
                    Returns:
                        tuple: A tuple containing the trace data (numpy.ndarray), the time axis (numpy.ndarray), and the trace number (int).
                    """
                
                    trace_number = self.ui.traceNumberInput.value()
                    trace = self.processed_data[trace_number] if self.processed_data is not None else self.data[trace_number]
                    t = np.arange(0, len(trace)) * self.sample_interval

                    # Plot the original trace
                    self.ui.tracePlot.clear()
                    self.ui.tracePlot.plot(t, trace, pen='b')
                    self.ui.tracePlot.setTitle(f"Raw Trace {trace_number}")
                    self.ui.tracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.tracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.tracePlot.showGrid(x=True, y=True)
                    return trace, t, trace_number

                # FFT processing
                trace, t, trace_number = trace_update()
                trace_fft = np.fft.fft(trace)
                freqs = np.fft.fftfreq(len(trace), self.sample_interval)

                # Set slider ranges
                self.ui.lowcutSlider.setRange(0, int(self.sample_rate / 2))
                self.ui.highcutSlider.setRange(0, int(self.sample_rate / 2))
                self.ui.lowcutSlider.setValue(0)
                self.ui.highcutSlider.setValue(int(self.sample_rate / 2))
                
                @pyqtSlot()
                # Function to update the preview plot
                def update_preview():
                    """
                    Updates the seismic trace preview by applying a bandpass filter to the selected trace and displaying the reconstructed signal.
                    This function retrieves the current low-cut and high-cut frequency values, as well as the filter order, from the UI. It validates the frequency range, applies a bandpass filter in the frequency domain using FFT, reconstructs the filtered signal via inverse FFT, and updates the preview plot in the UI with the filtered trace.
                    Raises:
                        Displays an error message in the UI if the frequency range is invalid.
                    """

                    low_cut = self.ui.lowcutSlider.value()
                    high_cut = self.ui.highcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    if low_cut >= high_cut or low_cut < 0 or high_cut > self.sample_rate / 2:
                        self.show_error(f"Invalid frequency range: {low_cut}-{high_cut} Hz.")
                        return

                    trace, t, trace_number = trace_update() # Get the trace number and plot the trace
                    # Apply bandpass filter
                    trace_fft = np.fft.fft(trace)
                    freqs = np.fft.fftfreq(len(trace), self.sample_interval)
                    filtered_fft = np.zeros_like(trace_fft)
                    mask = (freqs >= low_cut) & (freqs <= high_cut)
                    filtered_fft[mask] = trace_fft[mask]

                    # Reconstruct the signal
                    reconstructed_signal = np.fft.ifft(filtered_fft).real
                    t = np.arange(0, len(reconstructed_signal)) * self.sample_interval
                    self.ui.reconstructedTracePlot.clear()
                    self.ui.reconstructedTracePlot.plot(t, reconstructed_signal, pen='r')
                    self.ui.reconstructedTracePlot.setTitle(f"Reconstructed Trace {trace_number}")
                    self.ui.reconstructedTracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.reconstructedTracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.reconstructedTracePlot.showGrid(x=True, y=True)

                @pyqtSlot()
                def FilterAccept():
                    """
                    Handles the acceptance of the filter dialog by retrieving filter parameters from the UI,
                    validating them, and returning the relevant values.

                    Returns:
                        tuple: A tuple containing the filter order (int), low cut frequency (int), and high cut frequency (int).

                    Raises:
                        ValueError: If the filter parameters are invalid as determined by `validate_filter_params`.
                    """
                    # Get the filter parameters and close the dialog
                    self.filterDialog.accept()  # Close the dialog 
                    freq = self.ui.lowcutSlider.value()
                    freqmax = self.ui.highcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    self.validate_filter_params(order, freq, self.sample_rate, filter_type, bandpass=True, freqmax=freqmax)
                    return order, freq, freqmax

                @pyqtSlot()
                def FilterCancel():
                    '''Close the dialog without applying the filter'''
                    self.filterDialog.reject() # Close the dialog without applying the filter
                    
                # Connect signals to slots
                self.ui.traceNumberInput.valueChanged.connect(trace_update)
                self.ui.lowcutSlider.valueChanged.connect(update_preview)
                self.ui.highcutSlider.valueChanged.connect(update_preview)
                self.ui.button_box.accepted.connect(FilterAccept)
                self.ui.button_box.rejected.connect(FilterCancel)

                if self.filterDialog.exec() == QDialog.DialogCode.Accepted: # If the user clicks the OK button on the dialog box 
                    return FilterAccept() # Return the filter parameters to the calling function (apply_butter_highpass_filter)
                
        if type == 'lowpass':
            # Create a dialog for the filter preview
                self.filterDialog = QDialog(self)
                self.ui = lowpass_filter_UI()
                self.ui.setupUi(self.filterDialog, traceCount=len(self.processed_data if self.processed_data is not None else self.data))
                self.filterDialog.setWindowTitle(f"{filter_type.capitalize()} Lowpass Filter Preview")
                # default trace number (can be changed by the user)
                self.ui.traceNumberInput.setValue(0)
                self.ui.traceNumberInput.setRange(0, len(self.processed_data if self.processed_data is not None else self.data) - 1)

                @pyqtSlot()
                # Function to get the user slected trace number plot the trace and perform FFT
                def trace_update():
                
                    trace_number = self.ui.traceNumberInput.value()
                    trace = self.processed_data[trace_number] if self.processed_data is not None else self.data[trace_number]
                    t = np.arange(0, len(trace)) * self.sample_interval

                    # Plot the original trace
                    self.ui.tracePlot.clear()
                    self.ui.tracePlot.plot(t, trace, pen='b')
                    self.ui.tracePlot.setTitle(f"Raw Trace {trace_number}")
                    self.ui.tracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.tracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.tracePlot.showGrid(x=True, y=True)
                    return trace, t, trace_number
                
                # FFT processing
                trace, t, trace_number = trace_update()
                trace_fft = np.fft.fft(trace)
                freqs = np.fft.fftfreq(len(trace), self.sample_interval)

                # Set slider ranges
                self.ui.lowcutSlider.setRange(0, int(self.sample_rate / 2))
                self.ui.lowcutSlider.setValue(0)

                @pyqtSlot()
                # Function to update the preview plot
                def update_preview():
                    low_cut = self.ui.lowcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    if low_cut < 0 or low_cut > self.sample_rate / 2:
                        self.show_error(f"Invalid frequency range: {low_cut} Hz.")
                        return
                    
                    trace, t, trace_number = trace_update() # Get the trace number and plot the trace


                    # Apply lowpass filter
                    trace_fft = np.fft.fft(trace)
                    freqs = np.fft.fftfreq(len(trace), self.sample_interval)
                    filtered_fft = np.zeros_like(trace_fft)
                    mask = (freqs <= low_cut)
                    filtered_fft[mask] = trace_fft[mask]

                    # Reconstruct the signal
                    reconstructed_signal = np.fft.ifft(filtered_fft).real
                    t = np.arange(0, len(reconstructed_signal)) * self.sample_interval
                    self.ui.reconstructedTracePlot.clear()
                    self.ui.reconstructedTracePlot.plot(t, reconstructed_signal, pen='r')
                    self.ui.reconstructedTracePlot.setTitle(f"Reconstructed Trace {trace_number}")
                    self.ui.reconstructedTracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.reconstructedTracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.reconstructedTracePlot.showGrid(x=True, y=True)

                @pyqtSlot()
                def FilterAccept():
                    # Get the filter parameters and close the dialog
                    self.filterDialog.accept()  # Close the dialog
                    freq = self.ui.lowcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    self.validate_filter_params(order, freq, self.sample_rate, filter_type)
                    return order, freq

                @pyqtSlot()
                def FilterCancel():
                    '''Close the dialog without applying the filter'''
                    self.filterDialog.reject()

                # Connect signals to slots
                self.ui.traceNumberInput.valueChanged.connect(trace_update)
                self.ui.lowcutSlider.valueChanged.connect(update_preview)
                self.ui.button_box.accepted.connect(FilterAccept)
                self.ui.button_box.rejected.connect(FilterCancel)

                if self.filterDialog.exec() == QDialog.DialogCode.Accepted: # If the user clicks the OK button on the dialog box 
                    return FilterAccept() # Return the filter parameters to the calling function (apply_butter_lowpass_filter)
        
        if type == 'highpass':
            # Create a dialog for the filter preview
                self.filterDialog = QDialog(self)
                self.ui = highpass_filter_UI()
                self.ui.setupUi(self.filterDialog, traceCount=len(self.processed_data if self.processed_data is not None else self.data))
                self.filterDialog.setWindowTitle(f"{filter_type.capitalize()} Highpass Filter Preview")
                # default trace number (can be changed by the user)
                self.ui.traceNumberInput.setValue(0)
                self.ui.traceNumberInput.setRange(0, len(self.processed_data if self.processed_data is not None else self.data) - 1)

                @pyqtSlot()
                # Function to get the user slected trace number plot the trace and perform FFT
                def trace_update():
                
                    trace_number = self.ui.traceNumberInput.value()
                    trace = self.processed_data[trace_number] if self.processed_data is not None else self.data[trace_number]
                    t = np.arange(0, len(trace)) * self.sample_interval

                    # Plot the original trace
                    self.ui.tracePlot.clear()
                    self.ui.tracePlot.plot(t, trace, pen='b')
                    self.ui.tracePlot.setTitle(f"Raw Trace {trace_number}")
                    self.ui.tracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.tracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.tracePlot.showGrid(x=True, y=True)
                    return trace, t, trace_number
                
                # FFT processing
                trace, t, trace_number = trace_update()
                trace_fft = np.fft.fft(trace)
                freqs = np.fft.fftfreq(len(trace), self.sample_interval)

                # Set slider ranges
                self.ui.highcutSlider.setRange(0, int(self.sample_rate / 2))
                self.ui.highcutSlider.setValue(0)

                @pyqtSlot()
                # Function to update the preview plot
                def update_preview():
                    high_cut= self.ui.highcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    if high_cut < 0 or high_cut > self.sample_rate / 2:
                        self.show_error(f"Invalid frequency range: {high_cut} Hz.")
                        return
                    
                    trace, t, trace_number = trace_update() # Get the trace number and plot the trace

                    # Apply highpass filter
                    trace_fft = np.fft.fft(trace)
                    freqs = np.fft.fftfreq(len(trace), self.sample_interval)
                    filtered_fft = np.zeros_like(trace_fft)
                    mask = (freqs >= high_cut)
                    filtered_fft[mask] = trace_fft[mask]

                    # Reconstruct the signal
                    reconstructed_signal = np.fft.ifft(filtered_fft).real
                    t = np.arange(0, len(reconstructed_signal)) * self.sample_interval
                    self.ui.reconstructedTracePlot.clear()
                    self.ui.reconstructedTracePlot.plot(t, reconstructed_signal, pen='r')
                    self.ui.reconstructedTracePlot.setTitle(f"Reconstructed Trace {trace_number}")
                    self.ui.reconstructedTracePlot.setLabel('bottom', 'Time', units='seconds')
                    self.ui.reconstructedTracePlot.setLabel('left', 'Amplitude', units='dB')
                    self.ui.reconstructedTracePlot.showGrid(x=True, y=True)

                @pyqtSlot()
                def FilterAccept():
                    # Get the filter parameters and close the dialog
                    self.filterDialog.accept()  # Close the dialog
                    freq = self.ui.highcutSlider.value()
                    order = int(self.ui.filterOrderInput.text())
                    self.validate_filter_params(order, freq, self.sample_rate, filter_type)
                    return order, freq

                @pyqtSlot()
                def FilterCancel():
                    '''Close the dialog without applying the filter'''
                    self.filterDialog.reject()

                # Connect signals to slots
                self.ui.traceNumberInput.valueChanged.connect(trace_update)
                self.ui.highcutSlider.valueChanged.connect(update_preview)
                self.ui.button_box.accepted.connect(FilterAccept)
                self.ui.button_box.rejected.connect(FilterCancel)

                if self.filterDialog.exec() == QDialog.DialogCode.Accepted: # If the user clicks the OK button on the dialog box 
                    return FilterAccept() # Return the filter parameters to the calling function (apply_butter_highpass_filter)

    @pyqtSlot()
    def apply_butter_bandpass_filter(self):
        """
        Applies a Butterworth bandpass filter to the seismic data.

        This method retrieves the filter parameters (order, minimum frequency, and maximum frequency)
        using the filt_preview method, then applies the bandpass filter to the data using the
        apply_procces_method with the IIR_Filters.bandpass_filter function. If an error occurs during
        the process (e.g., invalid parameters), an error message is displayed to the user.

        Raises:
            Displays an error dialog if the filter cannot be applied due to invalid parameters.
        """
        # Get the filter parameters and apply the bandpass filter
        try:
            order, freqmin, freqmax = self.filt_preview(filter_type='Butterworth', type='bandpass')
            self.apply_procces_method(IIR_Filters.bandpass_filter, self.sample_rate, order, freqmin, freqmax)  # Apply the filter to the data
        except ValueError as e:
            self.show_error("Error", f"Unable to apply bandpass filter: {e}")

    @pyqtSlot()
    def apply_butter_highpass_filter(self):
        """
        Applies a Butterworth highpass filter to the seismic data.
        This method retrieves the filter parameters (order and cutoff frequency) using the filt_preview method,
        then applies the highpass filter to the data using the apply_procces_method with the IIR_Filters.highpass_filter function.
        If an error occurs during the process (e.g., invalid parameters), an error message is displayed to the user.
        Raises:
            Displays an error dialog if the filter cannot be applied due to invalid parameters.
        """
        # Get the filter parameters and apply the highpass filter
        try:
            order, freq = self.filt_preview(filter_type='Butterworth', type='highpass')
            self.apply_procces_method(IIR_Filters.highpass_filter, self.sample_rate, order, freq)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply highpass filter: {e}")

    @pyqtSlot()
    def apply_butter_lowpass_filter(self):

        try:
            order, freq = self.filt_preview(filter_type='Butterworth', type='lowpass')
            self.apply_procces_method(IIR_Filters.lowpass_filter, self.sample_rate, order, freq)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply lowpass filter: {e}")

    @pyqtSlot()
    def apply_cheby_bandpass_filter(self):
        try:
            order, freqmin, freqmax = self.get_filter_params(bandpass=True, filter_type='Chebyshev')
            ripple = self.get_chebyshev_ripple()
            self.apply_procces_method(IIR_Filters.cheby2_bandpass_filter, self.sample_rate, order, freqmin, freqmax, ripple)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply Chebyshev bandpass filter: {e}")

    @pyqtSlot()
    def apply_cheby_highpass_filter(self):
        try:
            order, freq = self.get_filter_params(filter_type='Chebyshev')
            ripple = self.get_chebyshev_ripple()
            self.apply_procces_method(IIR_Filters.cheby2_highpass_filter, self.sample_rate, order, freq, ripple)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply Chebyshev highpass filter: {e}")

    @pyqtSlot()
    def apply_cheby_lowpass_filter(self):
        try:
            order, freq = self.get_filter_params(filter_type='Chebyshev')
            ripple = self.get_chebyshev_ripple()
            self.apply_procces_method(IIR_Filters.cheby2_lowpass_filter, self.sample_rate, order, freq, ripple)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply Chebyshev lowpass filter: {e}")

    def get_chebyshev_ripple(self):
        ripple, ok = QInputDialog.getDouble(self, "Enter Ripple (dB)", "Ripple (dB):", 0.5, 0.01, 10.0, 2)
        if not ok:
            raise ValueError("No ripple provided")
        return ripple

    @pyqtSlot()
    def apply_fir_bandpass_filter(self):
        try:
            order, freqmin, freqmax = self.get_filter_params(bandpass=True, filter_type='FIR')
            window = self.get_fir_window()
            self.apply_procces_method(FIR_Filters.bandpass_filter, freqmin, freqmax, self.sample_rate, order, window)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply FIR bandpass filter: {e}")

    @pyqtSlot()
    def apply_fir_highpass_filter(self):
        try:
            order, freq = self.get_filter_params(filter_type='FIR')
            window = self.get_fir_window()
            self.apply_procces_method(FIR_Filters.highpass_filter, freq, self.sample_rate, order, window)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply FIR highpass filter: {e}")

    @pyqtSlot()
    def apply_fir_lowpass_filter(self):
        try:
            order, freq = self.get_filter_params(filter_type='FIR')
            window = self.get_fir_window()
            self.apply_procces_method(FIR_Filters.lowpass_filter, freq, self.sample_rate, order, window)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply FIR lowpass filter: {e}")

    @pyqtSlot()
    def apply_fk_filter(self):
        try:
            order, ok = QInputDialog.getInt(self, "Enter Filter Order", "Filter Order:", 10, 1, 100, 1)
            if not ok:
                raise ValueError("No filter order provided")
            self.apply_procces_method(FIR_Filters.fk_filter, self.sample_rate, order)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply F-K filter: {e}")

    @pyqtSlot()
    def apply_zero_phase_filter(self):
        try:
            order, freqmin, freqmax = self.get_filter_params(bandpass=True, filter_type='FIR')
            self.apply_procces_method(FIR_Filters.zero_phase_bandpass_filter, freqmin, freqmax, self.sample_rate, order)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply zero-phase bandpass filter: {e}")

    @pyqtSlot()
    def apply_wavelet_filter(self):
        try:
            wavelet_type, ok = QInputDialog.getText(self, "Enter Wavelet Type", "Wavelet Type:", text="db4")
            if not ok:
                raise ValueError("No wavelet type provided")
            level, ok = QInputDialog.getInt(self, "Enter Decomposition Level", "Decomposition Level:", 5, 1, 10, 1)
            if not ok:
                raise ValueError("No decomposition level provided")
            self.apply_procces_method(FIR_Filters.wavelet_filter, wavelet_type, level)
        except ValueError as e:
            self.show_error("Error", f"Unable to apply wavelet filter: {e}")

    def get_fir_window(self):
        window, ok = QInputDialog.getText(self, "Enter Window Type", "Window Type:", text="hamming")
        if not ok:
            raise ValueError("No window type provided")
        return window

    @pyqtSlot()
    def agc_gain(self):
        param1, ok = QInputDialog.getInt(self, "Enter AGC Window Size", "Window Size:", 51, 1, 1000, 1)
        if ok:
            self.apply_gain('agc', param1)
    
    @pyqtSlot()
    def tvg_gain(self):
        param1, ok = QInputDialog.getDouble(self, "Enter TVG time gradient", "Time gradient:", 2.0, 0.1, 10.0, 1)
        if ok:
            self.apply_gain('tvg', param1)
    
    @pyqtSlot()
    def const_gain(self):
        param1, ok = QInputDialog.getDouble(self, "Enter Constant Gain Factor", "Gain Factor:", 2.0, 0.1, 10.0, 1)
        if ok:
            self.apply_gain('const', param1)

    def apply_gain(self, gain_type, param1=None):
        if self.data is None:
            self.show_error("Error", "No data loaded.")
            return
        try:
            data_to_gain = self.processed_data if self.processed_data is not None else self.data
            if gain_type == 'agc':
                self.processed_data = agc_gain(data_to_gain, param1)
            elif gain_type == 'tvg':
                self.processed_data = tvg_gain(data_to_gain, param1)
            elif gain_type == 'const':
                self.processed_data = constant_gain(data_to_gain, param1)
            
            self.plot_processed_seismic_image()
            self.data_info_label.setText(f"Applied {gain_type.upper()} gain and updated processed data.")
        except ValueError as e:
            self.show_error("Error", f"Unable to apply {gain_type} gain: {e}")
    
    @pyqtSlot()
    def apply_top_mute(self):
        """Slot to apply top mute using a user-specified mute time."""
        mute_time, ok = QInputDialog.getDouble(self, "Enter Mute Time", "Mute Time (seconds):", 0.1, 0, 10, 3)
        if ok:
            self.processed_data = Mute.top_mute(self.processed_data if self.processed_data is not None else self.data, mute_time, self.sample_interval)
            self.plot_processed_seismic_image()
            self.data_info_label.setText("Applied top mute and updated processed data.")
    
    @pyqtSlot()
    def apply_bottom_mute(self):
        """Slot to apply bottom mute using a user-specified mute time."""
        mute_time, ok = QInputDialog.getDouble(self, "Enter Mute Time", "Mute Time (seconds):", 0.1, 0, 10, 3)
        if ok:
            self.processed_data = Mute.bottom_mute(self.processed_data if self.processed_data is not None else self.data, mute_time, self.sample_interval)
            self.plot_processed_seismic_image()
            self.data_info_label.setText("Applied bottom mute and updated processed data.")
    
    """
    def apply_offset_mute(self):
        #Slot to apply offset mute.

         if self.processed_data is not None:
            self.processed_data = offset_mute(self.processed_data, offsets, mute_offset)
       
         else:
            self.processed_data = offset_mute(self.data, offsets, mute_offset)

        self.plot_processed_seismic_image()
        self.data_info_label.setText("Applied offset mute and updated processed data.")   
    """
    @pyqtSlot()
    def apply_time_variant_mute(self):
        """Slot to apply time-variant mute."""
        initial_time, ok1 = QInputDialog.getDouble(self, "Enter Initial Mute Time", "Initial Mute Time (seconds):", 0.1, 0, 10, 3)
        if not ok1: return
        final_time, ok2 = QInputDialog.getDouble(self, "Enter Final Mute Time", "Final Mute Time (seconds):", 1.0, 0, 10, 3)
        if not ok2: return
        
        self.processed_data = Mute.time_variant_mute(self.processed_data if self.processed_data is not None else self.data, initial_time, final_time, self.sample_interval)
        self.plot_processed_seismic_image()
        self.data_info_label.setText("Applied time-variant mute and updated processed data.")
    
    @pyqtSlot()
    def apply_SZ_mute(self):
        """Slot to apply shallow mute."""
        self.processed_data = PredefinedMute.shallow_zone_mute(self.processed_data if self.processed_data is not None else self.data, self.sample_interval)
        self.plot_processed_seismic_image()
        self.data_info_label.setText("Applied shallow zone mute and updated processed data.")
    
    @pyqtSlot()
    def apply_DW_mute(self):
        """Slot to apply shallow mute."""
        self.processed_data = PredefinedMute.marine_direct_wave_mute(self.processed_data if self.processed_data is not None else self.data, self.sample_interval)
        self.plot_processed_seismic_image()
        self.data_info_label.setText("Applied shallow zone mute and updated processed data.") 
    
    @pyqtSlot()
    def apply_DZ_mute(self):
        """Slot to apply shallow mute."""
        self.processed_data = PredefinedMute.deep_zone_mute(self.processed_data if self.processed_data is not None else self.data, self.sample_interval)
        self.plot_processed_seismic_image()
        self.data_info_label.setText("Applied shallow zone mute and updated processed data.")       

    pyqtSlot()
    def apply_userinteractive_mute(self):
        """Trigger the interactive surgical mute on the seismic data."""
        if self.data is None:
            self.data_info_label.setText("No seismic data loaded.")
            return

        # Use the Mute class to enable interactive muting
        self.data_info_label.setText("Draw the mute polygon on the plot and press 'Enter' or double-click to finish.")
        
        # Trigger interactive mute but don't expect immediate return of processed data
        self.mute_functions.interactive_mute(self.ax, self.processed_data if self.processed_data is not None else self.data)    
    
    @pyqtSlot()
    def apply_spiking_dec(self):
        """
        Opens a dialog window for the user to select and configure a wavelet for spiking deconvolution.
        The method dynamically updates parameter input fields based on the selected wavelet type
        (e.g., Ricker, Chirp, Ormsby, Minimum Phase, Klauder, Boomer, Zero Phase). After the user
        enters the parameters and accepts the dialog, the method creates the specified wavelet,
        applies spiking deconvolution to the seismic data using the selected wavelet, and updates
        the UI to reflect the applied process. Handles user cancellation and displays error messages
        if parameter parsing or processing fails.
        """
    
        self.dialog = WaveletWindowUI(self)
        wavelet_parameters = {}
        self.dialog.ok_button.clicked.connect(self.dialog.accept)
        self.dialog.cancel_button.clicked.connect(self.dialog.destroy)
        self.dialog.importwavelet_button.clicked.connect(self.import_wavelet)

        def update_parameter_inputs(index):
            """
            Dynamically updates the parameter input fields in the dialog based on the selected wavelet type.
            Args:
                index (int): The index of the currently selected wavelet in the combo box.
            Behavior:
                - Clears existing wavelet parameters and input fields.
                - Adds appropriate parameter input fields for the selected wavelet type:
                    - "Ricker": Frequency and Duration.
                    - "Chirp": Start Frequency (f0), End Frequency (f1), and Duration.
                    - "Ormsby": f1, f2, f3, and f4.
                    - "Minimum Phase": Frequency.
                    - "Klauder": Start Frequency (f0), End Frequency (f1), and Sweep Duration.
                    - "Boomer": Start Frequency (f0), End Frequency (f1), and Duration.
                    - "Zero Phase": Frequency.
                - Uses dialog methods to add labeled input fields and updates the wavelet_parameters dictionary.
            """
          
            wavelet_name = self.dialog.wavelet_combo.currentText()
            wavelet_parameters.clear()
            self.dialog.clear_parameters()

            # Add parameter inputs dynamically
            if wavelet_name == "Ricker":
                wavelet_parameters["frequency"] = self.dialog.add_parameter_input("Frequency (Hz):", "frequency")
                wavelet_parameters["duration"] = self.dialog.add_parameter_input("Duration (s):", "duration")
            elif wavelet_name == "Chirp":
                wavelet_parameters["f0"] = self.dialog.add_parameter_input("Start Frequency (Hz):", "f0")
                wavelet_parameters["f1"] = self.dialog.add_parameter_input("End Frequency (Hz):", "f1")
                wavelet_parameters["duration"] = self.dialog.add_parameter_input("Duration (s):", "duration")
            elif wavelet_name == "Ormsby":
                wavelet_parameters["f1"] = self.dialog.add_parameter_input("f1:", "f1")
                wavelet_parameters["f2"] = self.dialog.add_parameter_input("f2:", "f2")
                wavelet_parameters["f3"] = self.dialog.add_parameter_input("f3:", "f3")
                wavelet_parameters["f4"] = self.dialog.add_parameter_input("f4:", "f4")
            elif wavelet_name == "Minimum Phase":
                wavelet_parameters["frequency"] = self.dialog.add_parameter_input("Frequency (Hz):", "frequency")
            elif wavelet_name == "Klauder":
                wavelet_parameters["f0"] = self.dialog.add_parameter_input("Start Frequency (Hz):", "f0")
                wavelet_parameters["f1"] = self.dialog.add_parameter_input("End Frequency (Hz):", "f1")
                wavelet_parameters["sweep_duration"] = self.dialog.add_parameter_input("Sweep Duration (s):", "sweep_duration")
            elif wavelet_name == "Boomer":
                wavelet_parameters["f0"] = self.dialog.add_parameter_input("Start Frequency (Hz):", "f0")
                wavelet_parameters["f1"] = self.dialog.add_parameter_input("End Frequency (Hz):", "f1")
                wavelet_parameters["duration"] = self.dialog.add_parameter_input("Duration (s):", "duration")
            elif wavelet_name == "Zero Phase":
                wavelet_parameters["frequency"] = self.dialog.add_parameter_input("Frequency (Hz):", "frequency")

        # Connect combo box signal and initialize inputs
        self.dialog.wavelet_combo.currentIndexChanged.connect(update_parameter_inputs)
        update_parameter_inputs(0)

        if self.dialog.exec() == QDialog.DialogCode.Accepted:
            print("Dialog accepted")  # Debugging
            try:
                params = {key: float(edit.text()) for key, edit in wavelet_parameters.items() if edit.text()}
                wavelet_name = self.dialog.wavelet_combo.currentText()
                print("Parameters:", params, "Wavelet Name:", wavelet_name)  # Debugging

                wavelet = self.create_wavelet(wavelet_name, params)
                self.apply_procces_method(Deconvolution.spiking_deconvolution, wavelet)
                #self.processed_data = np.array([Deconvolution.spiking_deconvolution(trace, wavelet) for trace in data])
                #self.plot_processed_seismic_image()
                self.data_info_label.setText(f"Applied spiking deconvolution with {wavelet_name} wavelet.")
            except Exception as e:
                print("Error:", e)  # Debugging
                self.data_info_label.setText(f"Error: {str(e)}")
        else:
            print("Dialog rejected")  # Debugging


    def create_wavelet(self, wavelet_name, params):
        """
        Create a seismic wavelet based on the specified wavelet type and parameters.
        Parameters:
            wavelet_name (str): The name of the wavelet to create. Supported values are:
                - "Ricker"
                - "Chirp"
                - "Ormsby"
                - "Minimum Phase"
                - "Klauder"
                - "Boomer"
                - "Zero Phase"
            params (dict): Dictionary of parameters required for the selected wavelet type. 
                The required keys depend on the wavelet:
                    - "Ricker": {"frequency", "duration"}
                    - "Chirp": {"duration", "f0", "f1"}
                    - "Ormsby": {"f1", "f2", "f3", "f4"}
                    - "Minimum Phase": {"frequency"}
                    - "Klauder": {"f0", "f1", "sweep_duration"}
                    - "Boomer": {"f0", "f1", "duration"}
                    - "Zero Phase": {"frequency"}
        Returns:
            np.ndarray: The generated wavelet as a NumPy array.
        Raises:
            KeyError: If required parameters are missing from the params dictionary.
            ValueError: If an unsupported wavelet_name is provided.
        """
       
        if wavelet_name == "Ricker":
            return Wavelets.ricker(params["frequency"], self.sample_interval, params["duration"])
        elif wavelet_name == "Chirp":
            return Wavelets.chirp(params["duration"], params["f0"], params["f1"], 1 / self.sample_interval)
        elif wavelet_name == "Ormsby":
            return Wavelets.ormsby(
                np.linspace(-1, 1, int(2 / self.sample_interval)),
                params["f1"], params["f2"], params["f3"], params["f4"]
            )
        elif wavelet_name == "Minimum Phase":
            return Wavelets.minimum_phase(
                np.linspace(-1, 1, int(2 / self.sample_interval)), params["frequency"]
            )
        elif wavelet_name == "Klauder":
            return Wavelets.klauder(
                np.linspace(0, params["sweep_duration"], int(params["sweep_duration"] / self.sample_interval)),
                params["f0"], params["f1"], params["sweep_duration"]
            )
        elif wavelet_name == "Boomer":
            return Wavelets.boomer(
                np.linspace(0, params["duration"], int(params["duration"] / self.sample_interval)),
                params["f0"], params["f1"], params["duration"]
            )
        elif wavelet_name == "Zero Phase":
            return Wavelets.zero_phase(
                np.linspace(-1, 1, int(2 / self.sample_interval)), params["frequency"]
            )
    
    @pyqtSlot()        
    def import_wavelet(self):
        """
        Opens a file dialog to import a wavelet data file (CSV, Excel, or TXT), loads the wavelet data,
        and applies spiking deconvolution to the seismic data using the imported wavelet.
        The method updates the data information label with the operation status or error message.
        Steps:
            1. Prompts the user to select a wavelet file.
            2. Loads the wavelet data from the selected file.
            3. Converts the amplitude data to a NumPy array.
            4. Applies spiking deconvolution to the seismic data using the imported wavelet.
            5. Updates the UI label with the result or any error encountered.
            
        Raises:
            Displays an error message in the UI label if file loading or processing fails.
        """
            
        file_path = QFileDialog.getOpenFileName(self, "Import Wavelet data file", "", "CSV Files (*.csv);;Excel Files (*.xls *.xlsx);;Text Files (*.txt)")
        if file_path:
            try:
                data = MAGY.MAGGY.CSV_TXT_XLS.load_files(self, file_path)
                wavelet = np.asarray(data['Amplitude'])
                #duration = np.asarray(data['time'])
                #data = self.processed_data if self.processed_data is not None else self.data
                #self.processed_data = np.array([Deconvolution.spiking_deconvolution(trace, wavelet) for trace in data])
                #self.plot_processed_seismic_image()
                self.apply_procces_method(Deconvolution.spiking_deconvolution, wavelet)
                self.data_info_label.setText(f"Applied spiking deconvolution with estimated wavelet.")

            except Exception as e:
                self.data_info_label.setText(f"Error: {str(e)}")

    pyqtSlot()
    def apply_predictive_dec(self):
        """
        Applies predictive deconvolution to the seismic data.

        This method is a slot that triggers the predictive deconvolution process
        by calling the `apply_procces_method` with the appropriate parameters.
        After applying the deconvolution, it updates the `data_info_label` to
        inform the user that predictive deconvolution has been applied.
        """
      
        self.apply_procces_method(Deconvolution.predictive_deconvolution, 1, 2)
        self.data_info_label.setText("Applied predictive Deconvolution.")
    
    pyqtSlot()
    def apply_wiener_dec(self):
        """
        Applies Wiener deconvolution to the current seismic data.

        This method is a slot that triggers the Wiener deconvolution process using
        predefined parameters (filter length of 15 and noise level of 0.001) by calling
        the `apply_procces_method` with `Deconvolution.wiener_deconvolution`. After
        processing, it updates the data information label to indicate that Wiener
        deconvolution has been applied.
        """
    
        self.apply_procces_method(Deconvolution.wiener_deconvolution, 15, 0.001)
        self.data_info_label.setText("Applied wiener Deconvolution.")

    @pyqtSlot()
    def apply_Horizon_pick(self):
        """
        Opens the Seismic Interpretation Window for horizon picking.

        If the interpretation window does not already exist, it creates a new instance
        using the processed seismic data if available, otherwise the raw data, and the
        current sample rate. Then, it displays the interpretation window to the user.
        """

        if not hasattr(self, 'interpretation_window') or self.interpretation_window is None:
            self.interpretation_window = SeismicInterpretationWindow(
                seismic_data=self.processed_data if self.processed_data is not None else self.data,
                sample_rate = self.sample_rate
            )
        self.interpretation_window.show()

    @pyqtSlot()
    def apply_trace_qc(self):
        dialog = TraceQCUI(seismic_data = self.processed_data if self.processed_data is not None else self.data,
                           qc = TraceQC(),
                           sample_interval=self.sample_interval*1e3)
        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = SeismicEditor()
    main_window.show()
    sys.exit(app.exec())
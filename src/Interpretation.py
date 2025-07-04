"""
Interpretation.py

This module defines the SeismicInterpretationWindow class, which provides a graphical interface
for interpreting seismic data. The user can mark points, tag them, erase them, apply edge detection
techniques, and extract horizons interactively. This is achieved using PyQt5 for the GUI components
and Matplotlib for plotting seismic data. Additionally, SciKit-Image is used for edge detection
and horizon extraction.

Classes:
    SeismicInterpretationWindow: A GUI window for seismic interpretation with various tools for horizon detection and point marking.

Key Features:
    - Load and display seismic data as an image.
    - Mark and erase horizon points with tags.
    - Apply edge detection algorithms (Canny, Sobel).
    - Extract and display horizons.
    - Save and load horizon points.
"""

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import ( QMainWindow, QVBoxLayout, QToolBar, QFileDialog, QInputDialog, QWidget)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from skimage import feature
from skimage import filters, morphology, measure
from skimage.measure import label, regionprops
from Trace_analysis import instantaneous_attributes

class SeismicInterpretationWindow(QMainWindow):
    """
    SeismicInterpretationWindow class provides a graphical interface for seismic data interpretation.

    This class allows users to:
        - Mark and erase horizon points on seismic data.
        - Apply edge detection techniques (Canny, Sobel).
        - Extract horizons using image processing techniques.
        - Save and load horizon points from files.

    Attributes:
        seismic_data (ndarray): 2D array containing the seismic data (traces x samples).
        horizon_points (list): List of points marked by the user, stored as (x, y, tag) tuples.
        current_tag (str): The current tag used when marking horizon points.
        current_mode (str): The current mode for interacting with the data ('mark' or 'erase').

    Methods:
        init_ui(): Initializes the user interface (UI), including the menu and toolbar.
        create_menu(): Creates the menu for file operations and horizon detection.
        create_toolbar(): Creates the toolbar for marking, erasing, and tagging points.
        set_mark_mode(): Switches to mark mode for marking points on the seismic data.
        set_erase_mode(): Switches to erase mode for erasing points on the seismic data.
        set_tag(): Opens a dialog to set the current tag for marking horizon points.
        on_click(event): Handles mouse click events to mark or erase points on the seismic image.
        erase_nearest_point(x, y): Finds and erases the nearest marked point to the given coordinates.
        redraw_horizon_points(): Redraws all horizon points on the seismic image.
        save_horizon_points(): Saves the marked horizon points to a CSV or TXT file.
        load_horizon_points(): Loads horizon points from a CSV or TXT file and displays them on the seismic image.
        apply_canny_edge_detection(): Applies Canny edge detection to the seismic data.
        apply_sobel_edge_detection(): Applies Sobel edge detection to the seismic data.
        extract_and_plot_horizons(): Extracts horizons from the seismic data and plots them on the seismic image.
    """
    
    def __init__(self, seismic_data, sample_rate, parent=None):
        """
        Initialize the SeismicInterpretationWindow.

        Parameters:
            seismic_data (ndarray): 2D array representing the seismic data (traces x samples).
            parent (QWidget, optional): The parent widget for the window.
        """
        super().__init__(parent)
        self.setWindowTitle('Seismic Interpretation')
        self.setGeometry(100, 100, 1200, 800)

        self.seismic_data = seismic_data  # Store the seismic data
        self.sample_rate = sample_rate
        self.horizon_points = []  # Stores points as (x, y, tag) tuples
        self.current_tag = None
        self.current_mode = 'mark'  # Default mode to mark points

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface with the menu, toolbar, and canvas for displaying seismic data."""
        self.create_menu()
        self.create_toolbar()

        # Setup Matplotlib canvas and axis
        self.canvas = FigureCanvas(Figure())
        self.ax = self.canvas.figure.subplots()

        # Display the seismic data as an image
        self.ax.clear()
        self.ax.imshow(np.transpose(self.seismic_data), cmap='seismic', aspect='auto')
        self.ax.set_title("Seismic Image")
        self.ax.set_xlabel("Trace Number")
        self.ax.set_ylabel("Two Way Travel Time (ms)")

        # Setup layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        # Add Matplotlib toolbar for zooming and panning
        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Connect the Matplotlib event handler to handle clicks
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def create_menu(self):
        """Create the menu bar for file operations and horizon detection tools."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('File')
        save_action = QAction('Save Horizon Points', self)
        save_action.triggered.connect(self.save_horizon_points)
        file_menu.addAction(save_action)

        load_action = QAction('Load Horizon Points', self)
        load_action.triggered.connect(self.load_horizon_points)
        file_menu.addAction(load_action)

        horizon_detecting_menu = menu_bar.addMenu('Horizon Detection')
        
        canny_edge_action = QAction('Canny Edge Detection', self)
        canny_edge_action.triggered.connect(self.apply_canny_edge_detection)
        horizon_detecting_menu.addAction(canny_edge_action)

        sobel_edge_action = QAction('Sobel Edge Detection', self)
        sobel_edge_action.triggered.connect(self.apply_sobel_edge_detection)
        horizon_detecting_menu.addAction(sobel_edge_action)

        horizon_extraction_action = QAction('Horizon Extraction', self)
        horizon_extraction_action.triggered.connect(self.extract_and_plot_horizons)
        horizon_detecting_menu.addAction(horizon_extraction_action)

        instantaneous_attributes_menu = menu_bar.addMenu('Instantaneous Attributes')
        
        inst_amplitude_action = QAction('Instantaneous Amplitude', self)
        inst_amplitude_action.triggered.connect(self.plot_instantaneous_amplitude)
        instantaneous_attributes_menu.addAction(inst_amplitude_action)
        
        inst_phase_action = QAction('Instantaneous Phase', self)
        inst_phase_action.triggered.connect(self.plot_instantaneous_phase)
        instantaneous_attributes_menu.addAction(inst_phase_action)

        inst_frequency_action = QAction('Instantaneous Frequency', self)
        inst_frequency_action.triggered.connect(self.plot_instantaneous_frequency)
        instantaneous_attributes_menu.addAction(inst_frequency_action)

        plot_seismic_action = QAction('Plot Seismic Data', self)
        plot_seismic_action.triggered.connect(self.plot_seismic_data)
        instantaneous_attributes_menu.addAction(plot_seismic_action)
        

    def create_toolbar(self):
        """Create a toolbar for marking, erasing, and tagging points on the seismic image."""
        toolbar = QToolBar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        mark_action = QAction(QIcon('icons/mark.png'), 'Mark Point', self)
        mark_action.triggered.connect(self.set_mark_mode)
        toolbar.addAction(mark_action)

        erase_action = QAction(QIcon('icons/erase.png'), 'Erase Point', self)
        erase_action.triggered.connect(self.set_erase_mode)
        toolbar.addAction(erase_action)

        tag_action = QAction(QIcon('icons/tag.png'), 'Set Tag', self)
        tag_action.triggered.connect(self.set_tag)
        toolbar.addAction(tag_action)

    def set_mark_mode(self):
        """Switch to mark mode for marking points on the seismic image."""
        self.current_mode = 'mark'

    def set_erase_mode(self):
        """Switch to erase mode for erasing points from the seismic image."""
        self.current_mode = 'erase'

    def set_tag(self):
        """Prompt the user to enter a tag for marking horizon points."""
        tag, ok = QInputDialog.getText(self, 'Set Tag', 'Enter tag for horizon points:')
        if ok:
            self.current_tag = tag

    def on_click(self, event):
        """Handle mouse click events for marking or erasing points on the seismic image."""
        if event.inaxes != self.ax:
            return
        
        if self.current_mode == 'mark':
            point = (event.xdata, event.ydata, self.current_tag)
            self.horizon_points.append(point)
            self.ax.plot(event.xdata, event.ydata, 'ro')  # Mark the point with a red dot
            self.canvas.draw()

        elif self.current_mode == 'erase':
            self.erase_nearest_point(event.xdata, event.ydata)
            self.canvas.draw()

    def erase_nearest_point(self, x, y):
        """
        Erase the nearest point to the given coordinates.

        Parameters:
            x (float): X-coordinate of the point (trace number).
            y (float): Y-coordinate of the point (TWT).

        Returns:
            None: The nearest point is erased, and the image is updated.
        """
        if not self.horizon_points:
            return

        # Calculate distances to each point and find the nearest one
        distances = [np.hypot(px - x, py - y) for px, py, _ in self.horizon_points]
        min_index = np.argmin(distances)

        if distances[min_index] < 10:  # Threshold distance to identify nearby points
            del self.horizon_points[min_index]  # Remove the point
            self.ax.clear()
            self.ax.imshow(np.transpose(self.seismic_data), cmap='seismic', aspect='auto')  # Redraw seismic image
            self.redraw_horizon_points()  # Redraw all horizon points

    def redraw_horizon_points(self):
        """Redraw all marked horizon points on the seismic image."""
        for x, y, tag in self.horizon_points:
            self.ax.plot(x, y, 'ro')
        self.canvas.draw()

    def save_horizon_points(self):
        """Save the marked horizon points to a CSV or TXT file."""
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save Horizon Points', '', 'CSV Files (*.csv);;TXT Files (*.txt)')
        if file_path:
            df = pd.DataFrame(self.horizon_points, columns=['X', 'Y', 'Tag'])
            df.to_csv(file_path, index=False)

    def load_horizon_points(self):
        """Load horizon points from a CSV or TXT file and display them on the seismic image."""
        file_path, _ = QFileDialog.getOpenFileName(self, 'Load Horizon Points', '', 'CSV Files (*.csv);;TXT Files (*.txt)')
        if file_path:
            df = pd.read_csv(file_path)
            self.horizon_points = df.values.tolist()
            self.ax.clear()
            self.ax.imshow(np.transpose(self.seismic_data), cmap='seismic', aspect='auto')
            self.redraw_horizon_points()

    def apply_canny_edge_detection(self):
        """Apply Canny edge detection to the seismic data and display the result."""
        try:
            edges_canny = feature.canny(self.seismic_data)
            self.ax.clear()
            self.ax.imshow(np.transpose(edges_canny), cmap='gray', aspect='auto')
            self.ax.set_title("Seismic Image with Canny Edge Detection")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)

    def apply_sobel_edge_detection(self):
        """Apply Sobel edge detection to the seismic data and display the result."""
        try:
            edges_sobel = filters.sobel(self.seismic_data)
            self.ax.clear()
            self.ax.imshow(np.transpose(edges_sobel), cmap='gray', aspect='auto')
            self.ax.set_title("Seismic Image with Sobel Edge Detection")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)

    def plot_instantaneous_amplitude(self):
        """Plot the instantaneous amplitude of the seismic data."""
        try:
            instamplitude = [instantaneous_attributes(trace, self.sample_rate)['instantaneous_amplitude'] for trace in self.seismic_data]
            self.ax.clear()
            self.ax.imshow(np.transpose(instamplitude), cmap='hot', aspect='auto')
            self.ax.set_title("Instantaneous Amplitude")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)

    def plot_instantaneous_phase(self):
        """Plot the instantaneous phase of the seismic data."""
        try:
            instaphase = [instantaneous_attributes(trace, self.sample_rate)['instantaneous_phase'] for trace in self.seismic_data]
            self.ax.clear()
            self.ax.imshow(np.transpose(instaphase), cmap='viridis', aspect='auto')
            self.ax.set_title("Instantaneous Phase")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)

    def plot_instantaneous_frequency(self):
        """Plot the instantaneous frequency of the seismic data."""
        try:
            instafreq = [instantaneous_attributes(trace, self.sample_rate)['instantaneous_frequency'] for trace in self.seismic_data]
            self.ax.clear()
            self.ax.imshow(np.transpose(instafreq), cmap='plasma', aspect='auto')
            self.ax.set_title("Instantaneous Frequency")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)
    
    def plot_seismic_data(self):
        """Plot the seismic data on the canvas."""
        try:
            self.ax.clear()
            self.ax.imshow(np.transpose(self.seismic_data), cmap='seismic', aspect='auto')
            self.ax.set_title("Seismic Data")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")
            self.canvas.draw()
        except Exception as e:
            print("Error:", e)

    def extract_and_plot_horizons(self):
        """Extract horizons from the seismic data and plot them on the seismic image."""
        try:
            edges_sobel = filters.sobel(self.seismic_data)
            thresh = filters.threshold_otsu(edges_sobel)
            binary_image = edges_sobel > thresh

            labeled_image = label(binary_image)
            regions = regionprops(labeled_image)

            self.ax.clear()
            self.ax.imshow(np.transpose(self.seismic_data), cmap='seismic', aspect='auto')
            self.ax.set_title("Seismic Image with Detected Horizons")
            self.ax.set_xlabel("Trace Number")
            self.ax.set_ylabel("Two Way Travel Time (ms)")

            for region in regions:
                min_row, min_col, max_row, max_col = region.bbox
                trace_coords = (min_col + max_col) / 2
                sample_coords = (min_row + max_row) / 2
                self.ax.scatter(sample_coords, trace_coords, color='red', s=5)  # Mark horizon points with red dots

            self.canvas.draw()
        except Exception as e:
            print("Error:", e)
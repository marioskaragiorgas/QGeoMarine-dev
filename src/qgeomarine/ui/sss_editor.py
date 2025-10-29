"""
sss_editor.py

This module provides the a GUI editor for editing and analysing Side Scan Sonar (SSS) data.

"""

import sys 
from pathlib import Path
import re
import numpy as np
import logging
import sqlite3
import pandas as pd
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QTableWidgetItem, QTreeWidgetItem, QHeaderView, QComboBox,
    QVBoxLayout, QWidget, QFileDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, pyqtSlot, QThread
from qgeomarine.ui.ui import SSSonar_Editor_UI
from qgeomarine.data_io.sonar_io import XTF
from qgeomarine.core.processing.sss_processing import ManualBottomTrack
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(levelname)s - %(message)s", 
    stream=sys.stdout
    )

class FileParseWorker(QThread):
    """
    Worker thread for parsing side scan sonar (SSS) data from XTF files in the background.
    This class handles the parsing of SSS data from a file and emits signals when finished or if an error occurs.
    
    It uses the SSSHandler to load sonar pings from a binary file.
    Attributes:
        finished (pyqtSignal): Signal emitted when parsing is finished.
        error (pyqtSignal): Signal emitted when an error occurs during parsing.
        file_path (str): Path to the seismic database file to be parsed.
        sss_handler (SSSHandler): Handler for reading SSS data from the binary file.

    Methods:
        run(): The main method that runs in the background thread to parse the SSS file.
        It retrieves the sample interval, sample rate, data format, and trace data, and emits the results.
        It handles exceptions and emits error messages if any issues occur during parsing.
    """

    finished = pyqtSignal(object)  # Signal to emit when parsing is finished
    error = pyqtSignal(str)        # Signal to emit when an error occurs

    def __init__(self, file_path, frequency):
        """
        Initializes the FileParseWorker with the given file path.
        Args:
            file_path (str): Path to the sonar database file to be parsed.
        """
        super().__init__()
        self.file_path = file_path
        self.freq = frequency
        self.sss_handler = XTF(db_file_path=self.file_path, bin_file_path=None)
        self.sss_processor = ManualBottomTrack(db_path=self.file_path, freq=self.freq, side=None)
        self.sss_info = {}

    def run(self):
        """
        The main method that runs in the background thread to parse the SSS file.
        It retrieves the sample interval, sample rate, data format, and trace data from the SSS database.
        It emits the results when parsing is finished or emits an error message if any issues occur.
        This method is executed when the thread is started.
        """

        try:
            # loader; returns A of shape (P,N) and meta containing dtype, etc.
            A_port, meta_port = self.sss_processor.load_pings_from_bin_freq('port')
            A_stbd, meta_stbd = self.sss_processor.load_pings_from_bin_freq('stbd')
            if meta_port.dtype == "uint16":
                A_port = A_port.astype(np.float32) / 65535.0
            if meta_stbd.dtype == "uint16":
                A_stbd = A_stbd.astype(np.float32) / 65535.0

            # Load ping metadata and make sure both sides have same number of pings
            ping_ids_p, alt_p, dt_p, bps_p, bin_path_p, P_p = self.sss_processor.load_ping_metadata("port")
            ping_ids_s, alt_s, dt_s, bps_s, bin_path_s, P_s = self.sss_processor.load_ping_metadata("stbd")
            if not np.array_equal(ping_ids_p, ping_ids_s):
                P0 = min(len(ping_ids_p), len(ping_ids_s), A_port.shape[0], A_stbd.shape[0])
                A_port, A_stbd = A_port[:P0, :], A_stbd[:P0, :]
                ping_ids = ping_ids_p[:P0]
                alt, dt = alt[:P0], dt[:P0]
                P = P0
                logging.warning(f"Ping IDs mismatch between sides. Truncating to min {P0} pings.")
            
            elif A_port.shape[0] != P_p or A_stbd.shape[0] != P_s:
                P0 = min(A_port.shape[0], A_stbd.shape[0], P_p, P_s)
                A_port, A_stbd = A_port[:P0, :], A_stbd[:P0, :]
                alt, dt = alt_p[:P0], dt_p[:P0]
                P = P0
                logging.warning(f"Pings mismatch: port has {A_port.shape[0]}, stbd has {A_stbd.shape[0]}, DB has {P_p} and {P_s}. Truncating to min {P0}.")

            else:
                ping_ids = ping_ids_p
                alt, dt = alt_p, dt_p
                P = P_p

            result = {'data_port': A_port, 'data_stbd': A_stbd, 'ping_ids_port': ping_ids_p, 'ping_ids_starboard': ping_ids_s,
                      'ping_ids': ping_ids, 'alt': alt, 'dt': dt, 'P': P, 'meta_port': meta_port, 
                      'meta_stbd': meta_stbd}
            
            self.finished.emit(result)

        except Exception as e:
            logging.error(f"Error during file parsing: {e}")
            self.error.emit(str(e))

class SSS_Editor(QtWidgets.QMainWindow, SSSonar_Editor_UI):
    def __init__(self, db_file_path, frequency, parent=None):
        super().__init__(parent)
        self.ui = SSSonar_Editor_UI()
        self.ui.setupUI(self)
        self.db_file_path = db_file_path
        self.frequency = frequency
        self.sss_handler = XTF(db_file_path=self.db_file_path, bin_file_path=None)
        self.sss_file_info = {}
        self.bottom_track_processed = {}
        # BT state
        self.bt_mode = False
        self.bt_points_port = []     # list of (ping_idx, sample_idx) in RAW array coords (no mirroring)
        self.bt_points_stbd = []
        self.bt_curve_port = None
        self.bt_curve_stbd = None
        self.bt_scatter_port = None
        self.bt_scatter_stbd = None
        self.bt_masked_port = None   # last masked arrays (for redraw)
        self.bt_masked_stbd = None

        # Keep a reference to your processor if you’ll persist tracks
        self.bt_processor = ManualBottomTrack(db_path=self.db_file_path, freq=self.frequency, side=None)


        # ==== connect Menu actions ====== #
        # connect view toggles
        self.ui.view_raw_split_action.triggered.connect(lambda _: self.show_split(np.flip(self.sss_file_info['data_port'], axis=1), self.sss_file_info['data_stbd'], xgr_port=None, xgr_stbd=None))
        self.ui.view_raw_stitched_action.triggered.connect(lambda _: self.show_stitched(self.sss_file_info['data_port'], self.sss_file_info['data_stbd'], xgr_port=None, xgr_stbd=None))
        self.ui.view_raw_split_action.triggered.connect(self.view_split)
        self.ui.view_raw_stitched_action.triggered.connect(self.view_stitched)
                                                                                      

        # connect bottom track actions
        self.ui.bt_manual_action.triggered.connect(self.run_manual_bottom_track)
        self.ui.bt_clear_action.triggered.connect(self.clear_bottom_track)
        

        
        # Check if the file path is valid before parsing
        if db_file_path and frequency:
            logging.info(f"Database path: {db_file_path}")
            logging.info(f"Frequency: {frequency}")

            self.start_file_parsing(db_file_path, frequency)
            
        else:
            logging.error("Invalid seismic database path or frequency provided.")
            #self.data_info_label.setText("Invalid seismic database path or frequency provided.")

    def start_file_parsing(self, db_file_path, frequency):
        """
        Initiates parsing of the specified file in a separate thread.

        This method updates the UI to indicate that data is being loaded, creates a worker thread to parse the file,
        and connects the worker's signals to appropriate handler methods for completion and error events.

        Args:
            file_path (str): The path to the file to be parsed.
        """
        #self.data_info_label.setText("Loading data...")  # Update UI to indicate loading
        self.worker = FileParseWorker(db_file_path, frequency)
        self.worker.finished.connect(self.on_parsing_finished)
        self.worker.error.connect(self.on_parsing_error)
        self.worker.start()  # Start the worker thread

    def on_parsing_finished(self, result):
        """
        Handles the completion of the side scan sonar data parsing process.
        Updates internal data attributes with the parsed results, refreshes UI elements to display
        information about the loaded side scan sonar data, and updates the tree view with file and data details.
        Finally, triggers plotting of the raw side scan sonar waterfall plot image.

        Args:
            result (dict): A dictionary containing parsed side scan sonar data and metadata, including:
                - 'A_port': Numpy array of port channel data.
                - 'A_stbd': Numpy array of starboard channel data.
                - 'ping_ids_port': List of ping IDs for the port channel.
                - 'ping_ids_starboard': List of ping IDs for the starboard channel.
                - 'ping_ids': List of common ping IDs.
                - 'alt': Numpy array of altitudes.
                - 'dt': Numpy array of delta times.
                - 'P': Number of pings.
                - 'meta_port': Metadata for the port channel.
                - 'meta_stbd': Metadata for the starboard channel.
        """

        self.sss_file_info = result
        logging.info("SSS file parsing completed successfully.")

        self.show_split(port=np.flip(result['data_port'], axis=1), stbd=result['data_stbd'])
    def on_parsing_error(self, error_message):
        """Handle errors during parsing."""
        logging.error(f"Parsing error: {error_message}")
        #self.data_info_label.setText(f"Error loading data: {error_message}")
       
       
    def _common_levels(self, port, stbd):
        low = np.percentile(np.hstack([port.ravel(), stbd.ravel()]), 1)
        high = np.percentile(np.hstack([port.ravel(), stbd.ravel()]), 99)
        return float(low), float(high)

    def _range_per_sample_m(self):
        # Best-effort physical scaling (slant range): dx = c*dt/2
        # dt may be per-ping array; use median
        dt = np.asarray(self.sss_file_info.get('dt', None))
        if dt is None or dt.size == 0:
            return None
        c = 1500.0  # m/s (typical sound speed; tweak if you store exact value)
        return (c * float(np.median(dt))) / 2.0

    def show_split(self, port=None, stbd=None, xgr_port=None, xgr_stbd=None):
        """Symmetric split view with linked Y (recommended default)."""

        if port is None or stbd is None:
            logging.warning("Port or starboard data not available for split view.")
            return

        P, N = port.shape
        low, high = self._common_levels(port, stbd)

        # --- Rebuild layout completely (safe clear) ---
        self.ui.plotWidget.clear()
        self.ui.plotWidget.setRenderHints(self.ui.plotWidget.renderHints() | QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        
        # --- Create two plots side by side ---
        self.ui.plot_port = self.ui.plotWidget.addPlot(row=0, col=0)
        self.ui.plot_stbd = self.ui.plotWidget.addPlot(row=0, col=1)
        self.ui.plot_port.setTitle("Port Channel")
        self.ui.plot_stbd.setTitle("Starboard Channel")
        

        # --- Configure both plots ---
        for plot in (self.ui.plot_port, self.ui.plot_stbd):
            vb = plot.getViewBox()
            vb.invertY(True)  # ping 0 at top (waterfall orientation)
            vb.setAspectLocked(False)
            vb.setLimits(xMin=0, xMax=N - 1, yMin=0, yMax=P - 1)
            vb.setRange(xRange=(0, N - 1), yRange=(0, P - 1))
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setLabel("bottom", "Sample (index)")
            plot.setLabel("left", "Ping")

        # Mirror only LEFT (Port) so nadir is centered
        self.ui.plot_port.getViewBox().invertX(True)
        self.ui.plot_stbd.getViewBox().invertX(False)

        # Link vertical axes
        self.ui.plot_port.setYLink(self.ui.plot_stbd)

        # Reuse your existing ImageItems
        self.ui.img_port = pg.ImageItem(axisOrder="row-major")
        self.ui.img_stbd = pg.ImageItem(axisOrder="row-major")
        self.ui.img_port.setImage(port, autoLevels=False, levels=(low, high))
        self.ui.img_stbd.setImage(stbd, autoLevels=False, levels=(low, high))

        
        # Make image’s data coordinates be meters on x and pings on y if the data are slant range corrected after bottom track:
        if xgr_port is not None and xgr_stbd is not None:
            rect_port = QtCore.QRectF(0.0, 0.0, float(xgr_port[-1] - xgr_port[0]), float(port.shape[0]))
            self.ui.img_port.setRect(rect_port)
            rect_stbd = QtCore.QRectF(0.0, 0.0, float(xgr_stbd[-1] - xgr_stbd[0]), float(stbd.shape[0]))
            self.ui.img_stbd.setRect(rect_stbd)

        self.ui.plot_port.addItem(self.ui.img_port)
        self.ui.plot_stbd.addItem(self.ui.img_stbd)
        
        # toggle checks
        self.ui.view_split_action.setChecked(True)
        self.ui.view_stitched_action.setChecked(False)

        self.statusBar().showMessage("Split view ready.")

    def show_stitched(self, port=None, stbd=None, xgr_port=None, xgr_stbd=None, gap_cols: int = 0):
        """Display a single stitched waterfall image across the full panel."""
        
        if port is None or stbd is None:
            logging.warning("Port or starboard data not available for stitched view.")
            return

        P, N = port.shape

        # Combine port (flipped) and stbd with an optional nadir gap
        left = port
        gap = np.zeros((P, gap_cols), dtype=port.dtype) if gap_cols > 0 else None
        stitched = np.hstack([left, gap, stbd]) if gap is not None else np.hstack([left, stbd])

        low, high = np.percentile(stitched, [1, 99])

        # --- Rebuild layout (this removes any previous ImageItems) ---
        self.ui.plotWidget.clear()
        self.ui.plotWidget.setRenderHints(self.ui.plotWidget.renderHints() | QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        self.ui.plot_full = self.ui.plotWidget.addPlot(row=0, col=0)
        self.ui.plot_full.setTitle("Waterfall (Port + Starboard)")
        self.ui.plot_full.setLabel("left", "Ping")
        self.ui.plot_full.setLabel("bottom", "Sample (index)")
        self.ui.plot_full.showGrid(x=True, y=True, alpha=0.25)

        vb = self.ui.plot_full.getViewBox()
        vb.invertY(True)
        vb.setAspectLocked(False)
        vb.setLimits(xMin=0, xMax=stitched.shape[1] - 1, yMin=0, yMax=P - 1)
        vb.setRange(xRange=(0, stitched.shape[1] - 1), yRange=(0, P - 1))

        # --- New ImageItem ---
        self.ui.img_full = pg.ImageItem(axisOrder="row-major")
        self.ui.img_full.setImage(stitched, autoLevels=False, levels=(low, high))
        
        # Make image’s data coordinates be meters on x and pings on y if the data are slant range corrected after bottom track:
        if xgr_port is not None and xgr_stbd is not None:
            dx_port = xgr_port[1] - xgr_port[0] if len(xgr_port) > 1 else 1.0
            dx_stbd = xgr_stbd[1] - xgr_stbd[0] if len(xgr_stbd) > 1 else 1.0
            dx_gap = gap_cols * (dx_port + dx_stbd) / 2.0 if gap_cols > 0 else 0.0
            total_length = (xgr_port[-1] - xgr_port[0]) + dx_gap + (xgr_stbd[-1] - xgr_stbd[0])
            rect = QtCore.QRectF(0.0, 0.0, float(total_length), float(P))
            self.ui.img_full.setRect(rect)
            self.ui.plot_full.setLabel("bottom", "Slant range (m)")
        
        self.ui.plot_full.addItem(self.ui.img_full)

            

        # Update menu toggles
        self.ui.view_split_action.setChecked(False)
        self.ui.view_stitched_action.setChecked(True)

        self.statusBar().showMessage("Stitched view ready.")

    def run_manual_bottom_track(self):
        """
        Launch the manual bottom tracking tool using the loaded sonar data.
        """
        if not self.sss_file_info:
            QtWidgets.QMessageBox.warning(self, "No Data", "Please load a sonar file first.")
            return

        # Extract port/stbd arrays
        port = self.sss_file_info["data_port"]
        stbd = self.sss_file_info["data_stbd"]

        # Ask user which side(s) to track
        choice = QtWidgets.QMessageBox.question(
            self,
            "Manual Bottom Track",
            "Pick bottom on both sides?\n\nYes = Dual mode\nNo = Single combined waterfall.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        tracker = ManualBottomTrack(
            db_path=self.db_file_path,
            freq=self.frequency,
            side=None,
        )

        # Run manual track using the ManualBottomTrack methods
        # 1) pick bottom indices
        if choice == QtWidgets.QMessageBox.StandardButton.Yes:
            bottom_idx_port, bottom_idx_stbd = tracker.pick_bottom_indices_pg_dual(np.flip(port, axis=1), stbd)
            self.bottom_track = {"port": bottom_idx_port, "stbd": bottom_idx_stbd}
        else:
            # stitched = np.hstack([np.fliplr(port), stbd]) if you want single image
            bottom_idx_stbd = tracker.pick_bottom_indices_pg(stbd)
            self.bottom_track = {"stbd": bottom_idx_stbd}

        # 2) zero water column and ground-range correction
        alt = self.sss_file_info["alt"]
        dt = self.sss_file_info["dt"]
        A_gr_port, xgr_port, dx_port = tracker.slant_to_ground_range(tracker.remove_water_column(np.flip(port, axis=1), bottom_idx_port), bottom_idx_port, dt, alt)
        A_gr_stbd, xgr_stbd, dx_stbd = tracker.slant_to_ground_range(tracker.remove_water_column(stbd, bottom_idx_stbd), bottom_idx_stbd, dt, alt)

        # 3) Store processed bottom track data if needed
        self.bottom_track_processed = {
            "port": {"A_gr": A_gr_port, "xgr": xgr_port, "dx": dx_port},
            "stbd": {"A_gr": A_gr_stbd, "xgr": xgr_stbd, "dx": dx_stbd},
        }

        # 4) Display the information message with logging message and statusbar
        logging.info("Manual bottom track completed.")
        self.statusBar().showMessage("Manual bottom track completed.")
        QMessageBox.information(self, "Bottom Track", "Manual bottom track completed successfully.")
    
    def run_slant_range_correction(self):
        """
        Apply slant range correction using the last manual bottom track.
        """
        if not hasattr(self, "bottom_track_processed"):
            QtWidgets.QMessageBox.warning(self, "No Bottom Track", "Please perform bottom tracking first.")
            return

        port_data = self.bottom_track_processed.get("port", None)
        stbd_data = self.bottom_track_processed.get("stbd", None)

        if port_data:
            self.show_split(
                port=port_data["A_gr"],
                stbd=stbd_data["A_gr"] if stbd_data else self.sss_file_info["data_stbd"],
                xgr_port=port_data["xgr"] if port_data else None,
                xgr_stbd=stbd_data["xgr"] if stbd_data else None,
            )
        else:
            self.show_stitched(
                port=port_data["A_gr"] if port_data else np.flip(self.sss_file_info["data_port"], axis=1),
                stbd=stbd_data["A_gr"],
                xgr_port=port_data["xgr"] if port_data else None,
                xgr_stbd=stbd_data["xgr"] if stbd_data else None,
            )

        logging.info("Slant range correction applied.")
        self.statusBar().showMessage("Slant range correction applied.")
    def show_bottom_track_overlay(self):
        """
        Overlay the bottom track(s) as colored curves on the current plot(s).
        """
        if not hasattr(self, "bottom_track"):
            return

        # Clear old lines first
        self.ui.plot_port = self.ui.plotWidget.getItem(row=0, col=0)
        self.ui.plot_stbd = self.ui.plotWidget.getItem(row=0, col=1)
        for plot in [self.ui.plot_port, self.ui.plot_stbd]:
            for item in plot.listDataItems():
                if isinstance(item, pg.PlotDataItem) and item.name() in ("bottom_port", "bottom_stbd"):
                    plot.removeItem(item)

        if "port" in self.bottom_track:
            curve_port = pg.PlotDataItem(
                self.bottom_track["port"],
                np.arange(len(self.bottom_track["port"])),
                pen=pg.mkPen("r", width=2),
                name="bottom_port"
            )
            self.ui.plot_port.addItem(curve_port)

        if "stbd" in self.bottom_track:
            curve_stbd = pg.PlotDataItem(
                self.bottom_track["stbd"],
                np.arange(len(self.bottom_track["stbd"])),
                pen=pg.mkPen("y", width=2),
                name="bottom_stbd"
            )
            self.ui.plot_stbd.addItem(curve_stbd)

        self.statusBar().showMessage("Manual bottom track applied.")

    def clear_bottom_track(self):
        """Remove any bottom track overlays."""
        self.ui.plot_port = self.ui.plotWidget.getItem(row=0, col=0)
        self.ui.plot_stbd = self.ui.plotWidget.getItem(row=0, col=1)
        for plot in [self.ui.plot_port, self.ui.plot_stbd]:
            for item in plot.listDataItems():
                if isinstance(item, pg.PlotDataItem) and item.name() in ("bottom_port", "bottom_stbd"):
                    plot.removeItem(item)
        if hasattr(self, "bottom_track"):
            del self.bottom_track
        self.statusBar().showMessage("Bottom track cleared.")

    def view_split(self):
        """Show split ground-range images if bottom tracking exists."""
        data = getattr(self, "bottom_track_processed", None)
        if not data or "port" not in data or "stbd" not in data:
            QtWidgets.QMessageBox.warning(self, "No Bottom Track", "Please perform bottom tracking first.")
            return

        self.show_split(
            data["port"]["A_gr"],
            data["stbd"]["A_gr"],
            data["port"]["xgr"],
            data["stbd"]["xgr"]
        )

    def view_stitched(self):
        """Show stitched ground-range image if bottom tracking exists."""
        data = getattr(self, "bottom_track_processed", None)
        if not data or "stbd" not in data or "port" not in data:
            QtWidgets.QMessageBox.warning(self, "No Bottom Track", "Please perform bottom tracking first.")
            return

        self.show_stitched(
            data["port"]["A_gr"],
            data["stbd"]["A_gr"],
            data["port"]["xgr"],
            data["stbd"]["xgr"]
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = SSS_Editor()
    main_window.show()
    sys.exit(app.exec())
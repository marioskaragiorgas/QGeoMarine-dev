"""
Mute.py

Muting is a common technique used in seismic data processing,
particularly in the field of geophysics. It involves suppressing
or "muting" certain parts of the seismic data that are deemed to be noise,
unwanted reflections, or irrelevant to the analysis. The goal of muting is
to enhance the quality of the seismic signal and make it easier to interpret the data.
This script contains the basic muting techniques stored in a Mute class.
"""

import numpy as np
from matplotlib.widgets import PolygonSelector
from matplotlib.path import Path

class Mute:

    def __init__(self, parent = None):
        self.parent = parent
        self.mute_polygon = None
        self.selector = None

    @staticmethod
    def top_mute(data, mute_time, sample_interval):
        
        """
        Apply top mute to the seismic data. This technique mutes the early
        part of the seismic data, usually near the surface, where unwanted
        noise (e.g., ground roll or direct waves) is dominant. The top mute 
        removes these early arrivals, which are not of interest for deeper 
        subsurface exploration.
        
        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - mute_time: Time (in seconds) before which the data should be muted.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        mute_sample = int(mute_time / sample_interval)
        muted_data = np.copy(data)
        muted_data[:, :mute_sample] = 0
        
        return muted_data
    
    @staticmethod
    def bottom_mute(data, mute_time, sample_interval):
        
        """"
        Apply bottom mute to the seismic data. This technique is applied to the later part
        of the seismic data, where the signal is weak or where multiple reflections and noise dominate. 
        By muting these later arrivals, the interpreter can focus on the primary reflections that are more relevant.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - mute_time: Time (in seconds) after which the data should be muted.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        mute_sample = int(mute_time / sample_interval)
        muted_data = np.copy(data)
        muted_data[:, mute_sample:] = 0
        
        return muted_data
    
    @staticmethod
    def offset_mute(data, offsets, mute_offset):
        
        """
        Apply offset mute to the seismic data. Offset muting is applied based
        on the distance between the seismic source and the receivers. Seismic traces at 
        far offsets (large distances) may be muted because they often contain more noise 
        and less useful signal compared to near-offset traces.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - offsets: 1D numpy array containing the offsets for each trace.
        - mute_offset: The offset (in meters) after which the data should be muted.

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        muted_data = np.copy(data)
        for i, offset in enumerate(offsets):
            if offset > mute_offset:
                muted_data[i, :] = 0
        
        return muted_data

    @staticmethod
    def time_variant_mute(data, initial_time, final_time, sample_interval):
        
        """
        Apply time-variant mute to the seismic data. This technique progressively mutes 
        the data over time, which can be useful when certain noise or unwanted reflections 
        vary with time. For instance, in a marine seismic survey, the seabed reflections 
        might be stronger initially and fade out with depth, requiring a mute that adapts over time.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - initial_time: Time (in seconds) when the mute starts.
        - final_time: Time (in seconds) when the mute ends.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        num_samples = data.shape[1]
        mute_start_sample = int(initial_time / sample_interval)
        mute_end_sample = int(final_time / sample_interval)
        
        muted_data = np.copy(data)
        for trace in muted_data:
            for i in range(mute_start_sample, mute_end_sample):
                factor = (i - mute_start_sample) / (mute_end_sample - mute_start_sample)
                trace[i] *= (1 - factor)
        
        return muted_data

    def interactive_mute(self, ax, data):
        
        """
        Enable interactive mute using a polygon drawn by the user. This technique allows
        for precise muting of specific areas within the seismic data based on user-defined polygons.
        This is particularly useful for complex noise patterns that cannot be easily addressed
        with standard muting techniques.

        Parameters:
        - ax: Matplotlib axis on which the data is plotted.
        - data: 2D numpy array where each row represents a seismic trace.

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        self.mute_polygon = None
        self.data = data
        self.selector = PolygonSelector(ax, self.on_select_polygon, useblit=True)
        print("Draw the mute polygon on the plot and press 'Enter' or double-click to finish.")

    def on_select_polygon(self, verts):
        
        """
        Callback function when a polygon is drawn by the user.

        Parameters:
        - verts: Vertices of the polygon drawn by the user.

        Updates:
        - self.mute_polygon: The vertices of the drawn polygon.
        """

        self.mute_polygon = np.array(verts)
        
        # Disconnect the PolygonSelector once the polygon is finalized
        self.selector.disconnect_events()  # Stop accepting new points
        self.selector = None  # Clear the selector to prevent further modifications
        
        print(f"Polygon closed with vertices: {self.mute_polygon}")
        
       # Apply mute based on the drawn polygon
        muted_data = self.apply_polygon_mute()  # Update the seismic data

        # Update the processed data in the GUI
        self.parent.processed_data = muted_data  # parent is the GUI instance

        # Call the GUI to re-plot the muted data
        self.parent.plot_processed_seismic_image()  # Trigger the plot update

    def apply_polygon_mute(self):
        
        """
        Apply mute based on the polygon drawn interactively by the user.

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        if self.mute_polygon is None or self.data is None:
            return self.data
        
        # Create a mask to mute the data within the polygon
        mask = np.zeros_like(self.data, dtype=bool)
        for i, trace in enumerate(self.data):  # Iterate over traces
            for j, _ in enumerate(trace):  # Iterate over samples
                if self.is_inside_polygon(i, j):
                    mask[i, j] = True
        
        muted_data = np.where(mask, 0, self.data)
        print("User interactive mute applied.")
        return muted_data

    def is_inside_polygon(self, x, y):
        
        """
        Check if a point (x, y) is inside the polygon.

        Parameters:
        - x: X-coordinate (trace index).
        - y: Y-coordinate (time index).

        Returns:
        - Boolean value indicating whether the point is inside the polygon.
        """

        return Path(self.mute_polygon).contains_point((x, y))
    
    
class PredefinedMute:
    
    @staticmethod
    def shallow_zone_mute(data, sample_interval):
        
        """
        Apply a predefined shallow zone mute. This mute is typically used to remove 
        the top 200ms of the data where noise from shallow reflections or surface waves 
        may dominate.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        mute_time = 0.2  # 200ms shallow mute
        return Mute.top_mute(data, mute_time, sample_interval)

    @staticmethod
    def deep_zone_mute(data, sample_interval):
        
        """
        Apply a predefined deep zone mute. This mute is typically used to remove the 
        bottom 200ms of the data where signal strength is low, and noise or multiple reflections 
        may be more prominent.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """

        mute_time = data.shape[1] * sample_interval - 0.2  # Bottom 200ms mute
        return Mute.bottom_mute(data, mute_time, sample_interval)

    @staticmethod
    def marine_direct_wave_mute(data, sample_interval):
        
        """
        Apply a predefined mute to remove the direct wave in marine seismic data. 
        The direct wave is the initial strong wave that travels directly from the source 
        to the receiver, often considered noise in the context of subsurface imaging.

        Parameters:
        - data: 2D numpy array where each row represents a seismic trace.
        - sample_interval: The time interval between samples (in seconds).

        Returns:
        - Muted seismic data as a 2D numpy array.
        """
        
        mute_time = 0.1  # 100ms to remove the direct wave
        return Mute.top_mute(data, mute_time, sample_interval)
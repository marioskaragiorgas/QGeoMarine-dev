"""
trace_qc.py
"""
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)

class TraceQC:
    """
    TraceQC performs quality control checks on seismic trace data.
    It can detect:
        - Dead traces (all zeros or constant values)
        - Clipped traces (high amplitude spikes)
        - Low amplitude or flat traces

    Methods:
        - detect_dead_traces
        - detect_clipped_traces
        - detect_low_energy_traces
        - annotate_traces (optional visualization helper)
    """

    def __init__(self, threshold_dead=1e-6, clip_threshold=0.95, energy_threshold=1e-3):
        """
        Initialize the QC thresholds.

        Args:
            threshold_dead (float): Max amplitude below which a trace is considered dead.
            clip_threshold (float): Proportion of max value that triggers a clip warning.
            energy_threshold (float): RMS energy below which trace is flagged.
        """
        self.threshold_dead = threshold_dead
        self.clip_threshold = clip_threshold
        self.energy_threshold = energy_threshold

    def detect_dead_traces(self, data):
        """
        Identify traces that are effectively dead (zero or nearly constant).

        Args:
            data (ndarray): 2D seismic data (n_traces x n_samples)

        Returns:
            List[int]: Indices of dead traces
        """
        dead_indices = []
        for i, trace in enumerate(data):
            if np.all(np.abs(trace) < self.threshold_dead):
                dead_indices.append(i)
        logging.info(f"Detected {len(dead_indices)} dead traces.")
        return dead_indices

    def detect_clipped_traces(self, data):
        """
        Identify traces with clipping (many max or min values).

        Args:
            data (ndarray): 2D seismic data

        Returns:
            List[int]: Indices of clipped traces
        """
        clipped_indices = []
        for i, trace in enumerate(data):
            max_val = np.max(np.abs(trace))
            count_max = np.sum(np.abs(trace) > self.clip_threshold * max_val)
            if count_max > len(trace) * 0.1:  # 10% of samples are at clip level
                clipped_indices.append(i)
        logging.info(f"Detected {len(clipped_indices)} clipped traces.")
        return clipped_indices

    def detect_low_energy_traces(self, data):
        """
        Identify traces with very low RMS energy.

        Args:
            data (ndarray): 2D seismic data

        Returns:
            List[int]: Indices of low-energy traces
        """
        low_energy_indices = []
        for i, trace in enumerate(data):
            energy = np.sqrt(np.mean(trace ** 2))
            if energy < self.energy_threshold:
                low_energy_indices.append(i)
        logging.info(f"Detected {len(low_energy_indices)} low-energy traces.")
        return low_energy_indices

    def run_all_checks(self, data):
        """
        Run all QC checks and return a dictionary of results.

        Args:
            data (ndarray): 2D seismic data

        Returns:
            dict: {'dead': [...], 'clipped': [...], 'low_energy': [...]}
        """
        return {
            'dead': self.detect_dead_traces(data),
            'clipped': self.detect_clipped_traces(data),
            'low_energy': self.detect_low_energy_traces(data)
        }

    def annotate_traces(self, data, flagged_indices):
        """
        Helper method to mask or flag traces for visualization.

        Args:
            data (ndarray): Original seismic data
            flagged_indices (List[int]): Traces to highlight

        Returns:
            ndarray: Copy of data with flagged traces set to NaN
        """
        annotated = data.copy()
        for idx in flagged_indices:
            annotated[idx, :] = np.nan  # or use a distinct flagging approach
        return annotated

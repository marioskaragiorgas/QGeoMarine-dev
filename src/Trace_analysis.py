"""
Trace_analysis.py

This module provides a set of functions to analyze seismic traces using various signal processing techniques.
The primary analyses included are:
  - Periodogram: To estimate the power spectral density of a trace.
  - Welch Periodogram: An improved periodogram method to reduce noise by averaging.
  - Wavelet Transform: Continuous wavelet transform using the Ricker wavelet.
  - Spectrogram: Time-frequency analysis showing how spectral content changes over time.

Functions:
    trace_periodogram(trace, fs): Computes the periodogram of a seismic trace.
    trace_welch_periodogram(trace, fs): Computes the Welch periodogram of a seismic trace.
    trace_wavelet_transform(trace, widths): Computes the continuous wavelet transform (CWT) of a seismic trace.
    trace_spectrogram(trace, fs): Computes the spectrogram (time-frequency representation) of a seismic trace.
"""

import numpy as np
from scipy.signal import periodogram, welch, spectrogram, hilbert, cwt, ricker
from scipy.fft import fft, fftfreq

def trace_periodogram(trace, fs):

    """
    Compute the periodogram of a seismic trace.

    The periodogram estimates the power spectral density (PSD) of the signal, 
    showing the distribution of power into frequency components composing the signal.

    Parameters:
        trace (ndarray): The seismic trace to analyze.
        fs (float): The sampling frequency of the trace.

    Returns:
        tuple: Contains:
            - f (ndarray): Array of sample frequencies.
            - Pxx (ndarray): Power spectral density of the trace.
    """

    f, Pxx = periodogram(trace, fs)
    return f, Pxx

def trace_welch_periodogram(trace, fs):
    
    """
    Compute the Welch periodogram of a seismic trace.

    The Welch method is an improvement over the standard periodogram by splitting 
    the signal into overlapping segments, computing the periodogram of each segment, 
    and then averaging them. This helps reduce noise in the power spectral density estimate.

    Parameters:
        trace (ndarray): The seismic trace to analyze.
        fs (float): The sampling frequency of the trace.

    Returns:
        tuple: Contains:
            - f (ndarray): Array of sample frequencies.
            - Pxx (ndarray): Power spectral density of the trace using Welch's method.
    """

    f, Pxx = welch(trace, fs)
    return f, Pxx

def trace_wavelet_transform(trace, widths=None, wavelet=ricker, sampling_frequency=1.0):
    """
    Compute the continuous wavelet transform (CWT) of a seismic trace.

    The CWT provides a time-frequency representation of the signal. By default, it uses 
    the Ricker wavelet (also known as the "Mexican hat" wavelet), which is commonly used 
    for seismic analysis due to its similarity to seismic wavelets.

    Parameters:
        trace (ndarray): The seismic trace to analyze.
        widths (ndarray, optional): Widths of the wavelet. Determines the frequency scale. 
                                     Defaults to a range suitable for seismic data.
        wavelet (callable): The wavelet function to use. Defaults to `scipy.signal.ricker`.
        sampling_frequency (float): Sampling frequency of the seismic trace (Hz). Defaults to 1.0.

    Returns:
        tuple:
            - cwt_matrix (ndarray): CWT matrix where each row corresponds to a wavelet transform at a different width.
            - frequencies (ndarray): Approximate center frequencies corresponding to the wavelet widths.
    """
    # Default widths if none provided
    if widths is None:
        widths = np.arange(1, 128)  # Choose a reasonable default range

    # Compute the CWT
    cwt_matrix = cwt(trace, wavelet, widths)

    # Approximate center frequencies based on the widths
    frequencies = sampling_frequency / (widths * np.sqrt(2))

    return cwt_matrix, frequencies


def trace_spectrogram(trace, fs, window_duration=0.1, overlap=0.5, scaling='density', log_scale=False):
    """
    Compute the spectrogram of a seismic trace using short-time Fourier transform (STFT).
    
    Parameters:
        trace (ndarray): The seismic trace to analyze.
        fs (float): The sampling frequency of the trace.
        window_duration (float): Duration of the STFT window in seconds (default: 0.1).
        overlap (float): Fraction of overlap between windows (default: 0.5).
        scaling (str): Scaling of the spectrogram ('density' or 'spectrum').
        log_scale (bool): Whether to return the spectrogram in log scale (default: False).
    
    Returns:
        tuple:
            - f (ndarray): Array of sample frequencies [Hz].
            - t (ndarray): Array of time segments [s].
            - Sxx (ndarray): Spectrogram of the trace.
    """
    # Define the window length and overlap
    window_length = int(window_duration * fs)
    window = np.hanning(window_length)
    noverlap = int(window_length * overlap)
    nfft = max(256, 2 ** int(np.ceil(np.log2(window_length))))  # Power of 2 for FFT length

    # Compute the spectrogram
    f, t, Sxx = spectrogram(trace, fs, window=window, noverlap=noverlap, nfft=nfft, scaling=scaling)

    # Optionally convert to logarithmic scale
    if log_scale:
        Sxx = 10 * np.log10(Sxx + 1e-12)  # Add small value to avoid log(0)

    return f, t, Sxx

def tace_RMS(trace):
    """
    Compute the Root Mean Square (RMS) of a seismic trace.
    The Root Mean Square (RMS) of a seismic trace is a statistical
    measure that provides a single value representing the energy
    or amplitude of the signal over a specific time window. 
    Practical Significance of RMS in Seismic Data
    Amplitude Characterization:

    RMS provides a measure of the overall strength or energy of the seismic signal.
    It is often used to assess the reflectivity or energy of the subsurface layers.
    Seismic Attribute Analysis:

    RMS amplitude is a widely used seismic attribute for identifying hydrocarbon reservoirs.
    Areas with anomalously high RMS amplitudes might indicate the presence of gas-filled sands, oil-filled sands, or other geological features.
    Data Quality Assessment:

    RMS can help identify noisy or low-energy traces, which might indicate acquisition or processing issues.
    Windowed Analysis:

    By calculating RMS over specific time windows, geophysicists can analyze variations in amplitude with depth (or time) to identify geologically significant layers.
    Normalization:

    RMS is often used to normalize seismic data for further analysis or processing.
    
    """

    rms_trace  = np.sqrt(np.mean(trace**2))
    return rms_trace

def instantaneous_attributes(trace, fs):
    """
    Instantaneous attributes are derived from the analytic signal and provide information
    about the seismic trace at every point in time. The key instantaneous attributes are 
    instantaneous amplitude, instantaneous phase, and instantaneous frequency.
    """
    t = np.arange(len(trace)) / fs  # Time vector based on the sampling frequency

    # Compute the analytic signal using the Hilbert transform
    analytic_signal = hilbert(trace)

    # Compute instantaneous attributes
    instantaneous_amplitude = np.abs(analytic_signal)  # Instantaneous Amplitude
    instantaneous_phase = np.angle(analytic_signal)    # Instantaneous Phase
    
    # Instantaneous Frequency (derivative of unwrapped phase)
    unwrapped_phase = np.unwrap(instantaneous_phase)
    instantaneous_frequency = np.diff(unwrapped_phase) / (2.0 * np.pi * (t[1] - t[0]))
    
    # Pad to match original length
    instantaneous_frequency = np.concatenate(([instantaneous_frequency[0]], instantaneous_frequency))

    # Store all results in a dictionary
    attributes = {
        'instantaneous_amplitude': instantaneous_amplitude,
        'instantaneous_phase': instantaneous_phase,
        'instantaneous_frequency': instantaneous_frequency
    }

    return attributes

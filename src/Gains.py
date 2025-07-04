"""
Gains.py

This module contains functions for applying various gain adjustments to seismic data.
Gain functions are used to enhance or balance the amplitude of seismic traces during processing.

Functions:
    agc_gain(data, window_size): Applies Automatic Gain Control (AGC) to seismic data.
    tvg_gain(data, time_gradient): Applies Time-Variant Gain (TVG) to seismic data.
    constant_gain(data, gain_factor): Applies a constant gain factor to seismic data.
"""

import numpy as np

def agc_gain(data, window_size):
    
    """
    Apply Automatic Gain Control (AGC) to the seismic data.

    AGC normalizes the amplitude of seismic traces by dividing each trace by its 
    local RMS (Root Mean Square) value within a sliding window. This is useful for 
    compensating for amplitude variations caused by attenuation or other factors.

    Parameters:
        data (ndarray): 2D array of seismic data, where each row corresponds to a trace 
                        and each column represents a sample (n_traces, n_samples).
        window_size (int): The size of the sliding window used for gain normalization, in samples.

    Returns:
        agc_data (ndarray): 2D array of seismic data after applying AGC.
    """

    n_traces, n_samples = data.shape
    agc_data = np.zeros_like(data)
    
    # Apply AGC to each trace
    for i in range(n_traces):
        trace = data[i]
        # Compute the envelope (magnitude) of the trace
        envelope = np.abs(trace)
        
        # Calculate the local RMS (root mean square) within the window
        rms = np.sqrt(np.convolve(envelope**2, np.ones(window_size)/window_size, mode='same'))
        
        # Prevent division by zero by setting a minimum threshold
        rms[rms < 1e-10] = 1e-10
        
        # Normalize the trace by the local RMS to apply AGC
        agc_data[i] = trace / rms
    
    return agc_data


def tvg_gain(data, time_gradient):
    
    """
    Apply Time-Variant Gain (TVG) to the seismic data.

    TVG enhances the amplitude of seismic traces over time. As seismic signals 
    attenuate with time (depth), TVG compensates by applying an increasing gain 
    as the time/depth increases.

    Parameters:
        data (ndarray): 2D array of seismic data, where each row corresponds to a trace 
                        and each column represents a sample (n_traces, n_samples).
        time_gradient (float): The factor that controls the rate at which the gain increases over time. 
                               A higher value results in stronger gain applied to later samples.

    Returns:
        tvg_data (ndarray): 2D array of seismic data after applying TVG.
    """

    n_traces, n_samples = data.shape
    tvg_data = np.zeros_like(data)
    
    # Generate a time gain curve that increases with time
    time_curve = np.arange(1, n_samples + 1) ** time_gradient

    # Apply the time gain curve to each trace
    for i in range(n_traces):
        tvg_data[i] = data[i] * time_curve
    
    return tvg_data

def constant_gain(data, gain_factor):
    
    """
    Apply a Constant Gain to the seismic data.

    This function amplifies the entire seismic data by a constant factor. 
    It is useful when a uniform gain needs to be applied to all traces and samples.

    Parameters:
        data (ndarray): 2D array of seismic data, where each row corresponds to a trace 
                        and each column represents a sample (n_traces, n_samples).
        gain_factor (float): A constant factor used to amplify the seismic data.

    Returns:
        const_gain_data (ndarray): 2D array of seismic data after applying the constant gain.
    """
    
    const_gain_data = data * gain_factor
    return const_gain_data

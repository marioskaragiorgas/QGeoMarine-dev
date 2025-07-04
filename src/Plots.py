"""
Plots.py

This module contains functions for visualizing seismic data. It provides a variety of plotting methods, 
including plotting seismic traces, periodograms, Welch periodograms, wavelet transforms, spectrograms, 
and seismic images. The functions utilize Matplotlib for rendering the visualizations.

Functions:
    plot_trace(ax, trace, trace_number, delta): Plots a seismic trace.
    plot_periodogram(ax, f, Pxx, trace_number): Plots the periodogram of a seismic trace.
    plot_welch_periodogram(ax, f, Pxx, trace_number): Plots the Welch periodogram of a seismic trace.
    plot_wavelet_transform(ax, cwt_matrix, widths, trace_number): Plots the wavelet transform of a seismic trace.
    plot_spectrogram(ax, f, t, Sxx, trace_number): Plots the spectrogram of a seismic trace.
    plot_seismic_image(ax, seismic_data): Displays a seismic section as an image.
"""
import numpy as np

def plot_trace(ax, trace, trace_number, delta):
    
    """
    Plot the seismic trace on the given axis.

    Parameters:
        ax (matplotlib.axes.Axes): The axis on which to plot the trace.
        trace (ndarray): The seismic trace data (amplitude values).
        trace_number (int): The index of the seismic trace to be plotted.
        delta (float): The time interval between samples (sampling period).

    Returns:
        None: The trace is plotted on the provided Matplotlib axis.
    """
    # Compute the time axis based on sample interval (delta convetred in milliseconds)
    n_samples = len(trace)
    time_axis = np.arange(0, n_samples * delta, delta)
    ax.plot(time_axis, trace, color='black')
    ax.set_title(f"Seismic Trace {trace_number}")
    ax.set_xlabel("Tow Way Time (ms)")
    ax.set_ylabel("Amplitude")

def plot_periodogram(ax, f, Pxx, trace_number):
    
    """
    Plot the periodogram of a seismic trace.

    Parameters:
        ax (matplotlib.axes.Axes): The axis on which to plot the periodogram.
        f (ndarray): Array of sample frequencies.
        Pxx (ndarray): Power spectral density (PSD) values for each frequency.
        trace_number (int): The index of the seismic trace being analyzed.

    Returns:
        None: The periodogram is plotted on the provided Matplotlib axis.
    """

    ax.semilogy(f, Pxx, color = 'black')
    ax.set_title(f'Seismic Trace {trace_number} Periodogram')
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power/Frequency (dB/Hz)")

def plot_welch_periodogram(ax, f, Pxx, trace_number):
    
    """
    Plot the Welch periodogram of a seismic trace.

    Parameters:
        ax (matplotlib.axes.Axes): The axis on which to plot the Welch periodogram.
        f (ndarray): Array of sample frequencies.
        Pxx (ndarray): Power spectral density (PSD) values for each frequency using Welch's method.
        trace_number (int): The index of the seismic trace being analyzed.

    Returns:
        None: The Welch periodogram is plotted on the provided Matplotlib axis.
    """

    ax.semilogy(f, Pxx, color = 'black')
    ax.set_title(f"Seismic Trace {trace_number} Welch Periodogram")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power/Frequency (dB/Hz)")

def plot_wavelet_transform(ax, cwt_matrix, widths, trace_number):
    
    """
    Plot the wavelet transform of a seismic trace.

    Parameters:
        ax (matplotlib.axes.Axes): The axis on which to plot the wavelet transform.
        cwt_matrix (ndarray): The continuous wavelet transform (CWT) matrix. Each row corresponds to a different scale.
        widths (ndarray): Array of wavelet widths (scales) used for the transform.
        trace_number (int): The index of the seismic trace being analyzed.

    Returns:
        None: The wavelet transform is displayed as an image on the provided Matplotlib axis.
    """

    ax.imshow(np.abs(cwt_matrix), aspect='auto', extent=[0, len(cwt_matrix[0]), min(widths), max(widths)])
    ax.set_title(f"Seismic Trace {trace_number} Wavelet Transform")
    ax.set_xlabel("Sample")
    ax.set_ylabel("Scale")

def plot_spectrogram(ax, trace, fs):
    
    """
    Plot the spectrogram of a seismic trace.

    Parameters:
        ax (matplotlib.axes.Axes): The axis on which to plot the spectrogram.
        f (ndarray): Array of sample frequencies.
        t (ndarray): Array of time segments.
        Sxx (ndarray): Spectrogram matrix, representing the power at each time-frequency point.
        trace_number (int): The index of the seismic trace being analyzed.

    Returns:
        None: The spectrogram is displayed as a color map on the provided Matplotlib axis.
    """
    window = np.hanning(128)
    ax.specgram(trace, NFFT=128, Fs=fs, noverlap=120, cmap='jet', window=window, interpolation = 'bicubic')
    #ax.colorbar(label='Amplitude (dB)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title('Spectrogram with Hanning Window')

def plot_seismic_image(ax, seismic_data, delta):
    
    """Plot the seismic image with proper time scaling."""
    n_traces, n_samples = seismic_data.shape
    
    # Compute the time axis for the seismic image (in milliseconds)
    time_axis = np.arange(0, n_samples * delta, delta)
    
    # Plot the seismic image with time on the y-axis
    ax.imshow(np.transpose(seismic_data), cmap='seismic', aspect='auto', interpolation = 'bicubic',
                       extent=[0, n_traces, time_axis[-1], time_axis[0]])  # Time axis on y-axis
    ax.set_xlabel("Trace Number")
    ax.set_ylabel("Two-Way Travel Time (ms)")
    
"""""
    ax.imshow(seismic_data, cmap='seismic', aspect='auto')
    ax.set_xlabel('Trace')
    ax.set_ylabel('Two Way Time (ms)')
    

def plot_line_plotly(coordinates):
    
    #Plot seismic lines on a Plotly map.
        
    #Parameters:
    #    - coordinates: List of tuples [(lat1, lon1), (lat2, lon2), ...].
    
    try:
        if not coordinates:
            print("Error", "No seismic data available for plotting.")
            return

        # Prepare the seismic lines for plotting
        lats, lons = zip(*coordinates)
        print(f"lats:{lats}")
        print(f"lons:{lons}")

        # Create the Plotly map figure
        fig = go.Figure()

        # Add line
        fig.add_trace(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='lines',
            line=dict(width=2, color='blue'),
            name='Seismic Line'
        ))

        # Set the mapbox style and layout
        fig.update_layout(
            mapbox=dict(
                style="carto-positron",  # Offline-friendly map style
                center=dict(lat=lats[0], lon=lons[0]),
                zoom=10,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False
        )
        
        return fig
    except Exception as e:
        print(f"Error, Failed to create seismic lines map: {e}")
"""""
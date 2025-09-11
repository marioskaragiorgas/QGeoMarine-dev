"""
deconvolution.py

Deconvolution techniques are essential in seismic data processing for enhancing the temporal resolution of seismic signals. 
The primary goal of deconvolution is to compress the seismic wavelet into a spike, thereby retrieving the earth's reflectivity series. 
This script implements several key deconvolution methods, including spiking deconvolution, predictive deconvolution, 
and Wiener deconvolution. These methods help remove the effects of the seismic wavelet and attenuate multiples and reverberations, 
yielding a clearer image of subsurface structures.

Key concepts:
- **Convolutional Model:** The recorded seismic trace is a convolution of the earth’s impulse response with the seismic wavelet.
- **Wavelet Compression:** Deconvolution aims to compress the wavelet, ideally leaving only the earth's reflectivity.
- **Minimum Phase Assumption:** Deconvolution typically assumes that the seismic wavelet is minimum phase.
"""

import numpy as np
from scipy.signal import lfilter, correlate, wiener, chirp
from scipy.linalg import toeplitz
from scipy.optimize import minimize

class Wavelets:
    """
    A collection of static methods for generating and estimating seismic wavelets.
    This class provides various commonly used wavelet generators (Ricker, Ormsby, Klauder, minimum-phase, zero-phase, chirp, boomer)
    and several methods for estimating wavelets from seismic traces using autocorrelation, statistical assumptions, or matching filters.
    
    Methods:

    ricker(frequency, dt, length)
        Generate a Ricker (Mexican hat) wavelet.
    
    ormsby(t, f1, f2, f3, f4)
        Generate an Ormsby wavelet.
    
    klauder(t, f0, f1, t1)
        Generate a Klauder wavelet.
    
    minimum_phase(t, f)
        Generate a minimum-phase wavelet.
    
    zero_phase(t, f)
        Generate a zero-phase wavelet.
    
    chirp(duration, f0, f1, fs)
        Generate a linear chirp wavelet.
    
    boomer(t, f0, f1, duration)
        Generate a boomer wavelet.
    
    wavelet_autocorrelation(trace, wavelet_length)
    
    wavelet_statistically(trace, wavelet_length)
    
    estimate_wavelet_matching_filter(trace, reflector)
    """
    
    @staticmethod
    def ricker(frequency, dt, length):
        """
        Generates a Ricker (Mexican hat) wavelet.

        Parameters:
            frequency (float): Central frequency of the wavelet in Hz.
            dt (float): Sampling interval in seconds.
            length (float): Total length of the wavelet in seconds.

        Returns:
            numpy.ndarray: The normalized Ricker wavelet as a 1D array.

        Notes:
            The Ricker wavelet is commonly used in geophysics and signal processing as a model for seismic sources.
        """

        t = np.linspace(-length / 2, length / 2, int(length / dt))
        wavelet = (1 - 2 * (np.pi**2) * (frequency**2) * (t**2)) * np.exp(-(np.pi**2) * (frequency**2) * (t**2))
        return wavelet / np.max(np.abs(wavelet))
    
    @staticmethod
    def ormsby(t, f1, f2, f3, f4):
        """
        Generates an Ormsby wavelet for a given time array and frequency parameters.
        The Ormsby wavelet is a band-limited wavelet commonly used in seismic data processing.
        It is defined by four corner frequencies (f1, f2, f3, f4) and is constructed using a
        combination of sinc functions.
        Parameters
        ----------
        t : array_like or float
            Time or array of time samples at which to evaluate the wavelet.
        f1 : float
            Low-cut frequency (Hz). Frequencies below this are attenuated.
        f2 : float
            Low-pass frequency (Hz). Frequencies below this are passed.
        f3 : float
            High-pass frequency (Hz). Frequencies above this are passed.
        f4 : float
            High-cut frequency (Hz). Frequencies above this are attenuated.
        Returns
        -------
        a : float or ndarray
            The Ormsby wavelet evaluated at the given time(s).
        Notes
        -----
        - The function uses the normalized sinc function: np.sinc(x / np.pi).
        - The input frequencies must satisfy f1 < f2 < f3 < f4 for meaningful results.
        """

        def sinc(x):
            """
            Normalized sinc function.
            """
            return np.sinc(x / np.pi)
        
        a = (f4 - f3) * sinc(f4 * t) - (f3 - f2) * sinc(f3 * t) + (f2 - f1) * sinc(f2 * t) - f1 * sinc(f1 * t)
        return a / (f4 - f1)
    
    @staticmethod
    def klauder(t, f0, f1, t1):
        """
        Generates a Klauder wavelet signal.

        The Klauder wavelet is commonly used in seismic and signal processing applications. It is a type of linear frequency modulated (chirp) signal.

        Parameters:
            t (array_like): Time array over which to compute the wavelet.
            f0 (float): Starting frequency of the wavelet (Hz).
            f1 (float): Ending frequency of the wavelet (Hz).
            t1 (float): Duration of the wavelet (seconds).

        Returns:
            numpy.ndarray: The Klauder wavelet evaluated at each time in `t`.
        """

        return np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t**2 / (2 * t1)))
    
    @staticmethod
    def minimum_phase(t, f):
        """
        Generates a minimum phase wavelet using a Gaussian function.

        Parameters:
            t (float or np.ndarray): Time value(s) at which to evaluate the wavelet.
            f (float): Dominant frequency of the wavelet.

        Returns:
            float or np.ndarray: The value(s) of the minimum phase wavelet at time t.
        """

        a = 2 * (np.pi**2) * (f**2)
        return np.exp(-a * (t**2) / 2)
    
    @staticmethod
    def zero_phase(t, f):
        """
        Generates a zero-phase wavelet for a given time array and frequency.

        Parameters:
            t (array-like): Time values at which to evaluate the wavelet.
            f (float): Central frequency of the wavelet.

        Returns:
            numpy.ndarray: The zero-phase wavelet evaluated at the given time values.

        Notes:
            The function computes a Ricker (Mexican hat) wavelet, which is commonly used in seismic applications.
        """

        a = 2 * (np.pi**2) * (f**2)
        return np.cos(2 * np.pi * f * t) * np.exp(-a * (t**2) / 2)
                      
    @staticmethod
    def chirp(duration, f0, f1, fs):
        """
        Generates a linear chirp wavelet.

        Parameters:
            duration (float): Duration of the chirp in seconds.
            f0 (float): Starting frequency of the chirp in Hz.
            f1 (float): Ending frequency of the chirp in Hz.
            fs (float): Sampling frequency in Hz.

        Returns:
            numpy.ndarray: Array containing the generated chirp wavelet.
        """

        t = np.linspace(0, duration, int(fs * duration))
        wavelet = chirp(t, f0=f0, f1=f1, t1=duration, method='linear')
        return wavelet
    
    @staticmethod
    def boomer(t, f0, f1, duration):
        """
        Generates a synthetic boomer wavelet.

        Parameters
        ----------
        t : numpy.ndarray
            Array of time samples.
        f0 : float
            Starting frequency of the wavelet (Hz).
        f1 : float
            Ending frequency of the wavelet (Hz).
        duration : float
            Duration of the wavelet pulse (in the same units as t).

        Returns
        -------
        wavelet : numpy.ndarray
            The generated boomer wavelet as a numpy array.
        """

        wavelet = np.zeros_like(t)
        pulse_duration = duration / 2
        pulse = np.sin(2 * np.pi * np.linspace(f0, f1, int(pulse_duration * len(t))) * t[:int(pulse_duration * len(t))])
        wavelet[:len(pulse)] = pulse
        return wavelet
    
    @staticmethod
    def wavelet_autocorrelation(trace, wavelet_length):
        """
        Estimate the wavelet using the autocorrelation method.

        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - wavelet_length: Length of the estimated wavelet (int).

        Returns:
        - Estimated wavelet (1D numpy array).
        """
        autocorr = np.correlate(trace, trace, mode='full')[len(trace)-1:]
        wavelet = autocorr[:wavelet_length]
        return wavelet / np.max(np.abs(wavelet))  # Normalize the wavelet
    
    @staticmethod
    def wavelet_statistically(trace, wavelet_length):
        """
        Estimate the wavelet using statistical assumptions (e.g., minimum-phase).

        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - wavelet_length: Length of the estimated wavelet (int).

        Returns:
        - Estimated wavelet (1D numpy array).
        """
        autocorr = np.correlate(trace, trace, mode='full')[len(trace)-1:]
        wavelet_autocorr = autocorr[:wavelet_length]
        wavelet = np.linalg.solve(toeplitz(wavelet_autocorr[:-1]), wavelet_autocorr[1:])
        return np.append(1, -wavelet)  # Normalize with the first value as 1

    @staticmethod
    def estimate_wavelet_matching_filter(trace, reflector):
        """
        Estimate the wavelet using a matching filter with a known reflector.

        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - known_reflector: Known reflector (1D numpy array).

        Returns:
        - Estimated wavelet (1D numpy array).
        """
        wavelet = np.correlate(trace, reflector, mode='same')
        return wavelet / np.max(np.abs(wavelet))  # Normalize the wavelet


class Deconvolution:

    @staticmethod
    def spiking_deconvolution(trace, wavelet, noise_level=0.001):
        
        """
        Spiking Deconvolution (also known as least-squares inverse filtering) aims to compress the seismic wavelet 
        into a spike, effectively enhancing the resolution of the seismic data. This method assumes that the seismic 
        wavelet is minimum phase and that the trace can be represented as a convolution of this wavelet with the 
        earth's reflectivity series.

        Parameters:
        - trace: 1D numpy array, the seismic trace to be deconvolved.
        - wavelet: 1D numpy array, the estimated seismic wavelet.
        - noise_level: A small constant added to stabilize the inverse filter (default=0.001).

        Returns:
        - deconvolved_trace: 1D numpy array, the trace after spiking deconvolution.
        """

        autocorr = correlate(wavelet, wavelet, mode='full')
        mid_point = len(autocorr) // 2
        autocorr = autocorr[mid_point:]

        # Adding a small noise level to stabilize the inverse filter
        autocorr[0] += noise_level
        
        inverse_filter = np.linalg.inv(toeplitz(autocorr)).dot(np.eye(len(autocorr))[:, 0])
        deconvolved_trace = lfilter(inverse_filter, [1.0], trace)
        
        return deconvolved_trace
    
    @staticmethod
    def Spiking_Deconvolution(trace, wavelet_length):
        """
        Spiking deconvolution compresses the wavelet to a spike.
        
        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - wavelet_length: Length of the estimated wavelet (int).
        
        Returns:
        - Deconvolved trace (1D numpy array).
        """
        autocorr = np.correlate(trace, trace, mode='full')[len(trace)-1:]
        wavelet = autocorr[:wavelet_length]
        filter_coeffs = np.linalg.solve(
            toeplitz(wavelet),
            np.zeros(wavelet_length)
        )
        deconvolved_trace = np.convolve(trace, filter_coeffs, mode='same')
        return deconvolved_trace
    
    @staticmethod
    def predictive_deconvolution(trace, prediction_distance, filter_length, noise_level=0.001):
        
        """
        Predictive Deconvolution uses a prediction error filter to remove periodic components (such as multiples) 
        from the seismic trace. The technique aims to predict the primary reflections by filtering out predictable 
        (repeated) components (multiples, reverbations), enhancing the primary signal.

        Parameters:
        - trace: 1D numpy array, the seismic trace to be deconvolved.
        - prediction_distance: The lag distance for prediction.
        - filter_length: Length of the prediction error filter.
        - noise_level: A small constant added to stabilize the inverse filter (default=0.001).

        Returns:
        - deconvolved_trace: 1D numpy array, the trace after predictive deconvolution.
        """

        autocorr = correlate(trace, trace, mode='full')
        mid_point = len(autocorr) // 2
        autocorr = autocorr[mid_point:]

        # Creating the prediction error filter
        R = toeplitz(autocorr[:filter_length])
        R[:, 0] += noise_level
        p = autocorr[prediction_distance:prediction_distance + filter_length]
        prediction_error_filter = np.linalg.solve(R, p)
        
        # Deconvolution using the prediction error filter
        deconvolved_trace = lfilter(prediction_error_filter, [1.0], trace)
        
        return deconvolved_trace
    
    @staticmethod
    def Predictive_Deconvolution(trace, lag):
        """
        Predictive deconvolution suppresses multiples by using a prediction filter.
        
        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - lag: Prediction lag (int).
        
        Returns:
        - Deconvolved trace (1D numpy array).
        """
        autocorr = np.correlate(trace, trace, mode='full')[len(trace)-1:]  # Autocorrelation
        filter_coeffs = np.linalg.solve(
            toeplitz(autocorr[:lag]), 
            autocorr[1:lag+1]
        )
        deconvolved_trace = np.convolve(trace, -filter_coeffs, mode='same')
        return deconvolved_trace
    
    @staticmethod
    def wiener_deconvolution(seismic_data, window_size, noise_power):
        
        """
        Wiener Deconvolution aims to minimize the mean square error between the desired output and the actual output.
        This filter is optimal in the least-squares sense and can be designed to convert the seismic wavelet into any desired shape,
        typically a spike. Unlike spiking deconvolution, Wiener deconvolution can balance between wavelet compression and noise attenuation.

        Parameters:
        - seismic data: N-dimensional numpy array, the seismic data to be deconvolved.
        - window_size: int or array_like, optional. A scalar or an N-length
            list giving the size of the Wiener filter window in each dimension. 
            Elements of mysize should be odd. If size is a scalar, then this 
            scalar is used as the size in each dimension.
        - noise_power: float, optional. The noise-power to use. If None, 
            then noise is estimated as the average of the local variance of the input.

        Returns:
        - deconvolved_data: Wiener filtered result with the same shape as the imput data.
        """
        
        deconvolved_data = np.zeros_like(seismic_data)
        for i, trace in enumerate(seismic_data):
            deconvolved_data[i] = wiener(trace, mysize=window_size, noise = noise_power)
        return deconvolved_data

    @staticmethod
    def Wiener_Deconvolution(trace, wavelet, noise_level=0.01):
        """
        Wiener deconvolution optimally balances resolution and noise suppression.
            
        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - wavelet: Estimated wavelet (1D numpy array).
        - noise_level: Noise regularization parameter (float).
            
        Returns:
        - Deconvolved trace (1D numpy array).
        """
        trace_length = len(trace)
        wavelet_padded = np.pad(wavelet, (0, trace_length - len(wavelet)), mode='constant')

        # Fourier transforms
        wavelet_fft = np.fft.fft(wavelet_padded)
        trace_fft = np.fft.fft(trace)

        # Wiener filter
        wiener_filter = np.conj(wavelet_fft) / (np.abs(wavelet_fft)**2 + noise_level)

        # Apply the filter
        deconvolved_fft = trace_fft * wiener_filter
        deconvolved_trace = np.fft.ifft(deconvolved_fft).real

        return deconvolved_trace

    @staticmethod
    def sparse_spike_deconvolution(trace, wavelet, sparsity_weight=0.1):
        """
        Sparse-spike deconvolution assumes sparse reflectivity.
        
        Parameters:
        - trace: Input seismic trace (1D numpy array).
        - wavelet: Estimated wavelet (1D numpy array).
        - sparsity_weight: Weight for sparsity regularization (float).
        
        Returns:
        - Deconvolved trace (1D numpy array).
        """
        from scipy.optimize import minimize

        def objective(reflectivity):
            error = np.linalg.norm(np.convolve(wavelet, reflectivity, mode='same') - trace)
            sparsity = sparsity_weight * np.linalg.norm(reflectivity, 1)
            return error + sparsity

        reflectivity_init = np.zeros_like(trace)
        result = minimize(objective, reflectivity_init, method='L-BFGS-B')
        return result.x

    #def multichannel_deconvolution(traces, wavelet):
        """
        Multichannel deconvolution accounts for spatial variability.
        
        Parameters:
        - traces: Input seismic traces (2D numpy array, shape [n_traces, n_samples]).
        - wavelet: Estimated wavelet (1D numpy array).
        
        Returns:
        - Deconvolved traces (2D numpy array).
        """
        #n_traces, n_samples = traces.shape
        #deconvolved_traces = np.zeros_like(traces)
        #for i in range(n_traces):
            #deconvolved_traces[i] = wiener_deconvolution(traces[i], wavelet)
        #return deconvolved_traces

class Wavelet:

    def wavelet_from_well_logs(synthetic_seismogram, recorded_trace, initial_wavelet):
        """
        Estimate the wavelet by matching synthetic seismograms to recorded data.

        Parameters:
        - synthetic_seismogram: Synthetic data (1D numpy array).
        - recorded_trace: Recorded seismic data (1D numpy array).
        - initial_wavelet: Initial guess for the wavelet (1D numpy array).

        Returns:
        - Estimated wavelet (1D numpy array).
        """
        def objective(wavelet):
            convolved = np.convolve(wavelet, synthetic_seismogram, mode='same')
            return np.linalg.norm(convolved - recorded_trace)

        result = minimize(objective, initial_wavelet, method='L-BFGS-B')
        return result.x
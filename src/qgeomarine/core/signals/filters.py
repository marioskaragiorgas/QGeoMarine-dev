"""
filters.py 

This module contains various filtering techniques used in signal processing.
Filters are used to manipulate signals by selectively allowing certain frequencies to pass
while attenuating others. This can be useful in a wide range of applications, including
noise reduction, signal enhancement, and the removal of unwanted frequencies. The filters
implemented here include Infinite Impulse Response (IIR) and Finite Impulse Response (FIR) filters,
as well as wavelet-based filtering.

Class `IIR_Filters` contains methods for applying IIR filters:
    - Highpass, lowpass, and bandpass filters using Butterworth design.
    - Highpass, lowpass, and bandpass filters using Chebyshev Type II design.

Class `FIR_Filters` contains methods for applying FIR filters:
    - Highpass, lowpass, and bandpass filters using window methods (Hamming, Kaiser, etc.).
    - Specialized filters like the F-K filter, zero-phase bandpass filter, and wavelet filter.
"""

from scipy import signal
import numpy as np
import pywt

class IIR_Filters:
    
    @staticmethod
    def highpass_filter(signal_data, sample_rate, filter_order, freq):
        """
        Apply a highpass IIR filter to the signal. This filter allows frequencies higher
        than a specified cutoff frequency to pass, while attenuating frequencies lower
        than the cutoff. It is useful for removing low-frequency noise, such as DC offset
        or slow trends in the data.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Butterworth filter. Higher order results in a sharper transition.
        - freq: The cutoff frequency in Hz.

        Returns:
        - The highpass filtered signal as a 1D numpy array.
        """
        nyquist = sample_rate / 2
        if freq >= nyquist:
            raise ValueError(f"Highpass filter frequency {freq} must be less than Nyquist frequency {nyquist}.")
        try:
            sos = signal.butter(filter_order, freq, 'highpass', fs=sample_rate, output='sos')
            filtered_signal_data = signal.sosfilt(sos, signal_data)
            return filtered_signal_data
        except ValueError as e:
            raise ValueError(f"Error applying highpass filter: {e}")

    @staticmethod
    def lowpass_filter(signal_data, sample_rate, filter_order, freq):
        """
        Apply a lowpass IIR filter to the signal. This filter allows frequencies lower
        than a specified cutoff frequency to pass, while attenuating frequencies higher
        than the cutoff. It is useful for removing high-frequency noise, such as sensor noise.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Butterworth filter.
        - freq: The cutoff frequency in Hz.

        Returns:
        - The lowpass filtered signal as a 1D numpy array.
        """
        nyquist = sample_rate / 2
        if freq >= nyquist:
            raise ValueError(f"Lowpass filter frequency {freq} must be less than Nyquist frequency {nyquist}.")
        try:
            sos = signal.butter(filter_order, freq, 'lowpass', fs=sample_rate, output = 'sos')
            filtered_signal_data = signal.sosfilt(sos, signal_data)
            return filtered_signal_data
        except ValueError as e:
            raise ValueError(f"Error applying lowpass filter: {e}")

    @staticmethod
    def bandpass_filter(signal_data, sample_rate, filter_order, freqmin, freqmax):
        """
        Apply a bandpass IIR filter to the signal. This filter allows frequencies within
        a specified range (between freqmin and freqmax) to pass, while attenuating
        frequencies outside this range. Bandpass filtering is useful for isolating
        a specific frequency band of interest, such as removing low-frequency drift and
        high-frequency noise simultaneously.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Butterworth filter.
        - freqmin: The lower cutoff frequency in Hz.
        - freqmax: The upper cutoff frequency in Hz.

        Returns:
        - The bandpass filtered signal as a 1D numpy array.
        """
        nyquist = sample_rate / 2
        if freqmin >= nyquist or freqmax >= nyquist:
            raise ValueError(f"Bandpass filter frequencies {freqmin}-{freqmax} must be less than Nyquist frequency {nyquist}.")
        try:
            sos = signal.butter(filter_order, [freqmin, freqmax], 'bandpass', output = 'sos', fs=sample_rate)
            filtered_signal_data = signal.sosfilt(sos, signal_data)
            return filtered_signal_data
        except ValueError as e:
            raise ValueError(f"Error applying bandpass filter: {e}")
        
    @staticmethod
    def cheby2_highpass_filter(signal_data, sample_rate, filter_order, freq, ripple):
        """
        Apply a Chebyshev Type II highpass filter to the signal. This filter is designed
        to allow high frequencies to pass while attenuating low frequencies, similar to
        the Butterworth highpass filter, but with a steeper roll-off at the expense of
        allowing some ripple in the stopband.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Chebyshev filter.
        - freq: The cutoff frequency in Hz.
        - ripple: The maximum attenuation in the stopband in dB.

        Returns:
        - The highpass filtered signal as a 1D numpy array.
        """
        try:
            sos = signal.cheby2(filter_order, ripple, freq, 'highpass', fs=sample_rate, output='sos')
            filtered_signal_data = signal.sosfilt(sos, signal_data)
            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying Chebyshev Type II highpass filter: {e}")

    @staticmethod
    def cheby2_lowpass_filter(signal_data, sample_rate, filter_order, freq, ripple):
        """
        Apply a Chebyshev Type II lowpass filter to the signal. This filter is designed
        to allow low frequencies to pass while attenuating high frequencies. It has a steeper
        roll-off than a Butterworth filter, but it introduces ripple in the stopband.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Chebyshev filter.
        - freq: The cutoff frequency in Hz.
        - ripple: The maximum attenuation in the stopband in dB.

        Returns:
        - The lowpass filtered signal as a 1D numpy array.
        """
        try:
            sos = signal.cheby2(filter_order, ripple, freq, 'lowpass', fs=sample_rate)
            filtered_signal_data = signal.lfilter(sos, signal_data)
            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying Chebyshev Type II lowpass filter: {e}")

    @staticmethod
    def cheby2_bandpass_filter(signal_data, sample_rate, filter_order, freqmin, freqmax, ripple):
        """
        Apply a Chebyshev Type II bandpass filter to the signal. This filter allows
        frequencies within a specified range to pass while attenuating frequencies outside
        this range. It provides a sharper cutoff compared to Butterworth filters but
        introduces ripple in the stopband.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the Chebyshev filter.
        - freqmin: The lower cutoff frequency in Hz.
        - freqmax: The upper cutoff frequency in Hz.
        - ripple: The maximum attenuation in the stopband in dB.

        Returns:
        - The bandpass filtered signal as a 1D numpy array.
        """
        try:
            sos = signal.cheby2(filter_order, ripple, [freqmin, freqmax], 'bandpass', fs=sample_rate, output='sos')
            filtered_signal_data = signal.sosfilt(sos, signal_data)
            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying Chebyshev Type II bandpass filter: {e}")

class FIR_Filters:
    
    @staticmethod
    def lowpass_filter(signal_data, cutoff_freq, sample_rate, filter_order, window='hamming'):
        """
        Apply a lowpass FIR filter to the signal.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - cutoff_freq: The cutoff frequency in Hz.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the FIR filter (number of taps).
        - window: The windowing function to design the filter (default is 'hamming').

        Returns:
        - The lowpass filtered signal as a 1D numpy array.
        """
        try:
            nyquist = 0.5 * sample_rate
            normalized_cutoff = cutoff_freq / nyquist

            taps = signal.firwin(filter_order, normalized_cutoff, pass_zero='lowpass', window=window)
            filtered_signal_data = signal.lfilter(taps, 1.0, signal_data)
            return filtered_signal_data
        except ValueError as e:
                raise ValueError(f"Error applying lowpass FIR filter: {e}")

    @staticmethod
    def highpass_filter(signal_data, cutoff_freq, sample_rate, filter_order, window='hamming'):
        """
        Apply a highpass FIR filter to the signal.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - cutoff_freq: The cutoff frequency in Hz.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the FIR filter (number of taps).
        - window: The windowing function to design the filter (default is 'hamming').

        Returns:
        - The highpass filtered signal as a 1D numpy array.
        """
        try:
            nyquist = 0.5 * sample_rate
            normalized_cutoff = cutoff_freq / nyquist

            taps = signal.firwin(filter_order, normalized_cutoff, pass_zero='highpass', window=window)
            filtered_signal_data = signal.lfilter(taps, 1.0, signal_data)
            return filtered_signal_data
        except ValueError as e:
            raise ValueError(f"Error applying highpass FIR filter: {e}")


    @staticmethod
    def bandpass_filter(signal_data, freqmin, freqmax, sample_rate, filter_order, window='hamming'):
        """
        Apply a bandpass FIR filter to the signal. This filter allows frequencies within
        a specified range to pass while attenuating frequencies outside this range.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - freqmin: The lower cutoff frequency in Hz.
        - freqmax: The upper cutoff frequency in Hz.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the FIR filter (number of taps).
        - window: The windowing function to design the filter (default is 'hamming').

        Returns:
        - The bandpass filtered signal as a 1D numpy array.
        """
        try:
            nyquist = sample_rate / 2
            low = freqmin / nyquist
            high = freqmax / nyquist

            taps = signal.firwin(filter_order, [low, high], pass_zero='bandpass', window=window)
            filtered_signal_data = signal.lfilter(taps, 1.0, signal_data)
            return filtered_signal_data
        except ValueError as e:
            raise ValueError(f"Error applying bandpass FIR filter: {e}")
    
    @staticmethod
    def kaiser_bessel_filter(signal_data, freqmin, freqmax, sample_rate, filter_order, beta):
        """
        Apply a Kaiser-Bessel FIR filter to the signal. The Kaiser-Bessel window allows
        for control over the trade-off between the main-lobe width and side-lobe level
        in the frequency response. This makes it a versatile choice for designing FIR filters
        that require specific stopband attenuation characteristics.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - cutoff_freq: The cutoff frequency in Hz.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the FIR filter (number of taps).
        - beta: The shape parameter for the Kaiser window (higher beta gives better stopband attenuation).

        Returns:
        - The Kaiser-Bessel filtered signal as a 1D numpy array.
        """
        try:
            nyquist = sample_rate / 2
            low, high = freqmin / nyquist, freqmax / nyquist
            coefficients_kaiser = signal.firwin(filter_order, [low, high], pass_zero='bandpass', window=('kaiser', signal.kaiser_beta(beta)))

            filtered_signal_data = signal.lfilter(coefficients_kaiser, 1.0, signal_data)
            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying Kaiser-Bessel FIR filter: {e}")

    @staticmethod
    def fk_filter(signal_data, sample_rate, filter_order):
        """
        Apply F-K filtering to the signal. F-K filtering is commonly used in seismic processing
        to remove specific wave types or noise based on their apparent velocity and frequency.
        This method involves transforming the data to the frequency-wavenumber domain, applying
        a filter, and then transforming it back to the time-space domain.

        Parameters:
        - signal_data: The input signal as a 2D numpy array (e.g., seismic data with time and offset axes).
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order or size of the filter applied in the F-K domain.

        Returns:
        - The F-K filtered signal as a 2D numpy array.
        """
        try:
            # Example implementation using a 2D Gaussian window
            x = np.arange(-filter_order // 2, filter_order // 2)
            y = np.arange(-filter_order // 2, filter_order // 2)
            X, Y = np.meshgrid(x, y)
            window = np.exp(-(X**2 + Y**2) / (2 * (filter_order / 6)**2))  # Example: 2D Gaussian window
            window /= np.sum(window)  # Normalize the window
            filtered_signal_data = signal.convolve2d(signal_data, window, mode='same', boundary='wrap')

            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying F-K FIR filter: {e}")

    @staticmethod
    def zero_phase_bandpass_filter(signal_data, freqmin, freqmax, sample_rate, filter_order):
        """
        Apply a zero-phase bandpass FIR filter to the signal. This filter allows frequencies within
        a specified range to pass while attenuating frequencies outside this range. By applying the
        filter forward and backward, the phase shift introduced by the filter is canceled out,
        resulting in zero phase distortion.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - freqmin: The lower cutoff frequency in Hz.
        - freqmax: The upper cutoff frequency in Hz.
        - sample_rate: The sampling rate of the signal in Hz.
        - filter_order: The order of the FIR filter (number of taps).

        Returns:
        - The zero-phase bandpass filtered signal as a 1D numpy array.
        """
        try:
        
            sos = signal.butter(filter_order, [freqmin , freqmax], btype='band', fs=sample_rate, output= 'sos')
        
            # Apply the filter twice to achieve zero phase
            filtered_signal_data = signal.sosfiltfilt(sos, signal_data)

            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying zero-phase bandpass FIR filter: {e}")

    @staticmethod
    def wavelet_filter(signal_data, wavelet_type, level=5):
        """
        Apply wavelet-based filtering to the signal. Wavelet filtering involves decomposing the
        signal into different frequency components (wavelet coefficients) and then reconstructing
        the signal after modifying or thresholding these coefficients. This method is particularly
        useful for denoising or isolating specific signal features.

        Parameters:
        - signal_data: The input signal as a 1D numpy array.
        - wavelet_type: The type of wavelet to use for decomposition (default is 'db4').
        - level: The number of decomposition levels (higher levels correspond to coarser features).

        Returns:
        - The wavelet-filtered signal as a 1D numpy array.
        """
        try:
            coeffs = pywt.wavedec(signal_data, wavelet_type, level=level)
            # Set some coefficients to zero or modify as needed
            coeffs[1:] = [pywt.threshold(c, value=np.std(c), mode='soft') for c in coeffs[1:]]
            filtered_signal_data = pywt.waverec(coeffs, wavelet_type)
            return filtered_signal_data

        except ValueError as e:
            raise ValueError(f"Error applying wavelet filter: {e}")
        
    @staticmethod
    def fourier_filter(signal_data, freqmin, freqmax, sample_rate):
        try:
            fft_signal = np.fft.fft(signal_data)
            freqs = np.fft.fftfreq(len(signal_data), d=1/sample_rate)
            mask = (freqs > freqmin) & (freqs < freqmax)
            fft_signal[~mask] = 0
            filtered_data = np.real(np.fft.ifft(fft_signal))
            return filtered_data
        
        except ValueError as e:
            raise ValueError(f"Error applying Fourier filter: {e}")

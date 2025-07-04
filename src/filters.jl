"""
filters.jl 

This module contains various filtering techniques used in signal processing.
Filters are used to manipulate signals by selectively allowing certain frequencies to pass
while attenuating others. This can be useful in a wide range of applications, including
noise reduction, signal enhancement, and the removal of unwanted frequencies. The filters
implemented here include Infinite Impulse Response (IIR) and Finite Impulse Response (FIR) filters,
as well as wavelet-based filtering.

Module `IIRFilters` contains methods for applying IIR filters:
    - Highpass, lowpass, and bandpass filters using Butterworth design.
    - Highpass, lowpass, and bandpass filters using Chebyshev Type II design.

Module `FIRFilters` contains methods for applying FIR filters:
    - Highpass, lowpass, and bandpass filters using window methods (Hamming, Kaiser, etc.).
    - Specialized filters like the F-K filter, zero-phase bandpass filter, and wavelet filter.
"""

using DSP
using Wavelets
using LinearAlgebra
using FFTW

module IIRFilters

function highpass_filter(signal_data::Vector{Float64}, sample_rate::Float64, filter_order::Int, freq::Float64)::Vector{Float64}
    """
    Apply a highpass IIR filter to the signal. This filter allows frequencies higher
    than a specified cutoff frequency to pass, while attenuating frequencies lower
    than the cutoff. It is useful for removing low-frequency noise, such as DC offset
    or slow trends in the data.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the Butterworth filter. Higher order results in a sharper transition.
    - freq: The cutoff frequency in Hz.

    Returns:
    - The highpass filtered signal as a 1D array.
    """
    nyquist = 0.5 * sample_rate
    if freq >= nyquist
        error("Highpass filter frequency must be less than Nyquist frequency $nyquist.")
    end
    try
        normal_cutoff = freq / nyquist
        b, a = butter(filter_order, normal_cutoff, highpass=true)
        return filtfilt(b, a, signal_data)
    catch e
        error("Error applying highpass filter: $e")
    end
end

function lowpass_filter(signal_data::Vector{Float64}, sample_rate::Float64, filter_order::Int, freq::Float64)::Vector{Float64}
    """
    Apply a lowpass IIR filter to the signal. This filter allows frequencies lower
    than a specified cutoff frequency to pass, while attenuating frequencies higher
    than the cutoff. It is useful for removing high-frequency noise, such as aliasing
    or high-frequency interference.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the Butterworth filter. Higher order results in a sharper transition.
    - freq: The cutoff frequency in Hz.

    Returns:
    - The lowpass filtered signal as a 1D array.
    """
    nyquist = 0.5 * sample_rate
    if freq >= nyquist
        error("Lowpass filter frequency must be less than Nyquist frequency $nyquist.")
    end
    try
        normal_cutoff = freq / nyquist
        b, a = butter(filter_order, normal_cutoff)
        return filtfilt(b, a, signal_data)
    catch e
        error("Error applying lowpass filter: $e")
    end
end

function bandpass_filter(signal_data::Vector{Float64}, sample_rate::Float64, filter_order::Int, freqmin::Float64, freqmax::Float64)::Vector{Float64}
    """
    Apply a bandpass IIR filter to the signal. This filter allows frequencies within
    a specified range to pass, while attenuating frequencies outside of that range.
    It is useful for isolating specific frequency components in the signal.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the Butterworth filter. Higher order results in a sharper transition.
    - freqmin: The lower cutoff frequency in Hz.
    - freqmax: The upper cutoff frequency in Hz.

    Returns:
    - The bandpass filtered signal as a 1D array.
    """
    nyquist = 0.5 * sample_rate
    if freqmin >= nyquist || freqmax >= nyquist
        error("Bandpass filter frequencies must be less than Nyquist frequency $nyquist.")
    end
    try
        normal_cutoff = [freqmin, freqmax] / nyquist
        b, a = butter(filter_order, normal_cutoff, bandpass=true)
        return filtfilt(b, a, signal_data)
    catch e
        error("Error applying bandpass filter: $e")
    end
    
end

function cheby2_highpass_filter(signal_data::Vector{Float64}, sample_rate::Float64, filter_order::Int, freq::Float64, ripple::Float64)::Vector{Float64}
    """
    Apply a highpass IIR filter to the signal using Chebyshev Type II design. This filter
    allows frequencies higher than a specified cutoff frequency to pass, while attenuating
    frequencies lower than the cutoff. It is useful for removing low-frequency noise, such as
    DC offset or slow trends in the data.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the Chebyshev Type II filter. Higher order results in a sharper transition.
    - freq: The cutoff frequency in Hz.
    - ripple: The maximum ripple in the passband in decibels.

    Returns:
    - The highpass filtered signal as a 1D array.
    """
    nyquist = 0.5 * sample_rate
    if freq >= nyquist
        error("Highpass filter frequency must be less than Nyquist frequency $nyquist.")
    end
    try
        normal_cutoff = freq / nyquist
        b, a = cheby2(filter_order, ripple, normal_cutoff, highpass=true)
        return filtfilt(b, a, signal_data)
    catch e
        error("Error applying Chebyshev Type II highpass filter: $e")
    end
end

function cheby2_lowpass_filter(signal_data::Vector{Float64}, sample_rate::Float64, filter_order::Int, freq::Float64, ripple::Float64)::Vector{Float64}
    """
    Apply a lowpass IIR filter to the signal using Chebyshev Type II design. This filter
    allows frequencies lower than a specified cutoff frequency to pass, while attenuating
    frequencies higher than the cutoff. It is useful for removing high-frequency noise, such as
    aliasing or high-frequency interference.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the Chebyshev Type II filter. Higher order results in a sharper transition.
    - freq: The cutoff frequency in Hz.
    - ripple: The maximum ripple in the passband in decibels.

    Returns:
    - The lowpass filtered signal as a 1D array.
    """
    nyquist = 0.5 * sample_rate
    if freq >= nyquist
        error("Lowpass filter frequency must be less than Nyquist frequency $nyquist.")
    end
    try
        normal_cutoff = freq / nyquist
        b, a = cheby2(filter_order, ripple, normal_cutoff)
        return filtfilt(b, a, signal_data)
    catch e
        error("Error applying Chebyshev Type II lowpass filter: $e")
    end
end

end # End of IIR_Filters module

# Finite Impulse Response (FIR) Filters
module FIR_Filters

function lowpass_filter(signal_data::Vector{Float64}, cutoff_freq::Float64, sample_rate::Float64, filter_order::Int, window::String="hamming")::Vector{Float64}
    """
    Apply a lowpass FIR filter to the signal. This filter allows frequencies lower
    than a specified cutoff frequency to pass, while attenuating frequencies higher
    than the cutoff. It is useful for removing high-frequency noise, such as aliasing
    or high-frequency interference.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - cutoff_freq: The cutoff frequency in Hz.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the FIR filter (number of taps).
    - window: The windowing function for filter design (default is "hamming").

    Returns:
    - The lowpass filtered signal as a 1D array.
    """
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff_freq / nyquist
    try
        taps = firwin(filter_order, normalized_cutoff, window)
        return filtfilt(taps, signal_data)
    catch e
        error("Error applying lowpass FIR filter: $e")
    end
end

function highpass_filter(signal_data::Vector{Float64}, cutoff_freq::Float64, sample_rate::Float64, filter_order::Int, window::String="hamming")::Vector{Float64}
    """
    Apply a highpass FIR filter to the signal. This filter allows frequencies higher
    than a specified cutoff frequency to pass, while attenuating frequencies lower
    than the cutoff. It is useful for removing low-frequency noise, such as DC offset
    or slow trends in the data.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - cutoff_freq: The cutoff frequency in Hz.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the FIR filter (number of taps).
    - window: The windowing function for filter design (default is "hamming").

    Returns:
    - The highpass filtered signal as a 1D array.
    """
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff_freq / nyquist
    try
        taps = firwin(filter_order, normalized_cutoff, window, pass_zero=false)
        return filtfilt(taps, signal_data)
    catch e
        error("Error applying highpass FIR filter: $e")
    end
end

function bandpass_filter(signal_data::Vector{Float64}, freqmin::Float64, freqmax::Float64, sample_rate::Float64, filter_order::Int, window::String="hamming")::Vector{Float64}
    """
    Apply a bandpass FIR filter to the signal. This filter allows frequencies within
    a specified range to pass, while attenuating frequencies outside of that range.
    It is useful for isolating specific frequency components in the signal.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - freqmin: The lower cutoff frequency in Hz.
    - freqmax: The upper cutoff frequency in Hz.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the FIR filter (number of taps).
    - window: The windowing function for filter design (default is "hamming").

    Returns:
    - The bandpass filtered signal as a 1D array.
    """
    nyquist = sample_rate / 2
    if freqmin >= nyquist || freqmax >= nyquist
        error("Bandpass filter frequencies must be less than Nyquist frequency $nyquist.")
    end
    try
        taps = firwin(filter_order, [freqmin, freqmax] / nyquist, window, pass_zero=false)
        return filtfilt(taps, signal_data)
    catch e
        error("Error applying bandpass FIR filter: $e")
    end
end

function kaiser_bessel_filter(signal_data::Vector{Float64}, cutoff_freq::Float64, sample_rate::Float64, filter_order::Int, beta::Float64)::Vector{Float64}
    """
    Apply a lowpass FIR filter to the signal using the Kaiser window method. This filter
    allows frequencies lower than a specified cutoff frequency to pass, while attenuating
    frequencies higher than the cutoff. It is useful for removing high-frequency noise, such as
    aliasing or high-frequency interference.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - cutoff_freq: The cutoff frequency in Hz.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the FIR filter (number of taps).
    - beta: The Kaiser window shape parameter.

    Returns:
    - The lowpass filtered signal as a 1D array.
    """
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff_freq / nyquist
    try
        # Design the FIR filter with a Kaiser window
        taps = firwin(filter_order, normalized_cutoff, window=kaiser(filter_order, beta))
        return filt(taps, signal_data)
    catch e
        error("Error applying Kaiser window lowpass FIR filter: $e")
    end
end

function zero_phase_bandpass_filter(signal_data::Vector{Float64}, freqmin::Float64, freqmax::Float64, sample_rate::Float64, filter_order::Int)::Vector{Float64}
    """
    Apply a zero-phase bandpass FIR filter to the signal. This filter allows frequencies
    within a specified range to pass, while attenuating frequencies outside of that range.
    It is useful for isolating specific frequency components in the signal without introducing
    phase distortion.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - freqmin: The lower cutoff frequency in Hz.
    - freqmax: The upper cutoff frequency in Hz.
    - sample_rate: The sampling rate of the signal in Hz.
    - filter_order: The order of the FIR filter (number of taps).

    Returns:
    - The zero-phase bandpass filtered signal as a 1D array.
    """
    nyquist = sample_rate / 2
    if freqmin >= nyquist || freqmax >= nyquist
        error("Bandpass filter frequencies must be less than Nyquist frequency $nyquist.")
    end
    try
        low = freqmin / nyquist
        high = freqmax / nyquist
        # Design the FIR bandpass filter with a Blackman-Harris window
        taps = firwin(filter_order, [low, high], passband=:bandpass, window=blackmanharris(filter_order))

        # Apply the filter twice for zero-phase (forward and backward)
        filtered_signal = filtfilt(taps, signal_data)

        return filtered_signal
    catch e
        error("Error applying zero-phase bandpass FIR filter: $e")
    end
    
end

function fk_filter(signal_data::Matrix{Float64}, filter_order::Int)
    # Perform 2D FFT to transform to frequency-wavenumber domain
    fk_domain = fft(signal_data)

    # Create a Gaussian window in the F-K domain
    rows, cols = size(signal_data)
    x = collect(-filter_order÷2:filter_order÷2)
    y = collect(-filter_order÷2:filter_order÷2)

    X, Y = mesh_grid(x, y)
    sigma = filter_order / 6
    sigma2 = 2 * sigma^2
    window = exp.(-(X.^2 .+ Y.^2) / sigma2)
    window ./= sum(window)  # Normalize the window

    # Apply the filter by multiplying in the F-K domain
    filtered_fk = fk_domain .* window

    # Inverse 2D FFT to transform back to time-space domain
    filtered_signal = real(ifft(filtered_fk))

    return filtered_signal
end

"""
Helper function to generate meshgrid.

This function creates two 2D arrays representing the X and Y coordinates of a grid.

Parameters:
- x: A 1D array representing the x-coordinates.
- y: A 1D array representing the y-coordinates.

Returns:
- A tuple (X, Y) where X is a 2D array with repeated rows of x and Y is a 2D array with repeated columns of y.
"""
function meshgrid(x, y)
    X = repeat(x, 1, length(y))
    Y = repeat(y', length(x), 1)
    return X, Y
end

end # End of FIR_Filters module

# Wavelet-based Filtering
module Wavelet_Filters

function wavelet_filter(signal_data::Vector{Float64}, wavelet_type::String, level::Int=5)::Vector{Float64}
    """
    Apply a wavelet filter to the signal. Wavelet filtering is a powerful technique
    for analyzing and processing signals with both time and frequency localization.
    This method decomposes the signal into different frequency bands using wavelet
    transforms and then reconstructs the signal using only the desired frequency bands.

    Parameters:
    - signal_data: The input signal as a 1D array.
    - wavelet_type: The type of wavelet to use for filtering.
    - level: The level of decomposition for the wavelet transform.

    Returns:
    - The wavelet filtered signal as a 1D array.
    """
    try
        coeffs = wavedec(signal_data, wavelet_type, level)
        return waverec(coeffs, wavelet_type)
    catch e
        error("Error applying wavelet filter: $e")
    end
end
end # End of Wavelet_Filters module


# Import GLMakie for plotting
using GLMakie

# ---------------------------
# Plot Seismic Trace
# ---------------------------
function plot_trace!(ax, trace, trace_number, delta)
    """
    Plot the seismic trace on the given axis.

    Parameters:
        ax (Axis): The axis on which to plot the trace.
        trace (Vector{Float64}): The seismic trace data (amplitude values).
        trace_number (Int): The index of the seismic trace to be plotted.
        delta (Float64): The time interval between samples (sampling period in ms).
    """
    # Compute the time axis
    n_samples = length(trace)
    time_axis = 0:delta:(n_samples - 1) * delta

    # Plot the trace
    lines!(ax, time_axis, trace, color=:black)
    ax.title = "Seismic Trace $trace_number"
    ax.xlabel = "Two-Way Time (ms)"
    ax.ylabel = "Amplitude"
end

# ---------------------------
# Plot Periodogram
# ---------------------------
function plot_periodogram!(ax, f, Pxx, trace_number)
    """
    Plot the periodogram of a seismic trace.

    Parameters:
        ax (Axis): The axis on which to plot the periodogram.
        f (Vector{Float64}): Array of sample frequencies.
        Pxx (Vector{Float64}): Power spectral density (PSD) values.
        trace_number (Int): The index of the seismic trace being analyzed.
    """
    lines!(ax, f, Pxx, color=:black)
    ax.title = "Seismic Trace $trace_number Periodogram"
    ax.xlabel = "Frequency (Hz)"
    ax.ylabel = "Power/Frequency (dB/Hz)"
    ax.yscale = log10  # Semilogy equivalent
end

# ---------------------------
# Plot Welch Periodogram
# ---------------------------
function plot_welch_periodogram!(ax, f, Pxx, trace_number)
    """
    Plot the Welch periodogram of a seismic trace.

    Parameters:
        ax (Axis): The axis on which to plot the Welch periodogram.
        f (Vector{Float64}): Array of sample frequencies.
        Pxx (Vector{Float64}): Power spectral density (PSD) values.
        trace_number (Int): The index of the seismic trace being analyzed.
    """
    lines!(ax, f, Pxx, color=:black)
    ax.title = "Seismic Trace $trace_number Welch Periodogram"
    ax.xlabel = "Frequency (Hz)"
    ax.ylabel = "Power/Frequency (dB/Hz)"
    ax.yscale = log10  # Semilogy equivalent
end

# ---------------------------
# Plot Wavelet Transform
# ---------------------------
function plot_wavelet_transform!(ax, cwt_matrix, widths, trace_number)
    """
    Plot the wavelet transform of a seismic trace.

    Parameters:
        ax (Axis): The axis on which to plot the wavelet transform.
        cwt_matrix (Matrix{Float64}): The continuous wavelet transform (CWT) matrix.
        widths (Vector{Float64}): Array of wavelet widths (scales).
        trace_number (Int): The index of the seismic trace being analyzed.
    """
    image!(ax, abs.(cwt_matrix), axis=(; aspect=DataAspect()))
    ax.title = "Seismic Trace $trace_number Wavelet Transform"
    ax.xlabel = "Sample"
    ax.ylabel = "Scale"
end

# ---------------------------
# Plot Spectrogram
# ---------------------------
function plot_spectrogram!(ax, f, t, Sxx, trace_number)
    """
    Plot the spectrogram of a seismic trace.

    Parameters:
        ax (Axis): The axis on which to plot the spectrogram.
        f (Vector{Float64}): Array of sample frequencies.
        t (Vector{Float64}): Array of time segments.
        Sxx (Matrix{Float64}): Spectrogram matrix.
        trace_number (Int): The index of the seismic trace being analyzed.
    """
    heatmap!(ax, t, f, 10 .* log10.(Sxx), colormap=:viridis)
    ax.title = "Seismic Trace $trace_number Spectrogram"
    ax.xlabel = "Time (ms)"
    ax.ylabel = "Frequency (Hz)"
end

# ---------------------------
# Plot Seismic Image
# ---------------------------
function plot_seismic_image!(ax, seismic_data, delta)
    """
    Plot the seismic image with proper time scaling.

    Parameters:
        ax (Axis): The axis on which to plot the seismic image.
        seismic_data (Matrix{Float64}): The seismic section data.
        delta (Float64): The time interval between samples (sampling period in ms).
    """
    n_traces, n_samples = size(seismic_data)

    # Compute the time axis (in ms)
    time_axis = 0:delta:(n_samples - 1) * delta

    # Plot the seismic image
    image!(ax, 1:n_traces, time_axis, seismic_data', colormap=:seismic, axis=(; aspect=DataAspect()))
    ax.title = "Seismic Section"
    ax.xlabel = "Trace Number"
    ax.ylabel = "Two-Way Travel Time (ms)"
end

# ---------------------------
# Example Usage
# ---------------------------
function example()
    # Sample seismic data
    trace = sin.(0:0.01:2π) .+ randn(629) * 0.1  # Synthetic trace with noise
    delta = 2.0  # Sampling interval in ms

    # Plotting the seismic trace
    fig = Figure()
    ax = Axis(fig[1, 1], title="Seismic Trace 1", xlabel="Two-Way Time (ms)", ylabel="Amplitude")
    plot_trace!(ax, trace, 1, delta)
    display(fig)

    # Sample periodogram data
    f = 0:0.1:50
    Pxx = abs.(sin.(f)) .+ 1e-3

    fig = Figure()
    ax = Axis(fig[1, 1], title="Seismic Trace 1 Periodogram", xlabel="Frequency (Hz)", ylabel="Power/Frequency (dB/Hz)")
    plot_periodogram!(ax, f, Pxx, 1)
    display(fig)
end

# Run the example
example()

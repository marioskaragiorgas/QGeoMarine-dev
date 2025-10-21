# QGeoMarine

**A Modular Python GUI for Seismic and Magnetic Data Processing from Marine Geophysical Surveys**  
🚧 *This project is currently under active development.*

![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-GPLv3-blue)
![Status](https://img.shields.io/badge/status-beta-yellow)
![License](https://img.shields.io/badge/license-beta--restricted-lightgrey)

QGeoMarine is a modular, cross-platform application built in Python for the interactive processing, visualization, and interpretation of geophysical data collected from marine surveys. It supports workflows involving seismic (e.g., Sub-Bottom Profiler/Chirp) and magnetic datasets in commonly used formats (e.g., SEG-Y, CSV).

Designed for researchers, students, and professionals in marine geoscience, QGeoMarine provides a rich GUI that integrates scientific libraries with interactive PyQt6-based tools.

---

## 🚀 Features

- 📁 Project Manager with recent file tracking
- 🧭 Navigation parsing from SEG-Y or external ship logs
- 🎚️ Seismic signal processing (Gain, Mute, Filter, Deconvolution)
- 🧠 Advanced analysis (Periodogram, Wavelet Transform, Instantaneous Attributes)
- 🧰 Editable magnetic data tables with SQLite backend
- 🗺️ Interactive map display using folium and survey line plotting
- 📊 Synthetic wavelet modeling and interactive trace synthesis
- ✍️ Interactive horizon picking, annotation, and export tools

---

## 🧱 Application Structure

*Source code application modules structure*
```
QGeoMarine-dev/
├─ src/
│  └─ qgeomarine/
│     ├─ core/                        # High-level app logic & domain workflows
│     │  ├─ interpretation/           # Seismic interpretation tools (GUI)
│     │  │  ├─ __init__.py
│     │  │  └─ interpretation.py
│     │  ├─ maps/                     # Mapping & grids
│     │  │  ├─ __init__.py
│     │  │  ├─ grids.py
│     │  │  └─ maps.py
│     │  ├─ navigation/               # Towfish/ship navigation processing
│     │  │  ├─ __init__.py
│     │  │  └─ navigation.py
│     │  ├─ processing/               # Seismic/SSS processing pipelines
│     │  │  ├─ __init__.py
│     │  │  ├─ sss_processing.py
│     │  │  ├─ trace_analysis.py
│     │  │  └─ trace_qc.py
│     │  └─ __init__.py
│     │
│     ├─ signals/                     # Signal-processing primitives
│     │  ├─ __init__.py
│     │  ├─ deconvolution.py          # Spiking/predictive/Wiener/sparse
│     │  ├─ filters.py                # IIR/FIR/Fourier/Wavelet
│     │  ├─ gains.py                  # AGC/TVG/constant
│     │  └─ mute.py                   # Top/bottom/offset/time-variant & interactive
│     │
│     ├─ data_io/                     # File & database I/O
│     │  ├─ __init__.py               # I/O for seismic, magnetic, sonar
│     │  ├─ magy_io.py                # Magnetic CSV/XLS/DB
│     │  ├─ seismic_io.py             # SEG-Y (segyio) read/write
│     │  └─ sonar_io.py               # Side-scan/sonar readers
│     │
│     ├─ ui/                          # PyQt6 UI surfaces
│     │  ├─ __init__.py
│     │  ├─ maggy_editor.py           # Magnetic table editor (SQLite-backed)
│     │  ├─ seismic_editor.py         # Seismic editor
│     │  ├─ sss_editor.py             # Side-scan sonar editor
│     │  └─ ui.py                     # Shared widgets/dialogs
│     │
│     ├─ utils/                       # Cross-cutting helpers
│     │  ├─ __init__.py
│     │  └─ utils.py
│     │
│     ├─ visualization/               # Plotting/visual helpers
│     │  ├─ __init__.py
│     │  └─ plots.py
│     │
│     ├─ __init__.py
│     ├─ app.py                       # Application entry point (launch GUI)
```

| Module                                  | Purpose                                                           |
| --------------------------------------- | ----------------------------------------------------------------- |
| `core/interpretation/interpretation.py` | Horizon picking, edge detection, and instantaneous attributes UI. |
| `core/maps/{maps.py,grids.py}`          | Folium/Leaflet mapping, grid helpers.                             |
| `core/navigation/navigation.py`         | Towfish & ship navigation parsing + SBP layback.                  |
| `core/processing/sss_processing.py`     | Side-scan sonar processing routines.                              |
| `core/processing/trace_analysis.py`     | FFT/inst. amplitude/phase/frequency, etc.                         |
| `core/processing/trace_qc.py`           | QC utilities for traces.                                          |
| `signals/deconvolution.py`              | Spiking, predictive, Wiener, sparse-spike deconvoltion.           |
| `signals/filters.py`                    | IIR/FIR (Butter/Cheby), zero-phase, Fourier, wavelet.             |
| `signals/gains.py`                      | AGC, TVG, constant gain.                                          |
| `signals/mute.py`                       | Top/bottom/offset/time-variant + polygon mute.                    |
| `data_io/seismic_io.py`                 | SEG-Y read/write (segyio).                                        |
| `data_io/magy_io.py`                    | Magnetic CSV/XLS import/export to SQLite.                         |
| `data_io/sonar_io.py`                   | Sonar/SSS readers/parsers.                                        |
| `ui/seismic_editor.py`                  | Seismic editor window.                                            |
| `ui/maggy_editor.py`                    | Magnetic editor window.                                           |
| `ui/sss_editor.py`                      | Side-scan sonar editor window.                                    |
| `visualization/plots.py`                | Matplotlib/pyqtgraph plotting helpers.                            |
| `utils/utils.py`                        | Shared small utilities.                                           |
| `app.py`                                | Core application launcher and project workspace management.       |


---

🧩 *Julia integration planned*

To accelerate heavy numerical tasks, QGeoMarine includes Julia modules for future integration:

- **`filters.jl`**  
  Contains optimized IIR and FIR filters using `DSP.jl` and `Wavelets.jl`.  
  Features include Butterworth, Chebyshev, FIR window filters, F-K domain filters, and wavelet denoising.

- **`Plots.jl`**  
  Built with `Makie.jl` for high-performance plotting of seismic traces, periodograms, spectrograms, wavelet transforms, and full seismic sections.

These modules and other that are under developement will be linked into the Python GUI using [`PyJulia`](https://pyjulia.readthedocs.io/) or subprocess and **replace the corresponding Python modules** bridging to offload computationally intensive routines.

> 🧩 Goal: Seamlessly switch between Python and Julia backends for faster heavy computing tasks resulting in a lightweight faster application.

---

---

## 🧠 Machine Learning Extensions (Planned)

Future releases of **QGeoMarine** will integrate machine learning models to enhance interpretation and automation in marine geophysical workflows. These developments aim to assist users in detecting features, reducing manual interpretation time, and extracting deeper insights from large datasets.

### 🔹 Magnetic Data
- **Magnetic Anomaly Detection**  
  Leverage unsupervised learning (e.g., Isolation Forests, Autoencoders) to detect subtle or unusual magnetic anomalies, especially in noisy environments.
  
- **Target Classification**  
  Train classifiers (e.g., Random Forests, CNNs) to distinguish anomaly sources such as UXOs, pipelines, shipwrecks, or mineralized zones based on profile shape and contextual features.

### 🔹 Seismic Data
- **Geological Feature Extraction from Seismic Images**  
  Apply deep learning models (e.g., U-Net, ResNet) to segment seismic volumes and detect:
  - Faults
  - Horizons
  - Gas pockets
  - Stratigraphic structures

- **Attribute-Based Clustering and Prediction**  
  Cluster or classify regions using computed attributes (e.g., RMS amplitude, instantaneous frequency/phase) for facies analysis or sediment type inference.

### 🔬 Integration Path
- Models will be trained using PyTorch/TensorFlow and marine-labeled datasets.
- Outputs will be visualized as overlays or annotations within the seismic and magnetic editors.
- Interactive labeling tools may be included to support supervised learning workflows directly in the GUI.

> 🎯 **Goal**: Empower users with data-driven assistance for faster, smarter interpretation — reducing human error and unlocking high-throughput analysis.

---

## 🔧 Installation in developement/editable mode 

```bash
git clone https://github.com/marioskaragiorgas/qgeomarine.git
cd qgeomarine
pip install -e .
```

Typical requirements:
```text
PyQt6
pyqtgraph
numpy
pandas
matplotlib
scipy
segyio
folium
```

For Linux users (segyio dependency):
```bash
sudo apt-get install libsegyio-dev
```

Optional for future Julia integration:
```bash
pip install julia
```

---

## 🖥️ Usage

1. **Run the application**
2. Open a terminal and type:
   ```bash
   qgeomarine
   ```

3. **Start a new project** or open an existing `.qgm` QGeoMarine project file.

4. **Load SEG-Y or magnetic files** via the treeview.

5. **Apply filters, gain corrections, mutes, or trace analysis** using the context menu or toolbar.

6. **Use map view** to visualize navigation and seismic lines.

7. **Use the Maggy Editor** to filter, plot, or transform magnetic data.

8. **Pick horizons** using the seismic interpretation GUI.

---

## 🗂 Project Folder Structure

```
QGeoMarineExampleProject/
├── Navigation
├── Project
│   ├── QGeoMarineproject_file.qgm
│   └── .project_state.json # Metadata for GUI session
├── magnetics
│   └── magnetic_database.db
├── maps
│   └── default_map.html # The base map (it's created by default at the project creation and updated with the survey geospatial data)
├── seismic
│   ├── seismic_data.bin # Binary file which contains the seismic trace data stored after the import of a seismic file
│   └── seismic_metadata.db # database with the seismic metadata stored after the import of a seismic file 
└── sonar
```

---

## 📷 Some Screenshots (more will be added in the future)

QGeoMarine offers a modular GUI for marine geophysical data workflows, including seismic, magnetic, and mapping tools:

### 🔹 Application Start & Navigation
| Intro Screen | Project File Manager |
|--------------|----------------------|
| ![Intro](docs/screenshots/intro%20window.png) | ![Main](docs/screenshots/main%20window.png) |

---

### 🔹 Mapping and Project View
| File Tree + Map | Context Menu |
|------------------|--------------|
| ![Map 1](docs/screenshots/Screenshot%201.png) | ![Map 2](docs/screenshots/Screenshot%202.png) |

---

### 🔹 Seismic Editor
| Mute Polygon Tool | Gain/AGC Output |
|-------------------|-----------------|
| ![Mute](docs/screenshots/seismic%20editor%201.png) | ![AGC](docs/screenshots/seismic%20editor.png) |

---

### 🔹 Seismic Interpretation
| Edge Detection – Canny | Sobel |
|------------------------|--------|
| ![Canny](docs/screenshots/seismic%20interpretation%201.png) | ![Sobel](docs/screenshots/seismic%20interpretation%202.png) |

| Instantaneous Attributes | Horizon Picking  |
|----------------|---------------------------|
| ![Horizons](docs/screenshots/seismic%20interpretation.png) | ![InstAmp](docs/screenshots/seismic%20interpretation%203.png) |

---

### 🔹 Magnetic Editor
| SQL Channel Math | Table & Chart |
|------------------|----------------|
| ![Math](docs/screenshots/channe%3B%20math.png) | ![Table](docs/screenshots/magnetic%20editor.png) |

---

### 🔹 Filtering Preview
| Butterworth Bandpass Preview |
|------------------------------|
| ![Filter UI](docs/screenshots/filterUI.png) |

---


## 🔬 Scientific Capabilities

- **Navigation Correction**:
  - Calculate towfish location using ship’s GPS, heading, cable layback geometry
- **Signal Processing**:
  - AGC / TVG / Spiking Deconvolution / Mute windows
  - Signal filters with interactive preview
- **Time-Frequency Tools**:
  - Spectrogram, Wavelet Transform (CWT), Hilbert attributes
- **Column Math (Magnetic)**:
  - SQL-like channel formulas with offset and rolling support

---

---

## 📜 License

This project is licensed under the **QGeoMarine Beta License**.  
See the [LICENSE](BETA_LICENSE.txt) file for more information.

---

## 🧑‍💻 Developers

- **Author**: Marios Karagiorgas  

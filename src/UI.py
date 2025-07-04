"""
UI.py
Graphical User Interfaces for Marine Geophysical Application (QGeoMarine)

This module provides a suite of PyQt6-based GUI classes for seismic and magnetic data analysis,
filtering, visualization, and project management. Interfaces are designed to work with
SEG-Y seismic traces, magnetic profiles, and associated metadata.

Modules and Classes:
--------------------
- Ui_IntroWindow:
    Main entry screen showing app branding, new/open project buttons, and recent projects list.

- bandass_filter_UI, lowpass_filter_UI, highpass_filter_UI:
    Dialogs for seismic trace filtering using frequency cut sliders and order inputs.

- FilterUI:
    Unified wrapper that dynamically loads the appropriate filter UI (bandpass, lowpass, highpass)
    based on user selection.

- TraceAnalysisWindowUI:
    UI for advanced trace analysis using time-frequency methods like FFT, spectrograms,
    and instantaneous attributes.

- WaveletWindowUI:
    UI for selecting and parameterizing synthetic wavelets for seismic modeling.

- Maggy_editor_UI:
    Main interface for magnetic data table viewing, filtering, transformation, and plotting.
    Includes:
        - Tree view dock for loaded files
        - Table display for magnetic lines
        - Data analysis tools (filtering, channel math, plotting)
        - Dockable matplotlib + pyqtgraph charts

- ChannelMathDialog:
    Sub-dialog located in the Maggy-editor UI that allows users to write expressions using variables (e.g., C0, C1),
    assign them to real columns, and preview the resulting SQL-style translation.

Notes:
------
- Built using PyQt6 and pyqtgraph.
- Designed for geophysical data workflows, emphasizing seismic and magnetic profiles.
- All dialogs are styled with a consistent theme and designed for ease of data interaction.
- This module is under active development and will be extended with additional features and optimized updates."""

import os
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import re
import json

# UI Class Introduction Window
class Ui_IntroWindow(object):
    """
    Ui_IntroWindow
    This class sets up the main introduction window for the QGeoMarine application.
    It includes the application logo, name, and buttons for creating or opening projects.
    It also displays a list of recent projects.
    """

    def setupUi(self, QGeoMmarineIntroWindow):
        """
        Setup the main window layout, header, sidebar, and content sections.
        Args:
            pyqmarineIntroWindow (QMainWindow): The main window instance to set up.
        """
        # Main window setup
        QGeoMmarineIntroWindow.setObjectName("QGeoMmarineIntroWindow")
        QGeoMmarineIntroWindow.resize(851, 627)

        # Central Widget
        self.centralwidget = QtWidgets.QWidget(QGeoMmarineIntroWindow)
        self.centralwidget.setStyleSheet("background-color: rgb(230, 230, 230);")
        self.centralwidget.setObjectName("centralwidget")

        # Main Vertical Layout for the Entire Window
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)  # No extra margins
        self.mainLayout.setSpacing(60)  # Spacing between sections

        # Header Section
        self.header = QtWidgets.QFrame(self.centralwidget)
        self.header.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.header.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.header.setObjectName("header")

        # Header Layout
        self.headerLayout = QtWidgets.QHBoxLayout(self.header)
        self.headerLayout.setContentsMargins(10, 10, 10, 10)
        self.headerLayout.setSpacing(10)

        # Logo
        self.label = QtWidgets.QLabel(self.header)
        self.label.setPixmap(QtGui.QPixmap(os.path.join(os.path.dirname(__file__), "Images/Logo.png")))
        self.label.setScaledContents(True)
        self.label.setFixedSize(100, 80)  # Fixed size for the logo
        self.headerLayout.addWidget(self.label)

        # App Name Label
        self.Logolabel = QtWidgets.QLabel(self.header)
        self.Logolabel.setStyleSheet("color: rgb(0, 144, 144);")
        self.Logolabel.setObjectName("Logolabel")
        self.Logolabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.headerLayout.addWidget(self.Logolabel)

        # Add Header to Main Layout
        self.mainLayout.addWidget(self.header)

        # Content Section
        self.contentLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.setSpacing(30)

        # Sidebar Section (Left Panel)
        self.leftLayout = QtWidgets.QVBoxLayout()  # New vertical layout for sidebar 
        self.leftLayout.setSpacing(30)

        self.sidebar = QtWidgets.QFrame(self.centralwidget)
        self.sidebar.setStyleSheet("background-color: rgb(255, 255, 255); border-radius: 10px;")
        self.sidebar.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.sidebarLayout = QtWidgets.QVBoxLayout(self.sidebar)
        self.sidebarLayout.setContentsMargins(0, 0, 0, 0)

        # Sidebar Buttons
        buttonStyle = """
            QPushButton {
                background-color: rgb(255, 255, 255);
                color: rgb(0, 0, 0);
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                 background-color: rgb(255, 255, 255);
                color: rgb(0, 130, 130);
            }
            QPushButton:pressed {
                background-color: rgb(255, 255, 255);
                color: rgb(0, 144, 144);
            }
        """
        buttonStyle_1 = """
        QPushButton {
            background-color: rgb(255, 255, 255);
            color: rgb(0, 144, 144);
            border: none;
            border-radius: 10px;
            padding: 100px 100px 100px 100px; /* Space above for icon */
        }
        QPushButton:hover {
            background-color: rgb(220, 240, 255);
         }
        QPushButton:pressed {
            background-color: rgb(180, 210, 240);
        }
        """
        icon_size = QtCore.QSize(30,30)
        self.buttonnewproject = QtWidgets.QPushButton("    New Project", self.sidebar)
        self.buttonnewproject.setStyleSheet(buttonStyle)
        self.buttonnewproject.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "Images/newfolder.png")))
        self.buttonnewproject.setIconSize(icon_size)
        self.buttonnewproject.setFont(QtGui.QFont("Segoe UI", 16))
        self.sidebarLayout.addWidget(self.buttonnewproject)

        self.buttonopenproject = QtWidgets.QPushButton("   Open Project", self.sidebar)
        self.buttonopenproject.setStyleSheet(buttonStyle)
        self.buttonopenproject.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "Images/openfolder.png")))
        self.buttonopenproject.setIconSize(icon_size)
        self.buttonopenproject.setFont(QtGui.QFont("Segoe UI", 16))
        self.sidebarLayout.addWidget(self.buttonopenproject)

        self.buttonsettings = QtWidgets.QPushButton("Settings", self.sidebar)
        self.buttonsettings.setStyleSheet(buttonStyle)
        self.buttonsettings.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "Images/settings.png")))
        self.buttonsettings.setIconSize(icon_size)
        self.buttonsettings.setFont(QtGui.QFont("Segoe UI", 16))
        self.sidebarLayout.addWidget(self.buttonsettings)

        self.buttonresources = QtWidgets.QPushButton("   Documentation", self.sidebar)
        self.buttonresources.setStyleSheet(buttonStyle)
        self.buttonresources.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "Images/documentation.png")))
        self.buttonresources.setIconSize(icon_size)
        self.buttonresources.setFont(QtGui.QFont("Segoe UI", 16))
        self.sidebarLayout.addWidget(self.buttonresources)

        # Add Sidebar to Left Layout
        self.leftLayout.addWidget(self.sidebar)

        """
        # Documentation Bar Section
        self.documentationbar = QtWidgets.QFrame(self.centralwidget)
        self.documentationbar.setStyleSheet("background-color: rgb(255, 255, 255); border-radius: 10px;")
        self.documentationbar.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.documentationbarLayout = QtWidgets.QHBoxLayout(self.documentationbar)
        self.documentationbarLayout.setContentsMargins(0, 0, 0, 0)
        self.documentationbarLayout.setSpacing(50)

        self.buttonresources = QtWidgets.QPushButton("Documentation", self.documentationbar)
        self.buttonresources.setStyleSheet(buttonStyle)
        self.buttonresources.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "Images/documentation.png")))
        self.buttonresources.setIconSize(QtCore.QSize(30,30))
        self.buttonresources.setFont(QtGui.QFont("Segoe UI", 16))

        # Add Documentation Bar to Left Layout
        self.leftLayout.addWidget(self.documentationbar)
        """
        # Add Left Layout to Content Layout
        self.contentLayout.addLayout(self.leftLayout, 1)  # Left layout gets 1 stretch factor

        # Main Content Section (Right Panel)
        self.mainContent = QtWidgets.QFrame(self.centralwidget)
        self.mainContent.setStyleSheet("background-color: rgb(230, 230, 230);")
        self.mainContentLayout = QtWidgets.QVBoxLayout(self.mainContent)
        self.mainContentLayout.setContentsMargins(10, 10, 10, 10)

        # Recent Projects Label
        self.recentprojlabel = QtWidgets.QLabel("Recent Projects", self.mainContent)
        self.recentprojlabel.setStyleSheet("color: rgb(0, 0, 0);")
        self.recentprojlabel.setFont(QtGui.QFont("Segoe UI", 18))
        self.mainContentLayout.addWidget(self.recentprojlabel)

        # Recent Projects List
        self.listWidget = QtWidgets.QListWidget(self.mainContent)
        self.listWidget.setStyleSheet("color: rgb(0, 0, 0);")
        self.listWidget.setFont(QtGui.QFont("Segoe UI", 12))
        self.mainContentLayout.addWidget(self.listWidget)

        # Add Main Content to Content Layout
        self.contentLayout.addWidget(self.mainContent, 3)  # Main content gets 3 stretch factor

        # Add Content Layout to Main Layout
        self.mainLayout.addLayout(self.contentLayout)

        # Footer Section
        self.footer = QtWidgets.QFrame(self.centralwidget)
        self.footer.setStyleSheet("background-color: rgb(0, 144, 144);")
        self.footer.setFixedHeight(80)  # Fixed height for footer
        self.mainLayout.addWidget(self.footer)

        # Set Central Widget
        QGeoMmarineIntroWindow.setCentralWidget(self.centralwidget)

        # Retranslate the UI
        self.retranslateUi(QGeoMmarineIntroWindow)
        QtCore.QMetaObject.connectSlotsByName(QGeoMmarineIntroWindow)

    def retranslateUi(self, QGeoMmarineIntroWindow):
        _translate = QtCore.QCoreApplication.translate
        QGeoMmarineIntroWindow.setWindowTitle(_translate("QGeoMmarineIntroWindow", "QGeoMmarine"))
        self.Logolabel.setText(_translate("QGeoMmarineIntroWindow",
    "<html><head/><body><p><span style=\" font-size:25pt;\">QGeoMarine</span><span style=\" font-family:\'Segoe UI\',\'sans-serif\'; font-size:12pt; vertical-align:super;\">©</span></p></body></html>"))
        self.buttonnewproject.setText(_translate("QGeoMmarineIntroWindow", "    New Project"))
        self.buttonopenproject.setText(_translate("QGeoMmarineIntroWindow", "   Open Project"))
        self.buttonsettings.setText(_translate("QGeoMmarineIntroWindow", "   Settings"))
        self.buttonresources.setText(_translate("QGeoMmarineIntroWindow", "   Documentation"))
        self.recentprojlabel.setText(_translate("QGeoMmarineIntroWindow", "Recent Projects"))

class bandass_filter_UI(object):
    """
    bandass_filter_UI
    This class sets up the UI for a bandpass filter dialog, allowing users to select
    lowcut and highcut frequencies, filter order, and the seismic trace number to apply the filter on.
    It includes sliders for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
    """

    def setupUi(self, filterPreview, traceCount):
        """
        Setup the bandpass filter dialog layout, including frequency sliders, trace selection, and plots.
        Args:
            filterPreview (QDialog): The dialog instance to set up.
            traceCount (int): The total number of seismic traces available
        """
        # Dialog setup
        filterPreview.setObjectName("filterPreview")
        filterPreview.resize(1000, 800)
        self.traceCount = traceCount

        # Main Vertical Layout
        self.mainLayout = QtWidgets.QVBoxLayout(filterPreview)

        # Trace Number Input
        self.traceselectionlayout = QtWidgets.QHBoxLayout()
        self.traceSelectionlabel = QtWidgets.QLabel("Enter Seismic Trace Number:")
        self.traceSelectionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.traceselectionlayout.addWidget(self.traceSelectionlabel)
        self.traceNumberInput = QtWidgets.QSpinBox()
        self.traceNumberInput.setMinimum(0)
        self.traceNumberInput.setMaximum(max(0, self.traceCount - 1))  # Ensure max is non-negative
        self.traceselectionlayout.addWidget(self.traceNumberInput)
        self.mainLayout.addLayout(self.traceselectionlayout)

        # Filter Settings
        self.filterSettings = QtWidgets.QFrame()
        self.filterSettingsLayout = QtWidgets.QVBoxLayout(self.filterSettings)

        self.filterSettingsLabel = QtWidgets.QLabel("Filter Settings")
        self.filterSettingsLabel.setFont(QtGui.QFont("Segoe UI", 14))
        self.filterSettingsLayout.addWidget(self.filterSettingsLabel)

        # Frequency Sliders
        self.freqSliders = QtWidgets.QHBoxLayout()

        # Slider Style
        slider_style = """
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: #eee;
            height: 8px;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #0a84ff;
            border: 1px solid #5c5c5c;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -4px 0; /* Handle overlaps the groove */
        }
        QSlider::sub-page:horizontal {
            background: #0a84ff;
            border: 1px solid #0a84ff;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:horizontal {
            background: #c5c5c5;
            border: 1px solid #bbb;
            height: 8px;
            border-radius: 4px;
        }
        """

        # Slider Labels
        self.lowcutLabel = QtWidgets.QLabel("Lowcut Frequency (Hz):")
        self.lowcutLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.highcutLabel = QtWidgets.QLabel("Highcut Frequency (Hz):")
        self.highcutLabel.setFont(QtGui.QFont("Segoe UI", 10))

        # Lowcut Slider with Display
        self.lowcutSliderLayout = QtWidgets.QVBoxLayout()
        self.lowcutValueLabel = QtWidgets.QLabel("0 Hz")  # Initial frequency display
        self.lowcutValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lowcutValueLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.lowcutSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.lowcutSlider.setStyleSheet(slider_style)
        self.lowcutSlider.setRange(0, 10000)
        self.lowcutSlider.setValue(0)
        self.lowcutSlider.valueChanged.connect(self.update_lowcut_display)
        self.lowcutSliderLayout.addWidget(self.lowcutLabel)
        self.lowcutSliderLayout.addWidget(self.lowcutValueLabel)
        self.lowcutSliderLayout.addWidget(self.lowcutSlider)

        # Highcut Slider with Display
        self.highcutSliderLayout = QtWidgets.QVBoxLayout()
        self.highcutValueLabel = QtWidgets.QLabel("10000 Hz")  # Initial frequency display
        self.highcutValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.highcutValueLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.highcutSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.highcutSlider.setStyleSheet(slider_style)
        self.highcutSlider.setRange(0, 10000)
        self.highcutSlider.setValue(10000)
        self.highcutSlider.valueChanged.connect(self.update_highcut_display)
        self.highcutSliderLayout.addWidget(self.highcutLabel)
        self.highcutSliderLayout.addWidget(self.highcutValueLabel)
        self.highcutSliderLayout.addWidget(self.highcutSlider)

        # Connect Sliders for Constraints
        self.lowcutSlider.valueChanged.connect(self.update_slider_constraints)
        self.highcutSlider.valueChanged.connect(self.update_slider_constraints)

        # Filter Order Input
        self.filterOrder = QtWidgets.QVBoxLayout()
        self.filterOrderLabel = QtWidgets.QLabel("Filter Order:")
        self.filterOrderLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.filterOrderInput = QtWidgets.QLineEdit()
        self.filterOrderInput.setValidator(QtGui.QIntValidator(1, 100))  # Valid filter orders
        self.filterOrderInput.setText("")  # Default filter order
        self.filterOrderInput.setFixedWidth(50)
        self.filterOrder.addWidget(self.filterOrderLabel)
        self.filterOrder.addWidget(self.filterOrderInput)

        # Add Slider Layouts to Main Layout
        self.freqSliders.addLayout(self.lowcutSliderLayout)
        self.freqSliders.addLayout(self.highcutSliderLayout)
        self.filterSettingsLayout.addLayout(self.freqSliders)
        self.filterSettingsLayout.addLayout(self.filterOrder)
        self.mainLayout.addWidget(self.filterSettings)

        # Trace Plots
        self.tracePlot = pg.PlotWidget()
        self.tracePlot.setBackground("w")
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.setTitle("Original Trace")
        self.mainLayout.addWidget(self.tracePlot)

        self.reconstructedTracePlot = pg.PlotWidget()
        self.reconstructedTracePlot.setBackground("w")
        self.reconstructedTracePlot.showGrid(x=True, y=True)
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")
        self.mainLayout.addWidget(self.reconstructedTracePlot)

        # Create Accept and Cancel Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.mainLayout.addWidget(self.button_box)


        # Retranslate the UI
        self.retranslateUi(filterPreview)

    def retranslateUi(self, filterPreview):
        """Set the text for all UI elements."""
        filterPreview.setWindowTitle("Filter Preview")
        self.filterSettingsLabel.setText("Filter Settings")
        self.lowcutLabel.setText("Lowcut Frequency (Hz):")
        self.highcutLabel.setText("Highcut Frequency (Hz):")
        self.filterOrderLabel.setText("Filter Order:")
        self.traceSelectionlabel.setText("Enter Seismic Trace Number:")
        self.tracePlot.setTitle("Original Trace")
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")

    def update_lowcut_display(self, value):
        """Update the displayed value above the Lowcut slider."""
        self.lowcutValueLabel.setText(f"{value} Hz")

    def update_highcut_display(self, value):
        """Update the displayed value above the Highcut slider."""
        self.highcutValueLabel.setText(f"{value} Hz")

    def update_slider_constraints(self):
        """Ensure the sliders do not overlap."""
        self.highcutSlider.setMinimum(self.lowcutSlider.value() + 1)
        self.lowcutSlider.setMaximum(self.highcutSlider.value() - 1)

class lowpass_filter_UI(object):
    """
    lowpass_filter_UI
    This class sets up the UI for a lowpass filter dialog, allowing users to select
    a lowcut frequency, filter order, and the seismic trace number to apply the filter on.
    It includes a slider for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
    """
    def setupUi(self, filterPreview, traceCount):
        """
        Setup the lowpass filter dialog layout, including frequency slider, trace selection, and plots.
        Args:
            filterPreview (QDialog): The dialog instance to set up.
            traceCount (int): The total number of seismic traces available
        """

        filterPreview.setObjectName("filterPreview")
        filterPreview.resize(1000, 800)
        self.traceCount = traceCount

        # Main Vertical Layout
        self.mainLayout = QtWidgets.QVBoxLayout(filterPreview)

        # Trace Number Input
        self.traceselectionlayout = QtWidgets.QHBoxLayout()
        self.traceSelectionlabel = QtWidgets.QLabel("Enter Seismic Trace Number:")
        self.traceSelectionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.traceselectionlayout.addWidget(self.traceSelectionlabel)
        self.traceNumberInput = QtWidgets.QSpinBox()
        self.traceNumberInput.setMinimum(0)
        self.traceNumberInput.setMaximum(max(0, self.traceCount - 1))  # Ensure max is non-negative
        self.traceselectionlayout.addWidget(self.traceNumberInput)
        self.mainLayout.addLayout(self.traceselectionlayout)

        # Filter Settings
        self.filterSettings = QtWidgets.QFrame()
        self.filterSettingsLayout = QtWidgets.QVBoxLayout(self.filterSettings)

        self.filterSettingsLabel = QtWidgets.QLabel("Filter Settings")
        self.filterSettingsLabel.setFont(QtGui.QFont("Segoe UI", 14))
        self.filterSettingsLayout.addWidget(self.filterSettingsLabel)

        # Frequency Sliders
        self.freqSliders = QtWidgets.QHBoxLayout()

        # Slider Style
        slider_style = """
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: #eee;
            height: 8px;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #0a84ff;
            border: 1px solid #5c5c5c;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -4px 0; /* Handle overlaps the groove */
        }
        QSlider::sub-page:horizontal {
            background: #0a84ff;
            border: 1px solid #0a84ff;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:horizontal {
            background: #c5c5c5;
            border: 1px solid #bbb;
            height: 8px;
            border-radius: 4px;
        }
        """

        # Slider Labels
        self.lowcutLabel = QtWidgets.QLabel("Lowcut Frequency (Hz):")
        self.lowcutLabel.setFont(QtGui.QFont("Segoe UI", 10))

        # Lowcut Slider with Display
        self.lowcutSliderLayout = QtWidgets.QVBoxLayout()
        self.lowcutValueLabel = QtWidgets.QLabel("0 Hz")
        self.lowcutValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lowcutValueLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.lowcutSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.lowcutSlider.setStyleSheet(slider_style)
        self.lowcutSlider.setRange(0, 10000)
        self.lowcutSlider.setValue(0)
        self.lowcutSlider.valueChanged.connect(self.update_lowcut_display)
        self.lowcutSliderLayout.addWidget(self.lowcutLabel)
        self.lowcutSliderLayout.addWidget(self.lowcutValueLabel)
        self.lowcutSliderLayout.addWidget(self.lowcutSlider)

        # Connect Sliders for Constraints
        self.lowcutSlider.valueChanged.connect(self.update_slider_constraints)

        # Filter Order Input
        self.filterOrder = QtWidgets.QVBoxLayout()
        self.filterOrderLabel = QtWidgets.QLabel("Filter Order:")
        self.filterOrderLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.filterOrderInput = QtWidgets.QLineEdit()
        self.filterOrderInput.setValidator(QtGui.QIntValidator(1, 100))
        self.filterOrderInput.setText("")
        self.filterOrderInput.setFixedWidth(50)
        self.filterOrder.addWidget(self.filterOrderLabel)
        self.filterOrder.addWidget(self.filterOrderInput)

        # Add Slider Layouts to Main Layout
        self.freqSliders.addLayout(self.lowcutSliderLayout)
        self.filterSettingsLayout.addLayout(self.freqSliders)
        self.filterSettingsLayout.addLayout(self.filterOrder)
        self.mainLayout.addWidget(self.filterSettings)

        # Trace Plots
        self.tracePlot = pg.PlotWidget()
        self.tracePlot.setBackground("w")
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.setTitle("Original Trace")
        self.mainLayout.addWidget(self.tracePlot)

        self.reconstructedTracePlot = pg.PlotWidget()
        self.reconstructedTracePlot.setBackground("w")
        self.reconstructedTracePlot.showGrid(x=True, y=True)
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")
        self.mainLayout.addWidget(self.reconstructedTracePlot)

        
        # Create Accept and Cancel Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.mainLayout.addWidget(self.button_box)

        # Retranslate the UI
        self.retranslateUi(filterPreview)

    def retranslateUi(self, filterPreview):
        """Set the text for all UI elements."""
        filterPreview.setWindowTitle("Filter Preview")
        self.filterSettingsLabel.setText("Filter Settings")
        self.lowcutLabel.setText("Lowcut Frequency (Hz)")
        self.filterOrderLabel.setText("Filter Order:")
        self.traceSelectionlabel.setText("Enter Seismic Trace Number:")
        self.tracePlot.setTitle("Original Trace")
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")

    def update_lowcut_display(self, value):
        """Update the displayed value above the Lowcut slider."""
        self.lowcutValueLabel.setText(f"{value} Hz")

    def update_slider_constraints(self):
        """Ensure the sliders do not overlap."""
        pass
    
class highpass_filter_UI(object):
    """
    highpass_filter_UI
    This class sets up the UI for a highpass filter dialog, allowing users to select
    a highcut frequency, filter order, and the seismic trace number to apply the filter on.
    It includes a slider for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
    """

    def setupUi(self, filterPreview, traceCount):
        filterPreview.setObjectName("filterPreview")
        filterPreview.resize(1000, 800)
        self.traceCount = traceCount

        # Main Vertical Layout
        self.mainLayout = QtWidgets.QVBoxLayout(filterPreview)

        # Trace Number Input
        self.traceselectionlayout = QtWidgets.QHBoxLayout()
        self.traceSelectionlabel = QtWidgets.QLabel("Enter Seismic Trace Number:")
        self.traceSelectionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.traceselectionlayout.addWidget(self.traceSelectionlabel)
        self.traceNumberInput = QtWidgets.QSpinBox()
        self.traceNumberInput.setMinimum(0)
        self.traceNumberInput.setMaximum(max(0, self.traceCount - 1))  # Ensure max is non-negative
        self.traceselectionlayout.addWidget(self.traceNumberInput)
        self.mainLayout.addLayout(self.traceselectionlayout)

        # Filter Settings
        self.filterSettings = QtWidgets.QFrame()
        self.filterSettingsLayout = QtWidgets.QVBoxLayout(self.filterSettings)

        self.filterSettingsLabel = QtWidgets.QLabel("Filter Settings")
        self.filterSettingsLabel.setFont(QtGui.QFont("Segoe UI", 14))
        self.filterSettingsLayout.addWidget(self.filterSettingsLabel)

        # Frequency Sliders
        self.freqSliders = QtWidgets.QHBoxLayout()

        # Slider Style
        slider_style = """
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: #eee;
            height: 8px;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #0a84ff;
            border: 1px solid #5c5c5c;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -4px 0; /* Handle overlaps the groove */
        }
        QSlider::sub-page:horizontal {
            background: #0a84ff;
            border: 1px solid #0a84ff;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:horizontal {
            background: #c5c5c5;
            border: 1px solid #bbb;
            height: 8px;
            border-radius: 4px;
        }
        """

        # Slider Labels
        self.highcutLabel = QtWidgets.QLabel("Highcut Frequency (Hz):")
        self.highcutLabel.setFont(QtGui.QFont("Segoe UI", 10))

        # Highcut Slider with Display
        self.highcutSliderLayout = QtWidgets.QVBoxLayout()
        self.highcutValueLabel = QtWidgets.QLabel("10000 Hz")
        self.highcutValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.highcutValueLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.highcutSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.highcutSlider.setStyleSheet(slider_style)
        self.highcutSlider.setRange(0, 10000)
        self.highcutSlider.setValue(10000)
        self.highcutSlider.valueChanged.connect(self.update_highcut_display)
        self.highcutSliderLayout.addWidget(self.highcutLabel)
        self.highcutSliderLayout.addWidget(self.highcutValueLabel)
        self.highcutSliderLayout.addWidget(self.highcutSlider)

        # Connect Sliders for Constraints
        self.highcutSlider.valueChanged.connect(self.update_slider_constraints)

        # Filter Order Input
        self.filterOrder = QtWidgets.QVBoxLayout()
        self.filterOrderLabel = QtWidgets.QLabel("Filter Order:")
        self.filterOrderLabel.setFont(QtGui.QFont("Segoe UI", 10))
        self.filterOrderInput = QtWidgets.QLineEdit()
        self.filterOrderInput.setValidator(QtGui.QIntValidator(1, 100))
        self.filterOrderInput.setText("")
        self.filterOrderInput.setFixedWidth(50)
        self.filterOrder.addWidget(self.filterOrderLabel)
        self.filterOrder.addWidget(self.filterOrderInput)

        # Add Slider Layouts to Main Layout
        self.freqSliders.addLayout(self.highcutSliderLayout)
        self.filterSettingsLayout.addLayout(self.freqSliders)
        self.filterSettingsLayout.addLayout(self.filterOrder)
        self.mainLayout.addWidget(self.filterSettings)

        # Trace Plots
        self.tracePlot = pg.PlotWidget()
        self.tracePlot.setBackground("w")
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.setTitle("Original Trace")
        self.mainLayout.addWidget(self.tracePlot)

        self.reconstructedTracePlot = pg.PlotWidget()
        self.reconstructedTracePlot.setBackground("w")
        self.reconstructedTracePlot.showGrid(x=True, y=True)
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")
        self.mainLayout.addWidget(self.reconstructedTracePlot)
        
        # Create Accept and Cancel Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.mainLayout.addWidget(self.button_box)

        # Retranslate the UI
        self.retranslateUi(filterPreview)

    def retranslateUi(self, filterPreview):
        """Set the text for all UI elements."""
        filterPreview.setWindowTitle("Filter Preview")
        self.filterSettingsLabel.setText("Filter Settings")
        self.highcutLabel.setText("Highcut Frequency (Hz)")
        self.filterOrderLabel.setText("Filter Order:")
        self.traceSelectionlabel.setText("Enter Seismic Trace Number:")
        self.tracePlot.setTitle("Original Trace")
        self.reconstructedTracePlot.setTitle("Reconstructed Trace")

    def update_highcut_display(self, value):
        """Update the displayed value above the Highcut slider."""
        self.highcutValueLabel.setText(f"{value} Hz")

    def update_slider_constraints(self):
        """Ensure the sliders do not overlap."""
        pass


class FilterUI(object):
    """
    FilterUI
    This class is capable of creating different filter UIs based on the specified filter type.
    It supports bandpass, lowpass, and highpass filters, each with its own settings and layout.
    """

    def __init__(self, filter_type, trace_count):
        """
        Initialize the FilterUI for the specified filter type.
        :param filter_type: "bandpass", "lowpass", or "highpass"
        :param trace_count: The number of traces available
        """
        self.filter_type = filter_type
        self.trace_count = trace_count
        self.filter_class = self._get_filter_class(filter_type)(trace_count)

    def setupUi(self, filterPreview):
        """
        Set up the UI using the specific filter class.
        :param filterPreview: The parent QWidget for the UI.
        """
        self.filter_class.setupUi(filterPreview)

    def retranslateUi(self, filterPreview):
        """
        Retranslate UI if necessary (e.g., for localization).
        """
        self.filter_class.retranslateUi(filterPreview)

    @staticmethod
    def _get_filter_class(filter_type):
        """
        Map filter types to their respective nested classes.
        """
        filter_classes = {
            "bandpass": FilterUI.BandpassFilter,
            "lowpass": FilterUI.LowpassFilter,
            "highpass": FilterUI.HighpassFilter,
        }
        return filter_classes.get(filter_type, None)

    class BaseFilter:
        """
        BaseFilter
        This is a base class for all filter UIs, providing common setup methods.
        It should not be instantiated directly.
        """

        def __init__(self, trace_count):
            self.trace_count = trace_count

        def setupUi(self, filterPreview):
            """
            Set up the base UI layout for the filter dialog.
            :param filterPreview: The parent QWidget for the UI.
            """
            # Dialog setup
            filterPreview.setObjectName("filterPreview")
            filterPreview.resize(1000, 800)

           # Main Horizontal Splitter
            self.mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            
            # Left Panel
            self.leftPanel = QtWidgets.QWidget()
            self.leftLayout = QtWidgets.QVBoxLayout(self.leftPanel)

            # Trace Selection
            self.traceselectionlayout = QtWidgets.QHBoxLayout()
            self.traceSelectionlabel = QtWidgets.QLabel("Enter Seismic Trace Number:")
            self.traceSelectionlabel.setFont(QtGui.QFont("Segoe UI", 12))
            self.traceselectionlayout.addWidget(self.traceSelectionlabel)
            self.traceNumberInput = QtWidgets.QSpinBox()
            self.traceNumberInput.setMinimum(0)
            self.traceNumberInput.setMaximum(self.traceCount - 1 if self.traceCount > 0 else 0)  # Ensure max is valid
            self.traceNumberInput.setToolTip("Select a trace number for analysis.")
            self.traceselectionlayout.addWidget(self.traceNumberInput)
            self.leftLayout.addLayout(self.traceselectionlayout)

            # Filter Settings
            self.filterSettings = QtWidgets.QFrame()
            self.filterSettingsLayout = QtWidgets.QVBoxLayout(self.filterSettings)
            self.filterSettingsLabel = QtWidgets.QLabel("Filter Settings")
            self.filterSettingsLabel.setFont(QtGui.QFont("Segoe UI", 14))
            self.filterSettingsLayout.addWidget(self.filterSettingsLabel)
            self.leftLayout.addWidget(self.filterSettings)

            # Right Panel
            self.rightPanel = QtWidgets.QWidget()
            self.rightLayout = QtWidgets.QVBoxLayout(self.rightPanel)

            # QSplitter for Plots
            self.plotSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            
            # Trace Plots
            self.tracePlot = pg.PlotWidget()
            self.tracePlot.setBackground("w")
            self.tracePlot.showGrid(x=True, y=True)
            self.tracePlot.setTitle("Original Trace")
            self.rightLayout.addWidget(self.tracePlot)

            self.reconstructedTracePlot = pg.PlotWidget()
            self.reconstructedTracePlot.setBackground("w")
            self.reconstructedTracePlot.showGrid(x=True, y=True)
            self.reconstructedTracePlot.setTitle("Reconstructed Trace")
            self.rightLayout.addWidget(self.reconstructedTracePlot)

            # Buttons
            self.buttonLayout = QtWidgets.QHBoxLayout()
            self.acceptButton = QtWidgets.QPushButton("Accept")
            self.cancelButton = QtWidgets.QPushButton("Cancel")
            self.buttonLayout.addWidget(self.acceptButton)
            self.buttonLayout.addWidget(self.cancelButton)
            self.rightLayout.addLayout(self.buttonLayout)

        def retranslateUi(self, filterPreview):
            filterPreview.setWindowTitle("Filter Preview")
            self.filterSettingsLabel.setText("Filter Settings")
            self.traceSelectionlabel.setText("Enter Seismic Trace Number:")
            self.tracePlot.setTitle("Original Trace")
            self.reconstructedTracePlot.setTitle("Reconstructed Trace")

    class BandpassFilter(BaseFilter):
        """
        BandpassFilter
        This class sets up the UI for a bandpass filter dialog, allowing users to select
        lowcut and highcut frequencies, filter order, and the seismic trace number to apply the filter on.
        It includes sliders for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
        """

        def setupUi(self, filterPreview):
            """
            Set up the bandpass filter dialog layout, including frequency sliders, trace selection, and plots.
            Args:
                filterPreview (QDialog): The dialog instance to set up.
            """
            # Call the base setup
            super().setupUi(filterPreview)

            # Frequency Sliders
            self.freqSliders = QtWidgets.QHBoxLayout()
            self.lowcutSliderLayout = self._create_slider_layout("Lowcut Frequency (Hz):", 0)
            self.highcutSliderLayout = self._create_slider_layout("Highcut Frequency (Hz):", 10000)
            self.freqSliders.addLayout(self.lowcutSliderLayout)
            self.freqSliders.addLayout(self.highcutSliderLayout)
            self.filterSettingsLayout.addLayout(self.freqSliders)

        def _create_slider_layout(self, label_text, initial_value):
            return FilterUI._create_slider_layout(label_text, initial_value)

    class LowpassFilter(BaseFilter):
        """
        LowpassFilter
        This class sets up the UI for a lowpass filter dialog, allowing users to select
        a lowcut frequency, filter order, and the seismic trace number to apply the filter on.
        It includes a slider for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
        """
        def setupUi(self, filterPreview):
            """
            Set up the lowpass filter dialog layout, including frequency slider, trace selection, and plots.
            Args:
                filterPreview (QDialog): The dialog instance to set up.
            """
            # Call the base setup
            super().setupUi(filterPreview)

            # Frequency Slider
            self.freqSliders = QtWidgets.QHBoxLayout()
            self.lowcutSliderLayout = self._create_slider_layout("Lowcut Frequency (Hz):", 0)
            self.freqSliders.addLayout(self.lowcutSliderLayout)
            self.filterSettingsLayout.addLayout(self.freqSliders)

        def _create_slider_layout(self, label_text, initial_value):
            return FilterUI._create_slider_layout(label_text, initial_value)

    class HighpassFilter(BaseFilter):
        """
        HighpassFilter
        This class sets up the UI for a highpass filter dialog, allowing users to select
        a highcut frequency, filter order, and the seismic trace number to apply the filter on.
        It includes a slider for frequency selection, a spin box for trace number input, and plots for original and reconstructed traces.
        """

        def setupUi(self, filterPreview):
            """
            Set up the highpass filter dialog layout, including frequency slider, trace selection, and plots.
            Args:
                filterPreview (QDialog): The dialog instance to set up.
            """
            # Call the base setup
            super().setupUi(filterPreview)

            # Frequency Slider
            self.freqSliders = QtWidgets.QHBoxLayout()
            self.highcutSliderLayout = self._create_slider_layout("Highcut Frequency (Hz):", 10000)
            self.freqSliders.addLayout(self.highcutSliderLayout)
            self.filterSettingsLayout.addLayout(self.freqSliders)

        def _create_slider_layout(self, label_text, initial_value):
            return FilterUI._create_slider_layout(label_text, initial_value)

    @staticmethod
    def _create_slider_layout(label_text, initial_value):
        """
        Create a slider layout with a label and a value display.
        Args:
            label_text (str): The text for the label.
            initial_value (int): The initial value for the slider.
        Returns:
            QtWidgets.QVBoxLayout: The layout containing the label, value display, and slider.
        """

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel(label_text)
        label.setFont(QtGui.QFont("Segoe UI", 10))
        value_label = QtWidgets.QLabel(f"{initial_value} Hz")
        value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(0, 10000)
        slider.setValue(initial_value)
        slider.valueChanged.connect(lambda value, lbl=value_label: lbl.setText(f"{value} Hz"))
        layout.addWidget(label)
        layout.addWidget(value_label)
        layout.addWidget(slider)
        return layout

class TraceAnalysisWindowUI(object):
    """
    TraceAnalysisWindowUI
    This class sets up the UI for a trace analysis window, allowing users to select a seismic trace number and an analysis method.
    It includes a combo box for analysis selection, a spin box for trace number input, and plots for the original trace,
    frequency domain analysis, and advanced analysis (e.g., spectrogram).
    """

    def setupUI(self, TraceAnalysisWindow, traceCount):
        """
        Set up the trace analysis window layout, including trace selection, analysis method selection, and plots.
        Args:
            TraceAnalysisWindow (QDialog): The dialog instance to set up.
            traceCount (int): The total number of seismic traces available
        """
        # Dialog setup
        TraceAnalysisWindow.setObjectName("Trace Analysis")
        TraceAnalysisWindow.resize(1000, 800)
        self.traceCount = traceCount

        # Main Horizontal Splitter
        self.mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # Left Panel
        self.leftPanel = QtWidgets.QWidget()
        self.leftLayout = QtWidgets.QVBoxLayout(self.leftPanel)

        # Trace Selection
        self.traceselectionlayout = QtWidgets.QHBoxLayout()
        self.traceSelectionlabel = QtWidgets.QLabel("Enter Seismic Trace Number:")
        self.traceSelectionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.traceselectionlayout.addWidget(self.traceSelectionlabel)
        self.traceNumberInput = QtWidgets.QSpinBox()
        self.traceNumberInput.setMinimum(0)
        self.traceNumberInput.setMaximum(self.traceCount - 1 if self.traceCount > 0 else 0)  # Ensure max is valid
        self.traceNumberInput.setToolTip("Select a trace number for analysis.")
        self.traceselectionlayout.addWidget(self.traceNumberInput)
        self.leftLayout.addLayout(self.traceselectionlayout)

        # Analysis Combo Box
        self.comboBoxLayout = QtWidgets.QHBoxLayout()
        self.analysisLabel = QtWidgets.QLabel("Select Analysis Method:")
        self.analysisLabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.analysisComboBox = QtWidgets.QComboBox()
        self.analysisComboBox.addItems(["FFT", "Periodogram", "Welch Periodogram", "Spectrogram", "Wavelet Transform", "Instantaneous Amplitude", "Instantaneous Phase", "Instantaneous Frequency"])
        self.comboBoxLayout.addWidget(self.analysisLabel)
        self.comboBoxLayout.addWidget(self.analysisComboBox)
        self.leftLayout.addLayout(self.comboBoxLayout)

        # Ok and Cancel Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.leftLayout.addWidget(self.button_box)
        #self.leftLayout.addStretch()  # Push everything to the top

        # Right Panel
        self.rightPanel = QtWidgets.QWidget()
        self.rightLayout = QtWidgets.QVBoxLayout(self.rightPanel)

        # QSplitter for Plots
        self.plotSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # Trace Plot
        self.tracePlot = pg.PlotWidget()
        self.tracePlot.setBackground("w")
        self.tracePlot.showGrid(x=True, y=True)
        self.tracePlot.setTitle("Original Trace")
        self.tracePlot.setLabel("bottom", "Time (s)")
        self.tracePlot.setLabel("left", "Amplitude")
        self.plotSplitter.addWidget(self.tracePlot)

        # Analysis Section (Frequency Plot and Image Plot)
        self.analysisSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Analysis Plot (Frequency Domain)
        self.frequencyPlot = pg.PlotWidget(labels={'left': 'Frequency [Hz]', 'bottom': 'Amplitude'})
        self.frequencyPlot.setBackground("w")
        self.frequencyPlot.showGrid(x=True, y=True)
        self.analysisSplitter.addWidget(self.frequencyPlot)

        
        # Image Plot for Advanced Analysis (e.g., Spectrogram, Wavelet Transform)
        self.image = pg.ImageItem(axisOrder='col-major')  # This arg is purely for performance
        self.imagePlot = pg.PlotWidget(labels={'left': 'Frequency [Hz]', 'bottom': 'Time [s]'})
        self.imagePlot.setBackground("w")
        self.imagePlot.showGrid(x=True, y=True)
        self.imagePlot.setVisible(False)  # Initially hidden
        self.analysisSplitter.addWidget(self.imagePlot)
        
        
        # Add the analysis splitter to the main splitter
        self.plotSplitter.addWidget(self.analysisSplitter)

        # Add plot splitter to right panel layout
        self.rightLayout.addWidget(self.plotSplitter)

        # Add panels to the main splitter
        self.mainSplitter.addWidget(self.leftPanel)
        self.mainSplitter.addWidget(self.rightPanel)

        # Set stretch factors for resizing behavior
        self.mainSplitter.setStretchFactor(0, 1)  # Left panel has less priority
        self.mainSplitter.setStretchFactor(1, 3)  # Right panel has more priority

        # Add the main splitter to the main layout
        self.mainLayout = QtWidgets.QVBoxLayout(TraceAnalysisWindow)
        self.mainLayout.addWidget(self.mainSplitter)

        # Retranslate the UI
        self.retranslateUi(TraceAnalysisWindow)

    def retranslateUi(self, TraceAnalysisWindow):
        """Set the text for all UI elements."""
        TraceAnalysisWindow.setWindowTitle("Trace Analysis")
        self.traceSelectionlabel.setText("Enter Seismic Trace Number:")
        self.tracePlot.setTitle("Original Trace")
        self.tracePlot.setLabel("bottom", "Time (s)")
        self.tracePlot.setLabel("left", "Amplitude")

    def togglePlots(self, show_image: bool):
        """Toggle visibility between frequencyPlot and imagePlot."""
        self.frequencyPlot.setVisible(not show_image)
        self.imagePlot.setVisible(show_image)  # Show or hide the image plot based on the boolean value


class WaveletWindowUI(QtWidgets.QDialog):
    """
    WaveletWindowUI
    This class sets up the UI for a wavelet selection window, allowing users to choose a theoretical seismic wavelet
    and input parameters for the selected wavelet. It includes a combo box for wavelet selection and a form layout for parameter inputs.
    """

    def __init__(self, parent=None):
        """
        Initialize the WaveletWindowUI.
        :param parent: The parent widget for the dialog.
        """

        super().__init__(parent)
        self.setWindowTitle("Wavelets")

        # Main Layout
        self.main_layout = QtWidgets.QVBoxLayout()
        
        # Wavelet Selection Combo Box
        self.wavelet_label = QtWidgets.QLabel("Select the Theoretical Seismic Wavelet:")
        self.wavelet_combo = QtWidgets.QComboBox()
        self.wavelet_combo.addItems(["Ricker", "Chirp", "Ormsby", "Minimum Phase", "Klauder", "Boomer", "Zero Phase"])
        self.main_layout.addWidget(self.wavelet_label)
        self.main_layout.addWidget(self.wavelet_combo)

        # Parameter Input Area
        self.parameter_widget = QtWidgets.QWidget()
        self.parameter_layout = QtWidgets.QFormLayout()
        self.parameter_widget.setLayout(self.parameter_layout)
        self.main_layout.addWidget(self.parameter_widget)

        # OK and Cancel Buttons
        self.button_layout = QtWidgets.QHBoxLayout()
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.importwavelet_button = QtWidgets.QPushButton("Import estimated wavelet...")
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.importwavelet_button)
        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)

    def add_parameter_input(self, label_text, param_name):
        """Add a single input field for a wavelet parameter."""
        label = QtWidgets.QLabel(label_text)
        line_edit = QtWidgets.QLineEdit()
        self.parameter_layout.addRow(label, line_edit)
        return line_edit

    def clear_parameters(self):
        """Clear all parameter input fields."""
        while self.parameter_layout.count():
            widget = self.parameter_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

# UI class for the Magnetic Data Editor
class Maggy_editor_UI(object):
    """
    Maggy_editor_UI
    This class sets up the UI for the Maggy Editor, which includes a table for magnetic data,
    a tree view for loaded files, and docks for data visualization and analysis.
    It also includes a menu bar for data analysis options and a status bar for messages.
    """

    def setupUI(self, MaggyEditor):
        """
        Set up the main UI layout for the Maggy Editor.
        Args:
            MaggyEditor (QMainWindow): The main window instance to set up.
        """
        # Main Window Setup
        MaggyEditor.setObjectName("Maggy Editor")
        MaggyEditor.resize(1200, 800)  # Increase size for better layout

        # Central Widget (TableWidget takes main focus)
        self.centralwidget = QtWidgets.QWidget(MaggyEditor)
        MaggyEditor.setCentralWidget(self.centralwidget)
        main_layout = QtWidgets.QVBoxLayout(self.centralwidget)

        # === Magnetic Line selection ComboBox ===
        self.lineSelectionLayout = QtWidgets.QHBoxLayout()
        self.lineSelectionLabel = QtWidgets.QLabel("Select Magnetic Line:")
        self.lineSelectionLabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.lineSelectionLayout.addWidget(self.lineSelectionLabel)
        self.lineSelection = QtWidgets.QComboBox()
        self.lineSelectionLayout.addWidget(self.lineSelection)
        main_layout.addLayout(self.lineSelectionLayout)

        # === Data Table ===
        self.dataTable = QtWidgets.QTableWidget()
        main_layout.addWidget(self.dataTable)

        # === TreeView Dock (Moved to a DockWidget) ===
        self.treeDock = QtWidgets.QDockWidget("Loaded Files", MaggyEditor)
        self.treeDock.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea | QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.treeDock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.treeDock.setMinimumWidth(150)  # Make the dock smaller
        self.treeDock.setMaximumWidth(250)

        # TreeView inside Dock
        self.treeview = QtWidgets.QTreeWidget()
        self.treeview.setHeaderLabel("Loaded Files")
        root = QtWidgets.QTreeWidgetItem(["Loaded Files"])
        self.treeview.addTopLevelItem(root)
        self.treeDock.setWidget(self.treeview)  # Attach to Dock

        # Add TreeView Dock to Main Window
        MaggyEditor.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.treeDock)

        # === Graphs and Plots Dock ===
        self.plotDock = QtWidgets.QDockWidget("Data Visualization", MaggyEditor)
        self.plotDock.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
        self.plotDock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.plotDock.setMinimumHeight(150)
        self.plotDock.setMaximumHeight(250)

        # Placeholder Widget inside the Plot Dock
        self.plotDock.setWidget(QtWidgets.QWidget())
        MaggyEditor.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.plotDock)

        # Add a Pyqtgraph PlotWidget to the placeholder widget
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground("w")
        self.plotWidget.showGrid(x=True, y=True)
        self.plotDock.setWidget(self.plotWidget)

        # Linear Region for Zooming
        self.linearRegion = pg.LinearRegionItem()

        # === Menu Bar ===
        self.menuBar = QtWidgets.QMenuBar(MaggyEditor)
        self.menuFile = QtWidgets.QMenu("File", self.menuBar)
        self.menuBar.addMenu(self.menuFile)
        self.DataAnalysis = QtWidgets.QMenu("Data Analysis...", self.menuBar)
        self.menuBar.addMenu(self.DataAnalysis)
        self.plotting_action = self.DataAnalysis.addAction("Plot Data")
        self.plotting_action.triggered.connect(MaggyEditor.MaggyAnalysisWin) 
        
        self.filter_sort_action = self.DataAnalysis.addAction("Filter & Sorting")
        #self.filter_sort_action.triggered.connect(MaggyEditor.enable_filter_sorting)
        self.channelmath_action = self.DataAnalysis.addAction("Channel Math")
        self.channelmath_action.triggered.connect(MaggyEditor.create_column)
        self.delcolumn_action = self.DataAnalysis.addAction("Delete Column")
        self.delcolumn_action.triggered.connect(MaggyEditor.delete_column)
        
        MaggyEditor.setMenuBar(self.menuBar)

        # === Status Bar ===
        self.statusBar = QtWidgets.QStatusBar(MaggyEditor)
        self.statusBar.showMessage("Ready")
        MaggyEditor.setStatusBar(self.statusBar)

        self.retranslateUi(MaggyEditor)
        QtCore.QMetaObject.connectSlotsByName(MaggyEditor)


    # === Ui window for plotting data ===
    def plot_data_ui_win(self):
        """
        Create a new window for plotting data.
        """
        self.plot_data_win = QtWidgets.QWidget()
        self.plot_data_win.setWindowTitle("Maggy Analysis Window")
        #self.plot_data_win.resize(800, 600)
            
        # Main Horizontal Splitter
        self.mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            
        # Left Panel
        self.leftPanel = QtWidgets.QWidget()
        self.leftLayout = QtWidgets.QVBoxLayout(self.leftPanel)

        # X column Selection
        self.xcolumnselsctionlayout = QtWidgets.QHBoxLayout()
        self.xcolumnselsctionlabel = QtWidgets.QLabel("Enter the X column name for plotting:") # Change to x column name
        self.xcolumnselsctionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.xcolumnselsctionlayout.addWidget(self.xcolumnselsctionlabel)
        self.xcolumnInput = QtWidgets.QComboBox()
        self.xcolumnselsctionlayout.addWidget(self.xcolumnInput)
        self.leftLayout.addLayout(self.xcolumnselsctionlayout)

        # Y column Selection
        self.ycolumnselsctionlayout = QtWidgets.QHBoxLayout()
        self.ycolumnselsctionlabel = QtWidgets.QLabel("Enter the Y column name for plotting:") # Change to y column name
        self.ycolumnselsctionlabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.ycolumnselsctionlayout.addWidget(self.ycolumnselsctionlabel)
        self.ycolumnInput = QtWidgets.QComboBox()
        self.ycolumnselsctionlayout.addWidget(self.ycolumnInput)
        self.leftLayout.addLayout(self.ycolumnselsctionlayout)

        # Analysis Combo Box
        self.comboBoxLayout = QtWidgets.QHBoxLayout()
        self.analysisLabel = QtWidgets.QLabel("Select Analysis Method:")
        self.analysisLabel.setFont(QtGui.QFont("Segoe UI", 12))
        self.analysisComboBox = QtWidgets.QComboBox()
        self.analysisComboBox.addItems(["FFT", "Periodogram", "Welch Periodogram", "Spectrogram", "Wavelet Transform"])
        self.comboBoxLayout.addWidget(self.analysisLabel)
        self.comboBoxLayout.addWidget(self.analysisComboBox)
        self.leftLayout.addLayout(self.comboBoxLayout)

        # Ok and Cancel Buttons
        #self.button_box = QtWidgets.QDialogButtonBox(
            #QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        #)
        #self.leftLayout.addWidget(self.button_box)
        #self.leftLayout.addStretch()  # Push everything to the top

        # Right Panel
        self.rightPanel = QtWidgets.QWidget()
        self.rightLayout = QtWidgets.QVBoxLayout(self.rightPanel)

        # QSplitter for Plots
        self.plotSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # Data Plot
        self.Plot = pg.PlotWidget()
        self.Plot.setBackground("w")
        self.Plot.showGrid(x=True, y=True)
        self.plotSplitter.addWidget(self.Plot)

        # Analysis Section (Frequency Plot and Image Plot)
        self.analysisSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Analysis Plot (Frequency Domain)
        self.frequencyPlot = pg.PlotWidget()
        self.frequencyPlot.setBackground("w")
        self.frequencyPlot.showGrid(x=True, y=True)
        self.analysisSplitter.addWidget(self.frequencyPlot)

            
        # Create a matplotlib figure and canvas for Spectrogram plot and Wavelet transform plot
        from matplotlib import pyplot as plt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
        self.figure = plt.figure() # Create a figure
        plt.ion() # Set interactive mode on for matplotlib
        self.figure.canvas = FigureCanvas(self.figure) # Create a canvas for the figure
        self.figure.canvas.hide()
        self.analysisSplitter.addWidget(self.figure.canvas)

            
        # Add the analysis splitter to the main splitter
        self.plotSplitter.addWidget(self.analysisSplitter)

        # Add plot splitter to right panel layout
        self.rightLayout.addWidget(self.plotSplitter)

        # Add panels to the main splitter
        self.mainSplitter.addWidget(self.leftPanel)
        self.mainSplitter.addWidget(self.rightPanel)

        # Set stretch factors for resizing behavior
        self.mainSplitter.setStretchFactor(0, 1)  # Left panel has less priority
        self.mainSplitter.setStretchFactor(1, 3)  # Right panel has more priority

        # Add the main splitter to the main layout
        self.mainLayout = QtWidgets.QVBoxLayout(self.plot_data_win)
        self.mainLayout.addWidget(self.mainSplitter)


        return self.plot_data_win
    
    class Channel_MathDialog(QtWidgets.QDialog):
        """Dialog for channel math operations. It wil be triggered """
        def __init__(self, columns, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Channel Math")
            self.setMinimumWidth(500)
            self.expression = ""
            self.column_assignments = {}
            
            layout = QtWidgets.QVBoxLayout(self)

            # Expression input
            layout.addWidget(QtWidgets.QLabel("Expression:"))
            self.expression_editor = QtWidgets.QTextEdit()
            layout.addWidget(self.expression_editor)

            # Insert Channel Variable button
            insert_btn = QtWidgets.QPushButton("Insert Channel Variable")
            insert_btn.clicked.connect(self.insert_variable(columns, layout))
            insert_btn.setToolTip("Insert a channel variable (C0, C1, etc.) into the expression editor.")
            layout.addWidget(insert_btn)

            # Channel assignments area
            layout.addWidget(QtWidgets.QLabel("Assign channels:"))
            self.channel_assignments = [0] # List to store channel assignments
           

            # Expression file load/save
            file_layout = QtWidgets.QHBoxLayout()
            self.expr_path = QtWidgets.QLineEdit()
            file_layout.addWidget(self.expr_path)
            load_btn = QtWidgets.QPushButton("Load")
            load_btn.clicked.connect(self.load_expression_file)
            save_btn = QtWidgets.QPushButton("Save")
            save_btn.clicked.connect(self.save_expression_file)
            file_layout.addWidget(load_btn)
            file_layout.addWidget(save_btn)
            layout.addLayout(file_layout)

            # Buttons
            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel| QtWidgets.QDialogButtonBox.StandardButton.Reset)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Reset).clicked.connect(self.clear_fields)
            layout.addWidget(button_box)

        def insert_variable(self, columns, layout):
            """ Insert a new variable as a channel in the expression editor (C0, C1, etc.) and update the channel assignments list."""
            index = len(self.channel_assignments)
            var_name = f"C{index}"
            self.expression_editor.insertPlainText(var_name)
            self.channel_assignments.append((var_name, None))
            
            for i in enumerate(self.channel_assignments):  
                hbox = QtWidgets.QHBoxLayout()
                var_label = QtWidgets.QLabel(f"C{i} =")
                combo = QtWidgets.QComboBox()
                combo.addItems(columns)
                hbox.addWidget(var_label)
                hbox.addWidget(combo)
                layout.addLayout(hbox)
                self.channel_assignments.append((f"C{i}", combo))

        def clear_fields(self):
            """Clear the expression editor and reset channel assignments."""
            self.expression_editor.clear()
            for _, combo in self.channel_assignments:
                combo.setCurrentIndex(0)

        def load_expression_file(self):
            """Load an expression from a file and populate the expression editor."""
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Expression File", "", "Expression Files (*.exp)")
            if path:
                with open(path, 'r') as f:
                    self.expression_editor.setText(f.read())
                self.expr_path.setText(path)

        def save_expression_file(self):
            """Save the current expression to a file."""
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Expression File", "", "Expression Files (*.exp)")
            if path:
                with open(path, 'w') as f:
                    f.write(self.expression_editor.toPlainText())
                self.expr_path.setText(path)

        def get_result(self):
            """Get the current expression and channel assignments."""
            expr = self.expression_editor.toPlainText()
            vars_mapping = {name: combo.currentText() for name, combo in self.channel_assignments}
            return expr, vars_mapping

    class ChannelMathDialog(QtWidgets.QDialog):
        """
        A dialog window that allows users to define a new channel based on a mathematical expression.
        Users can assign existing columns to variable names and write expressions using them.
        A live SQL translation preview is also provided.
        """
        def __init__(self, columns, parent=None):
            """
            Initialize the ChannelMathDialog.
            :param columns: List of column names to be used in the expression.
            :param parent: The parent widget for the dialog.
            """

            super().__init__(parent)
            self.setWindowTitle("Channel Math")
            self.setMinimumWidth(600)
            self.setMinimumHeight(400)
            self.columns = columns
            self.column_assignments = []

            layout = QtWidgets.QVBoxLayout(self)

            # Expression editor
            layout.addWidget(QtWidgets.QLabel("Expression:"))
            self.expression_editor = QtWidgets.QTextEdit()
            self.expression_editor.textChanged.connect(self.update_preview)
            layout.addWidget(self.expression_editor)

            # Button to insert variable
            self.insert_btn = QtWidgets.QPushButton("Insert Channel Variable")
            self.insert_btn.clicked.connect(self.insert_variable)
            layout.addWidget(self.insert_btn)

            # Channel assignments area
            self.assign_layout = QtWidgets.QVBoxLayout()
            layout.addLayout(self.assign_layout)

            # SQL preview pane
            # Collapsible Preview Group
            self.preview_group = QtWidgets.QGroupBox("SQL Preview")
            self.preview_group.setCheckable(True)
            self.preview_group.setChecked(True)

            preview_layout = QtWidgets.QVBoxLayout()
            self.sql_preview = QtWidgets.QTextEdit()
            self.sql_preview.setReadOnly(True)
            preview_layout.addWidget(self.sql_preview)
            self.preview_group.setLayout(preview_layout)

            # Add to layout
            layout.addWidget(self.preview_group)


            # File save/load
            file_layout = QtWidgets.QHBoxLayout()
            self.expr_path = QtWidgets.QLineEdit()
            file_layout.addWidget(self.expr_path)
            load_btn = QtWidgets.QPushButton("Load")
            load_btn.clicked.connect(self.load_expression_file)
            save_btn = QtWidgets.QPushButton("Save")
            save_btn.clicked.connect(self.save_expression_file)
            file_layout.addWidget(load_btn)
            file_layout.addWidget(save_btn)
            layout.addLayout(file_layout)

            # Dialog buttons
            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                                    QtWidgets.QDialogButtonBox.StandardButton.Cancel |
                                                    QtWidgets.QDialogButtonBox.StandardButton.Reset)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Reset).clicked.connect(self.clear_fields)
            layout.addWidget(button_box)

        def insert_variable(self):
            """
            Insert a new variable as a channel in the expression editor (C0, C1, etc.) and add it to the channel assignments.
            """
            index = len(self.column_assignments)
            var_name = f"C{index}"
            self.expression_editor.insertPlainText(var_name)

            # Add channel assignment dropdown
            hbox = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(f"{var_name} =")
            combo = QtWidgets.QComboBox()
            combo.addItems(self.columns)
            combo.currentTextChanged.connect(self.update_preview)
            hbox.addWidget(label)
            hbox.addWidget(combo)
            self.assign_layout.addLayout(hbox)
            self.column_assignments.append((var_name, combo))

        def accept(self):
            """
            Validate the expression and channel assignments before accepting the dialog.
            If validation fails, show a warning message.
            """
            valid, message = self.validate_expression()
            if not valid:
                QtWidgets.QMessageBox.warning(self, "Validation Error", message)
                return
            super().accept()

        def clear_fields(self):
            """
            Clear the expression editor and reset all channel assignments.
            """

            self.expression_editor.clear()
            self.sql_preview.clear()
            for _, combo in self.column_assignments:
                combo.setCurrentIndex(0)

        def save_expression_file(self):
            """
            Save the current expression and channel assignments to a file.
            """

            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Expression File", "", "Expression Files (*.exp)")
            if path:
                try:
                    data = {
                        "expression": self.expression_editor.toPlainText(),
                        "mappings": {v: c.currentText() for v, c in self.column_assignments if c}
                    }
                    with open(path, 'w') as f:
                        json.dump(data, f, indent=2)
                    self.expr_path.setText(path)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Save Error", str(e))

        def load_expression_file(self):
            """
            Load an expression from a file and populate the expression editor and channel assignments.
            """
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Expression File", "", "Expression Files (*.exp)")
            if path:
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        self.expression_editor.setText(data.get("expression", ""))
                        for var, col in data.get("mappings", {}).items():
                            for assigned_var, combo in self.column_assignments:
                                if assigned_var == var:
                                    idx = combo.findText(col)
                                    if idx >= 0:
                                        combo.setCurrentIndex(idx)
                    self.expr_path.setText(path)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Load Error", str(e))

        def update_preview(self):
            """
            Update the SQL preview based on the current expression and channel assignments.
            """ 
            try: 
                # Get the current expression and channel assignments
                expr = self.expression_editor.toPlainText()
                mappings = {var: combo.currentText() for var, combo in self.column_assignments if combo}

                # Replace Cx.offset(n)
                def offset_repl(match):
                    var = match.group(1)
                    offset = int(match.group(2))
                    col = mappings.get(var, var)
                    func = "LEAD" if offset > 0 else "LAG"
                    return f'{func}("{col}", {abs(offset)}) OVER (ORDER BY rowid)'

                expr = re.sub(r'\b(C\d+)\.offset\((-?\d+)\)', offset_repl, expr)
                # Replace rollmean, rollsum
                def roll_repl(match):
                    func_name = match.group(1)
                    var = match.group(2)
                    window = int(match.group(3))
                    col = mappings.get(var, var)

                    if func_name == "mean":
                        agg_func = "AVG"
                    elif func_name == "sum":
                        agg_func = "SUM"
                    else:
                        raise ValueError(f"Unsupported rolling function: {func_name}")

                    preceding = (window - 1) // 2
                    following = window // 2

                    return f"{agg_func}({col}) OVER (ORDER BY rowid ROWS BETWEEN {preceding} PRECEDING AND {following} FOLLOWING)"

                # --- Step 1: handle rollmean / rollsum
                expr = re.sub(r'\broll(mean|sum)\(\s*(C\d+)\s*,\s*(\d+)\s*\)', 
                    roll_repl, expr)
                
                # Replace simple Cx with actual column names
                for var, col in mappings.items():
                    expr = re.sub(rf'\b{var}\b', f'"{col}"', expr)

                # --- MATH FUNCTIONS ---
                SQL_FUNCTIONS = {
                    "square": r"POWER(\1, 2)",
                    "sqrt": r"SQRT(\1)",
                    "abs": r"ABS(\1)",
                    "log": r"LOG(\1)",
                    "ln": r"LOG(\1)",
                    "log10": r"LOG10(\1)",
                    "cos": r"COS(\1)",
                    "sin": r"SIN(\1)",
                    "tan": r"TAN(\1)",
                    "atan": r"ATAN(\1)",
                    "atan2": r"ATAN2(\1)",
                    "pow": r"POWER(\1)",  # Note: Ideally use pow(x,y) pattern
                    "floor": r"FLOOR(\1)",
                    "ceil": r"CEIL(\1)",
                    "round": r"ROUND(\1)",
                    "exp": r"EXP(\1)"
                }

                for func, sql in SQL_FUNCTIONS.items():
                    expr = re.sub(fr'{func}\(([^)]+)\)', sql, expr)

                # --- STATISTICAL FUNCTIONS ---
                STAT_FUNCTIONS = {
                    "mean": r"AVG(\1)",
                    "median": r"MEDIAN(\1)",  # Only some DBs support this
                    "std": r"STDDEV(\1)",
                    "var": r"VARIANCE(\1)",
                    "min": r"MIN(\1)",
                    "max": r"MAX(\1)",
                    "sum": r"SUM(\1)",
                    "count": r"COUNT(\1)",
                    "countdistinct": r"COUNT(DISTINCT \1)",
                    "first": r"FIRST_VALUE(\1)",
                    "last": r"LAST_VALUE(\1)",
                }

                for func, sql in STAT_FUNCTIONS.items():
                    expr = re.sub(fr'{func}\(([^)]+)\)', sql, expr)


                # Quick validation for illegal characters (rudimentary)

                if re.search(r'[^\w\s\+\-\*\/\(\)\.,"]', expr):
                    self.sql_preview.setPlainText("Expression contains invalid characters.")

                self.sql_preview.setPlainText(expr)
            except Exception as e:
                self.sql_preview.setPlainText(f"Error in expression: {str(e)}")

        def validate_expression(self):
            """
            Validates the expression before submission.
            - Checks if all used Cx variables are assigned to actual columns.
            - Returns (bool, message)
            """
            expr = self.expression_editor.toPlainText()
            used_vars = set(re.findall(r'\bC\d+\b', expr))
            assigned_vars = {v for v, combo in self.column_assignments if combo.currentText()}

            missing = used_vars - assigned_vars
            if missing:
                return False, f"Missing channel assignment(s) for: {', '.join(missing)}"

            # Basic SQL safety check (prevent semicolons, DROP etc.)
            if ";" in expr or any(keyword in expr.upper() for keyword in ["DROP", "DELETE", "INSERT", "UPDATE"]):
                return False, "Invalid or unsafe SQL-like expression."

            return True, "Expression valid."

        def get_result(self):
            """
            Get the current expression and channel assignments.
            Returns:
                tuple: (expression, mapping) where mapping is a dict of variable names to column names.
            """

            expr = self.expression_editor.toPlainText()
            mapping = {var: combo.currentText() for var, combo in self.column_assignments}
            return expr, mapping
    
    class ColumnDeleteDialog(QtWidgets.QDialog):
        """Dialog for deleting a column."""
        def __init__(self, columns, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Delete Column")
            self.setMinimumWidth(300)

            layout = QtWidgets.QVBoxLayout(self)

            # Column selection
            self.column_label = QtWidgets.QLabel("Select column to delete:")
            self.column_combo = QtWidgets.QComboBox()
            self.column_combo.addItems(columns)
            layout.addWidget(self.column_label)
            layout.addWidget(self.column_combo)

            # Buttons
            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                                    QtWidgets.QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)

        def get_selected_column(self):
            """Return the selected column name."""
            return self.column_combo.currentText()

    def retranslateUi(self, MaggyEditor):
        """Set the text for all UI elements."""
        MaggyEditor.setWindowTitle("Maggy Editor")
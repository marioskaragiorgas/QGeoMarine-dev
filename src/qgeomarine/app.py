"""
app.py
This is the entry point of the QGeoMarine GUI application. It allows users to create and open geophysical data projects,
manage seismic and magnetic datasets, view interactive maps, and process data.

Key Features:
- Create and open projects with metadata
- Import and edit seismic (.segy) and magnetic (.csv, .txt, .xls) data
- Load and display base maps and survey lines
- Manage files via a tree view and context menus
- Supports Towfish and Ship-based navigation
- Saves and reloads project state
- Provides a console log for debugging and output messages
- Uses PyQt6 for GUI components and QtWebEngine for map display
- Implements a recent projects list with JSON storage
- Provides a dialog for creating new projects with validation
- Redirects stdout and stderr to a QTextEdit widget for console output
- Handles project state saving and loading to maintain user progress
- Uses logging for debugging and error reporting
- Implements a custom dialog for creating new projects with folder structure management
"""

import sys
import os
import json
from collections import defaultdict
from PyQt6 import QtGui, QtCore, QtWidgets, QtWebEngineWidgets, QtWebEngineCore
from PyQt6.QtCore import pyqtSlot
import pyproj
import pyproj.database
from qgeomarine.ui.ui import Ui_IntroWindow
from qgeomarine.data_io.seismic_io import SEGY
from qgeomarine.data_io.magy_io import MAGGY
from qgeomarine.core.navigation.navigation import NavigationFromTowFish, NavigationFromShip, NavigationFromFile
from qgeomarine.ui.seismic_editor import SeismicEditor
from qgeomarine.ui.maggy_editor import MaggyEditor
from qgeomarine.core.maps.maps import MAPS

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)

class IntroWindow(QtWidgets.QMainWindow):   
    """
    Main application window shown on startup. Allows users to create or open marine geophysical projects.
    Maintains a recent project list using a local JSON file.Provides options to create new projects, open
    existing ones, and manage recent projects. Recent projects are displayed in a list with project name and path.
    The window also handles project creation through a dialog, validates inputs, and saves project metadata.
    Attributes:
        RECENT_PROJECTS_FILE (str): Path to the JSON file storing recent projects.
        recent_projects (list): In-memory list of recent projects.
        ui (Ui_IntroWindow): UI object containing the layout and widgets.
    Methods:
        show_error(title, message): Displays an error message box with the given title and message.
        setup_connections(): Connects UI buttons to their respective handlers.
        save_recent_projects(): Saves the recent projects list to the JSON file.
        create_new_project(): Displays dialog for creating a new project and initializes folder structure.
        open_existing_project(): Opens an existing project from a file dialog.
        open_recent_project(): Opens a recent project from the list widget.
        populate_recent_projects(): Populates the list widget with recent projects.
        load_recent_projects(): Loads recent projects from the JSON file.
    """
    
    RECENT_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects.json")
    def __init__(self):
        """
        Initialize the IntroWindow with UI setup and recent projects management.
        Loads recent projects from a JSON file and populates the UI list widget.
        Sets up connections for buttons and list widget interactions.
        """

        super().__init__()
        self.ui = Ui_IntroWindow()
        self.ui.setupUi(self)
        self.recent_projects = [] # In-memory list of recent projects
        self.setup_connections()
        self.load_recent_projects()

    def show_error(self, title, message):
        """Display an critical error message box with the given title and message."""
        QtWidgets.QMessageBox.critical(self, title, message)
    
    def setup_connections(self):
        """Connect UI buttons to their respective handlers."""
        self.ui.buttonnewproject.clicked.connect(self.create_new_project)
        self.ui.buttonopenproject.clicked.connect(self.open_existing_project)
        self.ui.buttonresources.clicked.connect(
        lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/marioskaragiorgas/ScodaKit#readme"))
        )
        self.ui.listWidget.itemDoubleClicked.connect(self.open_recent_project)

    def save_recent_projects(self):
        """Save the recent projects list to the JSON file."""
        try:
            with open(self.RECENT_PROJECTS_FILE, "w") as file:
                json.dump(self.recent_projects, file, indent=4)
            logging.info(f"Recent projects saved to {self.RECENT_PROJECTS_FILE}")
            logging.debug(f"Saved data: {self.recent_projects}")
        except IOError as e:
            self.show_error("Error", f"Failed to save recent projects: {e}")

    def create_new_project(self):
        """
        Display dialog for creating a new project.
        Initializes folder structure and launches the main application window.
        """
        dialog = NewProjectDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:  # Check if the dialog was accepted
            project_data = dialog.get_project_data()  # Retrieve project data from the dialog

            # Debug: Log the new project data
            logging.debug(f"New project data: {project_data}")

            # Check if the project is already in the list (avoid duplicates)
            if project_data and project_data not in self.recent_projects:
                self.recent_projects.append(project_data)  # Append new project to the list
                logging.debug(f"Updated recent projects: {self.recent_projects}")

                # Save updated list to the file
                self.save_recent_projects()

                # Update the UI with the new project
                self.populate_recent_projects()
            else:
                logging.info("Project already exists in recent projects or data is invalid.")

            # Proceed to the main window
            self.main_window = QGeoMarine(project_data)
            self.main_window.show()
            self.close()

    def open_existing_project(self):
        """
        Open an existing project from a file dialog.
        Loads the project data from the selected file and initializes the main application window. 
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Project", "", "Proj  Files (*.proj)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    project_data = json.load(f)
                self.main_window = QGeoMarine(project_data)
                self.main_window.show()
                self.close()
            except Exception as e:
                self.show_error("Error", f"Failed to load project file: {e}")
    
    def open_recent_project(self):
        """
        Open a recent project from the list widget.
        Retrieves the selected project path from the list widget and initializes the main application window.
        """
        selected_item = self.ui.listWidget.currentItem()
        if selected_item:
            project_path = selected_item.data(QtCore.Qt.ItemDataRole.UserRole)
            try:
                with open(project_path, 'r') as f:
                    project_data = json.load(f)
                self.main_window = QGeoMarine(project_data)
                self.main_window.show()
                self.close()
            except Exception as e:
                self.show_error("Error", f"Failed to load project file: {e}")

    def populate_recent_projects(self):
        """Populate the list widget with recent projects."""
        self.ui.listWidget.clear()
        for project in self.recent_projects:
            # Create a custom widget for each project
            project_widget = QtWidgets.QWidget()
            project_layout = QtWidgets.QVBoxLayout()
            project_widget.setLayout(project_layout)

            # Project Name (bold)
            project_name_label = QtWidgets.QLabel(project['project_name'])
            project_name_label.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Weight.Bold))
            project_layout.addWidget(project_name_label)

            # Project Path (regular)
            project_path_label = QtWidgets.QLabel(project['file_path'])
            project_path_label.setFont(QtGui.QFont("Segoe UI", 12))
            project_path_label.setStyleSheet("color: gray;")
            project_layout.addWidget(project_path_label)

            # Add custom widget to the list widget
            item = QtWidgets.QListWidgetItem(self.ui.listWidget)
            item.setSizeHint(project_widget.sizeHint())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, project['file_path'])  # Store full path for later use
            self.ui.listWidget.setItemWidget(item, project_widget)

    def load_recent_projects(self):
        """Load recent projects from the JSON file."""
        if os.path.exists(self.RECENT_PROJECTS_FILE):
            try:
                with open(self.RECENT_PROJECTS_FILE, "r") as file:
                    self.recent_projects = json.load(file)
            except (json.JSONDecodeError, IOError):
                self.recent_projects = []  # Reset to empty list if the file is corrupted
                logging.warning(f"Failed to read {self.RECENT_PROJECTS_FILE}. Initialized with an empty list.")
        else:
            self.recent_projects = []  # Initialize with an empty list
            # Create an empty JSON file if it doesn't exist
            self.save_recent_projects()

        self.populate_recent_projects()


class NewProjectDialog(QtWidgets.QDialog):
    """
    Dialog to create a new project. It prompts the user to enter project details.
    Creates folder structure and saves project metadata to a .proj file.
    """
    RECENT_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects.json")
    def __init__(self, parent=None):
        """ Initialize the dialog with UI components for project creation."""
        super().__init__(parent)  # Initialize the base QDialog class
        self.init_ui()  # Call the custom UI initialization function
        self.project_data = None  # Initialize an attribute to store project data

    def init_ui(self):
        """Set up the dialog UI components for creating a new project."""
        self.setWindowTitle("Create a New Project")
        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(QtWidgets.QLabel("Project Name:"))
        self.project_name_input = QtWidgets.QLineEdit()
        layout.addWidget(self.project_name_input)

        layout.addWidget(QtWidgets.QLabel("Project Folder:"))
        self.folder_path_input = QtWidgets.QLineEdit()
        folder_button = QtWidgets.QPushButton("Browse...")
        folder_button.clicked.connect(self.browse_folder)
        folder_layout = QtWidgets.QHBoxLayout()
        folder_layout.addWidget(self.folder_path_input)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)

        layout.addWidget(QtWidgets.QLabel("Project Geospatial Information"))
        layout.addWidget(QtWidgets.QLabel("Latitude:"))
        self.latitude_input = QtWidgets.QLineEdit()
        layout.addWidget(self.latitude_input)

        layout.addWidget(QtWidgets.QLabel("Longitude:"))
        self.longitude_input = QtWidgets.QLineEdit()
        layout.addWidget(self.longitude_input)

        layout.addWidget(QtWidgets.QLabel("Project Coordinate Reference System (CRS):"))

        # Create a button to select the coordinate system
        crs_button = QtWidgets.QPushButton("Select Coordinate Reference System")
        layout.addWidget(crs_button)
        crs_button.clicked.connect(self.show_crs_dialog)

        # Create the coordinate system selection dialog box
        self.crs_selection_dialog = QtWidgets.QDialog(self)
        self.crs_selection_dialog.setWindowTitle("Coordinate Reference System (CRS) Selection")

        # Set the layout for the CRS selection dialog
        crs_layout = QtWidgets.QVBoxLayout(self.crs_selection_dialog)

        crs_layout.addWidget(QtWidgets.QLabel("Coordinate Reference System (CRS)"))
        
        # Create the CRS tree widget
        self.crs_tree = QtWidgets.QTreeWidget()
        self.crs_tree.setHeaderLabels(["CRS Category", "EPSG Code", "Name"])

        # Populate the tree with CRS categories and entries
        crs_categories = self.query_pyproj_crs()

        for category, entries in crs_categories.items():
            cat_item = QtWidgets.QTreeWidgetItem([category]) 

            for code, name in entries:
                child = QtWidgets.QTreeWidgetItem(["", code, name])
                cat_item.addChild(child)

            self.crs_tree.addTopLevelItem(cat_item)

        crs_layout.addWidget(self.crs_tree)

        # OK and Cancel buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        crs_layout.addWidget(button_box)
        button_box.accepted.connect(self.handle_crs_selection)
        button_box.rejected.connect(self.crs_selection_dialog.reject)
        
        layout.addWidget(QtWidgets.QLabel("EPSG CODE:"))
        self.ESPG_input = QtWidgets.QLineEdit()
        layout.addWidget(self.ESPG_input)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def show_crs_dialog(self):
        self.crs_selection_dialog.exec()
    
    def query_pyproj_crs(self):
        """
        Queries all available CRS entries in the pyproj database,
        groups CRS by coordinate system category (e.g., Geographic, Projected),
        and returns a dictionary where keys are category names and values are lists
        of (EPSG code, name) tuples.

        Returns:
            dict: {category: [(EPSG_code, CRS_name), ...]}
        Raises:
            Exception: If querying the CRS database fails.
        """
        try:
            all_crs = pyproj.database.query_crs_info(auth_name="EPSG")
            crs_by_category = defaultdict(list)

            for crs in all_crs:
                category = str(crs.type).split(".")[-1].capitalize()  # e.g., 'Geographic'
                label = crs.name
                code = f"EPSG:{crs.code}"
                crs_by_category[category].append((code, label))

            # Optional: Limit to top 50 per category for UI performance
            #for k in crs_by_category:
                #crs_by_category[k] = sorted(crs_by_category[k], key=lambda x: x[1])[:50]

            return dict(crs_by_category)

        except Exception as e:
            logging.error(f"Error querying CRS: {e}")
            return {}

    def browse_folder(self):
        """Open a file dialog to select a folder for the project."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_path_input.setText(folder)

    def handle_crs_selection(self):
        """
        Handle the selection of a CRS from the tree widget.
        Updates the EPSG input field with the selected CRS code and save the selected CRS as a project attribute.
        """
        selected_items = self.crs_tree.selectedItems()
 
        if selected_items:
            # Get the first selected item (the CRS entry)
            selected_item = selected_items[0]

            if selected_item.childCount() > 0:
                # If it's a category, get the first child
                selected_item = selected_item.child(0)

            # Get the EPSG code and name from the selected item
            epsg_code = selected_item.text(1).strip() 
 
            epsg_code = epsg_code.split(":")[-1]  # keep only the EPSG code numeric part (e.g., "EPSG:4326" -> "4326")
            epsg_name = selected_item.text(2) # Get the CRS name 
            
            # Debud: print the CRS name
            print(f"CRS name:{epsg_name}")
            
            self.ESPG_input.setText(epsg_code)  # Set the EPSG code in the input field
            self.crs_selection_dialog.accept()
            return str(epsg_name)

        else:
            QtWidgets.QMessageBox.warning(self, "Selection Error", "Please select a CRS from the list.")
            return None
        
    def accept(self):
        """Validate inputs and create the project folder structure."""
        if not self.project_name_input.text() or not self.folder_path_input.text():
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please fill out all fields.")
            return

        try:
            int(self.ESPG_input.text())  # Validate EPSG code as numeric
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Invalid EPSG code. Please enter a numeric EPSG code.")
            return

        # Generate the project folder path
        project_folder = os.path.join(self.folder_path_input.text(), self.project_name_input.text())
        
        # Create the folder structure if it doesn't exist
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
            for subfolder in ['Project', 'seismic', 'sonar', 'magnetics', 'maps', 'Navigation']:
                os.makedirs(os.path.join(project_folder, subfolder))
        else:
            QtWidgets.QMessageBox.warning(self, "Project Exists", "A project with this name already exists.")
            return
        
        # Define the project file path
        project_file = os.path.join(project_folder, 'Project', f"{self.project_name_input.text()}.qgm")

        
        # Create the project data dictionary
        self.project_data = {
            'project_name': self.project_name_input.text(),
            'folder_path': project_folder,
            'file_path': project_file,
            'latitude': self.latitude_input.text(),
            'longitude': self.longitude_input.text(),
            'coordinater eference system CRS': self.handle_crs_selection(),  # Get the selected CRS from the dialog
            'EPSG CODE': self.ESPG_input.text()
        }
        
        # Save the project file in the project folder
        with open(project_file, 'w') as f:
            json.dump(self.project_data, f, indent=4)

        # Close the dialog and signal acceptance
        super().accept()
    
    def get_project_data(self):
        """
        Return the project metadata collected in the dialog.

        Returns:
            dict: Dictionary containing project name, folder path, coordinates, EPSG code, and file path.
        """
        return self.project_data

class StreamRedirector:
    """
    Utility class to redirect stdout and stderr to a QTextEdit widget.
    Used to display logs in a docked log viewer.
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        """Write text to the QTextEdit widget."""
        self.text_widget.insertPlainText(text)
        self.text_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def flush(self):
        """Override the flush method to do nothing."""
        pass

class QGeoMarine(QtWidgets.QMainWindow):
    """
    Main window for project operation.
    Provides GUI to import, edit, and visualize seismic and magnetic data.
    Displays maps using QtWebEngine and Leaflet.js-generated HTML maps.
    Handles saving/loading project states.
    
    Attributes:

        project_data (dict): Dictionary containing project metadata such as name, folder path, and EPSG code.
        projectstate_file (str): Path to the JSON file storing the project state.
        segy_handler (SEISMIC.SEGYHandler): Handler for seismic data operations.
        mag_handler (MAGGY.CSV_TXT_XLS): Handler for magnetic data operations.
        map_handler (MAPS): Handler for map operations.
        sbp_coords (list): List of coordinates for side scan sonar data.
        data (dict): Dictionary to store seismic and magnetic data.
        segy_file (str): Path to the currently loaded SEG-Y file.
        segy_files (dict): Dictionary to store multiple SEG-Y files.
        seismic_db_files (dict): Dictionary to store seismic database files.
        active_seismic_lines (dict): Dictionary to store active seismic lines.
        mag_db (object): Magnetic database object.
        mag_files (dict): Dictionary to store magnetic files.
        active_mag_lines (dict): Dictionary to store active magnetic lines.
        map (object): Map object for displaying survey lines and layers.
        map_html (str): Path to the HTML file containing the map.
        dock_widget (QDockWidget): Dock widget for file data manager.
        treeview (QTreeWidget): Tree view for displaying opened files.
        consolelog_dock_widget (QDockWidget): Dock widget for console log output.
        logText (QTextEdit): Text edit widget for displaying console output.
        web_view (QWebEngineView): Web view for displaying maps.
        statusbar (QStatusBar): Status bar for displaying messages.
        toolbar (QToolBar): Toolbar for quick access to actions.
   
    Methods:
        init_ui(): Initializes the main window UI components.
        create_menus(): Creates the application menus for file management and editing.
        create_toolbar(): Creates the toolbar with quick access actions.
        closeEvent(event): Override close event to save project state and reset stdout/stderr.
        save_project_state(): Saves the current project state to a JSON file.
        load_project_state(): Loads the saved project state from a JSON file.
        show_error(title, message): Displays an error message box with the given title and message.
        show_warning(title, message): Displays a warning message box with the given title and message.
        import_seismic_data(): Imports seismic data from SEG-Y files.
        import_mag_data(): Imports magnetic data from CSV, TXT, or XLS files.
        import_raster(): Imports raster layers for maps.
        import_vector(): Imports vector layers for maps.
        import_tiles(): Imports tile/XYZ layers for maps.
    """
    
    def closeEvent(self, event):
        """ Override close event to save project state and reset stdout/stderr."""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)

    def __init__(self, project_data):
        """ Initialize the main application window with project data."""
        super().__init__()
        self.project_data = project_data
        
        self.projectstate_file = os.path.join(self.project_data.get('folder_path'), 'Project', f"{self.project_data.get('project_name')}.project_state.json")  # File to store project state
        # Try loading previous session
        self.load_project_state()
        
        # Initialize handlers
        self.segy_handler = SEGY(db_file_path=None, bin_file_path=None)
        self.mag_handler = MAGGY.CSV_TXT_XLS(mag_db_file_path=None, Line_column_name=None)
        self.map_handler = MAPS()
        
        # Seismic & magnetic data structures
        self.sbp_coords = None
        self.data = None
        self.segy_file = None
        self.segy_files = {}
        self.seismic_db_files = {}
        self.active_seismic_lines = {}
        self.mag_db = None
        self.mag_files = {}
        self.active_mag_lines = {}
        
        self.map = None
        self.map_html = None
        
        # UI Initialization
        self.init_ui()
        self.create_menus()
        self.create_toolbar()
        self.load_basemap()
        
        # Context menu for treeview
        self.treeview.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeview.customContextMenuRequested.connect(self.show_treeview_context_menu)

    def init_ui(self):
        self.setWindowTitle(f"QGeoMarine - {self.project_data.get('project_name', 'Project')}")
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.setGeometry(100, 100, 1200, 800)
        light_StyleSheet = (""" 
                            Background-color: #f0f0f0; 
                            color: #333;
                            font-family: 'Segoe UI';
                            border-radius: 5px;
                            border: 1px solid #ccc;
                            hover { 
                                background-color: #0078d4;
                                color: #fff;
                            }
                            selection-background-color: #0078d4;
                            selection-color: #fff;
                            QTreeWidget::item:selected {
                                background-color: #0078d4;
                                color: #fff;
                            }
                            QTreeWidget::item:hover {
                                background-color: #0078d4;
                                color: #fff;
                            }
                            QMenubar {
                                background-color: #0078d4;
                                color: #fff;
                            }
                           """)             
        
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self.central_widget)

        self.dock_widget = QtWidgets.QDockWidget()
        self.dock_widget.setWindowTitle('File Data Manager')
        self.dock_widget.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.dock_widget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        # Create a QTreeWidget for the file manager
        self.treeview = QtWidgets.QTreeWidget()
        self.treeview.setHeaderLabel("Opened Files")
        
        self.treeview_root_seismic = QtWidgets.QTreeWidgetItem(self.treeview, ["Seismic Files"]) 
        # show filenames in the treeview_root_seismic in the Seismic Files Folder which endwith .db
        # Get seismic files ending with .db
        seismic_files_path = os.path.join(self.project_data.get('folder_path'), 'seismic')
        
        # Add each .db file as a child of the "Seismic Files" root
        for file in os.scandir(seismic_files_path):
            if file.is_file() and file.name.endswith('.db'):
                file_item = QtWidgets.QTreeWidgetItem(self.treeview_root_seismic, [os.path.basename(file.path)])
                file_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, file.path)
    
        self.treeview_root_seismic.setExpanded(True)
        
        self.treeview_root_mag = QtWidgets.QTreeWidgetItem(self.treeview, ["Magnetic Files"])
        # show filenames in the treeview_root_mag in the magnetic Files Folder which endwith .db
        # Get magnetic files ending with .db
        mag_files_path = os.path.join(self.project_data.get('folder_path'), 'magnetics')
        
        # Add each .db file as a child of the "Magnetic Files" root
        for file in os.scandir(mag_files_path):
            if file.is_file() and file.name.endswith('.db'):
                file_item = QtWidgets.QTreeWidgetItem(self.treeview_root_mag, [os.path.basename(file.path)])
                file_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, file.path)
        
        self.treeview_root_mag.setExpanded(True)
        self.treeview_root_sss =QtWidgets.QTreeWidgetItem(self.treeview, ["Side Scan Sonar Files"])
        self.treeview_root_sss.setExpanded(True)
        self.treeview_root_maps = QtWidgets.QTreeWidgetItem(self.treeview, ["Maps"])
        self.treeview_root_maps.setExpanded(True)
        self.treeview_root_lines = QtWidgets.QTreeWidgetItem(self.treeview, ["Survey Lines"])
        self.treeview_root_lines.setExpanded(True)

        self.dock_widget.setWidget(self.treeview)
       
        splitter.addWidget(self.dock_widget)

        # Make a console log/ output dock widget
        self.consolelog_dock_widget = QtWidgets.QDockWidget()
        self.consolelog_dock_widget.setWindowTitle('Console Log')
        self.consolelog_dock_widget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        # Create a QTextEdit widget for the console log
        self.logText = QtWidgets.QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        sys.stdout = StreamRedirector(self.logText)
        sys.stderr = StreamRedirector(self.logText)

        self.consolelog_dock_widget.setWidget(self.logText)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.consolelog_dock_widget) # Add the dock widget to the main window

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.showMessage("Ready, No Data Loaded")
        #self.data_info_label = statusbar.showMessage(message)
        #right_layout.addWidget(self.data_info_label)

        self.web_view = QtWebEngineWidgets.QWebEngineView()
        right_layout.addWidget(self.web_view)

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 750])

        layout = QtWidgets.QHBoxLayout(self.central_widget)
        layout.addWidget(splitter)

    def create_menus(self):
        """Create the application menus for file management and editing."""
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu("File Manager")
        
        seismic_file_submenu = file_menu.addMenu("Seismic Files...")
        seismic_file_submenu.addAction(self.create_action("Import Data", self.import_seismic_data))
        seismic_file_submenu.addAction(self.create_action("Export Data", self.save_processed_segy))
        seismic_file_submenu.addAction(self.create_action("Close all", self.close_segy))
        

        mag_file_submenu = file_menu.addMenu("Magnetic Files...")
        mag_file_submenu.addAction(self.create_action("Import Data", self.import_mag_data))
        mag_file_submenu.addAction(self.create_action("Export Data", self.save_processed_mag))
        #mag_file_submenu.addAction(self.create_action("Close all", self.close_segy))
        

        seismic_edit_menu = self.menu_bar.addMenu("Seismic Editor")
        seismic_edit_menu.addAction(self.create_action("Open segy file in seismic editor...", self.seismic_editor))

        maggy_edit_menu = self.menu_bar.addMenu("Magnetic Editor")
        maggy_edit_menu.addAction(self.create_action("Open maggy file in magnetic editor...", self.maggy_editor))

        viewMenu = self.menu_bar.addMenu("View")
        viewStatAct = QtGui.QAction("View statusbar", self, checkable=True)
        viewStatAct.setStatusTip("View statusbar")
        viewStatAct.setChecked(True)
        viewStatAct.triggered.connect(self.toggleMenu)
        viewMenu.addAction(viewStatAct)

        mapsMenu = self.menu_bar.addMenu("Maps")
        mapsMenu.addAction(self.create_action("Add Raster Layer", self.import_raster))
        mapsMenu.addAction(self.create_action("Add Vector Layer", self.import_vector))
        mapsMenu.addAction(self.create_action("Add Tiles/XYZ layer", self.import_tiles))
    

    def toggleMenu(self, state):
        if state:
            self.statusBar.show()
        else:
            self.statusBar.hide()

    def create_action(self, name, method):
        action = QtGui.QAction(name, self)
        action.triggered.connect(method)
        return action

    def create_toolbar(self):
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        self.toolbar.setFixedHeight(36)
        open_file_icon_path = os.path.join(os.path.dirname(__file__), "Images/mIconFolderOpen.png")
        open_file_icon = QtGui.QIcon(open_file_icon_path)
        import_file_action = QtGui.QAction(open_file_icon, "Import file", self)
        import_file_action.triggered.connect(self.import_seismic_data)
        self.toolbar.addAction(import_file_action)
        self.addToolBar(self.toolbar)

    def closeEvent(self, event):
        self.save_project_state()
        event.accept()

    def save_project_state(self):
        """Save the project state to a JSON file."""
        try:
            # Make sure to exclude non-serializable objects like segyio files
            state = {
                "seismic_db_files": self.seismic_db_files,
                "active_seismic_lines": self.active_seismic_lines,
                "mag_files": self.mag_files,
                "active_mag_lines": self.active_mag_lines,
                "map_html": self.map_html,
                "sbp_coords": self.sbp_coords
            }

            with open(self.projectstate_file, "w") as file:
                json.dump(state, file)


            print("Project state saved successfully.")
        except Exception as e:
            print(f"Error saving project state: {e}")

    def load_project_state(self):
        """Load the saved project state from a JSON file."""
        if os.path.exists(self.projectstate_file):
            try:
                with open(self.projectstate_file, "r") as file:
                    saved_state = json.load(file)
                    self.seismic_db_files = saved_state.get("seismic_db_files", {})
                    self.active_seismic_lines = saved_state.get("active_seismic_lines", {})
                    self.mag_files = saved_state.get("mag_files", {})
                    self.active_mag_lines = saved_state.get("active_mag_lines", {})
                    self.map_html = saved_state.get("map_html", None)
                    self.sbp_coords = saved_state.get("sbp_coords", None)

                print("Project state loaded successfully.")
            except Exception as e:
                print(f"Error loading project state: {e}")

    def show_error(self, title, message):
        """Display a critical error message box with the given title and message."""
        QtWidgets.QMessageBox.critical(self, title, message)

    def show_warning(self, title, message):
        """Display a warning message box with the given title and message."""
        QtWidgets.QMessageBox.warning(self, title, message)

    def save_project_data(self):
        """Save the project data to the project file."""
        try:
            with open(self.project_data['project_file'], 'w') as f:
                json.dump(self.project_data, f, indent=4)
            logging.info(f"Project data saved to {self.project_data['project_file']}")
        except Exception as e:
            self.show_error("Error", f"Failed to save project data: {e}")

    
    def create_basemap(self):
        """Create a default basemap using the map handler and save it to the project folder."""
        try:

            # Create the default map
            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")
            self.map, self.map_html = self.map_handler.default_tile_map(output_dir)

            # Debug: Print file path
            print(f"Map HTML saved at: {self.map_html}")

            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Basemap saved and loaded at: {self.map_html}")
        except Exception as e:
            self.show_error("Error", f"Failed to create basemap: {e}")
    
    def load_basemap(self):
        """Load the basemap from the saved HTML file if exists in the maps subfolder of the project folder."""
        try:
            # Check if the basemap HTML file exists
            if os.path.exists(os.path.join(self.project_data.get('folder_path'), "maps", "default_map.html")):
                self.map_html = os.path.join(self.project_data.get('folder_path'), "maps", "default_map.html")
                
                # Enable QWebEngineView JavaScript and local file access
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

                # Load the map in the QWebEngineView
                self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
                print(f"Basemap loaded from: {self.map_html}")
            else:
                logging.warning("Basemap HTML file not found. Attempting to create a new basemap.")
                self.show_warning("Basemap not found", "Basemap HTML file not found. Attempting to create a new basemap.")
                self.create_basemap()
        except Exception as e:
            self.show_error("Error", f"Failed to load basemap: {e}")
    
    @pyqtSlot()
    def import_seismic_data(self):
        """ 
        Import seismic data from SEG-Y files.
        The user can select navigation source from Towfish or Ship
        and choose to load multiple SEG-Y files.
        """
        # Open file dialog to select SEG-Y files
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Open SEG-Y Files", "", "SEG-Y Files (*.sgy *.segy)")
        if not file_paths:
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Navigation Options")
        layout = QtWidgets.QVBoxLayout()
        self.checkbox_towfish = QtWidgets.QCheckBox("Select Navigation from Towfish")
        self.checkbox_ship = QtWidgets.QCheckBox("Select Navigation from Ship")
        layout.addWidget(self.checkbox_towfish)
        layout.addWidget(self.checkbox_ship)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                for file_path in file_paths:
                    self.load_segy_file(file_path)
            except Exception as e:
                self.statusbar.showMessage(f"Error loading data: {e}")
                logging.error(f"Failed to load SEG-Y file: {e}")
                self.show_error("Error", f"Failed to load SEG-Y file: {e}")
    
    @pyqtSlot()
    def import_mag_data(self):
        """
        Import magnetic data from CSV, TXT, or XLS files.
        The user can select the line column and navigation source.
        The user can select multiple files to import.
        """
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Import MAG Data", "", "CSV Files (*.csv);;Excel Files (*.xls *.xlsx);;Text Files (*.txt);;AscII Files (*.asc *ascii *asc2);;All Files (*)")
        if not file_paths:
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Magnetic File Options")
        layout = QtWidgets.QVBoxLayout()

        # Preview the data to select the line column
        try:
            for file_path in file_paths:
                mag_df = self.preview_mag_file(file_path)
        except Exception as e:
            self.statusbar.showMessage(f"Error loading data: {e}")
            logging.error(f"Failed to load MAG file: {e}")
            self.show_error("Error", f"Failed to load MAG file: {e}")
        
        # Create a table to preview the data
        self.table = QtWidgets.QTableWidget()
        self.table.setRowCount(mag_df.shape[0])
        self.table.setColumnCount(mag_df.shape[1])
        self.table.setHorizontalHeaderLabels(mag_df.columns)
        for row in range(mag_df.shape[0]):
            for col in range(mag_df.shape[1]):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(mag_df.iat[row, col]))) 
        layout.addWidget(self.table)

        # Add a combo box to select the line column, and the X and Y coordinates
        layout.addWidget(QtWidgets.QLabel("Select Line name Column:"))
        self.line_combo_box = QtWidgets.QComboBox()
        self.line_combo_box.addItems(mag_df.columns)
        layout.addWidget(self.line_combo_box)

        layout.addWidget(QtWidgets.QLabel("Select Lattitude Column:"))
        self.lat_combo_box = QtWidgets.QComboBox()
        self.lat_combo_box.addItems(mag_df.columns)
        layout.addWidget(self.lat_combo_box)

        layout.addWidget(QtWidgets.QLabel("Select Longitude Column:"))
        self.lon_combo_box = QtWidgets.QComboBox()
        self.lon_combo_box.addItems(mag_df.columns)
        layout.addWidget(self.lon_combo_box)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            line_col_name = self.line_combo_box.currentText()
            lat_col_name = self.lat_combo_box.currentText()
            lon_col_name = self.lon_combo_box.currentText()

            logging.info(f"Selected Line Column: {line_col_name}")
            logging.info(f"Selected Lattitude Column: {lat_col_name}")
            logging.info(f"Selected Longitude Column: {lon_col_name}")

            try:
                for file_path in file_paths:
                    self.load_mag_file(file_path, line_col_name, lon_col_name, lat_col_name)
            except Exception as e:
                self.statusbar.showMessage(f"Error loading data: {e}")
                logging.error(f"Failed to load MAG file: {e}")
                self.show_error("Error", f"Failed to load MAG file: {e}")

    def preview_mag_file(self, file_path):
        """
        Preview the magnetic data file to allow the user to select the line column.
        This function reads the file and returns a DataFrame for previewing.
        """
        
        # Check if the file exists
        try:

            mag_df = self.mag_handler.preview_data(file_path)
            return mag_df
        except Exception as e:
            self.statusbar.showMessage(f"Error loading data: {e}")
            logging.error(f"Failed to load MAG file: {e}")
            self.show_error("Error", f"Failed to load MAG file: {e}")
            
    @pyqtSlot()
    def import_raster(self):
        """ 
        Import raster layers for maps.
        The user can select multiple raster files to import.    
        """
        # Open file dialog to select raster files
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Import Maps", "", "Raster Files (*.geotiff *.tiff *.tif *.jpg *.png)")
        
        if not file_paths:
            return
        
        try:
            for file_path in file_paths:
                self.load_raster(file_path)
        except Exception as e:
                self.statusbar.showMessage(f"Error loading data: {e}")
                logging.error(f"Failed to Raster file: {e}")
                self.show_error("Error", f"Failed to load Raster file: {e}")

    @pyqtSlot()
    def import_vector(self):
        """
        Import vector layers for maps.
        The user can select multiple vector files to import.
        """
        # Open file dialog to select vector files
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Import Vector data", "", "Vector Files (*.shp *.geojson)")
        
        if not file_paths:
            return
        
        try:
            for file_path in file_paths:
                self.load_vector(file_path)
        except Exception as e:
                self.statusbar.showMessage(f"Error loading data: {e}")
                logging.error(f"Failed to Vector file: {e}")
                self.show_error("Error", f"Failed to load Vector file: {e}")
    
    @pyqtSlot()
    def import_tiles(self):
        """
        Import tile layers for maps.
        The user can add a tile layer by providing a URL in XYZ format and a layer name
        """
        # Open a dialog to get the tile layer URL and layer name
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add Tile Layer")

        layout = QtWidgets.QVBoxLayout(dialog)

        # XYZ URL input
        layout.addWidget(QtWidgets.QLabel("Tile Layer URL (XYZ format):"))
        tile_url_input = QtWidgets.QLineEdit()
        layout.addWidget(tile_url_input)

        # Layer Name input
        layout.addWidget(QtWidgets.QLabel("Layer Name:"))
        layer_name_input = QtWidgets.QLineEdit()
        layout.addWidget(layer_name_input)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            tile_url = tile_url_input.text()
            layer_name = layer_name_input.text()

            if tile_url and layer_name:
                # Define paths for map assets
                output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
                print(f"output dir: {output_dir}")
            
                self.map, self.map_html = self.map_handler.add_tile_layer(tile_url, output_dir)
                # Debug: Print file path
                print(f"Map HTML saved at: {self.map_html}")

                # Enable QWebEngineView JavaScript and local file access
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

                # Load the map in the QWebEngineView
                self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
                print(f"Map saved and loaded at: {self.map_html}")
            else:
                QtWidgets.QMessageBox.warning(self, "Input Error", "Please provide a valid URL and layer name.")



    def load_segy_file(self, file_path):
        """
        Load a SEG-Y file using segyio and store its metadata in a database.
        The SEG-Y file is processed and stored in a binary file.
        The user can select navigation source from Towfish or Ship.
        """
        
        db_filepath = os.path.join(self.project_data.get('folder_path'), 'seismic', os.path.basename(file_path)[:-4] + '.db')
        bin_filepath = os.path.join(self.project_data.get('folder_path'), 'seismic', os.path.basename(file_path)[:-4] + '.bin')
        print(f"seismic binary file path is:{bin_filepath}")
        
        if os.path.exists(db_filepath):
            os.remove(db_filepath)  # Deletes the existing database file
        
        try:
            self.segy_handler = SEGY(db_file_path=db_filepath, bin_file_path=bin_filepath)
            segy_file, spec, n_samples, twt, data_format, sample_interval, sample_rate = self.segy_handler.load_data_segyio(file_path)

            self.segy_files[file_path] = {
                'segy_file': segy_file,
                'spec': spec,
                #'data': data,
                'n_samples': n_samples,
                'twt': twt,
                'data_format': data_format,
                'sample_interval': sample_interval,
                'sample_rate': sample_rate
            }

            self.seismic_db_files[db_filepath] = {
                'segy_file': segy_file,
                'db_filepath': db_filepath,
                'spec': spec,
                #'data': data,
                'n_samples': n_samples,
                'twt': twt,
                'data_format': data_format,
                'sample_interval': sample_interval,
                'sample_rate': sample_rate
            }
            #print(self.seismic_db_files)
            self.statusbar.showMessage(f"Loaded data from {file_path} with Segyio")
            QtWidgets.QMessageBox.information(self, "Data Loaded", f"Loaded seismic metadata from {file_path} with Segyio and stored to {db_filepath} database. Seismic data stored in {bin_filepath} binary file.")
            self.update_treeview(file_path, db_filepath, n_samples, filetype='seismic')

            if self.checkbox_towfish.isChecked():
                self.load_towfish_navigation(file_path)
            elif self.checkbox_ship.isChecked():
                self.load_ship_navigation(file_path)

        except Exception as e:
            self.statusbar.showMessage(f"Error loading file {file_path}: {e}")
            logging.error(f"Failed to load SEG-Y file {file_path}: {e}")
            self.show_error('Error', f"Failed to load SEG-Y file {file_path}: {e}")


    def load_mag_file(self, file_path, line_col_name, lon_col_name, lat_col_name):
        """
        Load a magnetic data file using MAGGY and store its metadata in a database.
        The magnetic data is processed and stored in a database file.
        """

        mag_db_filepath = os.path.join(self.project_data.get('folder_path'), 'magnetics', os.path.basename(file_path)[:-4] + '.db')
        if os.path.exists(mag_db_filepath):
            os.remove(mag_db_filepath)
        try:
            self.mag_handler = MAGGY.CSV_TXT_XLS(mag_db_file_path=mag_db_filepath, Line_column_name=line_col_name)
            self.mag_db = self.mag_handler.load_files(file_path)

            self.mag_files[file_path] = {
                'mag_db_filepath': mag_db_filepath
                }
            
            self.statusbar.showMessage(f"Loaded magnetic data from {file_path}, and stored to {mag_db_filepath} database.")
            QtWidgets.QMessageBox.information(self, "Data Loaded", f"Loaded magnetic data from {file_path} and stored to {mag_db_filepath} database.")
            #self.update_treeview(file_path, filetype='mag')

            navigation = NavigationFromFile()
            espg = str(self.project_data.get('EPSG CODE'))
            
            # Load and transform coordinates
            mag_coords = navigation.load_navigation_data(
                file_path=file_path,
                line_col=line_col_name,
                x_col=lon_col_name,
                y_col=lat_col_name,
                input_epsg=espg
            )

            print(mag_coords)
            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")

            # Update the map
            self.map, self.map_html = self.map_handler.load_mag_lines(coordinates=mag_coords, dir=output_dir)
                
            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Map saved and loaded at: {self.map_html}")
                                
        except Exception as e:
            self.statusbar.showMessage(f"Error loading file {file_path}: {e}")
            logging.error(f"Failed to load MAG file {file_path}: {e}")

    def load_raster(self, file_path):
        """
        Load a raster file for maps using the map handler.
        The raster data is processed and stored in a map HTML file.
        The user can select multiple raster files to import.
        """

        try:
            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")
            
            self.map, self.map_html = self.map_handler.load_raster_data(file_path, output_dir)
            # Debug: Print file path
            print(f"Map HTML saved at: {self.map_html}")

            self.statusbar.showMessage(f"Loaded data from {file_path}")
            self.update_treeview(file_path=file_path, db_filepath=file_path, n_samples=None, filetype='map')
            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Map saved and loaded at: {self.map_html}")
        
        except Exception as e:
            self.statusbar.showMessage(f"Error loading file {file_path}: {e}")
            logging.error(f"Failed to load Raster file {file_path}: {e}")

    def load_vector(self, file_path):
        """
        Load a vector file for maps using the map handler.
        The vector data is processed and stored in a map HTML file.
        The user can select multiple vector files to import.
        """

        try:
            
            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")
            self.map, self.map_html = self.map_handler.load_vector_data(file_path, output_dir)
            self.statusbar.showMessage(f"Loaded data from {file_path}")
            self.update_treeview(file_path=file_path, db_filepath=file_path, n_samples=None, filetype='vector')

            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Map saved and loaded at: {self.map_html}")
        
        except Exception as e:
            self.statusbar.showMessage(f"Error loading file {file_path}: {e}")
            logging.error(f"Failed to load Raster file {file_path}: {e}")

    def update_treeview(self, file_path, db_filepath, n_samples, filetype):
        """
        Update the treeview with the loaded file information.
        The file information is displayed in the appropriate root item based on the file type.
        """

        # SEGY files
        if filetype == 'seismic':
            file_item = QtWidgets.QTreeWidgetItem(self.treeview_root_seismic)
            file_item.setText(0, os.path.basename(db_filepath))

            n_traces = self.segy_files[file_path]['segy_file'].tracecount
            trace_item = QtWidgets.QTreeWidgetItem(file_item)
            trace_item.setText(0, f"Number of Traces: {n_traces}")
            sample_item = QtWidgets.QTreeWidgetItem(file_item)
            sample_item.setText(0, f"Samples: {n_samples}")
            sample_interval_item = QtWidgets.QTreeWidgetItem(file_item)
            sample_interval_item.setText(0, f"Sample Interval: {self.segy_files[file_path]['sample_interval'] * 1e3} ms")
            file_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, db_filepath)
        
        # Mag files (Magnetic)
        elif filetype == 'mag':
            file_item = QtWidgets.QTreeWidgetItem(self.treeview_root_mag)
            file_item.setText(0, os.path.basename(db_filepath))
            file_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, db_filepath)

        # Map files 
        else :
            file_item = QtWidgets.QTreeWidgetItem(self.treeview_root_maps)
            file_item.setText(0, os.path.basename(file_path))
            file_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, file_path)

    def show_treeview_context_menu(self, position):
        item = self.treeview.itemAt(position)
        if item is None or item.parent() is None:
            return

        def create_and_show_menu(root_item, context_type):
            context_menu = QtWidgets.QMenu(root_item)
            open_action = self.create_action(f"Open file in {context_type} Editor...", lambda: self.on_file_selected(item))
            close_action = self.create_action("Close file", lambda: self.close_file(item))
            context_menu.addAction(open_action)
            context_menu.addAction(close_action)
            context_menu.exec(self.treeview.viewport().mapToGlobal(position))

        if item.parent() == self.treeview_root_seismic:
            create_and_show_menu(self.treeview, "Seismic")
        elif item.parent() == self.treeview_root_mag:
            create_and_show_menu(self.treeview, "Magnetic")
        elif item.parent() == self.treeview_root_maps:
            create_and_show_menu(self.treeview, "Map")

    def on_file_selected(self, item):
        """
        Open the selected file in the appropriate editor.
        """
        item = self.treeview.currentItem() # Get the selected item
        if item.parent() == self.treeview_root_seismic:
            file_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if file_path:
                self.seis_edit = SeismicEditor(seismic_filepath=None, db_file_path=file_path)
                self.seis_edit.show()
            else:
                QtWidgets.QMessageBox.warning(self, "File Error", "No valid file selected.")
        
        elif item.parent() == self.treeview_root_mag:
            file_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if file_path:
                self.mag_edit = MaggyEditor(maggy_file_path=None, db_file_path=file_path, project_data =self.project_data)
                self.mag_edit.show()

    def close_file(self, item):
        """
        Close the selected file and remove it from the treeview.
        """

        file_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if file_path:
            segyfile = self.segy_files[file_path]['segy_file']
            self.segy_handler.close_file()
            segyfile.data = None
            file_id = os.path.basename(file_path)
            self.remove_seismic_line(file_id)

    def load_towfish_navigation(self, segy_file_path):
        """
        Load Towfish navigation data from a SEG-Y file.
        The navigation data is extracted and transformed to latitude and longitude coordinates.
        The user can select a SEG-Y file to load the navigation data.
        """

        try:
            file_id = os.path.basename(segy_file_path)
            print(file_id)
            nav_towfish = NavigationFromTowFish()
            self.sbp_coords = nav_towfish.load_Nav_data_from_segyfile(segy_file_path)

            # Retrieve the EPSG code from project data and create a transformer if necessary
            epsg_code = str(self.project_data.get("EPSG CODE"))

            if epsg_code != "4326":
                transformer = pyproj.Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)

                # Transform each (x, y) coordinate
                lat_lon_coords = [transformer.transform(x, y) for x, y in self.sbp_coords] # Transform each (x, y) coordinate
                print("Transformed Coordinates for Plotting:", lat_lon_coords)
            else:
                lat_lon_coords = self.sbp_coords # No transformation needed

            filtered_coords = [(lat, lon) for lat, lon in lat_lon_coords if lat != 0 and lon != 0]

            print("Transformed Filtered Coordinates for Plotting:", filtered_coords)
            self.add_seismic_line(file_id, filtered_coords)
        except Exception as e:
            self.show_error("Error", f"Failed to load Towfish navigation: {e}")

    def load_ship_navigation(self, segy_file_path):
        """
        Load Ship navigation data from a CSV, TXT, or Excel file.
        The navigation data is extracted and transformed to latitude and longitude coordinates.
        The user can select a navigation file to load the navigation data.
        """

        try:
            file_id = os.path.basename(segy_file_path)
            nav_ship = NavigationFromShip()
            nav_filepath,_ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Navigation File", "", "CSV Files (*.csv);;Text Files (*.txt);;Excel Files (*.xlsx);;NaV Files(*.Nav);;P190 Files(*.P190)")
            nav_df = nav_ship.load_navigation_data(nav_filepath)
            X_sbp, Y_sbp = nav_ship.ship_to_sbp_nav(navigation_df=nav_df, segyfile=segy_file_path)
            self.add_seismic_line(file_id, X_sbp, Y_sbp)
        except Exception as e:
            self.show_error("Error", f"Failed to load Ship navigation: {e}")

    def add_seismic_line(self, file_id, coordinates):
        """
        Add a seismic line to the map using the provided coordinates.
        The coordinates are stored in the active seismic lines dictionary.
        The map is updated to display the seismic line.
        """

        if coordinates:
            # Store the coordinates in active seismic lines
            self.active_seismic_lines[file_id] = coordinates
            
            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")
            # Update the map
            self.map, self.map_html = self.map_handler.load_survey_lines(coordinates, output_dir)
            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Map saved and loaded at: {self.map_html}")

    def remove_seismic_line(self, file_id):
        if file_id in self.active_seismic_lines:
            # Remove the seismic line
            del self.active_seismic_lines[file_id]

            # Define paths for map assets
            output_dir = os.path.join(self.project_data.get('folder_path'), "maps")
            print(f"output dir: {output_dir}")
            # Update the map
            self.map, self.map_html = self.map_handler.load_survey_lines(coordinates=None, dir = output_dir)
            # Enable QWebEngineView JavaScript and local file access
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.web_view.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

            # Load the map in the QWebEngineView
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(self.map_html))
            print(f"Map saved and loaded at: {self.map_html}")

    @pyqtSlot()
    def save_processed_segy(self):
        """
        Save the processed SEG-Y data to a file.
        If no processed data is available, it saves the raw data instead.
        The user can select the file format to save the data.
        """

        if self.processed_data is None:
            QtWidgets.QMessageBox.warning(self, "Warning", "No processed data available. Saving raw data instead.")
            data_to_save = self.data
        else:
            data_to_save = self.processed_data

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Data File", "", "SEG-Y Files (*.sgy *.segy)")
        if file_path:
            try:
                self.segy_handler.save_segy_file(file_path, self.spec, data_to_save)
                self.statusbar.showMessage(f"Saved data to {file_path}")
            except Exception as e:
                self.statusbar.showMessage(f"Error saving data: {e}")
    
    @pyqtSlot()
    def save_processed_mag(self):
        """ 
        Save the processed magnetic data to a file.
        If no processed data is available, it saves the raw data instead.
        The user can select the file format to save the data.   
        """

        if self.processed_data is None:
            QtWidgets.QMessageBox.warning(self, "Warning", "No processed data available. Saving raw data instead.")
            data_to_save = self.mag_db
        else:
            data_to_save = self.processed_data

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Data File", "", "CSV Files (*.csv);;Excel Files (*.xls *.xlsx);;Text Files (*.txt)")
        if file_path:
            try:
                self.mag_handler.save_data(output_path=file_path)
                self.statusbar.showMessage(f"Saved data to {file_path}")
            except Exception as e:
                self.statusbar.showMessage(f"Error saving data: {e}")

    @pyqtSlot()
    def close_segy(self):
        """
        Close all open SEG-Y files and clear the active seismic lines.
        The user can close all SEG-Y files at once.
        """

        try:
            for segy_file_info in self.segy_files.values():
                self.segy_handler.close_file(segy_file_info['segy_file'])
            self.statusbar.showMessage("All files closed successfully.")
            self.segy_files.clear()
            self.active_seismic_lines.clear()
            #self.plot_seismic_line(self.web_view)
        except Exception as e:
            self.statusbar.showMessage(f"Error closing files: {e}")

    @pyqtSlot()
    def seismic_editor(self, seismic_filepath=None):
        """
        Open the Seismic Editor to view and edit seismic data.
        If the editor is already open, it brings it to the front.
        If no seismic file is provided, it opens the editor with a default file.
        """

        if not hasattr(self, 'Seismic Editor') or self.seis_edit is None:
            self.seis_edit = SeismicEditor(seismic_filepath, db_file_path=None)
        self.seis_edit.show()

    @pyqtSlot()
    def maggy_editor(self, mag_filepath=None):
        """
        Open the Maggy Editor to view and edit magnetic data.
        If the editor is already open, it brings it to the front.
        If no magnetic file is provided, it opens the editor with a default file.
        """

        if not hasattr(self, 'Maggy Editor') or self.mag_edit is None:
            self.mag_edit = MaggyEditor(mag_filepath, db_file_path=None, project_data = self.project_data)
        self.mag_edit.show()


def main() -> int:
    """Entry point used by the console script."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = IntroWindow()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
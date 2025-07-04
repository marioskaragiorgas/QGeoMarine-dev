"""
Maggy_Editor.py

This module provides a GUI application for editing and analyzing magnetic data.
It allows users to load magnetic data from a SQLite database, visualize it in a table,
and perform various operations such as plotting, creating new columns, and deleting existing columns.
It also includes a sub-dialog for writing expressions using variables and previewing the resulting SQL-style translation
It is designed to work with the QGeoMarine framework and integrates with the Maggy_editor_UI for the user interface.
It uses PyQt6 for the GUI and pandas for data manipulation.
"""

import sys
import os
import re
import logging
import sqlite3
import pandas as pd
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QTableWidgetItem, QTreeWidgetItem, QHeaderView, QComboBox,
    QVBoxLayout, QWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from UI import Maggy_editor_UI  

logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(levelname)s - %(message)s", 
    stream=sys.stdout
    )

class MaggyEditor(QtWidgets.QMainWindow):
    """
    MaggyEditor is the main window class for the Maggy Editor application, providing a graphical interface for loading,
    visualizing, and manipulating magnetic data stored in a SQLite database.
    This class manages the user interface, database interactions, and user-driven operations such as plotting, 
    creating new columns via expressions, and deleting columns. It also supports advanced SQL translation for custom expressions
    and integrates with sub-dialogs for user input.

    Attributes:
        Attributes:
        maggy_file_path (str): Path to the Maggy file.
        db_file_path (str): Path to the SQLite database file.   

    
    Methods:
        __init__(maggy_file_path, db_file_path, parent=None): Initializes the editor and loads the database.
        setup_connections(): Sets up signal-slot connections for UI elements.
        add_file_to_tree(file_path): Adds a file to the tree view in the UI.
        load_table_names(): Loads table names from the database and populates the selector.
        load_selected_table(): Loads the selected table and displays it in the UI.
        populate_table_widget(df): Populates the data table widget with DataFrame data.
        show_context_menu(pos): Displays a context menu for table actions.
        plot_column_data(): Plots the data of the selected column.
        save_changes(item): Saves changes made in the table widget back to the database.
        MaggyAnalysisWin(): Opens the analysis window for advanced plotting and analysis.
        create_column(): Creates a new column in the database using a user-defined expression.
        translate_expression(expr, var_map): Translates a custom expression into a valid SQL expression.
        delete_column(): Deletes a column from the database.
        closeEvent(event): Handles application close events.
    """

    def __init__(self, maggy_file_path, db_file_path, parent=None):
        """
        Initializes the MaggyEditor with the given file paths and sets up the UI.
        Args:
            maggy_file_path (str): Path to the Maggy file.
            db_file_path (str): Path to the SQLite database file.
            parent (QWidget, optional): Parent widget for the main window.
        """
        super().__init__(parent)
        self.ui = Maggy_editor_UI()
        self.ui.setupUI(self)

        self.maggy_file_path = maggy_file_path
        self.db_file_path = db_file_path
        self.dataFrame = None
        self.table_names = []
        
        # Set the LineSelector combobox
        self.lineSelector = self.ui.lineSelection
        self.lineSelector.setFixedWidth(200)
        self.proxy_model = QSortFilterProxyModel(self)
        
        # Set table context menu
        self.ui.dataTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.dataTable.customContextMenuRequested.connect(self.show_context_menu)
        
    
        self.setup_connections()

        if db_file_path and os.path.exists(db_file_path):
            logging.info(f"Database path: {db_file_path}")
            self.add_file_to_tree(db_file_path)
            self.load_table_names()
        else:
            logging.error("Invalid magnetic database path provided.")

    def setup_connections(self):
        """Set up connections for UI elements."""
        self.lineSelector.currentIndexChanged.connect(self.load_selected_table)
        self.ui.dataTable.itemChanged.connect(self.save_changes)


    def add_file_to_tree(self, file_path):
        """Add the given file path to the tree view."""
        root = self.ui.treeview.topLevelItem(0)
        file_item = QTreeWidgetItem([os.path.basename(file_path)])
        file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        root.addChild(file_item)

    def load_table_names(self):
        """Load table names from the SQLite database and populate the LineSelector combobox."""
        try:
            conn = sqlite3.connect(self.db_file_path)
            tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
            self.table_names = pd.read_sql_query(tables_query, conn)['name'].tolist()
            conn.close()

            if not self.table_names:
                logging.warning("No tables found in the database.")
                return

            self.lineSelector.clear()
            self.lineSelector.addItems(self.table_names)
            self.load_selected_table()

        except sqlite3.Error as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def load_selected_table(self):
        """Load the selected table from the database and populate the data table widget."""
        selected_table = self.lineSelector.currentText()
        if not selected_table:
            return

        try:
            conn = sqlite3.connect(self.db_file_path)
            query = f"SELECT * FROM {selected_table}"
            self.dataFrame = pd.read_sql_query(query, conn)
            conn.close()
            
            self.populate_table_widget(self.dataFrame)
            logging.info(f"Loaded table: {selected_table}")
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def populate_table_widget(self, df):
        """Populate the data table widget with the given DataFrame."""
        self.ui.dataTable.blockSignals(True)
        self.ui.dataTable.setRowCount(df.shape[0])
        self.ui.dataTable.setColumnCount(df.shape[1])
        self.ui.dataTable.setHorizontalHeaderLabels(df.columns)

        for row_idx, row in df.iterrows():
            for col_idx, value in enumerate(row):
                self.ui.dataTable.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        self.ui.dataTable.blockSignals(False)
        logging.info("Data successfully loaded into the table.")

    def show_context_menu(self, pos):
        """Show context menu for the data table."""
        context_menu = QtWidgets.QMenu(self)
        plot_action = context_menu.addAction("Plot Column Data")
        export_action = context_menu.addAction("Export Table")
        action = context_menu.exec(self.ui.dataTable.mapToGlobal(pos))

        if action == plot_action:
            self.plot_column_data()
        elif action == export_action:
            self.export_table()
    
    def plot_column_data(self):
        """Plot the data of the selected column in the data table."""
        selected_column = self.ui.dataTable.currentColumn()
        if selected_column == -1 or self.dataFrame is None:
            QMessageBox.warning(self, "Plot Error", "No column selected or no data loaded.")
            return

        column_name = self.ui.dataTable.horizontalHeaderItem(selected_column).text()
        if column_name not in self.dataFrame.columns:
            QMessageBox.warning(self, "Plot Error", "Invalid column selected.")
            return
        
        self.ui.plotWidget.clear()
        self.ui.plotWidget.plot(self.dataFrame[column_name].to_numpy(), pen="b")
        logging.info(f"Plotted column: {column_name}")
    
    def save_changes(self, item):
        """Save changes made to the data table back to the database."""
        selected_table = self.lineSelector.currentText()
        if not selected_table:
            return

        row, col = item.row(), item.column()
        new_value = item.text()
        column_name = self.dataFrame.columns[col]
        primary_key_col = self.dataFrame.columns[0]
        primary_key_value = self.dataFrame.iloc[row, 0]
        
        try:
            conn = sqlite3.connect(self.db_file_path)
            cursor = conn.cursor()
            query = f"UPDATE {selected_table} SET {column_name} = ? WHERE {primary_key_col} = ?"
            cursor.execute(query, (new_value, primary_key_value))
            conn.commit()
            conn.close()
            logging.info("Database updated successfully")
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def MaggyAnalysisWin(self):
        """Open the Analysis window."""
        if self.dataFrame is None:
            QMessageBox.critical(self, "Error", "No data loaded.")
            return
        
        self.analysis_window = self.ui.plot_data_ui_win()
        self.ui.xcolumnInput.addItems(self.dataFrame.columns)
        self.ui.ycolumnInput.addItems(self.dataFrame.columns)
        
        def trace_update():
            """Update the trace plot based on the selected x and y columns."""

            x_idx = self.ui.xcolumnInput.currentIndex()
            y_idx = self.ui.ycolumnInput.currentIndex()
            
            if x_idx == -1 or y_idx == -1:
                QMessageBox.warning(self, "Plot Error", "No column selected.")
                return
            
            x_column = self.dataFrame.columns[x_idx]
            y_column = self.dataFrame.columns[y_idx]
            
            self.ui.Plot.clear()
            self.ui.Plot.plot(self.dataFrame[x_column], self.dataFrame[y_column], pen='b')
            self.ui.Plot.setTitle(f"Plot of {y_column} vs {x_column}")
            
        # Uptate the trace plot based on the selected x and y columns
        self.ui.xcolumnInput.currentIndexChanged.connect(trace_update)
        self.ui.ycolumnInput.currentIndexChanged.connect(trace_update)
        self.analysis_window.show()


        """

        def update_analysis(index):
            #Update the analysis plot based on the selected method.
            trace, t, trace_number = trace_update()
            if trace is None:
                return
            
            # Determine if we need to toggle between frequencyPlot and imagePlot
            show_image = index in [3, 4]  # Spectrogram or Wavelet Transform
            self.ui.togglePlots(show_image)

            try:
                if index == 0:  # FFT
                    trace_fft = np.fft.fft(trace)
                    freqs = np.fft.fftfreq(len(trace), self.sample_interval)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(np.abs(freqs), np.abs(trace_fft), pen='b')
                    self.ui.frequencyPlot.setTitle(f"FFT of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power', units='')

                elif index == 1:  # Periodogram
                    f, Pxx = trace_periodogram(trace, fs=self.sample_rate)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(f, Pxx, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Periodogram of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power Spectral Density', units='')

                elif index == 2:  # Welch Periodogram
                    f, Pxx = trace_welch_periodogram(trace, fs=self.sample_rate)
                    self.ui.frequencyPlot.clear()
                    self.ui.frequencyPlot.plot(f, Pxx, pen='b')
                    self.ui.frequencyPlot.setTitle(f"Welch Periodogram of Trace {trace_number}")
                    self.ui.frequencyPlot.setLabel('bottom', 'Frequency', units='Hz')
                    self.ui.frequencyPlot.setLabel('left', 'Power Spectral Density', units='')

                elif index == 3:  # Spectrogram
                    try:
                        f, t, Sxx = trace_spectrogram(trace, self.sample_rate)
                        
                        # Ensure ImageItem is used for spectrogram visualization
                        self.ui.imageitem.setImage(Sxx)  
                        self.ui.imageitem.setLevels((Sxx.min(), Sxx.max()))  # Adjust display levels

                        # Configure colorbar
                        self.ui.colorbar.setImageItem(self.ui.imageitem)  # Link ImageItem to colorbar
                        self.ui.colorbar.show()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to plot spectrogram: {str(e)}")


                elif index == 4:  # Wavelet Transform
                    widths = np.arange(1, 128)
                    cwt_matrix = trace_wavelet_transform(trace, widths)
                    normalized_cwt = np.abs(cwt_matrix) / np.max(np.abs(cwt_matrix))
                    self.ui.imagePlot.setImage(normalized_cwt.T, levels=(0, 1))
                    self.ui.imagePlot.setLabel('left', 'Frequency (Scale)')
                    self.ui.imagePlot.setLabel('bottom', 'Time (s)')
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update analysis plot: {str(e)}")
            
            # Show grid for frequencyPlot if visible
            if not show_image:
                self.ui.frequencyPlot.showGrid(x=True, y=True)"
        
        """
    
    def create_column(self):
        """Create a new column in the database based on a user-defined expression."""
        selected_table = self.lineSelector.currentText()
        if not selected_table:
            QtWidgets.QMessageBox.warning(self, "No Table Selected", "Please select a table first.")
            return

        # Step 1: Get column names from the DB
        try:
            conn = sqlite3.connect(self.db_file_path)
            df = pd.read_sql_query(f"SELECT * FROM '{selected_table}' LIMIT 1", conn)
            conn.close()
        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Database Error", str(e))
            return

        # Step 2: Launch Channel Math Dialog
        dialog = self.ui.ChannelMathDialog(columns=df.columns, parent=self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        expression, var_mapping = dialog.get_result()

        # Step 3: Get output column name
        new_column_name, ok = QtWidgets.QInputDialog.getText(
            self, "New Column", "Enter name for new column:"
        )
        if not ok or not new_column_name.strip():
            return
        new_column_name = new_column_name.strip()

        # Step 4: Translate expression to SQL
        try:
            translated_sql_expr = self.translate_expression(expression, var_mapping)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Translation Error", f"Failed to translate expression: {e}")
            return

        logging.info(f"Final SQL Expression: {translated_sql_expr}")

        # Step 5: Update database
        try:
            conn = sqlite3.connect(self.db_file_path)
            cursor = conn.cursor()

            # Add the new column
            cursor.execute(f'ALTER TABLE "{selected_table}" ADD COLUMN "{new_column_name}" REAL')

            # Use CTE for complex expressions with LEAD/LAG
            update_query = f"""
            WITH computed AS (
                SELECT rowid, {translated_sql_expr} AS new_value
                FROM "{selected_table}"
            )
            UPDATE "{selected_table}"
            SET "{new_column_name}" = (SELECT new_value FROM computed WHERE computed.rowid = "{selected_table}".rowid);
            """

            cursor.executescript(update_query)
            conn.commit()
            conn.close()

            logging.info(f"Column '{new_column_name}' successfully added and updated.")
            self.load_selected_table()

        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Database Error", str(e))

    def translate_expression(self, expr, var_map):
        """
        Translates a custom expression string into a valid SQL expression using LEAD/LAG and window functions.
        Args:
            expr (str): The input expression string, which may include variable references (e.g., 'C0', 'C1.offset(1)'), 
                        rolling functions (e.g., 'rollmean(C0, 3)'), and mathematical/statistical functions 
                        (e.g., 'sqrt(C1)', 'mean(C2)').
            var_map (dict): A mapping from variable names (e.g., 'C0', 'C1') to actual SQL column names.
        Returns:
            str: The translated SQL expression string, with appropriate SQL functions and windowing applied.
        Raises:
            ValueError: If an unsupported rolling function is encountered in the expression.
        Supported Features:
            - Variable references with optional offsets (e.g., 'C0.offset(1)' → 'LEAD("colname", 1) OVER (...)').
            - Rolling mean and sum (e.g., 'rollmean(C0, 3)' → 'AVG("colname") OVER (...)').
            - Common mathematical and statistical functions (e.g., 'sqrt', 'abs', 'mean', 'sum', etc.).
            - Handles translation for use in SQL queries, assuming 'rowid' is available for ordering.
        """
     
        # Replace Cx.offset(n) with LEAD/LAG
        def repl(match):
            var = match.group(1)
            offset = match.group(2)
            column = f'"{var_map[var]}"'

            if offset:
                offset_val = int(offset)
                func = "LEAD" if offset_val > 0 else "LAG"
                return f"{func}({column}, {abs(offset_val)}) OVER (ORDER BY rowid)"
            else:
                return column

        # Replace rollmean, rollsum
        def roll_repl(match):
            func_name = match.group(1)
            var = match.group(2)
            window = int(match.group(3))
            column = f'"{var_map[var]}"'

            if func_name == "mean":
                agg_func = "AVG"
            elif func_name == "sum":
                agg_func = "SUM"
            else:
                raise ValueError(f"Unsupported rolling function: {func_name}")

            preceding = (window - 1) // 2
            following = window // 2

            return f"{agg_func}({column}) OVER (ORDER BY rowid ROWS BETWEEN {preceding} PRECEDING AND {following} FOLLOWING)"

        # --- Step 1: handle rollmean / rollsum
        expr = re.sub(r'\broll(mean|sum)\(\s*(C\d+)\s*,\s*(\d+)\s*\)', 
                    roll_repl, expr)

        # --- Step 2: handle variables and offsets
        expr = re.sub(r'\b(C\d+)(?:\.offset\((-?\d+)\))?', repl, expr)

        # --- Step 3: replace math functions
        func_map = {
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
            "pow": r"POWER(\1)",  # Note: Ideally power(x,y)
            "floor": r"FLOOR(\1)",
            "ceil": r"CEIL(\1)",
            "round": r"ROUND(\1)",
            "exp": r"EXP(\1)",
            # statistical functions
            "mean": r"AVG(\1)",
            "median": r"MEDIAN(\1)",  # Note: Only some DBs support this
            "std": r"STDDEV(\1)",
            "var": r"VARIANCE(\1)",
            "min": r"MIN(\1)",
            "max": r"MAX(\1)",
            "sum": r"SUM(\1)",
            "count": r"COUNT(\1)",
            "countdistinct": r"COUNT(DISTINCT \1)",
            "first": r"FIRST_VALUE(\1)",
            "last": r"LAST_VALUE(\1)",
            # mode usually needs special handling
        }

        for func, replacement in func_map.items():
            expr = re.sub(fr'{func}\(([^)]+)\)', replacement, expr)

        return expr

    def delete_column(self):
        """Delete a column from the database."""
        selected_table = self.lineSelector.currentText()
        if not selected_table:
            QtWidgets.QMessageBox.warning(self, "No Table Selected", "Please select a table first.")
            return

        # Step 1: Get column names from the DB
        try:
            conn = sqlite3.connect(self.db_file_path)
            df = pd.read_sql_query(f"SELECT * FROM '{selected_table}' LIMIT 1", conn)
            conn.close()
        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Database Error", str(e))
            return

        # Step 2: Launch Column Deletion Dialog
        dialog = self.ui.ColumnDeleteDialog(columns=df.columns, parent=self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        column_to_delete = dialog.get_selected_column()

        # Step 3: Update database
        try:
            conn = sqlite3.connect(self.db_file_path)
            cursor = conn.cursor()

            # Create a new table without the column to be deleted
            columns = [col for col in df.columns if col != column_to_delete]
            columns_str = ", ".join([f'"{col}"' for col in columns])
            cursor.execute(f'CREATE TABLE "{selected_table}_temp" AS SELECT {columns_str} FROM "{selected_table}"')

            # Drop the old table and rename the new one
            cursor.execute(f'DROP TABLE "{selected_table}"')
            cursor.execute(f'ALTER TABLE "{selected_table}_temp" RENAME TO "{selected_table}"')

            conn.commit()
            conn.close()

            logging.info(f"Column '{column_to_delete}' successfully deleted.")
            self.load_selected_table()

        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Database Error", str(e))

    def closeEvent(self, event):
        logging.info("Closing application.")
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MaggyEditor()
    window.show()
    sys.exit(app.exec())
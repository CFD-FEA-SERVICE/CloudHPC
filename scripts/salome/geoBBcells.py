"""
-------------------------------------------------------------------------------
CFD FEA Service SRL
Company Owner: Ruggero Poletto
Author: Andrea Pisa
Release: 1.1
Date: 2024-04-30

Description:
This script provides utilities for performing geometrical calculations, meshing,
and simulation preparations specific to the needs of CFD and FEA analyses.
These tools are designed to integrate smoothly with the SALOME platform.

-------------------------------------------------------------------------------
"""
def geoBBcells(context):

    # Import necessary libraries
    import salome
    import GEOM
    from salome.geom import geomBuilder
    import math
    from salome.smesh import smeshBuilder
    from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox

    salome.salome_init()
    geompy = geomBuilder.New()
    smesh = smeshBuilder.New()

    # Select the geometry object from the SALOME study tree
    selected_id = salome.sg.getSelected(0)  # Assuming one object is selected
    selected_shape = salome.myStudy.FindObjectID(selected_id).GetObject()
    selected_shape_name = selected_shape.GetName()  # Get the name of the selected geometry

    # Calculate the bounding box of the selected geometry
    bbox = geompy.BoundingBox(selected_shape)

    # Extract dimensions of the bounding box
    dx = bbox[1] - bbox[0]  # x dimension
    dy = bbox[3] - bbox[2]  # y dimension
    dz = bbox[5] - bbox[4]  # z dimension

    # Calculate the volume of the bounding box
    bounding_box_volume = abs(dx * dy * dz)

    # Function to prompt the user for cell size using PyQt
    def get_cell_size():
        app = QApplication.instance()  # checks if QApplication already exists
        if not app:  # create QApplication if it doesnt exist 
            app = QApplication([])
        cell_size, ok = QInputDialog.getDouble(None, f"Input Cell Size - {selected_shape_name}", "Enter cell size (as a cube side length):", decimals=3)
        if ok:
            return cell_size
        else:
            return None
            

    # Get cell size from user
    cell_size = get_cell_size()

    if cell_size is not None:
        # Calculate the volume of a single cell
        cell_volume = cell_size ** 3

        # Calculate how many cells can fit inside the bounding box
        num_cells = bounding_box_volume / cell_volume

        # Round down to the nearest whole number
        num_cells_fit = math.floor(num_cells)
        
        # Format the number with commas
        formatted_num_cells = f"{num_cells_fit:,}"

        # Output the result in a Qt dialog
        msg = f"Number of cells that can fit inside the bounding box of '{selected_shape_name}': {formatted_num_cells}"
        QMessageBox.information(None, f"Calculation Result - {selected_shape_name}", msg)
    else:
        QMessageBox.warning(None, f"Input Error - {selected_shape_name}", "Cell size input was canceled or invalid.")

    # Finalizing and cleaning up SALOME session
    if salome.sg.hasDesktop():
        salome.sg.updateObjBrowser()

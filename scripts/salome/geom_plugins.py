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
import salome_pluginsmanager

from geoBBcells import *
from tenuFemPreprocessing import *

salome_pluginsmanager.AddFunction('Calculate bounding box cells ',
                                  'Similar to blockMeshDict utility',
                                  geoBBcells)

salome_pluginsmanager.AddFunction('TENUFEM pre processor ',
                                  'preprocessing of the mesh',
                                  tenuFemPreprocessing)

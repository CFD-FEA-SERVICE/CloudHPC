import tkinter as tk
from tkinter import ttk, TclError, filedialog
from data_singleton import DataSingleton
import os, math, sys
from utils import rm_buttons_map

# numpy-stl is optional — gracefully degrade if not installed
try:
    import numpy
    import stl
    from stl import mesh as stl_mesh
    _STL_AVAILABLE = True
except ImportError:
    _STL_AVAILABLE = False

data_instance = DataSingleton.get_instance()

def _stl_not_available(title):
    tk.messagebox.showerror(
        title=title,
        message="This feature requires the 'numpy-stl' package.\n"
                "Install it with:  pip install numpy-stl"
    )

def find_mins_maxs(obj):
   minx = maxx = miny = maxy = minz = maxz = None
   for p in obj.points:
      if minx is None:
         minx = p[stl.Dimension.X]; maxx = p[stl.Dimension.X]
         miny = p[stl.Dimension.Y]; maxy = p[stl.Dimension.Y]
         minz = p[stl.Dimension.Z]; maxz = p[stl.Dimension.Z]
      else:
         maxx = max(p[stl.Dimension.X], maxx); minx = min(p[stl.Dimension.X], minx)
         maxy = max(p[stl.Dimension.Y], maxy); miny = min(p[stl.Dimension.Y], miny)
         maxz = max(p[stl.Dimension.Z], maxz); minz = min(p[stl.Dimension.Z], minz)
   return minx, maxx, miny, maxy, minz, maxz

def estimate_coarseMesh():
   if not _STL_AVAILABLE:
       _stl_not_available("estimate coarseMesh"); return

   maxx=-1e+30; maxy=-1e+30; maxz=-1e+30
   minx=+1e+30; miny=+1e+30; minz=+1e+30

   for key in data_instance.all_data:
      if 'file' in data_instance.all_data[key]["data"].keys():
         for stlfile in list(data_instance.all_data[key]["data"]["file"].keys()):
            if stlfile.endswith('.stl'):
               main_body = stl_mesh.Mesh.from_file(stlfile)
               minx_f,maxx_f,miny_f,maxy_f,minz_f,maxz_f = find_mins_maxs(main_body)
               maxx=max(maxx,maxx_f); maxy=max(maxy,maxy_f); maxz=max(maxz,maxz_f)
               minx=min(minx,minx_f); miny=min(miny,miny_f); minz=min(minz,minz_f)
         dim_100k = (((maxx-minx)*(maxy-miny)*(maxz-minz))/100000)**(1/3)
         dim_1M   = (((maxx-minx)*(maxy-miny)*(maxz-minz))/1000000)**(1/3)
         dim_10M  = (((maxx-minx)*(maxy-miny)*(maxz-minz))/10000000)**(1/3)
         if len(list(data_instance.all_data[key]["data"]["file"].keys())) > 0:
            tk.messagebox.showinfo(title="estimate coarseMesh",
               message=f"100k coarseMesh: {dim_100k:.5f}\n1M coarseMesh: {dim_1M:.5f}\n10M coarseMesh: {dim_10M:.5f}")
         else:
            tk.messagebox.showerror(title="estimate coarseMesh",
               message="estimate coarseMesh only works with STL input files ...")

def get_boundingbox():
   if not _STL_AVAILABLE:
       _stl_not_available("get boundingBox"); return

   maxx=-1e+30; maxy=-1e+30; maxz=-1e+30
   minx=+1e+30; miny=+1e+30; minz=+1e+30

   for key in data_instance.all_data:
      if 'file' in data_instance.all_data[key]["data"].keys():
         for stlfile in list(data_instance.all_data[key]["data"]["file"].keys()):
            if stlfile.endswith('.stl'):
               main_body = stl_mesh.Mesh.from_file(stlfile)
               minx_f,maxx_f,miny_f,maxy_f,minz_f,maxz_f = find_mins_maxs(main_body)
               maxx=max(maxx,maxx_f); maxy=max(maxy,maxy_f); maxz=max(maxz,maxz_f)
               minx=min(minx,minx_f); miny=min(miny,miny_f); minz=min(minz,minz_f)
         dX=maxx-minx; dY=maxy-miny; dZ=maxz-minz
         if len(list(data_instance.all_data[key]["data"]["file"].keys())) > 0:
            tk.messagebox.showinfo(title="get boundingBox",
               message=f"X dimension: {dX:.5f}\nY dimension: {dY:.5f}\nZ dimension: {dZ:.5f}")
         else:
            tk.messagebox.showerror(title="get boundingBox",
               message="bounding box only works with STL input files ...")

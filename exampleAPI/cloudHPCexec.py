#!/bin/python3

#import PySimpleGUI as sg

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import os, json

# dependencies installation
os.system("pip install touch requests")
import touch, requests, shutil

try:
    os.makedirs( os.path.join( str( Path.home() ) , '.cfscloudhpc') )
except FileExistsError:
    pass

DOTENV_FILE = os.path.join( str( Path.home() ) , '.cfscloudhpc', 'apikey' )
touch.touch( DOTENV_FILE )

# window definition
root = tk.Tk()

root.title( "Cloud HPC - Run" )
root.grid_columnconfigure(0, weight=5)
root.grid_columnconfigure(1, weight=5)
root.grid_columnconfigure(2, weight=1)

window_width = 300
window_height = 200

# get the screen dimension
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# find the center point
center_x = int(screen_width/2 - window_width / 2)
center_y = int(screen_height/2 - window_height / 2)

root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
root.resizable(False,False)

#SEMPRE IN PRIMO PIANO
root.attributes('-topmost', 1)

#ICONA DELLA FINESTRA
#root.iconbitmap('./assets/pythontutorial.ico')

#APIKEY
apikey = tk.StringVar()

env_file = open( DOTENV_FILE, 'r' )
apikey_file = env_file.readline()
env_file.close()

apikey.set( apikey_file )

ttk.Label(root, text="APIKEY:").grid( row=3, column=0 )
ttk.Entry(root, textvariable=apikey, width=30).grid( row=3, column=1, columnspan=2 )
#apikey_entry.pack(fill='x', expand=True)

if ( apikey.get() != "" ):

   #CPU DROP DOWN
   headers = { "X-API-key" : apikey.get().rstrip("\n"), "accept" : "application/json", }
   cpu_response = requests.get( 'https://cloud.cfdfeaservice.it/api/v2/simulation/view-cpu', headers=headers)

   cpu_dropdown = tk.StringVar()
   cpu_dropdown.set( cpu_response.json()['response'][0] )

   ttk.Label(root, text="vCPU:").grid( row=4, column=0 )
   cpumenu = tk.OptionMenu( root, cpu_dropdown, *cpu_response.json()['response'] )
   cpumenu.grid( row=4, column=1, columnspan=2  )
   cpumenu.config(width=25)

   #RAM DROP DOWN
   headers = { 'X-API-key' : apikey.get().rstrip("\n"), 'accept' : 'application/json', }
   ram_response = requests.get( 'https://cloud.cfdfeaservice.it/api/v2/simulation/view-ram', headers=headers)

   ram_dropdown = tk.StringVar()
   ram_dropdown.set( ram_response.json()['response'][0] )

   ttk.Label(root, text="RAM:").grid( row=5, column=0 )
   rammenu = tk.OptionMenu( root, ram_dropdown, *ram_response.json()['response'] )
   rammenu.grid( row=5, column=1, columnspan=2 )
   rammenu.config(width=25)

   #SCRIPT DROP DOWN
   headers = { 'X-API-key' : apikey.get().rstrip("\n"), 'accept' : 'application/json', }
   scripts_response = requests.get( 'https://cloud.cfdfeaservice.it/api/v2/simulation/view-scripts', headers=headers)

   scripts_dropdown = tk.StringVar()
   scripts_dropdown.set( scripts_response.json()['response'][0] )

   ttk.Label(root, text="SCRIPT:").grid( row=6, column=0 )
   scriptmenu = tk.OptionMenu( root, scripts_dropdown, *scripts_response.json()['response'] )
   scriptmenu.grid( row=6, column=1, columnspan=2 )
   scriptmenu.config(width=25)

   #FOLDER
   def getFolderPath():
       folder_selected = filedialog.askdirectory()
       folderPath.set(folder_selected)

   folderPath = tk.StringVar()
   ttk.Label(root, text="FOLDER:").grid( row=7, column=0 )
   ttk.Entry(root, textvariable=folderPath).grid( row=7, column=1 )
   ttk.Button(root, text="Browse Folder",command=getFolderPath).grid( row=7, column=2)

   #BOTTONE
   def select(APIKEY, DOTENV_FILE, cpu, ram, script, path):
       print(APIKEY)
       print(cpu)
       print(ram)
       print(script)
       print(path)

       #Saving APIKEY
       env_file = open( DOTENV_FILE , 'w')
       env_file.write( APIKEY )
       env_file.close()

       #Compress folder
       shutil.make_archive( os.path.join( os.path.join( path, os.pardir ) , "simulation" ), 'zip', path )

       #URL upload
       data = { "dirname": os.path.basename( path ), 
                "filename": "simulation.zip",
                "contentType": "application/gzip"
               }

       headers = { 'X-API-key' : apikey.get().rstrip("\n"), 'accept' : 'application/json',  'Content-Type' : 'application/json',  }
       url_upload_response = requests.post( 'https://cloud.cfdfeaservice.it/api/v2/storage/upload-url', headers=headers, json=data )

       files = {'file': open( os.path.join( os.path.join( path, os.pardir ) , "simulation.zip" ) ,'rb')}
       headers = { 'content-type' : 'application/gzip',  }
       upload_file = requests.put( url_upload_response.json()['response']['url'], files=files, headers=headers )

       data = { "cpu": int( cpu),
                "ram": ram,
                "folder": os.path.basename( path ),
                "script": script,
              }
       headers = { 'X-API-key' : apikey.get().rstrip("\n"), 'accept' : 'application/json',  'Content-Type' : 'application/json',  }
       simulation_exec = requests.post( 'https://cloud.cfdfeaservice.it/api/v2/simulation/add', headers=headers, json=data )

       print( "Esecution ID: " + str( simulation_exec.json(['response'] ) )

       #if os.path.exists( os.path.join( os.path.join( path, os.pardir ) , "simulation.zip" ) ):
       #   print( "Rimozione file ZIP" )
       #   os.remove( os.path.join( path, os.pardir, "simulation.zip" ) )

       tk.Toplevel().destroy

   ButtonOK = ttk.Button(root, text='Launch', command=lambda: select( apikey.get().rstrip("\n") , DOTENV_FILE , cpu_dropdown.get(), ram_dropdown.get(), scripts_dropdown.get(), folderPath.get() ) ).place( x=window_width-160, y=window_height-30 )
   ButtonCancel = ttk.Button(root, text='Cancel', command=root.destroy).place( x=window_width-80, y=window_height-30 )

else:
   def saveapikey(APIKEY):
       #Saving APIKEY
       env_file = open( DOTENV_FILE , 'w')
       env_file.write( APIKEY )
       env_file.close()

   ButtonOK   = ttk.Button(root, text='Save', command=lambda: saveapikey( apikey.get().rstrip("\n") ) ).place( x=window_width-160, y=window_height-30 )
   ButtonEXIT = ttk.Button(root, text='Exit', command=root.destroy).place( x=window_width-80, y=window_height-30 )

# keep the window displaying
root.mainloop()

import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
import requests
import shutil, zipfile
from threading import Thread
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from IO_service import export_to_xml
from data_singleton import DataSingleton

class CloudHPCApp:
    def __init__(self, XMLfilename, GUIsetup_filename, vCPU, first_time=True):
        self.dotenv_file = os.path.join(Path.home(), '.cfscloudhpc', 'apikey')
        self.apikey = tk.StringVar()
        if first_time:
            self.exported_folder_path = export_to_xml(XMLfilename)
            self.Output_filename = XMLfilename
            self.GUIsetup_filename = GUIsetup_filename
            self.cpu = vCPU
            self.nopre = None
            self.script = None
            self.ram = None
            self.data_instance = DataSingleton.get_instance()
            self.prepare_api_key_file()
            self.setup_ui()
        else:
            self.change_api_key()

    def setup_ui(self):
        # Set up UI components
        self.read_api_key()
        if self.apikey.get():
            self.validate_api_key()
        else:
            self.prompt_for_api_key()
            self.master.grab_set()

    def prompt_for_api_key(self):
        # Set up UI components to enter the API key
        self.master = tk.Toplevel()
        self.master.title("Run on Cloud")
        self.create_api_key_entry()
        self.create_save_exit_buttons()


    def create_api_key_entry(self):
        ttk.Label(self.master, text="APIKEY:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        apikey_entry = ttk.Entry(self.master, textvariable=self.apikey, width=30)
        apikey_entry.grid(row=0, column=1, padx=5, pady=5)
        apikey_entry.focus()
        self.read_api_key()

    def create_save_exit_buttons(self):
        self.button_save = ttk.Button(self.master, text='Save', command=self.validate_api_key).grid(row=1, column=0, padx=5, pady=5)
        self.button_exit = ttk.Button(self.master, text='Exit', command=self.master.destroy).grid(row=1, column=1, padx=5, pady=5)

    def prepare_api_key_file(self):
        os.makedirs(os.path.dirname(self.dotenv_file), exist_ok=True)
        if not os.path.exists(self.dotenv_file):
            with open(self.dotenv_file, 'w'): pass

    def read_api_key(self):
        with open(self.dotenv_file, 'r') as file:
            apikey_file = file.readline().rstrip("\n")
        if apikey_file:
            self.apikey.set(apikey_file)

    def save_api_key(self):
        with open(self.dotenv_file, 'w') as file:
            file.write(self.apikey.get())

    def change_api_key(self):
        self.read_api_key()
        self.master = tk.Toplevel()
        self.master.title("Change API Key")
        ttk.Label(self.master, text="Current API Key:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        apikey_entry = ttk.Entry(self.master, textvariable=self.apikey, width=30)
        apikey_entry.grid(row=0, column=1, padx=5, pady=5)
        apikey_entry.focus()

        ttk.Button(self.master, text='Save', command=self.update_api_key).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(self.master, text='Cancel', command=self.master.destroy).grid(row=1, column=1, padx=5, pady=5)

    def update_api_key(self):
        self.save_api_key()
        self.master.destroy()

    def validate_api_key(self):
        # Make a request to validate the API key
        
        response = requests.get('https://cloud.cfdfeaservice.it/api/v2/simulation/view-cpu', headers=self.get_headers())
        if response.status_code == 200:
            # If the API key is valid, set up the full UI
            self.save_api_key()
            if hasattr(self, 'master') and isinstance(self.master, tk.Tk):
                self.master.destroy()
            self.read_xml_and_start_simulation()
        else:
            # If the API key is not valid, prompt for it
            self.prompt_for_api_key()

    def read_xml_and_start_simulation(self):
        # Read XML file for simulation parameters
        xml_params = self.read_xml_file()
        if xml_params:
            self.init_cloud_engine_with_params(xml_params)
        else:
            print("Error reading XML file or XML file does not contain required parameters")

    def read_xml_file(self):
        try:
            tree = ET.parse(self.GUIsetup_filename)
            root = tree.getroot()
            cloud_execution = root.find('cloudExecution')
            if cloud_execution is not None:
                #TODO da togliere [passato come inizializzazione
                #print(f"vCPU {cloud_execution.findtext('vCPU')}")

                print(f"script {cloud_execution.findtext('script')}")
                print(f"ram {cloud_execution.findtext('ram')}")
                print(f"nopre {cloud_execution.findtext('nopre')}")
                return {
                    #TODO da togliere [passato come inizializzazione
                    #'vCPU': cloud_execution.findtext('vCPU'),
                    'script': cloud_execution.findtext('script'),
                    'ram': cloud_execution.findtext('ram'),
                    'nopre': cloud_execution.findtext('nopre')
                }
            else:
                print("cloud_execution is NONE")
        except Exception as e:
            print(f"Error reading XML file: {e}")
        return None

    def init_cloud_engine_with_params(self, params):
        # Initialize the cloud engine with the parameters from the XML file
        
        #TODO da togliere [passato come inizializzazione
        #self.cpu = params['vCPU']

        self.script = params['script']
        self.ram = params['ram']
        self.nopre = params['nopre']
        self.launch_simulation()

    def launch_simulation(self):
        if not self.exported_folder_path:
           tk.messagebox.showerror( title="Execution impossible", message="No folder selected" )

        #If there are files => cloud execution and then return
        for key in self.data_instance.all_data:

           if 'file' in self.data_instance.all_data[key]["data"].keys():
              if ( len( list( self.data_instance.all_data[key]["data"]["file"].keys() ) ) > 0 ):
                 print( "Cloud execution starts" )
                 self.delete_folder_cloudhpc()
                 self.compress_folder()
                 self.upload_zip_file()
                 self.execute_simulation_with_params()
                 self.delete_zip_file()
                 return

        #If there are no files, the above return is never hit => errorbox"
        tk.messagebox.showerror( title="Execution impossible", message="No input file - check your data!" )

    def save_api_key_to_file(self):
        with open(self.dotenv_file, 'w') as file:
            file.write(self.apikey.get())

    def compress_folder(self):
        folder_path = self.exported_folder_path
        if folder_path:

            #re-generation of the folder attachments
            attachments_dir_path = os.path.dirname( folder_path + "/attachments/" )
            if os.path.exists( attachments_dir_path ) and os.path.isdir( attachments_dir_path ):
               shutil.rmtree( attachments_dir_path )
            os.makedirs( attachments_dir_path )

            #look for the files in the data instance and copy them to the folder
            for k, v in self.data_instance.all_data.items():
                if self.data_instance.all_data[k]["data"].get("file", None):
                    for file_path in self.data_instance.all_data[k]["data"]["file"]:
                        print(f"copied file {file_path} for simulation")
                        shutil.copy( file_path, attachments_dir_path )

            #Compress files with shutil: compress the whole folder content
            #shutil.make_archive(os.path.join(folder_path, "simulation"), 'zip', folder_path)

            #Compress files with zipfile: compress only XML and attachment folder
            def zip_files_and_folder(folder_path, files_to_zip, folder_to_zip, zip_filename):
               with zipfile.ZipFile(zip_filename, 'w') as zipf:
                  for file in files_to_zip:
                     file_path = os.path.join(folder_path, file)
                     zipf.write(file_path, arcname=file)

                  # Add the entire folder and its contents to the ZIP
                  for root, dirs, files in os.walk(os.path.join(folder_path, folder_to_zip)):
                     for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname=arcname)

	    # Example usage
            files_to_zip = [ self.Output_filename ]
            folder_to_zip = 'attachments'  # The name of the folder you want to include
            zip_filename = os.path.join( folder_path, 'simulation.zip' )

            print( folder_path )
            print( files_to_zip )
            print( folder_to_zip )
            print( zip_filename )

            zip_files_and_folder(folder_path, files_to_zip, folder_to_zip, zip_filename)

        else:
            print("No folder selected")

    def delete_folder_cloudhpc(self):
        data = { "path": os.path.basename(self.exported_folder_path) }
        try:
           filename = requests.post( 'https://cloud.cfdfeaservice.it/api/v2/storage/view-by-path', 
                                     headers=self.get_headers(), json=data )

           print( "ID TO DELETE: " + str( filename.json()["response"]["id"] ) )

           response = requests.delete("https://cloud.cfdfeaservice.it/api/v2/storage/delete/" +
                                                   str( filename.json()["response"]["id"] ), 
                                      headers=self.get_headers() )

           print( response.json() )

        except Exception as e:
           print(f"Error during upload: {e}")

    def upload_zip_file(self):
        data = {
            "dirname": os.path.basename(self.exported_folder_path),
            "filename": "simulation.zip",
            "contentType": "application/gzip"
        }
        try:
            upload_response = requests.post('https://cloud.cfdfeaservice.it/api/v2/storage/upload-url', 
                                            headers=self.get_headers(), json=data)
            if upload_response.status_code == 200:
                upload_url = upload_response.json()['response']['url']
                with open(os.path.join(self.exported_folder_path, "simulation.zip"), 'rb') as file:
                    requests.put(upload_url, data=file, headers={'content-type': 'application/gzip'})
            else:
                print("Error obtaining upload URL")
        except Exception as e:
            print(f"Error during upload: {e}")

    def delete_zip_file(self):
        if os.path.isfile( os.path.join(self.exported_folder_path, "simulation.zip") ):
            os.remove( os.path.join(self.exported_folder_path, "simulation.zip") )

    def execute_simulation_with_params(self):
        data = {
            "cpu": int(self.cpu),
            "ram": self.ram,
            "nopre": int(self.nopre),
            "folder": os.path.basename(self.exported_folder_path),
            "script": self.script,
        }
        try:
            clear_cache   = requests.delete('https://cloud.cfdfeaservice.it/api/v2/user/delete-cache', headers=self.get_headers())

            exec_response = requests.post('https://cloud.cfdfeaservice.it/api/v2/simulation/add', 
                                          headers=self.get_headers(), json=data)
            if exec_response.status_code == 200:
                execution_id = exec_response.json()['response']
                print("Execution ID:", execution_id)
                webbrowser.open(f'https://cloud.cfdfeaservice.it/en/simulation/view/{execution_id}')
 
            else:
                print(f"Error executing simulation {exec_response.content}")
        except Exception as e:
            print(f"Error during simulation execution: {e}")

    def get_headers(self):
        return {"X-API-key": self.apikey.get().rstrip("\n"), "accept": "application/json"}

class CloudHPCDownload:
    def __init__(self, XMLfilename, GUIsetup_filename):
        self.exported_folder_path = export_to_xml(XMLfilename)
        self.GUIsetup_filename = GUIsetup_filename
        self.download = []
        self.apikey = tk.StringVar()
        self.dotenv_file = os.path.join(Path.home(), '.cfscloudhpc', 'apikey')
        self.data_instance = DataSingleton.get_instance()
        self.prepare_api_key_file()
        self.setup_ui()

    def setup_ui(self):
        # Set up UI components
        self.read_api_key()
        if self.apikey.get():
            self.validate_api_key()
        else:
            self.prompt_for_api_key()
            self.master.grab_set()

    def prompt_for_api_key(self):
        # Set up UI components to enter the API key
        self.master = tk.Toplevel()
        self.master.title("Run on Cloud")
        self.create_api_key_entry()
        self.create_save_exit_buttons()


    def create_api_key_entry(self):
        ttk.Label(self.master, text="APIKEY:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        apikey_entry = ttk.Entry(self.master, textvariable=self.apikey, width=30)
        apikey_entry.grid(row=0, column=1, padx=5, pady=5)
        apikey_entry.focus()
        self.read_api_key()

    def create_save_exit_buttons(self):
        self.button_save = ttk.Button(self.master, text='Save', command=self.validate_api_key).grid(row=1, column=0, padx=5, pady=5)
        self.button_exit = ttk.Button(self.master, text='Exit', command=self.master.destroy).grid(row=1, column=1, padx=5, pady=5)

    def prepare_api_key_file(self):
        os.makedirs(os.path.dirname(self.dotenv_file), exist_ok=True)
        if not os.path.exists(self.dotenv_file):
            with open(self.dotenv_file, 'w'): pass

    def read_api_key(self):
        with open(self.dotenv_file, 'r') as file:
            apikey_file = file.readline().rstrip("\n")
        if apikey_file:
            self.apikey.set(apikey_file)

    def save_api_key(self):
        with open(self.dotenv_file, 'w') as file:
            file.write(self.apikey.get())

    def validate_api_key(self):
        # Make a request to validate the API key
        
        response = requests.get('https://cloud.cfdfeaservice.it/api/v2/simulation/view-cpu', headers=self.get_headers())
        if response.status_code == 200:
            # If the API key is valid, set up the full UI
            self.save_api_key()
            if hasattr(self, 'master') and isinstance(self.master, tk.Tk):
                self.master.destroy()
            self.read_xml_and_start_simulation()
        else:
            # If the API key is not valid, prompt for it
            self.prompt_for_api_key()

    def read_xml_and_start_simulation(self):
        # Read XML file for simulation parameters
        xml_params = self.read_xml_file()
        if xml_params:
            self.init_cloud_engine_with_params(xml_params)
        else:
            print("Error reading XML file or XML file does not contain required parameters")

    def read_xml_file(self):
        try:
            tree = ET.parse(self.GUIsetup_filename)
            root = tree.getroot()
            cloud_execution = root.find('cloudExecution')

            download_list = []

            if cloud_execution is not None:

                for item in cloud_execution.findall( 'download' ):
                   download_list.append( item.text )

                return ( download_list )
            else:
                print("cloud_execution is NONE")
        except Exception as e:
            print(f"Error reading XML file: {e}")
        return None

    def init_cloud_engine_with_params(self, params):
        # Initialize the cloud engine with the parameters from the XML file
        self.download = params
        self.download_results()

    def download_results(self):
        self.download_compress_file()

    def save_api_key_to_file(self):
        with open(self.dotenv_file, 'w') as file:
            file.write(self.apikey.get())

    def download_compress_file(self):
        folder_path = self.exported_folder_path

        if folder_path:
            popup = tk.Toplevel()
            popup.title("Download status")
            popup.geometry("300x100")
            progress_bar = ttk.Progressbar( popup, orient='horizontal', length=200, maximum=len( self.download ), mode='determinate' )
            progress_bar.pack(pady=20)
            progress_bar.start()
            popup.update()

            for file_to_download in self.download:

               try:
                  print( "@@ DOWNLOAD FILE " + file_to_download + " @@" )
                  response = requests.post( 'https://cloud.cfdfeaservice.it/api/v2/storage/view-by-path', headers=self.get_headers(), data={ "path": os.path.basename( folder_path ) + "/" + file_to_download } )
                  print( response.json() )

                  url = requests.get( 'https://cloud.cfdfeaservice.it/api/v2/storage/view-url/' + str( response.json()['response']['id'] ), headers=self.get_headers() )
                  print( url.json() )

                  filecontent = requests.get( url.json()['response']['mediaLink'] )
                  open( os.path.join( folder_path, os.pardir, file_to_download ) , 'wb').write(filecontent.content)

                  shutil.unpack_archive( os.path.join( folder_path, os.pardir, file_to_download ), folder_path )
                  os.remove( os.path.join( folder_path, os.pardir, file_to_download) )

                  progress_bar['value'] = self.download.index( file_to_download ) - 1
                  #popup.update_idletasks()
                  popup.update()
                  print( "@@ DOWNLOAD COMPLETE @@" )
               except:
                  tk.messagebox.showerror(title='Download failed', message="File not found: " + os.path.basename( folder_path ) + "/" + file_to_download )

            popup.destroy()

            os.startfile( folder_path ) 

        else:
            tk.messagebox.showerror( title="Download failed", message="No folder selected" )
            print("No folder selected")

    def get_headers(self):
        return {"X-API-key": self.apikey.get().rstrip("\n"), "accept": "application/json"}


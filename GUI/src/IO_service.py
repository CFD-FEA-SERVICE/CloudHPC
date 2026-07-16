import os
from xml.dom import minidom
import copy
from GUI_logic import update_fields
from utils import BASIC_SETTINGS_TAB_NAME, add_default_multiples_to_data, convert_string_to_bool, find_key_by_value, get_multis_by_indent, identify_multiple
from data_singleton import DataSingleton
from collections import OrderedDict

data_instance = DataSingleton.get_instance()

# Function to create the XML data structure based on the XML file.
def create_xml_datastructure(XML_rep, setup_filepath):

   # Recursive function to read nodes of XML and create a data representation of the XML structure.
   def get_XMLnode_child(root, XML_rep, indent):
      for node in root.childNodes:
         if (node.nodeType != 1):
            #nodeType = 1 stands for Element Node
            continue

         default = None
         type = None
         specify_name = False
         single_file = True
         probe_point = False

         # Get attributes of the XML node.
         for i in range( node.attributes.length ):
            attribute = node.attributes.item(i)
            if attribute.nodeName == "type":
               type = attribute.nodeValue
            if attribute.nodeName.lower() == "specifyName".lower():
               _sn_val = attribute.nodeValue.strip()
               if _sn_val == "CADgroups":
                  specify_name = "CADgroups"
               else:
                  specify_name = convert_string_to_bool(_sn_val)
            if attribute.nodeName.lower() == "singleFile".lower():
               single_file = convert_string_to_bool(attribute.nodeValue)
            if attribute.nodeName.lower() == "probePoint".lower():
               probe_point = convert_string_to_bool(attribute.nodeValue)

         # Convert the XML node value based on its type.
         if type == "int":
            default = int(node.firstChild.nodeValue)

         elif type == "float":
            if ( float( node.firstChild.nodeValue ) < 1e-4 ):
               default = format( float( node.firstChild.nodeValue ), '.10f' )
            else:
               default = float( node.firstChild.nodeValue )

         elif type == "bool":
            default = bool(node.firstChild.nodeValue)

         elif type == "file":
            print("found a file type")
            default = node.firstChild.nodeValue

         elif type == "software":
            print("found a software type")
            default = node.firstChild.nodeValue

         elif type == "CAD":
            # Embeds the STEP management UI as a tab
            default = node.firstChild.nodeValue if node.firstChild else ""

         elif type == "CADgroups-dropdown":
            default = node.firstChild.nodeValue if node.firstChild else ""

         else:
            default = node.firstChild.nodeValue

         XML_temp_rep = {
            'name': node.nodeName, 
            'type': type, 
            'default': default, 
            'indent': indent
         }

         #if specify_name:
         XML_temp_rep["specifyName"] = specify_name
         XML_temp_rep["probePoint"] = probe_point

         #if single_file:
         XML_temp_rep["singleFile"] = single_file

         # Append the node details to the XML representation.
         XML_rep.append(XML_temp_rep)

         # Recursive call to process child nodes.
         get_XMLnode_child(node, XML_rep, indent + 1)

   #Input file must be in the same directory as the PYTHON
   

   # Parse the XML file 
   mydoc = minidom.parse(setup_filepath)
   starting_node = mydoc.getElementsByTagName("XMLFileDescription")[0]

   get_XMLnode_child(starting_node, XML_rep, 1)

   return [ starting_node.attributes.item(0).nodeValue, starting_node.attributes.item(1).nodeValue ]


### EXPORT ###
def prepare_data(data):
   data_copy = copy.deepcopy(data)
   print(f"data copy before: {data_copy}")
   #get the data_copy element that contains the file type inside its "data" dictionary
   for k, v in data_copy.items():
      if isinstance(v["data"], dict):
         to_remove = []
         for key, value in v["data"].items():
            if isinstance(value, dict) and key=="file":
               print("you got me!")
               for file_path, d_value in value.items():
                  print(f"creating file element for {file_path}")
                  data_copy[k]["data"][f"file_{file_path}"] = d_value
               to_remove.append(key)
               break
         for _ in to_remove:
            data_copy[k]["data"].pop(_, None)
   print(f"data copy after files dict transform: {data_copy}")

   multiples = {}
   popKeys = {}

   #extract multiples for export
   for k, v in data_copy.items():
      print(f"Processing {k}: {v}")
      for key, value in v["data"].items():
         if isinstance(value, dict) and 'collection' in value:
            multiples[key] = value
            if popKeys.get(k, None):
               popKeys[k].append(key)
            else:
               popKeys[k] = [key]
   
   print(f"popKeys: {popKeys}")
   #Remove the raw multiples from data_copy
   for k,v in popKeys.items():
      if isinstance(v, list):
         for _ in v:
            print(f"popping {_} from {k}")
            res = data_copy[k]["data"].pop(_, None)
            print(f"popped {res} from {k}")
   print(f"my multiples: {multiples}")
   print(f"data copy mid {data_copy}")

   if multiples:
      for key, raw_multiple in multiples.items():
         print(f"Processing multiple: {key}")
         parent = find_key_by_value(popKeys, key)
         print(f"found {parent} by value {key}")
         for m in raw_multiple["collection"]:
            m = OrderedDict(m)
            m["multi"] = key
            m.move_to_end("multi", last=False)

            #nella gestione dei multipli, aggiungiamo temporaneamente la chiave (nome del multi)
            #poiche' lo stesso elemento può apparire in due multi diversi (i.e. patch ed extrusion in bc-snappy)
            #questo permette invece di avere elementi univoci e di gestirli correttamente 
            element_name = m["name"].replace(" ", "_") + "_" + key  
            data_copy[parent]["data"][element_name] = m
            data_copy[parent]["data"][element_name].pop("name", None)
            print(f"\nadded {element_name} to dataCopy --> {data_copy}\n")

   # ── CAD fields: export STL groups + save session, store path ───────
   import os as _os
   for frame_name, frame_val in data_copy.items():
      for field_name, field_val in list(frame_val.get('data', {}).items()):
         if isinstance(field_val, str) and field_val == '__CAD__':
            # Value was set to '__CAD__' by handle_cad_type on export
            # Already handled — leave as is
            pass

   print(f"data copy after: {data_copy}")
   return data_copy

def _export_cad_fields(folder_path: str):
    """For every type=CAD field in data_instance, export STL groups to
    <folder_path>/attachments/ and embed the full session state (groups,
    colours, transparency, hidden faces, etc.) directly as the text content
    of the CAD element in the output XML — base64-encoded JSON, so there is
    no separate session file on disk to keep track of or lose.

    For type=CADgroups-dropdown, the value is already a plain string
    (the selected group name) so nothing extra is needed.
    """
    import os, json, base64

    # Find any live StepEmbedWidget
    step_widget = None
    try:
        from PySide6.QtWidgets import QApplication
        from step_surface_selector import StepEmbedWidget
        for w in QApplication.allWidgets():
            if isinstance(w, StepEmbedWidget):
                step_widget = w._step
                break
    except Exception:
        pass

    if step_widget is None:
        return
    _probe_on = getattr(step_widget, "_probe_active", False)
    if not step_widget.groups and not _probe_on:
        return

    att_dir = os.path.join(folder_path, 'attachments')
    os.makedirs(att_dir, exist_ok=True)

    # ── Probe point → attachments/probe_point.vtk (if placed) ────────────
    if _probe_on and getattr(step_widget, "_probe_point", None):
        try:
            from step_surface_selector import _write_probe_vtk
            _write_probe_vtk(step_widget._probe_point,
                             os.path.join(att_dir, 'probe_point.vtk'))
        except Exception as e:
            print(f'Probe VTK export failed: {e}')

    # Export STL files for every group (these stay as real files — only the
    # session/group metadata gets embedded into the XML, not the geometry).
    from step_surface_selector import shapes_to_stl
    for group_name, indices in step_widget.groups.items():
        shapes = [step_widget.faces[i] for i in indices]
        safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in group_name)
        stl_path = os.path.join(att_dir, f'{safe}.stl')
        try:
            shapes_to_stl(shapes, stl_path)
        except Exception as e:
            print(f'STL export failed for {group_name}: {e}')

    # Build the session payload — same content the old .sgf file used to hold
    if not step_widget.step_path:
        return

    session = {
        'version': 1,
        'step_path': step_widget.step_path,
        'display_mode': step_widget._display_mode,
        'group_color_idx': step_widget._group_color_idx,
        'group_colors': step_widget._group_colors,
        'group_transparency': step_widget._group_transparency,
        'groups': step_widget.groups,
        'hidden_indices': sorted(step_widget.hidden_indices),
    }

    # Base64-encode the JSON so it's always XML-safe (no quotes, angle
    # brackets, or unicode surprises to worry about inside the text node).
    session_json = json.dumps(session)
    session_b64 = base64.b64encode(session_json.encode('utf-8')).decode('ascii')

    # Store the encoded session directly as the value of every CAD field —
    # this is what create_elements() will write as the element's text content.
    for frame_val in data_instance.all_data.values():
        for field_name in frame_val.get('data', {}):
            if field_name in _CAD_FIELD_REGISTRY:
                frame_val['data'][field_name] = session_b64


def decode_cad_session(encoded_value: str) -> dict:
    """Inverse of the encoding above — decode a CAD field's text content
    back into the session dict (groups, colours, etc.). Used when re-loading
    a saved XML file to restore the STEP session into the embedded CAD tab.
    Returns {} if the value isn't a valid encoded session (e.g. empty field).
    """
    import json, base64
    if not encoded_value:
        return {}
    try:
        raw = base64.b64decode(encoded_value.encode('ascii'))
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return {}


# Registry: (frame_name, field_name) pairs for type=CAD fields
_CAD_FIELD_REGISTRY: set = set()


def _check_cad_requirements() -> list:
    """Return a list of human-readable violation strings for the GEO tab's
    mandatory requirements (probe point / mandatory groups). Empty list means
    everything is satisfied — including the common case where no requirements
    were declared in the setup file at all.
    """
    violations = []
    step_widget = None
    try:
        from PySide6.QtWidgets import QApplication
        from step_surface_selector import StepEmbedWidget
        for w in QApplication.allWidgets():
            if isinstance(w, StepEmbedWidget):
                step_widget = w._step
                break
    except Exception:
        return violations

    if step_widget is None:
        return violations

    if getattr(step_widget, "_probe_required", False):
        if not getattr(step_widget, "_probe_active", False):
            violations.append("• Probe point not placed (use 'Place Probe Point' in the GEO tab)")

    for g in getattr(step_widget, "_mandatory_groups", []):
        indices = step_widget.groups.get(g)
        if indices is None:
            violations.append(f"• Mandatory group '{g}' does not exist")
        elif len(indices) == 0:
            violations.append(f"• Mandatory group '{g}' has no faces assigned")

    return violations


def export_to_xml(XML_filename):

   print( "--------------------------------------------" )

   # ── Block export if GEO-tab requirements aren't satisfied ─────────────
   _violations = _check_cad_requirements()
   if _violations:
      from PySide6.QtWidgets import QMessageBox
      QMessageBox.critical(
         None, "Cannot export — missing requirements",
         "The setup file declares requirements that are not yet met:\n\n"
         + "\n".join(_violations)
      )
      return

   from PySide6.QtWidgets import QFileDialog
   folder_path = QFileDialog.getExistingDirectory(None, "Select folder where the file will be saved")
   if not folder_path:
      print("No folder selected. Exiting.")
      return
   
   # ── Export CAD session files and STL groups ───────────────────────
   _export_cad_fields(folder_path)

   doc = minidom.Document()
   sys_data = doc.createElement("sysData")
   doc.appendChild(sys_data)
   prepared_data = prepare_data(data_instance.all_data)
   print(f"prepared_data:  {prepared_data}")

   def create_elements(parent_element, data):
      """
      Recursively creates XML elements based on the provided data dictionary.

      Args:
         parent_element (xml.dom.minidom.Element): The parent XML element to which the child elements will be added.
         data (dict): The data dictionary containing the key-value pairs to be converted into XML elements.

      Returns:
         None
      """
      print(f"parent_element: {parent_element} ----> {data}")
      if isinstance(data, dict) and data != {}:
         # divide subframes and data
         for key, value in data.items():
            child_element = doc.createElement(key)
            if isinstance(value, (dict)):
               create_elements(child_element, value)
            else:
               child_element.appendChild(doc.createTextNode(str(value)))
            parent_element.appendChild(child_element)

   def unpack_frame_content(name, frame_content, last_created_element, nesting_frame):
      print(f"unpacking {name}, nesting_frame {nesting_frame} -> {frame_content}")
      data_value = frame_content["data"]
      sub_frames = frame_content["sub_frames"]
      last_element = last_created_element

      if name == BASIC_SETTINGS_TAB_NAME:
         print(f"SPECIAL data_valueee: {data_value}")
         # Directly add children of basic_settings to sysData
         create_elements(nesting_frame, data_value)

      else:
         print(f"data_valueee: {data_value}")
         if data_value != {}:
            main_element = doc.createElement(name)
            create_elements(main_element, data_value)
            nesting_frame.appendChild(main_element)
            last_element = main_element

            if sub_frames != {}:
               nesting_frame = last_element

            print(f"value: {data_value} and sub_frames: {sub_frames}")
            rename_multis(data_value, last_element)
            rename_files(data_value, last_element)
         elif data_value == {}:
            print(f"DATA VALUE EMPTY!!{name}" )
         
            main_element = doc.createElement(name)

            if sub_frames == {}:
               main_element.appendChild(doc.createTextNode( ""))

            nesting_frame.appendChild(main_element)
            last_element = main_element

            if sub_frames != {}:
               nesting_frame = last_element

      print(f"starting sub_frames with nesting frame: {nesting_frame}")
      for sub_frame_name, sub_frame_content in sub_frames.items():
         last_element = unpack_frame_content(sub_frame_name, sub_frame_content, last_element, nesting_frame)
      return last_element

   def rename_multis(data_value, last_element):
      for nested_key, nested_value in data_value.items():
         if isinstance(nested_value, dict) and 'multi' in nested_value:
            original_name, main_element_name = rename_multi_no_specifyname(nested_key, nested_value)
            if last_element.nodeName == main_element_name or last_element.nodeName == nested_value["multi"]:
               parent_node = last_element.parentNode
               parent_node.removeChild(last_element)
               last_element = parent_node
            print(f"working on {original_name} -> {main_element_name}")
            print(f"last created element: {last_element}")
            # Check if an element with 'original_name' already exists and delete it for new one
            existing_elements = doc.getElementsByTagName(original_name)
            if existing_elements:
               #remove each element with the same name
               for element in existing_elements:
                  last_element.removeChild(element)

            main_element = doc.createElement(main_element_name)
            create_elements(main_element, nested_value)
            
            print(f"parent node {last_element.nodeName} is different from main element: {main_element.nodeName}")
            last_element.appendChild(main_element)

   def rename_files(data_value, last_element):
      print(f"renaming files with value {data_value}")
      to_remove = []
      for nested_key, nested_value in data_value.items():
         
         if "file" in nested_key and isinstance(nested_value, list):
            #remove the nested_key element
            print(f"popping {nested_key} as it is a list")
            to_remove.append(nested_key)

         elif "file" in nested_key:
            print(f"found file in nested_key: {nested_key} and nested_value: {nested_value} in last_element: {last_element}")
            # Remove existing elements with the same nested_key
            existing_elements = doc.getElementsByTagName(nested_key)
            for element in existing_elements:
               last_element.removeChild(element)
               element.unlink()  # Ensure the element is properly removed from memory

            file_element = doc.createElement("file")

            file_name_element = doc.createElement("name")
            file_name_element.appendChild(doc.createTextNode(f"{nested_key[5:].strip()}"))

            file_element.appendChild(file_name_element)
            
            if nested_value is not None:
               option_element = doc.createElement("option")
               option_element.appendChild(doc.createTextNode(nested_value))
               file_element.appendChild(option_element)
            else:
               print(f"option is none: {nested_value}")
            last_element.appendChild(file_element)
            print(f"Appended <file> element with value '{nested_value}' to last_element '{last_element.tagName}'")

   last_created_element = sys_data
   for key, value in prepared_data.items():
      last_created_element = unpack_frame_content(key, value, last_created_element, sys_data)
   print(f"it's over, last created element: {last_created_element}")

   print(f"doc before writing: {doc.toprettyxml(indent='  ')}") 
   # Save the XML to a file
   full_file_path = os.path.join(folder_path, XML_filename)
   with open(full_file_path, "w") as xml_file:
      xml_file.write(doc.toprettyxml(indent="  "))

   print(f"Data exported to {XML_filename}")
   return folder_path

def rename_multi_no_specifyname(original_name, multi_object):
   print(f"rename_multi_no_spcifyname {original_name}: {multi_object}")
   base_name = multi_object['multi']
   new_name = original_name
 
   if original_name.startswith(base_name + "_cloudHPC_"): #renaming the _cloudHPC_ suffix
      new_name = base_name
   else:
      #Nella gestione dei multi togliamo la chiave (base_name) che è stata inserita in precedenza
      #new_name = original_name
      new_name = original_name.replace( "_" + base_name , '')
   return original_name, new_name

### IMPORT ###
def load_xml(tk_string_map, frames_map):
   print("############################ START LOAD XML ############################")
   # 1. Prompt the user to choose an XML file
   from PySide6.QtWidgets import QFileDialog
   file_path, _ = QFileDialog.getOpenFileName(
       None, "Select an XML file", "", "XML files (*.xml);;All files (*)"
   )
   if not file_path:
      return  # User canceled the dialog
   
   # 2. Process the XML file and create its representation
   with open(file_path, 'r') as file:
      xml_content = file.read()
   data_instance.all_data = {}
   data_instance.all_data = parse_XML_to_dict(xml_content)
   print("__________ALL DATA AFTER GLOBAL UPDATE_____________")
   print(data_instance.all_data)
   update_fields(tk_string_map, frames_map)

   # 3. Restore any embedded CAD session (groups, colours, hidden faces, ...)
   #    from the base64-encoded JSON stored in each type=CAD field's text.
   _restore_cad_fields()


def _restore_cad_fields():
    """For every type=CAD field that holds an encoded session (i.e. its name
    is in _CAD_FIELD_REGISTRY), decode it and push the saved groups/colours/
    etc. into the live StepEmbedWidget — re-opening the STEP file first if
    it isn't already loaded there.
    """
    step_widget = None
    try:
        from PySide6.QtWidgets import QApplication
        from step_surface_selector import StepEmbedWidget, occ_color
        for w in QApplication.allWidgets():
            if isinstance(w, StepEmbedWidget):
                step_widget = w._step
                break
    except Exception:
        return

    if step_widget is None:
        return

    encoded = None
    for frame_val in data_instance.all_data.values():
        for field_name, field_val in frame_val.get('data', {}).items():
            if field_name in _CAD_FIELD_REGISTRY and isinstance(field_val, str) and field_val:
                encoded = field_val
                break
        if encoded:
            break

    if not encoded:
        return

    session = decode_cad_session(encoded)
    if not session:
        return

    step_path = session.get('step_path')
    if step_path and step_path != step_widget.step_path:
        if os.path.isfile(step_path):
            step_widget._open_file(step_path)
        else:
            print(f"Saved STEP path not found, cannot auto-restore: {step_path}")
            return

    # Restore display mode
    step_widget._display_mode = session.get('display_mode', step_widget._display_mode)
    step_widget._apply_display_mode_to_all()

    # Restore hidden faces
    hidden = set(session.get('hidden_indices', []))
    ctx = step_widget._display.Context if step_widget._display else None
    if ctx is not None:
        for i in hidden:
            if i < len(step_widget.ais_faces):
                ctx.Erase(step_widget.ais_faces[i], True)
        step_widget.hidden_indices = hidden

    # Restore group colours/transparency, then groups themselves
    step_widget._group_colors = {
        k: tuple(v) for k, v in session.get('group_colors', {}).items()
    }
    step_widget._group_transparency = {
        k: float(v) for k, v in session.get('group_transparency', {}).items()
    }
    step_widget._group_color_idx = session.get('group_color_idx', 0)
    step_widget.groups = {k: list(v) for k, v in session.get('groups', {}).items()}

    if ctx is not None:
        for name, indices in step_widget.groups.items():
            r, g, b = step_widget._group_colors.get(name, (0.7, 0.8, 0.9))
            color = occ_color(r, g, b)
            t = step_widget._group_transparency.get(name, 0.0)
            for i in indices:
                if i < len(step_widget.ais_faces):
                    ctx.SetColor(step_widget.ais_faces[i], color, True)
                    ctx.SetTransparency(step_widget.ais_faces[i], t, True)

    step_widget._refresh_group_tree()
    step_widget.status.showMessage(
        f"Session restored from saved XML — {len(step_widget.groups)} group(s)."
    )

def parse_XML_to_dict(xml_content):
   xmldoc = minidom.parseString(xml_content)
   root = xmldoc.getElementsByTagName('sysData')[0]

   data = {}
   basic_settings = {"sub_frames": {}, "data": {}}

   def parse_node(node, multi_type=False, file_type=False):
      print(f"node {node} is of type {node.nodeType} and has {len(node.childNodes)} children")
      if len(node.childNodes) == 1 and node.firstChild.nodeType == node.TEXT_NODE:
         value = node.firstChild.nodeValue
         print(f"TEXT NODE is: {value}")
         return value
      else:
         if node.nodeName == "file":
            print(f"ITS FILE BABE")
            sub_data = {}
            name_child = None
            d_value_child = None
            for child in node.childNodes:
               if child.nodeType == 1:
                  if child.nodeName == "name":
                     name_child = parse_node(child)
                  elif child.nodeName == "option":
                     d_value_child = parse_node(child)

            sub_data[name_child] = d_value_child
            return sub_data
         elif not multi_type and not file_type:
            print(f"this node {node} is not multi nor file")
            sub_data = {"sub_frames": {}, "data": {}}
            for child in node.childNodes:
               print(f"child: {child} nodeType: {child.nodeType}")
               #check if child is a subframe and doesn't contain "multi"
               if child.nodeType == 1 and any(grandchild.nodeType == 1 for grandchild in child.childNodes) and not any(grandchild.nodeName == "multi" for grandchild in child.childNodes):
                  print(f"child: {child} is a subframe")
                  sub_data["sub_frames"][child.nodeName] = parse_node(child)
               elif child.nodeType == 1:
                  print(f"child: {child} is a data node")
                  sub_data["data"][child.nodeName] = parse_node(child)
            return sub_data
         elif file_type:
            sub_data = {"file": {}}
            for child in node.childNodes:
               print(f"child in file_type is {child} of nodetype: {child.nodeType}")
               if child.nodeType == 1 and child.nodeName == "file":
                  val = parse_node(child)
                  print(f"appending peppo {val} to sub_data")
                  sub_data["file"].update(val)
               elif child.nodeType == 1:
                  print(f"child: {child} is a data node")
                  sub_data[child.nodeName] = parse_node(child) #  attributes the TEXT NODE value
            return sub_data
         else:
            sub_data = {}
            for child in node.childNodes:
               #check if child is a subframe or a data node
               if child.nodeType == 1 :
                  sub_data[child.nodeName] = parse_node(child)
            return sub_data
         

   def is_node_multiple(node):
      # Check if the current node itself is a Layer Node
      if any(child.nodeName == 'multipleID' for child in node.childNodes if child.nodeType == node.ELEMENT_NODE):
         return True
      return False
   
   def is_node_file_type(node):
      # Check if the current node itself is a File Node
      if any(child.nodeName == 'file' for child in node.childNodes if child.nodeType == node.ELEMENT_NODE):
         return True
      return False

   for node in root.childNodes:
      if node.nodeType != 1:  # Skip non-element nodes
         continue
      if is_node_multiple(node):
         parsed_parent_node = parse_node(node, multi_type=True)
         print(f"parsed parent node: {parsed_parent_node}")
         multiple_name = parsed_parent_node["multi"]
         print(f"parsed parent name is {node.nodeName} and multiple_name is {multiple_name}")
         if node.nodeName == multiple_name:
            #we have a root node with the same name as the multiple --> create the multiple frame in data
            parsed_parent_node["name"] = f"{multiple_name}_cloudHPC_{parsed_parent_node['multipleID']}"
         else:
            parsed_parent_node["name"] = node.nodeName.replace("_", " ")
         if data.get(multiple_name, None) is None:
            data[multiple_name] = {
               "sub_frames": {}, 
               "data": { 
                  multiple_name: {
                     'max_layers': 1, 
                     'selected_layer': 0, 
                     'collection': [parsed_parent_node]
                  }
               }
            }
         else:
            data[multiple_name]["data"][multiple_name]["collection"].append(parsed_parent_node)
            data[multiple_name]["data"][multiple_name]["max_layers"] += 1
      elif is_node_file_type(node):
         print(f"found an attachments node YOLO: {node}")
         parsed_node = parse_node(node, file_type=True)
         print(f"parsed node after file node: {parsed_node}")

         if data.get(node.nodeName, None) is None:
            data[node.nodeName] = {"sub_frames": {}, "data": {}}
         data[node.nodeName]["data"] = parsed_node
         print(f"data after file node: {data}")
      else:
         parsed_node = parse_node(node)
         if not isinstance(parsed_node, dict):
            basic_settings["data"][node.nodeName] = parsed_node
         else:
            data[node.nodeName] = parsed_node
         for child in node.childNodes:
            if child.nodeType == 1 and any(grandchild.nodeType == 1 for grandchild in child.childNodes):  # Node with nested children
               if is_node_multiple(child):
                  parsed_node = parse_node(child, multi_type=True)
                  multiple_name = parsed_node["multi"]
                  print(f"MMMMultiple_name: {multiple_name}")
                  
                  # Check if specifyName is True/False
                  if child.nodeName == multiple_name:
                     # if child.nodeName == multiple_name it means that we are always in "specifyName = False"
                     print(f"child.nodeName {child.nodeName} == multiple_name {multiple_name}")
                     parsed_node["name"] = f"{multiple_name}_cloudHPC_{parsed_node['multipleID']}"
                  else:
                     # if child.nodeName != multiple_name it means that we are always in "specifyName = True"
                     print(f"child.nodeName {child.nodeName} != multiple_name {multiple_name}")
                     #parsed_node["name"] = child.nodeName.replace("_", " ")
                     parsed_node["name"] = child.nodeName
                     
                  print(f"parsed node to insert: {parsed_node}")
                  print(f"partial data is {data}")
                  print(f"acting on node {node.nodeName} with parsed node name: {parsed_node['name']}")
                  print(f"data[node.nodeName]['data']: {data[node.nodeName]['data']}")

                  print(f"data[node.nodeName]['data'].get(parsed_node['name'], None): {data[node.nodeName]['data'].get(parsed_node['name'], None)}")
                  if data[node.nodeName]["data"].get(parsed_node["name"], None) is not None:
                     print(f"Presto Bio PARSED_NODE[NAME]")
                     if data[node.nodeName]["data"][parsed_node["name"]].get("max_layers", None) is None:
                        print(f"Presto Bio POP")
                        data[node.nodeName]["data"].pop(child.nodeName, None)

                  if data[node.nodeName]["data"].get(multiple_name, None) is None or data[node.nodeName]["data"][multiple_name].get("collection", None) is None:
                     print(f"Presto Bio COLLECTION 0 ")
                     data[node.nodeName]["data"][multiple_name] = {
                        'max_layers': 1, 
                        'selected_layer': 0, 
                        'collection': [parsed_node]
                     }
                     print(f"inserted {node.nodeName}:{data[node.nodeName]['data'][multiple_name]} for the first time WOWO")
                     print(f"inserted {node.nodeName}:{data[node.nodeName]['data']} WATCH WOWO")
                  else:
                     print(f"Presto Bio COLLECTION APPEND ")
                     data[node.nodeName]["data"][multiple_name]["collection"].append(parsed_node)
                     data[node.nodeName]["data"][multiple_name]["max_layers"] += 1
                     print(f"{data[node.nodeName]['data'][multiple_name]} already present WOWO")
   
   if basic_settings:
      data[BASIC_SETTINGS_TAB_NAME] = basic_settings

   #check indent 1 multi nodes that may have been removed
   multis = get_multis_by_indent(indent=1)
   for key,value in multis.items():
      if data.get(key, None):
         print(f"found {value} in data {key}")
      else:
         data[key] = {"sub_frames": {}, "data": {
            "max_layers": 0,
            "selected_layer": -1,
            "collection": []
         }}
         print(f"added default Multiple {key} to data {data}")

   #check indent 2 multi nodes that may have been removed
   print("check indent 2 multi nodes that may have been removed")
   multis = get_multis_by_indent(indent=2)
   print(f"data from import: {data}")
   for key,value in multis.items():
      #value is now a list of keywords {"fem_settings": [singleForce, singleLoad, etc.], k2:[v1,v2.etc]}
      if isinstance(value, list) and len(value) > 0:
         for v in value:
            if data.get(key, None):
               print(f"found Key {key} in data")
               if data[key]["data"].get(v, None) is None:
                  print(f"found {v} in data {key}")
                  data[key]["data"][v] = {
                     "max_layers": 0,
                     "selected_layer": -1,
                     "collection": []
                  }
            else:
               if key == v:
                  data[key] = {
                     "sub_frames": {}, 
                     "data": {
                        v: {
                           "max_layers": 0,
                           "selected_layer": -1,
                           "collection": []
                        }
                     }
                  }
               print(f"added default Multiple {v} to data {key}")
   
   print(f"data from import: {data}")

   return data

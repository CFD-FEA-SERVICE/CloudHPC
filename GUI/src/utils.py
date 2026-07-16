from data_singleton import DataSingleton

data_instance = DataSingleton.get_instance()

BASIC_SETTINGS_TAB_NAME = "Basic_Settings"

rm_buttons_map = {}

def get_frame_by_name_recursive(frames_map, frame_name):
    # Check if the frame is directly within the current level of frames_map
    if frame_name in frames_map:
        return frames_map[frame_name]  # Return the entire frame data

    # If the frame is not found at the current level, search within sub_frames recursively
    for sub_frame_key, sub_frame_value in frames_map.items():
        # Make sure we are dealing with a dictionary that may contain 'sub_frames'
        if 'sub_frames' in sub_frame_value and sub_frame_value['sub_frames']:
            frame_data = get_frame_by_name_recursive(sub_frame_value['sub_frames'], frame_name)
            if frame_data is not None:
                return frame_data  # Frame found in nested sub_frames

    return None  # Frame not found at any level


def get_tkstring_by_name_recursive(tk_string_map, target_frame_name, target_var_name):
   for frame_name, frame_content in tk_string_map.items():
      sub_frames = frame_content.get('sub_frames', None)
      data = frame_content.get('data', None)
      if frame_name == target_frame_name:
         if data.get(target_var_name, None):
            return data[target_var_name]
         else:
            if sub_frames:
               tk_string_var = get_tkstring_by_name_recursive(sub_frames, target_frame_name, target_var_name)
               if tk_string_var:
                  return tk_string_var
      else:
         if sub_frames:
            tk_string_var = get_tkstring_by_name_recursive(sub_frames, target_frame_name, target_var_name)
            if tk_string_var:
               return tk_string_var

   # If the function hasn't returned by now, the target wasn't found
   return None


def print_dict(dict):
    for key, value in dict.items():
        print(f"DICT: {key}: {value}")

def print_debug_util():
   print("Data Instance: ", data_instance.all_data)


def change_key(d, old_key, new_key):
   new_dict = {}
   for k, v in d.items():
      if k == old_key:
            new_dict[new_key] = v
      else:
            new_dict[k] = v
   return new_dict     

def add_default_multiples_to_data(frame_name, multiple_name):
   new_layer = dict(data_instance.multiple_struct_blueprint[multiple_name])
   new_layer.pop("xml_fields", None) # Avoid bringing all xml_fields
   multi = {}
   if data_instance.all_data[frame_name]["data"].get(multiple_name, None):
      multi = data_instance.all_data[frame_name]["data"][multiple_name]
   else:
      multi = data_instance.all_data[multiple_name]["data"]
   multi["collection"].append(new_layer)

def convert_string_to_bool(string):
   if "false" in string.lower():
      print(f"converted string to bool {string} : {False}")
      return False
   else:
      print(f"converted string to bool {string} : {True}")
      return True

def identify_multiple(json, multiples, parent, pop_keys):
   for key, value in json.items():
      if 'collection' in key:
         #indent 1 multiples
         if len(json["collection"])>0:
            multiples[parent] = json
         pop_keys[parent] = parent
      if isinstance(value, dict) and 'collection' in value:
         #nested multiples
         if len(value["collection"])>0:
            print(f"Found in key: {key}\nvalue: {value}")
            multiples[key] = value
         if not pop_keys.get(parent, None):
            pop_keys[parent] = []
         pop_keys[parent].append(key)
   return pop_keys

def find_key_by_value(my_dict, search_value):
    for key, value in my_dict.items():
        if isinstance(value, list):
           for v in value:
              if v == search_value:
                 return key
        elif value == search_value:
            return key
    return None  # Return None if the value is not found

def set_multiples_association():
   for key, value in data_instance.all_data.items():
      if isinstance(value["data"], dict) and 'collection' in value["data"]:
         data_instance.multiple_associations[key] = key
         print(f"Added pair {key} : {key}")
      elif isinstance(value["data"], dict):
         data_instance.multiple_associations[key] = []
         for k, v in value["data"].items():
            if isinstance(v, dict) and 'collection' in v:
               data_instance.multiple_associations[key].append(k)
               print(f"Added child pair: {key}\nvalue: {k}")
         if len(data_instance.multiple_associations[key]) == 0 : data_instance.multiple_associations.pop(key)
   print(f"data_instance.multiplesAssociations: {data_instance.multiple_associations}")

def get_multis_by_indent(indent=1):
   multis = {}
   for key, value in data_instance.multiple_associations.items():
      if indent==1:
         if key == value:
            multis[key] = value
      else:
         if key != value:
            multis[key] = value
   print(f"multies comeback indent {indent}: {multis}")
   return multis


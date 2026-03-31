# Utilities for addon's blend data
import bpy
import os

from . import utl_nodes

DATA_FILE_DIR = "data"

# find the root directory of the addon
def __addon_root():
    current_dir = os.path.dirname(__file__)

    # find the root directory of the addon
    while current_dir and not os.path.exists(os.path.join(current_dir, '__init__.py')):
        current_dir = os.path.dirname(current_dir)

        if current_dir == os.path.dirname(current_dir): # reached the root
            print("ERROR: Could not find the root directory of the addon")
            return os.path.dirname(__file__)

    return current_dir


###################################################################
def ensure_addon_data_collection( filename:str, collection_to_load:str ) -> bpy.types.Collection:
    """
    Load a colleciton from file and append to the scene
    If the collection already exists, it will be deleted and replaced
    """

    # delete existing collection
    existing_collection = bpy.data.collections.get(collection_to_load)
    if existing_collection:
        bpy.data.collections.remove(existing_collection, do_unlink=True)

    # load from file
    addon_dir = os.path.join( __addon_root(), DATA_FILE_DIR )
    filepath = os.path.join(addon_dir, filename)
    

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.collections = [name for name in data_from.collections if name == collection_to_load]
        #data_to. = [name for name in data_from.objects if name == dabablock_name]

    loaded = bpy.data.collections.get(collection_to_load)
    if not loaded:
        print("ERROR: Collection not found in data file: " + collection_to_load)
        return None
    
    bpy.context.scene.collection.children.link(loaded)
    return loaded


###################################################################
def ensure_addon_data_object( filename:str, obj_name_to_load:str, load_as:str ) -> bpy.types.Object:
    """
    Load custom data object from addon data blend file, 
    replace if it is already exist while maintianing world matrix

    filename: str - name of the file to load from
    obj_name_to_load: str - name of the object in the file to load
    load_as: str - name of the object to be created in the scene
    """
    # check existing, delete it and save matrix world to replicate
    if load_as in bpy.data.objects:
        obj = bpy.data.objects[load_as]
        mtx = obj.matrix_world
        bpy.data.objects.remove(obj, do_unlink=True)  
    else:
        mtx = None

    # load from file
    addon_dir = os.path.join( __addon_root(), DATA_FILE_DIR )
    filepath = os.path.join(addon_dir, filename)
    
    # check if the file exists
    if not os.path.exists(filepath):
        print("ERROR: File not found: " + filepath)
        return None
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name == obj_name_to_load]

    obj:bpy.types.Object = bpy.data.objects.get(obj_name_to_load)
    obj.name = load_as

    if mtx:
        obj.matrix_world = mtx

    return obj


###################################################################
def ensure_addon_data_node_group( name: str ) -> bpy.types.NodeGroup:
    """
    Load a node group from file and append to the scene
    If the node group already exists, it will be deleted and replaced
    """

    subdir_name = "geometory_nodes"
    filename = name.replace(" ", "_") + ".json"

    # Check file exists
    addon_dir = os.path.join( __addon_root(), DATA_FILE_DIR, subdir_name )
    filepath = os.path.join(addon_dir, filename)
    if not os.path.exists(filepath):
        print("ERROR: File not found: " + filepath)
        return None

    # load from file
    node_tree = utl_nodes.deserialize_node_tree_from_file(filepath)
    
    return node_tree

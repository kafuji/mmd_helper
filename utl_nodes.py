import re
import bpy
import json

################################################################################
# Utilities for serializing and deserializing node trees
################################################################################

def __save_geo_mod_params(ng: bpy.types.NodeTree) -> dict:
    """
    Save Geometory Node Modifier Parameters
    Modifier settings are stored as mod['SCOKET_X'] connnected with 
    interface item.identifier which is volatile when updating
    So we need to store the value with item name and restore it later
    """
    items = ng.interface.items_tree
    value_map = {}

    def __iterate_through_geo_mods(ng:bpy.types.GeometryNodeTree) -> bpy.types.Modifier:
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == ng:
                    yield mod

    for mod in __iterate_through_geo_mods(ng):
        value_map[mod] = {}
        for key,value in mod.items():
            item = next((i for i in items if i.identifier == key), None)
            if not item:
                continue
            value_map[mod] = {item.name: value} # Store value with item name (eg. 'Offset'=0.5)
    
    return value_map

def __restore_geo_mod_params(ng: bpy.types.NodeTree, value_map: dict) -> None:
    # Restore Input Values from saved value map
    items = ng.interface.items_tree
    for mod, kv in value_map.items():
        for key, value in kv.items():
            item = next((i for i in items if i.name == key), None) # Find item with name
            if not item:
                continue
            mod[item.identifier] = value # Set value with item identifier (eg. 'SOCKET_X'=0.5)
    
    return


def convert_to_serializable(obj):
    """
    Convert Blender-specific types to JSON-serializable types.
    
    :param obj: The object to convert.
    :return: JSON-serializable object.
    """
    if hasattr(obj, "__len__") and not isinstance(obj, str):
        return [x for x in obj]
    elif isinstance(obj, (int, float, str, bool)):
        return obj
    elif isinstance(obj, bpy.types.bpy_struct):
        return obj.name
    else:
        return str(obj)  # Fallback for unsupported types


def serialize_node_tree(node_tree:bpy.types.NodeTree, selected_only=False) -> str:
    """
    Serialize the node tree and return a JSON formatted string.
    
    :param node_tree: bpy.types.NodeTree, The node tree to serialize
    :param selected_only: bool, Serialize only selected nodes
    :return: str, JSON formatted string
    """
    data = {
    }


    if not selected_only: # Save entire node tree
        # Serialize Node Tree Properties
        PROP_TO_SAVE = [
            'type',
            'bl_idname',
            'name',
            'description',
            'color_tag',
            'is_modifier',
            'is_tool',
        ]
        for prop_name in PROP_TO_SAVE:
            data[prop_name] = getattr(node_tree, prop_name)

        # Serialise Node Tree Interface Properties
        interface_items = []
        for item in node_tree.interface.items_tree:
            item_data = {}
            PROP_TO_SAVE = [
                'item_type',
                'name',
                'socket_type',
                'in_out',
                'description',
                'default_attribute_name',
                'subtype',
                'default_value',
                'min_value',
                'max_value',
                'hide_value',
                'hide_in_modifier',
                'force_non_field',
                'default_closed',
            ]

            for prop_name in [n for n in item.bl_rna.properties.keys() if n in PROP_TO_SAVE]:
                prop = getattr(item, prop_name, None)
                if prop is not None:
                    item_data[prop_name] = convert_to_serializable(prop)

            interface_items.append(item_data)
        
        data["interface"] = interface_items
    # End if not selected_only

    # Serialize nodes
    data["nodes"] = []
    for node in node_tree.nodes:
        if selected_only and not node.select:
            continue

        node_data = {
            "bl_idname": node.bl_idname,
            "name": node.name,
        }

        _PROP_TO_SKIP = [
            "bl_rna", 
            "rna_type",
            "name",
            "bl_idname",
            "bl_static_type",
            "bl_width_default",
            "bl_width_min",
            "bl_width_max",
            "bl_height_default",
            "bl_height_min",
            "bl_height_max",
            "select",
            "is_active_output",
            "inputs",
            "outputs",
        ]

        # Retrieve node properties
        for prop_name in node.bl_rna.properties.keys():
            if prop_name in _PROP_TO_SKIP:
                continue

            # skip read-only properties
            if node.bl_rna.properties[prop_name].is_readonly:
                continue

            prop = getattr(node, prop_name)
            node_data[prop_name] = convert_to_serializable(prop)


        def retrieve_sockets_data(sockets) -> list:
            sockets_data = []
            for socket in [s for s in sockets if s.name and hasattr(s, 'default_value')]:
                socket_data = {
                    "identifier": socket.identifier,
                    "default_value": convert_to_serializable(socket.default_value),
                }
                sockets_data.append(socket_data)
            return sockets_data

        # Retrieve input sockets data
        node_data["inputs"] = retrieve_sockets_data(node.inputs)

        # Retrieve custom properties
        node_data["properties"] = {}
        for prop_name in node.keys():
            node_data["properties"][prop_name] = convert_to_serializable(node[prop_name])

        data["nodes"].append(node_data)

    # Serialize link data
    data["links"] = []
    for link in node_tree.links:
        if selected_only:
            # If selected_only is enabled, skip links that are not connected to selected nodes
            if not (link.from_node.select and link.to_node.select):
                continue

        # Ensure that both nodes are in the node_id_map
        link_data = {
            "from_node": link.from_node.name,
            "from_socket_id": link.from_socket.identifier,
            "from_socket_name": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket_id": link.to_socket.identifier,
            "to_socket_name": link.to_socket.name,
        }
        data["links"].append(link_data)

    return json.dumps(data, indent=4, ensure_ascii=False)


def deserialize_node_tree_from_json(node_tree: bpy.types.NodeTree, json_data: str) -> None:
    """
    Deserialize the node tree from a JSON formatted string.
    
    :param node_tree: bpy.types.NodeTree, The node tree to deserialize into
    :param data: str, JSON formatted string containing the serialized node tree
    """
    tree_type = json_data.get("type", "")
    if tree_type and tree_type != node_tree.type:
        raise ValueError(f"Node tree type mismatch: '{tree_type}' != '{node_tree.type}'")

    node_map = {}

    # Deserialize Node Tree Properties
    for prop_name, prop_value in json_data.items():
        if prop_name in ["nodes", "links", "interface"]:
            continue
        # Skip read-only properties
        if node_tree.bl_rna.properties[prop_name].is_readonly:
            continue

        try:
            setattr(node_tree, prop_name, prop_value)
        except Exception as e:
            print(f"Failed to set node tree property '{prop_name}': {e}")

    # Deserialize Node Tree Interface Properties
    if "interface" in json_data:

        # Skip if all interface items are present in the node tree
        recreate = False
        if len(node_tree.interface.items_tree) != len(json_data["interface"]):
            recreate = True # Different number of items
        
        for item, data in zip( node_tree.interface.items_tree, json_data["interface"]):
            item_name = data.get("name", "")
            item_in_out = data.get("in_out", "")
            socket_type = data.get("socket_type", "")

            if item.name != item_name or item.in_out != item_in_out or item.socket_type != socket_type:
                recreate = True # Different item type
                break
        
        if recreate:
            mod_value_map = __save_geo_mod_params(node_tree)
            # Clear interface
            node_tree.interface.clear()

            # Create interface items
            for ent in json_data.get("interface", []):
                item_type = ent.get("item_type", "")

                if item_type == 'SOCKET':
                    socket = node_tree.interface.new_socket(
                        name = ent.get("name", ""),
                        description = ent.get("description", ""),
                        socket_type = ent.get("socket_type", ""),
                        in_out = ent.get("in_out", ""),
                    )
                    for prop_name in ent.keys():
                        if prop_name in ["item_type", "name", "socket_type", "in_out", "description"]:
                            continue
                        if not hasattr(socket, prop_name):
                            continue
                        setattr(socket, prop_name, ent[prop_name])

                elif item_type == 'PANEL':
                    panel = node_tree.interface.new_panel(
                        name = ent.get("name", ""),
                        description = ent.get("description", ""),
                        default_closed = ent.get("default_closed", False)
                    )
            
            __restore_geo_mod_params(node_tree, mod_value_map)

    # First, create all nodes without setting 'parent' and 'text'
    for node_data in json_data.get("nodes", []):
        # Delete existing node
        node = node_tree.nodes.get(node_data.get("name", ""))
        if node:
            node_tree.nodes.remove(node)
        try:
            node = node_tree.nodes.new(type=node_data["bl_idname"])
        except Exception as e:
            print(f"Failed to create node '{node_data.get('name', '')}' of type '{node_data.get('bl_idname', '')}': {e}")
            continue

        node.name = node_data.get("name", "")
        node.location = tuple(node_data.get("location", [0.0, 0.0]))

        # Set node properties except 'parent' and 'text'
        for prop_name, prop_value in node_data.items():
            if prop_name in ["bl_idname", "name", "inputs", "outputs", "links", "parent"]:
                continue  # These are handled separately

            # Skip properties not present in node data
            if prop_name not in node.bl_rna.properties.keys():
                continue

            # Skip read-only properties
            if node.bl_rna.properties[prop_name].is_readonly:
                continue

            # NodeTree property
            if prop_name == 'node_tree':
                node.node_tree = bpy.data.node_groups.get(prop_value)
                continue

            # Image property
            if prop_name == 'image':
                node.image = bpy.data.images.get(prop_value)
                continue

            # Object property
            if prop_name == 'object':
                node.object = bpy.data.objects.get(prop_value)
                continue

            # Text property
            if prop_name == 'text':
                node.text = bpy.data.texts.get(prop_value)
                continue

            try:
                setattr(node, prop_name, prop_value)
            except Exception as e:
                print(f"Failed to set property '{prop_name}' on node '{node.name}': {e}")

        # Set custom properties
        for prop_name, prop_value in node_data.get("properties", {}).items():
            try:
                node[prop_name] = prop_value
            except Exception as e:
                print(f"Failed to set custom property '{prop_name}' on node '{node.name}': {e}")

        # Set input socket default values
        for data in node_data.get("inputs", []):
            socket = next((s for s in node.inputs if s.identifier == data.get("identifier", "")), None)
            if not socket:
                continue
            try:
                socket.default_value = data.get("default_value", socket.default_value)
            except TypeError as e: # Some socket types may not support setting default value
                continue


        # Map node name to node object for link creation
        node_map[node.name] = node

    # Second, set 'parent'
    for node_data in json_data.get("nodes", []):
        node = node_map.get(node_data.get("name", ""))
        if not node:
            continue

        # Set 'parent' property if available
        parent_name = node_data.get("parent")
        if parent_name and parent_name != "None":
            parent_node = node_map.get(parent_name)
            if parent_node:
                node.parent = parent_node

        # Set Position (relative to parent)
        if node.parent:
            node.location = tuple(node_data.get("location", [0.0, 0.0]))

    # Now, create links
    for link_data in json_data.get("links", []):
        from_node = link_data.get("from_node", "")
        from_socket_id = link_data.get("from_socket_id", "")
        from_socket_name = link_data.get("from_socket_name", "")
        to_node_name = link_data.get("to_node", "")
        to_socket_id = link_data.get("to_socket_id", "")
        to_socket_name = link_data.get("to_socket_name", "")

        from_node = node_map.get(from_node)
        to_node = node_map.get(to_node_name)

        if not from_node:
            print(f"From node '{from_node}' not found.")
            continue
        if not to_node:
            print(f"To node '{to_node_name}' not found.")
            continue

        # Find sockets, use identifier first then name (Group Input/Output sockets identifier may be change on creation)
        from_socket = next((s for s in from_node.outputs if s.identifier == from_socket_id), None) or from_node.outputs.get(from_socket_name)
        to_socket = next((s for s in to_node.inputs if s.identifier == to_socket_id), None) or to_node.inputs.get(to_socket_name)

        if not from_socket:
            print(f"From socket '{from_socket_id}' on node '{from_node}' not found.")
            continue
        if not to_socket:
            print(f"To socket '{to_socket_name}' on node '{to_node_name}' not found.")
            continue

        try:
            node_tree.links.new(from_socket, to_socket)
        except Exception as e:
            print(f"Failed to create link from '{from_node}.{from_socket_id}' to '{to_node_name}.{to_socket_name}': {e}")
            continue
    
    return


def deserialize_node_tree_from_str(node_tree:bpy.types.NodeTree, data:str) -> None:
    """
    Deserialize the node tree from a JSON formatted string.
    
    :param node_tree: bpy.types.NodeTree, The node tree to deserialize into
    :param data: str, JSON formatted string containing the serialized node tree
    """
    json_data = json.loads(data)
    deserialize_node_tree_from_json(node_tree, json_data)
    return



def deserialize_node_tree_from_file(filepath:str) -> bpy.types.NodeTree:
    """
    Deserialize the node tree from a file. The file should contain a JSON formatted string.
    This function removes the existing node tree and creates a new one.
    
    :param filepath: str, Path to the file containing the serialized node tree
    :param node_tree: bpy.types.NodeTree, The node tree to deserialize into
    """


    with open(filepath, 'r') as file:
        data = file.read()
        json_data = json.loads(data)
        ng_name = json_data.get("name", "")
        type = json_data.get("bl_idname", "")

        ng = bpy.data.node_groups.get(ng_name) or bpy.data.node_groups.new(name=ng_name, type=type)
        deserialize_node_tree_from_json(ng, json_data)

    return ng
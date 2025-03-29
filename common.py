# Common helper functions for the addon
from collections import deque
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Union

import bpy

################################################################################
#
# Context Managers
#
################################################################################

# Internal: Backup and restore basic context
def _get_basic_context_backup() -> dict:
    """Get basic context backup"""
    if not hasattr(bpy.context, 'object'):
        raise ValueError("Invalid context")

    active = bpy.context.object

    ret = {
        "active_obj": active,
        "mode": active.mode,
        "selected_objs": bpy.context.selected_objects[:],
        "objs_in_mode": bpy.context.objects_in_mode[:],
    }
    return ret

def _restore_basic_context( backup: dict ):
    """Restore basic context"""
    last_active = backup["active_obj"]
    last_mode = backup["mode"]
    last_sel = backup["selected_objs"]
    last_objs_in_mode = backup["objs_in_mode"]

    for obj in bpy.context.view_layer.objects:
        if obj in last_objs_in_mode: # Restore objects_in_mode
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
        else:
            obj.select_set(False)
    try:
        bpy.ops.object.mode_set(mode=last_mode)
    except RuntimeError:
        pass

    for obj in last_sel: # Restore selected objects
        obj.select_set(True)

    bpy.context.view_layer.objects.active = last_active



##############################################################
@contextmanager
def save_context( mode:str = None, active_obj:bpy.types.Object = None, selected_objs:List[bpy.types.Object] = None ):
    """
    Context manager to save entire basic context (mode, object selection, active object, objects_in_mode) temporarily
    
    Args:
        mode (str, optional): Mode to set. Defaults to None.
        active_obj (bpy.types.Object, optional): Active object to set. Defaults to None.
        selected_objs (List[bpy.types.Object], optional): Selected objects to set. Defaults to None.
    """

    backup = _get_basic_context_backup()

    if selected_objs:
        for obj in bpy.context.view_layer.objects:
            if obj in selected_objs:
                obj.select_set(True)
            else:
                obj.select_set(False)

    if active_obj:
        bpy.context.view_layer.objects.active = active_obj
        active_obj.select_set(True)

    if mode and bpy.context.object.mode != mode:
        bpy.ops.object.mode_set(mode=mode)

    try:
        yield

    finally:
        _restore_basic_context(backup)


##############################################################
@contextmanager
def save_modifiers_visibility( obj:bpy.types.Object ):
    """Context manager to save modifier visibility temporarily"""
    show_flag = [(mod, mod.show_viewport)  for mod in obj.modifiers]

    try:
        yield

    finally:
        for mod, flag in show_flag:
            mod.show_viewport = flag

##############################################################
@contextmanager
def save_objects_selection( objects:list = None ):
    """Context manager to save object selection temporarily"""
    last_sel = bpy.context.selected_objects
    last_active = bpy.context.object
    if objects:
        for obj in objects:
            obj.select_set(True)

    try:
        yield

    finally:
        for obj in bpy.context.selectable_objects:
            obj.select_set(obj in last_sel)

        bpy.context.view_layer.objects.active = last_active


##############################################################
@contextmanager
def save_active_object( obj:bpy.types.Object = None ):
    """Context manager to save active object temporarily"""
    active = bpy.context.object
    if obj:
        bpy.context.view_layer.objects.active = obj

    try:
        yield
    
    finally:
        bpy.context.view_layer.objects.active = active


##############################################################
@contextmanager
def save_bone_selection( new_selection:list = None ):
    """Context manager to save bone selection temporarily"""
    sel = bpy.context.selected_pose_bones

    if new_selection:
        arm = bone[0].id_data
        for bone in arm.data.bones:
            bone.select = bone in new_selection

    try:
        yield

    finally:
        for bone in sel:
            bone.bone.select = True
        for bone in bpy.context.selected_pose_bones:
            if not bone in sel:
                bone.bone.select = False

##############################################################
@contextmanager
def save_vertex_selection():
    """Context manager to save vertex selection temporarily"""
    objs = bpy.context.objects_in_mode

    # Save selection
    sel = {}
    for obj in [o for o in objs if o.type=='MESH']:
        mesh:bpy.types.Mesh = obj.data
        
        sel[obj.name] = []
        for v in mesh.vertices:
            if v.select:
                sel[obj.name].append(v.index)

    try:
        yield

    finally:
        # Restore selection
        for obj in [o for o in objs if o.type=='MESH']:
            mesh:bpy.types.Mesh = obj.data
            
            for v in mesh.vertices:
                v.select = False
            for i in sel.get(obj.name, []):
                mesh.vertices[i].select = True

##############################################################
@contextmanager
def save_mesh_selection_mode( mode:tuple = None ):
    """Context manager to save mesh_select_mode temporarily"""
    last_mode = bpy.context.tool_settings.mesh_select_mode
    if mode:
        if last_mode != mode:
            bpy.context.tool_settings.mesh_select_mode = mode
    
    try:
        yield

    finally:
        if last_mode != bpy.context.tool_settings.mesh_select_mode:
            bpy.context.tool_settings.mesh_select_mode = last_mode

##############################################################
@contextmanager
def save_paint_mask_mode( mesh:bpy.types.Mesh ):
    """Context manager to save paint mask mode """
    use_paint_mask = mesh.use_paint_mask
    use_paint_mask_vertex = mesh.use_paint_mask_vertex

    try:
        yield

    finally:
        mesh.use_paint_mask = use_paint_mask
        mesh.use_paint_mask_vertex = use_paint_mask_vertex


##############################################################
@contextmanager
def hide_modifiers(obj, filter_func: callable = None):
    """Context manager to hide modifiers temporarily in an object"""
    show_flags = [(mod, mod.show_viewport)  for mod in obj.modifiers]

    filter_func = filter_func or (lambda x: True)
    for mod in [m for m in obj.modifiers if filter_func(m)]:
        mod.show_viewport = False
    try:
        yield
        
    finally:
        for mod, flag in show_flags:
            mod.show_viewport = flag


##############################################################
@contextmanager
def save_shapekeys_state(obj:bpy.types.Object, mute_all:bool = False, reset_values:bool = False):
    """Context manager to save shapekey state temporarily in an object"""
    active_index = obj.active_shape_key_index
    if reset_values:
        obj.active_shape_key_index = 0

    skeys = obj.data.shape_keys
    backup = {}

    if skeys:
        for kb in skeys.key_blocks:
            backup[kb.name] = (kb.value, kb.mute) # uses name as key, for in case of keyblock instance changes
            if mute_all:
                kb.mute = True
            if reset_values:
                kb.value = 0.0

    try:
        yield

    finally:
        for kb_name, value in backup.items(): # check if shape keys still exists
            skeys = obj.data.shape_keys
            if not skeys:
                continue
            kb = obj.data.shape_keys.key_blocks.get(kb_name)
            if not kb:
                #print(f"Shape key {kb_name} not found in {obj.name}")
                continue
            #print(f"Restoring {kb_name} to {value}")
            kb.value, kb.mute = value
        
        obj.active_shape_key_index = active_index



##############################################################
@contextmanager
def _save_layercollections_visibility(layercollections: List[bpy.types.LayerCollection]=None):
    """
    Context manager to save layer collections visibility temporarily

    Args:
        layercollections (List[bpy.types.LayerCollection]): List of layer collections to save visibility.
        If None, all layer collections within active view layer will be used. Defaults to None.

    """
    hide_dict = {}

    layercollections = layercollections or get_layer_collections_recursive(bpy.context.view_layer.layer_collection)

    # for all layer collections recursively
    for layer in layercollections:
        hide_dict[layer] = (layer.exclude, layer.hide_viewport, layer.collection.hide_viewport)

    try:
        yield

    finally:
        # restore layer collections
        for layer, flags in hide_dict.items():
            layer.exclude, layer.hide_viewport, layer.collection.hide_viewport = flags

    return


##############################################################
@contextmanager
def save_objects_visibility(objects:List[bpy.types.Object]=None):
    """
    Context manager to save object and layer collections visibility temporarily

    Args:
        objects (List[bpy.types.Object], optional): List of objects to save visibility.
            If None, bpy.context.scene.objects will be used. Defaults to None.
    """
    hide_dict = {}
    objects = objects or bpy.context.scene.objects

    tgt_lcs:Dict[str, bpy.types.LayerCollection] = {} # {name: layercollection}
    for obj in objects:
        for coll in obj.users_collection:
            if not coll.name in tgt_lcs:
                lc = find_layer_collection_recursive(coll.name, None)
                if lc:
                    tgt_lcs[coll.name] = lc

    with _save_layercollections_visibility(tgt_lcs.values()):
        # gather all objects visibility
        for obj in objects:
            hide_dict[obj] = (obj.hide_viewport, obj.hide_render, obj.hide_get())

        try:
            yield

        finally:
            # restore objects visibility
            for obj, flags in hide_dict.items():
                hide_vewport, hide_render, hide = flags
                if obj.hide_viewport != hide_vewport:
                    obj.hide_viewport = hide_vewport
                if obj.hide_render != hide_render:
                    obj.hide_render = hide_render
                if obj.hide_get() != hide:
                    obj.hide_set(hide)

    return



##############################################################
@contextmanager
def temp_show_objects(objects:List[bpy.types.Object]=None):
    """
    Context manager to temporarily show objects

    Args:
        objects (List[bpy.types.Object], optional): List of objects to show. 
            If None, bpy.context.scene.objects will be used. Defaults to None.
    """

    objects = objects or bpy.context.scene.objects
    with save_objects_visibility(objects):
        show_objects(objects) # This will change layer collections visibility as well

        try:
            yield
        
        finally:
            pass

    return


##############################################################
@contextmanager
def save_pose( armature:bpy.types.Object ):
    """Context manager to save pose temporarily"""
    # Save pose
    mtx_dic = {}
    bone:bpy.types.PoseBone
    for bone in armature.pose.bones:
        mtx_dic[bone] = bone.matrix_basis.copy()

    try:
        yield
    
    finally:
        # Restore pose
        for bone, mtx in mtx_dic.items():
            bone.matrix_basis = mtx


################################################################################
#
# Decorators 
#
################################################################################

##############################################################
def execute_with_mode(mode: str):
    """Decorator to set mode temporarily for excute function"""
    def decorator(func):
        def wrapper(self, context):
            backup = _get_basic_context_backup()
            if mode != context.object.mode:
                bpy.ops.object.mode_set(mode=mode)
            try:
                return func(self, context)
            finally:
                _restore_basic_context(backup)

        return wrapper
    return decorator


################################################################################
#
# Collection and Layer Helpers 
#
################################################################################

##############################################################
def iter_layer_collections_recursive( root:bpy.types.LayerCollection, include_root:bool = True ) -> bpy.types.LayerCollection:
    """Iterate over all layer collections from a root layer collection, recursively"""
    if include_root:
        yield root
    for layer in root.children:
        yield from iter_layer_collections_recursive(layer)

##############################################################
def get_layer_collections_recursive( root:bpy.types.LayerCollection, include_root:bool = True ) -> bpy.types.LayerCollection:
    """Get all layer collections from a root layer collection, recursively"""
    return [layer for layer in iter_layer_collections_recursive(root, include_root) if layer.name != 'Master Collection']

##############################################################
def find_layer_collection_recursive( name:str, root:bpy.types.LayerCollection=None ) -> bpy.types.LayerCollection:
    """ Find a layer collection by given name from given root layer collection, recursively"""
    if root is None:
        root = bpy.context.view_layer.layer_collection

    for layer in iter_layer_collections_recursive(root):
        if layer.name == name:
            return layer

    return None


##############################################################
def ensure_collection( name:str, ensure_visible:bool=True ) -> bpy.types.Collection:
    """
    Ensure a collection with given name exists in the scene
    Get the collection if it exists, otherwise create it
    """
    coll = bpy.data.collections.get( name )
    if not coll:
        coll = bpy.data.collections.new( name )
        bpy.context.scene.collection.children.link(coll)
        coll.hide_render = True # hide collection in render

    if ensure_visible:
        # Show collection
        if coll.hide_viewport:
            coll.hide_viewport = False	

        # Show on LayerColleciton
        lc = find_layer_collection_recursive(coll.name, None )
        if lc:
            lc.hide_viewport = False
            lc.exclude = False

    return coll

##############################################################
def show_object( obj:bpy.types.Object ): 
    """
    Force show object in viewport and layer collection.

    Args:
        obj (bpy.types.Object): Object to show.

    Raises:
        ValueError: If the object is not in any layer collection
    """
    if obj.visible_get(): # already visible, do nothing
        return

    obj.hide_viewport = False
    obj.hide_set(False)

    if obj.visible_get(): # already visible, do nothing
        return

    # still invisible, show on LayerColleciton
    if len(obj.users_collection) == 0:
        return

    lc = find_layer_collection_recursive(obj.users_collection[0].name, None )

    if not lc:
        raise ValueError(f"{__name__}.show_object(): '{obj.name}' is not in any layer collection in current scene")

    # show on LayerColleciton
    lc.exclude = False
    lc.hide_viewport = False
    lc.collection.hide_viewport = False

    return


##############################################################
def show_objects( objs:List[bpy.types.Object]=None ):
    """
    Force show objects in viewport and layer collection

    Args:
        objs (List[bpy.types.Object], optional): List of objects to show.
            If None, bpy.context.selected_objects will be used.
            Defaults to None.
    """

    objs = objs or bpy.context.scene.objects

    for obj in objs:
        show_object(obj)


##############################################################
def redraw_viewport():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


################################################################################
#
# Environment checker 
#
################################################################################


##############################################################
def is_addon_installed(addon_name:str) -> bool:
    """Check if an addon is installed"""
    if addon_name in bpy.context.preferences.addons:
        return True

    ext_name = "bl_ext.blender_org." + addon_name
    if ext_name in bpy.context.preferences.addons:
        return True   

    return False

##############################################################
def is_pose_library_available() -> bool:
    """Check if pose library is available"""
    return 'pose_library' in bpy.types.Object.bl_rna.properties.keys()


################################################################################
#
# Objects Finder 
#
################################################################################

##############################################################
def is_armature( obj:bpy.types.Object ) -> bool:
    """Check if an object is an armature"""
    return obj and obj.pose


##############################################################
def get_model_root( obj:bpy.types.Object ) -> bpy.types.Object:
    """Returns root object (an armature object) of a model"""
    if not obj:
        return None
    
    if obj.pose:
        return obj
    
    arm = obj.find_armature()
    if arm:
        return arm


##############################################################
def list_objects_by_armature(arm: bpy.types.Object, from_objects:List[bpy.types.Object]=None ) -> List[bpy.types.Object]:
    """
    Returns objects bound to given armature

    Args:
        arm (bpy.types.Object): Armature object to search for. Never None.
        from_objects (List[bpy.types.Object], optional): List of objects to search from. 
            If None, bpy.context.scene.objects will be used. Defaults to None.

    Returns:
        List[bpy.types.Object]: List of objects bound to given armature.
    """
    from_objects = from_objects or bpy.context.scene.objects
    return [o for o in from_objects if o.find_armature() is arm]


##############################################################
def iter_objects_by_armature(arm: bpy.types.Object, from_objects:List[bpy.types.Object] ) -> Iterator[bpy.types.Object]:
    """
    Returns objects bound to given armature

    Args:
        arm (bpy.types.Object): Armature object to search for. Never None.
        from_objects (List[bpy.types.Object]): List of objects to search from.

    Returns:
        Iterator[bpy.types.Object]: Iterator of objects bound to given armature.
    """
    from_objects = from_objects or bpy.context.scene.objects
    for o in from_objects:
        if o.find_armature() is arm:
            yield o

##############################################################
def list_objects_by_material(mat:bpy.types.Material, from_objects:List[bpy.types.Object] ) -> List[bpy.types.Object]:
    """
    Returns objects uses given material.

    Args:
    mat (bpy.types.Material): Material to search for.
    from_objects (List[bpy.types.Object]): List of objects to search from.
    
    Returns:
    
    List[bpy.types.Object]: List of objects uses given material.
    """
    from_objects = from_objects or bpy.context.scene.objects
    return [o for o in from_objects if hasattr(o.data, 'materials') and mat.name in o.data.materials]


##############################################################
def list_materials_by_armature(arm:bpy.types.Object) -> List[bpy.types.Material]:
    """Returns materials used by objects bound to given armature"""
    if not arm:
        return []

    mats = set()
    objs = list_objects_by_armature(arm, bpy.data.objects)

    for obj in [o for o in objs if hasattr(o.data, 'materials') and o.data.materials]:
        for mat in obj.data.materials:
            if mat:
                mats.add(mat)

    return list(mats)


##############################################################
def list_target_objects( type_filter: Union[str, callable] = 'MESH', include_hidden:bool = False ) -> List[bpy.types.Object]:
    """
    Returns a list of objects that are selected or visible in the scene.
    It expands to armature objects if any selected objects are armatures.

    Args:
        type_filter (Union[str, callable], optional): Type filter. Defaults to ' MESH'.
            use lambda to filter objects by custom conditions. e.g. lambda obj: hasattr(obj.data, 'materials')

            include_hidden (bool, optional): Include hidden objects. Defaults to False.
    
    Returns:
        List[bpy.types.Object]: List of objects that are selected or visible in the scene.
    """
    objs = bpy.context.selected_objects
    from_objs = bpy.context.scene.objects if include_hidden else bpy.context.visible_objects

    arms = [o for o in objs if o.pose]
    objs += [o for o in from_objs if o not in objs and o.find_armature() in arms]

    if callable(type_filter):
        return [obj for obj in objs if type_filter(obj)]
    elif isinstance(type_filter, str):
        return [obj for obj in objs if obj.type == type_filter]
    else:
        return objs


##############################################################
def set_active_object( obj:bpy.types.Object ):
    """Set Active object"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


##############################################################
def deselect_all_objects( reset_active:bool = False ):
    """Deselect all objects"""
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    
    if reset_active:
        bpy.context.view_layer.objects.active = None
    return


##############################################################
def select_objects( objs:List[bpy.types.Object], active:Optional[bpy.types.Object]=None ):
    """Select objects"""
    for obj in objs:
        obj.select_set(True)
    
    if active:
        bpy.context.view_layer.objects.active = active

##############################################################
def select_single_object( obj:bpy.types.Object ):
    """Select single object"""
    deselect_all_objects()
    set_active_object(obj)


##############################################################
def set_mode( mode:str ):
    """Set mode"""
    if bpy.context.mode != mode:
        bpy.ops.object.mode_set(mode=mode)

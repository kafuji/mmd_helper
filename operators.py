################################################################################
# Custom Operators
################################################################################
import bpy
from bpy.props import *
from .properties import *
import mathutils

from . import mmd_bone_schema as schema

################################################################################
class MH_OT_ApplyMMDBoneMappings(bpy.types.Operator):
    bl_idname = "mmd_helper.apply_mmd_bone_mappings"
    bl_label = "Apply Bone Definitions" 
    bl_description = "Set mmd_bone.name_j and name_e by using mapped definition data"
    bl_options = {"REGISTER","UNDO"}

    # Main function
    def execute(self, context):
        arm = context.object

        for bone in arm.pose.bones:
            schema.apply_bone_map(bone)

        return {"FINISHED"}


################################################################################
class MH_OT_ClearMMDBoneNames(bpy.types.Operator):
    bl_idname = "mmd_helper.clear_mmd_bone"
    bl_label = "Clear mmd_bone.name" 
    bl_description = "Clear mmd_bone.name_j and name_e on selected bones"
    bl_options = {"REGISTER","UNDO"}

    for_all_bones: BoolProperty(
        name='For all bones',
        default=False
    )

    j_or_e: EnumProperty(
        name='Target',
        items=[
            ('NAME_J', 'name_j', 'mmd_bone.name_j (Japanese)'),
            ('NAME_E', 'name_e', 'mmd_bone.name_e (English)'),
        ],
        options = {'ENUM_FLAG'},
        default = {'NAME_J', 'NAME_E'}
    )


    # This Operator is Active,only when armature and meshes are selected
    @classmethod
    def poll(cls, context):
        return context.mode in ('EDIT_ARMATURE', 'POSE')

    def draw(self,context):
        layout=self.layout
        layout.use_property_decorate
        layout.prop(self,'for_all_bones')

    # Main function
    def execute(self, context):
        arm = context.object
        bones = context.selected_pose_bones if arm.mode == 'POSE' else context.selected_bones
        if self.for_all_bones:
            bones = arm.pose.bones

        for bone in bones:
            b = arm.pose.bones[bone.name]
            if 'NAME_J' in self.j_or_e:
                b.mmd_bone.name_j = ''
            if 'NAME_E' in self.j_or_e:
                b.mmd_bone.name_e = ''

        return {"FINISHED"}


################################################################################
# apply mmd_bone.names to actual bone names
class MH_OT_ApplyMMDBoneNames(bpy.types.Operator):
    bl_idname = "mmd_helper.apply_mmd_bone_names"
    bl_label = "Apply mmd_bone.name" 
    bl_description = "Apply mmd_bone.name_j or name_e to actual bone names on active armature (can be restored later)"
    bl_options = {"REGISTER","UNDO"}

    j_or_e: EnumProperty(
        name='Target',
        items=[
            ('NAME_J', 'name_j', 'mmd_bone.name_j (Japanese)'),
            ('NAME_E', 'name_e', 'mmd_bone.name_e (English)'),
        ],
        default = 'NAME_J'
    )

    convert_lr: BoolProperty(
        name='Convert LR Identifiers',
        description="Convert MMD's LR identifier to Blender .L/.R suffixes",
        default=True
    )

    #show options first
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    @classmethod
    def poll(cls, context):
        o = context.object
        if o and o.pose and not o.get('mmd_helper.bone_name_applied'):
            return True

    # Main function
    def execute(self, context):
        arm = context.object
        for bone in arm.pose.bones:
            b = arm.pose.bones[bone.name]
            name = b.mmd_bone.name_j if 'NAME_J' in self.j_or_e else b.mmd_bone.name_e
            if self.convert_lr:
                name = schema.convert_mmd_bone_name_to_blender_friendly(name)

            if name:
                b.mmd_bone['original_name'] = bone.name
                b.name = name
            else:
                print(f"Bone {b.name} has no mmd_bone.name_{self.j_or_e}. Skipping...")

        arm['mmd_helper.bone_name_applied'] = self.j_or_e

        return {"FINISHED"}

################################################################################
class MH_OT_RestoreBoneNames(bpy.types.Operator):
    bl_idname = "mmd_helper.restore_bone_names"
    bl_label = "Restore Bone Names" 
    bl_description = "Restore original bone names using stored original names on active armature"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.object
        if o and o.pose and o.get('mmd_helper.bone_name_applied'):
            return True

        return False

    # Main function
    def execute(self, context):
        arm = context.object
        for bone in arm.pose.bones:
            b = arm.pose.bones[bone.name]
            original_name = b.mmd_bone.get('original_name')
            if original_name:
                b.name = original_name
            else:
                print(f"Bone {b.name} has no original name. Skipping...")
            
        del arm['mmd_helper.bone_name_applied']

        return {"FINISHED"}





from bpy_extras.io_utils import ImportHelper
################################################################################
class MH_OT_LoadMaterialFromCSV(bpy.types.Operator,ImportHelper):
    bl_idname = "mmd_helper.load_material_from_csv"
    bl_label = "Set mmd_material from CSV" 
    bl_description = "Configure mmd_material and material/object sort order within the model from CSV file generated by PMX Editor"
    bl_options = {"REGISTER","UNDO"}

    # TODO: Support for Texture settings (Need to manipulate node tree connected to mmd_shader_dev)

    filename_ext = '.csv'
    filter_glob: StringProperty(
        default='*.csv',
        options={'HIDDEN'}
    )

    update_mmd_material: BoolProperty(
        name='Update MMD Material',
        description='Set mmd_material properties from CSV data',
        default = False,
    )

    update_material_order: BoolProperty(
        name='Update Material Order',
        description='Sort Materials and Objects according to CSV material order',
        default=True,
    )

    join_objects_before_sort: BoolProperty(
        name='Join Objects Before Sort',
        description='Join objects within the model before sorting materials to get perfect order',
        default=False,
    )

    prevent_joining_objects_with_modifiers: BoolProperty(
        name='Prevent Joining Objects with Modifiers',
        description='Prevent joining objects with modifiers(except armature) to avoid data loss',
        default=True,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        mmd_root = helpers.find_mmd_root(obj)
        return mmd_root is not None

    # Main function
    def execute(self, context):
        print("Loading CSV file...")
        obj = context.active_object
        mmd_root = helpers.find_mmd_root(obj)
        arm = helpers.find_armature_within_children(mmd_root)  
        if not arm:
            self.report({'ERROR'}, f'Armature not found in {mmd_root.name}')
            return {'CANCELLED'}

        # filter objects within the model
        objs = helpers.get_objects_by_armature(arm, mmd_root.children_recursive)
        objs = [o for o in objs if hasattr(o.data, 'materials') and len(o.data.materials)] # filter objects with materials
        print(f"Objects: {objs}")

        mat_dic={}
        for obj in objs:
            for mat in obj.data.materials:
                mat_name = mat.mmd_material.name_j if mat.mmd_material.name_j else mat.name
                mat_dic[mat_name] = mat

        print(f"Materials: {mat_dic}")

        mat_list = []

        with open(self.filepath, encoding='utf-8') as fp:
            next(fp) # skip header
            
            for l in fp:
                array = l.split(',')
                if len(array)<31:
                    self.report({'ERROR'}, f'Incompatible CSV file: It seems not generated by PMX Editor')
                    return {'CANCELLED'}

                # retrieve data
                (   _, name_j, name_e, 
                    dif_r, dif_g, dif_b, dif_a,
                    ref_r, ref_g, ref_b, ref_str,
                    amb_r, amb_g, amb_b,
                    doublesided, ground_shadow, self_shadow_map, self_shadow,
                    use_vertex_col, draw_type, 
                    use_edge, edge_size, edge_r, edge_g, edge_b, edge_a,
                    base_tex, sp_tex, sp_mode, toon_tex, memo 
                ) = array
                
                name_j = name_j.strip('"')
                name_e = name_e.strip('"')
                base_tex = base_tex.strip('"')
                sp_tex = sp_tex.strip('"')
                toon_tex = toon_tex.strip('"')
                memo = memo.strip().strip('"') # strip crlf then remove "
                
                mat = mat_dic.get(name_j)
                if not mat:
                    self.report({'WARNING'}, message=f'Material {name_j} not found in target objects')
                    continue

                mat_list.append(mat)

                if self.update_mmd_material:
                    m = mat.mmd_material
                    m.name_e = name_e
                    
                    m['ambient_color'] = (float(amb_r), float(amb_g), float(amb_b))
                    m['diffuse_color'] = (float(dif_r), float(dif_g), float(dif_b))
                    m['alpha'] = float(dif_a)
                    m['specular_color'] = (float(ref_r), float(ref_g), float(ref_b))
                    m['shininess'] = float(ref_str)
                    m['is_double_sided'] = bool(doublesided)
                    m['enabled_drop_shadow'] = bool(ground_shadow)
                    m['enabled_self_shadow_map'] = bool(self_shadow_map)
                    m['enabled_self_shadow'] = bool(self_shadow)
                    m['enabled_toon_edge'] = bool(use_edge)
                    m['edge_color'] = (float(edge_r), float(edge_g), float(edge_b), float(edge_a))
                    m['edge_weight'] = float(edge_size)
                    m['sphere_texture_type'] = sp_mode
                    m.comment = memo
                    self.report({'INFO'}, f'Material {mat.name} mmd_material configured from {self.filepath}')
                
                    if 0: # ignore texture settings, due from shader incompatibility 
                        m.is_shared_toon_texture = len(toon_tex)==10 and toon_tex.startswith('toon0') and toon_tex.endswith('.bmp')
                        
                        if m.is_shared_toon_texture:
                            m.shared_toon_texture = int(toon_tex[4:6])
                            m.toon_texture = ''
                        else:
                            m.toon_texture = toon_tex

        print(f"Materials from CSV: {mat_list}")
        # update material order
        if self.update_material_order:
            # uses mat_list to sort materials on mmd_tools internal collection
            # mmd_tools uses object.material order and object order in bpy.data by using prefix '000' to '999'

            # join objects
            if self.join_objects_before_sort:
                objs_to_join = [o for o in objs if not o.modifiers] if self.prevent_joining_objects_with_modifiers else objs
                objs_not_to_join = [o for o in objs if o not in objs_to_join]

                if len(objs_to_join) > 1:
                    # deselect all
                    bpy.ops.object.select_all(action='DESELECT')
                    # select objects to join
                    for o in objs_to_join:
                        o.select_set(True)
                    # active object
                    bpy.context.view_layer.objects.active = objs_to_join[0]
                    # join
                    bpy.ops.object.join()
                    # update objs
                    objs = [objs_to_join[0]] + objs_not_to_join

            # create material sort order
            mat_order = { mat: i for i, mat in enumerate(mat_list) }
            
            # sort materials
            for obj in objs:
                current_indices = { mat:i for i, mat in enumerate(obj.data.materials) }
                new_order = sorted(current_indices, key=lambda mat: mat_order.get(mat, 999))
                new_indices = { mat:i for i, mat in enumerate(new_order) }
                if(len(obj.data.materials)>2): # if more than 2 materials, then sort
                    for mat,i in new_indices.items():
                        obj.data.materials[i] = mat
                    
                    # update material indices
                    idx_old_to_new = { current_indices[mat]:new_indices[mat] for mat in new_indices }
                    for poly in obj.data.polygons:
                        poly.material_index = idx_old_to_new[poly.material_index]

            # object sorting, use first material to evaluate object index
            import re
            for obj in objs:
                __PREFIX_REGEXP = re.compile(r"(?P<prefix>[0-9A-Z]{3}_)(?P<name>.*)") # 000_ prefix
                try:
                    index = mat_order.get(obj.data.materials[0], 999)
                except IndexError:
                    print(f"Material error: {obj.name}")
                    index = 999

                match = __PREFIX_REGEXP.match(obj.name)
                if match:
                    prefix = match.group('prefix')
                    name = match.group('name')
                else:
                    prefix = ''
                    name = obj.name
                # index to 0~Z (36) base36
                prefix = f"{index:03X}_"
                obj.name = prefix + name

        return {"FINISHED"}







################################################################################
class MH_OT_Clear_MMD_Material_Names(bpy.types.Operator):
    bl_idname = "mmd_helper.clear_mmd_material_names"
    bl_label = "Clear MMD Material Names" 
    bl_description = "Clear MMD material names (j/e) on selected object or character"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    # Main function
    def execute(self, context):
        objs = helpers.get_target_objects(type_filter='MESH')

        for obj in objs:
            for mat in obj.data.materials:
                if not mat:
                    print( f"Material error: {obj.name}" )
                    continue
                mat.mmd_material.name_j = ''
                mat.mmd_material.name_e = ''

        return {'FINISHED'}


################################################################################
class MH_OT_Convert_BoneMorph_To_PoseLib(bpy.types.Operator):
    """Convert Bone Morphs to Pose Library"""
    bl_idname = "mmd_helper.bonemorph_to_poselib"
    bl_label = "BoneMorph -> PoseLib" 
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        return helpers.find_mmd_root(context.active_object)

    # Main function
    def execute(self, context):
        root = helpers.find_mmd_root( context.active_object )
        arm = helpers.find_armature_within_children( root )
        bone_morphs = root.mmd_root.bone_morphs
        poselib_name = arm.name + '_bonemorphs'
        poselib:bpy.types.Action = helpers.ensure_poselib( arm, name=poselib_name )
        # clear pose markers
        for marker in [e for e in poselib.pose_markers]:
            poselib.pose_markers.remove(marker)
        # clear fcurves
        for fcurve in [e for e in poselib.fcurves]:
            poselib.fcurves.remove(fcurve)

        poselib.pose_markers.active_index = 0

        fcurves = poselib.fcurves

        for morph in bone_morphs:
            marker:bpy.types.TimelineMarker = poselib.pose_markers.new( morph.name )
            marker.frame = len( poselib.pose_markers )

            for morph_data in morph.data:
                #print( morph_data.bone )
                #print( morph_data.rotation )
                #print( morph_data.location )

                # get data_path to posebone property
                pb:bpy.types.PoseBone = arm.pose.bones.get( morph_data.bone )
                if pb is None:
                    print(f"Pose Bone '{morph_data.bone}' not found in the armature")

                prop_names = ['rotation', 'location']

                for prop_name in prop_names:
                    values = getattr( morph_data, prop_name )

                    if prop_name == 'rotation':
                        rotation_mode = pb.rotation_mode if pb else 'QUATERNION'
                        if rotation_mode == 'QUATERNION':
                            prop_name = 'rotation_quaternion'
                        elif rotation_mode == 'AXIS_ANGLE':
                            prop_name = 'rotation_axis_angle'
                            values = mathutils.Quaternion(values).to_axis_angle()
                        else:
                            prop_name = 'rotation_euler'
                            values = mathutils.Quaternion(values).to_euler(rotation_mode)

                    data_path = f'pose.bones["{morph_data.bone}"].{prop_name}'

                    # insert keys
                    if hasattr(values, '__len__'):
                        for i, value in enumerate( values ):
                            fc = fcurves.find( data_path, index=i)
                            if fc is None:
                                fc = fcurves.new( data_path, index=i, action_group = pb.name )
                            fc.keyframe_points.insert(marker.frame, value)

        return {'FINISHED'}

################################################################################
class MH_OT_Convert_PoseLib_To_BoneMorph(bpy.types.Operator):
    """Convert Pose Library to Bone Morphs"""
    bl_idname = "mmd_helper.poselib_to_bonemorph"
    bl_label = "PoseLib -> BoneMorph" 
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        return helpers.is_armature(context.active_object)

    # Main function
    def execute(self, context):
        return {'FINISHED'}

################################################################################
class MH_OT_Export_PoseLib_To_CSV(bpy.types.Operator):
    """Export Pose Library to CSV file"""
    bl_idname = "mmd_helper.poselib_to_csv"
    bl_label = "PoseLib -> CSV" 
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        return helpers.is_armature(context.active_object)

    # Main function
    def execute(self, context):
        return {'FINISHED'}





# register & unregister
import inspect,sys

def register():
    ops = [c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass) if "_OT_" in c[0]]
    for c in ops:
        bpy.utils.register_class(c)

def unregister():
    ops = [c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass) if "_OT_" in c[0]]
    for c in ops:
        bpy.utils.unregister_class(c)

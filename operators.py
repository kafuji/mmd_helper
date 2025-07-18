################################################################################
# Custom Operators
################################################################################
from typing import Tuple
import bpy
from bpy.props import *
from .properties import *
import mathutils
import math
import os
import re

from bpy_extras.io_utils import ImportHelper, ExportHelper

from . import mmd_bone_schema


# ０１２３４５６７８９ -> 0123456789
to_ascii_num = str.maketrans(
    "０１２３４５６７８９",
    "0123456789"
)

# "bone_name.L.001" -> ("bone_name", "L", "001")
def split_bone_name(name: str) -> Tuple[str, str, str]:
    """ Split bone name and returns (basename, lr_suffix, number_suffix) """
    match = re.match(r"([^\.]+)(?:\.(L|R))?(?:\.(\d+))?$", name)

    if not match:
        raise ValueError(f"Unexpected bone name format: {name}")

    basename = match.group(1)
    lr_suffix = match.group(2) if match.group(2) else ""
    number_suffix = match.group(3) if match.group(3) else ""
    return basename, lr_suffix, number_suffix

# "腕捩1" -> ("腕捩", "1") / "親指０" -> ("親指", "０")
def split_by_trailing_number(text: str) -> Tuple[str, str]:
    """
    Split a string into a base part and a trailing number part.
    The trailing number can be either half-width (0-9) or full-width (０-９) digits.
    """
    match = re.match(r"(.*?)([0-9０-９]+)$", text)

    if match:
        return match.group(1), match.group(2)
    else:
        return text, ""


#################################################################################
class MH_OT_auto_set_mappings(bpy.types.Operator):
    bl_idname = "mmd_helper.auto_set_mappings"
    bl_label = "Auto Set Bone Mappings"
    bl_description = "Automatically set bone mappings based on predefined rules"
    bl_options = {"REGISTER", "UNDO"}

    set_by: EnumProperty(
        name="Set by",
        items=[
            ("BONE_NAME_JP", "Actual Bone Name (JP)", "Set mappings by actual blender bone name. Expecting japanese names. e.g.'腕.L'"),
            ("BONE_NAME_EN", "Actual Bone Name (EN)", "Set mappings by actual blender bone name. Expecting english names. e.g.'Arm.L'"),
            ("MMD_NAME", "MMD Bone Name", "Set mappings by mmd_bone.name_j. Use it for models imported by mmd_tools"),
            # ("STRUCTURE", "Bone Structure", "Estimate mappings by bone structure"),
        ],
        default="BONE_NAME_JP",
    )

    # Show options first
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    # Main function
    def execute(self, context):
        arm = context.object
        schema: mmd_bone_schema.MH_PG_MMDBoneSchema = arm.mmd_bone_schema
        name_j_id_map = { name_j:id for id, name_j, _, _, _ in schema.enum_bone_definitions() }
        name_e_id_map = { name_e:id for id, _, name_e, _, _ in schema.enum_bone_definitions() }

        for pbone in arm.pose.bones:
            if self.set_by == "BONE_NAME_JP":
                base_name, lr_suffix, number_suffix = split_bone_name(pbone.name) # "人指０.L" -> ("人指０", "L", "")

                # Split by trailing number
                if base_name != "上半身2":
                    base_name, trail_number = split_by_trailing_number(base_name) # "人指０" -> ("人指", "０")

                if base_name not in name_j_id_map:
                    continue

                bone_id = name_j_id_map[base_name]

                if "指" in base_name: # Finger bone specail case: Should set id on very first bone of the finger
                    # Check if parent bone is not a finger bone (should be hand bone)
                    if pbone.parent and '指' not in pbone.parent.name:
                        pbone.mmd_bone_map = bone_id
                else: # Normal bone
                    pbone.mmd_bone_map = bone_id
                    pbone.mmd_bone_suffix = trail_number

            if self.set_by == "BONE_NAME_EN":
                base_name, lr_suffix, number_suffix = split_bone_name(pbone.name.lower())
                # Split by trailing number
                if base_name != "upper body 2": # Originally contains "2" in the name
                    base_name, trail_number = split_by_trailing_number(base_name)

                if base_name not in name_e_id_map:
                    continue

                bone_id = name_e_id_map[base_name]

                def is_finger(name: str) -> bool:
                    return name.startswith("f_") or name in ("thumb", "index", "middle", "ring", "little")

                if is_finger(base_name):
                    if pbone.parent and not is_finger(pbone.parent.name):
                        pbone.mmd_bone_map = bone_id
                else: # Normal bone
                    pbone.mmd_bone_map = bone_id
                    pbone.mmd_bone_suffix = trail_number

            if self.set_by == "MMD_NAME":
                def remove_sayu_prefix(name: str) -> str:
                    """ Remove '左' or '右' prefix from the name """
                    if name.startswith('左'):
                        return name[1:]
                    elif name.startswith('右'):
                        return name[1:]
                    return name
                
                if not pbone.mmd_bone.name_j:
                    continue

                name_j = remove_sayu_prefix(pbone.mmd_bone.name_j) # "左腕" -> "腕"
                if name_j != "上半身2":
                    name_j, trail_number = split_by_trailing_number(name_j) # "腕捩1" -> ("腕捩", "1")

                if name_j not in name_j_id_map:
                    continue
                bone_id = name_j_id_map[name_j]
                if '指' in name_j:
                    if pbone.parent and '指' not in pbone.parent.mmd_bone.name_j:
                        pbone.mmd_bone_map = bone_id
                else: # Normal bone
                    pbone.mmd_bone_map = bone_id
                    pbone.mmd_bone_suffix = trail_number

        return {"FINISHED"}




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
            mmd_bone_schema.apply_bone_map(bone)

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
                name = helpers.convert_mmd_bone_name_to_blender_friendly(name)

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


################################################################################
class MH_OT_LoadBoneSettingsFromCSV(bpy.types.Operator,ImportHelper):
    bl_idname = "mmd_helper.load_bone_settings_from_csv"
    bl_label = "Set mmd_bone from CSV" 
    bl_description = "Configure mmd_bone properties from CSV data. Also creates mmd_bone_order_override object to sort bones in mmd_tools"
    bl_options = {"REGISTER","UNDO"}

    filename_ext = '.csv'
    filter_glob: StringProperty(
        default='*.csv',
        options={'HIDDEN'}
    )

    update_mmd_bone: BoolProperty(
        name='Update MMD Bone',
        description='Set mmd_bone properties from CSV data',
        default = False,
    )

    update_bone_order: BoolProperty(
        name='Update MMD Bone Order',
        description="Sort MMD Bones according to CSV bone order. It creates representative object [armature_name + '_bone_order'] to keep bone order for mmd_tools",
        default=True,
    )

    @classmethod
    def poll(cls, context:bpy.types.Context):
        if context.mode != 'OBJECT':
            return False
        obj = context.active_object
        if not obj or not obj.pose: # requires armature is active
            return False
        mmd_root = helpers.find_mmd_root(obj) # should have mmd_root
        return mmd_root is not None

    # Main function
    def execute(self, context: bpy.types.Context | None):
        # print("Loading CSV file...")
        arm = context.active_object
        mmd_root = helpers.find_mmd_root(arm)
        bones = arm.pose.bones

        # PmxBone,ボーン名,ボーン名(英),変形階層,物理後(0/1),位置_x,位置_y,位置_z,回転(0/1),移動(0/1),IK(0/1),表示(0/1),操作(0/1),  
        # 親ボーン名,表示先(0:オフセット/1:ボーン),表示先ボーン名,表示先オフセット_x,表示先オフセット_y,表示先オフセット_z,
        # ローカル付与(0/1),回転付与(0/1),移動付与(0/1),付与率,付与親名,軸制限(0/1),制限軸_x,制限軸_y,制限軸_z,
        # ローカル軸(0/1),ローカルX軸_x,ローカルX軸_y,ローカルX軸_z,ローカルZ軸_x,ローカルZ軸_y,ローカルZ軸_z,
        # 外部親(0/1),外部親Key,IKTarget名,IKLoop,IK単位角[deg]

        # PmxIKLink,親ボーン名,Linkボーン名,角度制限(0/1),XL[deg],XH[deg],YL[deg],YH[deg],ZL[deg],ZH[deg]

        def create_lookup_table_by_name_j(bones):
            lookup = {}
            for b in bones:
                name_j = b.mmd_bone.name_j
                if name_j:
                    if name_j in lookup:
                        self.report({'WARNING'}, f'Duplicated name_j: {name_j}, bone: {b.name} and {lookup[name_j].name}')
                        continue
                    lookup[name_j] = b
            return lookup

        name_j_lookup = create_lookup_table_by_name_j(bones)
        csv_bones = []

        try:
            with open(self.filepath, encoding='utf-8') as fp:
                next(fp) # skip header
                for i, l in enumerate(fp):
                    array = l.split(',')

                    if array[0] == 'PmxBone':
                        if len(array)<31:
                            self.report({'WARNING'}, f'Missing data in line {i+1}. Skipping...')
                            continue

                        # retrieve data
                        (   header, name_j, name_e, 
                            def_layer, after_phys, pos_x, pos_y, pos_z, can_rot, can_move, has_ik, is_visible, is_operable,
                            parent_name, dest_type, dest_name, dest_offset_x, dest_offset_y, dest_offset_z,
                            is_loal_add, has_addrot, has_addloc, add_rate, add_src_name, has_fixed_axis, fixed_axis_x, fixed_axis_y, fixed_axis_z,
                            has_local_axes, local_x_x, local_x_y, local_x_z, local_z_x, local_z_y, local_z_z,
                            has_ext_parent, ext_parent_key, ik_target_name, ik_loop, ik_unit_angle
                        ) = array
                    
                    elif array[0] == 'PmxIKLink':
                        if len(array)<10:
                            self.report({'WARNING'}, f'Missing data in line {i+1}. Skipping...')
                            continue

                        # retrieve data
                        (   header, parent_name, link_bone_name, has_angle_limit, xl, xh, yl, yh, zl, zh
                        ) = array
                    else:
                        if array[0].startswith(';'): # comment
                            continue
                        else:
                            self.report({'WARNING'}, f'Unknown data in line {i+1}. Skipping...')
                            continue


                    name_j = name_j.strip('"') # uses only name_j as key

                    # find bone by name_j
                    bone = bones.get(name_j)
                    if not bone: # try to find by name_j
                        bone = name_j_lookup.get(name_j)
                    
                    if not bone:
                        self.report({'WARNING'}, message=f'Bone {name_j} not found in armature')
                        continue

                    # use it later for bone order
                    csv_bones.append(bone)

                    if self.update_mmd_bone:
                        helpers.ensure_mmd_bone_id(bone)
                        m = bone.mmd_bone
                        m.name_e = name_e.strip('"')

                        strbool = lambda s: s!='0'
                        def rad(deg):
                            return math.radians(float(deg))

                        if header == 'PmxBone':
                            m.transform_order = int(def_layer)
                            m.is_controllable = strbool(is_operable)
                            m.transform_after_dynamics = strbool(after_phys)

                            m.enabled_fixed_axis = strbool(has_fixed_axis)
                            m.fixed_axis = (float(fixed_axis_x), float(fixed_axis_y), float(fixed_axis_z))
                            m.enabled_local_axes = strbool(has_local_axes)
                            m.local_axis_x = (float(local_x_x), float(local_x_y), float(local_x_z))
                            m.local_axis_z = (float(local_z_x), float(local_z_y), float(local_z_z))

                            m.has_additional_rotation = strbool(has_addrot)
                            m.has_additional_location = strbool(has_addloc)

                            add_src_name = add_src_name.strip('"')
                            tgt_bone = name_j_lookup.get(add_src_name)
                            if add_src_name and not tgt_bone:
                                self.report({'WARNING'}, f'Copy parent bone {add_src_name} not found in armature')

                            m.additional_transform_bone = tgt_bone.name if tgt_bone else ''
                            # m.additional_transform_bone_id = helpers.ensure_mmd_bone_id(tgt_bone) if tgt_bone else -1 # mmd tools automatically sets bone_id

                            m.additional_transform_influence = float(add_rate)
                            m.ik_rotation_constraint = rad(ik_unit_angle)
                        
                        if header == 'PmxIKLink':
                            pass # mmd_tools uses actual Ik contstraints to handle IK links. We don't want to mess with it

                # end for loop of lines
            # end with open
        except Exception as e:
            self.report({'ERROR'}, f'Error reading CSV file: {e}')
            if e == UnicodeDecodeError:
                self.report({'ERROR'}, f'Check if the file is in UTF-8 encoding')
            return {'CANCELLED'}

        # update bone order
        if self.update_bone_order:
            # create representative object that contains all bones vertex groups. The order of vertex groups is used by mmd_tools to sort bones when exporting
            # claude!
            ob_name = arm.name + '_bone_order'
            if ob_name in bpy.data.objects: # remove old object
                bpy.data.objects.remove( bpy.data.objects[ob_name], do_unlink=True )

            temp_mesh = bpy.data.meshes.new( ob_name )
            temp_ob = bpy.data.objects.new( ob_name, temp_mesh )
            colle = arm.users_collection[0]
            colle.objects.link( temp_ob )
            temp_ob.parent = arm

            # Add armature modifier 'mmd_bone_order_override' to the mesh. mmd_tools uses this modifier to read vertex group order
            mod = temp_ob.modifiers.new( name='mmd_bone_order_override', type='ARMATURE' )
            mod.object = arm

            # set vertex groups along with CSV bone order
            for i, bone in enumerate(csv_bones):
                temp_ob.vertex_groups.new( name=bone.name )
            
            # remove 'mmd_bone_order_override' from other objects within the model, to prevent mmd_tools from using wrong object to read bone order
            target_objs = set(arm.children_recursive)
            target_objs |= set([o for o in bpy.data.objects if o.find_armature() == arm]) # include armture bound objects

            for obj in [o for o in arm.children_recursive if o.type=='MESH']:
                if obj == temp_ob:
                    continue

                mod = obj.modifiers.get('mmd_bone_order_override')
                if mod:
                    mod.name = mod.name + '_old'

        return {"FINISHED"}

################################################################################
class MH_OT_SendBonesToClipboard(bpy.types.Operator):
    bl_idname = "mmd_helper.send_bones_to_clipboard"
    bl_label = "Send Bones to Clipboard"
    bl_description = "Send selected bones data to clipboard as CSV format. If no bones selected, all bones will be sent"
    bl_options = {"REGISTER","UNDO"}

    scale: FloatProperty(
        name='Scale',
        description='Scale factor for converting bone positions to MMD space',
        default=12.5,
        min=0.01, max=100.0, subtype='FACTOR',
    )

    use_pose: BoolProperty(
        name='Use Pose Position',
        description='Use pose position instead of rest position',
        default=False,
    )


    # 'Position', 'Setting', 'Parent', 'Display', 'Add_Deform', 'Fixed_Axis', 'Local_Axis', 'IK'
    categories: EnumProperty(
        name='Categories',
        description='Select categories to include (shift+click to select multiple)',
        items=[
            ('POSITION', 'Position', "Bone Position", 1),
            ('SETTING', 'Basic Settings', "Flags for Can Rotation, Can Move, Is Visible, Is Controllable", 2),
            ('PARENT', 'Parent Bone', "Parent bone", 4),
            ('DISPLAY', 'Display', "Bone tail display type, to bone name, or offset values", 8),
            ('ADD_DEFORM', 'Add Deform', "Add Rotation and Add Location setitngs", 16),
            ('FIXED_AXIS', 'Fixed Axis', "Fixed Axis settings", 32),
            ('LOCAL_AXIS', 'Local Axis', "Local Axis settings", 64),
            ('IK', 'IK', "IK settings", 128),
        ],
        options={'ENUM_FLAG'},
        default={'POSITION','DISPLAY'}
    )



    @classmethod
    def poll(cls, context):
        return context.mode in ('OBJECT', 'POSE')

    # Main function
    def execute(self, context):
        arm = context.object
        bones = context.selected_pose_bones if context.selected_pose_bones else arm.pose.bones
        mmd_root = helpers.find_mmd_root(arm)

        if not mmd_root:
            self.report({'ERROR'}, 'mmd_root not found in the model')
            return {'CANCELLED'}
        
        # create CSV data
        lines = []
        for bone in bones:
            pmxbone = helpers.PmxBoneData(scale=self.scale)
            categories = [c for c in self.categories]
            pmxbone.from_bone(bone, categories, use_pose=self.use_pose)
            lines.append( (bone, str(pmxbone) + '\n'))

        # use bone_sort_order to sort bones
        rep_obj = None
        for obj in arm.children:
            if obj.type == 'MESH' and obj.modifiers.get('mmd_bone_order_override'):
                rep_obj = obj
                break
        
        if rep_obj:
            vgs = rep_obj.vertex_groups
            bone_order = [vg.name for vg in vgs]
            # sort lines by bone_order
            try:
                lines.sort(key=lambda x: bone_order.index(x[0].name))
            except ValueError:
                self.report({'WARNING'}, "Failed to sort bones by bone_order. Bones will be remain in original order")

        # copy to clipboard
        bpy.context.window_manager.clipboard = ''.join([l[1] for l in lines])

        return {"FINISHED"}


#################################################################################
class MH_OT_GetBonesFromClipboard(bpy.types.Operator):
    bl_idname = "mmd_helper.get_bones_from_clipboard"
    bl_label = "Get Bones from Clipboard"
    bl_description = "Get bone data from clipboard as CSV format. It will create new bones or update existing bones"
    bl_options = {"REGISTER","UNDO"}

    scale: FloatProperty(
        name='Scale',
        description='Scale factor for converting bone positions to MMD space',
        default=12.5,
        min=0.01, max=100.0, subtype='FACTOR',
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj or not obj.pose: # requires armature is active
            return False
        return context.mode in ('OBJECT', 'POSE', 'EDIT_ARMATURE')

    def execute(self, context):
        arm = context.object

        # get lines from clipboard
        lines = bpy.context.window_manager.clipboard.split('\n')
        if not lines:
            self.report({'ERROR'}, 'Clipboard is empty')
            return {'CANCELLED'}
        
        for line in lines:
            if not line.strip(): # skip empty lines
                continue

            pmxbone = helpers.PmxBoneData(scale=self.scale)
            pmxbone.from_line(line)
            pmxbone.to_bone(arm)

        return {"FINISHED"}


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
        name="Update MMD Material",
        description="Set mmd_material properties from CSV data",
        default = True,
    )

    update_material_order: BoolProperty(
        name="Update Material Order",
        description="Sort Materials and Objects according to CSV material order. Warning: It renames objects by adding prefix such as '001_'",
        default=False,
    )

    join_objects_before_sort: BoolProperty(
        name="Join Objects Before Sort",
        description="Join objects within the model before sorting materials to get perfect order",
        default=False,
    )

    prevent_joining_objects_with_modifiers: BoolProperty(
        name="Prevent Joining Objects with Modifiers",
        description="Prevent joining objects with modifiers(except armature) to avoid data loss",
        default=True,
    )

    def draw(self, context):
        l = self.layout
        l.use_property_decorate
        l.prop(self, 'update_mmd_material')

        l.separator()

        l.label(text="Material Sorter")
        l.prop(self, 'update_material_order')
        col = l.column(align=True)
        col.enabled = self.update_material_order
        col.prop(self, 'join_objects_before_sort')
        col.prop(self, 'prevent_joining_objects_with_modifiers')


    @classmethod
    def poll(cls, context):
        obj = context.active_object
        mmd_root = helpers.find_mmd_root(obj)
        return mmd_root is not None

    # Main function
    def execute(self, context):
        # print("Loading CSV file...")
        obj = context.active_object
        mmd_root = helpers.find_mmd_root(obj)
        arm = helpers.find_armature_within_children(mmd_root)  
        if not arm:
            self.report({'ERROR'}, f'Armature not found in {mmd_root.name}')
            return {'CANCELLED'}

        # filter objects within the model
        objs = helpers.get_objects_by_armature(arm, mmd_root.children_recursive)
        objs = [o for o in objs if hasattr(o.data, 'materials') and len(o.data.materials)] # filter objects with materials
        # print(f"Objects: {objs}")

        mat_dic={}
        mat_owner={} # mat:obj
        for obj in objs:
            for mat in [m for m in obj.data.materials if m]:
                if mat.get('vrt_outline_mat'):   # Skip outline materials
                    continue
                mat_name = mat.mmd_material.name_j if mat.mmd_material.name_j else mat.name
                mat_dic[mat_name] = mat
                mat_owner[mat] = obj

        # print(f"Materials: {mat_dic}")

        mat_list = []

        self.report({'INFO'}, f'Loading materials from {self.filepath}')

        with open(self.filepath, encoding='utf-8') as fp:
            next(fp) # skip header
            for l in fp:
                array = l.split(',')
                if len(array)<31:
                    self.report({'ERROR'}, f'Incompatible CSV file: It seems not generated by PMX Editor')
                    self.report({'ERROR'}, f'Line: {l}')
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
                
                def bl_path(path):
                    return path if os.path.isabs(path) or path.startswith('//') or not path else f"//{path}"

                name_j = name_j.strip('"')
                name_e = name_e.strip('"')
                base_tex = bl_path( base_tex.strip('"') )
                sp_tex = bl_path( sp_tex.strip('"') )
                toon_tex = bl_path( toon_tex.strip('"') )
                memo = memo.strip().strip('"') # strip crlf then remove "
                
                mat = mat_dic.get(name_j)
                if not mat:
                    self.report({'WARNING'}, message=f'Material {name_j} not found in target objects')
                    continue

                mat_list.append(mat)

                if self.update_mmd_material:
                    m = mat.mmd_material
                    m.name_e = name_e

                    # update mmd_material properties. use dict access to avoid calling __setattr__ method (it will modify NodeTree)

                    # set textures
                    helpers.add_mmd_tex(mat, 'mmd_base_tex', base_tex)
                    helpers.add_mmd_tex(mat, 'mmd_sphere_tex', sp_tex)

                    m['is_shared_toon_texture'] = len(toon_tex)==10 and toon_tex.startswith('toon0') and toon_tex.endswith('.bmp')
                    if m.is_shared_toon_texture:
                        m['shared_toon_texture'] = int(toon_tex[4:6])
                        m['toon_texture'] = ''
                    else:
                        m['toon_texture'] = toon_tex

                    strbool = lambda s: s!='0'
                    m['ambient_color'] = (float(amb_r), float(amb_g), float(amb_b))
                    m['diffuse_color'] = (float(dif_r), float(dif_g), float(dif_b))
                    m['alpha'] = float(dif_a)
                    m['specular_color'] = (float(ref_r), float(ref_g), float(ref_b))
                    m['shininess'] = float(ref_str)
                    m['is_double_sided'] = strbool(doublesided)
                    m['enabled_drop_shadow'] = strbool(ground_shadow)
                    m['enabled_self_shadow_map'] = strbool(self_shadow_map)
                    m['enabled_self_shadow'] = strbool(self_shadow)
                    m['enabled_toon_edge'] = strbool(use_edge)
                    m['edge_color'] = (float(edge_r), float(edge_g), float(edge_b), float(edge_a))
                    m['edge_weight'] = float(edge_size)
                    m['sphere_texture_type'] = int(sp_mode) + 1
                    m.comment = memo

        self.report({'INFO'}, f'Materials from CSV: {[m.name for m in mat_list]}')
        not_configured = [m for m in {m for o in objs for m in o.data.materials if m and not m.get('vrt_outline_mat')} if m not in mat_list]
        if not_configured:
            self.report({'WARNING'}, f'Missing in CSV: {[m.name for m in not_configured]}')

        # print(f"Materials from CSV: {mat_list}")
        # update material order
        if self.update_material_order:
            # uses mat_list to sort materials on mmd_tools internal collection
            # mmd_tools uses object.material order and object order in bpy.data by using prefix '000' to '999'

            def check_safe_to_join(obj): # check if object is safe to join
                # check if object has modifiers except armature
                if obj.modifiers:
                    for mod in obj.modifiers:
                        if mod.type != 'ARMATURE':
                            return False
                return True
            

            # join objects
            if self.join_objects_before_sort:
                visible_objs = [o for o in objs if o.visible_get()]
                objs_to_join = [o for o in visible_objs if check_safe_to_join(o)] if self.prevent_joining_objects_with_modifiers else visible_objs
                objs_not_to_join = [o for o in visible_objs if o not in objs_to_join]

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
        # not implemented yet
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
        # not implemented yet
        return {'FINISHED'}


################################################################################
class MH_OT_quick_export_objects(bpy.types.Operator, ExportHelper):
    """Export selected objects to PMX file. Use it for objects which not require complex processing before exporting"""
    bl_idname = "mmd_helper.quick_export_objects"
    bl_label = "Quick Export PMX"
    bl_options = {"REGISTER","UNDO"}

    filename_ext = '.pmx'
    filter_glob: StringProperty(
        default='*.pmx',
        options={'HIDDEN'}
    )

    # Preprocessing

    hide_outline_mods: BoolProperty(
        name="Hide Outline Modifiers",
        description="Temporarily hide outline modifiers while exporting (Outline modifiers: Solifiy with use_flip_normals)",
        default=True
    )

    triangulate: BoolProperty(
        name="Triangulate",
        description="Triangulate meshes before exporting (except objects with traiangulate modifier)",
        default=True
    )

    edge_scale_source: StringProperty(
        name="Edge Scale Source",
        description="Source for edge scale (Vertex Group). If empty, it uses 'mmd_edge_scale' vertex group",
        default=""
    )

    # Patching Properties
    patch_export: BoolProperty(
        name="Patch Export",
        description="Enable patch export. Instead of exporting PMX, it will update existing PMX file with new data",
        default=False
    )

    # # Default options for merging PMX models (from pmxmerge.py)
    # options_default: Dict[str, Set[str]] = {
    #     "append": {'MATERIAL','BONE', 'MORPH', 'PHYSICS', 'DISPLAY'},  # Specify which features in the patch model to append to the base model. Bones and materials are always appended.
    #     "update": {'MAT_GEOM', 'MAT_SETTING', 'BONE_LOC', 'BONE_SETTING', 'MORPH', 'PHYSICS', 'DISPLAY'},  # Specify which features in the base model to update with the patch model
    # }

    append: EnumProperty(
        name="Features to Append",
        description="Select features to append to the existing PMX model",
        items=[
            ('MATERIAL', "Material", "Append new materials (and corresponding mesh data including shape keys)", 1),
            ('BONE', "Bone", "Append new bones", 2 ),
            ('MORPH', "Morph", "Append new morphs", 4),
            ('PHYSICS', "Physics", "Append new physics", 8),
            ('DISPLAY', "Display Slots", "Append new display slots", 16),
        ],
        options={'ENUM_FLAG'},
        default={'MATERIAL'},
    )

    update: EnumProperty(
        name="Features to Update",
        description="Select features to update in the existing PMX model",
        items=[
            ('MAT_GEOM', "Material Geometry", "Update existing materials mesh data (including shape keys)", 1),
            ('MAT_SETTING', "Material Settings", "Update existing material settings", 2),
            ('BONE_LOC', "Bone Location", "Update existing bone locations", 4),
            ('BONE_SETTING', "Bone Settings", "Update existing bone settings", 8),
            ('MORPH', "Morphs", "Update existing morphs", 16),
            ('PHYSICS', "Physics", "Update existing physics", 32),
            ('DISPLAY', "Display Slots", "Update existing display slots", 64),
        ],
        options={'ENUM_FLAG'},
        default={'MAT_GEOM'},
    )

    overwrite: BoolProperty(
        name="Overwrite Existing PMX",
        description="Overwrite the existing PMX file. If disabled, it will create a new file with a 'patched' suffix",
        default=False
    )

    # Internal state
    __mod_show_flags = {}
    __obj_hide_flags = {}
    __temp_mods = []

    __selected_objects = []
    __active_object = None

    def draw(self, context):
        l = self.layout

        l.label(text="* Exports selected objects only *")

        # Preprocess options
        b = l.box()
        b.use_property_split = True
        b.label(text="Preprocess")
        b.prop(self, 'hide_outline_mods')
        b.prop(self, 'triangulate')
        b.prop(self, 'edge_scale_source')

        l.separator()

        # Patching options
        l.prop(self, 'patch_export')
        b = l.box()
        b.enabled = self.patch_export
        b.use_property_split = False
        col = b.column(align=False)
        col.label(text="Append New")
        col.prop(self, 'append')
        col.separator()
        col.label(text="Update Existing")
        col.prop(self, 'update')
        col.separator()
        col.prop(self, 'overwrite')

    @classmethod
    def poll(cls, context:bpy.types.Context):
        obj = context.object
        # find mmd_root
        mmd_root = helpers.find_mmd_root(obj)
        if not mmd_root:
            return False
        
        return obj and obj.type in ('MESH', 'ARMATURE')


    def invoke(self, context, event):
        obj = context.object
        
        if obj.type == 'MESH':
            objs = helpers.get_target_objects(context.selected_objects, type_filter='MESH')
        elif obj.type == 'ARMATURE':
            objs = helpers.get_objects_by_armature(obj, context.visible_objects)
        else:
            self.report({'ERROR'}, "Unsupported object type")
            return {'CANCELLED'}

        # Save selected objects
        self.__selected_objects = context.selected_objects[:]
        self.__active_object = context.active_object

        # print(f"Exporting objects: {[o.name for o in objs]}")

        # add mmd_root and armature to objs
        mmd_root = helpers.find_mmd_root(objs[0])
        arm = helpers.find_armature_within_children(mmd_root)
        objs += [mmd_root, arm]

        # make armature is active
        arm.select_set(True)

        # make other objects invisible (because we use visible_meshes_only option)
        self.__obj_hide_flags = {}
        for o in [o for o in context.visible_objects if o not in objs]:
            self.__obj_hide_flags[o] = o.hide_viewport
            o.hide_viewport = True

        self.__mod_show_flags = {}
        self.__temp_mods = []

        # Process objects
        for o in objs:
            # temporarily hide outline modifiers
            for mod in [m for m in o.modifiers if m.type == 'SOLIDIFY' and m.use_flip_normals]:
                self.__mod_show_flags[mod] = mod.show_viewport
                mod.show_viewport = False
            
            # Temporarily add triangulate modifier to objects which not have it
            if self.triangulate and o.type == 'MESH' and not any([m for m in o.modifiers if m.type == 'TRIANGULATE']):
                mod:bpy.types.TriangulateModifier = o.modifiers.new(name="__triangulate_temp__", type='TRIANGULATE')
                mod.show_viewport = True
                mod.quad_method = 'BEAUTY'
                mod.keep_custom_normals = True
                self.__temp_mods.append(mod)
            
            # convert edge scale VG to mmd_edge_scale
            if self.edge_scale_source and o.type == 'MESH':
                self.report({'INFO'}, f"Converting edge scale from vertex group '{self.edge_scale_source}' to 'mmd_edge_scale' in {o.name}")
                src_vg = o.vertex_groups.get(self.edge_scale_source)
                if not src_vg:
                    self.report({'WARNING'}, f"Vertex group '{self.edge_scale_source}' not found in {o.name}. Skipping...")
                    continue

                mmd_edge_scale = obj.vertex_groups.get('mmd_edge_scale')
                if not mmd_edge_scale:
                    mmd_edge_scale = o.vertex_groups.new(name='mmd_edge_scale')
                
                for v in obj.data.vertices:
                    try:
                        weight = src_vg.weight(v.index)
                    except RuntimeError: # not assigned
                        weight = 0.0

                    mmd_edge_scale.add([v.index], weight, 'REPLACE')

        return super().invoke(context, event)


    def execute(self, context:bpy.types.Context):
        filepath = self.filepath
        # add _patch suffix if patch_export is enabled
        if self.patch_export:
            # self.filepath should point exsting PMX file
            if not os.path.exists(self.filepath):
                self.report({'ERROR'}, f"File {self.filepath} does not exist")
                return {'CANCELLED'}

            filepath = filepath.replace(".pmx", "_patch.pmx")

        # call mmd_tools.export_pmx
        bpy.ops.mmd_tools.export_pmx('EXEC_DEFAULT', filepath=filepath, copy_textures=False, visible_meshes_only=True)
        self.report({'INFO'}, f"PMX file exported to {filepath}")

        # if patch_export is enabled, we need to update existing PMX file
        if self.patch_export:
            # import pmxmerge
            from . import pmxmerge

            # prepare paths
            base_file = self.filepath
            patch_file = filepath
            out_file = base_file if self.overwrite else base_file.replace(".pmx", "_patched.pmx")

            # DEBUG: print options
            print(f"PMX Merge Options: append={self.append}, update={self.update}, base_file={base_file}, patch_file={patch_file}, out_file={out_file}")

            self.report({'INFO'}, f"Merging PMX files: {base_file} + {patch_file} -> {out_file}")

            # merge PMX files
            pmxmerge.merge_pmx_files(
                path_base = base_file,
                path_patch = patch_file,
                path_out = out_file,
                append=self.append,
                update=self.update,
            )

            # remove temporary patch file
            if os.path.exists(patch_file):
                os.remove(patch_file)
            else:
                self.report({'WARNING'}, f"Temporary patch file {patch_file} not found. It may be already removed.")
            
            # Report new file created
            if out_file != base_file:
                self.report({'INFO'}, f"Patched PMX file created: {out_file}")
            else:
                self.report({'INFO'}, f"PMX file patched: {base_file}")
        else:
            # report exported file
            self.report({'INFO'}, f"PMX file exported: {filepath}")


        # remove temporary triangulate modifiers
        for mod in self.__temp_mods:
            mod.id_data.modifiers.remove(mod)

        # restore visibility of modifiers
        mod:bpy.types.Modifier
        for mod, flag in self.__mod_show_flags.items():
            mod.show_viewport = flag
        
        # restore visibility of other objects
        o: bpy.types.Object
        for o, flag in self.__obj_hide_flags.items():
            o.hide_viewport = flag

        # restore selected objects
        for o in context.visible_objects:
            o.select_set( o in self.__selected_objects )
        
        # restore active object
        context.view_layer.objects.active = self.__active_object

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

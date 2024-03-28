################################################################################
# Custom Operators
################################################################################
import copy
import bpy
from bpy.props import *
from bpy.types import Context
from .properties import *
import mathutils
import math
import os


from bpy_extras.io_utils import ImportHelper, ExportHelper


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
    def execute(self, context:bpy.types.Context):
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

    # 'Position', 'Setting', 'Parent', 'Display', 'Add_Deform', 'Fixed_Axis', 'Local_Axis', 'IK'
    categories: EnumProperty(
        name='Categories',
        description='Select categories to include (shift+click to select multiple)',
        items=[ # use tolower() as identifier
            ('POSITION', 'Position', 'Position', 1),
            ('SETTING', 'Setting', 'Setting', 2),
            ('PARENT', 'Parent', 'Parent', 4),
            ('DISPLAY', 'Display', 'Display', 8),
            ('ADD_DEFORM', 'Add Deform', 'Add_Deform', 16),
            ('FIXED_AXIS', 'Fixed Axis', 'Fixed_Axis', 32),
            ('LOCAL_AXIS', 'Local Axis', 'Local_Axis', 64),
            ('IK', 'IK', 'IK', 128),
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
            cats = [c.lower() for c in self.categories]
            pmxbone.from_bone(bone, cats)
            lines.append( (bone, str(pmxbone) + '\n'))

        # use bone_sort_order to sort bones
        rep_obj = None
        for obj in arm.children:
            if obj.type == 'MESH' and obj.modifiers.get('mmd_bone_order_override'):
                rep_obj = obj
                break
        
        # if rep_obj:
        #     vgs = rep_obj.vertex_groups
        #     bone_order = [vg.name for vg in vgs]
        #     # sort lines by bone_order
        #     lines.sort(key=lambda x: bone_order.index(x[0].name))

        # copy to clipboard
        bpy.context.window_manager.clipboard = ''.join([l[1] for l in lines])

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
            for mat in obj.data.materials:
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
        not_configured = [m for m in {m for o in objs for m in o.data.materials} if m not in mat_list]
        if not_configured:
            self.report({'WARNING'}, f'Missing in CSV: {[m.name for m in not_configured]}')

        # print(f"Materials from CSV: {mat_list}")
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
class MH_OT_Quick_Export_Objects(bpy.types.Operator, ExportHelper):
    """Export selected objects to PMX file. Use it for objects which not require complex processing before exporting"""
    bl_idname = "mmd_helper.quick_export_objects"
    bl_label = "Quick Export PMX"
    bl_options = {"REGISTER","UNDO"}

    filename_ext = '.pmx'
    filter_glob: StringProperty(
        default='*.pmx',
        options={'HIDDEN'}
    )

    hide_outline_mods: BoolProperty(
        name="Hide Outline Modifiers",
        description="Temporarily hide outline modifiers while exporting (Outline modifiers: Solifiy with use_flip_normals)",
        default=True
    )

    mod_show_flags = {}
    obj_hide_flags = {}

    @classmethod
    def poll(cls, context:bpy.types.Context):
        obj = context.object
        # find mmd_root
        mmd_root = helpers.find_mmd_root(obj)
        if not mmd_root:
            return False
        
        return obj and obj.type == 'MESH'


    def invoke(self, context, event):
        objs = helpers.get_target_objects(context.selected_objects, type_filter='MESH')

        # print(f"Exporting objects: {[o.name for o in objs]}")

        # add mmd_root and armature to objs
        mmd_root = helpers.find_mmd_root(objs[0])
        arm = helpers.find_armature_within_children(mmd_root)
        objs += [mmd_root, arm]

        # make armature is active
        arm.select_set(True)

        # make other objects invisible (because we use visible_meshes_only option)
        self.obj_hide_flags = {}
        for o in [o for o in context.visible_objects if o not in objs]:
            self.obj_hide_flags[o] = o.hide_viewport
            o.hide_viewport = True

        # temporarily hide outline modifiers
        self.mod_show_flags = {}
        for o in objs:
            for mod in [m for m in o.modifiers if m.type == 'SOLIDIFY' and m.use_flip_normals]:
                self.mod_show_flags[mod] = mod.show_viewport
                mod.show_viewport = False

        return super().invoke(context, event)


    def execute(self, context:bpy.types.Context):
        # call mmd_tools.iexport_pmx
        bpy.ops.mmd_tools.export_pmx('EXEC_DEFAULT', filepath=self.filepath, copy_textures=False, visible_meshes_only=True)

        # restore visibility of modifiers
        mod:bpy.types.Modifier
        for mod, flag in self.mod_show_flags.items():
            mod.show_viewport = flag
        
        # restore visibility of other objects
        o: bpy.types.Object
        for o, flag in self.obj_hide_flags.items():
            o.hide_viewport = flag

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

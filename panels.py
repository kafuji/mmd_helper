################################################################################
# Custom Panels
################################################################################
import bpy

from . import mmd_bone_schema
from . import helpers


# Root Panel
class MH_PT_PMX_ExportHelper(bpy.types.Panel):
	bl_label = "PMX Export Helper"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"

	mmd_tools_module_names = ('mmd_tools', 'bl_ext.blender_org.mmd_tools')

	@classmethod
	def poll(cls, context):
		for name in cls.mmd_tools_module_names:
			if name in bpy.context.preferences.addons:
				return True
		return False

	def draw(self, context):
		l = self.layout
		obj = context.object
		if not obj:
			l.label(text="Select any object that belongs to the model.", icon='ERROR')
			return

		l.label(text=obj.name, icon='ARMATURE_DATA' if obj.type == 'ARMATURE' else 'OBJECT_DATA', translate=False)

		mmd_root = helpers.find_mmd_root(obj)
		if not mmd_root:
			l.label(text="Not a part of a MMD model.", icon='ERROR')
			return
		l.label(text=mmd_root.name, icon='EMPTY_DATA')
		return

# Bone Naming Helper
class MH_PT_BoneNamingHelper(bpy.types.Panel):
	bl_label = "Bone Naming Helper"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_PMX_ExportHelper"

	def draw(self,context):
		return

# Bone Mapping Tool
class MH_PT_BoneMapper(bpy.types.Panel):
	bl_label = "Bone naming by definitions"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_BoneNamingHelper"

	def _draw_bone_mapping_ui(self, context:bpy.types.Context, arm:bpy.types.Object, layout:bpy.types.UILayout):
		props = context.window_manager.mh_props
		schema:mmd_bone_schema.MH_PG_MMDBoneSchema = arm.mmd_bone_schema

		layout.prop(schema, 'additional_definitions_path', text="Extra Bone Defs")

		grid = layout.grid_flow(row_major=True)
		grid.use_property_decorate = True
#		grid.column().prop(props, 'use_english')
		grid.column().prop(props, 'show_suffix')
		grid.column().prop(props, 'show_mmd_bone')
		# grid.column().prop(props, 'max_display')


		bones = None
		if context.mode in ('EDIT_ARMATURE'):
			bones = context.selected_bones
		elif context.mode in ('POSE'):
			bones = context.selected_pose_bones
		
		ui_max_count = props.max_display

		layout.separator()
		if bones is not None and len(bones):
			for i, bone in enumerate(bones):

				if i==ui_max_count:
					box.label(text=f'... and more {len(bones)-ui_max_count} bones...')
					break
				
				pbone = arm.pose.bones.get(bone.name)
				if not pbone:
					continue
				
				box =layout.box()
				row = box.split(align=True)
				row.alert = pbone.mmd_bone_map not in schema.bones
				row.label( text=bone.name, icon='BONE_DATA')
				row.prop_search( pbone, 'mmd_bone_map', schema, 'bones', text="", translate=False)
				
				row.prop( pbone, 'mmd_bone_suffix')
				if props.show_mmd_bone:
					row = box.split(align=True)
					row.prop( pbone.mmd_bone, 'name_j', text='Japanese')
					row.prop( pbone.mmd_bone, 'name_e', text='English')
		else:
			layout.box().label(text='Select any bones')

		# list undefined bones            
		box = layout.box()
		row = box.row()
		row.label(text='Undefined Bones', icon='ERROR')
		row.prop(props, 'alert_only_essentials', toggle=True )

		defined = [b.mmd_bone_map for b in arm.pose.bones if b.mmd_bone_map !='NONE']
		undefined_bones = set(schema.get_bone_id_list(props.alert_only_essentials)) - set(defined)

		if len(undefined_bones):
			grid = box.grid_flow(row_major=True, columns=0,even_columns=False, even_rows=False, align=False)
			grid.alert = True
			for id in undefined_bones:
				bone_data = schema.get_bonedata_by_id(id)
				grid.column().label(
					text = bpy.app.translations.pgettext(bone_data.category) + ': ' + bone_data.name_j, 
					icon='BONE_DATA'
					)
		else:
			box.label(text='All bones are set!', icon='INFO')

		return

	def draw(self, context):
		arm = context.object
		layout = self.layout

		col = layout.column()
		if not arm or not arm.pose:
			col.label(text='Select any armature')
			return

		self._draw_bone_mapping_ui(context, arm, col)
		col.operator('mmd_helper.auto_set_mappings', icon='AUTO')
		col.operator('mmd_helper.apply_mmd_bone_mappings', icon='COPYDOWN')
		col.operator('mmd_helper.clear_mmd_bone', icon='REMOVE')

		col.separator()
		col.label(text="Extra:")
		row = col.row(align=True)
		row.operator('mmd_helper.apply_mmd_bone_names', icon='COPYDOWN')
		row.operator('mmd_helper.restore_bone_names', icon='RECOVER_LAST')

		return


# Adittional Bone definition panel
class MH_PT_AdditoinalPMXBones(bpy.types.Panel):
	bl_label = "Define Additional PMX Bones"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_BoneMapper"

	def draw(self,context):
		# prefs = context.preferences.addons[__package__].preferences
		# layout = self.layout
		# l = layout.column(align=True)
		# l.label(text='Additional PMX bone definitions file:')
		# l.prop(prefs,'user_bones', text='')
		# l = l.row()
		# l.alert = True
		# l.label(text='Please save addon preferenses to keep this!')
		return




################################################################################
class MH_OT_AddNamingRule(bpy.types.Operator):
	bl_idname = "mmd_helper.add_naming_rule"
	bl_label = "Add naming rule" 
	bl_description = "Add new naming rule for naming mmd_bone.name_j"
	bl_options = {"UNDO"}

	# Main function
	def execute(self, context):
		rules = context.scene.mh_naming_rules
		rules.data.add()
		return {"FINISHED"}

################################################################################
class MH_OT_RemoveNamingRule(bpy.types.Operator):
	bl_idname = "mmd_helper.remove_naming_rule"
	bl_label = "Remove naming rule" 
	bl_description = "Remove selected naming rule"
	bl_options = {"UNDO"}

	@classmethod
	def poll(cls, context):
		rules = context.scene.mh_naming_rules
		return len(rules.data) and rules.active_index >= 0 and rules.active_index < len(rules.data)

	# Main function
	def execute(self, context):
		rules = context.scene.mh_naming_rules
		rules.data.remove(rules.active_index)
		rules.active_index = max(rules.active_index-1, 0)
		return {"FINISHED"}

################################################################################
class MH_OT_MoveUpNamingRule(bpy.types.Operator):
	bl_idname = "mmd_helper.move_up_naming_rule"
	bl_label = "Move up" 
	bl_options = {"UNDO"}

	@classmethod
	def poll(cls, context):
		rules = context.scene.mh_naming_rules
		return len(rules.data)>1 and rules.active_index > 0 and rules.active_index < len(rules.data)

	def execute(self, context):
		root = context.scene.mh_naming_rules
		idx = root.active_index
		root.data.move(idx, idx-1)
		root.active_index -= 1
		return {"FINISHED"}

################################################################################
class MH_OT_MoveDownNamingRule(bpy.types.Operator):
	bl_idname = "mmd_helper.move_down_naming_rule"
	bl_label = "Move down" 
	bl_options = {"UNDO"}

	@classmethod
	def poll(cls, context):
		rules = context.scene.mh_naming_rules
		return len(rules.data)>1 and rules.active_index >= 0 and rules.active_index < len(rules.data)-1

	def execute(self, context):
		root = context.scene.mh_naming_rules
		idx = root.active_index
		root.data.move(idx, idx+1)
		root.active_index += 1
		return {"FINISHED"}


from bpy_extras.io_utils import ExportHelper
import json
################################################################################
class MH_OT_SaveNamingRules(bpy.types.Operator, ExportHelper):
	bl_idname = "mmd_helper.save_naming_rules"
	bl_label = "Save naming rules" 
	bl_description = "Save naming rules as json, for reusing in another workspace"
	bl_options = set()

	filename_ext = '.json'
	filter_glob: bpy.props.StringProperty(
		default='*.json',
		options={'HIDDEN'}
	)

	@classmethod
	def poll(self,context):
		rules = context.scene.mh_naming_rules
		return len(rules.data)

	# Main function
	def execute(self, context):
		rules = context.scene.mh_naming_rules
		
		dic = {}
		
		dic['replace_lr'] = rules.replace_lr
		for idx,rule in enumerate(rules.data):
			
			dic[idx] = {}
			dic[idx]['use_regex'] = rule.use_regex
			dic[idx]['search'] = rule.search
			dic[idx]['replace_to'] = rule.replace_to

		with open(self.filepath, 'w', encoding='utf-8') as fp:
			json.dump(dic, fp, indent=4, ensure_ascii=False)
		
		return {"FINISHED"}

from bpy_extras.io_utils import ImportHelper
################################################################################
class MH_OT_LoadNamingRules(bpy.types.Operator, ImportHelper):
	bl_idname = "mmd_helper.load_naming_rules"
	bl_label = "Load naming rules" 
	bl_description = "Load naming rules from a json"
	bl_options = {'REGISTER', 'UNDO'}

	filename_ext = '.json'
	filter_glob: bpy.props.StringProperty(
		default='*.json',
		options={'HIDDEN'}
	)

	# Main function
	def execute(self, context):
		dic = {}        
		with open(self.filepath, 'r', encoding='utf-8') as fp:
			dic = json.load(fp)

		rules = context.scene.mh_naming_rules

		rules.replace_lr = dic.get('replace_lr', True)
		dic.pop('replace_lr')
		for item in dic.values():
			rule = rules.data.add()
			rule.use_regex = item.get('use_regex', False)
			rule.search = item.get('search', '')
			rule.replace_to = item.get('replace_to', '')
		
		return {"FINISHED"}


################################################################################
class MH_OT_ExecuteNamingRule(bpy.types.Operator):
	bl_idname = "mmd_helper.execute_naming_rule"
	bl_label = "Execute naming rules"
	bl_description = "On active armature(Object mode) or selected bones(Pose/Edit mode), execute rules to set mmd_bone.name_j"
	bl_options = {"REGISTER","UNDO"}

	target_all: bpy.props.BoolProperty(
		name='For all bones',
		description='Run this operator for all bones',
		default=False
	)

	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj and obj.pose

	# Main function
	def execute(self, context):
		arm = context.active_object
		if context.mode == 'OBJECT':
			targets = arm.pose.bones
		else:
			targets = context.selected_pose_bones if context.selected_pose_bones else context.selected_editable_bones

		if self.target_all:
			targets =arm.pose.bones
		
		rules = context.scene.mh_naming_rules

		for b in targets:
			pb = arm.pose.bones[b.name]
			if pb.mmd_bone_map != 'NONE':
				continue

			name = b.name

			if rules.replace_lr:
				if helpers.get_lr_from_name(name):
					lr = arm.mmd_bone_schema.get_lr_string(b.name)
					name = lr + helpers.remove_lr_from_name(b.name)
			
			for rule in rules.data:
				if not rule.search:
					continue
				if rule.use_regex:
					continue

				name = name.replace(rule.search, rule.replace_to)
			
			pb.mmd_bone.name_j = name

		return {"FINISHED"}


# UI List Item: Naming Rule
class MH_UL_NamingRules(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row:bpy.types.UILayout = layout.row(align=True)
		row.label(text='', icon='VIEWZOOM')
		row.prop(item,'search', text='')
		row.label(text='', icon='RIGHTARROW')
		row.prop(item,'replace_to', text='')
	
	def draw_filter(self, context, layout):
		return


# Rule based naming tool
class MH_PT_RuleBasedNamingTool(bpy.types.Panel):
	bl_label = "Rule based naming"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_BoneNamingHelper"
	bl_options = {"DEFAULT_CLOSED"}

	def draw(self,context):
		layout = self.layout
		rules = context.scene.mh_naming_rules

		layout.label(text='Naming rules:')
		row = layout.row(align=False)
		row.prop(rules, 'replace_lr')

		row = layout.row()
		row.template_list(
			'MH_UL_NamingRules', '',
			rules, 'data',
			rules, 'active_index',
			rows=6
		)
		col=row.column(align=True)
		col.operator
		col.operator('mmd_helper.add_naming_rule', text='', icon='ADD')
		if len(rules.data):
			col.operator('mmd_helper.remove_naming_rule', text='', icon='REMOVE')
		if len(rules.data)>1:
			col.separator()
			col.operator('mmd_helper.move_up_naming_rule', text='', icon='TRIA_UP')
			col.operator('mmd_helper.move_down_naming_rule', text='', icon='TRIA_DOWN')
		
		col.separator()
		col.operator('mmd_helper.load_naming_rules', text='', icon='FILEBROWSER')
		if len(rules.data):
			col.operator('mmd_helper.save_naming_rules', text='', icon='FILE_TICK')


		if 0:
			for idx, rule in enumerate(rules.data):
				box = layout.column(align=True)
				row=box.row(align=True)
				row.prop(rule, 'search', text='', icon='VIEWZOOM' )
				row.label(text='', icon='RIGHTARROW')
				row.prop(rule, 'replace_to', text='' )
				row.separator()
				row.operator('mmd_helper.remove_naming_rule', text='', icon='REMOVE').idx = idx
				#row = box.row(align=True)
				#row.prop(rule, 'use_regex')

		layout.operator('mmd_helper.execute_naming_rule')
		row=layout.row(align=True)

		return

# Bone sort orrder setting Tool
class MH_PT_BoneSettigsTool(bpy.types.Panel):
	bl_label = "Bone Settings Helper"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_PMX_ExportHelper"

	def draw(self,context):
		l = self.layout
		l.operator('mmd_helper.load_bone_settings_from_csv')
		l.operator('mmd_helper.get_bones_from_clipboard', icon='PASTEDOWN')
		l.operator('mmd_helper.send_bones_to_clipboard', icon='COPYDOWN')
		return


# Material Setting Tool
class MH_PT_MaterialSettingTool(bpy.types.Panel):
	bl_label = "Material Settings Helper"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_PMX_ExportHelper"

	def draw(self,context):
		layout = self.layout
		layout.operator('mmd_helper.load_material_from_csv')
		layout.operator('mmd_helper.clear_mmd_material_names')
		return



# Operator: Click to show owner object
class MH_OT_ShowOwnerObject(bpy.types.Operator):
	bl_idname = "mmd_helper.show_owner_object"
	bl_label = "Show Owner Object"
	bl_description = "Show the object that owns this material"
	bl_options = {"UNDO"}

	mat_name: bpy.props.StringProperty()

	# Main function
	def execute(self, context):
		mat = bpy.data.materials.get(self.mat_name)
		if not mat:
			return {"CANCELLED"}

		for obj in [o for o in context.scene.objects if hasattr(o.data, 'materials')]:
			if mat.name in obj.data.materials:
				# unselect all
				for o in context.selected_objects:
					o.select_set(False)

				obj.select_set(True)
				context.view_layer.objects.active = obj
				obj.active_material_index = obj.data.materials.find(mat.name)
				break
		return {"FINISHED"}


# Material Viewer
class MH_PT_MaterialViewer(bpy.types.Panel):
	bl_label = "Material Viewer"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_MaterialSettingTool"
	bl_options = {"DEFAULT_CLOSED"}

	@classmethod
	def poll(cls, context:bpy.types.Context):
		# requires active object to be armature or mesh
		obj = context.object
		if not obj:
			return False
		return obj.pose or obj.find_armature()

	def draw(self,context):
		layout = self.layout

		layout.prop(context.window_manager, 'mh_material_view_show_invisible', icon='HIDE_OFF' if context.window_manager.mh_material_view_show_invisible else 'HIDE_ON')

		obj = context.object
		if not obj:
			layout.label(text='Select any object that belongs to the model')
			return
		
		if obj.pose:
			arm = obj
		else:
			arm = obj.find_armature()

		show_invisible = context.window_manager.mh_material_view_show_invisible
		if show_invisible:
			target_objs = set([o for o in context.scene.objects if o.find_armature() == arm])
		else:
			target_objs = set([o for o in context.visible_objects if o.find_armature() == arm])
		
		if not target_objs:
			layout.label(text='Select any object that belongs to the model')
			return

		mats = set([m for o in target_objs for m in o.data.materials if not m.get('vrt_outline_mat')])
		if not mats:
			layout.label(text='No materials found')
			return

		row = layout.row(align=True)
		row.alignment = 'LEFT'
		row.label(text="Material", icon='MATERIAL_DATA')
		row.label(text="Count:")
		row.label(text=str(len(mats)))

		for mat in mats:
			mat:bpy.types.Material
			row = layout.row(align=True)
			row.alignment = 'EXPAND'
			
			#row.label(text="", icon_value=mat.preview.icon_id)
			mat.preview_ensure()
			row.operator('mmd_helper.show_owner_object',
				text="",
				icon_value=mat.preview.icon_id
				).mat_name = mat.name
			row.prop(mat, 'name', text="")
			row.separator()
			row.prop(mat.mmd_material, 'name_j', text='Japanese')
			row.separator()
			row.prop(mat.mmd_material, 'name_e', text='English')

		return
	
	def register():
		mh_material_view_show_invisible = bpy.props.BoolProperty(
			name="Show Materials within invisible objects",
			description='Show materials within invisible objects',
			default=False
		)
		bpy.types.WindowManager.mh_material_view_show_invisible = mh_material_view_show_invisible
		pass


class MH_PT_BoneMorphTool(bpy.types.Panel):
	bl_label = "Bone Morph Helper"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_PMX_ExportHelper"

	def draw(self,context):
		layout = self.layout
		layout.operator('mmd_helper.bonemorph_to_poselib')
		layout.operator('mmd_helper.poselib_to_bonemorph')
		layout.operator('mmd_helper.poselib_to_csv')
		return


class MH_PT_MineDetector(bpy.types.Panel):
	bl_label = "Mine Detector"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "MMD"
	bl_parent_id = "MH_PT_PMX_ExportHelper"

	def draw(self,context):
		layout = self.layout

		obj = context.object
		if not obj:
			return
		
		if obj.pose:
			arm = obj
		else:
			arm = obj.find_armature()
		

		layout.label(text='Detects flaws that harms export result', icon='INFO')		

		col = layout.column()
		if not arm:
			col.label(text='Select any object that belongs to the model')
			return

		row = col.row(align=True)
		row.alignment = 'LEFT'
		row.label(text="Armature", icon='ARMATURE_DATA')
		row.label(text=arm.name)	

		box = layout.box()
		col = box.column()

		# check MMD bone name duplication
		col.label(text='MMD Bone Name Collision:', icon='BONE_DATA')

		first_users = {}
		dup_bones = []

		for pbone in (pb for pb in arm.pose.bones if pb.mmd_bone.name_j) :
			name_j = pbone.mmd_bone.name_j

			if name_j in first_users.keys():
				if first_users[name_j] not in dup_bones:
					dup_bones.append(first_users[name_j])
				dup_bones.append(pbone)
			else:
				first_users[name_j] = pbone
		
		if dup_bones:
			for pbone in dup_bones:
				name_j = pbone.mmd_bone.name_j
				col.prop(pbone.mmd_bone, 'name_j', text=pbone.name, icon='ERROR')

			row = col.row(align=True)
			row.alignment = 'RIGHT'			
			row.label(text="Please fix these bone's name_j", icon='ERROR')
		else:
			col.label(text='None', icon='INFO')

		box = layout.box()
		col = box.column()
		col.label(text="MMD Material Name Collision:", icon='MATERIAL_DATA')
		used_names = set()
		mat_dup = list()
		obj_in_model = set( [o for o in bpy.data.objects if o.find_armature() == arm] )

		mats_in_model = set( [m for o in obj_in_model for m in o.data.materials if m is not None] )
		for mat in mats_in_model:
			name = mat.mmd_material.name_j
			if not name:
				continue
			if name in used_names:
				mat_dup.append(name)
			else:
				used_names.add(name)

		if mat_dup:
			for name in mat_dup:
				for mat in mats_in_model:
					if mat.mmd_material.name_j == name:
						col.prop(mat.mmd_material, 'name_j', text=mat.name, icon='ERROR')
		else:
			col.label(text='None', icon='INFO')


		# check object bound to armature is not child of armature
		box = layout.box()
		col = box.column()
		col.label(text="Object not belongs to the model:", icon='OBJECT_DATA')
		obj_not_in_model = list()
		children = list( arm.children_recursive )
		for obj in obj_in_model:
			if obj not in children:
				obj_not_in_model.append(obj)
		
		if obj_not_in_model:
			for obj in obj_not_in_model:
				col.prop(obj, 'parent', text=obj.name, icon='ERROR')
		else:
			col.label(text='None', icon='INFO')


# register & unregister
_panels = [
	MH_PT_PMX_ExportHelper,
	MH_PT_BoneNamingHelper,
	MH_PT_BoneMapper,
	MH_UL_NamingRules,
	MH_PT_RuleBasedNamingTool,
	# MH_PT_AdditoinalPMXBones,
	MH_PT_BoneSettigsTool,
	MH_PT_MaterialSettingTool,
	MH_PT_MaterialViewer,
	MH_PT_MineDetector,
]


import inspect,sys
def register():
	ops = [c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass) if "_OT_" in c[0]]
	for c in ops:
		bpy.utils.register_class(c)

	for c in _panels:
		bpy.utils.register_class(c)

def unregister():
	for c in reversed(_panels):
		bpy.utils.unregister_class(c)
		
	ops = [c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass) if "_OT_" in c[0]]
	for c in ops:
		bpy.utils.unregister_class(c)

	
################################################################################
# Helper Functions
################################################################################
import bpy
from contextlib import contextmanager

################################################################################
def dump(obj):
	for attr in dir(obj):
		if hasattr( obj, attr ):
			print( "obj.%s = %s" % (attr, getattr(obj, attr)))



##############################################################
@contextmanager
def mode_change(mode):
	lastMode = None
	if mode != bpy.context.mode:
		lastMode = bpy.context.mode
		bpy.ops.object.mode_set(mode=mode, toggle=False)

	try:
		yield lastMode

	finally:
		if lastMode is None:
			return
				
		if lastMode in ('EDIT_MESH','EDIT_CURVE','EDIT_ARMATURE'):
			lastMode = 'EDIT'
		elif lastMode == 'PAINT_WEIGHT':
			lastMode = 'WEIGHT_PAINT'
		elif lastMode == 'PAINT_VERTEX':
			lastMode = 'VERTEX_PAINT'
		elif lastMode == 'PAINT_TEXTURE':
			lastMode = 'TEXTURE_PAINT'

		bpy.ops.object.mode_set(mode=lastMode, toggle=False)
		return

##############################################################
def is_armature(obj: bpy.types.Object) -> bool:
	if obj and obj.pose:
		return True
	else:
		return False

##############################################################
def find_armature_within_children( obj: bpy.types.Object ) -> bpy.types.Object:
	if not obj:
		return None
	for o in obj.children_recursive:
		if o.pose:
			return o
	
	return None


##############################################################
def find_mmd_root(obj: bpy.types.Object) -> bpy.types.Object:
	if not obj:
		return None
	if obj.mmd_type == 'ROOT':
		return obj
	return find_mmd_root(obj.parent)


##############################################################
def ensure_poselib(obj: bpy.types.Object, name:str ) -> bpy.types.Action:
	if not obj or not obj.pose:
		return None
	
	for action in bpy.data.actions:
		if action.name == name:
			obj.pose_library= action
	if obj.pose_library is None or obj.pose_library.name != name:
		obj.pose_library = bpy.data.actions.new( name )
	return obj.pose_library

##############################################################
def ensure_fcurve( action:bpy.types.Action, data, attr:str ):
	value = getattr(data, attr)
	if value is None:
		return None
	#fcurve: bpy.types.FCurve = action.fcurves.keyframe_insert()
	return None

##############################################################
def ensure_visible_obj( obj: bpy.types.Object ):
	if obj.visible_get():
		return

	obj.hide_viewport = False
	obj.hide_set(False)

	if obj.visible_get():
		return

	# still invisible. show 
	def check_layer_recursive(layer_collection):
		for lc in layer_collection.children:
			if check_layer_recursive(lc):
				lc.hide_viewport = lc.collection.hide_viewport = False
				return True
		
		if obj in layer_collection.collection.objects.values():
			layer_collection.exclude = False
			return True
		return False

	check_layer_recursive(bpy.context.view_layer.layer_collection)

	return


import re

# https://docs.blender.org/manual/en/dev/rigging/armatures/bones/editing/naming.html
__LR_REGEX = [
	{"re": re.compile(r'^(.+)(RIGHT|LEFT)(\.\d+)?$', re.IGNORECASE), "lr": 1, 'sep':-1},
	{"re": re.compile(r'^(.+)([\.\- _])(L|R)(\.\d+)?$', re.IGNORECASE), "lr": 2, 'sep': 1},
	{"re": re.compile(r'^(LEFT|RIGHT)(.+)$', re.IGNORECASE), "lr": 0, 'sep':-1},
	{"re": re.compile(r'^(L|R)([\.\- _])(.+)$', re.IGNORECASE), "lr": 0, 'sep':1},
	{"re": re.compile(r'^(.+)(左|右)(\.\d+)?$'), "lr": 1, 'sep':-1},
	{"re": re.compile(r'^(左|右)(.+)$'), "lr": 0, 'sep': -1 },
	]
__LR_MAP = {
	"RIGHT": "LEFT",
	"Right": "Left",
	"right": "left",
	"LEFT": "RIGHT",
	"Left": "Right",
	"left": "right",
	"L": "R",
	"l": "r",
	"R": "L",
	"r": "l",
	"左": "右",
	"右": "左",
	}

__LR_POSTFIX_MAP = {
	"RIGHT": "R",
	"Right": "R",
	"right": "R",
	"LEFT": "L",
	"Left": "L",
	"left": "L",
	"L": "L",
	"l": "L",
	"R": "R",
	"r": "R",
	"左": "L",
	"右": "R",
	}

################################################################################
def flip_name(name):
	for regex in __LR_REGEX:
		match = regex["re"].match(name)
		if match:
			groups = match.groups()
			lr = groups[regex["lr"]]
			if lr in __LR_MAP:
				flip_lr = __LR_MAP[lr]
				name = ''
				for i, s in enumerate(groups):
					if i == regex["lr"]:
						name += flip_lr
					elif s:
						name += s
				return name
	return name

################################################################################
def get_lr_from_name(name: str, return_dotted: bool=False) -> str: 
	for regex in __LR_REGEX:
		match = regex["re"].match(name)
		if match:
			groups = match.groups()
			lr = groups[regex["lr"]]
			return ('.' if return_dotted else '') + __LR_POSTFIX_MAP[lr]
	return ''

################################################################################
def remove_lr_from_name(name: str) -> str: 
	for regex in __LR_REGEX:
		match = regex["re"].match(name)
		if match:
			groups = match.groups()
			lr_idx = regex["lr"]
			sep_idx = regex["sep"]
			name = ''
			for i, s in enumerate(groups):
				if i==lr_idx or i==sep_idx:
					continue
				name += s if s else ''
			return name
	return ''
	

################################################################################
def get_objects_by_armature(arm: bpy.types.Object, from_objects ):
	return [o for o in from_objects if o.find_armature() is arm]

################################################################################　
def get_objects_by_material(mat:bpy.types.Material, from_objects ):
	objs = []
	for obj in [o for o in from_objects]:
		for slot in obj.material_slots:
				if slot.material is mat:
					objs.append(obj)
	return objs


##############################################################
def get_target_objects( from_obj=None, type_filter='' ):
	"""Returns selected and armature bound objects or each children recursive of selected objects"""
	objs = set(bpy.context.selected_objects[:])
	arms = [arm for arm in objs if arm.pose]
	
	from_obj = bpy.data.objects if from_obj is None else from_obj

	# add objes bound to armatures in selection
	objs_by_armature = False
	for arm in arms:
		objs_by_armature = True
		objs |= set(get_objects_by_armature(arm, from_obj) )

	if not objs_by_armature:
		# add children of each objects
		children = set()
		for obj in objs:
			for child in obj.children_recursive:
				if child.name in from_obj:
					children.add(child)

		objs |= children
	
	if type_filter != '':
		return [o for o in objs if type_filter in o.type]
	else:
		return objs



################################################################################
def create_morph_list():
		print(f"Creating Morph Data.")
		morphdic = dict()

		def __AddTarget(name, datablock:bpy.types.ID, type):
			if name not in morphdic:
				morphdic[name] = list()
			morphdic[name].append((datablock, datablock.name, type))

		# shape keys, type="SHAPEKEY"
		for obj in [o for o in bpy.data.objects if o.type=="MESH" and o.data.shape_keys is not None]:
			for kb in obj.data.shape_keys.key_blocks[1:]:
				__AddTarget(kb.name, obj, "SHAPEKEY")

		# material morphs, type="MATERIAL"
		for mat in [m for m in bpy.data.materials if len(m.kt_morph_setting.name)]:
			__AddTarget(mat.kt_morph_setting.name, mat, "MATERIAL")

		# bone poses, type="POSE"
		for arm in [o for o in bpy.data.objects if o.type=="ARMATURE"]:
			if arm.pose_library is None:
				continue
			for pm in arm.pose_library.pose_markers:
				if pm.name.startswith("_"):
					continue
				__AddTarget(pm.name, arm, "POSE")

		morphs = bpy.context.scene.kt_props.morphs
		
		# Remove unnecesary entries from Morph List
		for key in morphs.keys():
			if key not in morphdic:
				morphs.remove(morphs.find(key))

		# update morph list
		for name, targets in morphdic.items():
			created = False
			item = morphs.get(name)

			if item is None: # Create new
				item = morphs.add()
				item.name = name
				created = True

			# reset targets
			item.targets.clear()

			for datablock, name, type in targets:
				target = item.targets.add()
				target.name = name
				target.object = datablock
				target.type = type
				item.use_meshes = item.use_meshes or type == "SHAPEKEY"
				item.use_mats = item.use_mats or type == "MATERIAL"
				item.use_arms = item.use_arms or type == "POSE"

			if created:
				item.value = 0.0 # touching via item.valule's update() callback

		del morphdic
		
		if bpy.context.scene.kt_props.get("morph_is_invalid"):
			del bpy.context.scene.kt_props["morph_is_invalid"]

		return


################################################################################
def add_mmd_tex( mat:bpy.types.Material, node_name:str, filepath:str ) -> bpy.types.ShaderNodeTexImage or None:
	if not mat or not filepath:
		return None
	
	if not mat.node_tree:
		mat.use_nodes = True

	def get_tex_node(mat, node_name):
		tex_node = getattr(mat.node_tree, "nodes", {}).get(node_name, None)
		if isinstance(tex_node, bpy.types.ShaderNodeTexImage):
			return tex_node

	def get_img_node_by_filepath(filepath, default=None):
		for img in bpy.data.images:
			if img.filepath == filepath:
				# print(f"Image found: {img.name}, {img.filepath}")
				return img
		# create new image
		try:
			# print(f"Creating new image: {filepath}")
			img = bpy.data.images.new(filepath, 1, 1)
			img.filepath = filepath
			img.source = 'FILE'
			img.reload()
		except Exception as e:
			# print(f'Error creating image: {e}')
			return default
		return img


	def nt_get_freearea(tree:bpy.types.NodeTree):
		mmd_shader = mat.node_tree.nodes.get("mmd_shader", None)
		if mmd_shader:
			return mmd_shader.location.x-300, mmd_shader.location.y-300

		x, y = 0, 0
		for node in [n for n in tree.nodes if not n.name.startswith("mmd_")]:
			x = min(x, node.location.x)
			y = max(y, node.location.y)
		return x-1200, y+600

	node_pos_offsets = {
		'mmd_base_tex' : (0, 0),
		'mmd_sphere_tex' : (0, -300),
		'mmd_toon_tex' : (0, -600),
	}

	if node_name not in node_pos_offsets.keys():
		return None

	# --------------------------------
	tex_node = get_tex_node(mat, node_name)
	if tex_node: # already exists
		tex_node.image = get_img_node_by_filepath(filepath, tex_node.image)
	else: # create new
		node_pos = nt_get_freearea(mat.node_tree)
		tex_node:bpy.types.ShaderNodeTexImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
		tex_node.name = tex_node.label = node_name
		tex_node.image = get_img_node_by_filepath(filepath)
		tex_node.location.x = node_pos[0] + node_pos_offsets[node_name][0]
		tex_node.location.y = node_pos[1] + node_pos_offsets[node_name][1]
	
	return tex_node


################################################################################
def ensure_mmd_bone_id(bone: bpy.types.PoseBone) -> int:
	"""Ensure bone has mmd_bone.bone_id. If not, assign new id"""
	if not bone:
		return -1
	mmd_bone = bone.mmd_bone
	if mmd_bone.bone_id < 0:
		max_id = -1
		for bone in bone.id_data.pose.bones:
			max_id = max(max_id, bone.mmd_bone.bone_id)
		mmd_bone.bone_id = max_id + 1
	return mmd_bone.bone_id

################################################################################
def get_bone_by_mmd_bone_id(armature: bpy.types.Object, bone_id: int) -> bpy.types.PoseBone:
	"""Returns bone by mmd_bone.bone_id"""
	for bone in armature.pose.bones:
		if bone.mmd_bone.bone_id == bone_id:
			return bone
	return None


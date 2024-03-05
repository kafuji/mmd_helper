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

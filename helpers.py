################################################################################
# Helper Functions
################################################################################
import bpy

from mathutils import Vector
from typing import Tuple, List, Dict, Any, Optional

import math

from . import common


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


#################################################################################
def get_lr_string(name, eng=False):
    lr = get_lr_from_name(name)

    lr_map = {
        'j':{
            '': '',
            'L': '左',
            'R': '右'
        },
        'e':{
            '': '',
            'L': 'left ',
            'R': 'right '
        }
    }
    return lr_map['e'][lr] if eng else lr_map['j'][lr]


##################################################################################
# convert mmd bone name to blender friendly name, e.g. '左足首' to '足首.L'
def convert_mmd_bone_name_to_blender_friendly(name:str) -> str:
    if name.startswith('左'):
        return name[1:] + '.L'
    if name.startswith('右'):
        return name[1:] + '.R'
    if name.startswith('left '):
        return name[5:] + '.L'
    if name.startswith('right '):
        return name[6:] + '.R'
    
    return name


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
		# print(f"Creating Morph Data.")
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


#################################################################################
def get_bone_by_mmd_name_j(armature: bpy.types.Object, name: str) -> bpy.types.PoseBone:
	"""Returns bone by mmd_bone.name_j or mmd_bone.name_e"""
	pbones = armature.pose.bones
	ret = [b for b in pbones if b.mmd_bone.name_j == name or (b.mmd_bone.name_j == "" and b.name == name)]
	if len(ret) > 1:
		print(f"Warning: More than one bone found with name {name}.")
	return next(iter(ret), None) # return first or None


################################################################################

# read/write callbacks
readbool = lambda s: s != '0'
def writebool(b: bool) -> str:
	if b is None:
		return ''
	return '1' if b else '0'

readfloat = lambda s: float(s)
writefloat = lambda v: str(v) if v is not None else ''

readstr_naked = lambda s: s
writestr_naked = lambda s: s if s is not None else ''

readstr = lambda s: s.strip('"')
writestr = lambda s: f'"{s}"' if s is not None else ''

readint = lambda s: int(s)
writeint = lambda i: str(i) if i is not None else ''

def conv_loc_blender_to_mmd( loc: Vector, armature:bpy.types.Object, scale: float=12.5 ) -> Vector:
	"""
	Convert Blender's location to MMD's world location
	loc: armature space location
	armature: armature object to translate local -> world
	scale: scale factor for location
	"""

	# to World space, XYZ to XZY
	loc = armature.matrix_world @ loc
	loc = loc * scale
	return Vector((loc.x, loc.z, loc.y))

def conv_loc_mmd_to_blender( loc: Vector, armature:bpy.types.Object, scale: float=12.5 ) -> Vector:
	"""
	Convert MMD's location to Blender's location
	loc: world space location
	armature: armature object to translate world -> local
	scale: scale factor for location
	"""
	loc = Vector(loc) / scale
	loc = armature.matrix_world.inverted() @ loc
	return Vector((loc.x, loc.z, loc.y))


def get_name_j(bone:bpy.types.PoseBone) -> str:
	"""Get bone's MMD name in Japanese if exists, otherwise Blender name"""
	return bone.mmd_bone.name_j if bone.mmd_bone.name_j else bone.name

def get_name_e(bone:bpy.types.PoseBone) -> str:
	"""Get bone's MMD name in English if exists, otherwise Blender name"""
	return bone.mmd_bone.name_e if bone.mmd_bone.name_e else bone.name


class PmxBoneData: # reader/writer

	# PmxBone,ボーン名,ボーン名(英),変形階層,物理後(0/1),位置_x,位置_y,位置_z,回転(0/1),移動(0/1),IK(0/1),表示(0/1),操作(0/1),  
	# 親ボーン名,表示先(0:オフセット/1:ボーン),表示先ボーン名,表示先オフセット_x,表示先オフセット_y,表示先オフセット_z,
	# ローカル付与(0/1),回転付与(0/1),移動付与(0/1),付与率,付与親名,軸制限(0/1),制限軸_x,制限軸_y,制限軸_z,
	# ローカル軸(0/1),ローカルX軸_x,ローカルX軸_y,ローカルX軸_z,ローカルZ軸_x,ローカルZ軸_y,ローカルZ軸_z,
	# 外部親(0/1),外部親Key,IKTarget名,IKLoop,IK単位角[deg]

	# PmxIKLink,コントロールボーン名,制御対象ボーン名,角度制限On/Off,min_x, max_x, min_y, max_y, min_z, max_z

	col_data = [ # list of (attr_name, read, write) 
		( 'header', readstr_naked, writestr_naked ) ,

		# Bone Name ,ボーン名)
		( 'name_j', readstr, writestr ) ,
		( 'name_e', readstr, writestr ) ,

		# Deform Hierarchy ,変形階層)
		( 'def_layer', readint, writeint ) ,
		( 'after_phys', readbool, writebool ) ,

		# Position ,位置)
		( 'pos_x', readfloat, writefloat ) ,
		( 'pos_y', readfloat, writefloat ) ,
		( 'pos_z', readfloat, writefloat ) ,

		# Setting
		( 'can_rot', readbool, writebool ) ,
		( 'can_move', readbool, writebool ) ,
		( 'has_ik', readbool, writebool ) ,
		( 'is_visible', readbool, writebool ) ,
		( 'is_operatable', readbool, writebool ) ,

		# Parent
		( 'parent_name', readstr, writestr ) ,

		# Display Destination ,表示先)
		( 'dest_type', readint, writeint ) ,
		( 'dest_name', readstr, writestr ) ,
		( 'dest_offset_x', readfloat, writefloat ) ,
		( 'dest_offset_y', readfloat, writefloat ) ,
		( 'dest_offset_z', readfloat, writefloat ) ,

		# Add Deform ,付与)
		( 'is_local_add', readbool, writebool ) ,
		( 'has_addrot', readbool, writebool ) ,
		( 'has_addloc', readbool, writebool ) ,
		( 'add_rate', readfloat, writefloat ) ,
		( 'add_parent_name', readstr, writestr ) ,

		# Fixed Axis ,軸制限)
		( 'has_fixed_axis', readbool, writebool ) ,
		( 'fixed_axis_x', readfloat, writefloat ) ,
		( 'fixed_axis_y', readfloat, writefloat ) ,
		( 'fixed_axis_z', readfloat, writefloat ) ,

		# Local Axis ,ローカル軸)
		( 'has_local_axis', readbool, writebool ) ,
		( 'local_x_x', readfloat, writefloat ) ,
		( 'local_x_y', readfloat, writefloat ) ,
		( 'local_x_z', readfloat, writefloat ) ,
		( 'local_z_x', readfloat, writefloat ) ,
		( 'local_z_y', readfloat, writefloat ) ,
		( 'local_z_z', readfloat, writefloat ) ,

		# External Parent ,外部親)
		( 'has_ext_parent', readbool, writebool ) ,
		( 'ext_parent_key', readint, writeint ) ,

		# IK
		( 'ik_target_name', readstr, writestr ) ,
		( 'ik_loop', readint, writeint ) ,
		( 'ik_unit_angle', readfloat, writefloat ) ,
	]

	def __init__(self, scale:float=12.5): # Init using given line (from CSV or clipboard)
		self.scale = scale # scale factor for location
		self.header = 'PmxBone'

		# create atrributes
		for col_data in self.col_data:
			attr_name, _, _ = col_data
			setattr(self, attr_name, None)

	def __str__(self):
		# convert to string
		values = ['PmxBone']
		for col_data in self.col_data[1:]:
			attr_name, _, write = col_data
			value = write(getattr(self, attr_name, ''))
			values.append(value)
		
		ret = ','.join(values)

		# PMX IK Links
		if hasattr(self, 'ik_links') and len(self.ik_links):
			for ik_link in self.ik_links:
				ret += '\n' + ik_link

		return ret
	
	def __repr__(self):
		return self.__str__()


	def from_line(self, line:str):
		# split line
		values = line.split(',')
		if len(values) < 40:
			print(f"Invalid PmxBone line: {line}")
			return

		# set attributes
		for col_data, value in zip(self.col_data, values):
			attr_name, read, _ = col_data
			setattr(self, attr_name, read(value))
		return

	def to_str(self):
		return str(self)

	def to_bone( self, armature:bpy.types.Object ) -> bpy.types.PoseBone:
		"""
		Convert to Blender's PoseBone

		It finds the bone by mmd_bone.name_j or mmd_bone.name_e.
		If bone is available: Use it and set the attributes.
		If bone is not available: Create a new bone and set the attributes.
		"""
		if not getattr(self, 'name_j', None):
			print(f"Warning: Bone name not set. Cannot convert to PoseBone.")
			print(self)
			return None

		arm = armature

		# Set bone position
		with common.save_context(mode='EDIT', active_obj=arm):
			pbone = get_bone_by_mmd_name_j(arm, self.name_j)
			if pbone:
				ebone = arm.data.edit_bones.get(pbone.name)
			else:
				# create new bone
				ebone = arm.data.edit_bones.new(self.name_j)

			# Position
			pos_x = getattr(self, 'pos_x', 0.0)
			pos_y = getattr(self, 'pos_y', 0.0)
			pos_z = getattr(self, 'pos_z', 0.0)
			pos = conv_loc_mmd_to_blender( (pos_x, pos_y, pos_z), arm, self.scale )
			ebone.head = pos

			# Parent
			parent = get_bone_by_mmd_name_j(arm, self.parent_name)
			if parent:
				ebone.parent = arm.data.edit_bones.get(parent.name)
			else:
				ebone.parent = None

			# Display Destination
			dest_type = getattr(self, 'dest_type', 0)
			dest_name = getattr(self, 'dest_name', None)
			dest_offset_x = getattr(self, 'dest_offset_x', 0.0)
			dest_offset_y = getattr(self, 'dest_offset_y', 0.0)
			dest_offset_z = getattr(self, 'dest_offset_z', 0.0)

			if dest_type == 0: # offset
				dest_offset = conv_loc_mmd_to_blender( (dest_offset_x, dest_offset_y, dest_offset_z), arm, self.scale )
				ebone.tail = ebone.head + dest_offset
			elif dest_type == 1: # bone
				dest_bone = get_bone_by_mmd_name_j(arm, dest_name)
				if dest_bone:
					ebone.tail = arm.data.edit_bones.get(dest_bone.name).head
				else:
					pass # Let blender decide the tail position
		# end of with common.save_context('EDIT', active_obj=arm)

		# Set bone properties
		with common.save_context(mode='POSE', active_obj=arm):
			pbone = get_bone_by_mmd_name_j(arm, self.name_j)
			if not pbone:
				print(f"Warning: Bone {self.name_j} not found in armature {arm.name}.")
				return None

			pbone.mmd_bone.name_j = self.name_j
			pbone.mmd_bone.name_e = getattr(self, 'name_e', "")
			pbone.mmd_bone.bone_id = ensure_mmd_bone_id(pbone)
		
		return pbone


	def from_bone( self, pbone:bpy.types.PoseBone, categories=[], use_pose: bool=False ): # write only wanted categories
		arm:bpy.types.Object = pbone.id_data
		mmd = pbone.mmd_bone

#		if 'name' in categories: # always!
		self.bone = pbone
		self.name_j = get_name_j(pbone)
		self.name_e = get_name_e(pbone)

		if 'POSITION' in categories:
			loc = pbone.head if use_pose else pbone.bone.head_local
			self.pos_x, self.pos_y, self.pos_z = conv_loc_blender_to_mmd(loc, arm, self.scale)

		if 'SETTING' in categories:
			self.can_rot = not all(pbone.lock_rotation[:])
			self.can_move = not all(pbone.lock_location[:])
			# self.has_ik = ... # need to find any bone uses this bone as ik target
			self.is_visible = not pbone.bone.hide
			self.is_operatable = mmd.is_controllable

		if 'PARENT' in categories:
			parent = pbone.parent
			if not parent:
				self.parent_name = ''
			else:
				self.parent_name = get_name_j(parent)

		if 'DISPLAY' in categories:
			if any(c.bone.use_connect for c in pbone.children):
				for child in pbone.children:
					if child.bone.use_connect:
						self.dest_type = 1
						self.dest_name = get_name_j(child)
						break
			else:
				self.dest_type = 0
				self.dest_name = None
				head_pos = pbone.head if use_pose else pbone.bone.head_local
				tail_pos = pbone.tail if use_pose else pbone.bone.tail_local
				offset = tail_pos - head_pos
				offset = conv_loc_blender_to_mmd(offset, arm, self.scale)
				self.dest_offset_x, self.dest_offset_y, self.dest_offset_z = offset

		if 'ADD_DEFORM' in categories:
			con = next((c for c in pbone.constraints if c.type in {'COPY_ROTATION', 'COPY_LOCATION'}), None)
			if con:
				tgt_bone = arm.pose.bones.get(con.subtarget)
				self.is_local_add = False
				self.has_addrot = con.type == 'COPY_ROTATION'
				self.has_addloc = con.type == 'COPY_LOCATION'
				self.add_rate = con.influence
				if not tgt_bone:
					self.add_parent_name = ''
					print(f"Warning: Target bone not found for {pbone.name, con.name}.")
				else:
					self.add_parent_name = get_name_j(tgt_bone)

		if 'FIXED_AXIS' in categories:
			self.has_fixed_axis = mmd.enabled_fixed_axis
			self.fixed_axis_x, self.fixed_axis_y, self.fixed_axis_z = mmd.fixed_axis
		if 'LOCAL_AXIS' in categories:
			self.has_local_axis = mmd.enabled_local_axes
			self.local_x_x, self.local_x_y, self.local_x_z = mmd.local_axis_x
			self.local_z_x, self.local_z_y, self.local_z_z = mmd.local_axis_z
		if 'EXT_PARENT' in categories: # no such property in blender mmd_tools
			print(f"Warning: EXT_PARENT is not supported in blender mmd_tools")
		if 'IK' in categories: # implement later
			tgt = get_ik_target(pbone)
			if tgt:
				# Set PmxBone IK data
				self.ik_target_name = get_name_j(tgt)
				con:bpy.types.KinematicConstraint = next((c for c in tgt.constraints if c.type == 'IK'), None)
				self.ik_loop = con.iterations
				self.ik_unit_angle = 57.29578 # default value in PMX Editor, we can't know it in blender

				# Create PmxIKLink lines
				self.ik_links = []
				tgts = get_ik_target_chain(tgt)
				# print(f"Additional IK targets: {[t.name for t in tgts]}")
				for t in tgts:
					t:bpy.types.PoseBone
					ik_link = "PmxIKLink,"
					ik_link += f'"{get_name_j(pbone)}","{get_name_j(t)}",'

					con_limit = t.constraints.get("mmd_ik_limit_override")
					if con_limit and type(con_limit) == bpy.types.LimitRotationConstraint:
						ik_link += "1," # angle limit enabled
						min = Vector( (con_limit.min_x, con_limit.min_y, con_limit.min_z) )
						max = Vector( (con_limit.max_x, con_limit.max_y, con_limit.max_z) )

						# to degrees
						min = Vector([math.degrees(v) for v in min])
						max = Vector([math.degrees(v) for v in max])

						ik_link += f"{min.z},{max.z},{min.y},{max.y},{min.x},{max.x}"

					else:
						ik_link += "0,0,0,0,0,0,0"

					self.ik_links.append(ik_link)

		return self

def get_ik_target(bone:bpy.types.PoseBone) -> bpy.types.PoseBone:
	# find IK constraint from entire armature
	arm:bpy.types.Object = bone.id_data
	for pbone in arm.pose.bones:
		for con in [c for c in pbone.constraints if c.type == 'IK']:
			con: bpy.types.KinematicConstraint
			if con.target is arm and con.subtarget == bone.name:
				print(f"This is IK controller: {bone.name}")
				return pbone

def get_ik_target_chain(bone:bpy.types.PoseBone) -> list:
	"""
		bone: the first target bone (which has IK constraint)
a		returns: list of additional target bones
	"""

	ret = [bone]
	con:bpy.types.KinematicConstraint = next((c for c in bone.constraints if c.type == 'IK'), None)
	if con.chain_count <= 0: # doesn't support this
		return ret

	for i in range(con.chain_count-1):
		bone = bone.parent
		if not bone:
			break
		ret.append(bone)
	
	return ret

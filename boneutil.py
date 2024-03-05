import bpy

##############################################################
# calc inverse matrix for constraint (Child of or others)
def con_set_inverse_matrix(constraint : bpy.types.Constraint):
    c = constraint

    if c.target is None:
        return

    subtarget = None
    if c.target.pose and c.subtarget:
        subtarget = c.target.pose.bones.get(c.subtarget, None)

    if subtarget:
        if c.id_data is c.target: 
            c.inverse_matrix = subtarget.matrix.inverted()
        else:
            c.inverse_matrix = c.target.matrix_world @ subtarget.matrix.inverted()
    else:
        c.inverse_matrix = c.target.matrix_world.inverted()

    return

##############################################################
# works only in edit mode
def batch_calc_bone_roll(roll_type:str, edit_bones ):
    bpy.ops.armature.select_all(action='DESELECT')

    for eb in edit_bones:
        eb.select = True
    
    bpy.ops.armature.calculate_roll(type=roll_type)

    return

from mathutils import Vector

##############################################################
# works only in edit mode
def move_bone_by_command(bone:bpy.types.EditBone, commands:str, target_bone:bpy.types.EditBone, target_part:str, axes:str, offset:Vector ):
        if not bone:
            return

        target_pos = Vector( getattr(target_bone, target_part) )
        target_pos += Vector(offset)

        if 'head' in commands:
            bone.head.x = target_pos.x if 'x' in axes else bone.head.x
            bone.head.y = target_pos.y if 'y' in axes else bone.head.y
            bone.head.z = target_pos.z if 'z' in axes else bone.head.z

        if 'tail' in commands:
            bone.tail.x = target_pos.x if 'x' in axes else bone.tail.x
            bone.tail.y = target_pos.y if 'y' in axes else bone.tail.y
            bone.tail.z = target_pos.z if 'z' in axes else bone.tail.z

        if 'move' in commands:
            delta = bone.tail - bone.head
            bone.head.x = target_pos.x if 'x' in axes else bone.head.x
            bone.head.y = target_pos.y if 'y' in axes else bone.head.y
            bone.head.z = target_pos.z if 'z' in axes else bone.head.z
            bone.tail = bone.head + delta
            
        if 'align' in commands:
            bone_dir = Vector(target_bone.tail - target_bone.head)
            bone_dir.normalize()
            bone_len = Vector(bone.tail - bone.head).length
            bone.tail = bone.head + bone_dir*bone_len
            bone.roll = target_bone.roll

        elif 'lookat' in commands:
            bone_dir = Vector(target_bone.head - bone.head)
            bone_dir.normalize()
            bone_len = Vector(bone.tail - bone.head).length
            bone.tail = bone.head + bone_dir*bone_len
            
        if 'reset_roll' in commands:
            bone.roll = 0
        
        return



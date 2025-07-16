import bpy
from .helpers import find_mmd_root

class MH_PT_object_context_menu(bpy.types.Menu):
    bl_idname = "MH_MT_context_menu"
    bl_label = "PMX Export Helper"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or not find_mmd_root(obj):
            return False

        return True

    def draw(self, context):
        l = self.layout

        obj = context.active_object

        l.label(text="Export", icon='FILE_TICK')
        # if obj.type == 'ARMATURE':
        #     op = l.operator("mmd_tools.export_pmx", text="Export PMX")
        #     op.copy_textures = False
        #     op.visible_meshes_only = True
        
        #     l.operator("mmd_tools.import_model", text="Import PMX/PMD")
        #     l.operator("mmd_tools.import_vmd", text="Import VMD")
        #     l.operator("mmd_tools.export_vmd", text="Export VMD")
        if obj.type in {'MESH', 'ARMATURE'}:
            l.operator("mmd_helper.quick_export_objects")

        if obj.type == 'ARMATURE':
            l.label(text="Bone Settings", icon='BONE_DATA')
            l.operator("mmd_helper.load_bone_settings_from_csv")
            l.operator("mmd_helper.get_bones_from_clipboard")
            l.operator("mmd_helper.send_bones_to_clipboard")

            l.label(text="Material Settings", icon='MATERIAL')
            l.operator("mmd_helper.load_material_from_csv")
            l.operator("mmd_helper.clear_mmd_material_names")

        return


class MH_PT_pose_context_menu(bpy.types.Menu):
    bl_idname = "MH_MT_pose_context_menu"
    bl_label = "PMX Export Helper"

    def draw(self, context):
        l = self.layout
        l.operator("mmd_helper.load_bone_settings_from_csv")
        l.operator("mmd_helper.get_bones_from_clipboard")
        l.operator("mmd_helper.send_bones_to_clipboard")

        return


def menu_func(self, context):  
    if context.mode == 'OBJECT':
        self.layout.menu(MH_PT_object_context_menu.bl_idname)
    if context.mode == 'POSE':
        self.layout.menu(MH_PT_pose_context_menu.bl_idname)


menu_classes = [
    MH_PT_object_context_menu,
    MH_PT_pose_context_menu,
]

def register():
    for cls in menu_classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    bpy.types.VIEW3D_MT_pose_context_menu.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_pose_context_menu.remove(menu_func)

    for cls in menu_classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()


import bpy

class MH_PT_context_menu(bpy.types.Menu):
    bl_idname = "MH_MT_context_menu"
    bl_label = "PMX Export Helper"

    def draw(self, context):
        l = self.layout
        op = l.operator("mmd_tools.export_pmx", text="Export PMX")
        op.copy_textures = False
        op.visible_meshes_only = True
        
        l.operator("mmd_tools.import_model", text="Import PMX/PMD")
        l.operator("mmd_tools.import_vmd", text="Import VMD")
        l.operator("mmd_tools.export_vmd", text="Export VMD")

def menu_func(self, context):  
    self.layout.separator()
    self.layout.menu(MH_PT_context_menu.bl_idname)

def register():
    bpy.utils.register_class(MH_PT_context_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(MH_PT_context_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()


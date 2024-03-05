bl_info = {
    "name" : "PMX setup helper for mmd_tools",
    "author" : "Kafuji",
    "version" : (0,1,1),
    "blender" : (3,0,0),
    "location" : "View3D > Side Bar > MMD",
    "description" : "PMX setup helper utilities for mmd_tools",
    "warning" : "",
    "wiki_url" : "", 
    "tracker_url" : "",
    "category" : "Object"
}

from . import operators
from . import panels
from . import properties
from . import translation
from . import preferences

################################################################################
# Register & Unregister

# Register This Addon
def register():
    translation.register()
    properties.register()
    preferences.register()

    # touch user_bones to sync mmd_bone_schema internal data
    user_bones = preferences.get_prefs().user_bones
    preferences.get_prefs().user_bones = user_bones

    operators.register()
    panels.register()
    return


# Unregister This Addon
def unregister():
    panels.unregister()
    operators.unregister()
    preferences.unregister()
    properties.unregister()
    translation.unregister()
    return

# call register() if this script is invoked under main process of Blender
if __name__ == "__main__":
    register()

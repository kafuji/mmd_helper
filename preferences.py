import bpy

from . import mmd_bone_schema
from os.path import exists

def update_user_bones(self,context):
    mmd_bone_schema.clear_user_bones()
    if len(self.user_bones) < 1:
        return

    filepath = self.user_bones
    
    if not filepath.endswith('.csv'):
        print(f'User pmx bone definitions: file {filepath} is not .csv')
        self['user_bones'] = ''
        return

    
    if not exists(filepath):
        print("WARNING: Additional Bone Definition File {filepath} is not exist.")
        return

    mmd_bone_schema.load_user_bones_from_csv(filepath)
    return


################################################################################
# Addon Preferences 
class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    user_bones: bpy.props.StringProperty(
        name='Additional PMX bone definitions file',
        description='You can add pmx bone definitions from CSV file',
        default='',
        subtype='FILE_PATH',
        update=update_user_bones,
        options=set()
        )

    def draw(self,context):
        layout:bpy.types.UILayout = self.layout
        layout.use_property_decorate = True
        layout.use_property_split = True
        layout.label(text='Additional PMX bone definitions file:')
        layout.prop(self, 'user_bones', text='')
        return

# get pref
def get_prefs():
    return bpy.context.preferences.addons[__package__].preferences


# register & unregister
def register():
    bpy.utils.register_class(Preferences)
    
def unregister():
    bpy.utils.unregister_class(Preferences)
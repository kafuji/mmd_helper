################################################################################
# Addon Properties
################################################################################
import bpy
from bpy.props import *
from bpy.types import PropertyGroup

from . import helpers
from . import mmd_bone_schema

# bone mapping update callback, automatically set to opposite bone, fingers
def on_update_mmd_bone_map(self, context):
    mmd_bone_schema.apply_bone_map(self)
    pbones = context.object.pose.bones

    if 0: # Disabled for some cases where the user intentionally set the same bone map
        # remove duplicate
        if self.mmd_bone_map != 'NONE':
            for bone in pbones:
                if bone.name == self.name:
                    continue

                if bone.mmd_bone_map == self.mmd_bone_map:
                    bone['mmd_bone_map'] = 'NONE'

    # bone map mirror
    opposite_bone = pbones.get(helpers.flip_name(self.name))
    if opposite_bone and opposite_bone is not self:
        opposite_bone['mmd_bone_map'] = self['mmd_bone_map']
        mmd_bone_schema.apply_bone_map(opposite_bone)

    return

# mmd bone suffix update callback
def on_update_mmd_bone_suffix(self, context):
    mmd_bone_schema.apply_bone_map(self)
    pbones = context.object.pose.bones
    opposite_bone = pbones.get(helpers.flip_name(self.name))
    if opposite_bone and opposite_bone is not self:
        opposite_bone['mmd_bone_suffix'] = self['mmd_bone_suffix']
        mmd_bone_schema.apply_bone_map(opposite_bone)
    return


# Rulse based naming entry
class MH_NamingRule(PropertyGroup):
    use_regex: BoolProperty(
        name='Use Regex',
        description='Use Regex for search/replace',
        default=False,
        options=set()
    )
    search: StringProperty(name='Search', options=set())
    replace_to: StringProperty(name='Replace',options=set())

# Naming Rules holder
class MH_NamingRules(PropertyGroup):
    replace_lr: BoolProperty(
        name='Replace LR',
        description='Convertr L/R identifier to prefix Hidari/Migi(Jp) or left/right(En)',
        default=True
    )
    data: CollectionProperty(type=MH_NamingRule)
    active_index: IntProperty()


# Main props for UI 
class MH_UIProps(PropertyGroup):
    show_suffix: BoolProperty(name='Show Suffix', description='Show suffix option: typically used for adding D or something', default=True)
    show_mmd_bone: BoolProperty(name='Show mmd_bone.name', description='Show mmd_bone.name_j and mmd_bone.name_e in the list', default=False)
    use_english: BoolProperty(name='Use English', description='Use english bone name for display', default=False)
    max_display: IntProperty(name='Display Max', description='Maximum number of items shown on the list', default=10)
    alert_only_essentials: BoolProperty(name='Alert essentials only', default=True, options=set())


################################################################################
# register & unregister this module
_property_classes = (
    MH_UIProps,
    MH_NamingRule,
    MH_NamingRules,
)

__properties = {
    bpy.types.PoseBone: {
        'mmd_bone_map': StringProperty(
            name='MMD Bone Definition',
            description = "Define bone name in MMD",
            update=on_update_mmd_bone_map,
            options=set()
        ),
        'mmd_bone_suffix': StringProperty(
            name='Suffix',
            description='Additive Suffix on mmd_bone name. e.g: "D"',
            update=on_update_mmd_bone_suffix,
        )
    },
    
    bpy.types.WindowManager: {
        'mh_props': PointerProperty(type=MH_UIProps)
    },
    
    bpy.types.Scene:{
        'mh_naming_rules': PointerProperty(type=MH_NamingRules)
    }
}

def register():
    for c in _property_classes:
        bpy.utils.register_class(c)
    
    for typ, t in __properties.items():
        for attr, prop in t.items():
            if hasattr(typ, attr):
                print(f'{__name__} Warning: register(): Overwriting {typ} with {attr}')
            try:
                setattr(typ, attr, prop)
            except:
                print(f'{__name__} Warning: warning: register {typ} {attr}')
    return


def unregister():
    for typ, t in __properties.items():
        for attr in t.keys():
            if hasattr(typ, attr):
                delattr(typ, attr)

    for c in reversed(_property_classes):
        bpy.utils.unregister_class(c)
    return



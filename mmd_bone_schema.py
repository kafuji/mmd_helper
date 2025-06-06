from typing import List, Tuple

import bpy
from bpy.props import *
from bpy.types import PropertyGroup

from . import helpers
from .data import mmd_bone_definition


# Bone definition item
class MH_PG_BoneDefinitionItem(PropertyGroup):
    category: StringProperty(name='Category', options=set())
    name: StringProperty(name='ID', options=set())
    name_j: StringProperty(name='Japanese', options=set())
    name_e: StringProperty(name='English', options=set())
    is_essential: BoolProperty(name='Essential', default=False, options=set())

class MH_PG_EssentialBoneItem(PropertyGroup):
    name: StringProperty(name='ID', options=set())

# # Bone category item
# class MH_PG_BoneCategoryItem(PropertyGroup):
#     name: StringProperty(name='ID', options=set())
#     display_name: StringProperty(name='Name', options=set())
#     description: StringProperty(name='Description', options=set())
#     bones: CollectionProperty(type=MH_PG_BoneDefinitionItem)
#     active_index: IntProperty()

# Bone definition holder
class MH_PG_MMDBoneSchema(PropertyGroup):
    bones: CollectionProperty(type=MH_PG_BoneDefinitionItem)
    essential_bones: CollectionProperty(type=MH_PG_EssentialBoneItem)
    active_index: IntProperty()

    additional_definitions_path: StringProperty(
        name="Additional PMX bone definitions file",
        description="Path to additional PMX bone definitions file in CSV format. See Readme to create your own",
        default='',
        subtype='FILE_PATH',
        options=set(),
        update=lambda self, context: self.load_definitions()
    )

    def enum_bone_definitions(self, only_essentials:bool=False) -> Tuple[str, str, str, str, bool]:
        """
        Iterate through bone definitions.
        Yields a tuple of (bone_id, name_j, name_e, category_id, is_essential).
        """
        for bone in self.bones:
            bone: MH_PG_BoneDefinitionItem
            if only_essentials and not bone.is_essential:
                continue
            yield (bone.name, bone.name_j, bone.name_e, bone.category, bone.is_essential)

    def get_bonedata_by_id(self, id) -> MH_PG_BoneDefinitionItem:
        return self.bones.get(id, None)

    def get_bone_id_list(self, only_essentials:bool=False) -> List[str]:
        if only_essentials:
            return [bone.name for bone in self.essential_bones]

        return [bone.name for bone in self.bones]

    def __add_bone_definition(self, category_id, bone_id, name_j, name_e, is_essential):
        # Check if the bone ID already exists
        if self.get_bonedata_by_id(bone_id) is not None:
            print(f"Bone ID {bone_id} already exists. Skipping bone definition.")
            return

        # Create a new bone definition item
        bone:MH_PG_BoneDefinitionItem = self.bones.add()
        bone.category = category_id
        bone.name = bone_id
        bone.name_j = name_j
        bone.name_e = name_e
        bone.is_essential = is_essential

        # Check if the bone is essential
        if is_essential:
            self.essential_bones.add().name = bone_id

    def __load_default_definitions(self):
        # Clear existing bone definitions
        self.bones.clear()

        # load default bone definitions
        for cat, items in mmd_bone_definition.bones.items():
            for item in items:
                self.__add_bone_definition(cat, *item)
        return

    def __load_additional_definitions(self):
        # restore default bone definitions
        filepath = self.additional_definitions_path
        if not filepath:
            return

        # Convert it to full path if it's relative
        filepath = bpy.path.abspath(filepath)
        if not filepath.endswith('.csv'):
            print(f"Invalid file format: {filepath}. Expected .csv")
            return

        # load additional bone definitions from file
        try:
            with open(filepath, 'r') as f:
                next(f)  # skip header
                lines = f.readlines()
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            return

        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split(',')
            if len(parts) != 5:
                continue

            category_id, bone_id, name_j, name_e, is_essential = parts

            if self.get_bonedata_by_id(bone_id) is not None:
                print(f"Bone ID {bone_id} already exists. Skipping bone definition.")
                continue

            self.__add_bone_definition(category_id, bone_id, name_j, name_e, is_essential.lower() == 'true')

            print(f"Loaded additional bone definition: {bone_id} - {name_j} / {name_e}")

        return


    def load_definitions(self):
        # Load default and additional definitions
        self.__load_default_definitions()
        self.__load_additional_definitions()
        return


    def __get_lr_string(self, name, eng=False):
        lr = helpers.get_lr_from_name(name)

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


    def apply_bone_map(self, pbone: bpy.types.PoseBone):
        if not pbone.mmd_bone_map: # Not assigned, skip
            return

        bone_data = self.get_bonedata_by_id(pbone.mmd_bone_map)
        if not bone_data: # Undefined bone map id, do nothing
            return

        if pbone.mmd_bone_map == 'NONE': # Assigned to none, clear the name
            pbone.mmd_bone.name_j = ""
            pbone.mmd_bone.name_e = ""
            return

        name_j = bone_data.name_j
        name_e = bone_data.name_e

        lr_j = self.__get_lr_string(pbone.name)
        lr_e = self.__get_lr_string(pbone.name, True)

        # Normal bones
        if not pbone.mmd_bone_map.startswith('F_'):
            pbone.mmd_bone.name_j = lr_j + name_j + pbone.mmd_bone_suffix
            pbone.mmd_bone.name_e = lr_e + name_e + pbone.mmd_bone_suffix
            return

        # Finger mode    
        b = pbone.bone
        count = 1
        while b.children:
            b = b.children[0]
            count+=1
        
        num_j_dic = {
            0:'０',
            1:'１',
            2:'２',
            3:'３',
        }

        if pbone.mmd_bone_map == 'F_THUMB':
            bone_num = 0 # 0, 1, 2
        else:
            if count > 3:
                bone_num = 0 # 0, 1, 2, 3
            else:
                bone_num = 1 # 1, 2, 3

        b = pbone.bone
        while True:
            try:
                pbone.id_data.pose.bones[b.name].mmd_bone.name_j = lr_j + name_j + num_j_dic[bone_num] + pbone.mmd_bone_suffix
                pbone.id_data.pose.bones[b.name].mmd_bone.name_e = lr_e + name_e + str(bone_num) + pbone.mmd_bone_suffix
            except Exception as e:
                print(f"bone.name: {b.name}, bone_num: {bone_num} count: {count}")
                raise Exception(e)
            bone_num += 1
            if not b.children or bone_num > 3:
                    break
            b = b.children[0]

        return


def apply_bone_map(pbone:bpy.types.PoseBone):
    pbone.id_data.mmd_bone_schema.apply_bone_map(pbone)
    return

# Register and unregister functions
__classes_in_order = (
    MH_PG_BoneDefinitionItem,
    MH_PG_EssentialBoneItem,
    MH_PG_MMDBoneSchema,
)

# Init definitions on all armature objects on startup/load
from bpy.app.handlers import persistent
@persistent
def on_load(dummy):
    for obj in (o for o in bpy.data.objects if o.pose):
        obj.mmd_bone_schema.load_definitions()
    return

def register():
    for cls in __classes_in_order:
        bpy.utils.register_class(cls)
    bpy.types.Object.mmd_bone_schema = PointerProperty(type=MH_PG_MMDBoneSchema, name='MMD Bone Schema', description='MMD Bone Schema')

    bpy.app.handlers.load_post.append(on_load)

    return

def unregister():
    del bpy.types.Object.mmd_bone_schema
    for cls in reversed(__classes_in_order):
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(on_load)

    return

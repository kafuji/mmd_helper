import hashlib

from . import helpers
from .data import mmd_bone_definition

# Internal Data
_idx_table = {}
_cat_table = {} # cat: bone_id
_bone_table = {} # bone_id: (name_j, name_e, is_essential, category)
_use_eng_display = False


# append pmx bone data, update internal data
def append_bone_internal(bone_id, name_j, name_e, is_essential, category):
    # create mian db:    name_j, name_e, is_essencial, category, EnumItem idx
    _bone_table[bone_id] = (name_j, name_e, is_essential, category)

    # create 4byte hashes for bone_id
    idx = int.from_bytes(hashlib.sha256(bone_id.encode()).digest()[:3], 'little')
    while idx in _idx_table.values(): # resolve conflict
        print(f'{__name__} Warning: append_bone_internal({bone_id}) idx conflict: resolving')
        idx += 1
    _idx_table[bone_id] = idx

    # category: bone_id table
    if bone_id in _cat_table[category]:
        _cat_table[category].remove(bone_id)

    _cat_table[category].append(bone_id)
    return

# update pmx bone data, update internal data
def update_bone_internal(bone_id, name_j, name_e, is_essential, category):
    if _bone_table[bone_id] == (name_j, name_e, is_essential, category):
        return

    old_category = _bone_table[bone_id][3]
    _bone_table[bone_id] = (name_j, name_e, is_essential, category)

    # category
    if _cat_table.get(category) is None:
        _cat_table[category] = []

    _cat_table[old_category].remove(bone_id)
    _cat_table[category].append(bone_id)
    return


# remove pmx bone data, update internal data
def remove_bone_internal(bone_id):
    del _idx_table[bone_id]
    cat = _bone_table[bone_id][3]
    del _bone_table[bone_id]
    _cat_table[cat].remove(bone_id)
    return
    
# set english mode for enum_bones_callback()
def use_english(flag):
    global _use_eng_display
    _use_eng_display = flag

# returns enum list for EnumProperty
def enum_bones_callback(scene, context):
    ret = [('NONE', 'None', 'Export this bone as is', 0)]

    # EnumProperty.itemsにCollectionProperty内StringPropertyの日本語を与えると文字化けするので内部データのみを使用
    for bone_ids in _cat_table.values():
        ret.append(None)
        for bone_id in bone_ids:
            data = _bone_table[bone_id]
            ret.append( (bone_id, data[0], data[1], '', _idx_table[bone_id]))

    return ret


# returns list of bone_id, filtered by is_essential
def bone_id_list(only_essentials):
    if only_essentials:
        return [id for id, ent in _bone_table.items() if ent[2] is True]
    return _bone_table.keys()


# returns mmd bone name by id
def bone_name(bone_id, eng=False):
    return _bone_table[bone_id][eng]

# returns mmd bone name by id
def bone_category(bone_id):
    return _bone_table[bone_id][3]

def bone_category_name(bone_id):
    return mmd_bone_definition.categories[bone_category(bone_id)][0]

def get_lr_string(name, eng=False):
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


# apply bone map. set mmd_bone.name_j and name_e
def apply_bone_map(bone):
    if bone.mmd_bone_map == 'NONE':
        return

    name_j = bone_name(bone.mmd_bone_map)
    name_e = bone_name(bone.mmd_bone_map, True)
    lr_j = get_lr_string(bone.name)
    lr_e = get_lr_string(bone.name, True)

    # Normal bones
    if not bone.mmd_bone_map.startswith('F_'):
        bone.mmd_bone.name_j = lr_j + name_j + bone.mmd_bone_suffix
        bone.mmd_bone.name_e = lr_e + name_e + bone.mmd_bone_suffix
        return

    # Finger mode    
    b = bone.bone
    count = 1
    while len(b.children):
        b = b.children[0]
        count+=1
    
    num_j_dic = {
        0:'０',
        1:'１',
        2:'２',
        3:'３',
    }
    
    bone_num = 3 - count if bone.mmd_bone_map == 'F_THUMB' else 4-count
    b = bone.bone
    while True:
        bone.id_data.pose.bones[b.name].mmd_bone.name_j = lr_j + name_j + num_j_dic[bone_num] + bone.mmd_bone_suffix
        bone.id_data.pose.bones[b.name].mmd_bone.name_e = lr_e + name_e + str(bone_num) + bone.mmd_bone_suffix
        bone_num += 1
        if not len(b.children):
            break
        b = b.children[0]

    return


user_bones = []
# load bone definitions from csv
def load_user_bones_from_csv(filepath):
    with open(filepath, 'r') as fp:
        next(fp) # skip header
        for line in fp:
            array = line.split(',')
            if len(array) != 5:
                continue

            (cat, id, name_j, name_e, essential) = [i.strip() for i in array]

            if cat not in _cat_table.keys():
                print(f'User pmx bone definitions: Category {cat} is not defined. Ignoring this definition.')
                continue
            if id in _bone_table.keys():
                print(f'User pmx bone definitions: Bone ID {id} is already used. Ignoring this definition.')
                continue

            append_bone_internal(id, name_j, name_e, essential, cat)
            user_bones.append(id)

# clear user bone definitions
def clear_user_bones():
    for id in user_bones:
        remove_bone_internal(id)
    user_bones.clear()
    return

# initialize internal data
def init():
    # init idx
    _idx_table['NONE'] = 0

    # init cat_table
    for cat in mmd_bone_definition.categories.keys():
        _cat_table[cat] = []

    # init bone_table
    for cat, definitions in mmd_bone_definition.bones.items():
        for bone_data in definitions:
            (id, name_j, name_e, essential) = bone_data
            append_bone_internal(id, name_j, name_e, essential, cat)

init()
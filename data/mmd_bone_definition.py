# PMX Bone definitions
# Please change this file carefully, for your convenience

# Bone category for display purpose - ID : (name, desc) 
categories={
    'ROOT': ('Root', 'Root bones. eg: master / center / groove...'),
    'TORSO': ('Torso', 'Torso bones. eg: hips / upper_body / upper_body2...'),
    'FACIAL': ( 'Facials', 'Facial bones. eg: eye / eyebrow / mouth...'),
    'ARMS': ('Upper Limbs', 'Arm bones. eg: arm / forearm / hand...'),
    'LEGS': ('Lower Limbs', 'Leg bones. eg: leg / knee / ankle...'),
    'FINGERS': ('Fingers', 'Finger bones. eg: thumb / index / middle...'),
    'IK': ('IK', 'IK bones. eg: ankle_ik / wrist_ik...'),
    'PHYS': ('Physics', 'Physics bones. eg: breast / hair_xx...'),
    'OTHER': ('Others', 'Other bones. For any purpose you need'),
}

# Bone definition - categoryID : list of ( boneID, name_j, name_e, is_essential )
bones={
    'ROOT':[
        ('', 'なし', 'none', False),
        ('MASTER', '全ての親', 'master', True),
        ('CENTER', 'センター', 'center', True),
        ('GROOVE', 'グルーブ', 'groove', False),
        ('WAIST', '腰', 'waist', False),
    ],

    'TORSO':[
        ('LOWER_BODY', '下半身', 'lower body', True),
        ('UPPER_BODY', '上半身', 'upper body', True),
        ('UPPER BODY 2', '上半身2', 'upper body 2', True),
        ('NECK', '首', 'neck', True),
        ('HEAD', '頭', 'head', True),
    ],

    'FACIAL':[
        ('EYE', '目', 'eye', True),
        ('EYES','両目', 'eyes', True),
    ],
    
    'ARMS':[
        ('SHOULDER', '肩', 'shoulder', True),
        ('ARM', '腕', 'arm', True),
        ('ARM_TWIST', '腕捩', 'arm twist', True),
        ('ELBOW', 'ひじ', 'elbow', True),
        ('WRIST_TWIST', '手捩', 'wrist twist', True),
        ('WRIST', '手首', 'wrist', True),
    ],

    'FINGERS':[
        ('F_THUMB', '親指', 'thumb', True),
        ('F_INDEX', '人指', 'index', True),
        ('F_MIDDLE', '中指', 'middle', True),
        ('F_RING', '薬指', 'ring', True),
        ('F_LITTLE', '小指', 'little', True),
    ],

    'LEGS':[
        ('LEG', '足', 'leg', True),
        ('KNEE', 'ひざ', 'knee', True),
        ('ANKLE', '足首', 'ankle', True),
        ('TOE', 'つま先', 'toe', True),
    ],

    'IK':[
        ('ANKLE_IK', '足ＩＫ', 'ankle_ik', False),
        ('TOE_IK', 'つま先ＩＫ', 'toe_ik', False),
    ],

    'PHYS':[
    ],
}

# Bone name aliases - boneID : list of aliases
# This is used to match bone names in the model to the defined bone IDs.
# The first alias in the list is the primary MMD bone name.
aliases = {
    'MASTER' : ('全ての親', 'master', 'root', 'origin'),
    'CENTER' : ('センター', 'center', 'centre'),
    'GROOVE' : ('グルーブ', 'groove'),
    'WAIST' : ('腰', 'waist', 'hip'),
    'LOWER_BODY' : ('下半身', 'lowerbody', 'pelvis'),
    'UPPER_BODY' : ('上半身', 'upperbody', 'torso', 'spine'),
    'UPPER BODY 2' : ('上半身2', 'upperbody2', 'chest'),
    'NECK' : ('首', 'neck'),
    'HEAD' : ('頭', 'head', 'face'),
    'EYE' : ('目', 'eye'),
    'EYES': ('両目', 'eyes'),
    'SHOULDER' : ('肩', 'shoulder', 'clavicle'),
    'ARM' : ('腕', 'arm', 'upperarm'),
    'ARM_TWIST' : ('腕捩', 'armtw', 'armtwist', 'upperarmtwist'),
    'ELBOW' : ('ひじ', 'elbow', 'forearm', 'lowerarm'),
    'WRIST_TWIST' : ('手捩', 'wristtwist', 'wristtw', 'handtwist', 'handtw', 'forearmtwist', 'forearmtw', 'lowerarmtwist', 'lowerarmtw'),
    'WRIST' : ('手首', 'wrist', 'hand'),
    'F_THUMB' : ('親指', 'thumb', 'fthumb'),
    'F_INDEX' : ('人指', 'index', 'findex'),
    'F_MIDDLE' : ('中指', 'middle', 'fmiddle'),
    'F_RING' : ('薬指', 'ring', 'fring'),
    'F_LITTLE' : ('小指', 'little', 'pinky', 'flittle', 'fpinky'),
    'LEG' : ('足', 'leg', 'thigh', 'upperleg'),
    'KNEE' : ('ひざ', 'knee', 'calf', 'shin', 'lowerleg'),
    'ANKLE' : ('足首', 'ankle', 'foot'),
    'TOE' : ('つま先', 'toe', 'forefoot'),
    'ANKLE_IK' : ('足ＩＫ', 'ankleik', 'footik', 'ikankle', 'ikfoot'),
    'TOE_IK' : ('つま先ＩＫ', 'toeik', 'iktoe'),
}

def bone_id_from_name(name: str) -> str:
    """ Get bone ID from bone name """
    # Remove '_' from the name and convert to lowercase
    name = name.replace('_', '').strip().lower()

    for bone_id, aliases_list in aliases.items():
        if name in aliases_list:
            return bone_id
    return ''  # Return empty string if no match found

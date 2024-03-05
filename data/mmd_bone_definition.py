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
        ('MASTER', '全ての親', 'master', True),
        ('CENTER', 'センター', 'center', True),
        ('GROOVE', 'グルーブ', 'groove', False),
        ('WAIST', '腰', 'waist', False),
    ],

    'TORSO':[
        ('HIPS', '下半身', 'lower body', True),
        ('SPINE', '上半身', 'upper body', True),
        ('CHEST', '上半身2', 'upper body 2', True),
        ('NECK', '首', 'neck', True),
        ('HEAD', '頭', 'head', True),
    ],

    'FACIAL':[
        ('EYE', '目', 'eye', True),
        ('EYES','両目', 'eyes', True),
    ],
    
    'ARMS':[
        ('SHOULDER', '肩', 'shoulder', True),
        ('UPPER_ARM', '腕', 'arm', True),
        ('ARM_TWIST', '腕捩', 'arm twist', True),
        ('LOWER_ARM', 'ひじ', 'elbow', True),
        ('HAND_TWIST', '手捩', 'wrist twist', True),
        ('HAND', '手首', 'wrist', True),
    ],

    'FINGERS':[
        ('F_THUMB', '親指', 'thumb', True),
        ('F_INDEX', '人指', 'index', True),
        ('F_MIDDLE', '中指', 'middle', True),
        ('F_RING', '薬指', 'ring', True),
        ('F_LITTLE', '小指', 'little', True),
    ],

    'LEGS':[
        ('UPPER_LEG', '足', 'leg', True),
        ('LOWER_LEG', 'ひざ', 'knee', True),
        ('FOOT', '足首', 'ankle', True),
        ('TOE', 'つま先', 'toe', True),
    ],

    'IK':[
        ('FOOT_IK', '足ＩＫ', 'ankle_ik', False),
        ('TOE_IK', 'つま先ＩＫ', 'toe_ik', False),
    ],

    'PHYS':[
    ],
}

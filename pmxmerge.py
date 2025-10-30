"""
pmxmerge.py - A script to merge PMX models by patching bones, materials, etc.
Version 1.3.0

This script merges two PMX models: a base model and a patch model.

The main purpose is to update existing model with partially edited model which is exported from DCC tools like Blender, Maya, etc.
Or you can use it to make an chimera model by merging multiple models together (e.g. combining a character model with a prop model).
The patch model can contain new bones, materials, morphs, and physics, which are merged into the base model.

- These features can be appended or updated by selection from the patch model to the base model:
    - Bones: New bones are appended, existing bones can be updated if specified.
    - Materials: New materials and their mesh data (vertices, faces, vertex/uv morophs) are appended/merged, existing materials settings can be updated if specified.
    - Morphs: New morphs (Material, Bone, Group) are appended, existing morphs can be updated if specified.
    - Physics: New rigid bodies and joints are appended, existing settings can be updated if specified.
    - Display Items: New display groups and their entries are appended, existing display groups can be replaced if specified.

- NOTE:
    - This script now supports models with duplicate names and unnamed elements. A warning will be issued if such elements are found.
    - When updating an element by name, the script will target the first element found with that name in the base model, following the behavior of the pypmx module.
    - The script only supports PMX 2.0.
    
- Unsupported features (Raises error when loading):
    - PMX 2.1 features:
        - QDEF Weights
        - Vertex Colors
        - Flip Morphs
        - Impulse Morphs
        - Joints other than Spring 6DOF
        - Soft Body Settings (no one uses it anyway)

Copyright (c) 2025 Kafuji Sato

LICENCE: GPL-3.0-or-later (https://www.gnu.org/licenses/gpl-3.0.en.html)
"""

import os
from typing import Dict, Set, Tuple, List

from . import pypmx  # Import the pypmx module for PMX model manipulation

import logging
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s : %(levelname)s - %(message)s')

def report_problematic_elements(model: pypmx.Model) -> Tuple[bool, List[str]]:
    """Check for duplicate or unnamed elements and log them as warnings.
    Returns True if any problematic elements are found.
    """
    msgs = []
    has_problems = False

    def check(collection: pypmx.NamedElements, element_type: str) -> bool:
        """Check for duplicate and unnamed items in the list."""
        seen_names = set()
        collection_has_problems = False
        for i, item in enumerate(collection):
            if not item.name:
                msg = f"Unnamed item found: (type: {element_type}, index: {i})"
                msgs.append(msg)
                logging.warning(msg)
                collection_has_problems = True
                continue
            
            if item.name in seen_names:
                msg = f"Duplicate item found: '{item.name}' (type: {element_type}, index: {i})"
                msgs.append(msg)
                logging.warning(msg)
                collection_has_problems = True
            else:
                seen_names.add(item.name)
        return collection_has_problems

    if check(model.bones, "Bone"): has_problems = True
    if check(model.materials, "Material"): has_problems = True
    if check(model.morphs, "Morph"): has_problems = True
    if check(model.display_slots, "DisplaySlot"): has_problems = True
    if check(model.rigids, "RigidBody"): has_problems = True
    if check(model.joints, "Joint"): has_problems = True

    return has_problems, msgs


def append_update_bones(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new bones from patch to base model, update existing bones if specified."""
    if 'BONE' not in append and ('BONE_LOC' not in update and 'BONE_SETTING' not in update):
        return

    logging.info(f"🦴 -------- Merging Bones -------- 🦴")

    # Append New Bones
    if 'BONE' in append:
        appended = []
        appended_names = set()
        for bone in patch.bones:
            if not bone.name: # Always append unnamed bones
                base.bones.append(bone)
                appended.append(bone)
                logging.info(f"➕️ New Unnamed Bone Appended (index: {len(base.bones) - 1})")
                continue
            
            if bone.name not in base.bones and bone.name not in appended_names:
                base.bones.append(bone)
                appended.append(bone)
                appended_names.add(bone.name)
                logging.info(f"➕️ New Bone Appended: '{bone.name}' (index: {len(base.bones) - 1})")
        
        if appended:
            logging.info(f"➕️ Appended {len(appended)} new bones from patch.")
        else:
            logging.info("☑ No new bones to append from patch.")

    # Update Existing Bone settings
    updated = []
    if any(b in update for b in ['BONE_LOC', 'BONE_SETTING']):
        processed_bones = set()
        for bone in (b for b in patch.bones if b.name and b.name in base.bones and b.name not in processed_bones):
            b_base:pypmx.Bone = base.bones[bone.name]
            b_base.name_e = bone.name_e

            if 'BONE_LOC' in update:
                attributes = ['location', 'disp_connection_type', 'disp_connection_bone', 'disp_connection_vector']
                for attr in attributes:
                    setattr(b_base, attr, getattr(bone, attr))

            if 'BONE_SETTING' in update:
                attributes = [
                    'parent', 'trans_order', 'trans_after_physics',
                    'is_rotatable', 'is_movable', 'is_visible', 'is_controllable',
                    'has_add_rot', 'has_add_loc', 'add_trans_bone', 'add_trans_value',
                    'fixed_axis', 'local_coord',
                    'is_ik', 'ik_target', 'loop_count', 'rotation_unit', 'ik_links'

                ]
                for attr in attributes:
                    setattr(b_base, attr, getattr(bone, attr))
            updated.append(bone)
            processed_bones.add(bone.name)
            logging.debug(f"♻️ Updated: '{b_base.name}' (index: {base.bones.index(b_base)})")

    if updated:
        logging.info(f"♻️ Updated {len(updated)} existing bones with new settings from patch.")
    else:
        logging.info("☑ No existing bones to update from patch.")

    logging.info("✔️ Finished Merging Bones.")
    return


def append_update_material(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new materials and their mesh data from patch to base model, update existing material settings if specified."""
    if 'MATERIAL' not in append and ('MAT_GEOM' not in update and 'MAT_SETTING' not in update):
        return

    logging.info("🧵 -------- Merging Materials -------- 🧵")

    if 'MATERIAL' in append or 'MAT_GEOM' in update:
        base.append_vertices(patch.vertices)

    for tex in patch.textures:
        base.ensure_texture(tex)

    if 'MATERIAL' in append:
        appended = []
        appended_names = set()
        for mat in patch.materials:
            if not mat.name:
                base.materials.append(mat)
                appended.append(mat)
                logging.info(f"➕️ New Unnamed Material Appended (index: {len(base.materials) - 1})")
                continue

            if mat.name not in base.materials and mat.name not in appended_names:
                base.materials.append(mat)
                appended.append(mat)
                appended_names.add(mat.name)
                logging.info(f"➕️ New Material Appended: '{mat.name}' (index: {len(base.materials) - 1})")

        if appended:
            logging.info(f"➕️ Appended {len(appended)} new materials from patch.")
        else:
            logging.info("☑ No new materials to append from patch.")

    if 'MAT_GEOM' in update:
        updated = []
        processed_mats = set()
        for mat in (m for m in patch.materials if m.name and m.name in base.materials and m.name not in processed_mats):
            base.replace_material_faces(base.materials[mat.name], mat.faces)
            updated.append(mat)
            processed_mats.add(mat.name)
            logging.debug(f"♻️ Updated faces for: '{mat.name}' (index: {base.materials.index(base.materials[mat.name])})")

        if updated:
            logging.info(f"♻️ Updated {len(updated)} existing materials with new faces from patch.")
        else:
            logging.info("☑ No existing materials to update from patch.")

    appended_morphs, updated_morphs = [], []
    appended_morph_names = set()
    processed_morphs = set()
    for morph in (m for m in patch.morphs if isinstance(m, (pypmx.VertexMorph, pypmx.UVMorph))):
        if not morph.name:
            base.morphs.append(morph)
            appended_morphs.append(morph)
            logging.info(f"➕️ New Unnamed Vertex/UV Morph Appended (index: {len(base.morphs) - 1})")
            continue
        
        if morph.name not in base.morphs and morph.name not in appended_morph_names:
            base.morphs.append(morph)
            appended_morphs.append(morph)
            appended_morph_names.add(morph.name)
            logging.debug(f"➕️ Morph Appended: '{morph.name}' (index: {len(base.morphs) - 1})")
        elif morph.name in base.morphs and morph.name not in processed_morphs:
            base_morph = base.morphs.get(morph.name)
            if type(base_morph) is not type(morph):
                logging.warning(f"🧬 Morph type mismatch: '{morph.name}' (base: {base_morph.type_name()}, patch: {morph.type_name()}), replacing instead of merging.")
                base.morphs[morph.name] = morph
            else:
                base_morph.offsets.extend(morph.offsets)
            updated_morphs.append(morph)
            processed_morphs.add(morph.name)
            logging.debug(f"♻️ Vertex/UV Morph Updated: '{morph.name}' (index: {base.morphs.index(base_morph)})")

    if appended_morphs: logging.info(f"➕️ Appended {len(appended_morphs)} new morphs (Vertex, UV) from patch.")
    if updated_morphs: logging.info(f"♻️ Updated {len(updated_morphs)} existing morphs (Vertex, UV) with new offsets from patch.")

    updated = []
    if 'MAT_SETTING' in update:
        processed_mats = set()
        logging.info("🧵 Updating material settings...")
        for mat in (m for m in patch.materials if m.name and m.name in base.materials and m.name not in processed_mats):
            base.materials[mat.name] = mat # This replaces the entire material object
            updated.append(mat)
            processed_mats.add(mat.name)
            logging.debug(f"♻️ Replaced: '{mat.name}' (index: {base.materials.index(mat.name)})")
    if updated:
        logging.info(f"♻️ Updated {len(updated)} existing materials with new settings from patch.")
    else:
        logging.info("☑ No existing materials to update from patch.")

    logging.info("✔️ Finished Merging Materials.")
    return


def append_update_morphs(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new morphs from patch to base model, update existing morph settings if specified."""
    if 'MORPH' not in append and 'MORPH' not in update:
        return

    logging.info(f"🧬 -------- Merging Material/Bone/Group Morphs -------- 🧬")

    appended, updated = [], []
    appended_names, processed_names = set(), set()

    morphs_to_process = [m for m in patch.morphs if not isinstance(m, (pypmx.VertexMorph, pypmx.UVMorph))]

    if 'MORPH' in append:
        for morph in morphs_to_process:
            if not morph.name:
                base.morphs.append(morph)
                appended.append(morph)
                logging.info(f"➕️ New Unnamed Morph Appended (type: {morph.type_name()}, index: {len(base.morphs) - 1})")
                continue
            
            if morph.name not in base.morphs and morph.name not in appended_names:
                base.morphs.append(morph)
                appended.append(morph)
                appended_names.add(morph.name)
                logging.debug(f"➕️ New Morph Appended: '{morph.name}' (index: {len(base.morphs) - 1})")

    if 'MORPH' in update:
        logging.info("♻️ Updating morph settings (Material, Bone, Group)...")
        for morph in (m for m in morphs_to_process if m.name and m.name in base.morphs and m.name not in processed_names):
            base.morphs[morph.name] = morph
            updated.append(morph)
            processed_names.add(morph.name)
            logging.debug(f"♻️ Updated: '{morph.name}' (index: {base.morphs.index(morph.name)})")

    if appended: logging.info(f"➕️ Appended {len(appended)} new morphs (Material, Bone, Group) from patch.")
    else: logging.info("☑ No new Material/Bone/Group morphs to append from patch.")
    if updated: logging.info(f"♻️ Updated {len(updated)} existing morphs (Material, Bone, Group) with new settings from patch.")
    else: logging.info("☑ No existing Material/Bone/Group morphs to update from patch.")

    logging.info("✔️ Finished Merging Morphs.")
    return


def append_update_physics(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new rigid bodies and joints from patch to base model, update existing settings if specified."""
    if 'PHYSICS' not in append and 'PHYSICS' not in update:
        return

    logging.info(f"🪨 -------- Merging Physics -------- 🪨")

    if 'PHYSICS' in append:
        appended_rigids, appended_joints = [], []
        appended_rigid_names, appended_joint_names = set(), set()
        
        for rigid in patch.rigids:
            if not rigid.name:
                base.rigids.append(rigid)
                appended_rigids.append(rigid)
                logging.info(f"➕️ New Unnamed Rigid Body Appended (index: {len(base.rigids) - 1})")
                continue
            if rigid.name not in base.rigids and rigid.name not in appended_rigid_names:
                base.rigids.append(rigid)
                appended_rigids.append(rigid)
                appended_rigid_names.add(rigid.name)
                logging.info(f"➕️ New Rigid Body Appended: '{rigid.name}' (index: {len(base.rigids) - 1})")
        
        for joint in patch.joints:
            if not joint.name:
                base.joints.append(joint)
                appended_joints.append(joint)
                logging.info(f"➕️ New Unnamed Joint Appended (index: {len(base.joints) - 1})")
                continue
            if joint.name not in base.joints and joint.name not in appended_joint_names:
                base.joints.append(joint)
                appended_joints.append(joint)
                appended_joint_names.add(joint.name)
                logging.info(f"➕️ New Joint Appended: '{joint.name}' (index: {len(base.joints) - 1})")

        if appended_rigids: logging.info(f"➕️ Appended {len(appended_rigids)} new rigid bodies from patch.")
        else: logging.info("☑ No new rigid bodies to append from patch.")
        if appended_joints: logging.info(f"➕️ Appended {len(appended_joints)} new joints from patch.")
        else: logging.info("☑ No new joints to append from patch.")

    if 'PHYSICS' in update:
        updated_rigids, updated_joints = [], []
        processed_rigid_names, processed_joint_names = set(), set()

        logging.info("🪨 Updating existing rigidbody settings...")
        for rigid in (r for r in patch.rigids if r.name and r.name in base.rigids and r.name not in processed_rigid_names):
            base.rigids[rigid.name] = rigid
            updated_rigids.append(rigid)
            processed_rigid_names.add(rigid.name)
            logging.debug(f"♻️ Updated Rigid Body: '{rigid.name}' (index: {base.rigids.index(rigid.name)})")
        
        logging.info("🔗 Updating existing joint settings...")
        for joint in (j for j in patch.joints if j.name and j.name in base.joints and j.name not in processed_joint_names):
            base.joints[joint.name] = joint
            updated_joints.append(joint)
            processed_joint_names.add(joint.name)
            logging.debug(f"♻️ Updated Joint: '{joint.name}' (index: {base.joints.index(joint.name)})")

        if updated_rigids: logging.info(f"♻️ Updated {len(updated_rigids)} existing rigid bodies with new settings from patch.")
        else: logging.info("☑ No existing rigid bodies to update from patch.")
        if updated_joints: logging.info(f"♻️ Updated {len(updated_joints)} existing joints with new settings from patch.")
        else: logging.info("☑ No existing joints to update from patch.")

    logging.info("✔️ Finished Merging Physics.")
    return


def append_update_displayitems(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new display groups and their entries from patch to base model, update existing display groups if specified."""
    if 'DISPLAY' not in append and 'DISPLAY' not in update:
        return

    logging.info(f"📺 -------- Merging Display Slots -------- 📺")

    if 'DISPLAY' in append:
        appended_slots = []
        appended_slot_names = set()
        for slot in patch.display_slots:
            if not slot.name:
                base.display_slots.append(slot)
                appended_slots.append(slot)
                logging.info(f"📺 New Unnamed Display Slot Appended (index: {len(base.display_slots) - 1})")
                continue
            
            if slot.name not in base.display_slots and slot.name not in appended_slot_names:
                base.display_slots.append(slot)
                appended_slots.append(slot)
                appended_slot_names.add(slot.name)
                logging.info(f"📺 New Display Slot Appended: '{slot.name}' (index: {len(base.display_slots) - 1})")

        if appended_slots:
            logging.info(f"📺 Appended {len(appended_slots)} new display slots from patch.")
        else:
            logging.info("☑ No new display slots to append from patch.")

        for slot in (d for d in patch.display_slots if d.name and d.name in base.display_slots):
            base_slot = base.display_slots.get(slot.name)
            appended_items = []
            
            base_item_tuples = {(item.disp_type, item.name) for item in base_slot.items}
            for item in slot.items:
                item_tuple = (item.disp_type, item.name)
                if item_tuple not in base_item_tuples:
                    base_slot.items.append(item)
                    appended_items.append(item)
                    base_item_tuples.add(item_tuple)
            
            if appended_items:
                logging.info(f"📺 Appended {len(appended_items)} new items to display slot '{slot.name}' from patch.")

    if 'DISPLAY' in update:
        updated = []
        processed_names = set()
        logging.info("📺 Replacing existing Display Slots...")
        for slot in (d for d in patch.display_slots if d.name and d.name in base.display_slots and d.name not in processed_names):
            base.display_slots[slot.name] = slot
            updated.append(slot)
            processed_names.add(slot.name)
            logging.debug(f"📺 Replaced Display Group: '{slot.name}' (index: {base.display_slots.index(slot.name)})")
        if updated:
            logging.info(f"📺 Updated {len(updated)} existing display slots with new settings from patch.")
        else:
            logging.info("☑ No existing display slots to update from patch.")

    return


def merge_models(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Merge patch model into base model, appending and updating specified features."""
    logging.info("🔄 Merging Models...")
    append_update_bones(base, patch, append, update)
    append_update_material(base, patch, append, update)
    append_update_morphs(base, patch, append, update)
    append_update_physics(base, patch, append, update)
    append_update_displayitems(base, patch, append, update)
    logging.info("✔️ Finished Merging Models.")
    return


def post_load_report(model: pypmx.Model, name:str) -> None:
    """Print a report of the model's structure after loading."""
    face_count = sum(len(m.faces) for m in model.materials)
    logging.info(f"{name}: {len(model.vertices)} vertices, {face_count} faces, {len(model.bones)} bones, {len(model.materials)} materials, {len(model.morphs)} morphs, {len(model.rigids)} rigids, {len(model.joints)} joints.")
    return

def report_empty_morphs(model: pypmx.Model) -> None:
    """Report empty morphs in the model."""
    empty_morphs = [m for m in model.morphs if isinstance(m, pypmx.VertexMorph) and not m.offsets]
    if empty_morphs:
        logging.info("FYI: The following VertexMorphs are empty and will not have any effect on the model:")
        for morph in empty_morphs:
            logging.info(f"  - {morph.name} (index: {model.morphs.index(morph)})")
    else:
        print("No empty VertexMorphs found.")


def load_pmx_file(path: str) -> pypmx.Model:
    """Load a PMX model from the specified path."""
    try:
        model = pypmx.load(path)
        return model
    except Exception as e:
        print(f"Error loading PMX model from '{path}': {e}")


def save_pmx_file(model: pypmx.Model, path: str) -> Tuple[bool, str]:
    """Save a PMX model to the specified path."""
    try:
        pypmx.save(path, model)
    except Exception as e:
        logging.error(f"Error saving PMX model to '{path}': {e}")
        raise
    return True, "Model saved successfully."


options_default: Dict[str, Set[str]] = {
    "append": {'MATERIAL', 'BONE', 'MORPH', 'PHYSICS', 'DISPLAY'},
    "update": {'MAT_GEOM', 'MAT_SETTING', 'BONE_LOC', 'BONE_SETTING', 'MORPH', 'PHYSICS', 'DISPLAY'},
}

def merge_pmx_files(
            path_base:str, 
            path_patch:str, 
            path_out:str, 
            append: Set = options_default['append'],
            update: Set = options_default['update'],
        ) -> Tuple[bool, str]:
    """Merge two PMX models: a base model and a patch model. Returns a tuple of success status and message."""
    logging.info(f"▶️ Starting merge: {path_base} + {path_patch} -> {path_out}")
    logging.info(f"🔧 Options: Append: {append}, Update: {update}")

    if not path_base or not path_patch or not path_out:
        return False, "Base, patch and output paths must be specified."
    if path_base == path_patch:
        return False, "Base and patch files cannot be the same."
    if path_out == path_base:
        logging.warning("NOTICE: Overwriting the base model.")

    base = load_pmx_file(path_base)
    if not base:
        return False, f"Failed to load base model from '{path_base}'. Please check the file path and format."
    post_load_report(base, f"Base model '{path_base}'")

    if not os.path.isabs(path_out) and os.path.isabs(path_base):
        base_dir = os.path.dirname(path_base)
        path_out = os.path.join(base_dir, path_out)

    logging.info(f"Validating base model for problematic elements (duplicates, unnamed)...")
    report_problematic_elements(base)

    patch = load_pmx_file(path_patch)
    if not patch:
        return False, f"Failed to load patch model from '{path_patch}'. Please check the file path and format."
    post_load_report(patch, f"Patch model '{path_patch}'")

    logging.info(f"Validating patch model for problematic elements (duplicates, unnamed)...")
    report_problematic_elements(patch)

    logging.info(f"Options: Appending {append} from patch model, updating {update} in base model.")
    merge_models(base, patch, append=append, update=update)

    ret, msg = save_pmx_file(base, path_out)
    if not ret:
        return False, f"Failed to save merged model to '{path_out}': {msg}"

    post_load_report(base, f"Successfully saved '{path_out}'")
    return True, f"Merge completed successfully ({path_base} + {path_patch} -> {path_out})"
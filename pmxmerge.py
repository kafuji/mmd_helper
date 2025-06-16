"""
pmxmerge.py - A script to merge PMX models by patching bones, materials, etc.
Version 1.2.0

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
    - Bones and Materials are always appended, even if not specified in the append options.
    - Morphs, Physics, and Display Items are only appended if specified in the append options.
    - The script checks for duplicate/unnamed elements in the base and patch models. You should fix them before merging.
    - The script only supports PMX 2.0.
    
- Unsupported features (Raises error when loading):
    - Duplicate names in the model elements (bones, materials, morphs, etc.)
    - Unnamed elements in the model (bones, materials, morphs, etc.)
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
from typing import Dict, Set, Tuple

from . import pypmx  # Import the pypmx module for PMX model manipulation

import logging
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s : %(levelname)s - %(message)s')

def validate_elements(model: pypmx.Model) -> bool:
    """Check for duplicate elements. Also check unnamed elements. Returns True if either duplicates or unnamed elements are found."""

    def check(collection: list) -> bool:
        """Check if there are duplicate items in the list."""
        seen = set()
        duplicate_found = False
        unnamed_found = False
        for item in collection:
            if not item.name:
                logging.critical(f"Unnamed item found: {item} (type: {type(item)}, index: {collection.index(item)})")
                unnamed_found = True
                continue
            if item.name in seen:
                logging.critical(f"Duplicate item found: {item.name} (type: {type(item)}, index: {collection.index(item)})")
                duplicate_found = True
                continue
            seen.add(item.name)
        return duplicate_found or unnamed_found

    ret = False
    ret |= check(model.bones)
    ret |= check(model.materials)
    ret |= check(model.morphs)
    ret |= check(model.display_slots)
    ret |= check(model.rigids)
    ret |= check(model.joints)

    return ret


def append_update_bones(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new bones from patch to base model, update existing bones if specified."""
    if 'BONE' not in append and ('BONE_LOC' not in update and 'BONE_SETTING' not in update):
        return

    logging.info(f"🦴 -------- Merging Bones -------- 🦴")

    # Append New Bones
    if 'BONE' in append:
        appended = []
        for bone in (b for b in patch.bones if b.name not in base.bones):
            base.bones.append(bone)
            appended.append(bone)
            logging.info(f"➕️ New Bone Appended: '{bone.name}' (index: {len(base.bones) - 1})")
        if appended:
            logging.info(f"➕️ Appended {len(appended)} new bones from patch.")
        else:
            logging.info("☑ No new bones to append from patch.")

    # Update Existing Bone settings
    updated = []
    if any(b in update for b in ['BONE_LOC', 'BONE_SETTING']):
        for bone in (b for b in patch.bones if b.name in base.bones):
            b:pypmx.Bone = base.bones[bone.name]
            b.name_e = bone.name_e

            if 'BONE_LOC' in update:
                attributes = ['location', 'disp_connection_type', 'disp_connection_bone', 'disp_connection_vector']
                for attr in attributes:
                    setattr(b, attr, getattr(bone, attr))

            if 'BONE_SETTING' in update:
                attributes = [
                    'parent', 'trans_order', 'trans_after_physics',
                    'is_rotatable', 'is_movable', 'is_visible', 'is_controllable',
                    'has_add_rot', 'has_add_loc', 'add_trans_bone', 'add_trans_value',
                    'fixed_axis', 'local_coord',
                    'is_ik', 'ik_target', 'loop_count', 'rotation_unit', 'ik_links'

                ]
                for attr in attributes:
                    setattr(b, attr, getattr(bone, attr))
            updated.append(bone)
            logging.debug(f"♻️ Updated: '{b.name}' (index: {base.bones.index(b)})")

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

    # Append New Vertices (prun when saving)
    if 'MATERIAL' in append or 'MAT_GEOM' in update:
        base.append_vertices(patch.vertices)

    # Append new textures (prun when saving)
    for tex in patch.textures:
        base.ensure_texture(tex)  # This appends if not exists

    # Append New Materials
    if 'MATERIAL' in append:
        appended = []
        for mat in (m for m in patch.materials if m.name not in base.materials):
            base.materials.append(mat)
            appended.append(mat)
            logging.info(f"➕️ New Material Appended: '{mat.name}' (index: {len(base.materials) - 1})")

        if appended:
            logging.info(f"➕️ Appended {len(appended)} new materials from patch.")
        else:
            logging.info("☑ No new materials to append from patch.")

    # Update Existing Material Geometry
    if 'MAT_GEOM' in update:
        updated = []
        for mat in (m for m in patch.materials if m.name in base.materials):
            base.replace_material_faces(base.materials[mat.name], mat.faces)
            updated.append(mat)
            logging.debug(f"♻️ Updated faces for: '{mat.name}' (index: {base.materials.index(base.materials[mat.name])})")

        if updated:
            logging.info(f"♻️ Updated {len(updated)} existing materials with new faces from patch.")
        else:
            logging.info("☑ No existing materials to update from patch.")

    # Append/Merge Vertex/UV Morphs here (because they are part of mesh data)
    appended = []
    updated = []
    for morph in (m for m in patch.morphs if isinstance(m, (pypmx.VertexMorph, pypmx.UVMorph))):
        if morph.name not in base.morphs: # Append new Vertex/UV morphs
            base.morphs.append(morph)
            appended.append(morph)
            logging.debug(f"➕️ Morph Appended: '{morph.name}' (index: {len(base.morphs) - 1})")
        else: # Update existing Vertex/UV morphs
            base_morph = base.morphs.get(morph.name)
            if type(base_morph) is not type(morph):
                logging.warning(f"🧬 Morph type mismatch: '{morph.name}' (base: {base_morph.type_name()}, patch: {morph.type_name()}), replacing instead of merging.")
                base.morphs[morph.name] = morph  # Replace with patch morph
                continue
            base_morph.offsets.extend(morph.offsets)
            updated.append(morph)
            logging.debug(f"♻️ Vertex/UV Morph Updated: '{morph.name}' (index: {base.morphs.index(base_morph)})")

    if appended:
        logging.info(f"➕️ Appended {len(appended)} new morphs (Vertex, UV) from patch.")
    else:
        logging.info("☑ No new Vertex/UV morphs to append from patch.")
    if updated:
        logging.info(f"♻️ Updated {len(updated)} existing morphs (Vertex, UV) with new offsets from patch.")
    else:
        logging.info("☑ No existing Vertex/UV morphs to update from patch.")

    # Update existing Material Settings
    updated = []
    if 'MAT_SETTING' in update:
        logging.info("🧵 Updating material settings...")
        for mat in (m for m in patch.materials if m.name in base.materials):
            index = base.materials.index(mat.name)
            base.materials[index] = mat
            updated.append(mat)
            logging.debug(f"♻️ Replaced: '{mat.name}' (index: {index})")
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


    # Handle Material Morphs, Bone Morphs, and Group Morphs (Vertex and UV Morphs are handled at append_update_material)
    appended = []
    updated = []
    if 'MORPH' in append:
        for morph in (m for m in patch.morphs if m.name not in base.morphs):
            if isinstance(morph, (pypmx.VertexMorph, pypmx.UVMorph)):
                continue # Already handled in append_update_material
            base.morphs.append(morph)
            appended.append(morph)
            logging.debug(f"➕️ New Morph Appended: '{morph.name}' (index: {len(base.morphs) - 1})")

    if 'MORPH' in update:
        logging.info("♻️ Updating morph settings (Material, Bone, Group)...")
        for morph in (m for m in patch.morphs if m.name in base.morphs):
            if isinstance(morph, (pypmx.VertexMorph, pypmx.UVMorph)):
                continue # Already handled in append_update_material

            base.morphs[morph.name] = morph  # Replace with patch morph
            updated.append(morph)
            logging.debug(f"♻️ Updated: '{morph.name}' (index: {base.morphs.index(morph.name)})")

    if appended:
        logging.info(f"➕️ Appended {len(appended)} new morphs (Material, Bone, Group) from patch.")
    else:
        logging.info("☑ No new Material/Bone/Group morphs to append from patch.")
    if updated:
        logging.info(f"♻️ Updated {len(updated)} existing morphs (Material, Bone, Group) with new settings from patch.")
    else:
        logging.info("☑ No existing Material/Bone/Group morphs to update from patch.")


    logging.info("✔️ Finished Merging Morphs.")
    return


def append_update_physics(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new rigid bodies and joints from patch to base model, update existing settings if specified."""
    if 'PHYSICS' not in append and 'PHYSICS' not in update:
        return

    logging.info(f"🪨 -------- Merging Physics -------- 🪨")

    # Append
    if 'PHYSICS' in append:
        appended = []
        for rigid in (r for r in patch.rigids if r.name not in base.rigids):
            base.rigids.append(rigid)
            appended.append(rigid)
            logging.info(f"➕️ New Rigid Body Appended: '{rigid.name}' (index: {len(base.rigids) - 1})")
        if appended:
            logging.info(f"➕️ Appended {len(appended)} new rigid bodies from patch.")
        else:
            logging.info("☑ No new rigid bodies to append from patch.")

        for joint in (j for j in patch.joints if j.name not in base.joints):
            base.joints.append(joint)
            appended.append(joint)
            logging.info(f"➕️ New Joint Appended: '{joint.name}' (index: {len(base.joints) - 1})")
        if appended:
            logging.info(f"➕️ Appended {len(appended)} new joints from patch.")
        else:
            logging.info("☑ No new joints to append from patch.")

    # Update
    if 'PHYSICS' in update:
        logging.info("🪨 Updating existing rigidbody settings...")
        updated = []
        for rigid in (r for r in patch.rigids if r.name in base.rigids):
            index = base.rigids.index(rigid.name)
            base.rigids[index] = rigid
            updated.append(rigid)
            logging.debug(f"♻️ Updated Rigid Body: '{rigid.name}' (index: {index})")
        if updated:
            logging.info(f"♻️ Updated {len(updated)} existing rigid bodies with new settings from patch.")
        else:
            logging.info("☑ No existing rigid bodies to update from patch.")


        updated = []
        logging.info("🔗 Updating existing joint settings...")
        for joint in (j for j in patch.joints if j.name in base.joints):
            index = base.joints.index(joint.name)
            base.joints[index] = joint
            updated.append(joint)
            logging.debug(f"♻️ Updated Joint: '{joint.name}' (index: {index})")
        if updated:
            logging.info(f"♻️ Updated {len(updated)} existing joints with new settings from patch.")
        else:
            logging.info("☑ No existing joints to update from patch.")

    logging.info("✔️ Finished Merging Physics.")
    return

def append_update_displayitems(base: pypmx.Model, patch: pypmx.Model, append: Set, update: Set) -> None:
    """Append new display groups and their entries from patch to base model, update existing display groups if specified."""
    if 'DISPLAY' not in append and 'DISPLAY' not in update:
        return

    logging.info(f"📺 -------- Merging Display Slots -------- 📺")

    appended_slots = []
    if 'DISPLAY' in append:
        for slot in (d for d in patch.display_slots if d.name not in base.display_slots):
            base.display_slots.append(slot)
            appended_slots.append(slot)
            logging.info(f"📺 New Display Slot Appended: '{slot.name}' (index: {len(base.display_slots) - 1})")
        if appended_slots:
            logging.info(f"📺 Appended {len(appended_slots)} new display slots from patch.")
        else:
            logging.info("☑ No new display slots to append from patch.")

        # Append each display slot entry from patch to base
        for slot in (d for d in patch.display_slots if d.name in base.display_slots):
            base_slot = base.display_slots.get(slot.name)
            appended_items = []
            for item in slot.items:
                if item not in base_slot.items:
                    base_slot.items.append(item)
                    appended_items.append(item)
                    logging.debug(f"📺 Appended Display Slot Item: '{item}' to '{slot.name}' (index: {base.display_slots.index(base_slot)})")
            if appended_items:
                logging.info(f"📺 Appended {len(appended_items)} new items to display slot '{slot.name}' from patch.")

    updated = []
    if 'DISPLAY' in update:
        logging.info("📺 Replacing existing Display Slots...")
        for slot in (d for d in patch.display_slots if d.name in base.display_slots):
            index = base.display_slots.index(slot.name)
            base.display_slots[index] = slot
            updated.append(slot)
            logging.debug(f"📺 Replaced Display Group: '{slot.name}' (index: {index})")
    if updated:
        logging.info(f"📺 Updated {len(updated)} existing display slots with new settings from patch.")
    else:
        logging.info("☑ No existing display slots to update from patch.")

    return


# Process pmx.Model objects by merging patch into base
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


# Report functions to print model structure and check for empty morphs
def post_load_report(model: pypmx.Model, name:str) -> None:
    """Print a report of the model's structure after loading."""
    logging.info(f"{name}: {len(model.vertices)} vertices, {len(model.bones)} bones, {len(model.materials)} materials, {len(model.morphs)} morphs, {len(model.rigids)} rigids, {len(model.joints)} joints.")
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


# Default options for merging PMX models
options_default: Dict[str, Set[str]] = {
    "append": {'MATERIAL', 'BONE', 'MORPH', 'PHYSICS', 'DISPLAY'},  # Specify which features in the patch model to append to the base model. Bones and materials are always appended.
    "update": {'MAT_GEOM', 'MAT_SETTING', 'BONE_LOC', 'BONE_SETTING', 'MORPH', 'PHYSICS', 'DISPLAY'},  # Specify which features in the base model to update with the patch model
}

# Main function to load, merge, and save PMX model files
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

    # if path_out is relpath, change it to absolute path based on the base model path
    if not os.path.isabs(path_out) and os.path.isabs(path_base):
        base_dir = os.path.dirname(path_base)
        if not base_dir:
            return False, f"Base model path '{path_base}' is not a valid directory."
        path_out = os.path.join(base_dir, path_out)

    # Validate base model elements for duplicates
    if validate_elements(base):
        return False, f"Base model {path_base} has duplicate elements, merging may not work correctly. Please fix the base model before merging."

    patch = load_pmx_file(path_patch)
    if not patch:
        return False, f"Failed to load patch model from '{path_patch}'. Please check the file path and format."
    post_load_report(patch, f"Patch model '{path_patch}'")

    if validate_elements(patch):
        return False, f"Patch model {path_patch} has duplicate elements, merging may not work correctly. Please fix the patch model before merging."

    logging.info(f"Options: Appending {append} from patch model, updating {update} in base model.")
    merge_models(base, patch, append=append, update=update)

    ret, msg = save_pmx_file(base, path_out)
    if not ret:
        return False, f"Failed to save merged model to '{path_out}': {msg}"

    post_load_report(base, f"Successfully saved '{path_out}'")


    # report_empty_morphs(base)
    return True, f"Merge completed successfully ({path_base} + {path_patch} -> {path_out})"

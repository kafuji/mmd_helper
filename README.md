# PMX Export helper for mmd_tools

This is a Blender addon that provides a set of tools to help exporting PMX files for MMD by using mmd_tools.

## Requirements

- Blender 3 and 4 series
- recent mmd_tools

## Features

- Bone mapping utility
  - Map bone names by using bone name definitions (can be customized).
  - Rule based renaming tool. Supporting Japanese LR identifiers.
- Load mmd_material settings and material/object sort order from CSV file from PMX Editor.
- Mine Sweeper - detects flaws that leads unexpected result.

## Usage

1. Install the addon.
2. Open the MMD tab in the tool shelf.
3. Look for the PMX Export Helper panel.
4. Explore the features.

## Bone Mapping Utility

Yet mmd_tools uses bone.mmd_bone.name_j and name_e to export PMX, it is hard to set them manually. This tool provides a way to map the bone names by using bone name definitions.

It supports Semi-Standard Bone set by default, and you can customize the bone name definitions by using a CSV file.

- In pose mode or armature edit mode, select any bone you want to map.
- Slected bones will be listed in the bone list on the panel.
- Configure bone mapping by using the pulldown menu.
- After all bones are mapped, click "Apply" button to apply the mapping to the armature.
- It will set mmd_bone.name_j and name_e to the bone. LR prefix will be automatically generated.

### User bone definition

The user bone definition is a CSV file that contains the mapping of the bone names.
It will append the bone definitions to the default bone definitions.
If you have your standard bone set that needs to be translated in MMD, make one by yorself and load it from the panel.

### Example of user bone definition

```csv
CATEGORY_ID,BONE_ID,Japanese,English,IsEssential?
FACIAL,JAW,顎,jaw,False
PHYS,BREAST,胸,breast,False
PHYS,BELLY,おなか,belly,False
PHYS,THIGH,腿,thigh,False
```

- CATEGORY_ID
  - The category of the bone. It is used for grouping the bones in the panel.
  - Any of {'ROOT', 'TORSO', 'FACIAL', 'ARMS', 'LEGS', 'FINGERS', 'IK', 'PHYS', 'OTHER'}.
- BONE_ID
  - The bone identifier. It can be any string.
- Japanese
  - The Japanese name of the bone. LR prefix "左" and "右" will be automatically generated.
- English
  - The English name of the bone. LR prefix "left" and "right" will be automatically generated.
- IsEssential?
  - If the bone is essential for the model. It can be "True" or "False". This is used for warn the user if the bone is not mapped in the model.

## Rule based renaming tool

This tool also sets mmd_bone.name_j and name_e to the bone.
Unlike the bone mapping utility, you can use your own renaming rules.

## Load Bone settings from CSV file

This tool loads mmd_bone settings from CSV file from PMX Editor.

You can choose actions individually:

- Update mmd_bone settings.
- Sort mmd bones along with CSV row order.
  - It creates representive object '[Armature Name]_bone_order' that stores the bone order.

## Material settings and sort order loader

This tool loads mmd_material settings and material/object sort order from CSV file from PMX Editor.
The CSV file must be created by using the PMX Editor's "Export as CSV" feature in the materials panel.

You can choose actions individually:

- Update Material.mmd_material settings.
- Sort materials / objects along with CSV row order.

These features help you to export updated model to existing PMX file.

Notice: The CSV file must be encoded in UTF-8. Older versions of PMX Editor may produce Shift-JIS encoded CSV file. Please use recent version of PMX Editor to export CSV file in UTF-8.

## Mine Sweeper

This panel detects errors and flaws that leads unexpected result.
Such as:

- Material name conflict (same name_j or name_e on different materials)
- Bone name conflict (same name_j or name_e on different bones)
- Object not belongs to the model (not parented to the armature)

## Quick Export and Patch Export

This feature allows you to export PMX files quickly with minimal settings.
It is useful for quick testing and iteration of the model.

- Quick Export:
  - It can be found in the context menu of the 3D Viewport (with selecting Armature or Object)
  - It exports only visible meshes within the selected model / selected objects.
  - It can ignore outline modifier (solidify with flipped normals) when exporting.
  - It can convert specified vertex group to MMD edge weights.
- Patch Export:
  - It can be enabled in the Quick Export panel.
  - It appends/updates the target PMX file with the exported meshes.
  - You can specify which features to be appended/updated.
  - Rest of features will be remain untouched in the target PMX file.

## Change Log

- 2025/07/16: Version 0.5.0
  - Added Quick Export - Patch Export features.
  - Updated translations.
  - Removed unnecessary context menu items.
  - Added changelog (this part) to README.md.

## Licence

[GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html)

## Author

- **Kafuji Sato** - VR Character Workshop
  - [Twitter](https://twitter.com/kafuji)
  - [GitHub](https://kafuji.github.io)

## Copyright

© 2022-2025 Kafuji Sato, all rights reserved.

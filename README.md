# PMX Export helper for mmd_tools

This is a Blender addon that provides a set of tools to help exporting PMX files for MMD by using mmd_tools.

## Requirements:

- Blender 3.0, 4.0 series
- recent mmd_tools

## Features:

- Bone mapping utility
  - Map bone names by using bone name definitions (can be customized).
  - Rule based renaming tool. Supporting Japanese LR identifiers.
- Load mmd_material settings and material/object sort order from CSV file from PMX Editor.
- Mine Sweeper - detects flaws that leads unexpected result.

## Usage:

1. Install the addon.
2. Open the MMD tab in the tool shelf.
3. Look for the PMX Export Helper panel.
4. Explore the features.

## Bone Mapping Utility:

Yet mmd_tools uses bone.mmd_bone.name_j and name_e to export PMX, it is hard to set them manually. This tool provides a way to map the bone names by using bone name definitions.

It supports Semi-Standard Bone set by default, and you can customize the bone name definitions by using a CSV file.

- In pose mode or armature edit mode, select any bone you want to map.
- Slected bones will be listed in the bone list on the panel.
- Configure bone mapping by using the pulldown menu.
- After all bones are mapped, click "Apply" button to apply the mapping to the armature.
- It will set mmd_bone.name_j and name_e to the bone. LR prefix will be automatically generated.

### User bone definition:

The user bone definition is a CSV file that contains the mapping of the bone names.
It will append the bone definitions to the default bone definitions.
If you have your standard bone set that needs to be translated in MMD, make one by yorself and load it from the panel.

### Example of user bone definition:

```csv
CATEGORY_ID,BONE_ID,Japanese,English,IsEssential?
FACIAL,JAW,顎,jaw,False
PHYS,BREAST,胸,breast,False
PHYS,BELLY,おなか,belly,False
PHYS,THIGH,腿,thigh,False
```


- CATEGORY_ID: The category of the bone. It is used for grouping the bones in the panel.
  - Any of {'ROOT', 'TORSO', 'FACIAL', 'ARMS', 'LEGS', 'FINGERS', 'IK', 'PHYS', 'OTHER'}.
- BONE_ID: The bone identifier. It can be any string.
- Japanese: The Japanese name of the bone. LR prefix "左" and "右" will be automatically generated.
- English: The English name of the bone. LR prefix "left" and "right" will be automatically generated.
- IsEssential?: If the bone is essential for the model. It can be "True" or "False". This is used for warn the user if the bone is not mapped in the model.


## Rule based renaming tool:

This tool also sets mmd_bone.name_j and name_e to the bone.
Unlike the bone mapping utility, you can use your own renaming rules.

## Material settings and sort order loader:

This tool loads mmd_material settings and material/object sort order from CSV file from PMX Editor.
The CSV file must be created by using the PMX Editor's "Export as CSV" feature in the materials panel.

You can choose actions individually:
  - Update Material.mmd_material settings.
  - Sort materials / objects along with CSV row order.

These features help you to export updated model to existing PMX file.

Notice: The CSV file must be encoded in UTF-8. Older versions of PMX Editor may produce Shift-JIS encoded CSV file. Please use recent version of PMX Editor to export CSV file in UTF-8.


## Mine Sweeper:

This panel detects errors and flaws that leads unexpected result.
Such as:

- Material name conflict (same name_j or name_e on different materials)
- Bone name conflict (same name_j or name_e on different bones)
- Object not belongs to the model (not parented to the armature)


# Licence

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# Author

- **Kafuji Sato** - VR Character Workshop
  - [Twitter](https://twitter.com/kafuji)
  - [GitHub](https://kafuji.github.io)
  - [Fantia](https://fantia.jp/fanclubs/3967)
  - [Fanbox](https://kafuji.fanbox.cc/)
  - [Gumroad](https://kafuji.gumroad.com)
  - [Blender Market](https://blendermarket.com/creators/kafuji)

# Copyright

© 2022 Kafuji Sato

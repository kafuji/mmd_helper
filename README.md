# PMX Export helper for mmd_tools

This is a Blender addon that provides a set of tools to help exporting PMX files for MMD.
mmd_tools is needed to use this addon.

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


## User bone definition:

The user bone definition is a CSV file that contains the mapping of the bone names.
It will append the bone definitions to the default bone definitions.

### Example of user bone definition:

```csv
CATEGORY_ID,BONE_ID,Japanese,English,IsEssential?
HEAD,JAW,顎,jaw,False
PHYS,BREAST,胸,breast,False
PHYS,BELLY,おなか,belly,False
PHYS,THIGH,腿,thigh,False
```


- CATEGORY_ID: The category of the bone. It can be any string.
- BONE_ID: The bone identifier. It can be any string.
- Japanese: The Japanese name of the bone. LR prefix "左" and "右" will be automatically generated.
- English: The English name of the bone. LR prefix "left" and "right" will be automatically generated.
- IsEssential?: If the bone is essential for the model. It can be "True" or "False". This is used for warn the user if the bone is not mapped in the model.


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

- Kafuji Sato
- GitHub: @kafuji

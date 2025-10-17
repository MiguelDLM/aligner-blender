# Procrustes Aligner - Blender Add-on

![Blender](https://img.shields.io/badge/Blender-4.4+-orange.svg)
![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)

Advanced Blender add-on for aligning multiple mesh objects using landmark-based Procrustes analysis.

## Overview

Procrustes Aligner allows you to precisely align two or more 3D objects by defining corresponding landmarks (vertices) on each object. The add-on uses Procrustes analysis to compute the optimal rotation, translation, and optionally scaling to minimize the distance between corresponding landmarks across all objects.

## Key Features

- **Landmark-based Alignment**: Define corresponding points across multiple objects
- **Dynamic Landmarks**: Landmarks reference vertex indices, not coordinates - they follow mesh deformations
- **Procrustes Analysis**: Optimal transformation using least-squares fitting
- **Flexible Options**: Control scaling and reflection permissions
- **Visual Preview**: Color-coded circles show landmark positions in real-time
- **Custom Properties**: Landmarks stored as object custom properties
- **Easy Workflow**: Intuitive panel with clear step-by-step process

## Installation

### Requirements

- Developed and tested on Blender 4.4 or later ([Download Blender](https://www.blender.org/))
- NumPy (included with Blender by default)

### Installation Steps

1. Download or clone this repository
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install from disk" and select the folder or ZIP file
4. Enable the add-on by checking the box next to "Procrustes Aligner"
5. The add-on panel will appear in the 3D Viewport sidebar (press `N` to toggle sidebar)

## Workflow

### 1. Prepare Your Objects

- Import or create multiple mesh objects that you want to align
- Ensure all objects are visible and selectable

### 2. Define Landmarks

For each object you want to align:

1. **Select the object** in the viewport
2. **Click "Select Landmark"** - This enters Edit Mode with vertex selection active
3. **Select a vertex** that represents a corresponding anatomical or geometric point
4. **Enter a landmark name** in the "Name" field (e.g., `landmark_1`, `tip`, `center`)
   - Use the same names across all objects for corresponding points
5. **Click "Submit Landmark"** - The vertex index is saved as a custom property
6. **Repeat** for all landmarks on this object

**Important**: All objects must have:
- The same number of landmarks
- The same landmark names
- At least 3 landmarks for proper alignment

**Note**: Landmarks store the **vertex index**, not coordinates. This means:
- If you modify the mesh (move vertices, sculpt, etc.), landmarks will follow the vertex
- Landmarks remain valid even after transformations or deformations
- You can see landmark positions in real-time with the preview toggle

### 3. Visual Preview

- **Enable "Landmark Preview"** toggle to visualize all landmarks
- Each landmark name gets a unique color (same name = same color across objects)
- Colored circles appear at landmark positions in the 3D viewport
- Helps verify that corresponding landmarks are correctly placed

### 4. Alignment Options

- **Reference Object**: Choose a specific object as reference (optional)
  - If set, this object stays fixed and others align to it
  - If not set, all objects align to their mean shape
- **Allow Scaling**: Enable if objects may have different sizes and need to be scaled to match
- **Allow Reflection**: Enable to allow mirroring transformations (usually disabled for anatomical data)

### 5. Execute Alignment

1. **Select all objects** you want to align (including the reference object)
2. The **first selected object** will be used as the reference (others will align to it)
3. **Click "Align Objects"** - The Procrustes analysis will be performed
4. Objects will be transformed to minimize landmark distances

### 5. Utilities

- **Delete Landmark**: Click the X button next to any landmark to remove it
- **Clear All Landmarks**: Remove all landmarks from the active object

## Example Use Cases

### Aligning Fossil Specimens

Align multiple fossil scans by marking corresponding anatomical landmarks:
- `landmark_1` = anterior tip
- `landmark_2` = posterior end
- `landmark_3` = dorsal ridge
- etc.

### Registering Medical Images

Align 3D reconstructions from different imaging modalities:
- Mark anatomical reference points
- Allow scaling if images have different resolutions

### Comparing Shape Variations

Study shape differences across specimens:
- Align all specimens to a reference
- Analyze remaining differences after optimal alignment

## Technical Details

### Procrustes Analysis

The add-on implements **Ordinary Procrustes Analysis (OPA)** which finds the optimal transformation to align one configuration of landmarks to another. The algorithm:

1. **Centers** both point sets by subtracting their centroids
2. **Scales** (optional) to normalize size differences
3. **Rotates** using Singular Value Decomposition (SVD) to find optimal rotation matrix
4. **Translates** to align centroids

The transformation minimizes the sum of squared distances between corresponding landmarks.

### Mathematical Foundation

Given reference points **X** and target points **Y**, we find transformation **T** that minimizes:

$$\sum_{i=1}^{n} ||x_i - T(y_i)||^2$$

Where **T** includes rotation **R**, translation **t**, and optional scaling **s**:

$$T(y) = s \cdot R \cdot y + t$$

## Landmark Storage

Landmarks are stored as custom properties on each object with the format:
```python
obj["landmark_name"] = [x, y, z]  # World coordinates
```

This allows landmarks to persist with the Blender file and be easily inspected or modified.

## Tips for Best Results

1. **Consistent Landmark Naming**: Use identical names for corresponding points across all objects
2. **Sufficient Landmarks**: Use at least 3 non-colinear landmarks; more is better for complex shapes
3. **Distributed Landmarks**: Place landmarks across the entire object, not just in one region
4. **Anatomical Correspondence**: For biological specimens, use true homologous points
5. **Check Alignment**: Visually inspect results and adjust landmarks if needed

## Troubleshooting

### "All objects must have the same landmark names"

Make sure you've defined the exact same landmark names on each object. Names are case-sensitive.

### "Need at least 3 landmarks for alignment"

Define at least 3 landmarks on each object. More landmarks generally give better results.

### Poor Alignment Quality

- Ensure landmarks truly correspond across objects
- Try adding more landmarks
- Check if landmarks are well-distributed (not all in one small region)
- Verify that Allow Scaling is set appropriately for your use case

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

## Citation

If you use this add-on in your research, please cite it as:

```
Díaz de León-Muñoz, E. M. (2025). Procrustes Aligner: A Blender Add-On for Landmark-Based Object Alignment
[Computer software]. Retrieved from https://github.com/MiguelDLM/aligner-blender
```

## Author

**Miguel Díaz de León-Muñoz**

## Acknowledgments

Inspired by standard Procrustes analysis methods used in geometric morphometrics and shape analysis research.

## References

- Dryden, I. L., & Mardia, K. V. (2016). *Statistical shape analysis: with applications in R* (Vol. 995). John Wiley & Sons.
- Rohlf, F. J., & Slice, D. (1990). Extensions of the Procrustes method for the optimal superimposition of landmarks. *Systematic Biology*, 39(1), 40-59.

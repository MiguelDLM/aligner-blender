# Procrustes Aligner - Blender Add-on

![Blender](https://img.shields.io/badge/Blender-4.4+-orange.svg)
![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)

Blender add-on for aligning one mesh object onto another using landmark
correspondences. It offers both **rigid Procrustes** alignment and a non-rigid
**Thin-Plate Spline (TPS)** warp, plus a built-in landmark verifier.

## Overview

You pick two objects — an **Original** (the reference, stays fixed) and a
**Target** (the object that gets moved/deformed). You then place pairs of
corresponding landmarks (one vertex on each object) and align the Target onto
the Original using the method of your choice.

## Key Features

- **Original / Target selectors**: pick the two objects directly in the panel
- **Guided pairing workflow**: place a vertex on the Original, then the add-on
  switches you straight to the Target to pick the equivalent vertex
- **Two alignment methods**:
  - **Procrustes (rigid)** — optimal rotation, translation and global scale
    (best least-squares compromise)
  - **Thin-Plate Spline (warp)** — deforms the Target mesh so every landmark
    lands *exactly* on its match, with smooth deformation in between
- **Landmark verifier**: detects mis-clicks, duplicate vertices, out-of-range
  indices, unpaired/collinear/coplanar landmarks and outlier residuals
- **Dynamic landmarks**: stored as vertex indices, so they follow the mesh
- **Visual preview**: color-coded markers show landmark positions in real time

## Installation

### Requirements

- Blender 4.4 or later ([Download Blender](https://www.blender.org/))
- NumPy (included with Blender by default)

### Installation Steps

1. Download the release `.zip` (or clone this repository)
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install from disk** and select the ZIP file
4. Enable the add-on by checking the box next to "Procrustes Aligner"
5. The panel appears in the 3D Viewport sidebar — press `N` and open the
   **Procrustes** tab

## Workflow

### 1. Select the objects

In the **Objects** box, set:

- **Original** — the reference object (stays fixed)
- **Target** — the object that will be aligned onto the Original

Both must be different mesh objects.

### 2. Create landmark pairs

1. (Optional) Edit the **Name** field for the next landmark pair
   (defaults to `landmark_1`, `landmark_2`, … and auto-increments).
2. Click **Select Landmark** — the add-on enters Edit Mode on the **Original**.
3. Select the vertex you want and click **Submit Landmark**.
4. The add-on automatically switches to Edit Mode on the **Target** — select
   the *equivalent* vertex and click **Submit Landmark** again.
5. The pair is saved on both objects and the name auto-increments. Repeat for
   as many pairs as you need.

Use **Cancel** at any point to abort the current pair (a half-finished pair is
cleaned up automatically).

Each pair is listed as `landmark_n:  vX → vY`, where `vX` is the vertex index
on the Original and `vY` on the Target. Use the **X** button to delete a pair.

**How many do I need?**
- **3+** pairs for Procrustes
- **4+** non-coplanar pairs for TPS

### 3. Visual Preview

Enable the **Landmark Preview** toggle to draw colored markers at every
landmark in the 3D viewport (same name = same color), making it easy to check
that corresponding points line up.

### 4. Alignment Options

- **Method**
  - **Procrustes (rigid)** — rotates, translates and (optionally) scales the
    whole Target. It minimizes the sum of squared landmark distances, so it is
    a *best compromise*: landmarks do **not** coincide exactly unless the two
    shapes are genuinely related by a similarity transform.
  - **Thin-Plate Spline (warp)** — deforms the Target geometry so each landmark
    lands exactly on its Original match, warping the rest of the mesh smoothly.
    Use this when you need the landmarks to actually coincide. ⚠️ This modifies
    the Target mesh (undoable with `Ctrl+Z`).
- **Allow Scaling** *(Procrustes)* — scale the Target to match the Original size
- **Allow Reflection** *(Procrustes)* — allow mirroring (usually off for
  anatomical data)
- **Smoothing** *(TPS)* — `0` = exact landmark match; higher values relax the
  fit so noisy or mis-clicked landmarks are not matched exactly

### 5. Verify & Execute

- **Verify Landmarks** runs a set of checks and shows the results in a popup.
  This is the fastest way to find a mis-clicked vertex: a landmark placed on the
  wrong vertex shows up as an **unusually large residual** outlier.
- **Align Target to Original** runs the selected method. Errors block the run;
  warnings are reported but do not stop it.

### 6. Utilities

- **Clear All Landmarks** removes every landmark from both objects
- **Landmark Preview** toggles the viewport overlay

## Landmark Verification

The verifier (and the pre-alignment check) detects:

| Check | Severity |
|-------|----------|
| Same vertex used by two landmarks on one object (likely mis-click) | warning |
| A landmark with an unusually large residual after a rigid fit | warning |
| Vertex index out of range | error |
| Landmark present on only one object (unpaired) | warning |
| Fewer than the required number of pairs (3 / 4 for TPS) | error |
| Collinear landmarks | error |
| Coplanar landmarks | warning (error for TPS) |
| Non-integer landmark data | error |

## Technical Details

### Procrustes Analysis

Implements **Ordinary Procrustes Analysis (OPA)**: center both point sets,
optionally scale, then find the optimal rotation via Singular Value
Decomposition (SVD), and translate to align centroids. The result minimizes:

$$\sum_{i=1}^{n} ||x_i - (s\,R\,y_i + t)||^2$$

where **R** is rotation, **t** translation and **s** an optional global scale.
Because it is a rigid (similarity) transform, it cannot change the Target's
proportions — it produces the best compromise, not exact landmark coincidence.

### Thin-Plate Spline

The TPS finds a smooth mapping that interpolates every landmark exactly (when
smoothing is `0`) while minimizing bending energy. In 3D it uses the biharmonic
radial kernel `U(r) = r`. Each Target vertex is taken to world space, warped,
and written back, so the landmarks coincide with the Original's. A non-zero
**smoothing** value relaxes the interpolation to suppress noisy landmarks.

## Landmark Storage

Landmarks are stored as integer custom properties (vertex indices) on each
object:

```python
obj["landmark_1"] = 482   # index of the vertex used as this landmark
```

Because indices (not coordinates) are stored, landmarks follow the mesh through
edits and deformations, and they persist with the `.blend` file.

## Tips for Best Results

1. **True correspondence**: pick genuinely homologous points on both objects
2. **Distribute landmarks** across the whole object, not one region
3. **Enough landmarks**: 3+ for Procrustes, 4+ non-coplanar for TPS
4. **Verify first**: run *Verify Landmarks* to catch mis-clicks before aligning
5. **Pick the right method**: Procrustes to reposition, TPS to make landmarks
   coincide / study shape differences

## Troubleshooting

### Poor alignment with Procrustes

Procrustes is rigid: if the two objects have different shapes, the landmarks
**cannot** all coincide. Either accept the least-squares compromise or switch to
**TPS** for exact landmark matching.

### A single landmark seems to throw everything off

Run **Verify Landmarks** — a wrong vertex pick (e.g. accidentally selecting
vertex 0) is flagged as an outlier residual or a duplicate vertex.

### "Need at least N valid landmark pairs"

Add more pairs: 3 for Procrustes, 4 (non-coplanar) for TPS.

## License

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

## Citation

If you use this add-on in your research, please cite it as:

```
Díaz de León-Muñoz, E. M. (2025). Procrustes Aligner: A Blender Add-On for Landmark-Based Object Alignment
[Computer software]. Retrieved from https://github.com/MiguelDLM/aligner-blender
```

## Author

**Miguel Díaz de León-Muñoz**

## Acknowledgments

Inspired by standard Procrustes and thin-plate-spline methods used in geometric
morphometrics and shape analysis research.

## References

- Dryden, I. L., & Mardia, K. V. (2016). *Statistical shape analysis: with applications in R* (Vol. 995). John Wiley & Sons.
- Rohlf, F. J., & Slice, D. (1990). Extensions of the Procrustes method for the optimal superimposition of landmarks. *Systematic Biology*, 39(1), 40-59.
- Bookstein, F. L. (1989). Principal warps: thin-plate splines and the decomposition of deformations. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 11(6), 567-585.

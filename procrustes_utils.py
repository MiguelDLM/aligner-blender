"""
Procrustes analysis utilities for landmark-based alignment.

This module implements Procrustes analysis to find the optimal transformation
(rotation, translation, and optionally scaling) to align one set of landmarks
to another.
"""

import numpy as np
from typing import Tuple


def procrustes_alignment(
    reference_points: np.ndarray,
    target_points: np.ndarray,
    allow_scale: bool = True,
    allow_reflection: bool = False
) -> Tuple[bool, np.ndarray, float]:
    """
    Perform Procrustes analysis to align target points to reference points.
    
    This function computes the optimal rotation, translation, and optionally
    scaling to transform target_points to best match reference_points in a
    least-squares sense.
    
    Args:
        reference_points: Nx3 array of reference landmark coordinates
        target_points: Nx3 array of target landmark coordinates to be aligned
        allow_scale: If True, compute optimal scaling factor
        allow_reflection: If True, allow reflections (determinant can be negative)
    
    Returns:
        Tuple of (success, transformation_matrix, scale_factor)
        - success: Boolean indicating if alignment was successful
        - transformation_matrix: 4x4 homogeneous transformation matrix
        - scale_factor: Computed scale factor (1.0 if scaling not allowed)
    """
    
    # Validate input
    if reference_points.shape != target_points.shape:
        print("Error: Reference and target point sets must have the same shape")
        return False, np.eye(4), 1.0
    
    if reference_points.shape[0] < 3:
        print("Error: Need at least 3 points for Procrustes alignment")
        return False, np.eye(4), 1.0
    
    if reference_points.shape[1] != 3:
        print("Error: Points must be 3-dimensional")
        return False, np.eye(4), 1.0
    
    # Step 1: Compute centroids
    ref_centroid = np.mean(reference_points, axis=0)
    tgt_centroid = np.mean(target_points, axis=0)
    
    # Step 2: Center the point sets
    ref_centered = reference_points - ref_centroid
    tgt_centered = target_points - tgt_centroid
    
    # Step 3: Compute scale factor if allowed
    scale = 1.0
    if allow_scale:
        ref_scale = np.sqrt(np.sum(ref_centered ** 2))
        tgt_scale = np.sqrt(np.sum(tgt_centered ** 2))
        
        if tgt_scale > 1e-10:  # Avoid division by zero
            scale = ref_scale / tgt_scale
        else:
            print("Warning: Target points have near-zero variance")
            return False, np.eye(4), 1.0
    
    # Step 4: Scale the target points
    tgt_centered_scaled = tgt_centered * scale
    
    # Step 5: Compute optimal rotation using SVD
    # The cross-covariance matrix
    H = tgt_centered_scaled.T @ ref_centered
    
    # Singular Value Decomposition
    U, S, Vt = np.linalg.svd(H)
    
    # Compute rotation matrix
    R = Vt.T @ U.T
    
    # Step 6: Handle reflection if not allowed
    if not allow_reflection:
        # Check if we have a reflection (determinant < 0)
        if np.linalg.det(R) < 0:
            # Flip the last column of Vt
            Vt_corrected = Vt.copy()
            Vt_corrected[-1, :] *= -1
            R = Vt_corrected.T @ U.T
    
    # Step 7: Compute translation
    # We want: ref_centroid = R @ (scale * tgt_centroid) + translation
    # So: translation = ref_centroid - R @ (scale * tgt_centroid)
    translation = ref_centroid - R @ (scale * tgt_centroid)
    
    # Step 8: Build 4x4 homogeneous transformation matrix
    # The transformation applies: scale, then rotate, then translate
    transform = np.eye(4)
    transform[:3, :3] = R * scale
    transform[:3, 3] = translation
    
    return True, transform, scale


def tps_fit(source: np.ndarray, dest: np.ndarray, smoothing: float = 0.0):
    """Fit a 3D Thin-Plate Spline mapping source landmarks onto dest landmarks.

    The TPS warp passes exactly through every landmark (when smoothing == 0)
    and deforms space smoothly in between, minimizing bending energy.

    Args:
        source: Nx3 array of source landmark coordinates (the points to move)
        dest:   Nx3 array of destination landmark coordinates (where they go)
        smoothing: Regularization lambda. 0 = exact interpolation; larger
                   values relax the fit so noisy landmarks are not matched
                   exactly (useful to suppress mis-clicks).

    Returns:
        (success, params) where params is an (N+4)x3 array of TPS coefficients,
        or (False, None) if the system could not be solved.
    """
    source = np.asarray(source, dtype=np.float64)
    dest = np.asarray(dest, dtype=np.float64)

    if source.shape != dest.shape or source.shape[0] < 4 or source.shape[1] != 3:
        # 3D TPS needs at least 4 non-coplanar landmarks for the affine part.
        return False, None

    n = source.shape[0]

    # Radial kernel U(r) = r is the biharmonic Green's function in 3D.
    diff = source[:, None, :] - source[None, :, :]
    K = np.sqrt(np.sum(diff ** 2, axis=2))

    if smoothing > 0.0:
        K = K + np.eye(n) * smoothing

    P = np.hstack([np.ones((n, 1)), source])  # (n, 4)

    L = np.zeros((n + 4, n + 4))
    L[:n, :n] = K
    L[:n, n:] = P
    L[n:, :n] = P.T

    Y = np.vstack([dest, np.zeros((4, 3))])

    try:
        params, _residuals, _rank, _sv = np.linalg.lstsq(L, Y, rcond=None)
    except np.linalg.LinAlgError:
        return False, None

    if not np.all(np.isfinite(params)):
        return False, None

    return True, params


def tps_apply(params: np.ndarray, source: np.ndarray, points: np.ndarray,
              chunk_size: int = 50000) -> np.ndarray:
    """Apply a fitted TPS warp to an array of points.

    Args:
        params: (N+4)x3 coefficients from tps_fit
        source: Nx3 source landmarks used in the fit
        points: Mx3 points to warp
        chunk_size: process points in chunks to bound memory on large meshes

    Returns:
        Mx3 array of warped points
    """
    source = np.asarray(source, dtype=np.float64)
    points = np.asarray(points, dtype=np.float64)
    n = source.shape[0]

    w = params[:n]   # (n, 3) non-linear weights
    a = params[n:]   # (4, 3) affine part

    out = np.empty_like(points)
    for start in range(0, points.shape[0], chunk_size):
        chunk = points[start:start + chunk_size]
        Ph = np.hstack([np.ones((chunk.shape[0], 1)), chunk])
        affine = Ph @ a
        diff = chunk[:, None, :] - source[None, :, :]
        r = np.sqrt(np.sum(diff ** 2, axis=2))  # (chunk, n)
        out[start:start + chunk_size] = affine + r @ w

    return out


def compute_alignment_error(
    reference_points: np.ndarray,
    target_points: np.ndarray,
    transform_matrix: np.ndarray
) -> float:
    """
    Compute the root mean square error after applying transformation.
    
    Args:
        reference_points: Nx3 array of reference landmarks
        target_points: Nx3 array of target landmarks
        transform_matrix: 4x4 transformation matrix
    
    Returns:
        RMSE between transformed target points and reference points
    """
    
    # Convert to homogeneous coordinates
    target_homo = np.hstack([target_points, np.ones((target_points.shape[0], 1))])
    
    # Apply transformation
    transformed = (transform_matrix @ target_homo.T).T[:, :3]
    
    # Compute RMSE
    differences = reference_points - transformed
    rmse = np.sqrt(np.mean(np.sum(differences ** 2, axis=1)))
    
    return rmse


def procrustes_superimposition(
    point_sets: list,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    allow_scale: bool = True
) -> Tuple[bool, list, np.ndarray]:
    """
    Perform Generalized Procrustes Analysis (GPA) on multiple point sets.
    
    This aligns multiple configurations to a common mean shape iteratively.
    
    Args:
        point_sets: List of Nx3 numpy arrays, each representing a configuration
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance for mean shape change
        allow_scale: Whether to allow scaling
    
    Returns:
        Tuple of (success, aligned_point_sets, mean_shape)
    """
    
    if len(point_sets) < 2:
        print("Error: Need at least 2 point sets for GPA")
        return False, [], np.array([])
    
    # Check all point sets have same shape
    shape = point_sets[0].shape
    for pts in point_sets:
        if pts.shape != shape:
            print("Error: All point sets must have the same shape")
            return False, [], np.array([])
    
    # Initialize with the first point set as reference
    aligned = [pts.copy() for pts in point_sets]
    
    # Compute initial mean shape
    mean_shape = np.mean(aligned, axis=0)
    
    for iteration in range(max_iterations):
        old_mean = mean_shape.copy()
        
        # Align each configuration to current mean
        for i in range(len(aligned)):
            success, transform, scale = procrustes_alignment(
                mean_shape,
                point_sets[i],
                allow_scale=allow_scale,
                allow_reflection=False
            )
            
            if not success:
                print(f"Warning: Failed to align configuration {i}")
                continue
            
            # Transform points
            pts_homo = np.hstack([point_sets[i], np.ones((point_sets[i].shape[0], 1))])
            aligned[i] = (transform @ pts_homo.T).T[:, :3]
        
        # Recompute mean shape
        mean_shape = np.mean(aligned, axis=0)
        
        # Check convergence
        change = np.max(np.abs(mean_shape - old_mean))
        if change < tolerance:
            print(f"GPA converged after {iteration + 1} iterations")
            break
    else:
        print(f"GPA reached maximum iterations ({max_iterations})")
    
    return True, aligned, mean_shape

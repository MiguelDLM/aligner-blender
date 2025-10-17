"""Preview drawing for Procrustes landmarks.

This module adds a 3D View draw handler that draws a small marker and a label
for each landmark stored as object custom properties (keys starting with
"landmark_"). The drawing uses the GPU shader and BLF for text rendering.
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
import blf

_handler = None


def _draw_callback_3d(self, context):
    # Draw landmarks for all mesh objects
    points = []
    labels = []
    # Gather points
    for obj in context.scene.objects:
        if obj.type != 'MESH':
            continue
        for key in obj.keys():
            if str(key).startswith('landmark_'):
                try:
                    coord = obj[key]
                    co_world = Vector(coord)
                    points.append(co_world)
                    labels.append((co_world, str(key)))
                except Exception:
                    continue
    
    # Draw points as small dots using POINT_UNIFORM_COLOR shader
    if points:
        try:
            shader = gpu.shader.from_builtin('POINT_UNIFORM_COLOR')
            coords = [tuple(p) for p in points]
            batch = batch_for_shader(shader, 'POINTS', {"pos": coords})
            shader.bind()
            shader.uniform_float("color", (1.0, 0.2, 0.2, 1.0))
            # Set point size
            gpu.state.point_size_set(10.0)
            batch.draw(shader)
            gpu.state.point_size_set(1.0)
        except Exception as e:
            # Silently fail if drawing fails
            pass

    # Draw labels in 2D overlay
    # Use region_2d conversion
    region = context.region
    rv3d = context.region_data
    if labels and region and rv3d:
        try:
            blf.size(0, 12, 72)
            for co_world, text in labels:
                co2d = location_3d_to_region_2d(region, rv3d, co_world)
                if co2d:
                    x, y = int(co2d.x), int(co2d.y)
                    blf.position(0, x + 6, y + 6, 0)
                    blf.color(0, 1.0, 1.0, 1.0, 1.0)
                    blf.draw(0, text)
        except Exception:
            pass


# Helper to convert 3D location to 2D region coords
from bpy_extras.view3d_utils import location_3d_to_region_2d


def register_draw_handler():
    global _handler
    if _handler is None:
        _handler = bpy.types.SpaceView3D.draw_handler_add(_draw_callback_3d, (None, bpy.context), 'WINDOW', 'POST_VIEW')
        print('Procrustes: draw handler registered')


def unregister_draw_handler():
    global _handler
    if _handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        except Exception:
            pass
        _handler = None
        print('Procrustes: draw handler unregistered')


class PROCRUSTES_OT_toggle_landmark_preview(bpy.types.Operator):
    bl_idname = "procrustes.toggle_landmark_preview"
    bl_label = "Toggle Landmark Preview"
    bl_description = "Show/hide landmark preview in the 3D View"

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, 'procrustes_preview_active') or not scene.procrustes_preview_active:
            register_draw_handler()
            scene.procrustes_preview_active = True
        else:
            unregister_draw_handler()
            scene.procrustes_preview_active = False
        return {'FINISHED'}


def cleanup():
    unregister_draw_handler()

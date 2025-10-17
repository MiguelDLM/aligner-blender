"""Preview drawing for Procrustes landmarks.

Draws markers, labels, and connector arrows for landmarks stored as custom
properties on visible mesh objects. Uses modern GPU and BLF APIs.
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
import hashlib
import math
from bpy_extras.view3d_utils import location_3d_to_region_2d

_handler_3d = None
_handler_2d = None
_label_cache = []  # Cached (world_location, label) tuples shared between handlers


def _visible_landmarks(context):
    """Collect world-space landmark coordinates and labels for visible mesh objects."""
    landmarks = []

    visible_objects = getattr(context, "visible_objects", None)
    if visible_objects is None:
        visible_objects = [obj for obj in context.scene.objects if not obj.hide_viewport and not obj.hide_get()]

    for obj in visible_objects:
        if obj.type != 'MESH':
            continue
        if obj.hide_viewport or obj.hide_get():
            continue

        for key in obj.keys():
            if str(key).startswith("landmark_"):
                try:
                    coord = Vector(obj[key])
                except Exception:
                    continue
                landmarks.append((coord, str(key)))

    return landmarks


def _draw_callback_3d(_self, context):
    """Cache landmarks for the 2D pass. No 3D drawing needed."""
    global _label_cache
    try:
        landmarks = _visible_landmarks(context)
        _label_cache = landmarks
        print(f"[DEBUG 3D] Found {len(landmarks)} landmarks")
    except Exception as e:
        print(f"[ERROR 3D] {e}")
        import traceback
        traceback.print_exc()


def _draw_callback_2d(_self, context):
    """Draw labels, lines, and arrowheads in POST_PIXEL using cached data."""
    print(f"[DEBUG 2D] Callback called, cache has {len(_label_cache)} items")
    
    if not _label_cache:
        print("[DEBUG 2D] Cache is empty, returning")
        return

    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        print("[DEBUG 2D] No region or rv3d, returning")
        return

    # No text labels anymore. Instead draw a colored circle marker per landmark
    def _name_to_color(name: str):
        # Deterministic color from name using md5 -> hue
        h = int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16) % 360
        s = 0.65
        v = 0.95
        # HSV to RGB
        c = v * s
        hh = h / 60.0
        x = c * (1 - abs((hh % 2) - 1))
        if 0 <= hh < 1:
            r1, g1, b1 = c, x, 0
        elif 1 <= hh < 2:
            r1, g1, b1 = x, c, 0
        elif 2 <= hh < 3:
            r1, g1, b1 = 0, c, x
        elif 3 <= hh < 4:
            r1, g1, b1 = 0, x, c
        elif 4 <= hh < 5:
            r1, g1, b1 = x, 0, c
        else:
            r1, g1, b1 = c, 0, x
        m = v - c
        return (r1 + m, g1 + m, b1 + m, 1.0)

    def _circle_fan(center, radius=8.0, segments=16):
        cx, cy = center.x, center.y
        verts = [(cx, cy)]
        for i in range(segments + 1):
            a = (i / segments) * (2.0 * math.pi)
            verts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
        return verts

    offset_vec = Vector((48.0, 48.0))
    margin = 8

    try:
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        print(f"[DEBUG 2D] Starting to draw {len(_label_cache)} landmarks")

        for world_co, name in _label_cache:
            co2d = location_3d_to_region_2d(region, rv3d, world_co)
            if co2d is None:
                print(f"[DEBUG 2D] Landmark '{name}' not visible (co2d is None)")
                continue

            point_2d = Vector((co2d.x, co2d.y))
            # Draw circle directly at point_2d for now (no offset) to ensure visibility
            label_pos = point_2d  # Changed from: point_2d + offset_vec

            # Clamp label position inside region with margin
            lx = max(margin, min(label_pos.x, region.width - margin))
            ly = max(margin, min(label_pos.y, region.height - margin))
            label_pos = Vector((lx, ly))

            color = _name_to_color(name)
            
            print(f"[DEBUG 2D] Drawing landmark '{name}' at {label_pos} with color {color}")

            # Draw filled circle at point position with per-landmark color
            circle_verts = _circle_fan(label_pos, radius=10.0, segments=24)
            batch_circle = batch_for_shader(shader, 'TRI_FAN', {"pos": circle_verts})
            shader.bind()
            shader.uniform_float('color', color)
            batch_circle.draw(shader)

    except Exception as e:
        print(f"[ERROR 2D] {e}")
        import traceback
        traceback.print_exc()
    finally:
        gpu.state.blend_set('NONE')


def _area_redraw_all_view3d():
    wm = bpy.context.window_manager
    if wm is None:
        return
    for window in wm.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def register_draw_handlers():
    global _handler_3d, _handler_2d
    print("[DEBUG] Registering draw handlers...")
    if _handler_3d is None:
        _handler_3d = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback_3d,
            (None, bpy.context),
            'WINDOW',
            'POST_VIEW'
        )
        print(f"[DEBUG] 3D handler registered: {_handler_3d}")
    if _handler_2d is None:
        _handler_2d = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback_2d,
            (None, bpy.context),
            'WINDOW',
            'POST_PIXEL'
        )
        print(f"[DEBUG] 2D handler registered: {_handler_2d}")
    _area_redraw_all_view3d()
    print("[DEBUG] Handlers registered and redraw triggered")


def unregister_draw_handlers():
    global _handler_3d, _handler_2d
    print("[DEBUG] Unregistering draw handlers...")
    if _handler_3d is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_handler_3d, 'WINDOW')
            print("[DEBUG] 3D handler unregistered")
        except Exception as e:
            print(f"[ERROR] Failed to unregister 3D handler: {e}")
        _handler_3d = None
    if _handler_2d is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_handler_2d, 'WINDOW')
            print("[DEBUG] 2D handler unregistered")
        except Exception as e:
            print(f"[ERROR] Failed to unregister 2D handler: {e}")
        _handler_2d = None
    _area_redraw_all_view3d()


def preview_toggle_update(self, _context):
    """Scene property update callback to toggle preview handlers."""
    enabled = bool(getattr(self, 'procrustes_preview_active', False))
    print(f"[DEBUG] Preview toggle update called, enabled={enabled}")
    if enabled:
        register_draw_handlers()
    else:
        unregister_draw_handlers()


def cleanup():
    unregister_draw_handlers()

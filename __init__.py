# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from .operators import (
    PROCRUSTES_OT_select_landmark,
    PROCRUSTES_OT_submit_landmark,
    PROCRUSTES_OT_delete_landmark,
    PROCRUSTES_OT_align_objects,
    PROCRUSTES_OT_clear_landmarks
)
from .panel import PROCRUSTES_PT_panel
from .preview import preview_toggle_update, cleanup as preview_cleanup


def register():
    """Register addon classes and properties"""
    
    # Register operators
    bpy.utils.register_class(PROCRUSTES_OT_select_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_submit_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_delete_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_align_objects)
    bpy.utils.register_class(PROCRUSTES_OT_clear_landmarks)
    
    # Register UI panel
    bpy.utils.register_class(PROCRUSTES_PT_panel)
    
    # Scene properties
    bpy.types.Scene.procrustes_landmark_name = bpy.props.StringProperty(
        name="Landmark Name",
        description="Name for the landmark to be created",
        default="landmark_"
    )
    
    bpy.types.Scene.procrustes_selected_vertex = bpy.props.IntProperty(
        name="Selected Vertex",
        description="Index of the currently selected vertex",
        default=-1
    )
    
    bpy.types.Scene.procrustes_allow_scale = bpy.props.BoolProperty(
        name="Allow Scale",
        description="Allow scaling during Procrustes alignment",
        default=True
    )
    
    bpy.types.Scene.procrustes_allow_reflection = bpy.props.BoolProperty(
        name="Allow Reflection",
        description="Allow reflection during Procrustes alignment",
        default=False
    )
    
    # Reference object selector (optional)
    bpy.types.Scene.procrustes_reference_object = bpy.props.PointerProperty(
        name="Reference Object",
        description="Optional: choose an object to be the fixed reference for alignment",
        type=bpy.types.Object
    )
    
    # Preview active flag
    bpy.types.Scene.procrustes_preview_active = bpy.props.BoolProperty(
        name="Preview Active",
        description="Display landmark preview overlay in the 3D View",
        default=False,
        update=preview_toggle_update
    )


def unregister():
    """Unregister addon classes and properties"""
    
    # Unregister operators
    bpy.utils.unregister_class(PROCRUSTES_OT_select_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_submit_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_delete_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_align_objects)
    bpy.utils.unregister_class(PROCRUSTES_OT_clear_landmarks)
    
    # Unregister UI panel
    bpy.utils.unregister_class(PROCRUSTES_PT_panel)
    
    # Delete scene properties
    del bpy.types.Scene.procrustes_landmark_name
    del bpy.types.Scene.procrustes_selected_vertex
    del bpy.types.Scene.procrustes_allow_scale
    del bpy.types.Scene.procrustes_allow_reflection
    del bpy.types.Scene.procrustes_reference_object
    # Preview cleanup and property
    preview_cleanup()
    del bpy.types.Scene.procrustes_preview_active

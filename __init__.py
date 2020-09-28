import bpy

from . import PivotPainterTool

bl_info = {
    "name": "Pivot Painter",
    "author": "George Vogiatzis (Gvgeo)",
    "version": (1, 1, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Tool Shelf > Unreal Tools",
    "description": "Tools to create 3d model for Unreal Engine 4, that make use of the Pivot Painter Tool's material functions",
    "wiki_url": "https://github.com/Gvgeo/Pivot-Painter-for-Blender",
    "category": "Unreal Tools",
}

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.pivot_painter = PointerProperty(
        type=UE4_PivotPainterProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.pivot_painter

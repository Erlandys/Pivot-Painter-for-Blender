import importlib

from . import Properties, Operators, Utils
from .core import PivotAndRotation, CreateTextures, MeshOperations
from .data import TextureOptions, TexturePackingFunctions
from .ui import Panels

bl_info = {
    "name": "Pivot Painter",
    "author": "George Vogiatzis (Gvgeo) refactored by Erlandas Barauskas (Hayato)",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Tool Shelf > Unreal Tools",
    "description": "Tools to create 3d model for Unreal Engine 5, that make use of the Pivot Painter Tool's material functions",
    "wiki_url": "https://github.com/Gvgeo/Pivot-Painter-for-Blender",
    "category": "Unreal Tools",
}

modules = [
    Operators,
    Properties,
    Panels,
    Utils,
    PivotAndRotation,
    CreateTextures,
    MeshOperations,
    TexturePackingFunctions,
    TextureOptions
]


def register():
    for module in modules:
        importlib.reload(module)

    try:
        Properties.register()
        Operators.register()
        Panels.register()
    except RuntimeError as error:
        print(error)


def unregister():
    try:
        Properties.unregister()
        Operators.unregister()
        Panels.unregister()
    except RuntimeError as error:
        print(error)

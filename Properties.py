import bpy.types

from .data.TextureOptions import texture_rgb_options, texture_alpha_options
from bpy.props import BoolProperty, IntProperty, StringProperty, FloatProperty


class PivotPainterPropertyGroup(bpy.types.PropertyGroup):
    def get_group_name(self):
        return ''


class PivotPainterTextureOptionProperties(PivotPainterPropertyGroup):
    def get_group_name(self):
        return 'pp_textures_list'

    rgb_options = []
    for key, rgb_option in texture_rgb_options.items():
        rgb_options.append(rgb_option.get_property_definition())

    alpha_options = []
    for key, alpha_option in texture_alpha_options.items():
        alpha_options.append(alpha_option.get_property_definition())

    rgb: bpy.props.EnumProperty(
        items=rgb_options,
        name="RGB",
        default="pivot_point")
    alpha: bpy.props.EnumProperty(
        items=alpha_options,
        name="Alpha",
        default="index")

    generate_hdr: bpy.props.BoolProperty(
        name="HDR",
        description="Generate HDR textures",
        default=True)

    def get_rgb_option(self) -> 'TextureOptions.PivotPainterTextureTypeData':
        return texture_rgb_options[self.rgb]

    def get_alpha_option(self) -> 'TextureOptions.PivotPainterTextureTypeData':
        return texture_alpha_options[self.alpha]


class PivotPainterTextureProperties(PivotPainterPropertyGroup):
    def get_group_name(self):
        return 'pp_texture_properties'

    display_textures: BoolProperty(
        name="Display Textures",
        default=True)

    uv_map_name: StringProperty(
        name="UV Map Name",
        description="Choose UV Map name which will be reused or created for new UVs",
        default='PivotPainterMap',
        maxlen=1024)

    extra_options: BoolProperty(
        name="Extra options",
        default=False)

    selecting_objects: BoolProperty(
        name="Selecting Objects",
        default=False,
        description="Press Again to confirm selection, or ESC to cancel.\n\nYou can select more than 1 object each time. ")
    order_start: IntProperty(
        name="Order Start Number",
        description="The number the order count should start.\nDefault 1",
        default=1,
        min=1,
        soft_max=100,
        max=30000)
    dont_count: BoolProperty(
        name="Same order number",
        default=False,
        description="Create the same order number for all selected objects")

    save_textures: BoolProperty(
        name="Save Textures to folder",
        default=False,
        description="Will always OVERWRITE texture files with the same name\n\nSave textures to the specified folder location")
    folder_path: StringProperty(
        name="Save location",
        description="Choose a directory:",
        default='',
        maxlen=1024,
        subtype='DIR_PATH')
    create_new: BoolProperty(
        name="Always create new textures",
        default=True,
        description="Should it create a new texture or use the first one?")


class PivotPainterCalculatePivotProperties(PivotPainterPropertyGroup):
    def get_group_name(self):
        return 'pp_calculate_pivot_properties'

    show: BoolProperty(
        name="Show Pivot Settings",
        default=True)

    enabled: BoolProperty(
        name="Calculate Pivots",
        default=True,
        description="Should change pivots to selected objects?")

    no_parent_type_options = [
        ("origin", "Origin", 'Will set objects origin to (0, 0, 0)'),
        ("axis_middle", "Axis middle", 'Will set to middle of lowest/highest axis vertices')
    ]
    no_parent_pivot_type: bpy.props.EnumProperty(
        items=no_parent_type_options,
        name="No parent pivot",
        description="Type of origin for object without parent",
        default="origin")

    no_parent_axis_type = [
        ("x_pos", "+X", 'Will look for highest X vertices'),
        ("x_neg", "-X", 'Will look for lowest X vertices'),
        ("y_pos", "+Y", 'Will look for highest Y vertices'),
        ("y_neg", "-Y", 'Will look for lowest Y vertices'),
        ("z_pos", "+Z", 'Will look for highest Z vertices'),
        ("z_neg", "-Z", 'Will look for lowest Z vertices')
    ]
    no_parent_axis: bpy.props.EnumProperty(
        items=no_parent_axis_type,
        name="No parent axis",
        description="Axis to look for base",
        default="z_neg")

    no_parent_max_axis_difference: FloatProperty(
        name="Maximum Axis Difference",
        default=0.01,
        precision=3,
        min=0.000001,
        soft_max=0.5,
        unit="LENGTH",
        description="Maximum Axis difference from lowest point, when using bottom middle parentless option")

    type_options = [
        ("face", "Face", 'Will use middle of face'),
        ("vertex", "Vertex", 'Will use vertex position'),
        ("overlap", "Overlap (Fastest)", "Will use BVH Tree, to find overlapping positions between object and its parent.\nWill fallback to vertex calculation, when no overlaps found")
    ]
    item_type: bpy.props.EnumProperty(
        items=type_options,
        name="Type",
        description="When calculating pivot, use middle of face or vertex positions.",
        default="overlap")

    calculation_type_options = [
        ("closest_item", "Closest Item", 'Will use only the closest face/vertex to the parent mesh'),
        ("mean", "Mean of closest items", 'Will use distance, to find multiple closest face/vertices and calculate their mean.\nIf no items will be found by minimum distance, closest face/vertex will be used.')
    ]
    calculation_type: bpy.props.EnumProperty(
        items=calculation_type_options,
        name="Calculation Type",
        description="",
        default="mean")
    max_distance: FloatProperty(
        name="Maximum Distance",
        default=0.01,
        precision=3,
        min=0.000001,
        soft_max=0.5,
        unit="LENGTH",
        description="Maximum distance from closest face/vertex to include into mean calculation.")


class PivotPainterCalculateRotationsProperties(PivotPainterPropertyGroup):
    def get_group_name(self):
        return 'pp_calculate_direction_properties'

    show: BoolProperty(
        name="Show Rotation Settings",
        default=True)

    enabled: BoolProperty(
        name="Calculate Rotations",
        default=True,
        description="Should change rotations to selected objects?")

    type_options = [
        ("bounding_box", "Bounding Box", 'Will use objects bounding box for direction'),
        ("vertex", "Vertex", 'Will use furthest mean of furthest vertices')
    ]
    item_type: bpy.props.EnumProperty(
        items=type_options,
        name="Calculation Type",
        description="",
        default="vertex")

    calculation_type_options = [
        ("closest_item", "Closest Item", 'Will use only the closest face/vertex to the parent mesh'),
        ("mean", "Mean of closest items", 'Will use distance, to find multiple closest face/vertices and calculate their mean.\nIf no items will be found by minimum distance, closest face/vertex will be used.')
    ]
    calculation_type: bpy.props.EnumProperty(
        items=calculation_type_options,
        name="Calculation Type",
        description="",
        default="mean")

    max_distance: FloatProperty(
        name="Maximum Distance",
        default=0.01,
        precision=3,
        min=0.000001,
        soft_max=0.5,
        unit="LENGTH",
        description="Maximum distance for vertex inclusion for mean calculation.")


class PivotPainterHierarchyBaseMeshProperties(PivotPainterPropertyGroup):
    mesh_name: bpy.props.StringProperty(
        name='Mesh'
    )


class PivotPainterDefaultMeshOperationsProperties(PivotPainterPropertyGroup):
    def get_group_name(self):
        return 'pp_default_mesh_operations'

    show_split_mesh: BoolProperty(
        name="Show Split Mesh",
        default=True)

    show_copy_uvs: BoolProperty(
        name="Show Copy UVs",
        default=True)

    copy_uvs_target: StringProperty(
        name="Copy UVs Target",
        description="If set, will copy generated UVs into target object"
    )

    copy_uvs_uv_precision_lookup: IntProperty(
        name="UV Lookup Precision",
        description="When looking for matching UV coordinates, float precision errors appears, so lowering down precision with some tolerance will increase matching.",
        default=4,
        min=1,
        max=12
    )

    show_generate_hierarchy: BoolProperty(
        name="Show Generate Hierarchy",
        default=True)

    base_meshes: bpy.props.CollectionProperty(
        type=PivotPainterHierarchyBaseMeshProperties,
        name='Base Meshes',
        description="List of base meshes from which to go hierarchy up"
    )

    base_mesh_index: bpy.props.IntProperty(
        name='Base Mesh Index',
    )

    show_empty_axis_meshes: BoolProperty(
        name="Show No Wind Objects",
        default=True)

    empty_axis_meshes: bpy.props.CollectionProperty(
        type=PivotPainterHierarchyBaseMeshProperties,
        name='No Wind Meshes',
        description="List of no wind meshes, which will generate extent as 0, to ignore wind movement."
    )

    empty_axis_mesh_index: bpy.props.IntProperty(
        name='No Wind Mesh Index',
    )


property_classes = [
    (PivotPainterTextureProperties, 'pp_texture_properties'),
    (PivotPainterCalculatePivotProperties, 'pp_calculate_pivot_properties'),
    (PivotPainterCalculateRotationsProperties, 'pp_calculate_direction_properties'),
    (PivotPainterDefaultMeshOperationsProperties, 'pp_default_mesh_operations'),
]


def get_texture_settings(context: bpy.types.Context) -> 'PivotPainterTextureProperties':
    return context.scene.pp_texture_properties


def get_textures_list_settings(context: bpy.types.Context) -> 'PivotPainterTextureOptionProperties':
    return context.scene.pp_textures_list


def get_calculate_pivot_settings(context: bpy.types.Context) -> 'PivotPainterCalculatePivotProperties':
    return context.scene.pp_calculate_pivot_properties


def get_calculate_rotation_settings(context: bpy.types.Context) -> 'PivotPainterCalculateRotationsProperties':
    return context.scene.pp_calculate_direction_properties


def get_mesh_operations_settings(context: bpy.types.Context) -> 'PivotPainterDefaultMeshOperationsProperties':
    return context.scene.pp_default_mesh_operations


def onRegister():
    textures_list = get_textures_list_settings(bpy.context)
    if len(textures_list) > 0:
        return
    textures_list.add()


def register():
    bpy.utils.register_class(PivotPainterHierarchyBaseMeshProperties)
    bpy.utils.register_class(PivotPainterTextureOptionProperties)
    bpy.types.Scene.pp_textures_list = bpy.props.CollectionProperty(type=PivotPainterTextureOptionProperties)
    bpy.app.timers.register(onRegister, first_interval=0)

    for property_class, property_name in property_classes:
        bpy.utils.register_class(property_class)
        setattr(bpy.types.Scene, property_name, bpy.props.PointerProperty(type=property_class))
    # bpy.types.Scene.pp_texture_properties['textures'][1]


def unregister():
    bpy.utils.unregister_class(PivotPainterHierarchyBaseMeshProperties)
    bpy.utils.unregister_class(PivotPainterTextureOptionProperties)
    delattr(bpy.types.Scene, 'pp_textures_list')
    for property_class, property_name in property_classes:
        bpy.utils.unregister_class(property_class)
        delattr(bpy.types.Scene, property_name)

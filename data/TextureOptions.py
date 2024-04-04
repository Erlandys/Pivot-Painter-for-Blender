from typing import Callable, Type

import bpy


texture_rgb_options: dict[str, 'PivotPainterTextureTypeData'] = {}
texture_alpha_options: dict[str, 'PivotPainterTextureTypeData'] = {}


class PivotPainterTextureTypeData:
    from ..data.TexturePackingFunctions import TexturePacking
    __key: str
    __display_name: str = ""
    __description: str = ""
    __packer: Type['TexturePacking']
    __texture_suffix: str = ""
    __build_hierarchy: bool = False
    __test_selection_order: bool = False
    __test_bound_box_center: bool = False
    __rgba: bool = False

    @staticmethod
    def create_alpha_option(
            key: str
            , display_name: str
            , description: str
            , packer: Type['TexturePacking']
            , texture_suffix: str
            , test_selection_order: bool = False
            , test_bound_box_center: bool = False):
        new_option = PivotPainterTextureTypeData()
        new_option.__key = key
        new_option.__display_name = display_name
        new_option.__description = description
        new_option.__packer = packer
        new_option.__texture_suffix = texture_suffix
        new_option.__test_selection_order = test_selection_order
        new_option.__test_bound_box_center = test_bound_box_center
        texture_alpha_options[key] = new_option

    @staticmethod
    def create_rgb_option(
            key: str
            , display_name: str
            , description: str
            , packer: Type['TexturePacking']
            , texture_suffix: str
            , test_selection_order: bool = False
            , test_bound_box_center: bool = False
            , rgba: bool = False):
        new_option = PivotPainterTextureTypeData()
        new_option.__key = key
        new_option.__display_name = display_name
        new_option.__description = description
        new_option.__packer = packer
        new_option.__texture_suffix = texture_suffix
        new_option.__test_selection_order = test_selection_order
        new_option.__test_bound_box_center = test_bound_box_center
        new_option.__rgba = rgba
        texture_rgb_options[key] = new_option

    def key(self) -> str:
        return self.__key

    def display_name(self) -> str:
        return self.__display_name

    def description(self) -> str:
        return self.__description

    def packer(self, context: bpy.types.Context, selection: list[bpy.types.Object], is_hdr: bool) -> 'TexturePacking':
        from ..Properties import get_texture_settings
        from ..data.TexturePackingFunctions import TexturePacking
        packer_object: TexturePacking = TexturePacking.__new__(self.__packer)
        packer_object.__init__(get_texture_settings(context), selection, is_hdr)
        return packer_object

    def suffix(self):
        return self.__texture_suffix

    def test_selection_order(self) -> bool:
        return self.__test_selection_order

    def test_bound_box_center(self) -> bool:
        return self.__test_bound_box_center

    def rgba(self) -> bool:
        return self.__rgba

    def get_property_definition(self) -> tuple[str, str, str]:
        return self.__key, self.__display_name, self.__description


def register():
    ###########################################################
    ###################  ALPHA HDR OPTIONS ####################
    ###########################################################

    from ..data.TexturePackingFunctions import PackObjectParentIndex
    PivotPainterTextureTypeData.create_alpha_option(
        key="index",
        display_name="Parent Index ( Int as float )",
        description="The index number of each part.",
        packer=PackObjectParentIndex,
        texture_suffix="Index",
    )
    from ..data.TexturePackingFunctions import PackObjectParentsNum
    PivotPainterTextureTypeData.create_alpha_option(
        key="steps",
        display_name="Number of Steps From Root",
        description="The level in the hierarchy.",
        packer=PackObjectParentsNum,
        texture_suffix="Steps"
    )
    from ..data.TexturePackingFunctions import PackRandomFloat
    PivotPainterTextureTypeData.create_alpha_option(
        key="random",
        display_name="Random 0-1 Value Per Element",
        description="Creates a random number per object.",
        packer=PackRandomFloat,
        texture_suffix="Random",
    )
    from ..data.TexturePackingFunctions import PackDiagonalBoundBoxLength
    PivotPainterTextureTypeData.create_alpha_option(
        key="diameter",
        display_name="Bounding Box Diameter",
        description="The length of the diagonal of the bound box before scale.",
        packer=PackDiagonalBoundBoxLength,
        texture_suffix="Diameter"
    )
    from ..data.TexturePackingFunctions import PackSelectionOrder
    PivotPainterTextureTypeData.create_alpha_option(
        key="selection_order",
        display_name="Selection Order ( Int as float )",
        description="First create selection order from the extra options.\nAfter you create the order, you can change it.\nYou can also set more objects on the same number,\nor skip numbers to create empty time in the animation.\n",
        packer=PackSelectionOrder,
        texture_suffix="SelectionOrder",
        test_selection_order=True
    )
    from ..data.TexturePackingFunctions import PackNormalizedObjectParentsNum
    PivotPainterTextureTypeData.create_alpha_option(
        key="hierarchy",
        display_name="Normalized 0-1 Hierarchy Position",
        description="Object number/ Total number of objects.",
        packer=PackNormalizedObjectParentsNum,
        texture_suffix="Hierarchy"
    )
    from ..data.TexturePackingFunctions import PackXExtent
    PivotPainterTextureTypeData.create_alpha_option(
        key="x_extent",
        display_name="Object X Extent",
        description="The extent of each object on its local X axis.\nValue source is the X Dimension.",
        packer=PackXExtent,
        texture_suffix="XWidth",
        test_bound_box_center=True
    )
    from ..data.TexturePackingFunctions import PackYExtent
    PivotPainterTextureTypeData.create_alpha_option(
        key="y_extent",
        display_name="Object Y Extent",
        description="The extent of each object on its local Y axis.\nValue source is the Y Dimension.",
        packer=PackYExtent,
        texture_suffix="YDepth"
    )
    from ..data.TexturePackingFunctions import PackZExtent
    PivotPainterTextureTypeData.create_alpha_option(
        key="z_extent",
        display_name="Object Z Extent",
        description="The extent of each object on its local Z axis.\nValue source is the Z Dimension.",
        packer=PackZExtent,
        texture_suffix="ZHeight"
    )
    from ..data.TexturePackingFunctions import PackDiagonalBoundBoxScaledLength
    PivotPainterTextureTypeData.create_alpha_option(
        key="diameter_scaled",
        display_name="Scaled Bounding Box Diameter",
        description="The length of the diagonal of the bound box WITH scale taken into calculation.",
        packer=PackDiagonalBoundBoxScaledLength,
        texture_suffix="DiameterScaled"
    )
    from ..data.TexturePackingFunctions import PackEmptyAlpha
    PivotPainterTextureTypeData.create_alpha_option(
        key="none",
        display_name="None",
        description="Will use as alpha value 0",
        packer=PackEmptyAlpha,
        texture_suffix="None"
    )

    ###########################################################
    ####################  RGB HDR OPTIONS #####################
    ###########################################################

    from ..data.TexturePackingFunctions import PackPivot
    PivotPainterTextureTypeData.create_rgb_option(
        key="pivot_point",
        display_name="Pivot Point",
        description="The origin point of each object.",
        packer=PackPivot,
        texture_suffix="PivotPoint"
    )
    from ..data.TexturePackingFunctions import PackRelativeParentPivot
    PivotPainterTextureTypeData.create_rgb_option(
        key="parent_relative_pivot_point",
        display_name="Parent Relative Pivot Point",
        description="Pivot relative to parent position.",
        packer=PackRelativeParentPivot,
        texture_suffix="RelativePivot"
    )
    from ..data.TexturePackingFunctions import PackOrigin
    PivotPainterTextureTypeData.create_rgb_option(
        key="origin_position",
        display_name="Origin Position",
        description="The bound box center of each object.",
        packer=PackOrigin,
        texture_suffix="OriginPosition"
    )
    from ..data.TexturePackingFunctions import PackExtents
    PivotPainterTextureTypeData.create_rgb_option(
        key="origin_extents",
        display_name="Origin Extents",
        description="The maximum length of every local axis of each object\nValues source are the object Dimensions.",
        packer=PackExtents,
        texture_suffix="OriginExtents"
    )

    ###########################################################
    ####################  RGB LDR OPTIONS #####################
    ###########################################################

    from ..data.TexturePackingFunctions import PackXAxis
    PivotPainterTextureTypeData.create_rgb_option(
        key="x_axis",
        display_name="X Axis",
        description="X Axis from rotation.",
        packer=PackXAxis,
        texture_suffix="XAxis",
        test_bound_box_center=True
    )
    from ..data.TexturePackingFunctions import PackYAxis
    PivotPainterTextureTypeData.create_rgb_option(
        key="y_axis",
        display_name="Y Axis",
        description="Y Axis from rotation.",
        packer=PackYAxis,
        texture_suffix="YAxis"
    )
    from ..data.TexturePackingFunctions import PackZAxis
    PivotPainterTextureTypeData.create_rgb_option(
        key="z_axis",
        display_name="Z Axis",
        description="Z Axis from rotation.",
        packer=PackZAxis,
        texture_suffix="ZAxis"
    )
    from ..data.TexturePackingFunctions import PackParentsNumRandomDiameter
    PivotPainterTextureTypeData.create_rgb_option(
        key="hierarchy_random_diameter",
        display_name="Hierarchy 0-1, Random 0-1, BBox Diameter",
        description="Object number / Total number of objects in Red channel\n\nRandom number per object in Green channel\n\nThe length of the diagonal of the bound box WITH scale taken into calculation\nValues between 8-2048 in increments of 8 in Blue channel",
        packer=PackParentsNumRandomDiameter,
        texture_suffix="HierarchyRandomDiameter"
    )
    from ..data.TexturePackingFunctions import PackEmptyRGB
    PivotPainterTextureTypeData.create_rgb_option(
        key="none",
        display_name="None",
        description="Will use as rgb values 0",
        packer=PackEmptyRGB,
        texture_suffix="None"
    )

    ###########################################################
    #####################  RGBA OPTIONS #######################
    ###########################################################

    from ..data.TexturePackingFunctions import PackQuaternion
    PivotPainterTextureTypeData.create_rgb_option(
        key="quaternion",
        display_name="Quaternion Rotation",
        description="Packs quaternion rotation",
        packer=PackQuaternion,
        texture_suffix="Quaternion",
        rgba=True
    )


register()
